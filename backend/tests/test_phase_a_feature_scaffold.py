"""
12H Phase A — scaffolding / auto-gate tests for the LightGBM pipeline.

Two sets of checks:

1. `download_historical_data` exists and imports cleanly — a sanity
   gate to catch accidental deletes / broken top-level imports that
   would only surface the day someone actually runs the downloader.

2. `train_direction_model` correctly skips training (exit 0 with
   `insufficient_data`) when fewer than 90 labeled sessions exist in
   `trading_prediction_outputs`. This is the core auto-gate
   — premature training on a handful of sessions would overfit and
   the resulting model file would silently start gating real trades
   via execution_engine once it exists.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend/ and backend/scripts are importable.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))


# ── 1. download_historical_data: existence + importability ────────────


def test_download_script_exists():
    """The Phase A downloader file must exist at the documented path.
    Deleting or renaming it would leave the training script with no
    upstream data source, but a simple path check catches it instantly."""
    path = BACKEND_ROOT / "scripts" / "download_historical_data.py"
    assert path.exists(), (
        f"Expected {path} to exist — Phase A downloader script missing"
    )


def test_download_script_importable():
    """Importing the module must not raise — a broken top-level import
    (missing dep, syntax error, misconfigured path) would only surface
    when someone tried to `python -m scripts.download_historical_data`
    manually. This catches it in CI."""
    scripts_dir = BACKEND_ROOT / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        import download_historical_data  # noqa: F401
    finally:
        sys.path.remove(str(scripts_dir))


# ── 2. train_direction_model: 90-session auto-gate ────────────────────


def _load_train_module():
    """Load scripts/train_direction_model.py as a module in a way that
    survives repeated import in the same test session (pytest imports
    test files one-shot, but the script does a `sys.path.insert` at
    import time which we want to isolate)."""
    scripts_dir = BACKEND_ROOT / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        if "train_direction_model" in sys.modules:
            del sys.modules["train_direction_model"]
        import train_direction_model
        return train_direction_model
    finally:
        if str(scripts_dir) in sys.path:
            sys.path.remove(str(scripts_dir))


def test_train_script_gates_on_session_count():
    """Core 12H auto-gate: below 90 labeled sessions the script must
    exit(0) without calling load_data(), engineer_features(), or any
    of the heavy training pipeline. A non-zero exit would page the
    scheduler on-call for what is just a still-warming data window."""
    mod = _load_train_module()

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.not_.is_.return_value.limit.return_value.execute.return_value.data = [
        {"session_id": f"sess-{i}"} for i in range(50)
    ]

    with patch("db.get_client", return_value=mock_client), \
         patch.object(mod, "load_data") as mock_load, \
         patch.object(mod, "engineer_features") as mock_engineer, \
         patch.object(mod, "train_and_evaluate") as mock_train, \
         patch.object(mod, "save_model") as mock_save:
        with pytest.raises(SystemExit) as exc_info:
            mod.main()

    assert exc_info.value.code == 0, (
        "Insufficient-data exit must use code 0 — a scheduled job "
        "returning non-zero would trigger alerting for what is a "
        "legitimate skip."
    )
    mock_load.assert_not_called()
    mock_engineer.assert_not_called()
    mock_train.assert_not_called()
    mock_save.assert_not_called()


def test_train_script_count_uses_distinct_sessions():
    """Multiple labeled predictions per session must count as ONE
    session. Counting raw rows would let us cross the 90 threshold
    after only a dozen real sessions if each has several hourly
    predictions, which would train on a tiny dataset and ship a
    weak model to production."""
    mod = _load_train_module()

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.not_.is_.return_value.limit.return_value.execute.return_value.data = [
        # 30 rows but only 3 distinct session_ids → gate must fail.
        {"session_id": f"sess-{i % 3}"} for i in range(30)
    ]

    with patch("db.get_client", return_value=mock_client):
        count = mod.count_labeled_sessions()

    assert count == 3, (
        f"Expected 3 distinct session_ids from 30 duplicated rows, got {count}"
    )


def test_train_script_gate_fails_closed_on_supabase_error():
    """When Supabase is unreachable the gate must FAIL CLOSED (return
    0, refuse to train) rather than fail open. Training on a model
    assumed to have data we cannot verify would silently ship random
    weights to production."""
    mod = _load_train_module()

    def _boom(*_a, **_kw):
        raise ConnectionError("supabase outage")

    with patch("db.get_client", side_effect=_boom):
        count = mod.count_labeled_sessions()
        _, passed = mod.check_labeled_sessions_gate()

    assert count == 0
    assert passed is False


def test_train_script_gate_passes_at_90_sessions():
    """Boundary: exactly 90 distinct sessions → gate passes. A
    regression that used `> 90` instead of `>= 90` would permanently
    delay first training by one session; this pins the threshold."""
    mod = _load_train_module()

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.not_.is_.return_value.limit.return_value.execute.return_value.data = [
        {"session_id": f"sess-{i}"} for i in range(90)
    ]

    with patch("db.get_client", return_value=mock_client):
        count, passed = mod.check_labeled_sessions_gate()

    assert count == 90
    assert passed is True
