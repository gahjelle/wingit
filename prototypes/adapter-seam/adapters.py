"""PROTOTYPE — four throwaway adapters against the candidate seam.

Written against the *recorded* output of the real binaries (see recordings/), not
against documentation. Every `leak()` call marks a place the uniform interface did
not fit and the adapter had to do something special.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from seam import (
    AnswerChunk,
    Capability,
    Event,
    Failed,
    FinalAnswer,
    ReasoningChunk,
    Request,
    ToolActivity,
    leak,
)


def _json(line: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


# --- Claude Code ------------------------------------------------------------


class ClaudeDriver:
    name = "claude"
    capabilities = frozenset(
        {
            Capability.SEPARABLE_REASONING,
            Capability.RELIABLE_FAILURE,
            Capability.SESSIONS,
            # No token deltas without --include-partial-messages; message-level only.
            Capability.STREAMING_ANSWER,
        }
    )

    def argv(self, req: Request) -> list[str]:
        argv = [
            "claude",
            "-p",
            req.prompt,
            "--output-format",
            "stream-json",
            "--verbose",
        ]
        if not req.allow_tools:
            argv += ["--disallowedTools", "Bash,Glob,Grep,Read,Edit,Write"]
        return argv

    def feed(self, line: str) -> Iterator[Event]:
        ev = _json(line)
        if ev is None:
            return
        match ev.get("type"):
            case "assistant":
                for block in ev.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        yield AnswerChunk(block["text"])
                    elif block.get("type") == "thinking":
                        yield ReasoningChunk(block.get("thinking", ""))
                    elif block.get("type") == "tool_use":
                        yield ToolActivity(block.get("name", "?"))
            case "result":
                # LEAK: `.result` is the *deduplicated* final prose, while the
                # streamed `assistant` text also carries pre-tool preamble. The two
                # differ, and only one of them can be what wingit printed.
                leak(
                    self.name,
                    "streamed assistant text includes tool preamble; .result does not",
                )
                yield FinalAnswer(str(ev.get("result", "")))
                if ev.get("is_error"):
                    # LEAK: subtype is "success" even here. Keying off the obvious
                    # field silently reports failures as successes.
                    leak(
                        self.name,
                        'failure hides under is_error while subtype stays "success"',
                    )
                    yield Failed(str(ev.get("result", ""))[:200])

    def finish(self, harness_exit: int) -> Iterator[Event]:
        return iter(())


# --- Opencode ---------------------------------------------------------------


class OpencodeDriver:
    name = "opencode"
    capabilities = frozenset(
        {
            Capability.RELIABLE_FAILURE,
            Capability.SESSIONS,
        }
    )

    def __init__(self) -> None:
        # LEAK: no terminal answer field, so the adapter must buffer text per step
        # and only decide what "the answer" was once the stream ends.
        self._steps: list[list[str]] = []
        self._failed: str | None = None

    def argv(self, req: Request) -> list[str]:
        argv = ["opencode", "run", "--format", "json"]
        if req.allow_tools:
            argv.append("--auto")
        return [*argv, req.prompt]

    def feed(self, line: str) -> Iterator[Event]:
        ev = _json(line)
        if ev is None:
            return
        match ev.get("type"):
            case "step_start":
                self._steps.append([])
            case "text":
                if not self._steps:
                    self._steps.append([])
                self._steps[-1].append(ev.get("part", {}).get("text", ""))
            case "tool_use":
                yield ToolActivity(ev.get("part", {}).get("tool", "?"))
            case "error":
                self._failed = str(
                    ev.get("error", {}).get("data", {}).get("message", "")
                )
                yield Failed(self._failed)
        return

    def finish(self, harness_exit: int) -> Iterator[Event]:
        if self._failed is not None:
            return
        # LEAK: the whole answer is emitted here, at the end — nothing streamed.
        # Which text belongs to "the answer" is unknowable until the last step is
        # known, so Opencode structurally cannot stream a *final-prose-only* answer.
        leak(
            self.name,
            "no terminal answer event; answer reassembled from last step at EOF — cannot stream",
        )
        if self._steps:
            text = "".join(self._steps[-1])
            if text:
                yield FinalAnswer(text)


# --- Copilot CLI ------------------------------------------------------------


class CopilotDriver:
    name = "copilot"
    capabilities = frozenset(
        {
            # The only one of the four with true token-level deltas.
            Capability.STREAMING_ANSWER,
            Capability.SESSIONS,
        }
    )

    def __init__(self) -> None:
        self._saw_answer = False
        self._final: str | None = None

    def argv(self, req: Request) -> list[str]:
        argv = [
            "copilot",
            "-p",
            req.prompt,
            "--output-format",
            "json",
            "--log-level",
            "none",
        ]
        if req.allow_tools:
            # LEAK: auto-approve is a *required flag* here, where codex has no such
            # flag at all and claude uses a mode enum. One concept, three shapes.
            argv.append("--allow-all-tools")
        return argv

    def feed(self, line: str) -> Iterator[Event]:
        ev = _json(line)
        if ev is None:
            return
        data = ev.get("data") or {}
        match ev.get("type"):
            case "assistant.message_delta":
                self._saw_answer = True
                yield AnswerChunk(data.get("deltaContent", ""))
            case "assistant.message":
                # Complete message. Empty when the turn only requested tools, so
                # "the last one" is wrong — it must be the last *non-empty* one.
                if data.get("content"):
                    self._final = data["content"]
            case "assistant.reasoning":
                # LEAK: reasoning exists as an event but its content is always ""
                # — the actual reasoning is an opaque encrypted blob. The capability
                # is present in the schema and absent in reality.
                if not data.get("content"):
                    leak(
                        self.name,
                        "assistant.reasoning carries empty content (opaque blob only)",
                    )
                else:
                    yield ReasoningChunk(data["content"])
            case "tool.execution_start":
                yield ToolActivity(data.get("name", "?"))
        return

    def finish(self, harness_exit: int) -> Iterator[Event]:
        if self._final is not None:
            yield FinalAnswer(self._final)
        if harness_exit != 0 and not self._saw_answer:
            # LEAK: failures produce *nothing* in the JSONL stream — no result
            # event, no error event. The only signal is plain text on stderr plus
            # the exit code, so this adapter cannot detect failure from stdout.
            leak(
                self.name,
                "failures emit nothing on the JSON stream; stderr+exit code only",
            )
            yield Failed("harness failed (detail only on stderr)")


# --- Codex ------------------------------------------------------------------


class CodexDriver:
    name = "codex"
    capabilities = frozenset(
        {
            Capability.SEPARABLE_REASONING,
            Capability.RELIABLE_FAILURE,
            Capability.SESSIONS,
            Capability.OS_SANDBOX,
        }
    )

    def argv(self, req: Request) -> list[str]:
        argv = ["codex", "exec", "--json", "--skip-git-repo-check"]
        if req.allow_tools:
            # LEAK: there is no approval flag on `codex exec` — it never asks. The
            # knob is a sandbox mode, a different axis entirely from "allow tools".
            leak(self.name, "no approval concept; only a sandbox mode (--sandbox)")
            argv += ["--sandbox", "workspace-write"]
        return [*argv, req.prompt]

    def feed(self, line: str) -> Iterator[Event]:
        ev = _json(line)
        if ev is None:
            return
        match ev.get("type"):
            case "item.completed":
                item = ev.get("item", {})
                match item.get("type"):
                    case "agent_message":
                        # LEAK: arrives complete, only at the end. No deltas exist.
                        leak(
                            self.name,
                            "agent_message arrives whole at end; no token deltas",
                        )
                        yield FinalAnswer(item.get("text", ""))
                    case "command_execution":
                        yield ToolActivity(item.get("command", "?")[:60])
                    case "reasoning":
                        yield ReasoningChunk(item.get("text", ""))
                    case "error":
                        yield Failed(str(item.get("message", ""))[:200])
            case "turn.failed":
                yield Failed(str(ev.get("error", {}).get("message", ""))[:200])
        return

    def finish(self, harness_exit: int) -> Iterator[Event]:
        return iter(())


# --- Pi ---------------------------------------------------------------------


class PiDriver:
    name = "pi"
    capabilities = frozenset(
        {
            Capability.STREAMING_ANSWER,
            Capability.SEPARABLE_REASONING,
            Capability.SESSIONS,
            # No sandbox of any kind; pi's own docs say project trust "is not a
            # sandbox" and bash is on by default.
        }
    )

    def __init__(self) -> None:
        self._final: str | None = None
        self._saw_answer = False

    def argv(self, req: Request) -> list[str]:
        argv = ["pi", "-p", "--mode", "json", "-nc"]
        if not req.allow_tools:
            argv.append("-nt")
        return [*argv, req.prompt]

    def feed(self, line: str) -> Iterator[Event]:
        ev = _json(line)
        if ev is None:
            return
        match ev.get("type"):
            case "message_update":
                sub = ev.get("assistantMessageEvent") or {}
                match sub.get("type"):
                    case "text_delta":
                        self._saw_answer = True
                        yield AnswerChunk(sub.get("delta", ""))
                    case "thinking_delta":
                        yield ReasoningChunk(sub.get("delta", ""))
            case "tool_execution_start":
                yield ToolActivity(str(ev.get("toolName", "?")))
            case "turn_end":
                # Last turn wins: an early turn's content is thinking + toolCall
                # with no text at all.
                text = "".join(
                    b.get("text", "")
                    for b in ev.get("message", {}).get("content", [])
                    if b.get("type") == "text"
                )
                if text:
                    self._final = text
        return

    def finish(self, harness_exit: int) -> Iterator[Event]:
        if self._final is not None:
            yield FinalAnswer(self._final)
        if harness_exit != 0 and not self._saw_answer:
            # LEAK: same shape as copilot — a failing run emits nothing at all on
            # the JSON stream; the only detail is plain text on stderr.
            leak(self.name, "failures emit nothing on the JSON stream; stderr+exit code only")
            yield Failed("harness failed (detail only on stderr)")


DRIVERS = {
    "claude": ClaudeDriver,
    "opencode": OpencodeDriver,
    "copilot": CopilotDriver,
    "codex": CodexDriver,
    "pi": PiDriver,
}
