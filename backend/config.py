import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

REQUIRED_KEYS = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "DATABENTO_API_KEY",
    "TRADIER_API_KEY",
    "TRADIER_ACCOUNT_ID",
    "POLYGON_API_KEY",
]


def validate_config():
    missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
DATABENTO_API_KEY = os.getenv("DATABENTO_API_KEY")
TRADIER_API_KEY = os.getenv("TRADIER_API_KEY")
TRADIER_ACCOUNT_ID = os.getenv("TRADIER_ACCOUNT_ID")
TRADIER_SANDBOX = os.getenv("TRADIER_SANDBOX", "true").lower() == "true"
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

# Phase 2A: Economic Intelligence Layer (all optional — system works without them)
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

# Phase 2C: Options flow + sentiment intelligence (optional)
# Without UNUSUAL_WHALES_API_KEY, flow_agent falls back to Polygon put/call only.
UNUSUAL_WHALES_API_KEY = os.getenv("UNUSUAL_WHALES_API_KEY", "")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
