"""Harness drivers: one per harness, each normalizing to the `Event` seam.

`DRIVERS` maps each `Harness` to its driver class. The core constructs a fresh
instance per run (drivers may accumulate state across `feed`/`finish`), so the
registry holds classes, not instances.
"""

from typing import TYPE_CHECKING

from wingit.harnesses.claude import ClaudeDriver
from wingit.harnesses.codex import CodexDriver
from wingit.harnesses.copilot import CopilotDriver
from wingit.harnesses.opencode import OpencodeDriver
from wingit.harnesses.pi import PiDriver
from wingit.schemas import Harness

if TYPE_CHECKING:
    from wingit.harnesses.base import HarnessDriver

__all__ = ["DRIVERS"]

DRIVERS: dict[Harness, type[HarnessDriver]] = {
    Harness.CLAUDE: ClaudeDriver,
    Harness.PI: PiDriver,
    Harness.OPENCODE: OpencodeDriver,
    Harness.COPILOT: CopilotDriver,
    Harness.CODEX: CodexDriver,
}
