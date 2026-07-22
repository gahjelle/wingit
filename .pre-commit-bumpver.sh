#!/bin/sh
# bumpver's pre_commit_hook: re-lock so uv.lock rides in the bump commit.
# `set -eu` matters here — without it a failed `uv lock` would still stage a
# stale lockfile and bumpver would commit, tag, and push the release anyway.
set -eu
uv lock
git add uv.lock
