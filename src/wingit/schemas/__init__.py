"""Typed domain models: run, normalized events, and harness capabilities.

The `Event` union is the currency of the harness seam (ADR-0005): every driver
normalizes its harness's output into these events, and the core reduces them to
the Answer, the Reasoning, and a failure decision without knowing which harness
produced them.
"""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

__all__ = [
    "AnswerChunk",
    "Capability",
    "Event",
    "Failed",
    "FinalAnswer",
    "FrozenModel",
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


class Capability(StrEnum):
    """A user-visible property of a harness, declared per driver (ADR-0005).

    The four members are `CONTEXT.md`'s user-visible capabilities. T1 populates
    Claude's set but reads none of them; T2+ negotiate against them.
    """

    STREAMS = "streams"
    SHOWS_REASONING = "shows-reasoning"
    SUPPORTS_TOOLS_NONE = "supports-tools-none"
    RUNS_WITHOUT_STORING_SESSION = "runs-without-storing-session"


class Run(FrozenModel):
    """A single ask to run against a harness.

    T1 carries only the prompt; cwd is the runner's concern and model/tools
    arrive in later tracers.
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
