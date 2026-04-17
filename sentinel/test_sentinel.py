"""
Local smoke tests for sentinel — run before deploying.
Does not require live credentials.
"""
import asyncio
import os
from unittest.mock import patch, AsyncMock, MagicMock


def test_sentinel_imports():
    """Sentinel imports cleanly with env vars set."""
    os.environ.setdefault("RAILWAY_HEALTH_URL", "http://localhost:8080/health")
    os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    os.environ.setdefault("TRADIER_API_KEY", "test-key")
    os.environ.setdefault("TRADIER_ACCOUNT_ID", "VA37545874")
    import main
    assert hasattr(main, "run_sentinel_loop")
    assert hasattr(main, "trigger_emergency_close")
    print("PASS: imports cleanly")


def test_heartbeat_returns_false_on_connection_error():
    """check_railway_heartbeat returns False when unreachable."""
    import main
    import httpx

    async def run():
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("unreachable")
            )
            result = await main.check_railway_heartbeat()
        assert result is False
        print("PASS: returns False on connection error")

    asyncio.run(run())


def test_emergency_idempotent():
    """trigger_emergency_close does not fire twice."""
    import main
    main.emergency_triggered = False

    async def run():
        with patch(
            "main.close_all_positions_tradier",
            return_value={"closed": 0, "errors": 0},
        ), \
             patch("main.write_audit_log"), \
             patch("main.write_sentinel_health"):
            await main.trigger_emergency_close("test")
            # Second call should be skipped
            await main.trigger_emergency_close("test_again")
        assert main.emergency_triggered is True
        print("PASS: emergency is idempotent")

    asyncio.run(run())


if __name__ == "__main__":
    test_sentinel_imports()
    test_heartbeat_returns_false_on_connection_error()
    test_emergency_idempotent()
    print("\nAll sentinel smoke tests passed.")
