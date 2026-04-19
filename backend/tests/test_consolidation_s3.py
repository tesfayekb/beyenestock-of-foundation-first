"""
Consolidation Session 3 tests — reliability fixes.

Coverage:
    C-3 polygon_feed health writes 'polygon_feed' (not 'data_ingestor')
    C-4 strategy:long_straddle:enabled flag enforcement
    C-5 logged warnings on Supabase mirror failures (3 agents)
    C-8 every scheduler entry has replace_existing=True

These are static-source tests (no Redis / no live Supabase) so they
run cleanly inside the existing pytest suite without infrastructure.
"""

from __future__ import annotations

import ast
import os
import re

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


# ── C-3: polygon_feed service name ───────────────────────────────────────────

def test_polygon_feed_heartbeat_uses_correct_service_name():
    """_heartbeat_loop must write 'polygon_feed' not 'data_ingestor'."""
    path = os.path.join(REPO_ROOT, "backend", "polygon_feed.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    # No write_health_status call may pass 'data_ingestor' as the
    # first positional argument anywhere in polygon_feed.py.
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "write_health_status":
                if node.args:
                    first_arg = node.args[0]
                    if isinstance(first_arg, ast.Constant):
                        assert first_arg.value != "data_ingestor", (
                            "polygon_feed still writes to data_ingestor "
                            "service name"
                        )

    # Positive assertion: the correct service name must appear.
    assert "polygon_feed" in src


# ── C-4: long_straddle flag enforcement ──────────────────────────────────────

def test_long_straddle_flag_off_returns_false():
    """When strategy:long_straddle:enabled=false, the gate returns False."""
    from unittest.mock import MagicMock
    from strategy_selector import StrategySelector

    sel = StrategySelector.__new__(StrategySelector)
    redis = MagicMock()

    def mock_get(key):
        if key == "strategy:long_straddle:enabled":
            return b"false"
        return None

    redis.get.side_effect = mock_get
    sel.redis_client = redis

    result = sel._check_feature_flag(
        "strategy:long_straddle:enabled", default=False
    )
    assert result is False


def test_long_straddle_flag_on_returns_true():
    """When strategy:long_straddle:enabled=true, the gate returns True."""
    from unittest.mock import MagicMock
    from strategy_selector import StrategySelector

    sel = StrategySelector.__new__(StrategySelector)
    redis = MagicMock()
    redis.get.return_value = b"true"
    sel.redis_client = redis

    result = sel._check_feature_flag(
        "strategy:long_straddle:enabled", default=False
    )
    assert result is True


def test_strategy_selector_calendar_branch_checks_long_straddle_flag():
    """
    The calendar-spread-too-early fallback must consult the
    long_straddle flag before selecting the straddle. Static check —
    confirms the C-4 wiring is present and didn't drift.
    """
    path = os.path.join(REPO_ROOT, "backend", "strategy_selector.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    assert "_straddle_allowed" in src, (
        "long_straddle flag check missing from strategy_selector.py"
    )
    assert 'strategy:long_straddle:enabled' in src, (
        "strategy:long_straddle:enabled key missing from selector"
    )


# ── C-5: agent mirror logging ────────────────────────────────────────────────

def test_macro_agent_mirror_except_has_logging():
    """bare except around Supabase mirror must log, not silently pass."""
    path = os.path.join(REPO_ROOT, "backend_agents", "macro_agent.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "macro_agent_supabase_mirror_failed" in src, (
        "macro_agent bare except must log macro_agent_supabase_mirror_failed"
    )


def test_flow_agent_mirror_except_has_logging():
    path = os.path.join(REPO_ROOT, "backend_agents", "flow_agent.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "flow_agent_supabase_mirror_failed" in src, (
        "flow_agent bare except must log flow_agent_supabase_mirror_failed"
    )


def test_sentiment_agent_mirror_except_has_logging():
    path = os.path.join(REPO_ROOT, "backend_agents", "sentiment_agent.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "sentiment_agent_supabase_mirror_failed" in src, (
        "sentiment_agent bare except must log "
        "sentiment_agent_supabase_mirror_failed"
    )


# ── C-8: scheduler guards ────────────────────────────────────────────────────

def test_scheduler_entries_have_replace_existing():
    """Every scheduler.add_job entry must include replace_existing=True."""
    path = os.path.join(REPO_ROOT, "backend", "main.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    blocks = re.findall(
        r'scheduler\.add_job\(.*?replace_existing',
        src, re.DOTALL,
    )
    total = src.count('scheduler.add_job(')
    assert len(blocks) == total, (
        f"{total - len(blocks)} scheduler entries missing "
        f"replace_existing=True (total add_job calls: {total})"
    )


def test_agent_jobs_have_day_of_week_guard():
    """
    Every agent / earnings cron job that runs at a fixed hour must
    have day_of_week='mon-fri' so it never fires on weekends.

    These IDs were the ones flagged by the C-8 audit. Interval triggers
    are excluded because APScheduler IntervalTrigger does not accept
    day_of_week — the agent gates internally by market-hour checks.
    """
    path = os.path.join(REPO_ROOT, "backend", "main.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    weekday_required_ids = [
        "trading_economic_calendar",
        "trading_macro_agent",
        "trading_feedback_agent",
        "trading_synthesis_agent",
        "trading_surprise_detector",
        "trading_flow_agent",
        "trading_sentiment_agent",
        "trading_earnings_scan",
        "trading_earnings_entry",
        "trading_earnings_monitor",
        "trading_emergency_backstop",
        "trading_prediction_watchdog",
        "trading_eod_reconciliation",
        "trading_ab_eod",
        "trading_eod_criteria_evaluation",
        "trading_gex_computation",
    ]

    for job_id in weekday_required_ids:
        # Match the surrounding add_job(...) block — start at
        # 'scheduler.add_job(' and stop at the next ')' that closes
        # the call (line containing only whitespace + ')').
        pattern = (
            r'scheduler\.add_job\([^)]*?'
            rf'id="{re.escape(job_id)}"'
            r'[^)]*?\)'
        )
        match = re.search(pattern, src, re.DOTALL)
        assert match, f"add_job block for id={job_id!r} not found"
        block = match.group(0)
        assert 'day_of_week="mon-fri"' in block, (
            f"add_job id={job_id!r} missing day_of_week='mon-fri' guard"
        )
