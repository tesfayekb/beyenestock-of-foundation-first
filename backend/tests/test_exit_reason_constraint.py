"""
Companion test for the trading_positions_exit_reason_check constraint.

Purpose: catch the bug class that previously produced stuck-open
positions — a developer adds a new exit_reason string in Python code
but forgets to extend the DB CHECK constraint. Postgres then silently
rejects every close write with that reason, the monitor's fail-open
try/except swallows the error, and the position sits at status='open'
indefinitely.

How this test prevents recurrence:
  1. AST-parse backend/position_monitor.py and backend/execution_engine.py.
     Collect every string literal that is assigned to an `exit_reason`
     keyword argument or a dict key named 'exit_reason'. These are the
     values that actually get written to the DB.
  2. Parse the authoritative migration
     supabase/migrations/20260421_exit_reason_comprehensive.sql and
     extract the exit_reason IN (...) allowlist.
  3. Assert (code set) ⊆ (constraint set). Any gap fails CI with a
     diff that names the missing values and points the developer at
     the migration to extend.

The AST walker deliberately matches ONLY write-sites (kwarg=literal
and dict['exit_reason']=literal). Read-sites such as
`exit_reason not in ("profit_target", "manual")` in execution_engine.py
line 720 are correctly ignored — those strings are comparison
predicates, not inserted values.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Iterable

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
_MIGRATION = (
    _REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260421_exit_reason_comprehensive.sql"
)
# Files whose hardcoded exit_reason= writes must be in the constraint.
# Test files are deliberately excluded — fixture values in tests do not
# run against the real DB constraint.
_AUDITED_FILES = (
    _BACKEND / "position_monitor.py",
    _BACKEND / "execution_engine.py",
)


def _is_str_const(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _extract_exit_reason_literals(py_path: Path) -> set[str]:
    """Walk the AST and collect every string literal written to an
    `exit_reason` destination. Matches two patterns:

      1. Call keyword argument:
             close_virtual_position(..., exit_reason="emergency_backstop")
      2. Dict literal:
             {"exit_reason": "watchdog_engine_silent", ...}

    A `Call` with `func.id == 'dict'` would also be captured via its
    keywords, but the codebase uses literal dicts everywhere.
    """
    tree = ast.parse(py_path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if (
                    kw.arg == "exit_reason"
                    and _is_str_const(kw.value)
                ):
                    found.add(kw.value.value)
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    _is_str_const(key)
                    and key.value == "exit_reason"  # type: ignore[attr-defined]
                    and _is_str_const(value)
                ):
                    found.add(value.value)  # type: ignore[attr-defined]
    return found


def _extract_constraint_allowlist(sql_path: Path) -> set[str]:
    """Pull the IN (...) body for exit_reason out of the comprehensive
    migration and return the set of quoted literal values. Robust
    against SQL line comments (`-- …`) and block whitespace so the
    developer-friendly comments in the migration don't break parsing.
    """
    text = sql_path.read_text(encoding="utf-8")
    # Narrow to the ADD CONSTRAINT … CHECK (…) region so we never
    # accidentally pick up an `exit_reason IN (…)` that might appear
    # in a COMMENT or an earlier DROP in the same file.
    add_region = re.search(
        r"ADD\s+CONSTRAINT\s+trading_positions_exit_reason_check\s+"
        r"CHECK\s*\((?P<body>.*?)\)\s*;",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    assert add_region, (
        f"Could not find ADD CONSTRAINT trading_positions_exit_reason_check "
        f"in {sql_path}. Did the migration filename or constraint name "
        f"change? Update _MIGRATION in this test."
    )
    body = add_region.group("body")
    # Strip SQL line comments so commentary doesn't leak quoted words.
    body_clean = re.sub(r"--[^\n]*", "", body)
    return set(re.findall(r"'([^']+)'", body_clean))


def test_all_exit_reasons_in_constraint():
    """Every hardcoded exit_reason string in the write paths must be
    in the DB CHECK constraint. A failure here means someone added
    a new reason without shipping the companion migration; the fix
    is to extend the allowlist in the migration named in the error
    message (or open a new migration that drops and recreates the
    constraint)."""
    allowed = _extract_constraint_allowlist(_MIGRATION)

    code_values: set[str] = set()
    per_file: dict[str, Iterable[str]] = {}
    for path in _AUDITED_FILES:
        literals = _extract_exit_reason_literals(path)
        per_file[path.name] = sorted(literals)
        code_values |= literals

    missing = sorted(code_values - allowed)
    assert not missing, (
        "exit_reason string(s) written in code but NOT in the DB "
        "CHECK constraint — Postgres will silently reject these close "
        "writes, leaving positions stuck at status='open'.\n\n"
        f"  missing: {missing}\n"
        f"  audited files: {dict(per_file)}\n"
        f"  constraint source: {_MIGRATION.relative_to(_REPO_ROOT)}\n\n"
        "Fix: add the missing value(s) to the CHECK (exit_reason IN (...)) "
        "list in the migration above (or create a NEW migration that "
        "drops and recreates trading_positions_exit_reason_check). "
        "Then update the VALID EXIT REASONS comment block at the top "
        "of backend/position_monitor.py."
    )


def test_constraint_keeps_all_legacy_values():
    """Dropping legacy values would retroactively reject any historical
    row whose exit_reason matches the old allowlist (e.g. during a
    Postgres table rewrite). Pin the legacy set explicitly so a
    future migration can't accidentally remove them."""
    legacy = {
        "profit_target",
        "stop_loss",
        "time_stop_230pm",
        "time_stop_345pm",
        "touch_prob_threshold",
        "cv_stress_trigger",
        "state4_degrading",
        "portfolio_stop",
        "circuit_breaker",
        "capital_preservation",
        "manual",
    }
    allowed = _extract_constraint_allowlist(_MIGRATION)
    dropped = sorted(legacy - allowed)
    assert not dropped, (
        f"Legacy exit_reason values removed from the constraint: "
        f"{dropped}. Historical rows with these values exist in the DB "
        f"and must remain valid. Re-add them to "
        f"{_MIGRATION.relative_to(_REPO_ROOT)}."
    )
