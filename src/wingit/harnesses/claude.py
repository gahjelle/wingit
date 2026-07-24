"""The Claude Code driver: `claude -p` in structured stream-json mode.

Claude Code does not stream a trustworthy answer (ADR-0005 §2): its streamed
`assistant` text carries pre-tool preamble that diverges from the deduplicated
`.result`. So this driver ignores everything but the terminal `result` event and
takes the Answer from `.result` alone. Failure hides under `subtype:"success"`;
the in-band signal is `is_error`, with the process exit code authoritative in
the core.
"""

from typing import TYPE_CHECKING, ClassVar

from wingit.harnesses.base import FAILURE_GIST_LIMIT, parse_json_object
from wingit.schemas import Capability, Event, Failed, FinalAnswer, Run

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["ClaudeDriver"]


class ClaudeDriver:
    """Normalizes Claude Code's stream-json output into `Event`s."""

    name = "claude"
    capabilities: ClassVar = {
        Capability.STREAMS: False,
        Capability.SHOWS_REASONING: True,
        Capability.SUPPORTS_TOOLS_NONE: True,
        Capability.RUNS_WITHOUT_STORING_SESSION: True,
    }

    def argv(self, run: Run) -> list[str]:
        """Build `claude --print` in full-approval headless mode."""
        return [
            "claude",
            "--print",
            run.prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "bypassPermissions",
        ]

    def feed(self, line: str) -> Iterator[Event]:
        """Emit the Answer (and a failure gist) from the terminal result event."""
        event = parse_json_object(line)
        if event is None or event.get("type") != "result":
            return
        result = str(event.get("result", ""))
        yield FinalAnswer(text=result)
        if event.get("is_error"):
            yield Failed(gist=result[:FAILURE_GIST_LIMIT])

    def finish(self, harness_exit: int) -> Iterator[Event]:  # noqa: ARG002 - Protocol signature; the result event already carried the answer
        """Emit nothing; the result event already carried the answer."""
        return iter(())
