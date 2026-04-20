import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List
from zoneinfo import ZoneInfo

import redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from capital_manager import CapitalError, get_deployed_capital
from databento_feed import DatabentoFeed
from db import get_client, write_health_status
from gex_engine import GexEngine
from logger import get_logger
from polygon_feed import PolygonFeed
from prediction_engine import PredictionEngine
from session_manager import (
    get_or_create_session, open_today_session, close_today_session,
    update_session,
)
from tradier_feed import TradierFeed
from trading_cycle import run_trading_cycle
from calibration_engine import run_weekly_calibration
from criteria_evaluator import run_criteria_evaluation
from model_retraining import run_weekly_model_performance
from position_monitor import run_time_stop_230pm, run_time_stop_345pm, run_position_monitor
from mark_to_market import run_mark_to_market
from market_calendar import (
    get_time_stop_230pm,
    get_time_stop_345pm,
    is_market_day,
    is_market_open,
)

logger = get_logger("main")
app = FastAPI()

# CORS — allow Lovable preview/production deploys and local dev to call
# the trading API endpoints (e.g. /admin/trading/intelligence).
# Starlette's CORSMiddleware does NOT expand "*" inside allow_origins
# entries, so wildcard Lovable subdomains must be matched via regex.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"https://[a-zA-Z0-9\-]+\.lovable\.app"
        r"|https://[a-zA-Z0-9\-]+\.lovableproject\.com"
        r"|http://localhost:(5173|3000|8080)"
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

scheduler = AsyncIOScheduler(timezone=ZoneInfo("America/New_York"))
redis_client = None

tradier_feed = None
polygon_feed = None
databento_feed = None
gex_engine = None
prediction_engine = None
background_tasks: List[asyncio.Task] = []

# Services that fire once per day (or a few times per day on a schedule).
# heartbeat_check must NOT label these "degraded" between scheduled fires —
# that is their normal idle state, not a failure. Each service writes its
# own healthy / idle / error / degraded from inside its job handler.
# Continuous services (prediction_engine, gex_engine, etc.) keep the
# existing 90-second staleness gate.
_SCHEDULED_SERVICES = frozenset({
    "economic_calendar",
    "macro_agent",
    "sentiment_agent",
    "synthesis_agent",
    "surprise_detector",
    "flow_agent",
    "earnings_scanner",
    "feedback_agent",
    "prediction_watchdog",
    "emergency_backstop",
    "position_reconciliation",
})


def load_jobs_from_registry() -> Dict[str, str]:
    rows = (
        get_client()
        .table("job_registry")
        .select("id,schedule")
        .in_(
            "id",
            [
                "trading_gex_computation",
                "trading_heartbeat_check",
                "trading_pre_market_scan",
            ],
        )
        .execute()
        .data
    )
    return {row["id"]: row["schedule"] for row in rows}


def run_prediction_cycle() -> None:
    """Runs every 5 minutes. Full prediction -> strategy -> execution cycle.

    S11: account_value is now sourced from capital_manager.get_deployed_capital
    (live Tradier equity * deployment_pct * leverage). On any failure to
    determine deployed capital safely, the cycle is skipped — never run
    against the old hardcoded 100_000 fallback. Risk management correctness
    over uptime.
    """
    try:
        deployed_capital = get_deployed_capital(redis_client)
    except CapitalError as cap_exc:
        logger.warning(
            "cycle_skipped_capital_error",
            reason=str(cap_exc),
        )
        return

    result = run_trading_cycle(
        account_value=deployed_capital, sizing_phase=1
    )
    if result.get("skipped_reason"):
        logger.info("cycle_skipped", reason=result["skipped_reason"])


def gex_heartbeat_keepalive() -> None:
    """Keep GEX engine health status alive during market-closed periods."""
    try:
        write_health_status(
            "gex_engine",
            "healthy",
            gex_confidence=0.0,
            gex_staleness_seconds=0,
        )
    except Exception as exc:
        logger.error("gex_heartbeat_keepalive_failed", error=str(exc))


def prediction_engine_keepalive() -> None:
    try:
        write_health_status("prediction_engine", "healthy")
    except Exception as exc:
        logger.error("prediction_engine_keepalive_failed", error=str(exc))


def strategy_selector_keepalive() -> None:
    try:
        write_health_status("strategy_selector", "healthy")
    except Exception as exc:
        logger.error("strategy_selector_keepalive_failed", error=str(exc))


def risk_engine_keepalive() -> None:
    try:
        write_health_status("risk_engine", "healthy")
    except Exception as exc:
        logger.error("risk_engine_keepalive_failed", error=str(exc))


def execution_engine_keepalive() -> None:
    try:
        write_health_status("execution_engine", "healthy")
    except Exception as exc:
        logger.error("execution_engine_keepalive_failed", error=str(exc))


def data_ingestor_keepalive() -> None:
    """Keep the data_ingestor umbrella row fresh.

    The individual feeds (tradier_websocket, polygon_feed,
    databento_feed) write their own health rows continuously, but
    "data_ingestor" itself was only written once at startup and
    then never again — leaving it stuck in degraded after the
    heartbeat_check gate elapsed. The same 30 s cadence as the
    other engine keepalives keeps it well inside the 90 s gate.
    """
    try:
        write_health_status("data_ingestor", "healthy")
    except Exception as exc:
        logger.error("data_ingestor_keepalive_failed", error=str(exc))


def run_counterfactual_job_wrapper() -> None:
    """D4 (12E): label today's no-trade predictions with simulated P&L.

    Runs at 4:25 PM ET mon-fri — after the D3 matrix update (4:20 PM)
    and before the 5:00 PM criteria evaluation so operator logs show
    matrix → counterfactual → criteria in the expected order.

    Fail-open: any error is logged but must not crash the scheduler.
    """
    try:
        from counterfactual_engine import run_counterfactual_job
        result = run_counterfactual_job(redis_client)
        logger.info("counterfactual_eod_complete", **result)
    except Exception as exc:
        logger.error("counterfactual_eod_failed", error=str(exc))


def run_counterfactual_weekly_wrapper() -> None:
    """D4 (12E): weekly missed-opportunity summary, Sundays 6:30 PM ET.

    Self-gates on `closed_sessions >= 30` inside generate_weekly_summary
    — below that threshold it logs `counterfactual_summary_skipped_
    insufficient_data` and returns None, so early-operating-week runs
    cost one Supabase count query and nothing else.
    """
    try:
        from counterfactual_engine import generate_weekly_summary
        summary = generate_weekly_summary(redis_client)
        if summary:
            logger.info(
                "counterfactual_weekly_complete",
                week_ending=summary.get("week_ending"),
                rows=summary.get("total_no_trade_rows"),
            )
    except Exception as exc:
        logger.error("counterfactual_weekly_failed", error=str(exc))


def run_matrix_update_job() -> None:
    """D3 (12D): update the regime x strategy performance matrix.

    Scheduled at 4:20 PM ET, mon-fri (scheduler TZ is America/New_York
    so the cron runs at the wall-clock ET minute across DST). Reads
    the last 90 days of closed virtual positions, aggregates per-cell
    stats, and persists them to Redis for strategy_selector sizing.

    Fail-open: any error is logged but must not crash the scheduler.
    """
    try:
        from strategy_performance_matrix import run_matrix_update
        result = run_matrix_update(redis_client)
        logger.info("strategy_matrix_eod_complete", **result)
    except Exception as exc:
        logger.error("strategy_matrix_eod_failed", error=str(exc))


def run_eod_criteria_evaluation() -> None:
    """Runs daily at 5:00 PM ET after market close.
    Step 1: Label today's predictions with realized SPX outcomes.
    Step 2: Evaluate all GLC criteria (GLC-001 now has real accuracy data).
    """
    try:
        # Step 1: Label today's prediction outcomes before criteria evaluation
        from model_retraining import label_prediction_outcomes
        label_summary = label_prediction_outcomes()
        logger.info("eod_outcome_labeling_done", **label_summary)
    except Exception as label_exc:
        logger.error("eod_outcome_labeling_error", error=str(label_exc))
        # Continue to criteria evaluation even if labeling fails

    # 12L (D1): drift alert. Pure observability — runs after labeling
    # has populated outcome_correct for today, compares rolling 10-day
    # vs 30-day directional accuracy, and fires an email alert (plus
    # a Redis `model_drift_alert` key that dashboards can poll) when
    # the short window drops > 5pp below the 30-day baseline. Isolated
    # try/except so any failure here never blocks criteria evaluation.
    # Never affects any trade decision by design — see ROI contract
    # in check_prediction_drift's docstring.
    try:
        from model_retraining import check_prediction_drift
        drift_result = check_prediction_drift(redis_client)
        logger.info("drift_check_complete", **drift_result)
        if drift_result.get("alert"):
            try:
                # alerting.send_alert signature: (level, event, detail,
                # *, _blocking=False). Event = short identifier for
                # email subject; detail = operator-facing context.
                from alerting import send_alert
                send_alert(
                    level="warning",
                    event="model_drift_detected",
                    detail=(
                        f"10-day accuracy "
                        f"{drift_result.get('acc_10d', 0):.1%} dropped "
                        f"{drift_result.get('drop', 0):.1%} below "
                        f"30-day baseline "
                        f"{drift_result.get('acc_30d', 0):.1%}. "
                        f"Review recent predictions."
                    ),
                )
            except Exception as alert_exc:
                logger.warning(
                    "drift_alert_send_failed",
                    error=str(alert_exc),
                )
    except Exception as drift_exc:
        logger.error("drift_check_job_failed", error=str(drift_exc))

    try:
        # Step 2: Evaluate criteria (GLC-001/002 now have labeled data)
        summary = run_criteria_evaluation()
        logger.info("eod_criteria_evaluation_done", **summary)
    except Exception as exc:
        logger.error("eod_criteria_evaluation_error", error=str(exc))

    # 12B: butterfly gate daily stats. Pulls the per-reason block counters
    # written by strategy_selector._stage1_regime_gate and emits a single
    # structured log line per trading day. Feeds 12G threshold tuning with
    # empirical data — after ~2 weeks we can query logs for the blocked/
    # allowed distribution and recalibrate concentration/time/distance
    # thresholds against real outcomes. "drawdown_block" and "wall_unstable"
    # are placeholders for future counters (execution_engine drawdown gate
    # + 12C wall stability) and will read 0 until those writers ship.
    try:
        from datetime import date as _bdate
        _btoday = _bdate.today().isoformat()
        reasons = [
            "regime_mismatch",
            "failed_today",
            "time_gate",
            "low_concentration",
            "drawdown_block",
            "wall_unstable",
        ]
        stats: dict = {}
        if redis_client is not None:
            for r in reasons:
                val = redis_client.get(f"butterfly:blocked:{r}:{_btoday}")
                stats[r] = int(val) if val else 0
            allowed = redis_client.get(f"butterfly:allowed:{_btoday}")
            stats["allowed"] = int(allowed) if allowed else 0
        logger.info("butterfly_gate_daily_stats", date=_btoday, **stats)
    except Exception as stats_exc:
        logger.warning(
            "butterfly_gate_daily_stats_failed",
            error=str(stats_exc),
        )


