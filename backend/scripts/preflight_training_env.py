"""
Pre-flight: validate training environment library versions match
``backend/requirements.txt`` for every pickle-critical library
(T-ACT-044 / Fix PR 5).

Why this exists
---------------
Pickled ML artifacts (e.g. ``direction_lgbm_v1.pkl``) have transitive
runtime dependencies on EVERY library whose objects appear in the
pickled object graph, not just the headline ML library. For an
``LGBMClassifier`` pickle, that's at least:
  - ``lightgbm`` (Booster state)
  - ``scikit-learn`` (auto-created LabelEncoder when fit on string
    labels — see ``train_direction_model.py`` L394-396)
  - ``numpy`` (``classes_``, ``feature_importances_``, internal
    buffers)
  - ``scipy`` (transitively used by sklearn internals)
  - ``pandas`` (used in feature engineering; not directly in the
    pickle but pin-tracked for forensic visibility)

Train-vs-prod version skew on any of these can cause silent
``InconsistentVersionWarning`` (sklearn) or hard pickle-load failures
(numpy major-version drift). T-ACT-044 was triggered by exactly this
class of bug: PR 2 Stage 0 instructed a freelance
``pip install lightgbm pandas pyarrow`` (no version pins) which
resolved to libraries 1+ year ahead of production.

Usage (operator, before every training session)
-----------------------------------------------
    cd backend
    python -m scripts.preflight_training_env

Exit codes:
  0  — all pickle-critical libraries match requirements.txt exactly
  1  — at least one library mismatches; itemized diff printed.
       Operator must fix the venv before running
       ``train_direction_model.py``. Recommended fix: create a fresh
       venv and ``pip install`` each library with the exact pin.

Coupling
--------
Update ``PICKLE_CRITICAL`` whenever:
  - A new pickle-critical library is added to the model artifact's
    object graph.
  - ``train_direction_model.py`` adds new imports of libraries whose
    state could leak into the pickle.

This script is intentionally STANDALONE (not auto-invoked from
``train_direction_model.py``) so emergency-override remains possible
if the preflight logic itself ever has a bug — operator can skip it
deliberately rather than being forced through.
"""
import re
import sys
from importlib.metadata import version as _pkg_version, PackageNotFoundError
from pathlib import Path

PICKLE_CRITICAL = (
    "scikit-learn",
    "numpy",
    "pandas",
    "scipy",
    "lightgbm",
)

REQUIREMENTS_PATH = Path(__file__).resolve().parent.parent / "requirements.txt"


def _parse_exact_pins(req_path: Path) -> dict:
    """
    Extract `pkg==X.Y.Z` exact pins from requirements.txt.

    Range pins (``>=``, ``<``, etc.) and unpinned entries are
    intentionally NOT collected — for pickle-critical libraries we
    REQUIRE exact pins (T-ACT-044 lessons-learned A.3). A range pin
    on a pickle-critical library is itself a defect surfaced by
    this preflight.
    """
    pins = {}
    pattern = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([^\s;,]+)")
    for raw_line in req_path.read_text().splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            pkg = match.group(1).lower()
            pins[pkg] = match.group(2).strip()
    return pins


def _installed_version(pkg: str) -> str:
    try:
        return _pkg_version(pkg)
    except PackageNotFoundError:
        return "<not installed>"


def main() -> int:
    if not REQUIREMENTS_PATH.exists():
        print(
            f"PREFLIGHT ERROR: requirements.txt not found at "
            f"{REQUIREMENTS_PATH}. Run this script from a checkout of "
            "the repo with backend/ accessible.",
            file=sys.stderr,
        )
        return 1

    pinned = _parse_exact_pins(REQUIREMENTS_PATH)

    mismatches = []
    matches = []
    for pkg in PICKLE_CRITICAL:
        installed = _installed_version(pkg)
        expected = pinned.get(pkg)
        if expected is None:
            mismatches.append(
                f"  UNPINNED   {pkg:15s} installed={installed:12s} "
                f"(no exact pin in requirements.txt — pickle-critical "
                f"libraries MUST be exact-pinned per T-ACT-044 A.3)"
            )
        elif installed != expected:
            mismatches.append(
                f"  SKEW       {pkg:15s} installed={installed:12s} "
                f"expected={expected}"
            )
        else:
            matches.append(
                f"  OK         {pkg:15s} {installed}"
            )

    print("Preflight: pickle-critical training environment vs "
          f"{REQUIREMENTS_PATH.name}")
    print("-" * 72)
    for line in matches:
        print(line)
    for line in mismatches:
        print(line)
    print("-" * 72)

    if mismatches:
        print(
            f"PREFLIGHT FAILED — {len(mismatches)} pickle-critical "
            f"mismatch(es) detected.\n"
            "Fix: create a fresh venv and run\n"
            "    pip install \\\n"
            + "".join(
                f"      \"{pkg}=={pinned.get(pkg, '<add pin to requirements.txt first>')}\" \\\n"
                for pkg in PICKLE_CRITICAL
            )
            + "  (drop the trailing backslash on the last line)\n"
            "Then re-run this preflight before training.",
            file=sys.stderr,
        )
        return 1

    print(
        f"PREFLIGHT PASSED — all {len(PICKLE_CRITICAL)} pickle-critical "
        "libraries match requirements.txt exactly. Safe to train."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
