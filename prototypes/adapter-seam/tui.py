"""PROTOTYPE — replay recorded harness output through the candidate seam.

    just prototype-seam

Pick a harness and a scenario; see what the seam yields, and — the point of the
whole exercise — what it had to leak to get there.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from adapters import DRIVERS  # noqa: E402
from seam import LEAKS, Capability, Outcome, divergence, reset_leaks, run  # noqa: E402

RECORDINGS = Path(__file__).parent / "recordings"

HARNESSES = ["claude", "opencode", "copilot", "codex"]
SCENARIOS = ["prose", "tools", "fail"]

B, D, R = "\x1b[1m", "\x1b[2m", "\x1b[0m"
RED, GREEN, YELLOW, CYAN = "\x1b[31m", "\x1b[32m", "\x1b[33m", "\x1b[36m"


def load(harness: str, scenario: str) -> tuple[str, str, dict] | None:
    meta_path = RECORDINGS / f"{harness}.{scenario}.meta.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text())
    stdout = (RECORDINGS / f"{harness}.{scenario}.stdout").read_text()
    stderr = (RECORDINGS / f"{harness}.{scenario}.stderr").read_text()
    return stdout, stderr, meta


def replay(harness: str, scenario: str) -> tuple[Outcome, list, dict, str] | None:
    loaded = load(harness, scenario)
    if loaded is None:
        return None
    stdout, stderr, meta = loaded
    reset_leaks()
    driver = DRIVERS[harness]()
    outcome = run(driver, stdout, meta["exit_code"])
    return outcome, list(LEAKS), meta, stderr


def render(harness: str, scenario: str) -> None:
    print("\033[2J\033[H", end="")
    print(f"{B}adapter seam prototype{R} {D}— issue #13{R}\n")

    # Selector row.
    row = "  ".join(
        f"{B}{CYAN}[{h[0]}] {h}{R}" if h == harness else f"{D}[{h[0]}] {h}{R}"
        for h in HARNESSES
    )
    print(f"  {row}")
    row = "  ".join(
        f"{B}{CYAN}[{s[0]}] {s}{R}" if s == scenario else f"{D}[{s[0]}] {s}{R}"
        for s in SCENARIOS
    )
    print(f"  {row}\n")

    result = replay(harness, scenario)
    if result is None:
        print(f"  {D}(no recording for {harness}/{scenario}){R}\n")
        footer()
        return
    outcome, leaks, meta, stderr = result

    caps = DRIVERS[harness].capabilities
    print(f"  {B}declared capabilities{R}")
    for cap in Capability:
        mark = f"{GREEN}yes{R}" if cap in caps else f"{D} no{R}"
        print(f"    {mark}  {D}{cap.value}{R}")
    print()

    print(f"  {B}what `a` would emit{R}")
    streamed = outcome.answer.strip() or f"{D}(nothing streamed){R}"
    final = (outcome.final_answer or "").strip() or f"{D}(no final-answer field){R}"
    div = divergence(outcome)
    mark = f" {RED}<-- diverges{R}" if div and outcome.answer else ""
    print(f"    {D}streamed:{R} {streamed[:250]}{mark}")
    print(f"    {D}final   :{R} {final[:250]}")
    reasoning = " | ".join(x.strip() for x in outcome.reasoning if x.strip())
    print(f"    {D}stderr  :{R} {reasoning[:150] or D + '(silent)' + R}")
    print(f"    {D}tools   :{R} {', '.join(outcome.tools)[:150] or D + '(none)' + R}")
    code_colour = GREEN if outcome.exit_code == 0 else RED
    print(
        f"    {D}exit    :{R} {code_colour}{outcome.exit_code}{R} "
        f"{D}(harness exited {meta['exit_code']}){R}"
    )
    if outcome.failure:
        print(f"    {D}failure:{R} {RED}{outcome.failure[:150]}{R}")
    print()

    # The streaming question: did the first answer byte arrive early or at EOF?
    print(f"  {B}streaming{R}")
    if div:
        print(f"    {YELLOW}{div}{R}")
    if outcome.first_answer_at is None and outcome.answer:
        print(
            f"    {RED}answer only available at EOF{R} "
            f"{D}— nothing could have streamed{R}"
        )
    elif outcome.answer:
        pct = 100 * (outcome.first_answer_at + 1) / max(outcome.total_lines, 1)
        print(
            f"    {GREEN}first answer byte at line "
            f"{outcome.first_answer_at + 1}/{outcome.total_lines}{R} {D}({pct:.0f}% in){R}"
        )
    else:
        print(f"    {D}n/a — no answer{R}")
    print()

    print(f"  {B}seam leaks{R} {D}— where the interface did not fit{R}")
    if not leaks:
        print(f"    {GREEN}none{R}")
    for _, what in leaks:
        print(f"    {YELLOW}!{R} {what}")
    print()

    if stderr.strip():
        print(f"  {B}raw harness stderr{R}")
        print(f"    {D}{stderr.strip()[:200]}{R}\n")

    footer()


def footer() -> None:
    print(
        f"  {D}harness:{R} {B}c{R}laude {B}o{R}pencode c{B}p{R}ilot {B}x{R}codex"
        f"   {D}scenario:{R} {B}1{R}prose {B}2{R}tools {B}3{R}fail"
        f"   {D}|{R} {B}a{R}ll  {B}q{R}uit"
    )


def summary() -> None:
    """Cross-harness leak tally — the actual finding, on one screen."""
    print("\033[2J\033[H", end="")
    print(f"{B}seam leaks across all harnesses × scenarios{R} {D}— issue #13{R}\n")
    total = 0
    for h in HARNESSES:
        seen: set[str] = set()
        for s in SCENARIOS:
            result = replay(h, s)
            if result is None:
                continue
            for _, what in result[1]:
                seen.add(what)
        total += len(seen)
        print(f"  {B}{h}{R} {D}({len(seen)} distinct){R}")
        for what in sorted(seen):
            print(f"    {YELLOW}!{R} {what}")
        print()
    print(f"  {B}total distinct leaks: {total}{R}\n")
    print(f"  {D}any key to go back{R}")


def main() -> None:
    import termios
    import tty

    harness, scenario = "claude", "prose"
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        render(harness, scenario)
        while True:
            key = sys.stdin.read(1).lower()
            match key:
                case "q":
                    break
                case "c":
                    harness = "claude"
                case "o":
                    harness = "opencode"
                case "p":
                    harness = "copilot"
                case "x":
                    harness = "codex"
                case "1":
                    scenario = "prose"
                case "2":
                    scenario = "tools"
                case "3":
                    scenario = "fail"
                case "a":
                    summary()
                    sys.stdin.read(1)
                case _:
                    pass
            render(harness, scenario)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        print("\033[2J\033[H", end="")


if __name__ == "__main__":
    main()
