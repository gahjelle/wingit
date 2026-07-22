default: check

# Run all quality gates in order, stopping on the first failure.
check: fmt-check lint conventions typecheck test

# Cut a release: bump the CalVer version, re-lock, commit, tag, and push.
# Bare `just release` rolls the month over; a second release within the same
# month needs `just release --patch`.
release *args:
    uv run bumpver update {{args}}

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
