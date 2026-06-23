# SEL-121 — Decide whether to move the backlog from in-repo files to GitHub Issues

| | |
|---|---|
| **Type** | Research / Process |
| **Area** | repo / process |
| **Priority** | Low |
| **Status** | Open |

## Context

The backlog is a folder of `SEL-NNN-slug.md` files (this directory) with a hand-maintained index in
`README.md`. It is simple, versioned with the code, reviewable in a PR, and works offline. The
question is whether — even for a project this small — the benefits of GitHub Issues outweigh the
small extra process they impose. Note this repo is also a **showcase/portfolio piece**, so the
*visible* choice of tooling is itself a signal, not only an internal convenience.

## Trade-offs

**Keep in-repo files**
- Pros: zero tooling, atomic with the change that resolves them (the fix and the ticket close in one
  commit), greppable, no network, full control over format, diffable history per ticket.
- Cons: manual ID allocation and index upkeep, no first-class state/labels/assignee/search, no
  automatic PR↔ticket cross-linking, cross-references are relative paths that break on move (just
  hit during the SEL-142 → `resolved/` move).

**Move to GitHub Issues**
- Pros: native state machine, labels/milestones/assignees, `Fixes #N` auto-closes from PRs, backlinks
  and search for free, lower friction to file a quick bug, more legible to an outside reader/recruiter
  browsing the repo.
- Cons: state lives outside the repo (not versioned, not offline, harder to snapshot), some setup
  (labels mirroring our Area/Type/Priority, issue templates), and a one-time migration of ~20 tickets.

## Options

1. **Stay as-is** — keep the file backlog; accept the manual upkeep.
2. **Full move to Issues** — migrate all open tickets, add issue templates + labels, retire this
   folder (leave a README pointer). `resolved/` becomes closed issues.
3. **Hybrid** — Issues for day-to-day tracking; keep a thin in-repo design note only for tickets that
   carry real architectural reasoning (e.g. SEL-120), linked from the issue.

## Proposed work (if we move)

- Map Area/Type/Priority to labels; add a bug + an engineering issue template.
- Script the migration (the files are uniform front-matter + markdown — `gh issue create` in a loop).
- Decide the fate of `resolved/` and the README index; add a CONTRIBUTING note on the new flow.

## Why it matters

Small but compounding: the right answer removes recurring manual upkeep (IDs, index, relative-link
breakage) and makes the backlog legible to anyone browsing the repo — at the cost of moving state out
of version control. Worth a deliberate decision rather than drifting.

**Source:** session discussion after the SEL-142 resolution · **Touches:** `docs/tickets/` (whole)
