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
    from collections.abc import Iterable, Iterator

    from wingit.schemas import Capability, Event, Run

__all__ = ["HarnessDriver", "ProcessRunner", "RunResult"]


@dataclass(frozen=True, kw_only=True)
class RunResult:
    """The captured outcome of one harness invocation.

    `stdout_lines` is an iterable of lines: a materialized list today, but typed
    so a live line-iterator can sit behind the same `ProcessRunner` Protocol
    without changing this shape. The core only ever iterates it once.
    """

    stdout_lines: Iterable[str]
    stderr: str
    exit_code: int


class HarnessDriver(Protocol):
    """Adapts one harness CLI to wingit's normalized `Event` seam.

    Lifecycle: one instance per run. `feed`/`finish` may accumulate state
    across lines (several drivers buffer text and pick the answer at `finish`),
    so the core constructs a fresh driver for every dispatch.

    `capabilities` maps **every** `Capability` to an explicit bool \N{EN DASH}
    never a subset \N{EN DASH} so adding a new axis forces a conscious yes/no in
    each driver (enforced by a totality test).
    """

    name: str
    capabilities: dict[Capability, bool]

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
