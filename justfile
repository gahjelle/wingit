default: check

# Run all quality gates in order, stopping on the first failure.
check: fmt-check lint conventions typecheck test audit-workflows

# Audit the GitHub Actions workflows for security issues with zizmor (offline).
audit-workflows:
    uv run zizmor .github/workflows -q --offline

# Audit workflows online: adds network-backed rules (e.g. known-vulnerable-actions).
audit-workflows-ci:
    uv run zizmor .github/workflows -q

# Pin every workflow `uses:` to a commit SHA with gha-update.
pin-workflows:
    uv run gha-update

# Cut a release: bump the version, re-lock, commit, tag, and push.
release *args:
    uv run bumpver update --patch {{args}}

# Auto-format the codebase with ruff.
fmt:
    uv run ruff format -q

# Check formatting without writing changes.
fmt-check:
    uv run ruff format --check -q

# Lint the codebase with ruff.
lint:
    uv run ruff check -q

# Type-check src/ and tests/ with ty.
typecheck:
    uv run ty check -q

# Enforce repo-specific conventions ruff/ty can't express.
conventions *args:
    uv run garuff check -q {{args}}

# Run the test suite quietly.
test *args:
    uv run pytest -q {{args}}

# Auto-fix lint issues then reformat.
fix:
    uv run ruff check --fix -q
    uv run garuff check --fix
    uv run ruff format -q

# Requires all five harnesses installed and logged in. Proves the spawn contract
# (stdin=DEVNULL, cwd-on-child, tools-at-write), the pipe contract, and Ctrl-C.
# Manual liveness check against the real five harnesses — never in `check`, never CI.
live-check:
    #!/usr/bin/env bash
    set -uo pipefail
    a=".venv/bin/a"
    uv sync --quiet
    ask="how many markdown files are in the current directory? Answer with just the number."
    for flag in -cl -cp -cx -oc -pi; do
        echo "=== a ${flag} (ask-cwd) ==="
        "$a" "$flag" "$ask"
        echo "  -> exit $?"
    done
    echo "=== pipe smoke (Answer verbatim, one newline, no markup) ==="
    out=$("$a" "reply with exactly one word: pineapple" | cat)
    printf 'stdout: %q\n' "$out"
    echo "=== scripted SIGINT (expect exit 130, no surviving child) ==="
    "$a" "count slowly from 1 to 60, one number per line, pausing to think between each" &
    pid=$!
    sleep 2
    kill -INT "$pid"
    wait "$pid"; code=$?
    echo "  -> exit ${code} (expect 130)"
    if pgrep -P "$pid" >/dev/null; then echo "  !! FAIL: surviving child"; else echo "  -> no surviving child"; fi
