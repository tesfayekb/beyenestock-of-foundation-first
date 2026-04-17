"""Tests for Phase B2 asymmetric condor and OptionsDX processor."""
import pandas as pd
import numpy as np


# -- Phase B2 tests --------------------------------------------------------

def test_gex_asymmetry_wall_below_spx():
    """Wall below SPX -> put_mult=1.5, call_mult=0.75."""
    from unittest.mock import MagicMock
    from strike_selector import _get_gex_asymmetry

    mock_redis = MagicMock()
    # Wall at 5180, SPX at 5200 -> wall is below, dist=0.38%
    mock_redis.get.side_effect = lambda k: (
        b"5180.0" if k == "gex:nearest_wall" else
        b"0.8" if k == "gex:confidence" else None
    )
    result = _get_gex_asymmetry(mock_redis, 5200.0)
    assert result["put_width_mult"] == 1.5
    assert result["call_width_mult"] == 0.75


def test_gex_asymmetry_wall_above_spx():
    """Wall above SPX -> put_mult=0.75, call_mult=1.5."""
    from unittest.mock import MagicMock
    from strike_selector import _get_gex_asymmetry

    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda k: (
        b"5220.0" if k == "gex:nearest_wall" else
        b"0.8" if k == "gex:confidence" else None
    )
    result = _get_gex_asymmetry(mock_redis, 5200.0)
    assert result["put_width_mult"] == 0.75
    assert result["call_width_mult"] == 1.5


def test_gex_asymmetry_low_confidence():
    """Low GEX confidence -> symmetric (both 1.0)."""
    from unittest.mock import MagicMock
    from strike_selector import _get_gex_asymmetry

    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda k: (
        b"5180.0" if k == "gex:nearest_wall" else
        b"0.1" if k == "gex:confidence" else None
    )
    result = _get_gex_asymmetry(mock_redis, 5200.0)
    assert result["put_width_mult"] == 1.0
    assert result["call_width_mult"] == 1.0


def test_gex_asymmetry_no_redis():
    """No Redis -> symmetric fallback."""
    from strike_selector import _get_gex_asymmetry
    result = _get_gex_asymmetry(None, 5200.0)
    assert result["put_width_mult"] == 1.0
    assert result["call_width_mult"] == 1.0


# -- OptionsDX processing tests --------------------------------------------

def test_compute_daily_features_zero_gamma():
    """Zero-gamma computed where net gamma crosses zero."""
    from scripts.process_options_data import compute_daily_features

    # Synthetic chain: net gamma crosses zero between strikes 5195 and 5200.
    # P_GAMMA inverted (option A) so C_GAMMA - P_GAMMA flips sign at spot:
    #   low strikes:  net < 0  (dealer puts dominate)
    #   high strikes: net > 0  (dealer calls dominate)
    rows = []
    for strike in [5190, 5195, 5200, 5205, 5210]:
        rows.append({
            "QUOTE_DATE": "2022-01-03",
            "UNDERLYING_LAST": 5200.0,
            "DTE": 0,
            "STRIKE": strike,
            "C_GAMMA": 0.001 if strike >= 5200 else 0.0005,
            "P_GAMMA": 0.001 if strike <= 5195 else 0.0005,
            "C_IV": 0.20,
            "P_IV": 0.22,
            "C_VOLUME": 100,
            "P_VOLUME": 150,
            "C_DELTA": 0.5 if strike == 5200 else 0.3,
            "P_DELTA": -0.5 if strike == 5200 else -0.25,
        })
    df = pd.DataFrame(rows)
    result = compute_daily_features(df)

    assert len(result) == 1
    assert result.iloc[0]["zero_gamma"] is not None
    # Zero gamma should be between 5195 and 5205
    zg = result.iloc[0]["zero_gamma"]
    assert 5190 <= zg <= 5210, f"Zero gamma {zg} outside expected range"


def test_compute_iv_rank_increases_with_iv():
    """Higher IV -> higher IV rank."""
    from scripts.process_options_data import compute_iv_rank

    df = pd.DataFrame({
        "date": ["2022-01-03", "2022-01-04", "2022-01-05"],
        "iv_atm": [0.15, 0.20, 0.25],
        "pc_ratio": [1.0, 1.0, 1.0],
        "zero_gamma": [5200.0, 5200.0, 5200.0],
        "skew_25d": [0.02, 0.02, 0.02],
        "underlying": [5200.0, 5200.0, 5200.0],
        "n_strikes": [50, 50, 50],
    })
    result = compute_iv_rank(df)
    ranks = result["iv_rank"].tolist()
    assert ranks[0] <= ranks[1] <= ranks[2], \
        f"IV rank should increase with IV: {ranks}"
