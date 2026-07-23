"""The Copilot driver: `copilot --prompt` in JSON mode.

Copilot streams token-level `assistant.message_delta` events and closes each
turn with a complete `assistant.message`; the answer is the last non-empty such
message (a tool-only turn's message is empty). Its `assistant.reasoning` content
is always an opaque blob with empty text, so this driver shows no reasoning. A
failed run emits *nothing* in-band — no result, no error event — so this driver
raises no synthetic `Failed`; the core falls back to the exit code and stderr.
"""

from typing import TYPE_CHECKING, Any, ClassVar

from wingit.harnesses.base import parse_json_object
from wingit.schemas import (
    AnswerChunk,
    Capability,
    Event,
    FinalAnswer,
    Run,
    ToolActivity,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["CopilotDriver"]


class CopilotDriver:
    """Normalizes Copilot's JSON stream into `Event`s."""

    name = "copilot"
    # Copilot streams real token deltas, but its reasoning is an opaque blob
    # (no shown reasoning) and it can drop all tools; every run persists a
    # resumable session.
    capabilities: ClassVar[dict[Capability, bool]] = {
        Capability.STREAMS: True,
        Capability.SHOWS_REASONING: False,
        Capability.SUPPORTS_TOOLS_NONE: True,
        Capability.RUNS_WITHOUT_STORING_SESSION: False,
    }

    def __init__(self) -> None:
        """Start with no final message recorded."""
        self.final: str | None = None

    def argv(self, run: Run) -> list[str]:
        """Build `copilot --prompt` in auto-approve JSON mode, logs silenced."""
        return [
            "copilot",
            "--prompt",
            run.prompt,
            "--output-format",
            "json",
            "--allow-all-tools",
            "--log-level",
            "none",
        ]

    def feed(self, line: str) -> Iterator[Event]:
        """Stream answer deltas, record the final message, note tool activity."""
        event = parse_json_object(line)
        if event is None:
            return
        data: dict[str, Any] = event.get("data") or {}
        match event.get("type"):
            case "assistant.message_delta":
                yield AnswerChunk(text=str(data.get("deltaContent", "")))
            case "assistant.message":
                # Empty on a tool-only turn, so the answer is the last non-empty.
                if data.get("content"):
                    self.final = str(data["content"])
            case "tool.execution_start":
                yield ToolActivity(gist=str(data.get("toolName", "?")))

    def finish(self, harness_exit: int) -> Iterator[Event]:  # noqa: ARG002 - Protocol signature; a failed run emits nothing in-band (exit code + stderr are authoritative)
        """Emit the final message as the answer; a failure leaves this empty."""
        if self.final is not None:
            yield FinalAnswer(text=self.final)
