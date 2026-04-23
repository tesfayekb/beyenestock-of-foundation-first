"""
Deployment-config guard: nixpacks.toml MUST live at the repository
root, not inside backend/.

Why this matters — on 2026-04-20 the Railway container was being
built with Root Directory = /backend (Railway's "Root Directory"
setting determines which subtree is copied into the container).
Because backend_agents/ and backend_earnings/ are siblings of
backend/ (not children), they never entered the container and
every import of flow_agent / synthesis_agent / feedback_agent /
main_earnings raised ModuleNotFoundError at runtime. The health-
write fix in commit fd34c3c surfaced this by correctly reporting
those failures to Supabase — they had been silent before.

The infra fix (commit ships with this test) is to move
nixpacks.toml to the repo root and change Railway Root Directory
to / so the whole repo (backend/, backend_agents/, backend_earnings/,
common/, ...) enters the container. These tests pin that layout so
a future refactor cannot silently drift nixpacks.toml back inside
backend/ and re-break every agent job.
"""
import os


REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def test_nixpacks_at_repo_root():
    """nixpacks.toml MUST exist at the repository root."""
    root_nixpacks = os.path.join(REPO_ROOT, "nixpacks.toml")
    assert os.path.isfile(root_nixpacks), (
        f"nixpacks.toml not found at repo root ({root_nixpacks}). "
        f"Railway needs this file at the root so Root Directory can "
        f"be '/' and backend_agents/ + backend_earnings/ enter the "
        f"container as siblings of backend/. See commit history for "
        f"the 2026-04-20 'No module named flow_agent' incident."
    )


def test_nixpacks_not_inside_backend():
    """nixpacks.toml MUST NOT exist inside backend/ — prevents the
    file from drifting back to the pre-fix location (which caused
    Railway Root Directory to be /backend and dropped the sibling
    directories from the container)."""
    bad_nixpacks = os.path.join(REPO_ROOT, "backend", "nixpacks.toml")
    assert not os.path.exists(bad_nixpacks), (
        f"nixpacks.toml must not live at {bad_nixpacks}. When it does, "
        f"Railway's Root Directory autodetect trends toward /backend, "
        f"which excludes backend_agents/ and backend_earnings/ from "
        f"the container and causes ModuleNotFoundError at runtime. "
        f"Keep nixpacks.toml at the repo root."
    )


def test_nixpacks_forces_python_provider():
    """The root-level nixpacks.toml MUST declare `providers = ["python"]`
    at the top level so Nixpacks skips auto-detection. Without this,
    the frontend `package.json` at the repo root causes Nixpacks to
    detect the project as Node and attempt to build with bun/npm
    instead of pip — the Python backend never boots.

    Uses a whitespace-tolerant regex (not a literal string search) so
    this still passes if someone reformats the file with extra spaces
    around `=` or uses single-quoted strings in TOML (both valid).
    """
    import re
    root_nixpacks = os.path.join(REPO_ROOT, "nixpacks.toml")
    with open(root_nixpacks, "r", encoding="utf-8") as f:
        contents = f.read()
    pattern = re.compile(
        r'^\s*providers\s*=\s*\[\s*["\']python["\']\s*\]\s*$',
        re.MULTILINE,
    )
    assert pattern.search(contents), (
        "nixpacks.toml must declare `providers = [\"python\"]` at the "
        "top level to force the Python provider and skip Node/Bun "
        "auto-detection. Without this line, the frontend package.json "
        "at the repo root causes Nixpacks to build a Node image and "
        "the Python backend never starts."
    )


def test_nixpacks_install_references_backend_requirements():
    """The install command in the root-level nixpacks.toml MUST
    reference 'backend/requirements.txt' (not 'requirements.txt'),
    because when Root Directory = / the build cwd is the repo root,
    not backend/.

    Bare `pip install ...` (not `python -m pip install`) is the
    correct form here: Railway's default builder is Railpack, and
    Railpack's Python provider puts pip on PATH at the build-phase
    shell level. Legacy Nixpacks v1 does NOT, but the service is
    pinned to RAILPACK in railway.json so that code path is not
    taken. If a future operator switches the builder back to
    NIXPACKS (legacy) in railway.json, this file must also change
    to `python -m pip install ...` — guard test for that is
    deliberately not added because the builder pin is the stronger
    invariant.
    """
    root_nixpacks = os.path.join(REPO_ROOT, "nixpacks.toml")
    with open(root_nixpacks, "r", encoding="utf-8") as f:
        contents = f.read()
    assert "backend/requirements.txt" in contents, (
        "nixpacks.toml [phases.install] must `pip install -r "
        "backend/requirements.txt` — bare `requirements.txt` only "
        "worked when Root Directory was /backend."
    )


def test_nixpacks_start_cds_into_backend():
    """The start command MUST `cd backend` before launching uvicorn
    so that main.py's `os.path.dirname(__file__)` resolves to
    /app/backend and the abspath agent-path pattern produces
    /app/backend_agents (not /app/backend_agents/backend_agents)."""
    root_nixpacks = os.path.join(REPO_ROOT, "nixpacks.toml")
    with open(root_nixpacks, "r", encoding="utf-8") as f:
        contents = f.read()
    assert "cd backend" in contents and "uvicorn main:app" in contents, (
        "nixpacks.toml [start] cmd must `cd backend && uvicorn "
        "main:app ...` — running uvicorn from the repo root would "
        "import a different module path and break the sibling-dir "
        "abspath pattern in main.py."
    )
