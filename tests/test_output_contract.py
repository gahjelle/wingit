"""The output contract: Answer to stdout, Reasoning/errors to stderr, exit codes.

These drive the real `ClaudeDriver` and real core through `core.dispatch` on top
of a `RecordedRunner`, asserting the observable stdout/stderr split and exit code
(ADR-0014, testing.md).
"""

from typing import TYPE_CHECKING

from conftest import RecordedRunner, load_fixture_lines

from wingit import core
from wingit.harnesses.claude import ClaudeDriver
from wingit.schemas import Event, FinalAnswer, ReasoningChunk, Run

if TYPE_CHECKING:
    import pytest


def run_claude(
    runner: RecordedRunner, *, capsys: pytest.CaptureFixture[str]
) -> tuple[str, str, int]:
    """Dispatch a run through the real driver/core; return stdout, stderr, exit."""
    exit_code = core.dispatch(
        Run(prompt="ignored"), driver=ClaudeDriver(), runner=runner
    )
    captured = capsys.readouterr()
    return captured.out, captured.err, exit_code


def test_happy_path_answer_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that a successful run prints the answer to stdout, stderr empty, exit 0."""
    runner = RecordedRunner(stdout_lines=load_fixture_lines("claude", scenario="prose"))

    out, err, code = run_claude(runner, capsys=capsys)

    assert out == "pineapple\n"
    assert err == ""
    assert code == 0


def test_pipe_citizenship_exactly_one_trailing_newline(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that stdout is exactly one line ending in one newline (pipe citizenship)."""
    runner = RecordedRunner(stdout_lines=load_fixture_lines("claude", scenario="prose"))

    out, _, _ = run_claude(runner, capsys=capsys)

    assert out.count("\n") == 1
    assert out.endswith("\n")
    assert not out.endswith("\n\n")


def test_answer_with_trailing_newlines_collapses_to_one(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that a `.result` ending in several newlines prints exactly one."""
    crafted = (
        '{"type":"result","subtype":"success","is_error":false,"result":"hi\\n\\n"}'
    )
    runner = RecordedRunner(stdout_lines=[crafted], exit_code=0)

    out, _, code = run_claude(runner, capsys=capsys)

    assert out == "hi\n"
    assert code == 0


def test_tool_run_prints_result_not_preamble(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that a tool-using run prints `.result` (`3`), never the preamble."""
    runner = RecordedRunner(stdout_lines=load_fixture_lines("claude", scenario="tools"))

    out, _, code = run_claude(runner, capsys=capsys)

    assert out == "3\n"
    assert "I'll" not in out
    assert code == 0


def test_failure_is_error_trap(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that a failed run (is_error under subtype success) is exit 1, no stdout."""
    runner = RecordedRunner(
        stdout_lines=load_fixture_lines("claude", scenario="fail"), exit_code=1
    )

    out, err, code = run_claude(runner, capsys=capsys)

    assert code == 1
    assert out == ""
    assert "no-such-model-xyz" in err


def test_empty_answer_on_clean_exit_is_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that an empty `.result` on a clean exit is a failure (exit 1, no stdout)."""
    crafted = '{"type":"result","subtype":"success","is_error":false,"result":""}'
    runner = RecordedRunner(stdout_lines=[crafted], exit_code=0)

    out, _, code = run_claude(runner, capsys=capsys)

    assert code == 1
    assert out == ""


def test_reasoning_channel_kept_separate_from_answer() -> None:
    """Test that a `ReasoningChunk` is routed to Reasoning while the Answer stays clean.

    The Claude driver emits no reasoning yet, so this exercises the built-but-
    silent channel at the reduction level with a crafted event stream.
    """
    events: list[Event] = [
        ReasoningChunk(text="thinking about it"),
        FinalAnswer(text="42"),
    ]
    outcome = core.reduce_events(events, exit_code=0, child_stderr="")

    assert outcome.exit_code == 0
    assert outcome.answer == "42"
    assert list(outcome.reasoning) == ["thinking about it"]
