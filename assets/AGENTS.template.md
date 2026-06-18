# Project Agent Rules

Use these rules when modifying this repository.

`references/protocol.md` is the canonical workflow for the safe project
improvement system. This file is a repo-local summary; if the two disagree,
follow the protocol.

## Default Code Style

- Default to beginner/intermediate-friendly code unless this repository already
  has stronger conventions.
- Follow PEP8.
- Use Google-style docstrings for public modules, classes, and functions.
- Add type hints at public boundaries and important data structures.
- Use comments as a comprehension tool for workflow intent, assumptions, side
  effects, safety constraints, and non-obvious guards.
- Prefer small maintainable changes over broad rewrites.

## Implementation Definition Of Done

Public modules, classes, and functions should have concise Google-style
docstrings unless they are clearly private or internal.

Code should be beginner/intermediate-friendly: clear names, simple control flow,
explicit side effects, understandable module boundaries, and comments where they
reduce the reader's cognitive load.

## Safe Improvement Workflow

Use this loop:

```text
inspect -> characterize -> verify setup -> audit -> backlog -> one patch -> verify
```

Do not start by refactoring. Inspect the current project structure, behavior,
tests, configuration, and entry points first.

Before audit, backlog, patch selection, or Full Automation work, build a short
Requirements Ledger internally from the user request, selected mode, repo-local
instructions, skill rules, approval boundaries, and user-provided audit/backlog
context. Must-have requirements need planned evidence or verification, and
deferrals need a reason. Show the ledger when it affects scope, approval,
backlog selection, Full Automation, deferrals, conflicts, or explicit
requirements/status reporting.

Before findings, backlog, or patch selection, make audit scope visible. State
selected audit areas, explain why they apply, and group findings by
audit family, audit area, then severity. List skipped-area details only in the
relevant skipped-area sections. Use `Engineering Audits` and
`AI System Audits` as the user-facing audit families. Use readable audit-area
blocks for Review Mode, audit outputs, persistent backlog outputs, and run
reports that include audit findings. Do not use wide Markdown tables for audit
findings; tables are only for short metadata summaries. Local Safe Refactor Mode
may report only the selected audit area and verification for one focused patch
unless the user requested a review/audit, a backlog is produced, or multiple
audit areas drive patch selection.

## One-Patch Policy

Make one focused patch at a time. Do not combine:

- refactor
- feature change
- dependency change
- UI change
- cleanup

Stop after the patch and verification unless the user asks for the next patch.
Use `references/patch-policy.md` for patch-size thresholds and split criteria.

## Characterization

Before medium/high-risk changes, create or identify characterization:

- automated tests
- smoke scripts
- golden input/output fixtures
- repeatable manual checklist

Manual characterization is temporary and should become automated when practical.

## Verification

Every code-changing patch needs verification. Prefer:

```text
make verify
```

Normal verification must not require live API keys, network access, or paid
services. Use fake clients/mocks for AI/API tests.

If verification fails, stop and report the command, failure summary, and smallest
next diagnostic step.

## Authorization Boundary

Do not push, install hooks, add strict CI, or make live API calls unless the user
explicitly authorizes that action.

In Full Automation Mode, run the pre-publish gate before commit, push, or pull
request creation/update: map findings to code/tests/docs/deferrals, recheck the
Requirements Ledger, confirm any required run report, state commit strategy,
respect or justify patch thresholds, prepare a pull request body with real
summary and verification, reject fake issue references or placeholder metadata,
check CI after push, and hand off only after process artifacts are complete.

When Codex hooks enforce Full Automation, create and maintain
`.codex/safe-project-workflow.json` before edits. Use stable item IDs such as
`P001`, keep exactly one item active while editing, run verification after the
latest write and before commit, map each commit SHA to one item, and keep
`docs/run-report.md` plus `docs/patch-backlog.md` updated with the same item IDs
and deferrals.
