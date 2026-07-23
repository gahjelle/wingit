"""Typed domain models: run, normalized events, and harness capabilities.

The `Event` union is the currency of the harness seam (ADR-0005): every driver
normalizes its harness's output into these events, and the core reduces them to
the Answer, the Reasoning, and a failure decision without knowing which harness
produced them.
"""

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict

__all__ = [
    "AnswerChunk",
    "Capability",
    "Event",
    "ExitCode",
    "Failed",
    "FinalAnswer",
    "FrozenModel",
    "Harness",
    "ReasoningChunk",
    "Run",
    "StrictModel",
    "ToolActivity",
]


class FrozenModel(BaseModel):
    """Immutable pydantic base that forbids unknown fields (GAC002)."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class StrictModel(BaseModel):
    """Mutable pydantic base that forbids unknown fields (GAC002)."""

    model_config = ConfigDict(extra="forbid")


class ExitCode(IntEnum):
    """The process exit codes wingit promises (`CONTEXT.md`, ADR-0005).

    `OK` is a clean answer, `FAILURE` is any harness or environmental failure,
    and `USAGE` is a malformed invocation — distinct so callers can tell a bad
    command line from a run that reached the harness and failed. `INTERRUPTED`
    is the code a shell reports for a SIGINT-killed process (ADR-0015).
    """

    OK = 0
    FAILURE = 1
    USAGE = 2
    INTERRUPTED = 130


class Harness(StrEnum):
    """A supported harness, by its canonical lowercase name.

    Members are ordered by `CONTEXT.md`'s ranked detection order (Claude Code >
    Pi > Opencode > Copilot > Codex): the highest-ranked harness on `PATH` wins
    when no harness is selected explicitly.
    """

    CLAUDE = "claude"
    PI = "pi"
    OPENCODE = "opencode"
    COPILOT = "copilot"
    CODEX = "codex"


class Capability(StrEnum):
    """A user-visible property of a harness, declared per driver (ADR-0005).

    The four members are `CONTEXT.md`'s user-visible capabilities; a driver
    declares the ones its harness has, and the core negotiates against them.
    """

    STREAMS = "streams"
    SHOWS_REASONING = "shows-reasoning"
    SUPPORTS_TOOLS_NONE = "supports-tools-none"
    RUNS_WITHOUT_STORING_SESSION = "runs-without-storing-session"


class Run(FrozenModel):
    """A single ask to run against a harness.

    Carries only the prompt for now; cwd is the runner's concern, and model and
    tool selection arrive alongside the features that need them.
    """

    prompt: str


@dataclass(frozen=True, kw_only=True)
class AnswerChunk:
    """A fragment of the Answer, streamed as the harness produces it."""

    text: str


@dataclass(frozen=True, kw_only=True)
class ReasoningChunk:
    """A fragment of the harness's Reasoning, destined for stderr."""

    text: str


@dataclass(frozen=True, kw_only=True)
class ToolActivity:
    """A note that the harness invoked a tool, for the Reasoning channel."""

    gist: str


@dataclass(frozen=True, kw_only=True)
class FinalAnswer:
    """The complete, deduplicated Answer emitted at the end of a run."""

    text: str


@dataclass(frozen=True, kw_only=True)
class Failed:
    """A signal that the run failed, carrying a short gist of why."""

    gist: str


type Event = AnswerChunk | ReasoningChunk | ToolActivity | FinalAnswer | Failed
