"""Orchestration and the pure reduction from events to an outcome.

The reduction is exit-code-primary (ADR-0005 §3): a non-zero child exit means
failure regardless of any `FinalAnswer`, and an empty answer on a clean exit is
also a failure. The decision logic is a pure function over the events and the
exit code, so it is trivially testable with no I/O.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from wingit import console
from wingit.schemas import (
    AnswerChunk,
    Event,
    ExitCode,
    Failed,
    FinalAnswer,
    ReasoningChunk,
    Run,
    ToolActivity,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from wingit.harnesses.base import HarnessDriver, ProcessRunner

__all__ = ["Outcome", "dispatch", "reduce_events"]

GENERIC_FAILURE_MESSAGE = "harness failed"


@dataclass(frozen=True, kw_only=True)
class Outcome:
    """The reduced result of a run: what to print and which exit code to use.

    On failure `answer` is empty and never reaches stdout; `error` holds the
    stderr message. On success `answer` holds the Answer and `reasoning` holds
    any Reasoning lines.
    """

    answer: str
    reasoning: Sequence[str]
    error: str
    exit_code: int


def reduce_events(
    events: Iterable[Event],
    *,
    exit_code: int,
    child_stderr: str,
) -> Outcome:
    """Reduce normalized events plus the child exit code to an `Outcome`."""
    answer = ""
    reasoning: list[str] = []
    failure_gist = ""
    for event in events:
        match event:
            case FinalAnswer(text=text):
                answer = text
            case AnswerChunk(text=text):
                answer += text
            case ReasoningChunk(text=text):
                reasoning.append(text)
            case ToolActivity(gist=gist):
                reasoning.append(gist)
            case Failed(gist=gist):
                failure_gist = gist

    failed = exit_code != 0 or bool(failure_gist) or not answer
    if failed:
        # In-band gist first, then captured child stderr, then a generic message.
        error = failure_gist or child_stderr.strip() or GENERIC_FAILURE_MESSAGE
        return Outcome(answer="", reasoning=[], error=error, exit_code=ExitCode.FAILURE)
    return Outcome(answer=answer, reasoning=reasoning, error="", exit_code=ExitCode.OK)


def collect_events(
    driver: HarnessDriver, *, lines: Iterable[str], exit_code: int
) -> list[Event]:
    """Feed each stdout line through the driver, then flush with `finish`."""
    events: list[Event] = []
    for line in lines:
        events.extend(driver.feed(line))
    events.extend(driver.finish(exit_code))
    return events


def dispatch(run: Run, *, driver: HarnessDriver, runner: ProcessRunner) -> int:
    """Execute one run end-to-end, honor the output contract, return the exit code."""
    result = runner.run(driver.argv(run), cwd=Path.cwd())
    events = collect_events(
        driver, lines=result.stdout_lines, exit_code=result.exit_code
    )
    outcome = reduce_events(
        events, exit_code=result.exit_code, child_stderr=result.stderr
    )
    if outcome.exit_code == ExitCode.OK:
        for line in outcome.reasoning:
            console.write_reasoning(line)
        console.write_answer(outcome.answer)
    else:
        console.write_error(outcome.error)
    return outcome.exit_code
