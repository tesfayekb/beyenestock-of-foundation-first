from unittest.mock import patch


def test_compute_position_size_zero_contracts_when_spread_width_zero():
    """Zero spread_width must return 0 contracts — prevents division by zero."""
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0, spread_width=0, sizing_phase=1
    )
    assert result["contracts"] == 0


def test_compute_position_size_reduced_regime_disagreement():
    """D-021: regime_agreement=False must halve the risk_pct."""
    from risk_engine import compute_position_size
    agreed = compute_position_size(
        account_value=100_000.0, spread_width=5.0,
        sizing_phase=1, regime_agreement=True
    )
    disagreed = compute_position_size(
        account_value=100_000.0, spread_width=5.0,
        sizing_phase=1, regime_agreement=False
    )
    assert disagreed["risk_pct"] < agreed["risk_pct"]
    assert disagreed["size_reduction_reason"] is not None
    assert "d021" in disagreed["size_reduction_reason"]


def test_compute_position_size_reduced_consecutive_losses():
    """D-022: 3 consecutive losses must halve the risk_pct."""
    from risk_engine import compute_position_size
    normal = compute_position_size(
        account_value=100_000.0, spread_width=5.0,
        sizing_phase=1, consecutive_losses_today=0
    )
    reduced = compute_position_size(
        account_value=100_000.0, spread_width=5.0,
        sizing_phase=1, consecutive_losses_today=3
    )
    assert reduced["risk_pct"] < normal["risk_pct"]
    assert reduced["size_reduction_reason"] is not None
    assert "d022" in reduced["size_reduction_reason"]


def test_check_daily_drawdown_halts_at_minus_3pct():
    """D-005: -$3100 on $100k account (> -3%) must trigger halt."""
    from risk_engine import check_daily_drawdown
    with patch("risk_engine.update_session", return_value=True), \
         patch("risk_engine.write_audit_log", return_value=True), \
         patch("risk_engine.write_health_status", return_value=True):
        result = check_daily_drawdown("session-id", -3100.0, 100_000.0)
    assert result is True


def test_check_daily_drawdown_ok_under_threshold():
    """D-005: -$2000 on $100k account (-2%) must NOT trigger halt."""
    from risk_engine import check_daily_drawdown
    with patch("risk_engine.update_session", return_value=True), \
         patch("risk_engine.write_audit_log", return_value=True), \
         patch("risk_engine.write_health_status", return_value=True):
        result = check_daily_drawdown("session-id", -2000.0, 100_000.0)
    assert result is False


def test_check_trade_frequency_blocked_in_panic():
    """D-020: panic regime must block all entries (max_trades=0)."""
    from risk_engine import check_trade_frequency
    allowed, reason = check_trade_frequency(0, "panic")
    assert allowed is False
    assert reason is not None
    assert "panic" in reason


def test_check_trade_frequency_blocked_at_regime_cap():
    """D-020: must block when trade count reaches the regime cap."""
    from risk_engine import check_trade_frequency, REGIME_MAX_TRADES
    cap = REGIME_MAX_TRADES["pin_range"]  # 3
    allowed, reason = check_trade_frequency(cap, "pin_range")
    assert allowed is False
    assert reason is not None


# ── T0-7: floor-to-1 sizing when budget is ≥ 50% of one contract cost ──────────

def test_minimum_1_contract_when_budget_above_floor():
    """
    T0-7 regression guard — iron_butterfly + moderate at spread_width=5
    produces 1 contract via the T0-7 floor.

    Post-2026-04-20 recalibration math:
      risk_pct = _DEBIT_RISK_PCT["iron_butterfly"] = 0.008 (2×)
      after moderate (0.70×)                      = 0.0056
      max_risk_dollars = $100k × 0.0056           = $560
      stressed_loss   = 5.0 × 100                 = $500
      int(560/500) = 1 → direct calculation (floor not needed)

    At historical values (risk=0.004, width=5, moderate) the floor
    WAS the reason contracts==1 here; after the recalibration the
    direct int() gives 1 already, so this test now confirms the
    stacking order still produces sane results at the old width.
    """
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0,
        spread_width=5.0,
        sizing_phase=1,
        allocation_tier="moderate",
        strategy_type="iron_butterfly",
    )
    assert result["contracts"] == 1, (
        f"Phase 1 moderate sizing must produce 1 contract minimum "
        f"when budget is 56% of contract cost. Got {result['contracts']}"
    )


