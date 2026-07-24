"""The Pi driver: `pi --print` in JSON mode.

Pi streams `text_delta` and `thinking_delta` events under `message_update` and
closes each turn with a `turn_end` carrying the turn's complete message; the
answer is the last turn whose message has text (an early turn is thinking plus
tool calls only). Like Copilot, a failed run emits nothing in-band, so this
driver raises no synthetic `Failed`; the core uses the exit code and stderr.
"""

from typing import TYPE_CHECKING, Any, ClassVar

from wingit.harnesses.base import parse_json_object
from wingit.schemas import (
    AnswerChunk,
    Capability,
    Event,
    FinalAnswer,
    ReasoningChunk,
    Run,
    ToolActivity,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["PiDriver"]


class PiDriver:
    """Normalizes Pi's JSON stream into `Event`s."""

    name = "pi"
    capabilities: ClassVar = {
        Capability.STREAMS: True,
        Capability.SHOWS_REASONING: True,
        Capability.SUPPORTS_TOOLS_NONE: True,
        Capability.RUNS_WITHOUT_STORING_SESSION: True,
    }

    def __init__(self) -> None:
        """Start with no final message recorded."""
        self.final: str | None = None

    def argv(self, run: Run) -> list[str]:
        """Build `pi --print` in auto-approve JSON mode."""
        return [
            "pi",
            "--print",
            "--mode",
            "json",
            "--approve",
            run.prompt,
        ]

    def feed(self, line: str) -> Iterator[Event]:
        """Stream answer and thinking deltas, note tools, record the final text."""
        event = parse_json_object(line)
        if event is None:
            return
        match event.get("type"):
            case "message_update":
                yield from self.feed_delta(event.get("assistantMessageEvent") or {})
            case "tool_execution_start":
                yield ToolActivity(gist=str(event.get("toolName", "?")))
            case "turn_end":
                # The last turn with text wins; earlier turns are thinking + tools.
                text = self.join_text(event.get("message") or {})
                if text:
                    self.final = text

    def feed_delta(self, message_event: dict[str, Any]) -> Iterator[Event]:
        """Turn one assistant-message delta into an answer or reasoning chunk."""
        match message_event.get("type"):
            case "text_delta":
                yield AnswerChunk(text=str(message_event.get("delta", "")))
            case "thinking_delta":
                yield ReasoningChunk(text=str(message_event.get("delta", "")))

    def join_text(self, message: dict[str, Any]) -> str:
        """Join the text blocks of a turn's message into one string."""
        return "".join(
            str(block.get("text", ""))
            for block in message.get("content", [])
            if block.get("type") == "text"
        )

    def finish(self, harness_exit: int) -> Iterator[Event]:  # noqa: ARG002 - Protocol signature; a failed run emits nothing in-band (exit code + stderr are authoritative)
        """Emit the final turn's text as the answer; a failure leaves this empty."""
        if self.final is not None:
            yield FinalAnswer(text=self.final)
