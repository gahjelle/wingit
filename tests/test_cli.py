"""CLI-boundary tests: usage errors, entry points, and the harness-not-found path."""

import sys
from importlib import metadata
from pathlib import Path

import pytest
from conftest import RecordedRunner

import wingit
from wingit import core
from wingit.harnesses.claude import ClaudeDriver
from wingit.runner import SubprocessRunner
from wingit.schemas import Run


def test_missing_prompt_is_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that invoking with no prompt exits 2 (usage error, not a failure)."""
    monkeypatch.setattr(sys, "argv", ["a"])

    with pytest.raises(SystemExit) as excinfo:
        wingit.main()

    assert excinfo.value.code == 2


def test_both_console_scripts_point_at_main() -> None:
    """Test that the `a` and `wingit` entry points both resolve to `main`."""
    scripts = metadata.entry_points(group="console_scripts")
    resolved = {ep.name: ep.load() for ep in scripts if ep.name in {"a", "wingit"}}

    assert resolved == {"a": wingit.main, "wingit": wingit.main}


def test_missing_harness_binary_is_clean_failure() -> None:
    """Test that a harness missing from PATH exits 1 with a clean message."""
    result = SubprocessRunner().run(["wingit-no-such-harness-xyz"], cwd=Path.cwd())

    assert result.exit_code == 1
    assert "not found" in result.stderr


def test_harness_not_found_reaches_stderr_via_dispatch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that a not-found runner result surfaces on stderr with exit 1, no stdout."""
    runner = RecordedRunner(
        stdout_lines=[],
        stderr="harness not found: 'claude' is not on PATH",
        exit_code=1,
    )

    code = core.dispatch(Run(prompt="hi"), driver=ClaudeDriver(), runner=runner)
    captured = capsys.readouterr()

    assert code == 1
    assert captured.out == ""
    assert "not found" in captured.err


def test_real_subprocess_runner_spawn_contract_smoke() -> None:
    """Test that the real runner captures a trivial command's output and exit code.

    Uses a portable stand-in binary, not a harness — the OS spawn is what T2's
    live-check exercises against real harnesses.
    """
    result = SubprocessRunner().run(["python", "-c", "print('ok')"], cwd=Path.cwd())

    assert result.exit_code == 0
    assert result.stdout_lines == ["ok"]
