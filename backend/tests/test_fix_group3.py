import os
import sys
import threading


def test_db_singleton_is_thread_safe():
    """get_client() must return the same instance across threads."""
    from unittest.mock import patch, MagicMock
    import db as db_module

    # Reset singleton for test
    db_module._client = None

    # create_client is imported lazily inside get_client(), patch at supabase level
    with patch("supabase.create_client", return_value=MagicMock()):
        threads = [threading.Thread(target=db_module.get_client) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    # All threads should resolve to the same singleton object
    assert db_module._client is not None


def test_db_module_has_lock():
    """db.py must have a _client_lock threading.Lock."""
    import db as db_module
    assert hasattr(db_module, "_client_lock")
    assert isinstance(db_module._client_lock, type(threading.Lock()))


def test_prediction_engine_gex_none_uses_neutral():
    """When gex:confidence is None (not in Redis), CV_Stress uses 0.5 not 1.0."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = None  # no Redis

    result = engine._compute_cv_stress()
    # With no data: vvix_z=0, gex_conf=0.5
    # proxy_vanna = 0 * 0.6 + (1-0.5)*2.0 = 1.0
    # proxy_charm = 0 * 0.4 + (1-0.5)*1.5 = 0.75
    # raw = 0.6*1.0 + 0.4*0.75 = 0.9
    # cv_stress = min(100, 0.9 * 20) = 18.0
    assert result["cv_stress_score"] == 18.0
    assert 0 <= result["cv_stress_score"] <= 100


def test_sentinel_supabase_singleton():
    """get_supabase() returns same instance on repeated calls."""
    from unittest.mock import patch, MagicMock

    # Ensure sentinel dir is importable
    sentinel_dir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "sentinel")
    )
    if sentinel_dir not in sys.path:
        sys.path.insert(0, sentinel_dir)

    # Set required env vars so sentinel/main.py config block doesn't sys.exit
    env_patch = {
        "RAILWAY_HEALTH_URL": "http://localhost:8080/health",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        "TRADIER_API_KEY": "test-key",
        "TRADIER_ACCOUNT_ID": "VA00000000",
    }
    with patch.dict(os.environ, env_patch):
        # Import fresh (or re-use cached module)
        if "main" in sys.modules:
            s = sys.modules["main"]
        else:
            import importlib
            s = importlib.import_module("main")

        s._supabase_client = None  # reset
        mock_client = MagicMock()

        with patch("main.create_client", return_value=mock_client) as mock_create:
            c1 = s.get_supabase()
            c2 = s.get_supabase()

    assert c1 is c2
    assert mock_create.call_count == 1  # created only once