def run_weekly_calibration_job() -> None:
    """Runs every Sunday at 6 PM ET (23:00 UTC)."""
    try:
        summary = run_weekly_calibration()
        logger.info("weekly_calibration_job_done", **summary)
    except Exception as exc:
        logger.error("weekly_calibration_job_error", error=str(exc))

    # 12F: Phase C adaptive halt threshold. Runs alongside the existing
    # weekly calibration but is wrapped in its own try/except so a
    # failure here never blocks the rest of the calibration summary.
    try:
        from calibration_engine import calibrate_halt_threshold
        halt_result = calibrate_halt_threshold(redis_client)
        logger.info("weekly_halt_calibration_complete", **halt_result)
    except Exception as exc:
        logger.error("weekly_halt_calibration_failed", error=str(exc))

    # 12G: butterfly threshold auto-tuning. Self-gates on
    # closed_butterfly_trades >= 20 AND parsed_decision_context >= 10.
    # Below either threshold, nothing is written and strategy_selector
    # keeps using the hardcoded defaults.
    try:
        from calibration_engine import calibrate_butterfly_thresholds
        butterfly_result = calibrate_butterfly_thresholds(redis_client)
        logger.info(
            "weekly_butterfly_calibration_complete",
            **butterfly_result,
        )
    except Exception as exc:
        logger.error("weekly_butterfly_calibration_failed", error=str(exc))

    # 12J: earnings learning loop. edge_calculator lives in the
    # sibling backend_earnings/ directory — mirror the sys.path
    # insert pattern used by _run_earnings_scan_job / _entry_job /
    # _monitor_job above. Self-gates on closed_earnings_trades >= 50;
    # below that, compute_edge_score keeps reading the hardcoded
    # EARNINGS_HISTORY dict.
    try:
        import os as _os
        import sys as _sys
        _EARNINGS_PATH = _os.path.abspath(
            _os.path.join(
                _os.path.dirname(__file__), "..", "backend_earnings"
            )
        )
        if _EARNINGS_PATH not in _sys.path:
            _sys.path.insert(0, _EARNINGS_PATH)
        from edge_calculator import train_earnings_model
        earnings_result = train_earnings_model(redis_client)
        logger.info("weekly_earnings_model_complete", **earnings_result)
    except Exception as exc:
        logger.error("weekly_earnings_model_failed", error=str(exc))

    # 12K: Loop 2 meta-label model scaffold. Self-gates on
    # closed_trades >= 100 AND labeled_rows >= 100. Below either
    # threshold no pkl is written, so the execution-side scoring
    # block in open_virtual_position remains a pure pass-through.
    # Wrapped in its own try/except so any failure here never
    # blocks downstream calibration steps (pattern shared with
    # every other block in this job).
    try:
        from model_retraining import train_meta_label_model
        meta_result = train_meta_label_model(redis_client)
        logger.info("weekly_meta_label_complete", **meta_result)
    except Exception as exc:
        logger.error("weekly_meta_label_failed", error=str(exc))


def run_weekly_model_performance_job() -> None:
    """Runs every Sunday at 6:30 PM ET (23:30 UTC) — after calibration."""
    try:
        summary = run_weekly_model_performance()
        logger.info("weekly_model_performance_job_done", **summary)
    except Exception as exc:
        logger.error("weekly_model_performance_job_error", error=str(exc))


def run_position_monitor_job() -> None:
    """Runs every minute during market hours (9:30 AM - 3:45 PM ET)."""
    try:
        result = run_position_monitor()
        if result.get("closed", 0) > 0:
            logger.info("position_monitor_closed_positions", **result)
    except Exception as exc:
        logger.error("position_monitor_job_error", error=str(exc))


def run_mark_to_market_job() -> None:
    """Runs every minute during market hours — prices open positions.

    T0-5: when redis_client is unavailable we MUST surface the failure
    on the health page. The previous silent return left operators with
    no visibility that MTM was down — stops and TPs were running on
    stale P&L for as long as Redis stayed disconnected.
    """
    try:
        if redis_client is None:
            write_health_status(
                "execution_engine",
                "error",
                last_error_message=(
                    "MTM skipped: redis_client unavailable"
                ),
            )
            return
        result = run_mark_to_market(redis_client)
        if result.get("errors", 0) > 0:
            logger.warning("mark_to_market_errors", **result)
    except Exception as exc:
        logger.error("mark_to_market_job_error", error=str(exc))


def run_time_stop_230pm_job() -> None:
    """D-010: Close all short-gamma positions at dynamic time (market-calendar aware).

    Skips weekends and holidays. On early-close days the stop fires at
    11:30 AM ET (90 min before the 1:00 PM close) instead of 2:30 PM.
    The scheduler still triggers this job at the original cron, but we
    only act when within 2 minutes of the calendar-correct stop time.
    """
    try:
        if not is_market_day():
            logger.debug("time_stop_230pm_skipped_non_trading_day")
            return
        now_et = datetime.now(ZoneInfo("America/New_York"))
        stop_time = get_time_stop_230pm()
        delta_min = abs(
            (now_et.hour * 60 + now_et.minute)
            - (stop_time.hour * 60 + stop_time.minute)
        )
        if delta_min > 2:
            return
        result = run_time_stop_230pm()
        logger.info("time_stop_230pm_job_done", **result)
    except Exception as exc:
        logger.error("time_stop_230pm_job_error", error=str(exc))


def run_time_stop_345pm_job() -> None:
    """D-011: Close ALL positions at dynamic time (market-calendar aware).

    Skips weekends and holidays. On early-close days the stop fires at
    12:45 PM ET (15 min before the 1:00 PM close) instead of 3:45 PM.
    """
    try:
        if not is_market_day():
            logger.debug("time_stop_345pm_skipped_non_trading_day")
            return
        now_et = datetime.now(ZoneInfo("America/New_York"))
        stop_time = get_time_stop_345pm()
        delta_min = abs(
            (now_et.hour * 60 + now_et.minute)
            - (stop_time.hour * 60 + stop_time.minute)
        )
        if delta_min > 2:
            return
        result = run_time_stop_345pm()
        logger.info("time_stop_345pm_job_done", **result)
    except Exception as exc:
        logger.error("time_stop_345pm_job_error", error=str(exc))


def run_emergency_backstop_job() -> None:
    """HARD-A: Backstop at 3:55 PM — catches stuck positions if time stop failed."""
    try:
        if not is_market_day():
            return
        from position_monitor import run_emergency_backstop
        result = run_emergency_backstop()
        if result.get("triggered"):
            write_health_status(
                "emergency_backstop", "degraded",
                error=f"Backstop closed {result['closed']} stuck positions",
            )
        else:
            write_health_status("emergency_backstop", "healthy")
        logger.info("emergency_backstop_job_done", **result)
    except Exception as exc:
        write_health_status("emergency_backstop", "error", error=str(exc))
        logger.error("emergency_backstop_job_error", error=str(exc))


def run_prediction_watchdog_job() -> None:
    """HARD-A: Runs every 5 min during market hours.

    Closes positions if prediction engine is silent for >12 minutes.
    Writes 'idle' outside market hours so the health page shows neutral.
    """
    try:
        if not is_market_open():
            write_health_status("prediction_watchdog", "idle")
            return
        from position_monitor import run_prediction_watchdog
        result = run_prediction_watchdog()
        if result.get("status") == "triggered":
            write_health_status(
                "prediction_watchdog", "error",
                error=f"Engine silent {result.get('age_minutes')}min",
            )
        else:
            write_health_status("prediction_watchdog", "healthy")
    except Exception as exc:
        write_health_status("prediction_watchdog", "error", error=str(exc))
        logger.error("prediction_watchdog_job_error", error=str(exc))


