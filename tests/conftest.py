"""Test seam: a fake `ProcessRunner` fed recorded harness bytes (ADR-0014).

The real `ClaudeDriver` and the real core run on top of `RecordedRunner`, so the
whole pipeline — argv, JSON parse, `is_error` trap, `.result` extraction,
reduction, stdout/stderr split, exit code — is exercised against ground-truth
bytes. Only the OS-level spawn is stubbed; that is validated by the manual
live-check, as it would be under any fast test approach.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from wingit import core
from wingit.harnesses.base import RunResult

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from wingit.harnesses.base import HarnessDriver
    from wingit.schemas import Event

FIXTURE_ROOT = Path(__file__).parent / "fixtures"


@dataclass(frozen=True, kw_only=True)
class RecordedRunner:
    """A `ProcessRunner` that replays recorded stdout, stderr, and exit code."""

    stdout_lines: Sequence[str]
    stderr: str = ""
    exit_code: int = 0

    def run(self, argv: list[str], *, cwd: Path) -> RunResult:  # noqa: ARG002 - Protocol signature; argv/cwd not consulted on replay
        """Return the recorded output, ignoring argv and cwd."""
        return RunResult(
            stdout_lines=self.stdout_lines,
            stderr=self.stderr,
            exit_code=self.exit_code,
        )


def load_fixture_lines(harness: str, *, scenario: str) -> list[str]:
    """Read a recorded harness stdout fixture and split it into lines."""
    path = FIXTURE_ROOT / harness / f"{scenario}.stdout"
    return path.read_text(encoding="utf-8").splitlines()


def load_fixture_stderr(harness: str, *, scenario: str) -> str:
    """Read a recorded harness stderr fixture, or "" if none was recorded."""
    path = FIXTURE_ROOT / harness / f"{scenario}.stderr"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def make_collector(
    driver_cls: type[HarnessDriver], *, harness: str
) -> Callable[..., list[Event]]:
    """Build a `collect(scenario, *, exit_code=0)` bound to one driver and its fixtures.

    Each driver test runs the real driver and core over recorded bytes; only the
    driver class and fixture directory differ, so the loop lives here once.
    """

    def collect(scenario: str, *, exit_code: int = 0) -> list[Event]:
        """Run the real driver over a recorded fixture and collect its events."""
        return core.collect_events(
            driver_cls(),
            lines=load_fixture_lines(harness, scenario=scenario),
            exit_code=exit_code,
        )

    return collect
