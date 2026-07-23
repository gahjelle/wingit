"""Unit tests for the Codex driver: argv, completed-item answer, tools, failure."""

from conftest import load_fixture_lines

from wingit import core
from wingit.harnesses.codex import CodexDriver
from wingit.schemas import (
    Event,
    Failed,
    FinalAnswer,
    ReasoningChunk,
    Run,
    ToolActivity,
)


def collect(scenario: str, *, exit_code: int = 0) -> list[Event]:
    """Run the real driver over a recorded codex fixture and collect events."""
    return core.collect_events(
        CodexDriver(),
        lines=load_fixture_lines("codex", scenario=scenario),
        exit_code=exit_code,
    )


def test_argv_is_workspace_write_json_invocation() -> None:
    """Test that argv builds `codex exec` in JSON mode with the workspace sandbox."""
    argv = CodexDriver().argv(Run(prompt="hi"))

    assert argv == [
        "codex",
        "exec",
        "--json",
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write",
        "hi",
    ]


def test_prose_answer_is_agent_message() -> None:
    """Test that a tool-free run yields the completed `agent_message` text."""
    assert collect("prose") == [FinalAnswer(text="pineapple")]


def test_tools_yields_command_activity_and_answer() -> None:
    """Test that a tool run surfaces the command activity and the final answer."""
    events = collect("tools")

    assert any(isinstance(event, ToolActivity) for event in events)
    assert FinalAnswer(text="3") in events


def test_failure_turn_failed_yields_failed() -> None:
    """Test that a `turn.failed` event yields an in-band `Failed`."""
    events = collect("fail", exit_code=1)

    assert any(isinstance(event, Failed) for event in events)


def test_reasoning_item_yields_reasoning_chunk() -> None:
    """Test that a completed `reasoning` item maps to a `ReasoningChunk`.

    The recordings carry no reasoning item, so this feeds one realistic line
    (per testing.md) to pin the mapping the live path relies on.
    """
    line = '{"type":"item.completed","item":{"type":"reasoning","text":"thinking"}}'

    assert list(CodexDriver().feed(line)) == [ReasoningChunk(text="thinking")]