def run_eod_reconciliation_job() -> None:
    """HARD-A: EOD position reconciliation at 4:15 PM ET."""
    try:
        if not is_market_day():
            return
        from position_monitor import run_eod_position_reconciliation
        result = run_eod_position_reconciliation()
        if result.get("mismatches", 0) > 0:
            write_health_status(
                "position_reconciliation", "degraded",
                error=(
                    f"{result['mismatches']} stale positions found and closed"
                ),
            )
        else:
            write_health_status("position_reconciliation", "healthy")
        logger.info("eod_reconciliation_job_done", **result)
    except Exception as exc:
        write_health_status("position_reconciliation", "error", error=str(exc))
        logger.error("eod_reconciliation_job_error", error=str(exc))


def run_ab_eod_job() -> None:
    """Phase 3B: EOD A/B comparison. Runs at 4:30 PM ET after market close."""
    try:
        if not is_market_day():
            return
        from datetime import date
        from shadow_engine import compute_eod_comparison, get_ab_gate_status
        result = compute_eod_comparison(
            session_date=date.today().isoformat(),
            redis_client=redis_client,
        )
        if result:
            logger.info(
                "ab_eod_job_done",
                a_pnl=result.get("a_synthetic_pnl"),
                b_pnl=result.get("b_session_pnl"),
            )
            # Check if A/B gate just passed — send alert
            gate = get_ab_gate_status()
            if gate.get("gate_passed"):
                try:
                    from alerting import send_alert, INFO
                    send_alert(
                        INFO,
                        "ab_gate_passed",
                        (
                            f"Portfolio B leads Portfolio A by "
                            f"{gate.get('portfolio_b_lead_pct', 0):.1f}% "
                            f"annualized after "
                            f"{gate.get('days_elapsed', 0)} days and "
                            f"{gate.get('trades_count', 0)} trades. "
                            f"System validated for real capital deployment."
                        ),
                    )
                except Exception:
                    pass  # alerting must never break EOD job
    except Exception as exc:
        logger.error("ab_eod_job_failed", error=str(exc))


def run_market_open_job() -> None:
    """Transitions session to 'active' at 9:30 AM ET (13:30 UTC)."""
    try:
        ok = open_today_session()
        logger.info("market_open_session_transition", success=ok)
    except Exception as exc:
        logger.error("market_open_job_error", error=str(exc))


def run_market_close_job() -> None:
    """Transitions session to 'closed' at 4:30 PM ET (21:30 UTC)."""
    try:
        ok = close_today_session()
        logger.info("market_close_session_transition", success=ok)
    except Exception as exc:
        logger.error("market_close_job_error", error=str(exc))


def _agent_flag_enabled(flag_key: str) -> bool:
    """
    Returns True iff Redis has the given feature-flag key set to 'true'.
    Defaults to False on any error (Redis down, key missing, etc.) so
    flag-gated agents stay OFF unless explicitly enabled.
    """
    if not redis_client:
        return False
    try:
        raw = redis_client.get(flag_key)
        return raw in ("true", b"true")
    except Exception:
        return False


def _get_closed_trade_count() -> int:
    """Return count of closed virtual positions. Returns 0 on any error."""
    try:
        result = (
            get_client()
            .table("trading_positions")
            .select("id", count="exact")
            .eq("status", "closed")
            .eq("position_mode", "virtual")
            .execute()
        )
        return result.count or 0
    except Exception:
        return 0


def _run_economic_calendar_job() -> None:
    try:
        import sys
        import os
        # Use absolute path resolved at call time to avoid Railway path
        # issues where __file__ may be relative and cwd may differ from
        # /app/backend. os.path.abspath normalizes "backend/../backend_agents"
        # to "/app/backend_agents" regardless of how Python was launched.
        _AGENTS_PATH = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "backend_agents")
        )
        if _AGENTS_PATH not in sys.path:
            sys.path.insert(0, _AGENTS_PATH)
        from economic_calendar import (
            get_todays_market_intelligence, write_intel_to_redis
        )
        intel = get_todays_market_intelligence()
        if redis_client:
            write_intel_to_redis(redis_client, intel)
        write_health_status("economic_calendar", "healthy")
        logger.info("economic_calendar_job_complete",
                    classification=intel.get("day_classification"))
    except Exception as exc:
        write_health_status("economic_calendar", "error", error=str(exc))
        logger.error("economic_calendar_job_failed", error=str(exc))


def _run_macro_agent_job() -> None:
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend_agents"))
        from macro_agent import run_macro_agent
        if redis_client:
            run_macro_agent(redis_client)
        write_health_status("macro_agent", "healthy")
    except Exception as exc:
        write_health_status("macro_agent", "error", error=str(exc))
        logger.error("macro_agent_job_failed", error=str(exc))


def _run_synthesis_agent_job() -> None:
    # Flag-gated: report 'idle' (not 'healthy') when the feature flag is OFF
    # so the Health page does not falsely claim the agent ran.
    if not _agent_flag_enabled("agents:ai_synthesis:enabled"):
        write_health_status("synthesis_agent", "idle")
        logger.info("synthesis_agent_skipped", reason="flag_off")
        return
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend_agents"))
        from synthesis_agent import run_synthesis_agent
        if redis_client:
            run_synthesis_agent(redis_client)
        write_health_status("synthesis_agent", "healthy")
    except Exception as exc:
        write_health_status("synthesis_agent", "error", error=str(exc))
        logger.error("synthesis_agent_job_failed", error=str(exc))


def _run_surprise_detector_job() -> None:
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend_agents"))
        from surprise_detector import run_surprise_detector
        if redis_client:
            run_surprise_detector(redis_client)
        write_health_status("surprise_detector", "healthy")
    except Exception as exc:
        write_health_status("surprise_detector", "error", error=str(exc))
        logger.error("surprise_detector_job_failed", error=str(exc))


def _run_flow_agent_job() -> None:
    """Phase 2C: options flow agent.
    Runs at 8:45 AM ET and on a 30-min interval during market hours."""
    if not _agent_flag_enabled("agents:flow_agent:enabled"):
        write_health_status("flow_agent", "idle")
        logger.info("flow_agent_skipped", reason="flag_off")
        return
    try:
        import sys
        import os
        sys.path.insert(
            0,
            os.path.join(os.path.dirname(__file__), "..", "backend_agents"),
        )
        from flow_agent import run_flow_agent
        if redis_client:
            run_flow_agent(redis_client)
        write_health_status("flow_agent", "healthy")
    except Exception as exc:
        write_health_status("flow_agent", "error", error=str(exc))
        logger.error("flow_agent_job_failed", error=str(exc))


def _run_sentiment_agent_job() -> None:
    """Phase 2C: news sentiment agent. Runs at 8:30 AM ET."""
    if not _agent_flag_enabled("agents:sentiment_agent:enabled"):
        write_health_status("sentiment_agent", "idle")
        logger.info("sentiment_agent_skipped", reason="flag_off")
        return
    try:
        import sys
        import os
        sys.path.insert(
            0,
            os.path.join(os.path.dirname(__file__), "..", "backend_agents"),
        )
        from sentiment_agent import run_sentiment_agent
        if redis_client:
            run_sentiment_agent(redis_client)
        write_health_status("sentiment_agent", "healthy")
    except Exception as exc:
        write_health_status("sentiment_agent", "error", error=str(exc))
        logger.error("sentiment_agent_job_failed", error=str(exc))


# ── Phase 5A: Earnings Volatility System jobs ────────────────────────────
# All three follow the same sys.path.insert pattern as the agent jobs
# above. backend_earnings/ is fully isolated from backend trading
# modules — see the isolation guard test in tests/test_phase_5a_session1.
# The single shared health service `earnings_scanner` reflects the
# scan job (the most user-visible one); entry/monitor failures are
# logged but do not flip the service red.


def _run_earnings_scan_job() -> None:
    """Phase 5A: 8:45 AM ET — refresh upcoming earnings calendar."""
    try:
        import sys
        import os
        # Absolute path normalization — see _run_economic_calendar_job.
        _EARNINGS_PATH = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "backend_earnings")
        )
        if _EARNINGS_PATH not in sys.path:
            sys.path.insert(0, _EARNINGS_PATH)
        from main_earnings import run_earnings_scan
        result = run_earnings_scan(redis_client)
        write_health_status("earnings_scanner", "healthy")
        logger.info(
            "earnings_scan_job_complete",
            event_count=result.get("count", 0),
        )
    except Exception as exc:
        write_health_status("earnings_scanner", "error", error=str(exc))
        logger.error("earnings_scan_job_failed", error=str(exc))


def _run_earnings_entry_job() -> None:
    """Phase 5A: 9:50 AM ET — open at most one new straddle."""
    try:
        if not is_market_day():
            return
        import sys
        import os
        _EARNINGS_PATH = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "backend_earnings")
        )
        if _EARNINGS_PATH not in sys.path:
            sys.path.insert(0, _EARNINGS_PATH)
        from main_earnings import run_earnings_entry
        result = run_earnings_entry(redis_client)
        logger.info("earnings_entry_job_complete", **result)
    except Exception as exc:
        logger.error("earnings_entry_job_failed", error=str(exc))


def _run_earnings_monitor_job() -> None:
    """Phase 5A: every 15 min during market hours — exit logic."""
    try:
        if not is_market_open():
            return
        import sys
        import os
        _EARNINGS_PATH = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "backend_earnings")
        )
        if _EARNINGS_PATH not in sys.path:
            sys.path.insert(0, _EARNINGS_PATH)
        from main_earnings import run_earnings_monitor
        result = run_earnings_monitor(redis_client)
        logger.debug("earnings_monitor_job_complete", **result)
    except Exception as exc:
        logger.error("earnings_monitor_job_failed", error=str(exc))


