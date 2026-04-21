"""Regression guard for the health_write_failed bug (fix(infra) 2026-04-20).

The `trading_system_health` table has no `error` column — the correct
column is `last_error_message`. Before this fix, 14 call sites in
backend/main.py passed `error=str(exc)` as a kwarg, which
`write_health_status(service_name, status, **kwargs)` spread straight
into the Supabase upsert payload. Supabase rejected the row, the
agent status never flipped to 'error', and the operator had no
visibility into agent failures.

This test statically parses every Python module in `backend/` and
`backend_agents/` and asserts that no `write_health_status(...)` call
passes a kwarg named `error`. The correct error-payload kwarg is
`last_error_message`.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCAN_DIRS = [
    REPO_ROOT / "backend",
    REPO_ROOT / "backend_agents",
    REPO_ROOT / "backend_earnings",
]


def _iter_py_files():
    """Yield every .py file under the scan roots, excluding tests."""
    for root in SCAN_DIRS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            # Skip the tests directory itself — tests may legitimately
            # reference the old bug pattern in docstrings/comments
            # without actually invoking write_health_status.
            if "tests" in path.parts:
                continue
            yield path


def _iter_write_health_calls(tree: ast.AST):
    """Yield every ast.Call whose callee is the bare name
    `write_health_status` (the import style used across the codebase).
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "write_health_status":
            yield node


def test_no_write_health_status_call_uses_error_kwarg():
    """Every write_health_status() call must use last_error_message=,
    never error=. `error` is not a column on trading_system_health —
    Supabase silently rejects the upsert."""
    offenders = []
    for path in _iter_py_files():
        try:
            src = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(src, filename=str(path))
        except SyntaxError:
            continue
        for call in _iter_write_health_calls(tree):
            for kw in call.keywords:
                if kw.arg == "error":
                    rel = path.relative_to(REPO_ROOT)
                    offenders.append(f"{rel}:{call.lineno}")

    assert not offenders, (
        "Found write_health_status(..., error=...) call sites — "
        "use last_error_message= instead (no `error` column on "
        "trading_system_health):\n  "
        + "\n  ".join(offenders)
    )


def test_main_error_handlers_use_last_error_message():
    """Positive check: every `write_health_status(service, "error", ...)`
    call in backend/main.py that carries exception context must use
    `last_error_message=` (not bare positional, not `error=`).

    Guards against regression where a developer re-adds `error=` while
    refactoring an agent job wrapper.
    """
    main_py = REPO_ROOT / "backend" / "main.py"
    src = main_py.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(main_py))

    offenders = []
    for call in _iter_write_health_calls(tree):
        # Only inspect calls whose second positional arg is "error".
        if len(call.args) < 2:
            continue
        status_arg = call.args[1]
        if not (isinstance(status_arg, ast.Constant)
                and status_arg.value == "error"):
            continue
        # A call with no kwargs at all is fine (pure status ping).
        if not call.keywords:
            continue
        kw_names = {kw.arg for kw in call.keywords}
        if "error" in kw_names:
            offenders.append(
                f"backend/main.py:{call.lineno} uses error= kwarg"
            )
        # If any kwargs are present on an 'error' status and none of
        # them is last_error_message, the error payload is lost.
        if kw_names and "last_error_message" not in kw_names:
            # Allow structured diagnostics that intentionally omit the
            # message (e.g. last_error_message=None would still count).
            # Only fail when the only kwarg is the legacy `error`.
            if kw_names == {"error"}:
                offenders.append(
                    f"backend/main.py:{call.lineno} error-status "
                    f"write carries no last_error_message"
                )

    assert not offenders, (
        "Found backend/main.py error-status writes that still use "
        "the wrong kwarg:\n  " + "\n  ".join(offenders)
    )


def test_agent_job_wrappers_use_abspath_and_guard():
    """Defence-in-depth: every _run_*_agent_job / _run_*_job in
    backend/main.py that imports a module from backend_agents or
    backend_earnings must build the sys.path entry with
    os.path.abspath(...) and guard the insert with `if ... not in
    sys.path`. This is the fix from commit 3cd1c8c.
    """
    main_py = REPO_ROOT / "backend" / "main.py"
    src = main_py.read_text(encoding="utf-8")

    # Count occurrences of the canonical pattern.
    # Fixed form uses os.path.abspath(os.path.join(..., "backend_agents"))
    # and os.path.abspath(os.path.join(..., "backend_earnings")).
    agents_abspath_count = src.count(
        'os.path.abspath(\n            os.path.join(os.path.dirname(__file__), "..", "backend_agents")\n        )'
    )
    earnings_abspath_count = src.count(
        'os.path.abspath(\n            os.path.join(os.path.dirname(__file__), "..", "backend_earnings")\n        )'
    )

    # At minimum: 7 agent wrappers + 3 earnings wrappers.
    assert agents_abspath_count >= 7, (
        f"Expected >=7 backend_agents abspath sites in main.py, "
        f"found {agents_abspath_count}. Railway path fix (3cd1c8c) "
        f"may have regressed."
    )
    assert earnings_abspath_count >= 3, (
        f"Expected >=3 backend_earnings abspath sites in main.py, "
        f"found {earnings_abspath_count}. Railway path fix (3cd1c8c) "
        f"may have regressed."
    )

    # The guard pattern must appear alongside every insert.
    # Counting distinct guard lines ensures no naked sys.path.insert
    # slipped in.
    agents_guard_count = src.count(
        "if _AGENTS_PATH not in sys.path:"
    )
    earnings_guard_count = src.count(
        "if _EARNINGS_PATH not in sys.path:"
    )
    assert agents_guard_count >= 7, (
        f"Missing `if _AGENTS_PATH not in sys.path` guard — "
        f"found {agents_guard_count}, expected >=7"
    )
    assert earnings_guard_count >= 3, (
        f"Missing `if _EARNINGS_PATH not in sys.path` guard — "
        f"found {earnings_guard_count}, expected >=3"
    )
