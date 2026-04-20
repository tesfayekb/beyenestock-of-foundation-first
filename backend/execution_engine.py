"""
Execution engine — virtual position recorder.
position_mode='virtual'. No real Tradier orders in Phase 2.
Implements D-006 (OCO placeholder), D-022 counters, full audit trail.
"""
from datetime import datetime, timezone
from typing import Optional

from db import get_client, write_health_status, write_audit_log
from logger import get_logger
from risk_engine import check_execution_quality
from session_manager import get_today_session, update_session
from strategy_selector import STATIC_SLIPPAGE_BY_STRATEGY

logger = get_logger("execution_engine")


def _submit_oco_bracket(
    signal: dict,
    fill: dict,
    position_id: str,
) -> Optional[str]:
    """
    Submit an OCO bracket order to Tradier for real-capital positions.
    Returns the Tradier order ID on success, None on any failure.
    Fail-open: never raises.

    ###################################################################
    #  SCAFFOLD ONLY -- DO NOT SET OCO_BRACKET_ENABLED=TRUE WITHOUT   #
    #  ADDRESSING EVERY MUST-FIX BELOW.                               #
    #                                                                 #
    #  The code below builds a bracket payload that is KNOWN to be    #
    #  wrong for most of our strategies. The dual TRADIER_SANDBOX /   #
    #  OCO_BRACKET_ENABLED guard in the caller keeps this function    #
    #  dormant until these are fixed. Submitting it against a real    #
    #  Tradier account today will produce rejected orders at best,    #
    #  unintended fills at worst.                                     #
    #                                                                 #
    #  MUST FIX before flipping OCO_BRACKET_ENABLED=true:             #
    #                                                                 #
    #  1. SIDE INFERENCE                                              #
    #     '"side": "buy_to_close"' hardcoded below is correct only    #
    #     for credit strategies (credit spreads, iron_condor,         #
    #     iron_butterfly). Debit strategies (long_*, debit_*_spread,  #
    #     long_straddle, calendar_spread) were opened with            #
    #     buy_to_open and must close with sell_to_close. Infer from   #
    #     strategy_type or fill["signed_fill"] sign.                  #
    #                                                                 #
    #  2. TP/SL MATH (DEBIT STRATEGIES)                               #
    #     tp/sl below compute 'entry_credit * 0.60' and               #
    #     'entry_credit * 2.50' -- correct for credits but INVERTED   #
    #     for debits. For a $1.50 long call, close at $0.90 is a      #
    #     40% loss not a 40% profit. Branch on strategy_type.         #
    #                                                                 #
    #  3. MULTI-LEG CLOSE ORDER SHAPE                                 #
    #     Tradier 'class: bracket' on a single 'symbol: SPX' cannot   #
    #     close a 2-to-4-leg spread. SPX is an index -- Tradier       #
    #     rejects it for option close orders outright. Multi-leg      #
    #     closes require 'class: multileg' with per-leg OCC symbols   #
    #     (e.g. SPXW241220P05000000) built from short_strike /        #
    #     long_strike / expiry_date on the position. See              #
    #     backend/strike_selector.py for OCC symbol construction.     #
    #                                                                 #
    #  4. SANDBOX VERIFICATION                                        #
    #     Once 1-3 are addressed, validate the order shape in the     #
    #     Tradier sandbox account first with OCO_BRACKET_ENABLED=true #
    #     and TRADIER_SANDBOX=true. Only after a full round-trip      #
    #     there (submit -> fill -> cancel) should production enable   #
    #     it. The dual-flag guard below is precisely what makes       #
    #     that staged rollout possible.                                #
    ###################################################################
    """
    try:
        import config
        import requests

        account_id = getattr(config, "TRADIER_ACCOUNT_ID", None)
        api_key = getattr(config, "TRADIER_API_KEY", None)
        if not account_id or not api_key:
            logger.warning("oco_bracket_missing_credentials")
            return None

        entry_credit = abs(float(fill.get("signed_fill") or 0))
        if entry_credit <= 0:
            return None

        tp_debit = round(entry_credit * (1 - 0.40), 2)   # buy back at 40% profit
        sl_debit = round(entry_credit * (1 + 1.50), 2)   # buy back at 150% loss

        # Tradier bracket order — see MUST-FIX #3 above re: multi-leg shape.
        payload = {
            "class": "bracket",
            "symbol": signal.get("instrument", "SPX"),
            "side": "buy_to_close",
            "quantity": str(signal.get("contracts", 1)),
            "type": "limit",
            "duration": "day",
            "price": str(tp_debit),
            "stop": str(sl_debit),
            "tag": f"mm_{position_id[:8]}",
        }

        # Base URL pattern mirrors gex_engine / position_monitor:
        # sandbox host for TRADIER_SANDBOX=true, prod host otherwise.
        # OCO submission is additionally gated on OCO_BRACKET_ENABLED,
        # but keeping the URL branch here means the sandbox test plan
        # in MUST-FIX #4 can exercise the prod/sandbox split cleanly.
        base_url = (
            "https://sandbox.tradier.com"
            if getattr(config, "TRADIER_SANDBOX", True)
            else "https://api.tradier.com"
        )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        resp = requests.post(
            f"{base_url}/v1/accounts/{account_id}/orders",
            data=payload,
            headers=headers,
            timeout=5,
        )
        if resp.status_code == 200:
            order_data = resp.json()
            order_id = str(order_data.get("order", {}).get("id", ""))
            if order_id:
                return order_id
            logger.warning("oco_bracket_no_order_id", response=resp.text[:200])
            return None
        else:
            logger.warning(
                "oco_bracket_api_error",
                status=resp.status_code,
                body=resp.text[:200],
            )
            return None

    except Exception as exc:
        logger.warning("oco_bracket_exception", error=str(exc))
        return None