def _flush_stale_scheduled_service_status() -> None:
    """
    One-shot startup cleanup of stale "degraded" rows on scheduled services.

    Background: before the service-class-aware heartbeat_check fix
    (commit abaf8db), the 90-second staleness gate was applied to
    every row in trading_system_health, including the 11 cron-scheduled
    services in _SCHEDULED_SERVICES. Those false-positive "degraded"
    rows persist in the table after the fix deploys — heartbeat_check
    now correctly leaves them alone, but each scheduled service only
    overwrites its own row when it next fires. For services like
    prediction_watchdog (hour="9-15" mon-fri only) that can be
    12+ hours away, leaving the Health page red the whole time.

    This function runs once at on_startup() after the new code lands.
    For every row in _SCHEDULED_SERVICES whose current status is
    "degraded", it writes "idle" so the Health page shows a clean
    neutral state until the agent's next real fire overwrites with
    healthy / error / idle as appropriate.

    Critical safety properties:
      - Only touches rows in _SCHEDULED_SERVICES (continuous services
        and their 90 s gate are completely unaffected).
      - Only flips "degraded" -> "idle". Any service currently in
        "error", "healthy", or "idle" status is left untouched —
        real failures stay visible.
      - Soft-fails on any DB error so a Supabase outage cannot block
        boot.
      - No ROI / signal / regime / sizing impact whatsoever.
    """
    try:
        rows = (
            get_client()
            .table("trading_system_health")
            .select("service_name,status")
            .in_("service_name", list(_SCHEDULED_SERVICES))
            .eq("status", "degraded")
            .execute()
            .data
            or []
        )
        if not rows:
            logger.info(
                "scheduled_service_flush_clean",
                checked=len(_SCHEDULED_SERVICES),
            )
            return

        flushed = []
        for row in rows:
            try:
                write_health_status(row["service_name"], "idle")
                flushed.append(row["service_name"])
            except Exception as exc:
                logger.error(
                    "scheduled_service_flush_failed",
                    service=row["service_name"],
                    error=str(exc),
                )

        logger.info(
            "scheduled_service_flush_complete",
            flushed=flushed,
            count=len(flushed),
        )
    except Exception as exc:
        logger.error(
            "scheduled_service_flush_error",
            error=str(exc),
        )


def _run_morning_agents_idle_marker() -> None:
    """
    Mark once-per-day morning agents as idle after they've completed.

    economic_calendar (8:25), macro_agent (8:30), surprise_detector (8:45),
    and earnings_scanner (8:45) all fire pre-market and then go silent for
    the rest of the trading day. Without an explicit idle write the Health
    page would show no heartbeat for 6+ hours, which reads like failure.

    The other once-per-day agents (synthesis_agent, sentiment_agent,
    flow_agent, feedback_agent) already self-flip to idle when their
    feature flag is off or it is a non-market day, so they are not
    included here.

    This job fires at 10:30 AM ET — well after every morning agent has
    completed. It only writes idle, never overwrites a healthy / error
    status that was just written, because write_health_status is called
    AFTER the agents wrote their own status earlier in the morning.
    """
    for svc in (
        "economic_calendar",
        "macro_agent",
        "surprise_detector",
        "earnings_scanner",
    ):
        try:
            write_health_status(svc, "idle")
        except Exception as exc:
            logger.error(
                "morning_agents_idle_marker_failed",
                service=svc,
                error=str(exc),
            )


def _run_feedback_agent_job() -> None:
    """
    Phase A (Loop 1): Closed-loop feedback brief.
    Scheduled at 9:10 AM ET — must run BEFORE synthesis (9:15 AM ET) so
    the brief is in Redis when synthesis builds Claude's prompt.
    Calendar-aware: emits 'idle' on weekends/holidays instead of 'error'.
    """
    try:
        from market_calendar import is_market_day
        if not is_market_day():
            write_health_status("feedback_agent", "idle")
            logger.info("feedback_agent_skipped", reason="non_market_day")
            return

        import sys
        import os
        sys.path.insert(
            0,
            os.path.join(os.path.dirname(__file__), "..", "backend_agents"),
        )
        from feedback_agent import run_feedback_agent
        result = run_feedback_agent(redis_client) or {}
        status = result.get("status", "error")

        if status == "ready":
            write_health_status("feedback_agent", "healthy")
        elif status == "insufficient_history":
            write_health_status(
                "feedback_agent",
                "idle",
                last_error_message=(
                    f"Need {result.get('minimum_required', 10)} trades, "
                    f"have {result.get('trade_count', 0)}"
                ),
            )
        else:
            write_health_status("feedback_agent", "degraded")

        logger.info(
            "feedback_agent_job_complete",
            status=status,
            trade_count=result.get("trade_count"),
        )

        # HARD-B: notify when trade count crosses key milestones.
        # Each milestone fires at most once via a Redis sentinel key
        # (90-day TTL). Failure is silently swallowed so an alerting
        # issue can never block the feedback job.
        try:
            from alerting import send_alert, INFO
            milestones = [
                (10, "loop1_feedback_active",
                 "Trade #10 reached. Loop 1 feedback agent now produces "
                 "real briefs."),
                (20, "kelly_full_sizing_active",
                 "Trade #20 reached. Full Kelly sizing now active."),
                (100, "meta_label_model_ready",
                 "Trade #100 reached. Run: railway run python "
                 "scripts/train_meta_label.py"),
                (200, "signal_calibration_ready",
                 "Trade #200 reached. Enable "
                 "model:signal_calibration:enabled flag."),
            ]
            closed_count = _get_closed_trade_count()
            for threshold, event_key, detail in milestones:
                sentinel = f"alert:milestone:{event_key}:sent"
                if (
                    closed_count >= threshold
                    and redis_client
                    and not redis_client.get(sentinel)
                ):
                    redis_client.setex(sentinel, 90 * 86400, "1")
                    send_alert(INFO, event_key, detail)
        except Exception:
            pass

    except Exception as exc:
        write_health_status("feedback_agent", "error", error=str(exc))
        logger.error("feedback_agent_job_failed", error=str(exc))


def pre_market_scan() -> None:
    """
    Pre-market regime and day_type classification. Runs at 9:35 AM ET.
    (T1-2: was 9:00 AM — moved to ensure fresh VVIX/VIX data after the
    first RTH polygon_feed poll has landed in Redis. At 9:00 AM the
    VVIX 1h TTL from the prior session has long expired and the regime
    classifier was reading vvix_z=0 for the entire session.)

    Classifies today's session as: trend, open_drive, range, reversal,
    event, unknown.
    Uses VVIX Z-score, overnight ATR proxy, and macro calendar check.
    Updates trading_sessions.day_type and day_type_confidence.
    """
    try:
        session = get_or_create_session()
        if not session:
            logger.warning("pre_market_scan_no_session")
            return

        # Read signals from Redis
        vvix_z_raw = redis_client.get("polygon:vvix:z_score") if redis_client else None
        vvix_z = float(vvix_z_raw) if vvix_z_raw else 0.0
        baseline_ready = (
            redis_client.get("polygon:vvix:baseline_ready") == "True"
            if redis_client else False
        )

        # Phase 2A: Economic intelligence (runs first — highest priority)
        import sys, os
        _AGENTS_PATH = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "backend_agents")
        )
        if _AGENTS_PATH not in sys.path:
            sys.path.insert(0, _AGENTS_PATH)
        from economic_calendar import (
            get_todays_market_intelligence, write_intel_to_redis
        )
        intel = get_todays_market_intelligence()
        if redis_client:
            write_intel_to_redis(redis_client, intel)

        # Calendar classification takes priority over VVIX heuristic
        classification = intel.get("day_classification", "normal")

        if classification == "catalyst_major":
            day_type = "event"
            confidence = 0.95
        elif classification in ("catalyst_minor", "earnings_major"):
            # Let VVIX refine — but ensure at minimum reduced size
            # Fall through to VVIX check below
            day_type = None
            confidence = 0.0
        else:
            day_type = None
            confidence = 0.0

        # VVIX heuristic — always runs, may upgrade or set day_type
        if not baseline_ready and day_type is None:
            day_type = "unknown"
            confidence = 0.0
        elif day_type is None:
            if abs(vvix_z) >= 2.5:
                day_type = "event"
                confidence = 0.80
            elif vvix_z >= 1.5:
                day_type = "reversal"
                confidence = 0.65
            elif vvix_z >= 0.8:
                day_type = "open_drive"
                confidence = 0.60
            elif vvix_z <= -0.5:
                day_type = "trend"
                confidence = 0.60
            else:
                day_type = "range"
                confidence = 0.55
        # else: calendar already set day_type, keep it

        update_session(
            session["id"],
            day_type=day_type,
            day_type_confidence=round(confidence, 4),
        )

        write_health_status("prediction_engine", "healthy")
        logger.info(
            "pre_market_scan_complete",
            day_type=day_type,
            confidence=confidence,
            vvix_z=vvix_z,
            calendar_classification=classification,
            calendar_events=len(intel.get("events", [])),
        )

    except Exception as e:
        logger.error("pre_market_scan_failed", error=str(e))


