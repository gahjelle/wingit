"""The Opencode driver: `opencode run` in JSON mode.

Opencode emits no terminal answer event (ADR-0005): it streams `text` parts per
step and the answer is whichever text the last step produced, known only once
the stream ends. So this driver buffers text per `step_start` and takes the
final answer from the last step at `finish`. `--thinking` surfaces `reasoning`
events carrying real text, and an `error` event is the in-band failure signal.
"""

from typing import TYPE_CHECKING, Any, ClassVar

from wingit.harnesses.base import FAILURE_GIST_LIMIT, parse_json_object
from wingit.schemas import (
    Capability,
    Event,
    Failed,
    FinalAnswer,
    ReasoningChunk,
    Run,
    ToolActivity,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["OpencodeDriver"]


class OpencodeDriver:
    """Normalizes Opencode's JSON stream into `Event`s."""

    name = "opencode"
    # Opencode has no trustworthy streamed answer (reassembled at EOF), shows
    # reasoning under `--thinking`, and supports a tools-off permission map, but
    # every run persists a resumable session.
    capabilities: ClassVar[dict[Capability, bool]] = {
        Capability.STREAMS: False,
        Capability.SHOWS_REASONING: True,
        Capability.SUPPORTS_TOOLS_NONE: True,
        Capability.RUNS_WITHOUT_STORING_SESSION: False,
    }

    def __init__(self) -> None:
        """Start with no steps buffered and no failure recorded."""
        self.steps: list[list[str]] = []
        self.failed = False

    def argv(self, run: Run) -> list[str]:
        """Build `opencode run` in auto-approve JSON mode with reasoning on."""
        return [
            "opencode",
            "run",
            "--format",
            "json",
            "--auto",
            "--thinking",
            run.prompt,
        ]

    def feed(self, line: str) -> Iterator[Event]:
        """Buffer step text and reasoning; note tools and in-band failure."""
        event = parse_json_object(line)
        if event is None:
            return
        part: dict[str, Any] = event.get("part") or {}
        match event.get("type"):
            case "step_start":
                self.steps.append([])
            case "text":
                if not self.steps:
                    self.steps.append([])
                self.steps[-1].append(str(part.get("text", "")))
            case "reasoning":
                yield ReasoningChunk(text=str(part.get("text", "")))
            case "tool_use":
                yield ToolActivity(gist=str(part.get("tool", "?")))
            case "error":
                self.failed = True
                message = event.get("error", {}).get("data", {}).get("message", "")
                yield Failed(gist=str(message)[:FAILURE_GIST_LIMIT])

    def finish(self, harness_exit: int) -> Iterator[Event]:  # noqa: ARG002 - Protocol signature; the answer is reassembled from buffered steps
        """Emit the last step's joined text as the answer, unless the run failed."""
        if self.failed or not self.steps:
            return
        text = "".join(self.steps[-1])
        if text:
            yield FinalAnswer(text=text)
