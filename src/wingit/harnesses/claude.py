"""The Claude Code driver: `claude -p` in structured stream-json mode.

Claude Code does not stream a trustworthy answer (ADR-0005 §2): its streamed
`assistant` text carries pre-tool preamble that diverges from the deduplicated
`.result`. So this driver ignores everything but the terminal `result` event and
takes the Answer from `.result` alone. Failure hides under `subtype:"success"`;
the in-band signal is `is_error`, with the process exit code authoritative in
the core.
"""

import json
from typing import TYPE_CHECKING, Any

from wingit.schemas import Capability, Event, Failed, FinalAnswer, Run

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["ClaudeDriver"]

FAILURE_GIST_LIMIT = 200


def parse_json_object(line: str) -> dict[str, Any] | None:
    """Parse one JSONL line to a dict, or None if it is not a JSON object."""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


class ClaudeDriver:
    """Normalizes Claude Code's stream-json output into `Event`s."""

    name = "claude"
    # Claude streams no trustworthy answer, shows reasoning, and supports
    # `--tools none`, but stores every session, so it cannot run without one.
    capabilities = frozenset(
        {Capability.SHOWS_REASONING, Capability.SUPPORTS_TOOLS_NONE}
    )

    def argv(self, run: Run) -> list[str]:
        """Build `claude -p` in full-approval headless mode."""
        return [
            "claude",
            "-p",
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
