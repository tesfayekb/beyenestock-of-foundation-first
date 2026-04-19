"""
Phase 5A: Earnings Volatility System.

Separate from backend/ — communicates via Redis only.
Strategy: ATM straddle 2-3 days before earnings announcement.

TAX NOTE: Individual equity options (NVDA, AAPL, etc.) are NOT
Section 1256 contracts. Standard short/long-term capital gains apply.
This is different from the core SPX system's 60/40 treatment.

Architecture:
  backend_earnings/ runs alongside backend/ but never imports from it.
  Uses same Supabase DB and Redis, but separate tables and Redis keys.
  If backend_earnings/ crashes, backend/ continues trading SPX unaffected.

Redis keys written by this system:
  earnings:upcoming_events  — JSON list of upcoming events with edge scores
                              (was previously documented as earnings:upcoming
                              — the canonical name is earnings:upcoming_events,
                              which is what the code actually writes)
  earnings:active_position  — JSON of current open straddle (if any)
  earnings:last_scan_at     — ISO timestamp of last calendar scan
"""