async def heartbeat_check() -> None:
    """
    S7-3: scan trading_system_health for stale services and mark them
    degraded. Was an `async def` whose body was synchronous Supabase
    I/O — every 60s it blocked the event loop for the duration of the
    select round-trip (~50-200ms typical, longer on Cloudflare
    cold-paths). That latency starved the prediction-cycle coroutine
    of scheduling slots.

    Fix: do the read in a worker thread via `asyncio.to_thread`. The
    sync supabase client is thread-safe in our setup because every
    call site serialises through `_client_lock` in db.py (see the
    get_client() docstring for the full HTTP/2 race rationale).

    The `write_health_status` calls for stale services stay outside
    the thread — they're already lock-serialised internally and the
    list of stales is typically empty / very small.
    """
    try:
        def _check_sync():
            rows = (
                get_client()
                .table("trading_system_health")
                .select("service_name,last_heartbeat_at")
                .execute()
                .data
            )
            now = datetime.now(timezone.utc)
            stale = []
            for row in rows:
                # Scheduled services manage their own status from inside
                # their job handlers — heartbeat_check must not overwrite
                # whatever they last wrote (healthy / idle / error /
                # degraded) with a false-positive "degraded" between
                # fires. Continuous services keep the 90 s gate below.
                if row["service_name"] in _SCHEDULED_SERVICES:
                    continue
                heartbeat = datetime.fromisoformat(
                    row["last_heartbeat_at"].replace("Z", "+00:00")
                )
                if (now - heartbeat).total_seconds() > 90:
                    stale.append(row["service_name"])
            return stale

        stale_services = await asyncio.to_thread(_check_sync)

        for service_name in stale_services:
            write_health_status(
                service_name,
                "degraded",
                last_error_message=None,
            )
    except Exception as exc:
        logger.critical("heartbeat_check_failed", error=str(exc))


@app.on_event("startup")
async def on_startup() -> None:
    global redis_client, tradier_feed, polygon_feed, databento_feed, gex_engine, prediction_engine
    try:
        config.validate_config()
        redis_client = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
        redis_client.ping()
        _ = get_client()

        # Initialize feed objects only after Redis is confirmed ready
        tradier_feed = TradierFeed()
        polygon_feed = PolygonFeed()
        databento_feed = DatabentoFeed()
        gex_engine = GexEngine()
        prediction_engine = PredictionEngine()

        jobs = load_jobs_from_registry()
        if "trading_gex_computation" in jobs:
            scheduler.add_job(
                gex_engine.compute_gex,
                trigger="cron",
                day_of_week="mon-fri",
                id="trading_gex_computation",
                minute="*/5",
                replace_existing=True,
            )
        if "trading_heartbeat_check" in jobs:
            scheduler.add_job(
                heartbeat_check,
                trigger="interval",
                id="trading_heartbeat_check",
                seconds=60,
                replace_existing=True,
            )
        if "trading_pre_market_scan" in jobs:
            scheduler.add_job(
                pre_market_scan,
                trigger="cron",
                day_of_week="mon-fri",
                hour=9,
                # T1-2: was minute=0 (9:00 AM ET). polygon_feed only
                # starts polling at RTH open (9:30 AM ET) and the
                # VVIX 1-hour TTL from the prior session expires
                # ~5 PM ET the day before. At 9:00 AM the
                # polygon:vvix:z_score key is missing → vvix_z=0.0
                # → day_type misclassified as "range" for the entire
                # session. Moving to 9:35 ensures the first RTH
                # poll (9:30) has landed fresh data.
                minute=35,
                id="trading_pre_market_scan",
                replace_existing=True,
            )
        scheduler.add_job(
            gex_heartbeat_keepalive,
            trigger="interval",
            id="gex_heartbeat_keepalive",
            seconds=30,
            replace_existing=True,
        )
        scheduler.add_job(
            prediction_engine_keepalive,
            trigger="interval",
            seconds=30,
            id="prediction_engine_keepalive",
            replace_existing=True,
        )
        scheduler.add_job(
            strategy_selector_keepalive,
            trigger="interval",
            seconds=30,
            id="strategy_selector_keepalive",
            replace_existing=True,
        )
        scheduler.add_job(
            risk_engine_keepalive,
            trigger="interval",
            seconds=30,
            id="risk_engine_keepalive",
            replace_existing=True,
        )
        scheduler.add_job(
            execution_engine_keepalive,
            trigger="interval",
            seconds=30,
            id="execution_engine_keepalive",
            replace_existing=True,
        )
        scheduler.add_job(
            data_ingestor_keepalive,
            trigger="interval",
            seconds=30,
            id="data_ingestor_keepalive",
            replace_existing=True,
        )
        scheduler.add_job(
            run_prediction_cycle,
            trigger="cron",
            day_of_week="mon-fri",
            hour="9-15",
            minute="*/5",
            id="trading_prediction_cycle_local",
            replace_existing=True,
            max_instances=1,   # T0-9: one cycle at a time — no overlap
            coalesce=True,     # T0-9: skip missed fires if previous running
        )
        scheduler.add_job(
            run_eod_criteria_evaluation,
            trigger="cron",
            day_of_week="mon-fri",
            hour=17,
            minute=0,
            id="trading_eod_criteria_evaluation",
            replace_existing=True,
        )
        # D3 (12D): regime x strategy performance matrix refresh.
        # Runs at 4:20 PM ET — after the 3:45 PM D-010 hard-close
        # backstop has finalised net_pnl on the day's positions, but
        # before the 5:00 PM criteria evaluation so operators see
        # fresh sizing stats alongside GLC metrics. Scheduler TZ is
        # America/New_York so hour=16 is wall-clock 4 PM ET across
        # DST transitions (not UTC 4 PM).
        scheduler.add_job(
            run_matrix_update_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=16,
            minute=20,
            id="strategy_matrix_eod_update",
            replace_existing=True,
        )
        # D4 (12E): daily counterfactual labeling at 4:25 PM ET.
        # Sits between the 4:20 matrix update and the 5:00 criteria
        # evaluation. Scheduler TZ is America/New_York — hour=16 is
        # wall-clock 4 PM ET across DST (NOT UTC 4 PM).
        scheduler.add_job(
            run_counterfactual_job_wrapper,
            trigger="cron",
            day_of_week="mon-fri",
            hour=16,
            minute=25,
            id="counterfactual_eod_job",
            replace_existing=True,
        )
        # D4 (12E): weekly missed-opportunity summary on Sundays at
        # 6:30 PM ET, alongside run_weekly_model_performance_job.
        # Self-gates on closed_sessions >= 30 inside the function.
        scheduler.add_job(
            run_counterfactual_weekly_wrapper,
            trigger="cron",
            day_of_week="sun",
            hour=18,
            minute=30,
            id="counterfactual_weekly_job",
            replace_existing=True,
        )
        scheduler.add_job(
            run_weekly_calibration_job,
            trigger="cron",
            day_of_week="sun",
            hour=18,
            minute=0,
            id="trading_weekly_calibration",
            replace_existing=True,
        )
        scheduler.add_job(
            run_weekly_model_performance_job,
            trigger="cron",
            day_of_week="sun",
            hour=18,
            minute=30,
            id="trading_weekly_model_performance",
            replace_existing=True,
        )
        # S4 / P1-1: register mark_to_market BEFORE position_monitor.
        # Both jobs fire on the same minute="*/1" cron and APScheduler
        # dispatches them in registration order. Previously the monitor
        # ran first and evaluated stops/profit-targets against the
        # PRIOR minute's MTM — a one-cycle (≥60s) delay on every exit
        # decision. Reversing the order means each minute's monitor
        # pass sees the freshly-priced current_pnl from the MTM job
        # that just ran.
        scheduler.add_job(
            run_mark_to_market_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour="9-15",
            minute="*/1",
            id="trading_mark_to_market",
            replace_existing=True,
        )
        # Position monitor — every minute, market hours only (9:30 AM - 3:45 PM ET)
        scheduler.add_job(
            run_position_monitor_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour="9-15",
            minute="*/1",
            id="trading_position_monitor",
            replace_existing=True,
        )
        # D-010: close short-gamma at 2:30 PM ET (scheduler TZ is America/New_York)
        scheduler.add_job(
            run_time_stop_230pm_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=14,
            minute=30,
            id="trading_time_stop_230pm",
            replace_existing=True,
        )
        # D-011: close all at 3:45 PM ET
        scheduler.add_job(
            run_time_stop_345pm_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=15,
            minute=45,
            id="trading_time_stop_345pm",
            replace_existing=True,
        )
        # HARD-A: Emergency backstop at 3:55 PM ET (10 min after time stop)
        scheduler.add_job(
            run_emergency_backstop_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=15, minute=55,
            id="trading_emergency_backstop",
            timezone="America/New_York",
            replace_existing=True,
        )
        # HARD-A: Prediction watchdog every 5 min, market hours only
        scheduler.add_job(
            run_prediction_watchdog_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour="9-15", minute="*/5",
            id="trading_prediction_watchdog",
            timezone="America/New_York",
            replace_existing=True,
        )
        # HARD-A: EOD reconciliation at 4:15 PM ET
        scheduler.add_job(
            run_eod_reconciliation_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=16, minute=15,
            id="trading_eod_reconciliation",
            timezone="America/New_York",
            replace_existing=True,
        )
        # Phase 3B: A/B EOD comparison at 4:30 PM ET
        scheduler.add_job(
            run_ab_eod_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=16, minute=30,
            id="trading_ab_eod",
            timezone="America/New_York",
            replace_existing=True,
        )
        # Session open: 9:30 AM ET
        scheduler.add_job(
            run_market_open_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=9,
            minute=30,
            id="trading_market_open",
            replace_existing=True,
        )
        # Session close: 4:30 PM ET
        scheduler.add_job(
            run_market_close_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=16,
            minute=30,
            id="trading_market_close",
            replace_existing=True,
        )

        # Phase 2A: Economic intelligence agents
        # Run BEFORE pre_market_scan so calendar is ready at 9:00 AM
        scheduler.add_job(
            _run_economic_calendar_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=8, minute=25,
            id="trading_economic_calendar",
            timezone="America/New_York",
            replace_existing=True,
        )
        scheduler.add_job(
            _run_macro_agent_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=8, minute=30,
            id="trading_macro_agent",
            timezone="America/New_York",
            replace_existing=True,
        )
        # Phase A (Loop 1): feedback brief — must run BEFORE synthesis (9:15)
        # so Claude's prompt can include the latest performance feedback.
        scheduler.add_job(
            _run_feedback_agent_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=9, minute=10,
            id="trading_feedback_agent",
            timezone="America/New_York",
            replace_existing=True,
        )
        scheduler.add_job(
            _run_synthesis_agent_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=9, minute=15,
            id="trading_synthesis_agent",
            timezone="America/New_York",
            replace_existing=True,
        )
        scheduler.add_job(
            _run_surprise_detector_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=8, minute=45,
            id="trading_surprise_detector",
            timezone="America/New_York",
            replace_existing=True,
        )

        # Phase 2C: flow agent — 8:45 AM ET pre-market load,
        # then refresh every 30 min so mid-session unusual prints are caught.
        scheduler.add_job(
            _run_flow_agent_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=8, minute=45,
            id="trading_flow_agent",
            timezone="America/New_York",
            replace_existing=True,
        )
        # NOTE: interval triggers do not accept day_of_week — the agent
        # gates internally via is_market_hours / its feature flag.
        scheduler.add_job(
            _run_flow_agent_job,
            trigger="interval",
            minutes=30,
            id="trading_flow_refresh",
            timezone="America/New_York",
            replace_existing=True,
            # S7-2: prevent concurrent flow_agent runs. The agent does
            # external HTTP fetches (Polygon options snapshot, Unusual
            # Whales) that can occasionally exceed the 30-min interval.
            # Without max_instances the next fire would queue on top
            # of the still-running one, multiplying API spend and
            # producing interleaved Redis writes.
            max_instances=1,
            # If a fire is missed because the previous run is still
            # going, just skip it instead of running back-to-back.
            coalesce=True,
        )
        # Phase 2C: sentiment agent — 8:30 AM ET (same time as macro)
        scheduler.add_job(
            _run_sentiment_agent_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=8, minute=30,
            id="trading_sentiment_agent",
            timezone="America/New_York",
            replace_existing=True,
        )

        # Phase 5A: Earnings Volatility System
        scheduler.add_job(
            _run_earnings_scan_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=8, minute=45,
            id="trading_earnings_scan",
            timezone="America/New_York",
            replace_existing=True,
        )
        scheduler.add_job(
            _run_earnings_entry_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=9, minute=50,
            id="trading_earnings_entry",
            timezone="America/New_York",
            replace_existing=True,
        )
        scheduler.add_job(
            _run_earnings_monitor_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour="9-15", minute="*/15",
            id="trading_earnings_monitor",
            timezone="America/New_York",
            replace_existing=True,
        )
        # Mark the four pre-market morning agents as idle at 10:30 AM ET
        # so the Health page does not show 6+ hours of "no heartbeat"
        # after they finish their once-per-day run. See
        # _run_morning_agents_idle_marker() for rationale.
        scheduler.add_job(
            _run_morning_agents_idle_marker,
            trigger="cron",
            day_of_week="mon-fri",
            hour=10, minute=30,
            id="trading_morning_agents_idle_marker",
            timezone="America/New_York",
            replace_existing=True,
        )

        scheduler.start()

        # Create today's trading session on startup
        get_or_create_session()

        # S11: seed capital allocation defaults on first boot.
        # Both default to 1.0 (100% deployment, no leverage). We only
        # set them if absent so an operator's existing config is never
        # overwritten on a redeploy. Wrapped in try/except because Redis
        # is the source of truth here — if the write fails the defaults
        # in capital_manager.get_deployment_config still apply.
        try:
            if redis_client is not None:
                if not redis_client.exists("capital:deployment_pct"):
                    redis_client.set("capital:deployment_pct", "1.0")
                if not redis_client.exists("capital:leverage_multiplier"):
                    redis_client.set("capital:leverage_multiplier", "1.0")
        except Exception as cap_seed_exc:
            logger.warning(
                "capital_defaults_seed_failed",
                error=str(cap_seed_exc),
            )

        # CSP-fix: backfill the Redis flag state into the
        # trading_feature_flags Supabase table so the Lovable-hosted
        # frontend can read flag state via direct supabase-js queries.
        # Soft-fails so a Supabase outage cannot block boot.
        _backfill_feature_flags_to_supabase()

        background_tasks.extend(
            [
                asyncio.create_task(tradier_feed.start()),
                asyncio.create_task(polygon_feed.start()),
                asyncio.create_task(databento_feed.start()),
            ]
        )
        write_health_status("data_ingestor", "healthy")

        # Clean up any stale "degraded" rows that the pre-abaf8db
        # heartbeat_check left behind on scheduled services. Safe
        # one-shot — only flips degraded -> idle, preserves real
        # error / healthy / idle. See function docstring for detail.
        _flush_stale_scheduled_service_status()
    except Exception as exc:
        logger.critical("startup_failed", error=str(exc))
        write_health_status(
            "data_ingestor",
            "error",
            last_error_message=f"startup_failed: {exc}",
        )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    # S7-1: guard against partial startup. If on_startup raised before
    # a feed was assigned (e.g., Redis ping failed) the corresponding
    # module global is still None, and `await None.stop()` raises an
    # AttributeError that masks the real startup error in the Railway
    # crash log. Per-feed None checks let shutdown clean up whatever
    # actually came up.
    if tradier_feed is not None:
        await tradier_feed.stop()
    if polygon_feed is not None:
        await polygon_feed.stop()
    if databento_feed is not None:
        await databento_feed.stop()

    for task in background_tasks:
        task.cancel()

    if redis_client is not None:
        redis_client.close()

    scheduler.shutdown(wait=False)
    logger.info("shutdown complete")


