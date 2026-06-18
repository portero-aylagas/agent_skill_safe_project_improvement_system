# Protocol

Use this protocol for safe project improvement with one lead editing agent.

## Default Workflow

```text
inspect -> characterize -> verify setup -> audit -> backlog -> one patch -> verify
```

## Non-Negotiable Rules

- Use one lead agent for edits.
- Always inspect the project before changing it.
- Characterization is mandatory before medium/high-risk changes.
- Every code-changing patch needs verification.
- Do not combine refactor, feature change, dependency change, UI change, and
  cleanup in one patch.
- Do not push, install hooks, or add strict CI unless explicitly authorized.
- Use fake clients/mocks for AI/API tests.
- Normal verification must not require live API keys.
- Stop if verification fails.

## Step 1: Inspect

Identify:

- project type and entry points
- package manager and runtime
- tests, scripts, Makefile targets, CI, hooks, and linting
- environment variables and live-service dependencies
- public interfaces, schemas, prompts, and provider boundaries
- uncommitted or unrelated work that must not be reverted

Do not make code changes during inspection.

## Step 2: Characterize

Before medium/high-risk changes, capture current behavior with one of:

- existing automated tests
- new focused characterization tests
- a smoke script with fake clients
- a repeatable manual checklist

Manual characterization is acceptable temporarily, but prefer automation when
practical.

## Step 3: Verify Setup

Find or add a normal local verification command. Prefer:

```text
make verify
```

Verification should normally include import/compile checks and tests. It must not
require live API keys.

## Requirements Ledger

Before audit, backlog, patch selection, or Full Automation work, build a short
Requirements Ledger internally. This is an operational checklist, not a PRD, and
it does not always need to be printed in the final response.

Extract ledger rows from:

- the user request
- selected mode
- repo-local instructions such as `AGENTS.md`
- skill rules
- explicit approval boundaries
- previous audit findings or backlog items, if the user provided them

Use this shape:

| Requirement | Source | Must/Should | Planned Evidence Or Verification | Status Or Deferral |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

Generic examples:

| Requirement | Source | Must/Should | Planned Evidence Or Verification | Status Or Deferral |
| --- | --- | --- | --- | --- |
| Use Review Mode | User request | Must | Report mode used and files changed: none | Planned |
| Do not edit files | Review Mode | Must | `git status` / final files changed report | Planned |
| Run verification | Skill protocol | Must for code changes | `make verify` result | Planned |
| Create run report | Full Automation Mode | Must when required | Report path in final response | Planned |

Rules:

- Must-have requirements need planned evidence or verification before work
  proceeds.
- If a requirement is deferred, state why in `Status Or Deferral`.
- Keep the ledger short and operational. Do not turn it into a project
  requirements document.
- Show the ledger when it affects audit scope, approval boundaries, backlog
  selection, Full Automation, deferrals, conflicting requirements, or when the
  user explicitly asks for requirements or status.
- For trivial Local Safe Refactor Mode changes, the final response may summarize
  only must-have requirement status instead of showing the full ledger table.
- In Review Mode, the ledger can be shown briefly before the audit blocks when
  it helps explain scope or constraints.
- In Full Automation Mode, check the ledger again before commit, push, or pull
  request creation/update.

## Audit Scope Gate

Before audit, backlog, or patch selection in any mode, make the audit scope
visible.

First inspect enough project structure to choose relevant audit areas. Then
report:

- selected audit families and areas
- what each selected area checks
- why each selected area applies to this repository
- that skipped audit areas, if any, are listed only in the relevant skipped-area
  section

Ask the user to choose the scope unless the prompt already gives explicit scope.
If interaction is unavailable, proceed with the recommended relevant scope and
report that default.

Use these user-facing audit families:

- `Engineering Audits`
- `AI System Audits`

`AI System Audits` covers AI software architecture, prompts, model/API
integrations, RAG, agents, tools, speech, cost, and multi-step AI/tool
automation. `Workflow Automation` is an audit area inside `AI System Audits`; it
means trigger conditions, idempotency, retries, state transitions, approvals,
logs, run IDs, recovery paths, and cost controls.

## Step 4: Audit

Run only audits relevant to the project. Use `audit-matrix.md` to choose checks.
Record findings as backlog items with risk, expected behavior, and verification.
When reviewing software engineering quality, assess conformance to
`coding-standards.md`; it is the source of truth for code-level standards.

Group findings by audit family, then audit area, then severity. Do not return a
single mixed severity list.

Readable block-based audit reporting is the canonical audit/report format.
Do not use wide Markdown tables for audit findings in chat responses or persisted
Markdown reports. The block format is mandatory for Review Mode, audit outputs,
persistent backlog outputs, and run reports that include audit findings. Local
Safe Refactor Mode does not need to print full audit blocks unless the user
requested a review/audit, a backlog is produced, or patch selection depends on
multiple audit areas. If only one focused patch is implemented, the agent may
report the selected audit area and verification without printing every checked
audit area block.

For every checked `Engineering Audits` area with findings, list one block:

## <Audit Area>

