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
    """Runs every 5 minutes. Full prediction -> strategy -> execution cycle."""
    result = run_trading_cycle(account_value=100_000.0, sizing_phase=1)
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

    try:
        # Step 2: Evaluate criteria (GLC-001/002 now have labeled data)
        summary = run_criteria_evaluation()
        logger.info("eod_criteria_evaluation_done", **summary)
    except Exception as exc:
        logger.error("eod_criteria_evaluation_error", error=str(exc))


def run_weekly_calibration_job() -> None:
    """Runs every Sunday at 6 PM ET (23:00 UTC)."""
    try:
        summary = run_weekly_calibration()
        logger.info("weekly_calibration_job_done", **summary)
    except Exception as exc:
        logger.error("weekly_calibration_job_error", error=str(exc))


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
    """Runs every minute during market hours — prices open positions."""
    try:
        if redis_client is None:
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
        sys.path.insert(
            0,
            os.path.join(os.path.dirname(__file__), "..", "backend_agents"),
        )
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
    Pre-market regime and day_type classification. Runs at 9:00 AM ET (14:00 UTC).
    Classifies today's session as: trend, open_drive, range, reversal, event, unknown.
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
        sys.path.insert(
            0,
            os.path.join(os.path.dirname(__file__), "..", "backend_agents"),
        )
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
    try:
        rows = (
            get_client()
            .table("trading_system_health")
            .select("service_name,last_heartbeat_at")
            .execute()
            .data
        )
        now = datetime.now(timezone.utc)
        for row in rows:
            heartbeat = datetime.fromisoformat(
                row["last_heartbeat_at"].replace("Z", "+00:00")
            )
            if (now - heartbeat).total_seconds() > 90:
                write_health_status(
                    row["service_name"],
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
                id="trading_gex_computation",
                minute="*/5",
            )
        if "trading_heartbeat_check" in jobs:
            scheduler.add_job(
                heartbeat_check,
                trigger="interval",
                id="trading_heartbeat_check",
                seconds=60,
            )
        if "trading_pre_market_scan" in jobs:
            scheduler.add_job(
                pre_market_scan,
                trigger="cron",
                day_of_week="mon-fri",
                hour=9,
                minute=0,
                id="trading_pre_market_scan",
                replace_existing=True,
            )
        scheduler.add_job(
            gex_heartbeat_keepalive,
            trigger="interval",
            id="gex_heartbeat_keepalive",
            seconds=30,
        )
        scheduler.add_job(
            prediction_engine_keepalive,
            trigger="interval",
            seconds=30,
            id="prediction_engine_keepalive",
        )
        scheduler.add_job(
            strategy_selector_keepalive,
            trigger="interval",
            seconds=30,
            id="strategy_selector_keepalive",
        )
        scheduler.add_job(
            risk_engine_keepalive,
            trigger="interval",
            seconds=30,
            id="risk_engine_keepalive",
        )
        scheduler.add_job(
            execution_engine_keepalive,
            trigger="interval",
            seconds=30,
            id="execution_engine_keepalive",
        )
        scheduler.add_job(
            run_prediction_cycle,
            trigger="cron",
            day_of_week="mon-fri",
            hour="9-15",
            minute="*/5",
            id="trading_prediction_cycle_local",
            replace_existing=True,
        )
        scheduler.add_job(
            run_eod_criteria_evaluation,
            trigger="cron",
            hour=17,
            minute=0,
            id="trading_eod_criteria_evaluation",
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
        # Mark-to-market — every minute, market hours (prices open positions)
        scheduler.add_job(
            run_mark_to_market_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour="9-15",
            minute="*/1",
            id="trading_mark_to_market",
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
            hour=15, minute=55,
            id="trading_emergency_backstop",
            timezone="America/New_York",
            replace_existing=True,
        )
        # HARD-A: Prediction watchdog every 5 min, market hours only
        scheduler.add_job(
            run_prediction_watchdog_job,
            trigger="cron",
            hour="9-15", minute="*/5",
            id="trading_prediction_watchdog",
            timezone="America/New_York",
            replace_existing=True,
        )
        # HARD-A: EOD reconciliation at 4:15 PM ET
        scheduler.add_job(
            run_eod_reconciliation_job,
            trigger="cron",
            hour=16, minute=15,
            id="trading_eod_reconciliation",
            timezone="America/New_York",
            replace_existing=True,
        )
        # Phase 3B: A/B EOD comparison at 4:30 PM ET
        scheduler.add_job(
            run_ab_eod_job,
            trigger="cron",
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
            hour=8, minute=25,
            id="trading_economic_calendar",
            timezone="America/New_York",
        )
        scheduler.add_job(
            _run_macro_agent_job,
            trigger="cron",
            hour=8, minute=30,
            id="trading_macro_agent",
            timezone="America/New_York",
        )
        # Phase A (Loop 1): feedback brief — must run BEFORE synthesis (9:15)
        # so Claude's prompt can include the latest performance feedback.
        scheduler.add_job(
            _run_feedback_agent_job,
            trigger="cron",
            hour=9, minute=10,
            id="trading_feedback_agent",
            timezone="America/New_York",
        )
        scheduler.add_job(
            _run_synthesis_agent_job,
            trigger="cron",
            hour=9, minute=15,
            id="trading_synthesis_agent",
            timezone="America/New_York",
        )
        scheduler.add_job(
            _run_surprise_detector_job,
            trigger="cron",
            hour=8, minute=45,
            id="trading_surprise_detector",
            timezone="America/New_York",
        )

        # Phase 2C: flow agent — 8:45 AM ET pre-market load,
        # then refresh every 30 min so mid-session unusual prints are caught.
        scheduler.add_job(
            _run_flow_agent_job,
            trigger="cron",
            hour=8, minute=45,
            id="trading_flow_agent",
            timezone="America/New_York",
        )
        scheduler.add_job(
            _run_flow_agent_job,
            trigger="interval",
            minutes=30,
            id="trading_flow_refresh",
            timezone="America/New_York",
        )
        # Phase 2C: sentiment agent — 8:30 AM ET (same time as macro)
        scheduler.add_job(
            _run_sentiment_agent_job,
            trigger="cron",
            hour=8, minute=30,
            id="trading_sentiment_agent",
            timezone="America/New_York",
        )

        scheduler.start()

        # Create today's trading session on startup
        get_or_create_session()

        background_tasks.extend(
            [
                asyncio.create_task(tradier_feed.start()),
                asyncio.create_task(polygon_feed.start()),
                asyncio.create_task(databento_feed.start()),
            ]
        )
        write_health_status("data_ingestor", "healthy")
    except Exception as exc:
        logger.critical("startup_failed", error=str(exc))
        write_health_status(
            "data_ingestor",
            "error",
            last_error_message=f"startup_failed: {exc}",
        )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await tradier_feed.stop()
    await polygon_feed.stop()
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

from fastapi import Body as FBody

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
]