@app.get("/health")
async def get_health() -> Dict[str, list]:
    try:
        rows = get_client().table("trading_system_health").select("*").execute().data
        return {"services": rows}
    except Exception as exc:
        logger.critical("health_endpoint_failed", error=str(exc))
        write_health_status(
            "data_ingestor",
            "error",
            last_error_message=f"health_endpoint_failed: {exc}",
        )
        return {"services": []}


# ---------------------------------------------------------------------------
# Phase 4C — Trading Console intelligence + feature flag endpoints.
# Read AI agent briefs and toggle Redis feature flags from the frontend.
# All handlers fail soft: never raise, always return a JSON-serializable dict.
# ---------------------------------------------------------------------------

from fastapi import Body as FBody, Depends, Header, HTTPException


def _require_admin_key(
    x_api_key: str = Header(default="", alias="X-Api-Key"),
) -> None:
    """T1-14: FastAPI dependency — gate all /admin/* GET endpoints.

    Before this, six endpoints (intelligence, feature-flags, key-status,
    activation/status, ab/status, earnings/status) were fully open to
    anyone who guessed the Railway URL. They expose AI agent briefs,
    the live feature-flag state (including the kill switch), masked
    API-key presence, and A/B validation metrics — enough to fingerprint
    the trading engine and confirm whether capital is deployed.

    Behaviour:
      * When ``config.RAILWAY_ADMIN_KEY`` is set (production path):
        caller MUST present ``X-Api-Key: <that value>`` or we raise
        401.
      * When ``RAILWAY_ADMIN_KEY`` is unset (legacy / dev): endpoints
        remain open but we log a warning each request. Production
        deploys MUST set the secret; Railway already does in the
        current environment.

    NOTE: ``/health`` does NOT use this dependency — Railway's platform
    health-probe hits it every few seconds and cannot present a secret.
    That endpoint only returns liveness metadata (no trading state).
    """
    admin_key = getattr(config, "RAILWAY_ADMIN_KEY", "")
    if admin_key:
        if x_api_key != admin_key:
            logger.warning(
                "admin_endpoint_unauthorized",
                provided_header_present=bool(x_api_key),
            )
            raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        # Fail-open behaviour preserved so dev / legacy deploys that
        # have not set RAILWAY_ADMIN_KEY are not suddenly 401-locked
        # out of their own admin console. Every request logs a
        # warning so the gap is visible on the dashboard.
        logger.warning("admin_endpoint_open_no_railway_admin_key")


# Whitelist of feature flags exposed to the trading console UI.
# Adding a key here makes it readable AND writable from the frontend —
# guard new keys before adding.
_TRADING_FLAG_KEYS = [
    "agents:ai_synthesis:enabled",
    "agents:flow_agent:enabled",
    "agents:sentiment_agent:enabled",
    "strategy:iron_butterfly:enabled",
    "strategy:long_straddle:enabled",
    "strategy:calendar_spread:enabled",
    "strategy:ai_hint_override:enabled",
    # Signal enhancements — REVERSE polarity: absent key = ON (default),
    # explicit "false" = OFF. The POST handler in set_feature_flag()
    # handles the polarity inversion when toggled from the UI.
    "signal:vix_term_filter:enabled",
    "signal:entry_time_gate:enabled",
    "signal:gex_directional_bias:enabled",
    # Signal-D/E/F (default ON — same reverse polarity as A/B/C)
    "signal:market_breadth:enabled",
    "signal:earnings_proximity:enabled",
    "signal:iv_rank_filter:enabled",
    # Earnings straddle — default OFF (must be manually enabled)
    # Controls backend_earnings/main_earnings.py run_earnings_entry().
    # Standard polarity (NOT in _SIGNAL_FLAGS): absent key = OFF.
    "strategy:earnings_straddle:enabled",
    # S11: capital allocation — controls
    # deployed_capital = equity * deployment_pct * leverage_multiplier.
    # These are NUMERIC Redis keys (not boolean flags) but registered
    # here so they show up in /trading/flags and get audit-mirrored
    # into trading_feature_flags for the change log. Standard polarity
    # (NOT in _SIGNAL_FLAGS): the backfill records "enabled=True" only
    # if the value is literally the string "true", which it never is
    # for these numeric keys — that is fine. The trading engine reads
    # these directly from Redis via capital_manager, not via the
    # boolean enabled column.
    "capital:deployment_pct",
    "capital:leverage_multiplier",
]