class ExecutionEngine:

    # Legs per strategy (entry leg count × 2 sides = total commissions)
    LEGS_BY_STRATEGY = {
        "put_credit_spread":  4,  # 2 legs × open + close
        "call_credit_spread": 4,
        "debit_put_spread":   4,
        "debit_call_spread":  4,
        "iron_condor":        8,  # 4 legs × open + close
        "iron_butterfly":     8,
        "long_put":           2,  # 1 leg × open + close
        "long_call":          2,
    }

    def _simulate_fill(
        self, target_credit: Optional[float], strategy_type: str
    ) -> dict:
        """
        Simulate a virtual fill with realistic slippage perturbation.
        D-015 placeholder: actual slippage drawn from N(predicted, 20%) distribution.
        Real fill simulation via walk-the-book in Phase 5.
        """
        import random
        predicted_slippage = STATIC_SLIPPAGE_BY_STRATEGY.get(strategy_type, 0.15)
        base_credit = target_credit if target_credit else 1.50

        # Perturb actual slippage with ±20% noise — makes D-019 meaningful
        # actual = predicted * (1 + N(0, 0.2)), clamped to [0.5×, 2.0×] predicted
        noise = random.gauss(0, 0.20)
        actual_slippage = round(
            max(predicted_slippage * 0.5, min(predicted_slippage * 2.0,
            predicted_slippage * (1 + noise))), 4
        )
        is_debit = base_credit < 0
        if is_debit:
            # Debit: cost paid = abs(credit) + slippage (worse fill = more cost)
            actual_fill = round(abs(base_credit) + actual_slippage, 4)
        else:
            # Credit: premium received = credit - slippage (worse fill = less received)
            actual_fill = max(0.05, base_credit - actual_slippage)

        # S4 / A-1: store SIGNED entry premium so downstream consumers
        # (mark_to_market, position_monitor, close_virtual_position) can
        # detect debit vs credit via `entry_credit < 0`. Prior to this
        # fix `entry_credit` was always positive — `is_debit_pos` was
        # silently False, so all long_* and debit_*_spread positions
        # closed under the credit P&L formula and booked the wrong sign
        # of gross_pnl. `fill_price` is preserved (positive magnitude)
        # for the audit log and for the legacy commission ratio at
        # line ~384.
        signed_fill = -round(actual_fill, 4) if is_debit else round(actual_fill, 4)
        return {
            "fill_price": round(actual_fill, 4),
            "signed_fill": signed_fill,
            "is_debit": is_debit,
            "predicted_slippage": predicted_slippage,
            "actual_slippage": actual_slippage,
        }

    def open_virtual_position(
        self, signal: dict, prediction: dict
    ) -> Optional[dict]:
        """
        Record a new virtual position in trading_positions.
        Writes audit log and updates session counters.
        Returns created row or None on failure. Never raises.
        """
        try:
            session = get_today_session()
            if not session:
                logger.warning("open_virtual_position_no_session")
                return None

            # S4 / C-α: defense-in-depth. trading_cycle already gates on
            # session_status before reaching here, but other callers
            # (earnings module, future strategy modules, manual API
            # invocations) bypass that path. Refuse to open positions
            # under halt/closed regardless of how we got here.
            session_status = session.get("session_status")
            if session_status not in ("active", "pending", None):
                logger.info(
                    "open_virtual_position_skipped_session_status",
                    session_status=session_status,
                    strategy=signal.get("strategy_type"),
                )
                return None

            # T0-7: enforce a hard cap on concurrent open positions.
            # Without this, multiple cycles on the same correlated
            # signal can stack into 4-5 overlapping positions on the
            # same direction — turning a sized-as-isolated trade into
            # a leveraged directional bet. count="exact" populates
            # .count (not .data) on the Supabase response.
            #
            # Fail OPEN on count-query failure: a transient Supabase
            # blip must not block trading entirely. The drawdown halt
            # remains the last line of defense.
            MAX_OPEN_POSITIONS = 3
            try:
                open_count_result = (
                    get_client()
                    .table("trading_positions")
                    .select("id", count="exact")
                    .eq("session_id", session["id"])
                    .in_("status", ["open", "partial"])
                    .execute()
                )
                open_count = open_count_result.count or 0
                if open_count >= MAX_OPEN_POSITIONS:
                    logger.info(
                        "open_virtual_position_cap_reached",
                        open_count=open_count,
                        max_allowed=MAX_OPEN_POSITIONS,
                        strategy=signal.get("strategy_type"),
                    )
                    return None
            except Exception as cap_exc:
                logger.warning(
                    "open_position_cap_check_failed",
                    error=str(cap_exc),
                )

            # P-day butterfly safety sprint (Opus 4.7 review 2026-04-20,
            # recalibrated in follow-up commit): prevent piling into a
            # failing thesis. If any already-open position of the same
            # strategy is at >= 75% of its max loss, block new entries
            # in that strategy. A position at 50% of max loss still has
            # half the stop-loss distance remaining and may be recovering;
            # 75% is a genuine "about to stop out" signal where adding
            # another entry to the same thesis is reckless.
            #
            # Max loss math must match position_monitor.py L526 exactly:
            #   max_profit = abs(entry_credit) * contracts * 100
            #   stop_loss_threshold = -(max_profit * 1.5)
            # so max_loss = abs(entry) * 1.5 * contracts * 100 (dollars).
            # current_pnl is stored in total dollars (same units).
            #
            # Fail OPEN on query error — a transient Supabase blip must
            # not block trading. Regime/frequency caps are the backstops.
            try:
                strategy_type_new = signal.get("strategy_type", "")
                if strategy_type_new:
                    open_same = (
                        get_client()
                        .table("trading_positions")
                        .select("current_pnl, entry_credit, contracts")
                        .eq("session_id", session["id"])
                        .eq("strategy_type", strategy_type_new)
                        .in_("status", ["open", "partial"])
                        .execute()
                    )
                    for p in (open_same.data or []):
                        entry = float(p.get("entry_credit") or 0)
                        pnl = float(p.get("current_pnl") or 0)
                        pos_contracts = int(p.get("contracts") or 1)
                        max_loss = abs(entry) * 1.5 * pos_contracts * 100
                        if max_loss > 0 and abs(pnl) >= max_loss * 0.75 and pnl < 0:
                            logger.info(
                                "open_position_blocked_same_strategy_drawdown",
                                strategy=strategy_type_new,
                                existing_pnl=round(pnl, 2),
                                max_loss=round(max_loss, 2),
                                pct_of_max_loss=round(abs(pnl) / max_loss, 3),
                            )
                            return None
            except Exception as drawdown_exc:
                logger.warning(
                    "same_strategy_drawdown_check_failed",
                    error=str(drawdown_exc),
                )

            contracts = signal.get("contracts", 0)
            if contracts <= 0:
                logger.warning(
                    "open_virtual_position_zero_contracts",
                    signal_strategy=signal.get("strategy_type"),
                )
                return None

            # 12K: Loop 2 meta-label scoring.
            #
            # Activation contract:
            #   * No pkl file → ENTIRE block falls through immediately.
            #     Zero change to any trade decision until
            #     train_meta_label_model() has produced the file AND
            #     an operator has deployed it.
            #   * Fail-open: ANY exception inside this block lets the
            #     trade proceed with its pre-meta contracts count.
            #     The meta-label model is observability + soft gating,
            #     never a hard blocker on an inference error.
            #
            # Feature order MUST stay in lockstep with
            # model_retraining.train_meta_label_model()'s feature matrix
            # construction. A drift between the two silently corrupts
            # every score the model produces.
            #
            # Decision thresholds (from the 12K spec):
            #   score < 0.55  → skip trade (early return None)
            #   0.55 ≤ s < 0.75 → normal sizing, contracts unchanged
            #   score ≥ 0.75  → boost contracts by 1.5× (integer
            #     truncation) with a hard 2× ceiling. The 2× ceiling
            #     is belt-and-suspenders today (1.5× can never exceed
            #     2×) but documents intent if the boost factor is ever
            #     raised, and keeps the upstream Kelly/RCS sizing
            #     contract bounded to a known multiple.
            # Section 13 Batch 1: Redis-authoritative feature flag
            # kill-switch. Fail-open so today's behaviour is
            # preserved when the flag has never been set:
            #   missing / client-None / read error → ENABLED
            #   value == "false"                   → DISABLED
            _meta_label_enabled = True
            try:
                _redis_client = getattr(self, "redis_client", None)
                if _redis_client is not None:
                    _raw = _redis_client.get("model:meta_label:enabled")
                    if _raw in ("false", b"false"):
                        _meta_label_enabled = False
            except Exception:
                pass  # fail-open

            try:
                from pathlib import Path
                _model_path = (
                    Path(__file__).parent / "models" / "meta_label_v1.pkl"
                )
                if _meta_label_enabled and _model_path.exists():
                    import pickle
                    import numpy as np
                    with open(_model_path, "rb") as _f:
                        _meta_model = pickle.load(_f)

                    _pred = prediction or {}
                    # 9-feature vector — MUST match
                    # model_retraining.train_meta_label_model() and
                    # run_meta_label_champion_challenger._row_to_features
                    # in order and content. Section 13 Batch 1 dropped
                    # `signal_weak` across all three sites because its
                    # training distribution was a constant 0 (the
                    # training filter is no_trade_signal=False and
                    # signal_weak=True forces no_trade_signal=True).
                    _feat = np.array([[
                        float(_pred.get("confidence") or 0),
                        float(_pred.get("vvix_z_score") or 0),
                        float(_pred.get("gex_confidence") or 0),
                        float(_pred.get("cv_stress_score") or 0),
                        float(_pred.get("vix") or 18.0),
                        float(_pred.get("prior_session_return") or 0),
                        float(_pred.get("vix_term_ratio") or 1.0),
                        float(_pred.get("spx_momentum_4h") or 0),
                        float(_pred.get("gex_flip_proximity") or 0),
                    ]])
                    _score = float(_meta_model.predict_proba(_feat)[0][1])

                    if _score < 0.55:
                        logger.info(
                            "meta_label_trade_skipped",
                            score=round(_score, 3),
                            strategy=signal.get("strategy_type"),
                        )
                        return None
                    elif _score >= 0.75:
                        _orig = int(signal.get("contracts") or 0)
                        if _orig > 0:
                            _boosted = min(
                                _orig * 2,
                                max(_orig, int(_orig * 1.5)),
                            )
                            if _boosted != _orig:
                                signal = {**signal, "contracts": _boosted}
                                contracts = _boosted
                                logger.info(
                                    "meta_label_sizing_boosted",
                                    score=round(_score, 3),
                                    original=_orig,
                                    boosted=_boosted,
                                    cap_multiple=2,
                                )
            except Exception as _meta_exc:
                logger.warning(
                    "meta_label_scoring_failed_fail_open",
                    error=str(_meta_exc),
                )

            strategy_type = signal.get("strategy_type", "unknown")
            fill = self._simulate_fill(
                signal.get("target_credit"), strategy_type
            )

            position = {
                "session_id": signal.get("session_id"),
                "position_mode": "virtual",
                "instrument": signal.get("instrument", "SPX"),
                "strategy_type": strategy_type,
                "position_type": signal.get("position_type", "core"),
                "entry_at": datetime.now(timezone.utc).isoformat(),
                # S4 / A-1: signed_fill is negative for debit strategies
                # (long_*, debit_*_spread, long_straddle, calendar_spread)
                # and positive for credit strategies. Required for
                # is_debit_pos detection in close_virtual_position and
                # in mark_to_market._price_position.
                "entry_credit": fill["signed_fill"],
                "entry_slippage": fill["actual_slippage"],
                "entry_spx_price": prediction.get("spx_price", 5000.0),
                "entry_regime": signal.get("regime_at_signal"),
                "entry_rcs": signal.get("rcs_at_signal"),
                "entry_cv_stress": signal.get("cv_stress_at_signal"),
                "entry_touch_prob": 0.05,
                "entry_greeks": {},
                "contracts": contracts,
                "expiry_date": signal.get("expiry_date"),
                "far_expiry_date": signal.get("far_expiry_date"),
                "short_strike": signal.get("short_strike"),
                "long_strike": signal.get("long_strike"),
                "short_strike_2": signal.get("short_strike_2"),
                "long_strike_2": signal.get("long_strike_2"),
                "current_state": 1,
                "current_pnl": 0.0,
                "peak_pnl": 0.0,
                "current_touch_prob": 0.05,
                "current_cv_stress": prediction.get("cv_stress_score", 0.0),
                "status": "open",
            }

            # Phase A / Session 1+2: decision_context snapshot.
            # The strategy selector now provides a rich decision_context
            # dict (signal multipliers, flag state at the exact moment of
            # selection) via signal["decision_context"]. Prefer it.
            #
            # C-2 fix: ExecutionEngine has no Redis client of its own, so
            # the legacy fallback path defaulted every flag field to False
            # — corrupting the audit trail. The selector-provided context
            # is always more accurate (captured at selection time, not at
            # order time which can lag by seconds).
            #
            # The fallback path below is preserved for any signal that
            # somehow arrives without selector context (legacy callers,
            # tests, future strategy modules that bypass the selector).
            signal_ctx = signal.get("decision_context")
            if signal_ctx:
                try:
                    import config as _cfg
                    position["decision_context"] = {
                        **signal_ctx,
                        # Layer in static config + prediction metadata
                        # that the selector does not have access to.
                        "ai_provider":       getattr(_cfg, "AI_PROVIDER", "anthropic"),
                        "ai_model":          getattr(_cfg, "AI_MODEL", "claude-sonnet-4-5"),
                        "prediction_source": prediction.get("source", "rule_based"),
                        "prediction_confidence": prediction.get("confidence"),
                        "confluence_score":  prediction.get("confluence_score"),
                    }
                except Exception:
                    position["decision_context"] = signal_ctx
            else:
                # Legacy fallback — stale flag reads from this engine's
                # Redis client (typically absent → all False). Marked
                # with context_source so analytics can filter these out
                # of the meta-label training set.
                try:
                    import config as _cfg
                    redis_client = getattr(self, "redis_client", None)

                    def _flag(key: str) -> bool:
                        if not redis_client:
                            return False
                        try:
                            raw = redis_client.get(key)
                            return raw in ("true", b"true")
                        except Exception:
                            return False

                    position["decision_context"] = {
                        "synthesis_enabled": _flag("agents:ai_synthesis:enabled"),
                        "flow_enabled":      _flag("agents:flow_agent:enabled"),
                        "sentiment_enabled": _flag("agents:sentiment_agent:enabled"),
                        "ai_hint_override":  _flag("strategy:ai_hint_override:enabled"),
                        "ai_provider":       getattr(_cfg, "AI_PROVIDER", "anthropic"),
                        "ai_model":          getattr(_cfg, "AI_MODEL", "claude-sonnet-4-5"),
                        "prediction_source": prediction.get("source", "rule_based"),
                        "prediction_confidence": prediction.get("confidence"),
                        "confluence_score":  prediction.get("confluence_score"),
                        "context_source":    "fallback_no_selector_context",
                    }
                except Exception:
                    position["decision_context"] = {}

            # Phase A: record FK to the prediction that drove this trade
            # (required for Loop 2 meta-label model). Optional — column
            # tolerates NULL for legacy positions.
            pred_id = prediction.get("id")
            if pred_id:
                position["prediction_id"] = pred_id

            result = (
                get_client()
                .table("trading_positions")
                .insert(position)
                .execute()
            )
            created_row = result.data[0] if result.data else position
            position_id = created_row.get("id")

            # 12I (C1): OCO bracket order for real-capital mode only.
            #
            # DUAL-GUARD: submission requires BOTH
            #   (1) TRADIER_SANDBOX=False  — real-capital environment
            #   (2) OCO_BRACKET_ENABLED=True — operator has separately
            #       acknowledged the MUST-FIX items in the docstring of
            #       _submit_oco_bracket and validated the order shape.
            #
            # In paper/sandbox mode, or in any real-capital deploy that
            # has not yet flipped the second switch, this block is a
            # no-op. position_monitor continues to manage exits via P&L
            # polling unchanged. The outer try/except ensures an OCO
            # failure can NEVER fail a position open — the Supabase row
            # above has already been written.
            if position_id:
                try:
                    import config as _cfg
                    _sandbox = getattr(_cfg, "TRADIER_SANDBOX", True)
                    _oco_on = getattr(_cfg, "OCO_BRACKET_ENABLED", False)
                    if (not _sandbox) and _oco_on:
                        _oco_id = _submit_oco_bracket(
                            signal, fill, position_id
                        )
                        if _oco_id:
                            get_client().table(
                                "trading_positions"
                            ).update(
                                {"oco_order_id": _oco_id}
                            ).eq("id", position_id).execute()
                            logger.info(
                                "oco_bracket_submitted",
                                position_id=position_id,
                                oco_id=_oco_id,
                            )
                        else:
                            logger.info(
                                "oco_bracket_skipped_or_failed",
                                position_id=position_id,
                            )
                except Exception as oco_exc:
                    # Never fail a position open due to OCO failure.
                    logger.warning(
                        "oco_bracket_outer_failed",
                        error=str(oco_exc),
                    )

            write_audit_log(
                action="trading.virtual_position_opened",
                target_type="trading_positions",
                target_id=str(position_id) if position_id else None,
                metadata={
                    "strategy_type": strategy_type,
                    "contracts": contracts,
                    # S4 / A-1: log the signed entry premium so audit
                    # rows match the value persisted to entry_credit.
                    "entry_credit": fill["signed_fill"],
                    "session_id": signal.get("session_id"),
                },
            )

            current_count = session.get("virtual_trades_count", 0)
            update_session(
                session["id"],
                virtual_trades_count=current_count + 1,
            )

            logger.info(
                "virtual_position_opened",
                strategy=strategy_type,
                contracts=contracts,
                fill=fill["fill_price"],
            )
            self._write_heartbeat()
            return created_row

        except Exception as e:
            logger.error("open_virtual_position_failed", error=str(e))
            write_health_status(
                "execution_engine",
                "error",
                last_error_message=str(e),
            )
            return None

    def close_virtual_position(
        self,
        position_id: str,
        exit_reason: str,
        exit_credit: Optional[float] = None,
        current_spx_price: Optional[float] = None,
    ) -> bool:
        """
        Close an open virtual position and record P&L.
        Updates session win/loss counters and enforces D-022 audit logging.
        Returns True on success, False on failure. Never raises.
        """
        try:
            result = (
                get_client()
                .table("trading_positions")
                .select("*")
                .eq("id", position_id)
                .eq("status", "open")
                .maybe_single()
                .execute()
            )
            pos = result.data
            if not pos:
                logger.warning(
                    "close_virtual_position_not_found", position_id=position_id
                )
                return False

            strategy_type = pos.get("strategy_type", "unknown")
            entry_credit = pos.get("entry_credit", 1.50)
            contracts = pos.get("contracts", 0)
            session_id = pos.get("session_id")

            exit_slip = STATIC_SLIPPAGE_BY_STRATEGY.get(strategy_type, 0.15)
            if exit_credit is None:
                # Use mark-to-market current_pnl to derive real exit credit
                # Formula: exit_credit = entry_credit - (current_pnl / (contracts * 100))
                current_pnl_mtm = pos.get("current_pnl")
                contracts_count = contracts if contracts > 0 else 1
                if current_pnl_mtm is not None and contracts_count > 0:
                    is_debit_pos = entry_credit < 0
                    abs_entry = abs(entry_credit)
                    if is_debit_pos:
                        # Debit: current_pnl = (current_value - abs_entry) * contracts * 100
                        mtm_value = abs_entry + (current_pnl_mtm / (contracts_count * 100))
                        exit_credit = -round(max(0.01, mtm_value), 4)  # keep negative
                    else:
                        # Credit: current_pnl = (entry_credit - current_value) * contracts * 100
                        mtm_value = entry_credit - (current_pnl_mtm / (contracts_count * 100))
                        exit_credit = round(max(0.01, mtm_value), 4)
                else:
                    # T2-7: refuse to close without a real price.
                    # The previous 50% guess corrupted realized P&L,
                    # Kelly inputs, and the feedback-loop training
                    # data. Better to leave the position open — the
                    # next MTM cycle will price it properly, or the
                    # 2:30/3:45 time-stop jobs will close it cleanly.
                    # Mark as pending_close so EOD reconciliation
                    # picks it up. The pending_close write is best
                    # effort: the important thing is the False return,
                    # which signals the caller (position_monitor /
                    # time-stop jobs) that this attempt failed.
                    logger.error(
                        "close_virtual_position_no_price_available",
                        position_id=position_id,
                        strategy_type=strategy_type,
                        exit_reason=exit_reason,
                    )
                    try:
                        get_client().table("trading_positions").update({
                            "signal_status": "pending_close",
                        }).eq("id", position_id).execute()
                    except Exception as pc_exc:
                        logger.warning(
                            "pending_close_mark_failed",
                            position_id=position_id,
                            error=str(pc_exc),
                        )
                    return False

            # D-019: check execution quality and track degradation
            if session_id:
                predicted_slip = pos.get("entry_slippage") or exit_slip
                actual_slip = exit_slip
                check_execution_quality(
                    predicted_slippage=predicted_slip,
                    actual_slippage=actual_slip,
                    session_id=session_id,
                )

            gross_pnl = (entry_credit - exit_credit) * contracts * 100
            slippage_cost = exit_slip * contracts * 100
            legs = self.LEGS_BY_STRATEGY.get(strategy_type, 4)
            commission_cost = 0.35 * contracts * legs  # Tradier published rate: $0.35/contract/leg
            net_pnl = gross_pnl - slippage_cost - commission_cost

            get_client().table("trading_positions").update(
                {
                    "exit_at": datetime.now(timezone.utc).isoformat(),
                    "exit_credit": exit_credit,
                    "exit_slippage": exit_slip,
                    "exit_reason": exit_reason,
                    "exit_spx_price": current_spx_price,
                    "gross_pnl": round(gross_pnl, 2),
                    "slippage_cost": round(slippage_cost, 2),
                    "commission_cost": round(commission_cost, 2),
                    "net_pnl": round(net_pnl, 2),
                    "status": "closed",
                }
            ).eq("id", position_id).execute()

            # Update session counters
            session_result = (
                get_client()
                .table("trading_sessions")
                .select("*")
                .eq("id", session_id)
                .maybe_single()
                .execute()
            )
            session = session_result.data or {}
            is_win = net_pnl > 0
            virtual_pnl = (session.get("virtual_pnl") or 0.0) + net_pnl
            virtual_wins = (session.get("virtual_wins") or 0) + (1 if is_win else 0)
            virtual_losses = (session.get("virtual_losses") or 0) + (
                0 if is_win else 1
            )

            # D-022: track consecutive losses
            consecutive = session.get("consecutive_losses_today", 0)
            if is_win:
                consecutive = 0
            else:
                consecutive += 1

            update_session(
                session_id,
                virtual_pnl=round(virtual_pnl, 2),
                virtual_wins=virtual_wins,
                virtual_losses=virtual_losses,
                consecutive_losses_today=consecutive,
            )

            # D-022: audit log at 3 or 5 consecutive losses
            if consecutive in (3, 5):
                write_audit_log(
                    action="trading.capital_preservation_triggered",
                    metadata={
                        "session_id": session_id,
                        "consecutive_losses_today": consecutive,
                        "action": "size_50pct" if consecutive == 3 else "session_halt",
                        "net_pnl": round(net_pnl, 2),
                    },
                )
                logger.warning(
                    "capital_preservation_triggered_d022",
                    consecutive=consecutive,
                    session_id=session_id,
                )

                # T0-8: on 5th consecutive loss, enforce the halt.
                # Previously only logged "session_halt" — never called it.
                # Now update session_status so trading_cycle and
                # open_virtual_position both stop immediately.
                # update_session is already imported at module top
                # (line 12) — no local import needed.
                if consecutive == 5:
                    try:
                        update_session(
                            session_id,
                            session_status="halted",
                            halt_reason="D022_five_consecutive_losses",
                        )
                        logger.warning(
                            "session_halted_d022_five_consecutive_losses",
                            session_id=session_id,
                        )
                    except Exception as halt_exc:
                        logger.error(
                            "consecutive_loss_halt_failed",
                            session_id=session_id,
                            error=str(halt_exc),
                        )

            # Write calibration log entry for slippage model training (D-015)
            try:
                cal_entry = {
                    "position_id": position_id,
                    "regime": pos.get("entry_regime"),
                    "predicted_slippage": pos.get("entry_slippage"),
                    "actual_slippage": pos.get("entry_slippage") or exit_slip,
                    "cv_stress_score": pos.get("entry_cv_stress"),
                    "exit_reason": exit_reason,
                    "exit_triggered": exit_reason not in ("profit_target", "manual"),
                    "pct_max_profit": round(
                        (entry_credit - (exit_credit or 0)) / entry_credit, 4
                    ) if entry_credit > 0 else None,
                    "position_state": pos.get("current_state"),
                }
                get_client().table("trading_calibration_log").insert(cal_entry).execute()
            except Exception as cal_err:
                logger.warning("calibration_log_write_failed", error=str(cal_err))

            write_audit_log(
                action="trading.virtual_position_closed",
                target_type="trading_positions",
                target_id=str(position_id),
                metadata={
                    "exit_reason": exit_reason,
                    "net_pnl": round(net_pnl, 2),
                    "gross_pnl": round(gross_pnl, 2),
                    "contracts": contracts,
                    "is_win": is_win,
                },
            )

            logger.info(
                "virtual_position_closed",
                position_id=position_id,
                net_pnl=round(net_pnl, 2),
                exit_reason=exit_reason,
            )
            self._write_heartbeat()
            return True

        except Exception as e:
            logger.error("close_virtual_position_failed", error=str(e))
            write_health_status(
                "execution_engine",
                "error",
                last_error_message=str(e),
            )
            return False

    def _write_heartbeat(self) -> None:
        """Write healthy heartbeat for execution_engine service."""
        try:
            write_health_status("execution_engine", "healthy")
        except Exception as e:
            logger.error("execution_engine_heartbeat_failed", error=str(e))
