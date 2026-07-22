# Sessions build on native harness sessions via a name→UUID registry

> **Status: superseded by [ADR-0008](0008-follow-up-not-named-sessions.md).**
> Kept for history. **Do not treat anything below as current.** Named sessions, `-s <name>`
> and the name→UUID registry **do not exist**; wingit ships a single follow-up flag over a
> bounded LRU pointer cache. Decided in
> [issue #17](https://github.com/gahjelle/wingit/issues/17). Nothing here is inherited.

"Selective memory" is implemented by leaning on each harness's native session/resume
rather than wingit owning a portable transcript. wingit stores a mapping from a short
user-assigned session name to the harness's native session UUID, and a session is bound
to the harness that created it.

## Consequences

- Sessions do not transfer between harnesses — an accepted non-goal for now ("translating
  sessions" is a possible future direction, not a priority).
- Far less to build, and we get full-fidelity harness memory rather than a lossy
  wingit-owned transcript (wingit only sees stdout/stderr, not the harness's internal
  trajectory).
