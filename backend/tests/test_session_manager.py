from unittest.mock import patch, MagicMock
from datetime import date


def test_returns_none_on_db_error():
    """get_or_create_session returns None gracefully on DB failure."""
    from session_manager import get_or_create_session
    with patch("session_manager.get_client", side_effect=Exception("DB error")):
        result = get_or_create_session()
    assert result is None


def test_update_session_returns_false_on_error():
    """update_session returns False gracefully on DB failure."""
    from session_manager import update_session
    with patch("session_manager.get_client", side_effect=Exception("DB error")):
        result = update_session("fake-id", session_status="active")
    assert result is False