def test_zero_contracts_when_budget_below_floor():
    """
    T0-7: the floor must NOT round up when the budget is genuinely
    too small. Protects tiny accounts from auto-sizing to 1 on huge
    spreads.

    Post-2026-04-20 math: $20k × 0.008 × 0.70 = $112 budget against
    $500 stressed_loss → ratio 0.224 < 0.30 floor → 0 contracts.
    """
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=20_000.0,
        spread_width=5.0,
        sizing_phase=1,
        allocation_tier="moderate",
        strategy_type="iron_butterfly",
    )
    assert result["contracts"] == 0, (
        f"Budget 11% of contract cost must stay at 0 contracts. "
        f"Got {result['contracts']}"
    )


def test_floor_does_not_override_danger_tier():
    """
    T0-7: Danger tier short-circuits to 0 contracts BEFORE the floor check.
    The floor must not accidentally revive a danger-halted trade.
    """
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0,
        spread_width=5.0,
        sizing_phase=1,
        allocation_tier="danger",
        strategy_type="iron_butterfly",
    )
    assert result["contracts"] == 0, (
        f"Danger tier must always return 0 contracts regardless of budget. "
        f"Got {result['contracts']}"
    )
    assert result["size_reduction_reason"] == "allocation_tier_danger_d004"


def test_floor_covers_phase1_satellite_moderate_iron_condor_at_old_width():
    """
    T0-7 regression guard — preserves behavior of commit 167d7cd (the
    original T0-7 floor loosening). Uses the old spread_width=5 so the
    test remains meaningful as a unit check of the floor logic; this
    exact scenario cannot arise in production after the 2026-04-20
    width recalibration (widths are now 10pt minimum).

    Post-recalibration math at spread_width=5:
      base risk_pct = _RISK_PCT[1]["satellite"] = 0.005 (2× prior)
      after moderate (0.70×)                    = 0.0035
      max_risk_dollars = $100k × 0.0035         = $350
      stressed_loss   = 5.0 × 100               = $500
      ratio           = 350 / 500               = 0.70

    0.70 >> 0.30 floor → still produces 1 contract.

    For the current-widths equivalent (where the floor actually fires
    at the boundary and tests the 0.30 threshold), see
    test_floor_covers_sat_full_at_current_width below.
    """
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0,
        spread_width=5.0,
        sizing_phase=1,
        position_type="satellite",
        allocation_tier="moderate",
        strategy_type="iron_condor",
    )
    assert result["contracts"] == 1, (
        f"Phase 1 satellite + moderate iron_condor on $100k at old "
        f"width=5.0 must still produce 1 contract. Got "
        f"{result['contracts']} contracts, risk_pct={result['risk_pct']}."
    )
    assert result["risk_pct"] == round(0.005 * 0.70, 6), (
        f"Expected effective risk_pct 0.0035 (0.005 × 0.70) after "
        f"2026-04-20 Phase 1 doubling, got {result['risk_pct']}"
    )


def test_floor_covers_sat_full_at_current_width():
    """
    T0-7 (2026-04-20 recalibration): verify the floor fires at the
    current operating widths. VIX 15-20 band → width=15 → stressed=$1500.
    Phase 1 satellite+full is $500 budget — 0.33 ratio, which is above
    the 0.30 floor. This is the highest-leverage "floor fires" path in
    production after the recalibration.
    """
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0,
        spread_width=15.0,  # VIX 15-20 band (today's operating width)
        sizing_phase=1,
        position_type="satellite",
        allocation_tier="full",
        strategy_type="iron_condor",
    )
    assert result["contracts"] == 1, (
        f"Phase 1 satellite + full iron_condor on $100k at current "
        f"VIX 15-20 width=15 must produce 1 contract via T0-7 floor. "
        f"Got {result['contracts']} contracts, "
        f"risk_pct={result['risk_pct']}."
    )
    assert result["risk_pct"] == 0.005, (
        f"Expected effective risk_pct 0.005 (satellite full-tier Phase 1 "
        f"post-doubling), got {result['risk_pct']}"
    )


