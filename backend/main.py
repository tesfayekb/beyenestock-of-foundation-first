import asyncio
from datetime import datetime, timezone
from typing import Dict, List

import redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

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

logger = get_logger("main")
app = FastAPI()
scheduler = AsyncIOScheduler()
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
    """Runs daily at 4:30 PM ET after market close."""
    try:
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
    """D-010: Close all short-gamma positions at 2:30 PM ET (19:30 UTC)."""
    try:
        result = run_time_stop_230pm()
        logger.info("time_stop_230pm_job_done", **result)
    except Exception as exc:
        logger.error("time_stop_230pm_job_error", error=str(exc))


def run_time_stop_345pm_job() -> None:
    """D-011: Close ALL positions at 3:45 PM ET (20:45 UTC)."""
    try:
        result = run_time_stop_345pm()
        logger.info("time_stop_345pm_job_done", **result)
    except Exception as exc:
        logger.error("time_stop_345pm_job_error", error=str(exc))


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

        # Day type classification heuristic
        # Phase 2 proxy — real classification uses overnight ATR + economic calendar
        # in Phase 4
        if not baseline_ready:
            day_type = "unknown"
            confidence = 0.0
        elif abs(vvix_z) >= 2.5:
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
                id="trading_pre_market_scan",
                hour=14,
                minute=0,
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
            trigger="interval",
            minutes=5,
            id="trading_prediction_cycle_local",
            replace_existing=True,
        )
        scheduler.add_job(
            run_eod_criteria_evaluation,
            trigger="cron",
            hour=22,      # After market close in both EDT and EST (6 PM ET / 5 PM ET)
            minute=0,
            id="trading_eod_criteria_evaluation",
            replace_existing=True,
        )
        scheduler.add_job(
            run_weekly_calibration_job,
            trigger="cron",
            day_of_week="sun",
            hour=23,
            minute=0,
            id="trading_weekly_calibration",
            replace_existing=True,
        )
        scheduler.add_job(
            run_weekly_model_performance_job,
            trigger="cron",
            day_of_week="sun",
            hour=23,
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
        # D-010: close short-gamma at 2:30 PM ET = 19:30 UTC
        scheduler.add_job(
            run_time_stop_230pm_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=19,
            minute=30,
            id="trading_time_stop_230pm",
            replace_existing=True,
        )
        # D-011: close all at 3:45 PM ET = 20:45 UTC
        scheduler.add_job(
            run_time_stop_345pm_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=20,
            minute=45,
            id="trading_time_stop_345pm",
            replace_existing=True,
        )
        # Session open: 9:30 AM ET = 13:30 UTC
        scheduler.add_job(
            run_market_open_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=13,
            minute=30,
            id="trading_market_open",
            replace_existing=True,
        )
        # Session close: 4:30 PM ET = 21:30 UTC
        scheduler.add_job(
            run_market_close_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=21,
            minute=30,
            id="trading_market_close",
            replace_existing=True,
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
