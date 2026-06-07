---
name: safe-project-improvement-system
description: >-
  Use this skill when the user wants to safely review, audit, refactor, or
  improve a Python or AI-integrated project with characterization, local
  verification, focused patches, fake-client tests, and explicit approval gates
  for push, hooks, CI, or full automation.
---

# Safe Project Improvement System

Use this skill to improve a Python or AI-integrated project safely. The operating
loop is:

```text
inspect -> characterize -> verify setup -> audit -> backlog -> one patch -> verify
```

`references/protocol.md` is the authoritative workflow for this skill. The
sections below are a compact operating summary for agent use.

Do not begin with refactoring. First understand the project, current behavior,
verification surface, and risks.

## Adoption Context

This skill may be used from a shared external repository, from a small repo-local
guidance install, or from a vendored full copy under a target repository such as
`skills/safe_project_improvement_system/`.

Installing a few templates is not the same as vendoring the full skill bundle.

If the target repository already has `AGENTS.md`, `Makefile`, `verify.sh`, or
similar local files, merge carefully instead of overwriting them.

When the skill is vendored into another repository for traceability, it is
usually a `development/support skill`, not a runtime/project skill, unless that
repository explicitly integrates it into runtime behavior.

## Mode Selection

- **Review Mode**: inspect, characterize, audit, and produce a prioritized
  backlog. Do not edit files.
- **Local Safe Refactor Mode**: create or confirm characterization and
  verification, apply one small patch, run local verification, then stop. Use
  this by default when the user asks to refactor or improve code.
- **Full Automation Mode**: create a branch, add verification/tests, patch,
  commit, push, create or update a pull request when approved, wait for CI, and
  report. Use only after explicit user approval.

If the user says audit, review, or planning only, use Review Mode.

All modes consider a lightweight Requirements Ledger before audit, backlog,
patch, or Full Automation work. The ledger tracks must/should requirements from
the user request, selected mode, repo-local instructions, skill rules, approval
boundaries, and user-provided audit/backlog context. Must-have requirements need
planned evidence or verification, and deferrals need a reason. Show the ledger
only when it affects scope, approval, backlog selection, Full Automation,
deferrals, conflicts, or the user asks for requirements/status.

All modes pass through an Audit Scope Gate before findings, backlog, or patch
selection. Make selected audit areas visible and explain what will be checked
and why it applies; list skipped-area details only in the relevant skipped-area
sections. The canonical audit/report format uses readable
blocks for every checked `Engineering Audits` or `AI System Audits` area,
followed by `Skipped Engineering Areas` and `Skipped AI System Areas` sections.
This block format is mandatory for Review Mode, audit outputs, persistent
backlog outputs, and run reports that include audit findings. Local Safe
Refactor Mode may report only the selected audit area and verification for one
focused patch unless the user requested a review/audit, a backlog is produced,
or multiple audit areas drive patch selection.

## Non-Negotiable Rules

- Use one lead agent for edits.
- Always inspect the project before changing it.
- Characterization is mandatory before medium/high-risk code changes.
- Every code-changing patch needs verification.
- Do not combine refactor, feature change, dependency change, UI change, and
  cleanup in one patch.
- Do not push, install hooks, or add strict CI unless explicitly authorized.
- Use fake clients/mocks for AI/API tests.
- Normal verification must not require live API keys.
- Distinguish characterization tests, patch tests, regression tests, smoke
  tests, and full verification.
- Review Mode, audit outputs, persistent backlog outputs, and run reports with
  audit findings must use the required block-based audit format, not wide
  Markdown tables and not only a free-text findings list. Tables may only be used
  for short metadata summaries, not detailed findings.
- Full Automation Mode must pass the pre-publish gate before commit, push, or
  pull request creation/update.
- Stop if verification fails.

## Reference Loading

Load only the references needed for the current task:

Review mode always loads `references/protocol.md`,
`references/audit-matrix.md`, and `references/coding-standards.md`.

Deep audit references are optional. In review mode, load
`references/engineering-audits.md` for software engineering quality reviews,
including deeper general software testing strategy. Load
`references/ai-workflow-audits.md` for AI System Audits: AI Software
Architecture, prompts, APIs, RAG, tools, agents, speech, cost, evaluation, and
multi-step AI/tool automation. Use `references/ai-integration-quality.md` as
extra implementation guidance when working directly on model/provider, prompt,
RAG, or evaluation code. Load both engineering and AI System references only
when the repository clearly has both general software architecture risks and
AI-system-specific risks. Do not load deep audit references in safe refactor mode unless the patch directly touches that area.

- `references/protocol.md`: read first for the full workflow and mode details.
- `references/coding-standards.md`: read before reviewing, editing,
  refactoring, or installing project-local rules.
- `references/characterization.md`: read before medium/high-risk changes or
  when current behavior is unclear.
- `references/audit-matrix.md`: read for review/audit/backlog work.
- `references/engineering-audits.md`: read when review mode needs deeper
  general software architecture, error handling, testability, validation,
  documentation, hygiene, UI separation, software delivery testing, or security
  checks.
- `references/ai-workflow-audits.md`: read when review mode needs deeper prompt,
  AI Software Architecture, structured output, RAG, agent/tool, speech, cost, or
  workflow automation checks under `AI System Audits`.
- `references/patch-policy.md`: read before making code changes.
- `references/testing-strategy.md`: read when adding or repairing verification.
- `references/ai-integration-quality.md`: read for prompts, providers, APIs,
  RAG, tools, agents, or evaluation.
- `references/branching-ci-hooks.md`: read only for explicit branch, hook, CI,
  commit, push, or full automation requests.

## Implementation Definition Of Done

For implementation work, public modules, classes, and functions should have
concise Google-style docstrings unless they are clearly private or internal.

Code should be beginner/intermediate-friendly: clear names, simple control flow,
explicit side effects, understandable module boundaries, and comments where they
reduce the reader's cognitive load.

## Assets

Use `assets/` as project templates, adapting them to the target repository:

- `AGENTS.template.md`: project-local agent rules.
- `development-skill-note.template.md`: local note for repositories that need
  to document this system as a development/support skill.
- `Makefile.template` and `verify.sh.template`: minimal local verification.
- `pyproject.template.toml`: beginner-friendly pytest/ruff defaults.
- `pre-commit-config.template.yaml`: low-risk hooks with optional ruff.
- `github-actions-verify.template.yaml`: CI template that runs `make verify`
  without live secrets.
- `behavior-inventory-template.md`: behavior characterization worksheet.
- `patch-backlog-template.md`: prioritized improvement backlog.
- `run-report-template.md`: required audit trail for full automation and
  optional audit trail for review, medium/high-risk patches, verification
  failures, or persistent backlogs.

## Default Output

When work is complete, report:

- audit scope selected, with skipped-area details only in skipped sections
- Requirements Ledger status for must-have items and deferrals
- mode used
- files changed
- findings in the required block-based audit format
- characterization added or confirmed
- verification command and result
- any stopped work, failed verification, or approval needed
