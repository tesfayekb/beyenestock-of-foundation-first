"""Tests for Phase B4: Kelly-adjusted position sizing."""


def test_kelly_multiplier_high_win_rate():
    """High win rate produces multiplier > 1.0."""
    from risk_engine import compute_kelly_multiplier
    mult = compute_kelly_multiplier(
        recent_win_rate=0.725,
        avg_win_dollars=70.0,
        avg_loss_dollars=143.0,
    )
    assert mult > 1.0, f"Expected > 1.0 for 72.5% WR, got {mult}"
    assert mult <= 2.0, f"Multiplier capped at 2.0, got {mult}"


def test_kelly_multiplier_low_win_rate():
    """Win rate below edge threshold produces multiplier <= 1.0."""
    from risk_engine import compute_kelly_multiplier
    mult = compute_kelly_multiplier(
        recent_win_rate=0.52,
        avg_win_dollars=60.0,
        avg_loss_dollars=200.0,
    )
    assert mult <= 1.0, f"Expected <= 1.0 for weak edge, got {mult}"
    assert mult >= 0.5, f"Multiplier floored at 0.5, got {mult}"


def test_kelly_multiplier_negative_kelly():
    """Negative Kelly (no edge) returns minimum 0.5."""
    from risk_engine import compute_kelly_multiplier
    # 40% WR with 0.3 b = clearly negative Kelly
    mult = compute_kelly_multiplier(
        recent_win_rate=0.40,
        avg_win_dollars=30.0,
        avg_loss_dollars=200.0,
    )
    assert mult == 0.5, f"Expected 0.5 for negative Kelly, got {mult}"


def test_kelly_multiplier_none_inputs():
    """None inputs return 1.0 (no adjustment)."""
    from risk_engine import compute_kelly_multiplier
    assert compute_kelly_multiplier(None, None, None) == 1.0
    assert compute_kelly_multiplier(0.72, None, 143.0) == 1.0
    assert compute_kelly_multiplier(None, 70.0, 143.0) == 1.0


def test_kelly_multiplier_boundary_win_rates():
    """Win rate of 0 or 1 returns 1.0 (guard against degenerate inputs)."""
    from risk_engine import compute_kelly_multiplier
    assert compute_kelly_multiplier(0.0, 70.0, 143.0) == 1.0
    assert compute_kelly_multiplier(1.0, 70.0, 143.0) == 1.0


def test_compute_position_size_accepts_kelly_multiplier():
    """compute_position_size accepts kelly_multiplier and adjusts contracts."""
    from risk_engine import compute_position_size

    # Base sizing (no Kelly)
    base = compute_position_size(
        account_value=100_000.0,
        spread_width=5.0,
        kelly_multiplier=1.0,
    )

    # 1.5× Kelly — should produce more contracts
    boosted = compute_position_size(
        account_value=100_000.0,
        spread_width=5.0,
        kelly_multiplier=1.5,
    )

    # 0.5× Kelly — should produce fewer contracts
    reduced = compute_position_size(
        account_value=100_000.0,
        spread_width=5.0,
        kelly_multiplier=0.5,
    )

    assert boosted["contracts"] >= base["contracts"], \
        "Kelly 1.5x should produce >= base contracts"
    assert reduced["contracts"] <= base["contracts"], \
        "Kelly 0.5x should produce <= base contracts"


def test_compute_position_size_default_kelly_unchanged():
    """Default kelly_multiplier=1.0 produces same result as before B4."""
    from risk_engine import compute_position_size

    result = compute_position_size(
        account_value=100_000.0,
        spread_width=5.0,
    )
    # Should still work with no kelly_multiplier arg
    assert result["contracts"] >= 0
    assert "risk_pct" in result
