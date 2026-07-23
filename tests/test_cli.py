"""CLI-boundary tests: usage errors, entry points, and the harness-not-found path."""

from importlib import metadata

import pytest
from conftest import RecordedRunner

from wingit import core
from wingit.__main__ import main
from wingit.harnesses.claude import ClaudeDriver
from wingit.schemas import ExitCode, Run


def test_missing_prompt_is_usage_error() -> None:
    """Test that invoking with no prompt exits with the usage code, not a failure."""
    with pytest.raises(SystemExit) as excinfo:
        main([])

    assert excinfo.value.code == ExitCode.USAGE


def test_both_console_scripts_point_at_main() -> None:
    """Test that the `wingit` and `a` entry points both resolve to `main`."""
    scripts = metadata.entry_points(group="console_scripts")
    resolved = {ep.name: ep.load() for ep in scripts if ep.name in {"a", "wingit"}}

    assert resolved == {"a": main, "wingit": main}


def test_harness_not_found_reaches_stderr_via_dispatch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that a not-found runner result surfaces on stderr with exit 1, no stdout."""
    runner = RecordedRunner(
        stdout_lines=[],
        stderr="harness not found: 'claude' is not on PATH",
        exit_code=ExitCode.FAILURE,
    )

    code = core.dispatch(Run(prompt="hi"), driver=ClaudeDriver(), runner=runner)
    captured = capsys.readouterr()

    assert code == ExitCode.FAILURE
    assert captured.out == ""
    assert "not found" in captured.err
