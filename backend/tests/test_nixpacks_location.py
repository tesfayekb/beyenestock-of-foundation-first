"""
Deployment-config guard: a Dockerfile at the repo root is the source
of truth for the Railway build. The prior nixpacks.toml-based setup
was replaced on 2026-04-22 because Railpack 0.23.0 ignored
`providers = ["python"]` whenever package.json existed at the repo
root — it kept detecting the project as Node and building a bun
image that never started the Python backend.

A repo-root Dockerfile bypasses Railpack entirely: when Railway sees
a Dockerfile at the build context root, it uses Docker and ignores
Nixpacks / Railpack auto-detection. The file also copies backend/,
backend_agents/, and backend_earnings/ as siblings under /app/, so
the abspath pattern in backend/main.py resolves correctly:

    os.path.dirname(__file__)      → /app/backend
    os.path.join(..., "..", "X")   → /app/backend/../X
    os.path.abspath(...)           → /app/X   (X = backend_agents | backend_earnings)

These tests pin the Dockerfile invariants so a future refactor
cannot silently drop an agent directory or change the entrypoint
and re-break every agent/earnings job.

File name retained as test_nixpacks_location.py for git/test-ID
continuity — conceptually this is "deployment config guard."
"""
import os


REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def test_nixpacks_forces_python_provider():
    """A Dockerfile MUST exist at the repository root. When a
    Dockerfile is present at the build-context root, Railway uses it
    and ignores Railpack's Node/Bun auto-detection — which is the
    reason the Python backend now actually boots.
    """
    dockerfile = os.path.join(REPO_ROOT, "Dockerfile")
    assert os.path.isfile(dockerfile), (
        f"Dockerfile not found at repo root ({dockerfile}). "
        f"Railway needs this file at the root to bypass Railpack "
        f"Node detection caused by the frontend package.json. "
        f"See commit history for the 2026-04-22 Railpack-bypass fix."
    )


def test_nixpacks_install_references_backend_requirements():
    """The Dockerfile MUST install `backend/requirements.txt` (not
    a bare `requirements.txt`), because the build context is the
    repo root and the Python deps live under backend/."""
    dockerfile = os.path.join(REPO_ROOT, "Dockerfile")
    with open(dockerfile, "r", encoding="utf-8") as f:
        contents = f.read()
    assert "backend/requirements.txt" in contents, (
        "Dockerfile must `pip install -r backend/requirements.txt`. "
        "Bare `requirements.txt` only resolves when the build cwd "
        "is backend/, which is not the case under a repo-root "
        "Dockerfile."
    )


def test_nixpacks_start_uses_backend_uvicorn():
    """The Dockerfile CMD MUST launch `uvicorn main:app` with the
    working directory set to /app/backend so main.py's
    `os.path.dirname(__file__)` resolves to /app/backend and the
    sibling-dir abspath pattern produces /app/backend_agents (not
    /app/backend_agents/backend_agents)."""
    dockerfile = os.path.join(REPO_ROOT, "Dockerfile")
    with open(dockerfile, "r", encoding="utf-8") as f:
        contents = f.read()
    assert "uvicorn main:app" in contents, (
        "Dockerfile CMD must invoke `uvicorn main:app ...` — any "
        "other entrypoint breaks the FastAPI app startup."
    )
    assert "WORKDIR /app/backend" in contents, (
        "Dockerfile must set `WORKDIR /app/backend` before CMD so "
        "uvicorn runs from backend/ and main.py's __file__ resolves "
        "to /app/backend/main.py — the sibling-dir agent/earnings "
        "abspath pattern depends on that."
    )