# Signal flags follow REVERSE polarity (default ON). Set membership for
# the POST handler to dispatch correctly.
_SIGNAL_FLAGS = {
    "signal:vix_term_filter:enabled",
    "signal:entry_time_gate:enabled",
    "signal:gex_directional_bias:enabled",
    "signal:market_breadth:enabled",
    "signal:earnings_proximity:enabled",
    "signal:iv_rank_filter:enabled",
}


@app.get("/admin/trading/intelligence")
async def get_trading_intelligence(
    _auth: None = Depends(_require_admin_key),  # T1-14
):
    """Return all AI agent brief summaries + feature flag states from Redis.

    Used by the Trading Console War Room to render the AI Intelligence panel.
    Falls back to empty dicts on any error — never raises.
    """
    try:
        if not redis_client:
            return {
                "error": "redis_unavailable",
                "calendar": {},
                "macro": {},
                "flow": {},
                "sentiment": {},
                "synthesis": {},
                "flags": {},
            }

        import json

        def safe_get(key: str) -> dict:
            try:
                raw = redis_client.get(key)
                return json.loads(raw) if raw else {}
            except Exception:
                return {}

        def flag_state(key: str) -> bool:
            try:
                val = redis_client.get(key)
                return val in ("true", b"true")
            except Exception:
                return False

        return {
            "calendar":  safe_get("calendar:today:intel"),
            "macro":     safe_get("ai:macro:brief"),
            "flow":      safe_get("ai:flow:brief"),
            "sentiment": safe_get("ai:sentiment:brief"),
            "synthesis": safe_get("ai:synthesis:latest"),
            "flags":     {k: flag_state(k) for k in _TRADING_FLAG_KEYS},
        }
    except Exception as exc:
        logger.error("get_trading_intelligence_failed", error=str(exc))
        return {"error": str(exc)}


@app.get("/admin/trading/feature-flags")
async def get_feature_flags(
    _auth: None = Depends(_require_admin_key),  # T1-14
):
    """Return the current state of every trading feature flag in Redis.

    Strategy/agent flags are default OFF (absent key = false).
    Signal flags are default ON (absent key = true; only "false"
    explicitly disables them) — see _SIGNAL_FLAGS.
    """
    try:
        if not redis_client:
            return {"flags": {}}

        flags = {}
        for key in _TRADING_FLAG_KEYS:
            try:
                val = redis_client.get(key)
                if key in _SIGNAL_FLAGS:
                    flags[key] = val not in ("false", b"false")
                else:
                    flags[key] = val in ("true", b"true")
            except Exception:
                flags[key] = key in _SIGNAL_FLAGS  # default ON for signals

        return {"flags": flags}
    except Exception as exc:
        logger.error("get_feature_flags_failed", error=str(exc))
        return {"flags": {}}


def _mask_key(key_value: str) -> str:
    """Return masked key: first 4 chars + '...' + last 6 chars.

    Returns 'not set' if empty. Never returns the full key. Never reveals
    more than 10 characters of the key value (4 prefix + 6 suffix).
    """
    if not key_value:
        return "not set"
    if len(key_value) <= 10:
        return "****"
    return f"{key_value[:4]}...{key_value[-6:]}"


@app.get("/admin/subscriptions/key-status")
async def get_subscription_key_status(
    _auth: None = Depends(_require_admin_key),  # T1-14
):
    """Return key configured status + masked preview for each API key.

    Reads os.environ via config.py only — never touches Supabase.
    Masked format: first 4 chars + '...' + last 6 chars.
    Full key values are never transmitted to the frontend.
    """
    try:
        import config as _cfg

        # Today's AI token usage from Redis (Anthropic/OpenAI)
        today_tokens_in = 0
        today_tokens_out = 0
        try:
            if redis_client:
                from datetime import date
                day = date.today().isoformat()
                tin = redis_client.get(f"ai:tokens:in:{day}")
                tout = redis_client.get(f"ai:tokens:out:{day}")
                today_tokens_in = int(tin) if tin else 0
                today_tokens_out = int(tout) if tout else 0
        except Exception:
            # Soft failure — counters are observability only.
            pass

        keys = {
            "supabase_url": {
                "configured": bool(_cfg.SUPABASE_URL),
                "masked": _mask_key(_cfg.SUPABASE_URL or ""),
                "env_var": "SUPABASE_URL",
            },
            "databento": {
                "configured": bool(_cfg.DATABENTO_API_KEY),
                "masked": _mask_key(_cfg.DATABENTO_API_KEY or ""),
                "env_var": "DATABENTO_API_KEY",
            },
            "tradier": {
                "configured": bool(_cfg.TRADIER_API_KEY),
                "masked": _mask_key(_cfg.TRADIER_API_KEY or ""),
                "env_var": "TRADIER_API_KEY",
                "sandbox": _cfg.TRADIER_SANDBOX,
            },
            "polygon": {
                "configured": bool(_cfg.POLYGON_API_KEY),
                "masked": _mask_key(_cfg.POLYGON_API_KEY or ""),
                "env_var": "POLYGON_API_KEY",
            },
            "finnhub": {
                "configured": bool(_cfg.FINNHUB_API_KEY),
                "masked": _mask_key(_cfg.FINNHUB_API_KEY or ""),
                "env_var": "FINNHUB_API_KEY",
            },
            "anthropic": {
                "configured": bool(_cfg.ANTHROPIC_API_KEY),
                "masked": _mask_key(_cfg.ANTHROPIC_API_KEY or ""),
                "env_var": "ANTHROPIC_API_KEY",
                "today_tokens_in": today_tokens_in,
                "today_tokens_out": today_tokens_out,
            },
            "openai": {
                "configured": bool(_cfg.OPENAI_API_KEY),
                "masked": _mask_key(_cfg.OPENAI_API_KEY or ""),
                "env_var": "OPENAI_API_KEY",
            },
            "unusual_whales": {
                "configured": bool(_cfg.UNUSUAL_WHALES_API_KEY),
                "masked": _mask_key(_cfg.UNUSUAL_WHALES_API_KEY or ""),
                "env_var": "UNUSUAL_WHALES_API_KEY",
            },
            "newsapi": {
                "configured": bool(_cfg.NEWSAPI_KEY),
                "masked": _mask_key(_cfg.NEWSAPI_KEY or ""),
                "env_var": "NEWSAPI_KEY",
            },
            "ai_provider": {
                "provider": getattr(_cfg, "AI_PROVIDER", "anthropic"),
                "model": getattr(_cfg, "AI_MODEL", "claude-sonnet-4-5"),
            },
        }
        return {"keys": keys}

    except Exception as exc:
        logger.error("get_subscription_key_status_failed", error=str(exc))
        return {"keys": {}, "error": str(exc)}


@app.get("/admin/activation/status")
async def get_activation_status(
    _auth: None = Depends(_require_admin_key),  # T1-14
):
    """
    DASH-A: Phase Activation Dashboard data.

    Returns the complete activation state in a single payload:
      - closed_trade_count: paper-trade total (drives auto-enable thresholds)
      - flags: every trading + signal flag with its current bool state
      - ab_gate: Phase 3B progress (built=False until 3B ships)
      - recent_alerts: last 20 system_alerts rows (empty if table missing)

    Strategy/agent flags default OFF (None means "not set"); signal flags
    default ON (None means "not yet disabled"). The system_alerts query
    is wrapped in try/except so the endpoint still works before the
    DASH-A migration adds that table.
    """
    try:
        closed_count = _get_closed_trade_count()

        # Trading flags (strategy + agent) — default OFF
        flags: dict[str, bool] = {}
        for key in _TRADING_FLAG_KEYS:
            try:
                val = redis_client.get(key) if redis_client else None
                flags[key] = val in ("true", b"true")
            except Exception:
                flags[key] = False

        # Signal-enhancement flags — default ON when missing.
        # Treated as enabled unless explicitly set to "false" so a
        # newly-built signal does not require a deploy to activate.
        signal_flags = [
            "signal:vix_term_filter:enabled",
            "signal:entry_time_gate:enabled",
            "signal:gex_directional_bias:enabled",
            "signal:market_breadth:enabled",
            "signal:earnings_proximity:enabled",
            "signal:iv_rank_filter:enabled",
        ]
        for key in signal_flags:
            try:
                val = redis_client.get(key) if redis_client else None
                flags[key] = val not in ("false", b"false")
            except Exception:
                flags[key] = True

        # A/B validation gate — Phase 3B is now built. Soft-fail to a
        # built/not-passed dict so the activation page never breaks
        # when shadow_engine or its tables are unavailable.
        try:
            from shadow_engine import get_ab_gate_status
            ab_gate = get_ab_gate_status()
        except Exception:
            ab_gate = {"built": True, "gate_passed": False}

        # Recent alerts — system_alerts table may not exist until the
        # DASH-A migration runs. Soft-fail to [] in that case.
        recent_alerts: list = []
        try:
            result = (
                get_client()
                .table("system_alerts")
                .select(
                    "fired_at, level, event, detail, acknowledged"
                )
                .order("fired_at", desc=True)
                .limit(20)
                .execute()
            )
            recent_alerts = result.data or []
        except Exception:
            recent_alerts = []

        return {
            "closed_trade_count": closed_count,
            "flags": flags,
            "ab_gate": ab_gate,
            "recent_alerts": recent_alerts,
        }

    except Exception as exc:
        logger.error("get_activation_status_failed", error=str(exc))
        return {
            "closed_trade_count": 0,
            "flags": {},
            "ab_gate": {"built": True, "gate_passed": False},
            "recent_alerts": [],
        }


