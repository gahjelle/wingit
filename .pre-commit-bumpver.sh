#!/bin/sh
# Re-lock so uv.lock rides in the bump commit. `set -eu` keeps a failed
# `uv lock` from staging a stale lockfile and releasing it anyway.
set -eu
uv lock
git add uv.lock
