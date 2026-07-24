"""The Ctrl-C contract: an interrupt is a hard stop to exit 130, no partial flush.

This owns one slice of ADR-0015: a `KeyboardInterrupt` surfacing from the spawn
boundary makes `main()` exit `130` with empty stdout. Two companions cover the
rest — `test_runner.py` pins the spawn kwargs that keep the child in wingit's
process group (so a real Ctrl-C reaches it), and `just live-check` proves the
real signal → child-death → no-orphan path against live harnesses.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from wingit import cli
from wingit.__main__ import main
from wingit.schemas import ExitCode

if TYPE_CHECKING:
    from wingit.harnesses.base import RunResult


class InterruptingRunner:
    """A `ProcessRunner` whose spawn is interrupted mid-run, like a Ctrl-C."""

    def run(self, argv: list[str], *, cwd: Path) -> RunResult:  # noqa: ARG002 - Protocol signature; the run never returns
        """Raise `KeyboardInterrupt` as a terminal SIGINT would during the spawn."""
        raise KeyboardInterrupt


def test_interrupt_exits_130_with_empty_stdout(
    *,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that a Ctrl-C during the run exits `130` and writes no partial answer."""
    monkeypatch.setattr(cli, "SubprocessRunner", InterruptingRunner)

    with pytest.raises(SystemExit) as excinfo:
        main(["hi"])
    captured = capsys.readouterr()

    assert excinfo.value.code == ExitCode.INTERRUPTED
    assert captured.out == ""