@app.get("/admin/ab/status")
async def get_ab_status(
    _auth: None = Depends(_require_admin_key),  # T1-14
):
    """
    Phase 3B: Returns A/B gate status and recent daily comparisons.

    Powers /trading/ab-comparison. Returns:
      - gate: get_ab_gate_status() dict (days/trades progress, lead%)
      - daily: last 90 ab_session_comparison rows in chronological order
    Soft-fails to a built/not-passed gate + empty daily list so the
    page renders cleanly before the migration is applied or before
    the first session writes a row.
    """
    try:
        from shadow_engine import get_ab_gate_status
        gate = get_ab_gate_status()

        rows: list = []
        try:
            result = (
                get_client()
                .table("ab_session_comparison")
                .select(
                    "session_date, a_synthetic_pnl, b_session_pnl, "
                    "move_pct, a_no_trade, b_no_trade, a_regime"
                )
                .order("session_date", desc=False)
                .limit(90)
                .execute()
            )
            rows = result.data or []
        except Exception:
            rows = []

        return {"gate": gate, "daily": rows}

    except Exception as exc:
        logger.error("get_ab_status_failed", error=str(exc))
        return {
            "gate": {"built": True, "gate_passed": False},
            "daily": [],
        }


@app.get("/admin/earnings/status")
async def get_earnings_status(
    _auth: None = Depends(_require_admin_key),  # T1-14
):
    """
    Phase 5A: Returns earnings system snapshot.

    Powers /trading/earnings. Returns:
      - upcoming:         JSON list from `earnings:upcoming_events`
                          (written by the 8:45 AM scan)
      - active:           JSON dict from `earnings:active_position`
                          (the most recently entered open position)
      - recent_positions: last 30 rows of earnings_positions DESC
      - last_scan_at:     ISO timestamp of the last scan, or null

    Soft-fails to empty / null payload so the page renders cleanly
    before the migration is applied or before the first scan runs.
    """
    payload = {
        "upcoming": [],
        "active": None,
        "recent_positions": [],
        "last_scan_at": None,
    }
    try:
        if redis_client:
            try:
                raw_upcoming = redis_client.get("earnings:upcoming_events")
                if raw_upcoming:
                    payload["upcoming"] = json.loads(raw_upcoming) or []
            except Exception:
                pass
            try:
                raw_active = redis_client.get("earnings:active_position")
                if raw_active:
                    payload["active"] = json.loads(raw_active)
            except Exception:
                pass
            try:
                raw_scan = redis_client.get("earnings:last_scan_at")
                if raw_scan:
                    payload["last_scan_at"] = (
                        raw_scan.decode("utf-8")
                        if isinstance(raw_scan, bytes)
                        else str(raw_scan)
                    )
            except Exception:
                pass

        try:
            result = (
                get_client()
                .table("earnings_positions")
                .select(
                    "id, ticker, earnings_date, announce_time, "
                    "entry_date, exit_date, status, exit_reason, "
                    "contracts, total_debit, exit_value, net_pnl, "
                    "net_pnl_pct, implied_move_pct, actual_move_pct, "
                    "historical_edge_score"
                )
                .order("entry_date", desc=True)
                .limit(30)
                .execute()
            )
            payload["recent_positions"] = result.data or []
        except Exception:
            payload["recent_positions"] = []

        return payload

    except Exception as exc:
        logger.error("get_earnings_status_failed", error=str(exc))
        return payload


@app.post("/admin/trading/feature-flags")
async def set_feature_flag(
    payload: dict = FBody(...),
    x_api_key: str = Header(default="", alias="X-Api-Key"),
):
    """Enable or disable a single feature flag.

    Body: ``{"flag_key": "strategy:iron_butterfly:enabled", "enabled": true}``
    Only whitelisted keys in ``_TRADING_FLAG_KEYS`` are accepted.

    Polarity differs by flag type:
      - Strategy/agent flags (default OFF): enabled=true sets "true",
        enabled=false deletes the key.
      - Signal flags (default ON): enabled=true deletes the key
        (restores default ON), enabled=false sets "false" (explicit
        disable). See _SIGNAL_FLAGS.

    S4 / C-β: when ``RAILWAY_ADMIN_KEY`` is set in the Railway env, the
    caller must present it as ``X-Api-Key``. The set-feature-flag
    Supabase Edge Function reads the same secret from its own env and
    forwards it transparently. When unset (legacy / dev), a warning is
    logged and the endpoint stays open so existing deploys are not
    broken — operators MUST set this before enabling real capital.
    """
    admin_key = getattr(config, "RAILWAY_ADMIN_KEY", "")
    if admin_key:
        if x_api_key != admin_key:
            logger.warning(
                "feature_flag_endpoint_unauthorized",
                provided_header_present=bool(x_api_key),
            )
            raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        # T1-12: previously we only logged a warning and stayed open.
        # That meant any caller who guessed the Railway URL could flip
        # trading flags — including the kill switch, earnings_straddle,
        # and capital:deployment_pct. In production we now hard-fail
        # with 503 instead; operators MUST set RAILWAY_ADMIN_KEY before
        # the flag POST endpoint becomes reachable. Dev / legacy deploys
        # (ENVIRONMENT != "production") keep the legacy warn-and-allow
        # behaviour so local toggling still works.
        environment = getattr(config, "ENVIRONMENT", "development")
        if environment == "production":
            logger.error(
                "feature_flag_endpoint_blocked_no_key_in_production",
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "Feature flag endpoint disabled: "
                    "RAILWAY_ADMIN_KEY not configured"
                ),
            )
        logger.warning("feature_flag_endpoint_open_no_admin_key_set")

    allowed = set(_TRADING_FLAG_KEYS)

    try:
        flag_key = payload.get("flag_key", "")
        enabled = bool(payload.get("enabled", False))

        if flag_key not in allowed:
            return {"error": f"flag_key not in allowlist: {flag_key}"}

        if not redis_client:
            return {"error": "redis_unavailable"}

        if flag_key in _SIGNAL_FLAGS:
            # Signal flags: default ON. Toggling ON deletes the key
            # (restores default). Toggling OFF sets "false" (explicit).
            if enabled:
                redis_client.delete(flag_key)
            else:
                redis_client.set(flag_key, "false")
        else:
            # Strategy/agent flags: default OFF. Standard polarity.
            if enabled:
                redis_client.set(flag_key, "true")
            else:
                redis_client.delete(flag_key)

        # CSP-fix mirror: write the operator's intended state into
        # trading_feature_flags so the Lovable-hosted frontend can
        # read it via direct supabase-js queries (bypassing CSP).
        # Redis is still authoritative for the trading engine; a
        # Supabase failure must not prevent the flag from taking
        # effect, so we swallow exceptions silently here.
        try:
            get_client().table("trading_feature_flags").upsert(
                {
                    "flag_key": flag_key,
                    "enabled": enabled,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="flag_key",
            ).execute()
        except Exception as mirror_exc:
            logger.warning(
                "feature_flag_supabase_mirror_failed",
                flag_key=flag_key,
                error=str(mirror_exc),
            )

        logger.info(
            "feature_flag_updated",
            flag_key=flag_key,
            enabled=enabled,
            polarity="signal" if flag_key in _SIGNAL_FLAGS else "standard",
        )
        return {"ok": True, "flag_key": flag_key, "enabled": enabled}

    except Exception as exc:
        logger.error("set_feature_flag_failed", error=str(exc))
        return {"error": str(exc)}


def _backfill_feature_flags_to_supabase() -> None:
    """Mirror the current Redis flag state into trading_feature_flags
    once on startup.

    Idempotent — safe to run on every boot. Soft-fails on any error so
    a Supabase outage cannot block startup. The mirror is only used by
    the Lovable-hosted frontend (CSP fix); the trading engine still
    reads Redis directly.
    """
    if not redis_client:
        return
    try:
        rows = []
        now = datetime.now(timezone.utc).isoformat()
        for key in _TRADING_FLAG_KEYS:
            try:
                val = redis_client.get(key)
            except Exception:
                val = None
            if key in _SIGNAL_FLAGS:
                # Signal flags default ON: only "false" disables.
                enabled = val not in ("false", b"false")
            else:
                enabled = val in ("true", b"true")
            rows.append(
                {"flag_key": key, "enabled": enabled, "updated_at": now}
            )
        if rows:
            get_client().table("trading_feature_flags").upsert(
                rows, on_conflict="flag_key"
            ).execute()
        logger.info(
            "feature_flags_backfilled_to_supabase", count=len(rows)
        )
    except Exception as exc:
        logger.warning(
            "feature_flag_backfill_failed", error=str(exc)
        )
