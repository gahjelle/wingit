"""`SubprocessRunner` tests: the real OS spawn and the missing-binary path."""

from pathlib import Path

from wingit.runner import SubprocessRunner
from wingit.schemas import ExitCode


def test_missing_harness_binary_is_clean_failure() -> None:
    """Test that a harness missing from PATH exits with the failure code, cleanly."""
    result = SubprocessRunner().run(["wingit-no-such-harness-xyz"], cwd=Path.cwd())

    assert result.exit_code == ExitCode.FAILURE
    assert "not found" in result.stderr


def test_real_subprocess_runner_spawn_contract_smoke() -> None:
    """Test that the real runner captures a trivial command's output and exit code.

    Uses a portable stand-in binary, not a harness — the OS spawn is what the
    manual live-check exercises against real harnesses.
    """
    result = SubprocessRunner().run(["python", "-c", "print('ok')"], cwd=Path.cwd())

    assert result.exit_code == ExitCode.OK
    assert result.stdout_lines == ["ok"]
