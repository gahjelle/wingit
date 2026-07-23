"""Unit tests for the Claude driver: argv shape and event normalization."""

from conftest import load_fixture_lines

from wingit.harnesses.claude import ClaudeDriver
from wingit.schemas import Capability, Failed, FinalAnswer, Run


def feed_all(driver: ClaudeDriver, *, lines: list[str]) -> list[object]:
    """Feed every line through the driver and collect the emitted events."""
    events: list[object] = []
    for line in lines:
        events.extend(driver.feed(line))
    return events


def test_argv_is_full_approval_headless_invocation() -> None:
    """Test that argv builds `claude -p` in bypass-permissions stream-json mode."""
    argv = ClaudeDriver().argv(Run(prompt="hi"))

    assert argv == [
        "claude",
        "-p",
        "hi",
        "--output-format",
        "stream-json",
        "--verbose",
        "--permission-mode",
        "bypassPermissions",
    ]


def test_declares_claudes_capabilities() -> None:
    """Test that the driver declares shows-reasoning and supports-tools-none."""
    assert ClaudeDriver().capabilities == frozenset(
        {Capability.SHOWS_REASONING, Capability.SUPPORTS_TOOLS_NONE}
    )


def test_prose_yields_final_answer_only() -> None:
    """Test that a tool-free run yields the `.result` text and no failure."""
    events = feed_all(
        ClaudeDriver(), lines=load_fixture_lines("claude", scenario="prose")
    )

    assert events == [FinalAnswer(text="pineapple")]


def test_tools_answer_is_result_not_preamble() -> None:
    """Test that a tool-using run yields `.result`, dropping the streamed preamble."""
    events = feed_all(
        ClaudeDriver(), lines=load_fixture_lines("claude", scenario="tools")
    )

    assert events == [FinalAnswer(text="3")]


def test_failure_trips_is_error_under_subtype_success() -> None:
    """Test that `is_error` yields a `Failed` even though subtype stays success."""
    events = feed_all(
        ClaudeDriver(), lines=load_fixture_lines("claude", scenario="fail")
    )

    assert any(isinstance(event, Failed) for event in events)
    assert any(isinstance(event, FinalAnswer) for event in events)


def test_non_json_lines_yield_nothing() -> None:
    """Test that a non-JSON stdout line produces no events."""
    assert list(ClaudeDriver().feed("not json at all")) == []
