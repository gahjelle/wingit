"""PROTOTYPE — run the real harnesses once and freeze their raw output.

Slow and networked. The TUI replays what this writes; you should rarely need to
re-run it.

    just prototype-seam-record            # everything
    just prototype-seam-record claude     # one harness
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
WORKSPACE = HERE / "workspace"
RECORDINGS = HERE / "recordings"

TIMEOUT_S = 180

PROSE = "Reply with exactly one word: pineapple. No other text."
TOOLS = (
    "How many markdown files are in the current directory? "
    "Look, then answer with just the number."
)
BAD_MODEL = "no-such-model-xyz"

# (harness, scenario) -> argv. Deliberately verbatim rather than generated, so the
# real flags each harness needs are visible in one place — that asymmetry is itself
# part of what the prototype is measuring.
RUNS: dict[tuple[str, str], list[str]] = {
    # --- Claude Code: stream-json, terminal `result` event.
    ("claude", "prose"): [
        "claude",
        "-p",
        PROSE,
        "--output-format",
        "stream-json",
        "--verbose",
        "--disallowedTools",
        "Bash,Glob,Grep,Read,Edit,Write,WebFetch,WebSearch",
    ],
    ("claude", "tools"): [
        "claude",
        "-p",
        TOOLS,
        "--output-format",
        "stream-json",
        "--verbose",
        "--allowedTools",
        "Bash,Glob,Read",
    ],
    ("claude", "fail"): [
        "claude",
        "-p",
        PROSE,
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        BAD_MODEL,
    ],
    # --- Opencode: no terminal result event; answer lives in `text` parts.
    ("opencode", "prose"): ["opencode", "run", "--format", "json", PROSE],
    ("opencode", "tools"): ["opencode", "run", "--format", "json", "--auto", TOOLS],
    ("opencode", "fail"): [
        "opencode",
        "run",
        "--format",
        "json",
        "--model",
        BAD_MODEL,
        PROSE,
    ],
    # --- Copilot: undocumented JSONL...
    ("copilot", "prose"): [
        "copilot",
        "-p",
        PROSE,
        "--output-format",
        "json",
        "--log-level",
        "none",
    ],
    ("copilot", "tools"): [
        "copilot",
        "-p",
        TOOLS,
        "--output-format",
        "json",
        "--allow-all-tools",
        "--log-level",
        "none",
    ],
    ("copilot", "fail"): [
        "copilot",
        "-p",
        PROSE,
        "--output-format",
        "json",
        "--model",
        BAD_MODEL,
        "--log-level",
        "none",
    ],
    # ...and the documented answer path, which is plain text. Recorded separately
    # because it may have to be the *primary* path for this harness.
    ("copilot-text", "prose"): ["copilot", "-p", PROSE, "-s", "--log-level", "none"],
    ("copilot-text", "tools"): [
        "copilot",
        "-p",
        TOOLS,
        "-s",
        "--allow-all-tools",
        "--log-level",
        "none",
    ],
    # --- Codex: cleanest JSON; read-only OS sandbox is the exec default.
    ("codex", "prose"): ["codex", "exec", "--json", "--skip-git-repo-check", PROSE],
    ("codex", "tools"): ["codex", "exec", "--json", "--skip-git-repo-check", TOOLS],
    ("codex", "fail"): [
        "codex",
        "exec",
        "--json",
        "--skip-git-repo-check",
        "-c",
        f'model="{BAD_MODEL}"',
        PROSE,
    ],
}


def record(harness: str, scenario: str, argv: list[str]) -> None:
    # NB: not Path.with_suffix — "claude.prose" has a suffix of its own and
    # with_suffix would eat the scenario.
    base = f"{harness}.{scenario}"
    print(f"  {harness}/{scenario} ... ", end="", flush=True)
    started = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(
            argv,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            check=False,
        )
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = (
            exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        )
        code = -1
    except FileNotFoundError:
        print("MISSING BINARY")
        return
    elapsed = time.monotonic() - started

    (RECORDINGS / f"{base}.stdout").write_text(stdout)
    (RECORDINGS / f"{base}.stderr").write_text(stderr)
    (RECORDINGS / f"{base}.meta.json").write_text(
        json.dumps(
            {
                "harness": harness,
                "scenario": scenario,
                "argv": argv,
                "exit_code": code,
                "timed_out": timed_out,
                "elapsed_s": round(elapsed, 1),
                "stdout_bytes": len(stdout),
                "stderr_bytes": len(stderr),
            },
            indent=2,
        )
        + "\n"
    )
    flag = "TIMEOUT" if timed_out else f"exit={code}"
    print(f"{flag} {elapsed:.0f}s  out={len(stdout)}B err={len(stderr)}B")


def main() -> None:
    RECORDINGS.mkdir(exist_ok=True)
    WORKSPACE.mkdir(exist_ok=True)
    only = sys.argv[1:]
    for (harness, scenario), argv in RUNS.items():
        if only and harness not in only:
            continue
        record(harness, scenario, argv)


if __name__ == "__main__":
    main()
