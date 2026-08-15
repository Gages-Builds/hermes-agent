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


def test_no_credential_reading_source_remains(tmp_path=None):
    """No severed body may come back via a rebase: check the source text itself."""
    src = inspect.getsource(aa)
    for banned in ("find-generic-password", "claudeAiOauth"):
        live = [
            ln for ln in src.splitlines()
            if banned in ln and not ln.strip().startswith("#") and '"""' not in ln
        ]
        assert not live, f"live code referencing {banned!r} is back: {live}"


def test_user_agent_does_not_impersonate_claude_code(tmp_path=None):
    """We must identify as HermesAgent, never as the official CLI."""
    src = inspect.getsource(aa)
    live = [
        ln for ln in src.splitlines()
        if "claude-code/" in ln and "user-agent" in ln.lower()
        and not ln.strip().startswith("#")
    ]
    assert not live, f"claude-code user-agent impersonation is back: {live}"


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed}/6 floor-bend guards passed")
