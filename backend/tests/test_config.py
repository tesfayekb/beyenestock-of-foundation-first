import pytest

import config


def test_validate_config_raises_when_missing_required_key(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "x")
    monkeypatch.setenv("DATABENTO_API_KEY", "x")
    monkeypatch.setenv("TRADIER_API_KEY", "x")
    monkeypatch.setenv("POLYGON_API_KEY", "x")

    with pytest.raises(ValueError) as exc:
        config.validate_config()

    assert "SUPABASE_URL" in str(exc.value)
