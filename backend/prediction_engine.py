"""
Prediction engine — runs every 5 minutes.
Phase 2: placeholder model outputs. Real models trained in Phase 4.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import redis as redis_lib
except ModuleNotFoundError:
    redis_lib = None

from config import REDIS_URL
from db import get_client, write_health_status, write_audit_log
from logger import get_logger
from session_manager import get_today_session

logger = get_logger("prediction_engine")


def _safe_float(value, default: float) -> float:
    """S4 / E-5: parse a Redis string/bytes value to float, fall back
    to the provided default on any conversion error or empty value."""
    if value is None:
        return default
    try:
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="ignore")
        s = str(value).strip()
        if not s:
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


def _is_market_hours() -> bool:
    try:
        import zoneinfo
        from datetime import datetime
        et = zoneinfo.ZoneInfo("America/New_York")
        now = datetime.now(et)
        if now.weekday() >= 5:
            return False
        minutes = now.hour * 60 + now.minute
        return 9 * 60 + 30 <= minutes <= 16 * 60
    except Exception:
        return False


class PredictionEngine:

    def __init__(self) -> None:
        if redis_lib is None:
            raise RuntimeError(
                "redis dependency required for PredictionEngine"
            )
        try:
            self.redis_client = redis_lib.Redis.from_url(
                REDIS_URL, decode_responses=True
            )
        except Exception as e:
            logger.error("prediction_engine_redis_failed", error=str(e))
            self.redis_client = None
        self._cycle_count = 0

        # Phase A3 + T-ACT-041: load trained LightGBM direction model
        # via three-tier strategy. See _load_direction_model() for the
        # local-cache → Supabase-fallback → silent-miss contract and
        # the health-probe instrumentation.
        self._direction_model = None
        self._direction_features = None
        self._load_direction_model()

        # T-ACT-054: one-time observability marker for cv_stress
        # degenerate-input cycles. First cycle that hits the
        # NULL-on-degenerate-input path emits an INFO log so future
        # sessions can verify the AND-logic gate is firing as intended;
        # subsequent degenerate cycles are silent to avoid log noise.
        # Pattern matches Track B's `_quote_fields_logged` /
        # `_spx_fields_logged` markers from `tradier_feed.py` and
        # `polygon_feed.py`. See HANDOFF NOTE A.7 silent-failure-class
        # family convention.
        self._cv_stress_degenerate_logged: bool = False

    # ------------------------------------------------------------------
    # T-ACT-041 — three-tier model loader (extracted from __init__ for
    # test ergonomics per DIAGNOSE D5; bundles the partial-state fix
    # per D3; wires Supabase fallback per Q-D2/D3/D4/D6/D10/D11).
    # ------------------------------------------------------------------

    def _load_direction_model(
        self,
        local_pkl:   Optional[Path] = None,
        local_meta:  Optional[Path] = None,
        cache_pkl:   Optional[Path] = None,
        cache_meta:  Optional[Path] = None,
    ) -> None:
        """
        Three-tier model load with health-probe instrumentation.

        Tier 1 — local cache:
          1a. ``backend/models/`` (operator's training output, present
              on dev machines, absent on Railway since .gitignore at
              lines 38-40 blocks committing model files).
          1b. ``/tmp/lightgbm_cache/`` (populated by a previous
              invocation of this method that hit Tier 2 in the same
              container; lost on Railway cold-restart since /tmp is
              ephemeral, so always empty on first PredictionEngine
              instantiation per process).
        Tier 2 — Supabase storage download from
          ``ml-models/direction/v1/{direction_lgbm_v1.pkl, model_metadata.json}``,
          atomically staged into ``/tmp/lightgbm_cache/.staging-<pid>/``
          before move-into-place. Either both files land or neither
          does — no partial cache state.
        Tier 3 — total miss. ``_direction_model`` stays ``None``,
          ``_direction_features`` stays ``None``, the GEX/ZG fallback
          path at L545 takes over. Per Q-D10: fall-through over
          fail-fast — keeps trading running at degraded conviction
          rather than crashing uvicorn on a dependency hiccup.

        Health-probe states (one-shot at this call site, written via
        ``write_health_status("direction_model", state, ...)``):
          - ``healthy``  — Tier 1 hit (local cache).
          - ``degraded`` — Tier 2 hit (loaded from Supabase fallback).
          - ``error``    — Tier 3 (both tiers missed).

        Partial-state guard (D3): if a local cache has the .pkl but
        not the .json (or vice versa), it is treated as a cache miss
        and triggers Supabase fallback. Eliminates the pre-existing
        silent failure at the previous L67-89 inline block where
        ``direction_model_loaded`` would log but inference at L545
        would short-circuit because ``_direction_features`` stayed
        ``None``. The same guard is enforced inside
        ``_load_pickle_and_metadata`` via the empty-features check.

        Storage-client constraint (D2): supabase-py 2.10 uses a
        SEPARATE httpx client for storage (NOT the HTTP/1.1-patched
        postgrest client at db.py:132-167). Safe for this single-
        threaded startup-time call. If storage calls ever fire from
        scheduler threads later, apply the session-replacement patch
        to the storage client too.

        Concurrent-instantiation safety (D4 + Q-D11): main.py:1283
        instantiates one PredictionEngine; trading_cycle.py:34 lazy-
        instantiates a second. The atomic-rename pattern keeps both
        safe — second instance either sees the cache populated by
        the first OR re-downloads independently and atomically
        replaces the cache file (last writer wins; both writers'
        bytes are equivalent).

        Test-friendly path overrides: kwargs default to the
        production paths but accept overrides so unit tests can
        exercise all three tiers against tmp dirs without monkey-
        patching ``Path`` or ``__file__`` at module scope.
        """
        if local_pkl is None:
            local_pkl = Path(__file__).parent / "models" / "direction_lgbm_v1.pkl"
        if local_meta is None:
            local_meta = Path(__file__).parent / "models" / "model_metadata.json"
        if cache_pkl is None:
            cache_pkl = Path("/tmp/lightgbm_cache/direction_lgbm_v1.pkl")
        if cache_meta is None:
            cache_meta = Path("/tmp/lightgbm_cache/model_metadata.json")

        # Tier 1 — local cache (1a then 1b). Both files required per
        # D3 partial-state guard.
        for pkl_path, meta_path, source_label in (
            (local_pkl, local_meta, "local-tree"),
            (cache_pkl, cache_meta, "tmp-cache"),
        ):
            if pkl_path.exists() and meta_path.exists():
                try:
                    self._load_pickle_and_metadata(pkl_path, meta_path)
                    logger.info(
                        "direction_model_loaded",
                        model_version="v1",
                        features=len(self._direction_features or []),
                        source=source_label,
                    )
                    self._safe_write_health(
                        "healthy", last_error_message=None,
                    )
                    return
                except Exception as exc:
                    # Local cache is corrupt or partial — clear state
                    # and fall through to Tier 2.
                    self._direction_model = None
                    self._direction_features = None
                    logger.warning(
                        "direction_model_local_load_failed",
                        error=str(exc),
                        source=source_label,
                    )

        # Tier 2 — Supabase storage fallback.
        try:
            self._download_model_from_supabase(cache_pkl, cache_meta)
            self._load_pickle_and_metadata(cache_pkl, cache_meta)
            logger.info(
                "direction_model_loaded",
                model_version="v1",
                features=len(self._direction_features or []),
                source="supabase-fallback",
            )
            self._safe_write_health(
                "degraded",
                last_error_message=(
                    "loaded from supabase fallback — local cache absent "
                    "(expected on Railway cold start)"
                ),
            )
            return
        except Exception as exc:
            self._direction_model = None
            self._direction_features = None
            logger.warning(
                "direction_model_supabase_fetch_failed",
                error=str(exc),
            )

        # Tier 3 — total miss. Falls through to GEX/ZG at L545.
        logger.warning(
            "direction_model_unavailable",
            message=(
                "local cache and Supabase fallback both missed; "
                "GEX/ZG fallback active at L545"
            ),
        )
        self._safe_write_health(
            "error",
            last_error_message=(
                "local cache and Supabase fallback both missed"
            ),
        )

    def _load_pickle_and_metadata(
        self, pkl_path: Path, meta_path: Path,
    ) -> None:
        """
        Load both files together. Raises if either file is unreadable
        OR if the metadata's ``features`` list is empty — the latter
        is the D3 partial-state guard. Without this check, a model
        could load successfully while ``_direction_features`` stayed
        empty, causing the inference check at L545
        (``if direction_model is not None and direction_features:``)
        to short-circuit silently — the bug this PR closes.
        """
        import json as _json
        import pickle

        with open(pkl_path, "rb") as f:
            model = pickle.load(f)
        meta = _json.loads(meta_path.read_text())
        features = meta.get("features", [])
        if not features:
            raise RuntimeError(
                f"model_metadata.json at {meta_path} has empty features "
                f"list — load aborted to prevent silent inference skip"
            )
        self._direction_model = model
        self._direction_features = features

    def _download_model_from_supabase(
        self, dest_pkl: Path, dest_meta: Path,
    ) -> None:
        """
        Atomic two-file download from
        ``ml-models/direction/v1/{direction_lgbm_v1.pkl, model_metadata.json}``.

        Stages both files in a per-process temp dir on the SAME
        filesystem as the destination so that ``os.replace()`` is
        atomic. Both downloads must succeed before either move-into-
        place — if the second download fails, the first is discarded
        with the staging dir.

        See _load_direction_model() docstring for D2/D4/D11 context.
        """
        import os as _os
        import tempfile

        bucket = "ml-models"
        pkl_remote_path  = "direction/v1/direction_lgbm_v1.pkl"
        meta_remote_path = "direction/v1/model_metadata.json"

        cache_root = dest_pkl.parent
        cache_root.mkdir(parents=True, exist_ok=True)
        staging_dir = Path(tempfile.mkdtemp(
            prefix=f".staging-{_os.getpid()}-",
            dir=str(cache_root),
        ))

        try:
            client = get_client()
            storage = client.storage.from_(bucket)

            # Both downloads BEFORE any move so a mid-flight failure
            # leaves zero partial state on disk.
            pkl_bytes  = storage.download(pkl_remote_path)
            meta_bytes = storage.download(meta_remote_path)

            if not pkl_bytes:
                raise RuntimeError(
                    f"empty bytes from supabase {bucket}/{pkl_remote_path}"
                )
            if not meta_bytes:
                raise RuntimeError(
                    f"empty bytes from supabase {bucket}/{meta_remote_path}"
                )

            staged_pkl  = staging_dir / dest_pkl.name
            staged_meta = staging_dir / dest_meta.name
            staged_pkl.write_bytes(pkl_bytes)
            staged_meta.write_bytes(meta_bytes)

            # Per-file atomic rename. POSIX guarantees os.replace()
            # is atomic within a single filesystem. Two-file rename
            # is best-effort (a process kill between the two leaves
            # the cache in partial state) — the D3 partial-state
            # guard at the next process startup heals that case by
            # treating partial cache as a miss and re-downloading.
            _os.replace(str(staged_pkl),  str(dest_pkl))
            _os.replace(str(staged_meta), str(dest_meta))

            logger.info(
                "direction_model_supabase_downloaded",
                bucket=bucket,
                pkl_path=pkl_remote_path,
                pkl_bytes=len(pkl_bytes),
                meta_bytes=len(meta_bytes),
            )
        finally:
            # Best-effort cleanup of any leftover staging files
            # (typical case: nothing left after rename, dir is empty).
            try:
                for p in staging_dir.iterdir():
                    try:
                        p.unlink()
                    except Exception:
                        pass
                staging_dir.rmdir()
            except Exception:
                pass

    def _safe_write_health(self, state: str, last_error_message: Optional[str] = None) -> None:
        """
        Wrap write_health_status so a Supabase write failure during
        the model-load probe never blocks the model-load path itself.
        Health is observability, not a runtime dependency.
        """
        try:
            write_health_status(
                "direction_model",
                state,
                last_error_message=last_error_message,
            )
        except Exception as exc:
            logger.warning(
                "direction_model_health_write_failed",
                error=str(exc),
                state=state,
            )

    def _read_redis(self, key: str, default=None):
        if not self.redis_client:
            return default
        try:
            raw = self.redis_client.get(key)
            return raw if raw is not None else default
        except Exception:
            return default

    def _safe_redis(
        self,
        key: str,
        default: Any = None,
        max_age_seconds: Optional[int] = None,
        age_key: Optional[str] = None,
    ) -> tuple[Any, bool]:
        """
        HARD-A: Safe Redis read with optional staleness check.

        Returns (value, is_fresh) tuple.
        is_fresh = False if:
          - Redis is down (fallback used)
          - Value is missing (default used)
          - Value is older than max_age_seconds (if specified)

        age_key: a separate Redis key holding the write timestamp
        (ISO string). If omitted, staleness is not checked.

        Usage:
          value, fresh = self._safe_redis(
              "gex:net", "0",
              max_age_seconds=3600,
              age_key="gex:updated_at",
          )
          if not fresh:
              logger.warning("gex_data_stale")

        Fail-open: if the age_key parse fails, the value is returned
        and marked fresh — better to use slightly stale data than to
        block trading on a metadata error.
        """
        raw = self._read_redis(key, default)

        if raw is None or raw == default:
            return default, False

        if max_age_seconds is None or age_key is None:
            return raw, True

        try:
            ts_raw = self._read_redis(age_key, None)
            if ts_raw is None:
                return raw, True
            ts_str = ts_raw.decode() if isinstance(ts_raw, bytes) else ts_raw
            ts = datetime.fromisoformat(ts_str)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            if age > max_age_seconds:
                logger.warning(
                    "redis_value_stale",
                    key=key,
                    age_seconds=round(age),
                    threshold=max_age_seconds,
                )
                return raw, False
            return raw, True
        except Exception:
            return raw, True

    def _get_spx_price(self) -> float:
        """Read current SPX price from Redis.

        PRIMARY:   polygon:spx:current  (recency-class TBD; populated by
                   polygon_feed.py from `/v3/snapshot?ticker.any_of=I:SPX`
                   at the operator's Polygon Indices subscription tier —
                   currently Indices Starter ($49/mo). Polygon's published
                   policy says Indices Starter is 15-min delayed for I:*
                   symbols, but the snapshot endpoint may serve real-time
                   despite policy. Empirical determination is tracked via
                   T-ACT-045; see TASK_REGISTER §14 for status. As of
                   2026-05-03 T-ACT-045 = PENDING-RE-RUN against post-
                   PR-#90-deploy data; the May 1 empirical attempt was
                   structurally pre-deploy and could not validate.
                   NOTE: Polygon Stocks Advanced ($199/mo) does NOT cover
                   I:* indices — different product line.

        FALLBACK:  tradier:quotes:SPX  (15-min delayed in Tradier sandbox
                   per empirical verification 2026-05-01 — kept ONLY as
                   fallback when Polygon write is missing or stale).
        SENTINEL:  5200.0  (legacy hardcoded last resort).

        Logs WARN when Tradier fallback triggers — operator alert that
        Polygon feed is unhealthy and the system is operating on
        plausibly-stale data. Logs ERROR when both sources fail.
        """
        import json
        # Primary: Polygon real-time
        try:
            raw = self._read_redis("polygon:spx:current", None)
            if raw:
                data = json.loads(raw)
                price = float(data.get("price") or 0)
                if price > 0:
                    return round(price, 2)
        except Exception:
            pass

        # Fallback: Tradier sandbox (15-min delayed)
        try:
            raw = self._read_redis("tradier:quotes:SPX", None)
            if raw:
                data = json.loads(raw)
                price = float(
                    data.get("last") or data.get("ask") or data.get("bid") or 0
                )
                if price > 0:
                    logger.warning(
                        "spx_price_polygon_unavailable_tradier_fallback",
                        fallback_price=price,
                    )
                    return round(price, 2)
        except Exception:
            pass

        logger.error("spx_price_all_sources_failed_using_sentinel")
        return 5200.0

    def _compute_regime(self) -> dict:
        """
        Regime classification — dual-model approach for D-021 disagreement.

        Layer A (regime_hmm): VVIX Z-score proxy (unchanged from Phase 2).
        Layer B (regime_lgbm): GEX zero-gamma level (new — real signal).

        Two independent inputs → genuine D-021 disagreement possible.
        GEX confidence < 0.3 → fall back to HMM for both (data quality gate).
        """
        import math

        # ROI-1: Check for catalyst/earnings day FIRST.
        # calendar:today:intel is written by economic_calendar at 8:45 AM ET.
        # When today is a major catalyst (FOMC/CPI/NFP) or major earnings day,
        # override regime to "event" so strategy_selector picks long_straddle
        # or calendar_spread from REGIME_STRATEGY_MAP["event"]. Previously
        # _compute_regime never read calendar intel, so the entire "event"
        # branch was dead code — straddle/calendar were unreachable.
        # RCS is capped at 55 on event days: IV is elevated (entry is fine)
        # but direction is uncertain (no max-confidence sizing).
        try:
            cal_raw = self._read_redis("calendar:today:intel", None)
            if cal_raw:
                import json as _json
                intel = _json.loads(cal_raw)
                if (
                    intel.get("has_major_catalyst")
                    or intel.get("has_major_earnings")
                ):
                    logger.info(
                        "regime_event_day_override",
                        has_catalyst=intel.get("has_major_catalyst"),
                        has_earnings=intel.get("has_major_earnings"),
                        day_classification=intel.get("day_classification"),
                    )
                    return {
                        "regime": "event",
                        "regime_hmm": "event",
                        "regime_lgbm": "event",
                        "regime_agreement": True,
                        "rcs": 55.0,
                        "allocation_tier": "moderate",
                        "gex_flip_zone_used": None,
                        "gex_conf_at_regime": 0.0,
                    }

                # T2-5: minor catalyst branch (PPI, retail sales, IP,
                # housing starts, etc.). Same "event" regime label so
                # strategy_selector still picks the event-family
                # strategies (long_straddle / calendar_spread) instead
                # of a normal-day pin-range play, but with a softer
                # cap than major catalysts:
                #
                #   major:   rcs=55  tier=moderate
                #   minor:   rcs=65  tier=low
                #
                # Minor-catalyst days historically produce smaller
                # close-to-close moves and tighter IV crush than CPI
                # or NFP, so the sizing cap can relax. Previously
                # these days fell through to the VVIX/GEX regime
                # classifier entirely — losing the event override
                # and the straddle/calendar routing that goes with it.
                if intel.get("has_minor_catalyst"):
                    logger.info(
                        "regime_minor_catalyst_override",
                        day_classification=intel.get("day_classification"),
                    )
                    return {
                        "regime": "event",
                        "regime_hmm": "event",
                        "regime_lgbm": "event",
                        "regime_agreement": True,
                        "rcs": 65.0,
                        "allocation_tier": "low",
                        "gex_flip_zone_used": None,
                        "gex_conf_at_regime": 0.0,
                    }
        except Exception:
            pass  # Calendar unavailable — fall through to normal regime logic

        # --- Read all signals ---
        vvix_z_raw = self._read_redis("polygon:vvix:z_score", None)
        try:
            vvix_z = float(vvix_z_raw) if vvix_z_raw is not None else 0.0
        except (ValueError, TypeError):
            vvix_z = 0.0

        gex_conf_raw = self._read_redis("gex:confidence", None)
        try:
            gex_conf = float(gex_conf_raw) if gex_conf_raw is not None else 0.0
        except (ValueError, TypeError):
            gex_conf = 0.0

        flip_zone_raw = self._read_redis("gex:flip_zone", None)
        try:
            flip_zone = float(flip_zone_raw) if flip_zone_raw else None
        except (ValueError, TypeError):
            flip_zone = None

        spx_price = self._get_spx_price()

        # --- Layer A: VVIX Z-score regime (HMM proxy) ---
        if abs(vvix_z) > 2.5:
            regime_hmm = "volatile_bearish" if vvix_z > 0 else "volatile_bullish"
            rcs_hmm = 35.0
        elif abs(vvix_z) > 1.5:
            regime_hmm = "quiet_bullish"
            rcs_hmm = 55.0
        else:
            regime_hmm = "pin_range"
            rcs_hmm = 65.0

        # --- Layer B: GEX zero-gamma regime (LightGBM proxy) ---
        # Requires gex_conf >= 0.3 (enough option flow data) and valid flip_zone
        if gex_conf < 0.3 or flip_zone is None or flip_zone <= 0:
            # Insufficient GEX data — both layers agree (no D-021 penalty)
            regime_lgbm = regime_hmm
            rcs_lgbm = rcs_hmm
        else:
            # SPX position relative to zero-gamma level
            dist_pct = (spx_price - flip_zone) / flip_zone  # positive = above ZG

            if abs(vvix_z) > 2.5:
                # Crisis override regardless of ZG position
                regime_lgbm = "crisis"
                rcs_lgbm = 25.0
            elif dist_pct > 0.003 and abs(vvix_z) < 1.5:
                # SPX above ZG, low vol → dealers long gamma → mean-reversion
                regime_lgbm = "pin_range"
                rcs_lgbm = 70.0
            elif dist_pct > 0.001 and abs(vvix_z) < 0.8:
                # SPX just above ZG, calm → quiet trend
                regime_lgbm = "quiet_bullish"
                rcs_lgbm = 60.0
            elif dist_pct < -0.003 and vvix_z > 1.5:
                # SPX below ZG, rising vol → dealers short gamma → trending
                regime_lgbm = "volatile_bearish"
                rcs_lgbm = 45.0
            elif dist_pct < -0.001:
                # SPX below ZG → trend-following regime
                regime_lgbm = "trend"
                rcs_lgbm = 55.0
            else:
                # Near ZG, uncertain
                regime_lgbm = "range"
                rcs_lgbm = 60.0

        # --- Combine: use average RCS, apply D-021 on disagreement ---
        rcs = (rcs_hmm + rcs_lgbm) / 2.0

        # D-021: genuine disagreement between HMM and LightGBM signals
        regime_agreement = regime_hmm == regime_lgbm
        if not regime_agreement:
            rcs = max(0.0, rcs - 15.0)
            write_audit_log(
                action="trading.regime_disagreement",
                metadata={
                    "regime_hmm": regime_hmm,
                    "regime_lgbm": regime_lgbm,
                    "vvix_z": round(vvix_z, 3),
                    "gex_flip_zone": flip_zone,
                    "spx_price": spx_price,
                    "dist_pct": round(dist_pct, 5) if flip_zone else None,
                    "rcs_after_penalty": round(rcs, 1),
                },
            )
            logger.warning(
                "regime_disagreement_d021",
                regime_hmm=regime_hmm,
                regime_lgbm=regime_lgbm,
                rcs=round(rcs, 1),
            )

        # Use the LightGBM (GEX-based) regime as primary when data is available.
        # P1-4: threshold raised from 0.3 → 0.4 to align with the
        # strategy_selector pin-override gate (line ~574). 0.3 is still
        # the minimum data-quality gate above (line ~257) — below 0.3
        # the option flow is insufficient to consider GEX at all. 0.4
        # is the higher bar required to actually drive regime selection
        # (and, downstream, strategy pinning). Same threshold for both
        # decisions keeps regime and strategy choice consistent.
        regime = regime_lgbm if gex_conf >= 0.4 and flip_zone else regime_hmm

        if rcs >= 80:
            allocation_tier = "full"
        elif rcs >= 60:
            allocation_tier = "moderate"
        elif rcs >= 40:
            allocation_tier = "low"
        elif rcs >= 20:
            allocation_tier = "pre_event"
        else:
            allocation_tier = "danger"

        return {
            "regime": regime,
            "regime_hmm": regime_hmm,
            "regime_lgbm": regime_lgbm,
            "regime_agreement": regime_agreement,
            "rcs": round(rcs, 2),
            "allocation_tier": allocation_tier,
            "gex_flip_zone_used": flip_zone,
            "gex_conf_at_regime": round(gex_conf, 4),
        }

    def _compute_cv_stress(self) -> dict:
        """
        CV_Stress computation with NULL-on-degenerate-input semantics.

        Phase 2 proxy: uses VVIX Z-score and GEX confidence.
        Real charm/vanna velocities from options chain in Phase 4.
        Formula: cv_stress = 60% * proxy_vanna + 40% * proxy_charm

        NULL semantics (T-ACT-054, ratified in PR
        `fix/t-act-054-cv-stress-null-on-degenerate`):
        Returns {"cv_stress_score": None, "charm_velocity": None,
        "vanna_velocity": None} when BOTH input arms are degenerate
        simultaneously:
          - vvix_z arm: baseline not warmed, vvix_z key absent, OR
            vvix_z parses to exactly 0.0
          - gex_conf arm: gex_confidence key absent OR saturated at
            >= 1.0

        The AND-logic is critical: gex_conf=1.0 alone is the normal
        RTH steady-state (per gex_engine.py:175 saturation
        `min(1.0, len(trades) / 1000)`), so OR-logic would NULL the
        majority of healthy cycles. Empirical Query 1 (2026-05-02)
        found 29.2% of cycles have BOTH conditions simultaneously —
        that is the precise subset Choice A targets. Without the
        AND-logic discipline, cv_stress would silently NULL across
        the majority of RTH cycles and break downstream gates that
        actually have meaningful signal to act on.

        Consumers MUST handle None explicitly per HANDOFF A.7
        silent-failure-class family convention. See:
          - prediction_engine.py:1031 (no_trade > 85, active gate)
          - prediction_engine.py:961, 972 (rule-based tilt — discipline floor)
          - strategy_selector.py:176 (long_gamma override, active gate)
          - position_monitor.py:778 (D-017 cv_stress exit, active gate)
          - model_retraining.py:817, 1061 (meta-label training — Meta-3 NaN sentinel)
          - execution_engine.py:388 (meta-label inference — Meta-3 NaN sentinel)
        """
        gex_conf_raw = self._read_redis("gex:confidence", None)
        vvix_z_raw = self._read_redis("polygon:vvix:z_score", None)
        baseline_ready_raw = self._read_redis(
            "polygon:vvix:baseline_ready", "False"
        )
        baseline_ready = baseline_ready_raw == "True"

        # Parse vvix_z defensively: None on missing OR non-numeric
        try:
            vvix_z_parsed = (
                float(vvix_z_raw) if vvix_z_raw is not None else None
            )
        except (ValueError, TypeError):
            vvix_z_parsed = None

        # Parse gex_conf defensively: None on missing OR non-numeric
        try:
            gex_conf_parsed = (
                float(gex_conf_raw) if gex_conf_raw is not None else None
            )
        except (ValueError, TypeError):
            gex_conf_parsed = None

        # AND-logic degenerate detection — both input arms must be
        # degenerate for the formula to produce semantically
        # meaningless output. See docstring above for why OR-logic
        # would be a critical defect.
        vvix_z_degenerate = (
            not baseline_ready
            or vvix_z_parsed is None
            or vvix_z_parsed == 0.0
        )
        gex_conf_degenerate = (
            gex_conf_parsed is None
            or gex_conf_parsed >= 1.0
        )
        degenerate = vvix_z_degenerate and gex_conf_degenerate

        if degenerate:
            # One-time INFO log per process startup (observability per
            # F2-c convention from Track B). Subsequent degenerate
            # cycles are silent to avoid log noise — operators only
            # need to know the gate is firing, not log every match.
            if not self._cv_stress_degenerate_logged:
                logger.info(
                    "cv_stress_degenerate_first_cycle",
                    baseline_ready=baseline_ready,
                    vvix_z_present=(vvix_z_parsed is not None),
                    vvix_z_value=vvix_z_parsed,
                    gex_conf_value=gex_conf_parsed,
                    gex_conf_saturated=(
                        gex_conf_parsed is not None
                        and gex_conf_parsed >= 1.0
                    ),
                )
                self._cv_stress_degenerate_logged = True
            return {
                "cv_stress_score": None,
                "charm_velocity": None,
                "vanna_velocity": None,
            }

        # Healthy-input path — at least one arm carries real signal.
        # Treat None gex_conf as neutral 0.5 (existing convention
        # preserved for backward compat with tests/calibration logic).
        vvix_z = vvix_z_parsed if vvix_z_parsed is not None else 0.0
        gex_conf_val = (
            gex_conf_parsed if gex_conf_parsed is not None else 0.5
        )
        proxy_vanna = abs(vvix_z) * 0.6 + (1.0 - gex_conf_val) * 2.0
        proxy_charm = abs(vvix_z) * 0.4 + (1.0 - gex_conf_val) * 1.5
        raw = 0.6 * proxy_vanna + 0.4 * proxy_charm
        cv_stress = min(100.0, max(0.0, raw * 20.0))

        return {
            "cv_stress_score": round(cv_stress, 2),
            "charm_velocity": round(proxy_charm, 8),
            "vanna_velocity": round(proxy_vanna, 8),
        }

    def _compute_direction(
        self,
        regime: str,
        cv_stress: Optional[float],
        spx_price: float = 5200.0,
        flip_zone: float = None,
        gex_conf: float = 0.0,
    ) -> dict:
        """
        Direction prediction — LightGBM model (Phase A3) with GEX/ZG overlay.

        Priority order:
        1. LightGBM model (if loaded) — uses live Redis features
        2. GEX/ZG rule-based (fallback when model not loaded)
        3. Regime-based hardcoded (fallback when GEX unavailable)
        """
        import math

        # --- Priority 0: AI synthesis agent (Phase 2A) ---
        # Only activates when: (a) agents:ai_synthesis:enabled = true in Redis
        # and (b) ai:synthesis:latest key is fresh (< 30 min old)
        ai_synthesis = None
        try:
            reader = getattr(self, "_read_redis", None)
            if reader is not None and getattr(self, "redis_client", None):
                ai_synthesis = reader("ai:synthesis:latest", None)
        except Exception:
            ai_synthesis = None

        # B-8: respect the agents:ai_synthesis:enabled flag. The comment
        # above says the path "only activates when flag = true" but the
        # code never actually checked. Without this gate, stale synthesis
        # JSON in Redis can drive predictions even after the operator
        # has disabled the agent from the trading console.
        synthesis_flag_on = False
        try:
            flag_raw = self._read_redis(
                "agents:ai_synthesis:enabled", None
            )
            synthesis_flag_on = flag_raw in ("true", b"true")
        except Exception:
            synthesis_flag_on = False

        if not synthesis_flag_on:
            ai_synthesis = None  # Flag OFF → skip synthesis path entirely

        if ai_synthesis:
            try:
                import json, time
                from datetime import datetime, timezone
                synth = json.loads(ai_synthesis)
                # Check freshness (must be < 30 minutes old)
                gen_at = synth.get("generated_at", "")
                if gen_at:
                    age_s = (
                        datetime.now(timezone.utc)
                        - datetime.fromisoformat(gen_at)
                    ).total_seconds()
                    if age_s < 28800:  # 8 hours — coupled with synthesis_agent.py:201 TTL. Synthesis runs once per weekday at 09:15 ET; 8hr window covers full trading day after morning cron without a same-day refresh. If intra-day refresh is later added (cron */30), tighten this back to 1800.
                        direction = synth.get("direction", "neutral")
                        confidence = float(synth.get("confidence", 0.0))
                        strategy_hint = synth.get("strategy", "")
                        sizing_modifier = float(synth.get("sizing_modifier", 1.0))
                        if confidence >= 0.55 and direction in ("bull", "bear", "neutral"):
                            logger.info(
                                "prediction_from_ai_synthesis",
                                direction=direction,
                                confidence=confidence,
                                strategy_hint=strategy_hint,
                                age_seconds=int(age_s),
                            )
                            # ROI-4: ensure the probability triplet sums to 1.0.
                            # The previous shape returned only p_bull + p_bear,
                            # leaving downstream consumers (PredictionConfidence,
                            # cv_stress sizing) to assume p_neutral. Make it
                            # explicit and renormalise on any floating-point drift.
                            _p_bull = (
                                confidence if direction == "bull"
                                else (1 - confidence) * 0.5
                            )
                            _p_bear = (
                                confidence if direction == "bear"
                                else (1 - confidence) * 0.5
                            )
                            _p_neutral = max(0.0, 1.0 - _p_bull - _p_bear)
                            _total = _p_bull + _p_bear + _p_neutral
                            if _total > 0 and abs(_total - 1.0) > 0.001:
                                _p_bull /= _total
                                _p_bear /= _total
                                _p_neutral /= _total
                            # Match the dict shape emitted by other prediction
                            # paths (LightGBM L571-573, GEX/ZG L620-622, regime
                            # fallback L651-660): include signal_weak,
                            # expected_move_pts, expected_move_pct so downstream
                            # consumers (no-trade gate at L904, analytics) get
                            # the same fields they get from non-AI-synth paths.
                            #
                            # KEEP strategy_hint (consumed by strategy_selector
                            # L1019-1075 ai_hint_override path); KEEP
                            # sizing_modifier (forward-compat pass-through);
                            # KEEP source (consumed by strategy_selector L1517
                            # telemetry routing). Schema columns added in
                            # sibling migration 20260430_add_ai_synthesis_columns.
                            #
                            # NEUTRAL guard on signal_weak: a high-conviction
                            # AI synth neutral prediction (p_bull == p_bear by
                            # construction) is a real signal that the market
                            # will pin — iron_condor is the literal play.
                            # Treating it as signal_weak conflates it with the
                            # placeholder/no-signal case (regime fallback) and
                            # would silently block iron_condor trades. The
                            # gate only fires for directional weakness.
                            _signal_weak = (
                                direction != "neutral"
                                and abs(_p_bull - _p_bear) < 0.05
                            )
                            return {
                                "direction":         direction,
                                "p_bull":            round(_p_bull, 4),
                                "p_bear":            round(_p_bear, 4),
                                "p_neutral":         round(_p_neutral, 4),
                                "confidence":        round(confidence, 4),
                                "expected_move_pts": round(10.0 * (_p_bull - _p_bear), 2),
                                "expected_move_pct": round(0.002 * (_p_bull - _p_bear), 6),
                                "signal_weak":       _signal_weak,
                                "strategy_hint":     strategy_hint,
                                "sizing_modifier":   sizing_modifier,
                                "source":            "ai_synthesis",
                            }
            except Exception as e:
                logger.warning("ai_synthesis_parse_failed", error=str(e))
        # Priority 0 not used — fall through to LightGBM / GEX/ZG

        # --- Priority 1: LightGBM model inference ---
        # Use getattr to support tests that bypass __init__ via __new__.
        direction_model = getattr(self, "_direction_model", None)
        direction_features = getattr(self, "_direction_features", None)
        if direction_model is not None and direction_features:
            try:
                import numpy as np
                from datetime import datetime, timezone
                import zoneinfo

                now_et = datetime.now(zoneinfo.ZoneInfo("America/New_York"))

                # Build feature vector matching training features
                vix_raw  = self._read_redis("polygon:vix:current", "18.0")
                vvix_raw = self._read_redis("polygon:vvix:current", "120.0")
                vvix_z   = float(self._read_redis("polygon:vvix:z_score", "0.0"))
                rv_20d   = float(self._read_redis("polygon:spx:realized_vol_20d", "15.0") or 15.0)

                vix_val  = float(vix_raw or 18.0)
                vvix_val = float(vvix_raw or 120.0)
                iv_rv    = vix_val / rv_20d if rv_20d > 0 else 1.0

                minutes_from_open = (
                    (now_et.hour * 60 + now_et.minute) - (9 * 60 + 30)
                )
                minutes_to_close = 390 - minutes_from_open

                feature_map = {
                    "return_5m":          float(self._read_redis("polygon:spx:return_5m",  "0.0") or 0.0),
                    "return_30m":         float(self._read_redis("polygon:spx:return_30m", "0.0") or 0.0),
                    "return_1h":          float(self._read_redis("polygon:spx:return_1h",  "0.0") or 0.0),
                    "return_4h":          float(self._read_redis("polygon:spx:return_4h",  "0.0") or 0.0),
                    "overnight_gap":      float(self._read_redis("polygon:spx:overnight_gap", "0.0") or 0.0),
                    "prior_day_return":   float(self._read_redis("polygon:spx:prior_day_return", "0.0") or 0.0),
                    "rsi_14":             float(self._read_redis("polygon:spx:rsi_14", "50.0") or 50.0),
                    "macd_signal":        float(self._read_redis("polygon:spx:macd_signal", "0.0") or 0.0),
                    "bb_pct_b":           float(self._read_redis("polygon:spx:bb_pct_b", "0.5") or 0.5),
                    "minutes_from_open":  float(minutes_from_open),
                    "minutes_to_close":   float(minutes_to_close),
                    "vwap_distance":      float(self._read_redis("polygon:spx:vwap_distance", "0.0") or 0.0),
                    "morning_range":      float(self._read_redis("polygon:spx:morning_range", "0.005") or 0.005),
                    "vix_close":          vix_val,
                    "vix_5d_change":      float(self._read_redis("polygon:vix:5d_change", "0.0") or 0.0),
                    "vix_z_score":        float(self._read_redis("polygon:vix:z_score", "0.0") or 0.0),
                    "vvix_close":         vvix_val,
                    "vvix_z_score":       vvix_z,
                    "rv_20d":             rv_20d,
                    "iv_rv_ratio":        iv_rv,
                    "vix_term_ratio":     float(self._read_redis("polygon:vix9d:current", "18.0") or 18.0) / max(vix_val, 1.0),
                    "hour_sin":           math.sin(2 * math.pi * minutes_from_open / 390),
                    "hour_cos":           math.cos(2 * math.pi * minutes_from_open / 390),
                    "dow_sin":            math.sin(2 * math.pi * now_et.weekday() / 5),
                    "dow_cos":            math.cos(2 * math.pi * now_et.weekday() / 5),
                }

                X = np.array([[feature_map.get(f, 0.0) for f in direction_features]])
                pred_proba = direction_model.predict_proba(X)[0]
                classes = list(direction_model.classes_)

                p_bull    = float(pred_proba[classes.index("bull")])    if "bull"    in classes else 0.35
                p_bear    = float(pred_proba[classes.index("bear")])    if "bear"    in classes else 0.30
                p_neutral = float(pred_proba[classes.index("neutral")]) if "neutral" in classes else 0.35

                direction = max(
                    [("bull", p_bull), ("bear", p_bear), ("neutral", p_neutral)],
                    key=lambda x: x[1],
                )[0]
                confidence = max(p_bull, p_bear, p_neutral)
                signal_weak = abs(p_bull - p_bear) < 0.05

                return {
                    "p_bull":           round(p_bull, 4),
                    "p_bear":           round(p_bear, 4),
                    "p_neutral":        round(p_neutral, 4),
                    "direction":        direction,
                    "confidence":       round(confidence, 4),
                    "expected_move_pts": round(10.0 * (p_bull - p_bear), 2),
                    "expected_move_pct": round(0.002 * (p_bull - p_bear), 6),
                    "signal_weak":      signal_weak,
                    "model_source":     "lgbm_v1",
                }

            except Exception as model_err:
                logger.warning(
                    "direction_model_inference_failed",
                    error=str(model_err),
                )
                # Fall through to GEX/ZG rule-based below

        # --- GEX/ZG-based directional tilt ---
        if (
            flip_zone is not None
            and flip_zone > 0
            and gex_conf >= 0.3
        ):
            dist_pct = (spx_price - flip_zone) / flip_zone
            tilt = 0.15 * math.tanh(dist_pct * 50.0)

            p_bull_raw = 0.50 + tilt
            p_bear_raw = 0.50 - tilt
            p_neutral_raw = 0.12  # small fixed neutral component

            # Overlay CV_Stress: high stress tilts toward bear
            # T-ACT-054: guard with `is not None` as discipline floor.
            # This branch is dormant when LightGBM v1 is loaded but
            # would silently TypeError-skip via outer try/except if
            # the model becomes unavailable. Per HANDOFF A.7 fix all
            # known instances of the silent-failure-class family.
            if cv_stress is not None and cv_stress > 70:
                p_bear_raw += 0.08
                p_bull_raw -= 0.04

            total = p_bull_raw + p_bear_raw + p_neutral_raw
            p_bull = p_bull_raw / total
            p_bear = p_bear_raw / total
            p_neutral = p_neutral_raw / total

        else:
            # --- Fallback: regime-based probabilities (Phase 2 placeholder) ---
            # T-ACT-054: guard with `is not None` as discipline floor
            # (sister to the L1050 patch above). Per HANDOFF A.7.
            if cv_stress is not None and cv_stress > 70:
                p_bull, p_bear, p_neutral = 0.25, 0.35, 0.40
            elif regime in ("quiet_bullish",):
                p_bull, p_bear, p_neutral = 0.45, 0.25, 0.30
            elif regime in ("crisis", "volatile_bearish"):
                p_bull, p_bear, p_neutral = 0.20, 0.50, 0.30
            elif regime in ("pin_range", "range"):
                p_bull, p_bear, p_neutral = 0.35, 0.35, 0.30
            else:
                p_bull, p_bear, p_neutral = 0.35, 0.30, 0.35

            total = p_bull + p_bear + p_neutral
            p_bull /= total
            p_bear /= total
            p_neutral /= total

        direction = max(
            [("bull", p_bull), ("bear", p_bear), ("neutral", p_neutral)],
            key=lambda x: x[1],
        )[0]
        confidence = max(p_bull, p_bear, p_neutral)

        # Signal quality gate: if spread too narrow, flag as weak
        signal_weak = abs(p_bull - p_bear) < 0.05  # 0.05: blocks at <0.3% ZG distance, allows at >0.5%

        return {
            "p_bull": round(p_bull, 4),
            "p_bear": round(p_bear, 4),
            "p_neutral": round(p_neutral, 4),
            "direction": direction,
            "confidence": round(confidence, 4),
            "expected_move_pts": round(10.0 * (p_bull - p_bear), 2),
            "expected_move_pct": round(0.002 * (p_bull - p_bear), 6),
            "signal_weak": signal_weak,
        }

    def _evaluate_no_trade(
        self,
        rcs: float,
        cv_stress: Optional[float],
        vvix_z: float,
        session: dict,
    ) -> tuple:
        """
        Returns (no_trade: bool, reason: Optional[str]).
        Implements D-018 (VVIX), D-022 (capital preservation), RCS gate.

        T-ACT-054: cv_stress is Optional[float] — None when degenerate
        inputs (per _compute_cv_stress NULL contract). The cv_stress
        gate at L1120 below explicitly guards `is not None` and skips
        the no_trade-trigger when the signal is degenerate. Conservative
        choice: do NOT emergency-stop on missing data; keep trading on
        the signals we DO have. Per HANDOFF A.7 silent-failure-class
        family convention.
        """
        if session and session.get("session_status") == "halted":
            return True, "session_halted"

        # D-018: VVIX emergency threshold
        if vvix_z >= 3.0:
            return True, f"vvix_emergency_z_{vvix_z:.2f}"

        # RCS too low
        if rcs < 40:
            return True, f"rcs_too_low_{rcs:.0f}"

        # CV_Stress critical
        # T-ACT-054: guard with `is not None` — under Choice A NULL
        # semantics cv_stress is None when inputs are degenerate. Do
        # NOT trigger emergency no_trade on missing data (conservative:
        # the absence of stress signal is not itself a stress signal).
        # Per HANDOFF A.7 NULL-on-degenerate-input convention.
        if cv_stress is not None and cv_stress > 85:
            return True, f"cv_stress_critical_{cv_stress:.0f}"
        if cv_stress is None:
            logger.debug(
                "cv_stress_no_trade_gate_skipped",
                reason="cv_stress_is_none_degenerate_inputs",
            )

        # D-022: 5 consecutive losses = halt
        if session:
            consecutive = session.get("consecutive_losses_today", 0)
            if consecutive >= 5:
                return True, "capital_preservation_halt_5_losses"

        # IV/RV filter: don't sell premium when implied vol ≤ realized vol.
        # VIX = implied vol proxy. realized_vol_20d = 20-day annualized SPX RV.
        #
        # P-day butterfly safety sprint (Opus 4.7 review 2026-04-20):
        #   threshold raised 1.05 → 1.10 (match tests/docs, real edge band)
        #   added data-warmth guard rv_val >= 5.0 — polygon_feed's current
        #   realized_vol_20d is computed from an intraday 5-min buffer and
        #   emits garbage values (1.05-1.29) while the true 20-day daily
        #   RV builder warms up. Skipping the filter when rv < 5 prevents
        #   false positives against obviously-wrong data.
        try:
            vix_raw = self._read_redis("polygon:vix:current", None)
            rv_raw = self._read_redis("polygon:spx:realized_vol_20d", None)
            if vix_raw is not None and rv_raw is not None:
                vix_val = float(vix_raw)
                rv_val = float(rv_raw)
                if rv_val >= 5.0 and vix_val < rv_val * 1.10:
                    return True, f"iv_rv_cheap_premium_vix{vix_val:.1f}_rv{rv_val:.1f}"
        except (ValueError, TypeError):
            pass  # malformed Redis value — skip filter, don't block trading

        return False, None

    def _compute_phase_a_features(
        self,
        spx_price: Optional[float],
        gex_flip_zone: Optional[float],
    ) -> dict:
        """
        12H Phase A: compute the five additional LightGBM features that
        are persisted on every prediction cycle.

        Fail-open convention:
          - prior_session_return, spx_momentum_4h, earnings_proximity_score:
            default to 0.0 when their Redis key is absent. Those keys are
            set to the literal string "0" during warmup and normal flat
            sessions, so 0 is a valid domain value — not a missing signal.
          - vix_term_ratio, gex_flip_proximity: return None when either
            input is missing or malformed. These signals are either
            well-defined or not at all; persisting a fabricated value
            (e.g. 1.0 or 0) would teach the future model a phantom signal
            during any feed gap, corrupting walk-forward backtests.
            LightGBM handles NULL natively via its own missing-split.
        """
        prior_session_return = _safe_float(
            self._read_redis("polygon:spx:prior_day_return", None), 0.0
        )
        spx_momentum_4h = _safe_float(
            self._read_redis("polygon:spx:return_4h", None), 0.0
        )
        earnings_proximity_score = _safe_float(
            self._read_redis("calendar:earnings_proximity_score", None),
            0.0,
        )

        vix_raw = self._read_redis("polygon:vix:current", None)
        vix9d_raw = self._read_redis("polygon:vix9d:current", None)
        vix_term_ratio: Optional[float] = None
        if vix_raw is not None and vix9d_raw is not None:
            try:
                v_cur = float(vix_raw)
                v_9d = float(vix9d_raw)
                if v_cur > 0:
                    vix_term_ratio = round(v_9d / v_cur, 4)
            except (ValueError, TypeError):
                vix_term_ratio = None

        gex_flip_proximity: Optional[float] = None
        if (
            gex_flip_zone is not None
            and spx_price is not None
            and spx_price > 0
        ):
            gex_flip_proximity = round(
                abs(gex_flip_zone - spx_price) / spx_price, 6
            )

        return {
            "prior_session_return": round(prior_session_return, 6),
            "vix_term_ratio": vix_term_ratio,
            "spx_momentum_4h": round(spx_momentum_4h, 6),
            "gex_flip_proximity": gex_flip_proximity,
            "earnings_proximity_score": round(
                earnings_proximity_score, 4
            ),
        }

    def run_cycle(self) -> Optional[dict]:
        """Run one prediction cycle. Writes to trading_prediction_outputs."""
        try:
            # Guard: check Redis availability before running on potentially stale data
            redis_available = False
            if self.redis_client:
                try:
                    self.redis_client.ping()
                    redis_available = True
                except Exception:
                    redis_available = False

            if not redis_available:
                logger.warning("prediction_cycle_skipped_redis_unavailable")
                return {
                    "no_trade_signal": True,
                    "no_trade_reason": "redis_unavailable",
                    "regime": "unknown",
                    "rcs": 0.0,
                    "allocation_tier": "danger",
                    "spx_price": 5200.0,
                }

            # T2-4: gate the cycle on RTH (9:30 AM - 4:00 PM ET).
            # Scheduler fires at minute="*/5" from hour 9, which means
            # the 9:00, 9:05, 9:10, 9:15, 9:20, 9:25 fires land BEFORE
            # the market is open. At those minutes Polygon /v3/snapshot
            # has stale last-session data and Tradier quotes reflect
            # pre-market thin microstructure — the resulting prediction
            # rows pollute the outcome-labeling and drift-detection
            # pipelines. Post-16:00 fires (there is no cron for them
            # today, but market_calendar also returns False on holidays
            # and early-close afternoons) are suppressed for the same
            # reason.
            #
            # Import is method-local so that (a) the circular-import
            # risk with market_calendar stays contained, (b) the entire
            # block fails OPEN on any calendar error — a broken import
            # must never silently stop trading during a real session.
            try:
                from market_calendar import is_market_open
                if not is_market_open():
                    logger.debug("prediction_cycle_skipped_market_closed")
                    self._write_heartbeat()
                    return None
            except Exception:
                # Fail open — cycle proceeds if calendar check fails.
                pass

            self._cycle_count += 1
            session = get_today_session()
            if not session:
                logger.warning("prediction_cycle_no_session")
                self._write_heartbeat()
                return None

            # Read VVIX context
            vvix_z_raw = self._read_redis("polygon:vvix:z_score", None)
            gex_conf_raw = self._read_redis("gex:confidence", None)

            # If all feed signals are unavailable, don't trade on defaults
            if vvix_z_raw is None and gex_conf_raw is None:
                logger.info(
                    "prediction_cycle_skipped_no_feed_data",
                    reason="vvix_z and gex_confidence both unavailable",
                )
                return {
                    "no_trade_signal": True,
                    "no_trade_reason": "feed_data_unavailable",
                    "regime": "unknown",
                    "rcs": 0.0,
                    "allocation_tier": "danger",
                    "spx_price": self._get_spx_price(),
                }

            # 2026-05-01 SPX-real-time-feed freshness guard: refuse to
            # make trade decisions on stale SPX data. polygon_feed.py
            # writes polygon:spx:current every 5 min (poll cadence); the
            # threshold of 330s = 1 poll period + 30s slack. If the key
            # is missing or older than 330s, the system has fallen back
            # to Tradier sandbox (15-min delayed per 2026-05-01 empirical
            # verification) and the better default is to skip the cycle
            # rather than enter a position on stale data. MTM (separate
            # 1-min cadence) does NOT apply this guard — open positions
            # still need repricing even when the feed degrades; the
            # _get_spx_price() Tradier fallback handles that case.
            import json as _json
            spx_fresh = False
            try:
                spx_raw = self._read_redis("polygon:spx:current", None)
                if spx_raw:
                    spx_meta = _json.loads(spx_raw)
                    # 2026-05-03 silent-staleness fix (T-ACT-046,
                    # observability amendment per F6): explicitly handle
                    # the new contract that polygon_feed.py may write
                    # `fetched_at: null` when the upstream Polygon
                    # response lacked a quote-time field. The prior
                    # behaviour (relying on the outer try/except to
                    # convert None into a generic spx_freshness_check_
                    # failed log) was correct-but-noisy. Surfacing the
                    # missing-upstream-timestamp case with a distinct
                    # log makes the silent-failure-class family
                    # convention (HANDOFF A.7) explicit at the consumer.
                    fetched_at_raw = spx_meta.get("fetched_at")
                    fetched_at_source = spx_meta.get(
                        "fetched_at_source", "unknown"
                    )
                    if fetched_at_raw is None:
                        logger.warning(
                            "spx_price_upstream_timestamp_missing",
                            source=fetched_at_source,
                        )
                        # spx_fresh remains False — conservative skip.
                    else:
                        fetched_at = datetime.fromisoformat(fetched_at_raw)
                        age_seconds = (
                            datetime.now(timezone.utc) - fetched_at
                        ).total_seconds()
                        if age_seconds <= 330:
                            spx_fresh = True
                        else:
                            logger.warning(
                                "spx_price_stale",
                                age_seconds=round(age_seconds, 1),
                                source="polygon",
                                threshold_seconds=330,
                            )
            except Exception as fresh_err:
                logger.warning(
                    "spx_freshness_check_failed",
                    error=str(fresh_err),
                )

            if not spx_fresh:
                logger.info(
                    "cycle_skipped",
                    reason="spx_price_stale_or_unavailable",
                    service_name="main",
                )
                return {
                    "no_trade_signal": True,
                    "no_trade_reason": "spx_price_stale_or_unavailable",
                    "regime": "unknown",
                    "rcs": 0.0,
                    "allocation_tier": "danger",
                    "spx_price": self._get_spx_price(),
                }

            try:
                vvix = float(self._read_redis("polygon:vvix:current", "0.0"))
                vvix_z = float(vvix_z_raw) if vvix_z_raw is not None else 0.0
            except (ValueError, TypeError):
                vvix, vvix_z = 0.0, 0.0

            # Compute all layers
            regime_data = self._compute_regime()
            cv_data = self._compute_cv_stress()
            direction_data = self._compute_direction(
                regime_data["regime"],
                cv_data["cv_stress_score"],
                spx_price=self._get_spx_price(),
                flip_zone=regime_data.get("gex_flip_zone_used"),
                gex_conf=regime_data.get("gex_conf_at_regime", 0.0),
            )

            # Section 13 Batch 2: renamed from inline `_safe_float` to
            # `_read_float_key` to eliminate a name collision with the
            # module-level `_safe_float(value, default)` helper at the
            # top of this file. Both signatures survived side-by-side
            # only because Python scope rules kept them separate — but
            # any refactor that inlined phase_a_features into run_cycle
            # would have silently broken.
            def _read_float_key(key, default=0.0):
                try:
                    return float(self._read_redis(key, str(default)))
                except (ValueError, TypeError):
                    return default

            gex_net = _read_float_key("gex:net")
            gex_nearest_wall = _read_float_key("gex:nearest_wall") or None
            gex_flip_zone = _read_float_key("gex:flip_zone") or None
            gex_confidence = _read_float_key("gex:confidence")

            # D-022: capital preservation mode flag
            consecutive = session.get("consecutive_losses_today", 0)
            cap_pres = consecutive >= 3

            # No-trade evaluation
            no_trade, no_trade_reason = self._evaluate_no_trade(
                regime_data["rcs"],
                cv_data["cv_stress_score"],
                vvix_z,
                session,
            )

            # Signal quality gate: weak directional signal → no trade
            if not no_trade and direction_data.get("signal_weak"):
                no_trade = True
                no_trade_reason = "direction_signal_weak"

            # ── 12H (Phase A): additional LightGBM features ─────────────
            # Persist five extra features to trading_prediction_outputs
            # now, so by the time we have 90+ labeled sessions (auto-gate
            # in train_direction_model.py) we already have a full column
            # of training data — no backfill needed. Logic lives in
            # _compute_phase_a_features() to keep run_cycle() readable
            # and the new feature surface independently unit-testable.
            #
            # NOTE: `_read_float_key` is the INLINE helper defined at
            # the top of this try-block (signature: key, default).
            # Section 13 Batch 2 renamed it from `_safe_float` to stop
            # shadowing the module-level `_safe_float(value, default)`.
            spx_price = self._get_spx_price()
            vix_live = _read_float_key("polygon:vix:current", 18.0)
            phase_a_features = self._compute_phase_a_features(
                spx_price=spx_price,
                gex_flip_zone=gex_flip_zone,
            )

            output = {
                "session_id": session["id"],
                "predicted_at": datetime.now(timezone.utc).isoformat(),
                **direction_data,
                "gex_net": gex_net,
                "gex_nearest_wall": gex_nearest_wall,
                "gex_flip_zone": gex_flip_zone,
                "gex_confidence": round(gex_confidence, 4),
                **cv_data,
                **regime_data,
                "spx_price": spx_price,
                # S4 / E-5: prefer the live VIX from polygon_feed
                # (polygon:vix:current). Falls back to 18.0 only when
                # Redis is empty or the value is malformed — the prior
                # hardcode meant every persisted prediction row
                # reported a constant VIX regardless of actual market
                # state, breaking downstream backtests and analytics.
                "vix": vix_live,
                "vvix": vvix,
                "vvix_z_score": round(vvix_z, 3),
                "no_trade_signal": no_trade,
                "no_trade_reason": no_trade_reason,
                "capital_preservation_mode": cap_pres,
                "execution_degraded": False,
                # 12H Phase A features (see _compute_phase_a_features).
                **phase_a_features,
            }

            result = (
                get_client()
                .table("trading_prediction_outputs")
                .insert(output)
                .execute()
            )

            if no_trade:
                write_audit_log(
                    action="trading.no_trade_signal",
                    metadata={
                        "reason": no_trade_reason,
                        "rcs": regime_data["rcs"],
                        "cv_stress": cv_data["cv_stress_score"],
                    },
                )
                logger.info("no_trade_signal", reason=no_trade_reason)
            else:
                logger.info(
                    "prediction_cycle_complete",
                    direction=direction_data["direction"],
                    confidence=direction_data["confidence"],
                    regime=regime_data["regime"],
                    rcs=regime_data["rcs"],
                    cv_stress=cv_data["cv_stress_score"],
                )

            self._write_heartbeat()
            return result.data[0] if result.data else output

        except Exception as e:
            logger.error("prediction_cycle_failed", error=str(e), exc_info=True)
            write_health_status(
                "prediction_engine",
                "error",
                last_error_message=str(e),
            )
            return None

    def _write_heartbeat(self) -> None:
        write_health_status(
            "prediction_engine",
            "healthy",
            is_market_hours=_is_market_hours(),
        )
