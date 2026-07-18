"""PROTOTYPE — the candidate HarnessDriver seam under test.

This is the only file that matters. Everything else is scaffolding to drive it.

The hypothesis: one uniform interface, plus a declared capability set, is enough to
express every harness. The prototype's job is to find where that leaks — so adapters
call `leak()` whenever they have to do something the interface did not want them to,
and the TUI shows the leaks next to the output.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class Capability(StrEnum):
    """What a harness can do. The negotiation model the ticket asks about."""

    # Can emit answer prose incrementally, before the run finishes.
    STREAMING_ANSWER = "streaming-answer"
    # Can separate thinking / tool chatter from the answer.
    SEPARABLE_REASONING = "separable-reasoning"
    # Can distinguish success from failure without heuristics.
    RELIABLE_FAILURE = "reliable-failure"
    # Native session resume.
    SESSIONS = "sessions"
    # A real OS-level sandbox, not just tool-call gating.
    OS_SANDBOX = "os-sandbox"


@dataclass(frozen=True)
class Request:
    """What `a` was asked to do."""

    prompt: str
    cwd: str = "."
    allow_tools: bool = False
    model: str | None = None


# --- Events -----------------------------------------------------------------
# The normalized stream every adapter must produce.


@dataclass(frozen=True)
class AnswerChunk:
    text: str


@dataclass(frozen=True)
class ReasoningChunk:
    text: str


@dataclass(frozen=True)
class ToolActivity:
    gist: str


@dataclass(frozen=True)
class FinalAnswer:
    """The harness's own designated answer, known only once the run ends.

    Kept separate from AnswerChunk because the prototype's central finding is that
    these two are *not* the same string.
    """

    text: str


@dataclass(frozen=True)
class Failed:
    gist: str


Event = AnswerChunk | ReasoningChunk | ToolActivity | Failed | FinalAnswer


class HarnessDriver(Protocol):
    """The candidate seam. Four methods and a capability set."""

    name: str
    capabilities: frozenset[Capability]

    def argv(self, req: Request) -> list[str]:
        """Build the headless invocation."""
        ...

    def feed(self, line: str) -> Iterator[Event]:
        """Consume one line of harness stdout, yield normalized events."""
        ...

    def finish(self, harness_exit: int) -> Iterator[Event]:
        """Called once the harness has exited. Last chance to emit."""
        ...


# --- Leak tracking ----------------------------------------------------------
# The measurement instrument: every time an adapter has to fight the interface.

LEAKS: list[tuple[str, str]] = []


def leak(harness: str, what: str) -> None:
    """Record that the interface did not fit this harness cleanly."""
    LEAKS.append((harness, what))


def reset_leaks() -> None:
    LEAKS.clear()


# --- The reducer ------------------------------------------------------------
# Pure: drives a driver over recorded bytes and produces wingit's whole output.


@dataclass
class Outcome:
    """Everything `a` would emit for one run."""

    # What a streaming wingit would have printed as it went.
    answer: str = ""
    # What the harness itself calls the answer, available only at EOF.
    final_answer: str | None = None
    reasoning: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    failure: str | None = None
    exit_code: int = 0
    # When the first answer byte became available, as a line index into stdout.
    # None means "only at the very end" — i.e. not actually streamable.
    first_answer_at: int | None = None
    total_lines: int = 0


def run(driver: HarnessDriver, stdout: str, harness_exit: int) -> Outcome:
    """Replay recorded harness stdout through a driver. Pure."""
    out = Outcome()
    lines = stdout.splitlines()
    out.total_lines = len(lines)

    def absorb(events: Iterator[Event], at: int | None) -> None:
        for ev in events:
            match ev:
                case AnswerChunk(text):
                    if out.first_answer_at is None:
                        out.first_answer_at = at
                    out.answer += text
                case ReasoningChunk(text):
                    out.reasoning.append(text)
                case ToolActivity(gist):
                    out.tools.append(gist)
                case FinalAnswer(text):
                    out.final_answer = text
                case Failed(gist):
                    out.failure = gist

    for i, line in enumerate(lines):
        absorb(driver.feed(line), i)
    absorb(driver.finish(harness_exit), None)

    # wingit's own exit codes (#12): 0 answer, 1 failure/no answer, 2 usage.
    got_answer = bool(out.answer.strip() or (out.final_answer or "").strip())
    if out.failure is not None or not got_answer:
        out.exit_code = 1
    return out


def divergence(out: Outcome) -> str | None:
    """Did streaming and the harness's own answer disagree? The core finding."""
    if out.final_answer is None:
        return "no final-answer field exists" if out.answer else None
    if not out.answer:
        return "nothing streamed; final answer only"
    if out.answer.strip() != out.final_answer.strip():
        return "streamed text != final answer"
    return None