def test_floor_blocks_sat_moderate_at_current_width():
    """
    T0-7 (2026-04-20 recalibration): sat+moderate at the current VIX
    15-20 operating width is the row we deliberately accepted as
    blocked. $100k × 0.005 × 0.70 = $350 budget vs stressed=$1500 →
    0.23 ratio < 0.30 floor → contracts=0. This inverses the behavior
    of commit 167d7cd at the old narrow widths, and is documented as
    an accepted tradeoff ('fewer, better trades' — second trade of
    day under moderate RCS regime is intentionally skipped).
    """
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0,
        spread_width=15.0,
        sizing_phase=1,
        position_type="satellite",
        allocation_tier="moderate",
        strategy_type="iron_condor",
    )
    assert result["contracts"] == 0, (
        f"Phase 1 satellite + moderate iron_condor at current width=15 "
        f"must be blocked (deliberate tradeoff of the 2026-04-20 width "
        f"recalibration). Got {result['contracts']} contracts."
    )


def test_core_full_produces_contract_at_all_operating_widths():
    """
    T0-7 (2026-04-20 recalibration) — HARD INVARIANT: the core+full
    tier MUST produce contracts >= 1 at every width in the
    VIX_SPREAD_WIDTH_TABLE, including the high-stress VIX>30 wing.
    This is the constraint that drove the entire recalibration.

    If this test fails, trading has been unilaterally disabled for
    that VIX regime and the operator must be paged before any deploy.
    """
    from risk_engine import compute_position_size
    from strike_selector import VIX_SPREAD_WIDTH_TABLE

    for vix_threshold, width in VIX_SPREAD_WIDTH_TABLE:
        result = compute_position_size(
            account_value=100_000.0,
            spread_width=width,
            sizing_phase=1,
            position_type="core",
            allocation_tier="full",
            strategy_type="iron_condor",
        )
        assert result["contracts"] >= 1, (
            f"Phase 1 core+full at VIX<{vix_threshold} (width={width}) "
            f"produced {result['contracts']} contracts on $100k. This "
            f"violates the core+full hard invariant — the system "
            f"CANNOT enter any trade at this VIX regime. Review "
            f"either _RISK_PCT[1]['core'] or the width table."
        )


def test_core_moderate_produces_contract_at_normal_vix():
    """
    T0-7 (2026-04-20 recalibration) — operational invariant for the
    most common live path: Phase 1 core+moderate at the VIX 15-20
    band (today's band) must produce contracts >= 1. Budget $700 vs
    stressed $1500 = 0.47 ratio, floor fires.

    Separated from the all-VIX test because core+moderate is
    INTENTIONALLY blocked at VIX>30 (stressed $3000, floor $900,
    $700 < $900 → skipped) as part of the crisis-regime discipline.
    """
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0,
        spread_width=15.0,  # VIX 15-20 band
        sizing_phase=1,
        position_type="core",
        allocation_tier="moderate",
        strategy_type="iron_condor",
    )
    assert result["contracts"] == 1, (
        f"Phase 1 core+moderate iron_condor at VIX 15-20 width=15 "
        f"must produce 1 contract (most common live path). Got "
        f"{result['contracts']} contracts."
    )


def test_iron_butterfly_fires_at_current_width():
    """
    T0-7 (2026-04-20 recalibration): iron_butterfly risk_pct was
    doubled 0.004 → 0.008 in lockstep with the width widening. At
    full tier under today's width=15, budget = $100k × 0.008 × 1.0
    = $800, stressed = $1500, ratio = 0.53 → floor fires → 1 contract.

    Without the doubling, iron_butterfly would be disabled at all
    widths >= 10pt.
    """
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0,
        spread_width=15.0,
        sizing_phase=1,
        allocation_tier="full",
        strategy_type="iron_butterfly",
    )
    assert result["contracts"] == 1, (
        f"iron_butterfly at full tier / width=15 must produce 1 "
        f"contract after the 2026-04-20 risk_pct doubling. Got "
        f"{result['contracts']}."
    )
    assert result["risk_pct"] == 0.008, (
        f"Expected iron_butterfly risk_pct=0.008 (post-doubling), "
        f"got {result['risk_pct']}"
    )


def test_floor_respects_zero_spread_width():
    """
    T0-7: spread_width=0 short-circuits to 0 contracts before the floor.
    The floor must not kick in here (would also divide by zero).
    """
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0,
        spread_width=0,
        sizing_phase=1,
        allocation_tier="moderate",
        strategy_type="iron_butterfly",
    )
    assert result["contracts"] == 0
    assert result["size_reduction_reason"] == "zero_spread_width"