- Severity: High | Medium | Low | Info
- Finding: <finding>
- Evidence / Location: <files, functions, commands>
- Recommended Action: <action>
- Verification: <test, command, review method>

For every checked `Engineering Audits` area with no material findings, use the
compact form:

## <Audit Area>

No material findings.

Evidence:

- <brief evidence, if useful>

Verification:

- <brief verification, if useful>

After all checked `Engineering Audits` areas, add:

## Skipped Engineering Areas

- <Audit Area>: <reason>

For every checked `AI System Audits` area with findings, list one block:

## <Audit Area>

- Severity: High | Medium | Low | Info
- Finding: <finding>
- Evidence / Location: <files, functions, commands>
- Recommended Action: <action>
- Verification: <test, command, review method>

For every checked `AI System Audits` area with no material findings, use the
compact form:

## <Audit Area>

No material findings.

Evidence:

- <brief evidence, if useful>

Verification:

- <brief verification, if useful>

After all checked `AI System Audits` areas, add:

## Skipped AI System Areas

- <Audit Area>: <reason>

Rules:

- Do not omit checked areas.
- Checked areas with no material findings must still appear in the compact form.
- Do not include the old checked marker, none-severity placeholder, or empty
  recommended-action placeholder.
- Skipped areas do not need full blocks. List them only under the relevant
  skipped-area section with a reason.
- If no areas were skipped for a family, write
  `- None: all relevant areas were checked`.
- Use severity values consistently: `High`, `Medium`, `Low`, or `Info`.
- Tables may only be used for short metadata summaries, not detailed findings.
- Do not return only a free-text findings list. Brief narrative summaries are
  allowed before or after the audit blocks.
- Backlog items should trace to audit blocks.

## Step 5: Backlog

Prioritize small patches. Each backlog item should name:

- audit family
- audit area
- severity
- user-visible value or risk reduction
- files likely affected
- patch risk level
- characterization requirement
- verification command

## Step 6: One Patch

Apply one small patch only. Do not combine unrelated change types. A patch must be
small enough that failure is easy to understand and revert manually.

## Step 7: Verify

Run the agreed verification for the whole relevant repository surface, not only
the new or focused test. Stop if it fails. Report the failure, what changed, and
the smallest next diagnostic step.

## Run Artifacts

Use `assets/run-report-template.md` when a run needs a durable audit trail.
Create a run report when:

- the user asks for an audit log or run artifact
- the mode is full automation
- the patch is medium/high risk
- verification fails
- the run produces a backlog intended to persist

For low-risk local patches, the final chat report is usually enough.

## Modes

### Review Mode

Use when the user asks for audit, review, assessment, backlog, or planning.
Pass through the Audit Scope Gate before producing findings or backlog items.
Show the Requirements Ledger briefly before the audit blocks when it
affects scope, constraints, deferrals, or approval boundaries.

Always load:

- `references/protocol.md`
- `references/audit-matrix.md`
- `references/coding-standards.md`

For software engineering quality reviews, also load
`references/engineering-audits.md`. For AI System Audits, also load
`references/ai-workflow-audits.md`; use
`references/ai-integration-quality.md` as extra implementation guidance when
working directly on model/provider, prompt, RAG, or evaluation code.

Allowed:

- inspect files
- run safe read-only commands
- run existing verification when useful
- create a written backlog in the response

Not allowed:

- edit files
- add tests
- install hooks
- create branches
- commit or push

### Local Safe Refactor Mode

Use by default when the user asks to refactor or improve code.
Pass through the Audit Scope Gate before selecting the one patch.

Allowed:

- inspect project
- add or confirm verification
- add characterization before medium/high-risk change
- make one small local patch
- run local verification

Stop after one patch and report. Continue only if the user asks for another
patch.

### Full Automation Mode

Use only with explicit approval.
Pass through the Audit Scope Gate before backlog, patch selection, run report,
or CI follow-up work.

Allowed after approval:

- create a branch
- add verification and characterization
- make one small patch
- commit
- push
- create or update a pull request when explicitly approved
- wait for CI
- report CI result

Still required:

- no live API keys in normal verification
- no unrelated cleanup
- stop on verification failure

When hook enforcement is enabled, Full Automation also requires durable
machine-readable workflow state at `.codex/safe-project-workflow.json` before
edits. Use stable backlog item IDs such as `P001`, keep exactly one item active
while editing, record verification after the latest write and before commit, map
each commit SHA to one item, and keep `docs/run-report.md` plus
`docs/patch-backlog.md` aligned with the same item IDs. Unfinished items must be
completed or explicitly deferred in both workflow state and the run report.

Before commit, push, or pull request creation/update, run a pre-publish gate:

- all selected findings are mapped to code, tests, docs, or explicit deferral
- Requirements Ledger must-have items are satisfied or explicitly deferred
- run report exists when required
- commit strategy is explicit
- patch size/scope thresholds are respected or justified
- pull request body has real summary and verification
- pull request body contains no fake issue references or placeholder metadata
- CI result is checked after push
- final handoff happens only after process artifacts are complete
