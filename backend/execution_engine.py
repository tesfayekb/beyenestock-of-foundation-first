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

        return {
            "fill_price": round(actual_fill, 4),
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

            contracts = signal.get("contracts", 0)
            if contracts <= 0:
                logger.warning(
                    "open_virtual_position_zero_contracts",
                    signal_strategy=signal.get("strategy_type"),
                )
                return None

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
                "entry_credit": fill["fill_price"],
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

            # Phase A: decision_context snapshot for A/B analysis.
            # Records which flags/models were active when this trade fired.
            # Enables future analysis of "what changed between period A and B".
            # ExecutionEngine has no Redis client, so flag fields default
            # to False; static config + prediction metadata are always written.
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

            write_audit_log(
                action="trading.virtual_position_opened",
                target_type="trading_positions",
                target_id=str(position_id) if position_id else None,
                metadata={
                    "strategy_type": strategy_type,
                    "contracts": contracts,
                    "entry_credit": fill["fill_price"],
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
                    # No MTM data available — use 50% as last resort
                    exit_credit = round(entry_credit * 0.50, 4)

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
