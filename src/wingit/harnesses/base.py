"""The two Protocols that bound the harness seam.

`HarnessDriver` is the per-harness adapter (ADR-0005): it builds the headless
invocation and normalizes stdout into `Event`s. `ProcessRunner` is the I/O
boundary tests substitute (ADR-0014): it spawns the harness and exposes its
stdout lines, stderr, and exit code.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from wingit.schemas import Capability, Event, Run

__all__ = ["HarnessDriver", "ProcessRunner", "RunResult"]


@dataclass(frozen=True, kw_only=True)
class RunResult:
    """The captured outcome of one harness invocation (D10).

    `stdout_lines` is a sequence in T1; T7 swaps a live line-iterator behind the
    same `ProcessRunner` Protocol without changing this shape.
    """

    stdout_lines: Sequence[str]
    stderr: str
    exit_code: int


class HarnessDriver(Protocol):
    """Adapts one harness CLI to wingit's normalized `Event` seam."""

    name: str
    capabilities: frozenset[Capability]

    def argv(self, run: Run) -> list[str]:
        """Build the headless invocation for this run."""

    def feed(self, line: str) -> Iterator[Event]:
        """Consume one line of harness stdout; yield normalized events."""

    def finish(self, harness_exit: int) -> Iterator[Event]:
        """Emit any final events once the harness has exited."""


class ProcessRunner(Protocol):
    """Spawns a harness and captures its output — the substitution seam."""

    def run(self, argv: list[str], *, cwd: Path) -> RunResult:
        """Spawn `argv` in `cwd`; capture stdout lines, stderr, and exit code."""
