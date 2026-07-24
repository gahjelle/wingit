"""`SubprocessRunner` tests: the real OS spawn and the missing-binary path."""

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from wingit.runner import SubprocessRunner
from wingit.schemas import ExitCode

if TYPE_CHECKING:
    import pytest


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


def test_env_passes_through_to_the_child_untouched(
    *, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that the child inherits the parent environment whole (ADR-0011).

    Behavioral rather than a kwargs spy: a sentinel set in this process must
    reach the child, so any future env scrubbing would fail this test.
    """
    monkeypatch.setenv("WINGIT_ENV_PROBE", "inherited")
    probe = "import os; print(os.environ.get('WINGIT_ENV_PROBE', 'MISSING'))"

    result = SubprocessRunner().run(["python", "-c", probe], cwd=Path.cwd())

    assert result.stdout_lines == ["inherited"]


def test_spawn_keeps_child_in_our_process_group(
    *, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that the runner does not detach the child from wingit's process group.

    A terminal Ctrl-C reaches the harness only while it shares wingit's process
    group; `start_new_session` or a new `process_group` would break that path
    (ADR-0015: no signal handler, no session leader). This pins the spawn kwargs
    that keep the child reachable.
    """
    captured: dict[str, object] = {}

    def spy(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        """Record the spawn kwargs and return a trivial completed process."""
        captured.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", spy)
    SubprocessRunner().run(["python", "-c", "pass"], cwd=Path.cwd())

    assert not captured.get("start_new_session")
    assert captured.get("process_group", -1) == -1
    assert captured.get("preexec_fn") is None