@app.get("/admin/trading/intelligence")
async def get_trading_intelligence():
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
async def get_feature_flags():
    """Return the current state of every trading feature flag in Redis."""
    try:
        if not redis_client:
            return {"flags": {}}

        flags = {}
        for key in _TRADING_FLAG_KEYS:
            try:
                val = redis_client.get(key)
                flags[key] = val in ("true", b"true")
            except Exception:
                flags[key] = False

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
async def get_subscription_key_status():
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
async def get_activation_status():
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

        # A/B validation gate — Phase 3B placeholder until built
        ab_gate = {
            "built": False,
            "days_elapsed": None,
            "days_required": 90,
            "trades_count": closed_count,
            "trades_required": 100,
            "portfolio_b_lead_pct": None,
            "gate_passed": False,
        }

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
            "ab_gate": {"built": False, "gate_passed": False},
            "recent_alerts": [],
        }


@app.post("/admin/trading/feature-flags")
async def set_feature_flag(payload: dict = FBody(...)):
    """Enable or disable a single feature flag.

    Body: ``{"flag_key": "strategy:iron_butterfly:enabled", "enabled": true}``
    Only whitelisted keys in ``_TRADING_FLAG_KEYS`` are accepted.
    Setting ``enabled=false`` deletes the key (treated as off everywhere).
    """
    allowed = set(_TRADING_FLAG_KEYS)

    try:
        flag_key = payload.get("flag_key", "")
        enabled = bool(payload.get("enabled", False))

        if flag_key not in allowed:
            return {"error": f"flag_key not in allowlist: {flag_key}"}

        if not redis_client:
            return {"error": "redis_unavailable"}

        if enabled:
            redis_client.set(flag_key, "true")
        else:
            redis_client.delete(flag_key)

        logger.info("feature_flag_updated", flag_key=flag_key, enabled=enabled)
        return {"ok": True, "flag_key": flag_key, "enabled": enabled}

    except Exception as exc:
        logger.error("set_feature_flag_failed", error=str(exc))
        return {"error": str(exc)}
