"""The Codex driver: `codex exec` in JSON mode.

Codex reports completed items on the stream: the `agent_message` item is the
whole answer (arriving only at the end, no deltas), `reasoning` items carry real
text, and `command_execution` items are tool activity. Failure is in-band and
reliable: either a `turn.failed` event or an `error` item.
"""

from typing import TYPE_CHECKING, Any, ClassVar

from wingit.harnesses.claude import FAILURE_GIST_LIMIT, parse_json_object
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

__all__ = ["CodexDriver"]

COMMAND_GIST_LIMIT = 60


class CodexDriver:
    """Normalizes Codex's JSON stream into `Event`s."""

    name = "codex"
    # Codex delivers the answer whole at the end (no streaming), shows
    # reasoning, and has no tools-off rung (only sandbox modes), but `exec`
    # leaves no resumable session behind.
    capabilities: ClassVar[dict[Capability, bool]] = {
        Capability.STREAMS: False,
        Capability.SHOWS_REASONING: True,
        Capability.SUPPORTS_TOOLS_NONE: False,
        Capability.RUNS_WITHOUT_STORING_SESSION: True,
    }

    def argv(self, run: Run) -> list[str]:
        """Build `codex exec` in JSON mode with the workspace-write sandbox."""
        return [
            "codex",
            "exec",
            "--json",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            run.prompt,
        ]

    def feed(self, line: str) -> Iterator[Event]:
        """Emit the answer, reasoning, tool activity, and in-band failures."""
        event = parse_json_object(line)
        if event is None:
            return
        match event.get("type"):
            case "item.completed":
                yield from self.feed_item(event.get("item") or {})
            case "turn.failed":
                message = event.get("error", {}).get("message", "")
                yield Failed(gist=str(message)[:FAILURE_GIST_LIMIT])

    def feed_item(self, item: dict[str, Any]) -> Iterator[Event]:
        """Normalize one completed item by its type."""
        match item.get("type"):
            case "agent_message":
                yield FinalAnswer(text=str(item.get("text", "")))
            case "command_execution":
                yield ToolActivity(
                    gist=str(item.get("command", "?"))[:COMMAND_GIST_LIMIT]
                )
            case "reasoning":
                yield ReasoningChunk(text=str(item.get("text", "")))
            case "error":
                yield Failed(gist=str(item.get("message", ""))[:FAILURE_GIST_LIMIT])

    def finish(self, harness_exit: int) -> Iterator[Event]:  # noqa: ARG002 - Protocol signature; the item.completed event already carried the answer
        """Emit nothing; the completed items already carried the answer."""
        return iter(())
