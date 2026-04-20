"""
Infrastructure guard: every place backend/main.py constructs a
filesystem path ending in "backend_agents" (or "backend_earnings")
for injection into sys.path must wrap it in os.path.abspath(), and
every sys.path.insert(0, ...) of such a path must be guarded by a
`... not in sys.path` membership check.

Why this matters — e417113 fixed a production bug on Railway where
_run_earnings_* jobs prepended a relative path
("backend/../backend_earnings") to sys.path. On Railway __file__ can
resolve relatively and the scheduler invokes jobs from a worker
thread whose cwd is not guaranteed to be /app/backend, so the
relative entry sometimes failed to locate the target module and the
earnings scheduler errored every 15 minutes. The 2026-04-22 audit
(this commit) found 6 agent call sites that had never received the
e417113 treatment. The canonical fix is:

    _AGENTS_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "backend_agents")
    )
    if _AGENTS_PATH not in sys.path:
        sys.path.insert(0, _AGENTS_PATH)

These tests parse main.py with `ast` (not a naive grep) so that
string mentions of "backend_agents" in comments / docstrings don't
false-positive.
"""
import ast
import os
import re


MAIN_PY = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "main.py")
)

_AGENT_PKG_NAMES = ("backend_agents", "backend_earnings")


def _parent_map(tree: ast.AST) -> dict:
    """Build a child-id → parent map so we can ask "is this
    os.path.join wrapped in os.path.abspath?" without ast giving
    us parent pointers for free."""
    parents: dict = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _is_os_path_call(node: ast.AST, attr: str) -> bool:
    """True when `node` is exactly `os.path.<attr>(...)`."""
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    return (
        isinstance(f, ast.Attribute)
        and f.attr == attr
        and isinstance(f.value, ast.Attribute)
        and f.value.attr == "path"
        and isinstance(f.value.value, ast.Name)
        and f.value.value.id == "os"
    )


def _find_agent_joins(tree: ast.AST) -> list:
    """Return every os.path.join() Call node whose arg list
    contains a string literal from _AGENT_PKG_NAMES."""
    joins = []
    for node in ast.walk(tree):
        if not _is_os_path_call(node, "join"):
            continue
        has_agent_arg = any(
            isinstance(a, ast.Constant)
            and isinstance(a.value, str)
            and a.value in _AGENT_PKG_NAMES
            for a in node.args
        )
        if has_agent_arg:
            joins.append(node)
    return joins


def test_all_agent_paths_use_abspath():
    """Every `os.path.join(..., "backend_agents"|"backend_earnings")`
    in main.py must be the direct argument to an `os.path.abspath`
    call. Regression guard for the e417113 Railway-cwd bug and the
    2026-04-22 audit of the six remaining unfixed agent jobs."""
    with open(MAIN_PY, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    parents = _parent_map(tree)

    joins = _find_agent_joins(tree)
    # Pin the count: if a future refactor silently drops one of
    # these call sites the number changes and review sees it.
    assert len(joins) >= 8, (
        f"expected at least 8 os.path.join(..., <agent_pkg>) sites in "
        f"main.py (2 economic_calendar + 6 agents/earnings each); "
        f"found {len(joins)}"
    )

    violations = []
    for call in joins:
        parent = parents.get(id(call))
        if not _is_os_path_call(parent, "abspath"):
            src = ast.unparse(call)
            violations.append((call.lineno, src))

    assert not violations, (
        "os.path.join(..., <agent_pkg>) NOT wrapped in os.path.abspath — "
        "this is the Railway-cwd bug fixed in e417113. Wrap the join "
        "in os.path.abspath(...) and guard the sys.path.insert with "
        "`if path not in sys.path`. Violations:\n"
        + "\n".join(f"  line {ln}: {src}" for ln, src in violations)
    )


def test_all_agent_paths_are_guarded():
    """Every `sys.path.insert(0, _AGENTS_PATH)` or
    `sys.path.insert(0, _EARNINGS_PATH)` must be preceded by a
    `... not in sys.path` membership check in the 4 lines above.
    Prevents the same path being prepended on every scheduler
    tick — a slow-motion memory leak in long-running processes
    and the second half of the e417113 fix."""
    with open(MAIN_PY, "r", encoding="utf-8") as f:
        lines = f.readlines()

    insert_pattern = re.compile(
        r"(?:_?sys)\.path\.insert\s*\(\s*0\s*,\s*"
        r"(_AGENTS_PATH|_EARNINGS_PATH)\s*\)"
    )
    # Accept either `not in sys.path` or the aliased `not in _sys.path`
    # — one call site uses `import sys as _sys` to avoid shadowing a
    # surrounding function's `sys` binding.
    guard_pattern = re.compile(r"not in (?:_?sys)\.path")

    insert_lines = [
        i for i, line in enumerate(lines) if insert_pattern.search(line)
    ]
    assert insert_lines, (
        "no guarded sys.path.insert(0, _AGENTS_PATH) / _EARNINGS_PATH) "
        "sites found in main.py — did the canonical pattern get "
        "refactored away?"
    )

    unguarded = []
    for i in insert_lines:
        window = "".join(lines[max(0, i - 4):i])
        if not guard_pattern.search(window):
            unguarded.append((i + 1, lines[i].rstrip()))

    assert not unguarded, (
        "sys.path.insert site(s) missing the `if ... not in sys.path` "
        "guard within 4 lines above:\n"
        + "\n".join(f"  line {ln}: {src}" for ln, src in unguarded)
    )


def test_no_raw_relative_agent_insert():
    """Belt-and-braces: assert no line in main.py still uses the
    old unfixed pattern `sys.path.insert(0, os.path.join(...))`
    with a literal agent-package name. This catches a future
    refactor that reintroduces the raw relative path but happens
    to also define an unused _AGENTS_PATH above it, which the
    abspath test could miss if the dead variable were ever
    added."""
    with open(MAIN_PY, "r", encoding="utf-8") as f:
        source = f.read()
    bad_pattern = re.compile(
        r"sys\.path\.insert\s*\([^)]*os\.path\.join\s*\([^)]*"
        r"(backend_agents|backend_earnings)"
    )
    m = bad_pattern.search(source)
    assert not m, (
        f"found raw `sys.path.insert(0, os.path.join(... <agent>))` "
        f"pattern at offset {m.start() if m else '?'} — this is the "
        f"pre-e417113 bug. Use the _AGENTS_PATH / _EARNINGS_PATH "
        f"variable pattern with os.path.abspath instead."
    )
