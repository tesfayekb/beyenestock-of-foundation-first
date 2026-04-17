def test_tradier_account_id_in_required_keys():
    """TRADIER_ACCOUNT_ID must be in REQUIRED_KEYS."""
    import config
    assert "TRADIER_ACCOUNT_ID" in config.REQUIRED_KEYS


def test_gex_nearest_wall_returns_nearest_above_spx():
    """_nearest_positive_wall returns strike closest above SPX, not lowest."""
    from gex_engine import GexEngine
    gex_by_strike = {4800.0: 100.0, 5100.0: 50.0, 5300.0: 200.0}
    # SPX at 5200 — nearest above is 5300, not 4800
    result = GexEngine._nearest_positive_wall(gex_by_strike, spx_price=5200.0)
    assert result == 5300.0


def test_gex_nearest_wall_falls_back_to_below():
    """Falls back to nearest below when no strikes above SPX."""
    from gex_engine import GexEngine
    gex_by_strike = {4800.0: 100.0, 5000.0: 50.0}
    # SPX at 5200 — no strikes above, nearest below is 5000
    result = GexEngine._nearest_positive_wall(gex_by_strike, spx_price=5200.0)
    assert result == 5000.0


def test_gex_nearest_wall_returns_none_when_no_positives():
    """Returns None gracefully when no positive GEX strikes."""
    from gex_engine import GexEngine
    gex_by_strike = {5200.0: -100.0, 5300.0: -50.0}
    result = GexEngine._nearest_positive_wall(gex_by_strike, spx_price=5200.0)
    assert result is None


def test_open_today_session_returns_false_on_db_error():
    """open_today_session returns False gracefully on failure."""
    from unittest.mock import patch
    from session_manager import open_today_session
    with patch("session_manager.get_today_session", side_effect=Exception("DB error")):
        result = open_today_session()
    assert result is False


def test_close_today_session_returns_true_if_already_closed():
    """close_today_session is idempotent — returns True if already closed."""
    from unittest.mock import patch
    from session_manager import close_today_session
    with patch("session_manager.get_today_session", return_value={
        "id": "test-id",
        "session_status": "closed",
        "session_date": "2026-04-17",
    }):
        result = close_today_session()
    assert result is True
