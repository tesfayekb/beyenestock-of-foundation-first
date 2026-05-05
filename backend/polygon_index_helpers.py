"""T-ACT-062 (2026-05-04): shared backward-compatible parser for the
Polygon index live-price Redis keys written by ``polygon_feed.py``.

Background
----------
Pre-T-ACT-062 ``polygon_feed.py`` wrote ``polygon:vix:current`` /
``polygon:vvix:current`` / ``polygon:vix9d:current`` as raw float
strings (e.g. ``b"18.29"``). The companion ``polygon:spx:current``
key was upgraded to a JSON envelope in PR #92 / T-ACT-046 to carry
upstream-timestamp metadata so the freshness guard at
``prediction_engine.run_cycle`` could detect silent staleness.

T-ACT-062 mirrors the SPX pattern across the remaining three Polygon
index feeds. Post-T-ACT-062 the four keys all carry the same shape::

    {
      "price": 18.29,
      "fetched_at": "2026-05-04T17:35:01.271+00:00" | None,
      "fetched_at_source": "polygon_upstream" | "missing",
      "source": "polygon_v3_snapshot"
    }

Why this lives in its own module
--------------------------------
Seven distinct production consumer sites read these Redis keys today
(``prediction_engine``, ``strategy_selector``, ``mark_to_market``,
``shadow_engine``, ``strike_selector``, ``databento_feed``, and the
diagnostic dashboard at ``main._safe_float_key``). Inlining the parse
logic at each site would mean 7 copies of the same try/except chain —
high copy-paste-drift risk and exactly the class of fragility that
HANDOFF NOTE Appendix A.7 (silent-failure-class family convention)
catalogues. Centralising the parser here means any future format
change (e.g. adding a ``timeframe`` field per the operator's
2026-05-04 evening probe note) is made in exactly one place.

Backward-compatibility contract
-------------------------------
Both legacy raw-float values AND the new JSON envelope deserialize
correctly via :func:`parse_polygon_index_value`. This is required for
two reasons:

1. **Rollover window**: each Polygon index key has a 3600s setex TTL,
   so legacy raw-float values written before a deploy can persist for
   up to one hour after the new producer code rolls out. Consumers
   reading those keys during the rollover must accept both shapes.
2. **Test fixtures**: ~13 test files across the suite currently
   fixture VIX/VVIX/VIX9D as raw float strings. Accepting both shapes
   means those tests continue to pass without bulk modification.

Returns ``default`` (a float) on null, empty, or unparseable input —
mirroring the fail-open contract of the existing ``_safe_float``
helper in ``prediction_engine`` so consumer sites can substitute this
helper without changing their fallback semantics.
"""

import json
from typing import Any


def parse_polygon_index_value(raw: Any, default: float) -> float:
    """Parse a Polygon index Redis value (legacy float-string OR JSON
    envelope) to float, falling back to ``default`` on any
    null/empty/malformed input. See module docstring for full
    contract."""
    if raw is None:
        return default
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
        s = str(raw).strip()
        if not s:
            return default
        if s[:1] == "{":
            obj = json.loads(s)
            price = obj.get("price")
            if price is None:
                return default
            return float(price)
        return float(s)
    except (ValueError, TypeError):
        return default
