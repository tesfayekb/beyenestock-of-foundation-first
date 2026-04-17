"""Tests for Phase A2: historical data download helpers."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_get_polygon_key_from_env():
    """get_polygon_key reads from environment variable."""
    import os
    with patch.dict(os.environ, {"POLYGON_API_KEY": "test-key-abc"}):
        from scripts.download_historical_data import get_polygon_key
        key = get_polygon_key()
    assert key == "test-key-abc"


def test_get_polygon_key_raises_when_missing():
    """get_polygon_key raises RuntimeError when key not found."""
    import os
    env = {k: v for k, v in os.environ.items() if k != "POLYGON_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        # Also mock Path.exists to return False (no .env file)
        with patch("pathlib.Path.exists", return_value=False):
            from scripts.download_historical_data import get_polygon_key
            try:
                get_polygon_key()
                assert False, "Should have raised"
            except RuntimeError as e:
                assert "POLYGON_API_KEY" in str(e)


def test_polygon_get_retries_on_429():
    """polygon_get retries when rate limited (429)."""
    import time

    call_count = [0]
    def mock_response(status, json_data=None):
        m = MagicMock()
        m.status_code = status
        m.json.return_value = json_data or {}
        return m

    responses = [
        mock_response(429),   # first call: rate limited
        mock_response(200, {"results": [{"t": 1, "c": 5200.0}]}),  # retry: success
    ]

    with patch("httpx.Client") as mock_client, \
         patch("time.sleep"):  # don't actually sleep in tests
        mock_client.return_value.__enter__.return_value.get.side_effect = [
            r for r in responses
        ]
        from scripts.download_historical_data import polygon_get
        result = polygon_get("https://example.com", {}, "test-key", retries=3)
        assert result["results"][0]["c"] == 5200.0


def test_polygon_get_raises_on_403():
    """polygon_get raises RuntimeError on 403 (plan restriction)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
        from scripts.download_historical_data import polygon_get
        try:
            polygon_get("https://example.com", {}, "test-key")
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "403" in str(e)
            assert "plan" in str(e).lower()


def test_write_manifest_creates_valid_json(tmp_path):
    """write_manifest writes valid JSON with row counts."""
    import pandas as pd
    from scripts.download_historical_data import write_manifest, DATA_DIR

    # Temporarily redirect output
    with patch("scripts.download_historical_data.DATA_DIR", tmp_path):
        dfs = {
            "spx_5min": pd.DataFrame({
                "timestamp_ms": [1000000],
                "datetime_et": pd.to_datetime(["2024-01-02 09:35:00-05:00"]),
                "close": [5200.0],
            }),
            "vix_daily": pd.DataFrame({
                "date": pd.to_datetime(["2024-01-02"]),
                "close": [15.0],
            }),
        }
        from scripts import download_historical_data as m
        original_dir = m.DATA_DIR
        m.DATA_DIR = tmp_path
        write_manifest(dfs)
        m.DATA_DIR = original_dir

    manifest_file = tmp_path / "download_manifest.json"
    assert manifest_file.exists()
    manifest = json.loads(manifest_file.read_text())
    assert "downloaded_at" in manifest
    assert manifest["files"]["spx_5min"]["rows"] == 1


def test_validate_does_not_raise_on_valid_data():
    """validate_downloads runs without raising on typical good data."""
    import pandas as pd
    from scripts.download_historical_data import validate_downloads

    dfs = {
        "spx_5min": pd.DataFrame({
            "timestamp_ms": range(0, 1000 * 300_000, 300_000),  # 5-min intervals
            "datetime_et": pd.date_range("2024-01-02 09:35", periods=1000, freq="5min",
                                          tz="America/New_York"),
        }),
        "spx_daily": pd.DataFrame({"close": [5100.0, 5200.0]}),
        "vix_daily": pd.DataFrame({"close": [15.0, 16.0]}),
        "vvix_daily": pd.DataFrame({"close": [90.0, 95.0]}),
        "vix9d_daily": pd.DataFrame({"close": [14.0, 15.0]}),
    }
    # Should not raise
    validate_downloads(dfs)
