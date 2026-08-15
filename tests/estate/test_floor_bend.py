"""The estate floor bend must stay bent (bead gage-ifx4i).

Upstream hermes-agent reads the Anthropic subscription credential Claude Code owns
-- from the macOS Keychain and from ~/.claude/.credentials.json -- refreshes it,
writes it back, and talks to Anthropic wearing a `claude-code/<ver> (external, cli)`
user-agent. CONSTITUTION section 4 forbids routing a subscription through a
third-party harness, and Anthropic bans accounts for it.

Upstream's only guard was `provider == "anthropic"`, which is one config edit away
from firing, so the estate deleted the bodies instead. These tests fail if a rebase
onto upstream ever restores them.

Runs standalone (`python3 tests/estate/test_floor_bend.py`) as well as under pytest.
"""

from __future__ import annotations

import ast
import inspect
import json
import subprocess
from pathlib import Path

from agent import anthropic_adapter as aa


def test_keychain_reader_is_severed(tmp_path=None):
    """The macOS Keychain reader must return None and never shell out."""
    called = []
    real_run = subprocess.run
    aa.subprocess.run = lambda *a, **k: called.append(a) or real_run(["true"])
    try:
        assert aa._read_claude_code_credentials_from_keychain() is None
    finally:
        aa.subprocess.run = real_run
    assert not called, "severed keychain reader still shelled out to a subprocess"


def test_credentials_file_reader_is_severed(tmp_path=None):
    """The file reader must return None even when a real-looking file exists."""
    assert aa._read_claude_code_credentials_from_file() is None


def test_choke_point_is_severed(tmp_path=None):
    """The single function every caller used must return None."""
    assert aa.read_claude_code_credentials() is None


def test_writeback_never_touches_claude_code(tmp_path=None):
    """Upstream rewrote ~/.claude/.credentials.json. Ours must be a no-op."""
    real = Path.home() / ".claude" / ".credentials.json"
    before = real.stat().st_mtime_ns if real.exists() else None

    assert aa._write_claude_code_credentials("x", "y", 0) is None

    after = real.stat().st_mtime_ns if real.exists() else None
    assert before == after, "the bend wrote to Claude Code's real credential file"


def _live_string_literals() -> list:
    """Every string constant in the adapter that is NOT a docstring.

    Scanning raw source text is wrong here: our own stubs describe the deleted
    upstream behaviour in their docstrings, which a plain substring match reads as
    the behaviour itself. Comments never enter the AST, and docstrings are dropped
    explicitly, so what remains is only string data real code would use.
    """
    tree = ast.parse(inspect.getsource(aa))
    docstrings = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                    and isinstance(first.value.value, str):
                docstrings.add(id(first.value))
    return [
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
    ]


def test_no_credential_reading_source_remains(tmp_path=None):
    """No severed body may come back via a rebase."""
    live = _live_string_literals()
    for banned in ("find-generic-password", "claudeAiOauth", "Claude Code-credentials"):
        hits = [s for s in live if banned in s]
        assert not hits, f"live code referencing {banned!r} is back: {hits}"


def test_user_agent_does_not_impersonate_claude_code(tmp_path=None):
    """We must identify as HermesAgent, never as the official CLI."""
    hits = [s for s in _live_string_literals() if "claude-code/" in s]
    assert not hits, f"claude-code user-agent impersonation is back: {hits}"


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed}/6 floor-bend guards passed")
