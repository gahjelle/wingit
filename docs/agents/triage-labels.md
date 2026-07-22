# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

## Repo-local roles

Beyond the five canonical roles, this repo uses one more:

| Label          | Meaning                                        |
| -------------- | ---------------------------------------------- |
| `needs-design` | Sliced and ordered, awaiting its design session |

`needs-design` exists because the MVP is delivered as ten tracer bullets that were **sliced but deliberately not specified** ([Epic: MVP](https://github.com/gahjelle/wingit/issues/34)). A tracer carries it from creation until its `/grill-with-docs` design session finishes, then flips to `ready-for-agent`.

It is not `needs-triage`: these issues have been evaluated more thoroughly than anything else in the repo. And it is not mere absence of a label, which a future triage sweep could not distinguish from "nobody looked yet".

Edit the right-hand column to match whatever vocabulary you actually use.
