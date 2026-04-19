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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

# Phase 2A: AI provider selection for synthesis_agent.
# AI_PROVIDER must be one of: "anthropic" | "openai".
# Both default to current production values — flip via Railway env vars
# to A/B-test or fall back if one provider is degraded. The chosen
# provider's API key (ANTHROPIC_API_KEY / OPENAI_API_KEY) must be set
# or synthesis_agent will skip silently.
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic").lower()
AI_MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-5")

# Phase 2C: Options flow + sentiment intelligence (optional)
# Without UNUSUAL_WHALES_API_KEY, flow_agent falls back to Polygon put/call only.
UNUSUAL_WHALES_API_KEY = os.getenv("UNUSUAL_WHALES_API_KEY", "")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# HARD-B: External alerting via Gmail
# Set ALERT_EMAIL to receive critical trading event notifications.
# Set ALERT_GMAIL_APP_PASSWORD to a Gmail App Password (not your account password).
# To create: Google Account → Security → 2-Step Verification → App Passwords
# If either is empty, alerting is silently disabled (no error, no crash).
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")
ALERT_GMAIL_APP_PASSWORD = os.getenv("ALERT_GMAIL_APP_PASSWORD", "")
ALERT_FROM_EMAIL = os.getenv("ALERT_FROM_EMAIL", ALERT_EMAIL)
