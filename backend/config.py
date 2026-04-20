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
_tradier_sandbox_raw = os.getenv("TRADIER_SANDBOX")
if _tradier_sandbox_raw is None:
    # T2-13: no default — fail explicitly.
    # In development: set TRADIER_SANDBOX=true.
    # In production: set TRADIER_SANDBOX=false for live, true for paper.
    # Generating a default silently routes live keys to wrong environment.
    import warnings
    warnings.warn(
        "TRADIER_SANDBOX not set — defaulting to True (sandbox). "
        "Explicitly set TRADIER_SANDBOX=true or TRADIER_SANDBOX=false.",
        stacklevel=2,
    )
    TRADIER_SANDBOX = True
else:
    TRADIER_SANDBOX = _tradier_sandbox_raw.lower() == "true"
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

# 12I (C1): OCO bracket order submission to Tradier.
#
# Defaults to False. The scaffold in execution_engine._submit_oco_bracket
# is a C1 stub only — it does NOT yet construct a valid Tradier multileg
# close order for spread positions, does NOT infer sell_to_close vs
# buy_to_close from strategy direction, and does NOT compute correct
# TP/SL prices for debit strategies. See the docstring on
# `_submit_oco_bracket` for the full MUST-FIX list.
#
# Flipping TRADIER_SANDBOX=false is therefore NOT sufficient to activate
# OCO brackets — OCO_BRACKET_ENABLED=true is a deliberate second switch
# the operator must set only after the MUST-FIX items are addressed and
# the order shape has been validated against the Tradier sandbox account.
#
# When either switch is False, virtual position management in
# position_monitor continues to handle exits exclusively via P&L polling
# — the existing behaviour is unchanged.
_oco_enabled_raw = os.getenv("OCO_BRACKET_ENABLED", "false")
OCO_BRACKET_ENABLED = _oco_enabled_raw.lower() == "true"

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

# S4 / C-β: shared secret protecting POST /admin/trading/feature-flags.
# Must be set in BOTH Railway env vars AND the Supabase Edge Function
# secrets (set-feature-flag forwards it as X-Api-Key). When unset, the
# endpoint logs a warning and remains open — operators must set this
# before enabling real capital. Generate via:
#   python -c "import secrets; print(secrets.token_urlsafe(32))"
RAILWAY_ADMIN_KEY = os.getenv("RAILWAY_ADMIN_KEY", "")

# HARD-B: External alerting via Gmail
# Set ALERT_EMAIL to receive critical trading event notifications.
# Set ALERT_GMAIL_APP_PASSWORD to a Gmail App Password (not your account password).
# To create: Google Account → Security → 2-Step Verification → App Passwords
# If either is empty, alerting is silently disabled (no error, no crash).
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")
ALERT_GMAIL_APP_PASSWORD = os.getenv("ALERT_GMAIL_APP_PASSWORD", "")
ALERT_FROM_EMAIL = os.getenv("ALERT_FROM_EMAIL", ALERT_EMAIL)
