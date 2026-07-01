# Sessions build on native harness sessions via a name→UUID registry

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
