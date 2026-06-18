# Safe Project Improvement System

Safe Project Improvement System is a promptable development workflow for AI
coding agents. It helps a user ask an agent to inspect, review, refactor, and
improve a Python or AI-integrated repository without jumping straight into risky
edits.

This is not a runtime library or CLI. A user uses it by putting these files where
the agent can read them, choosing a mode, and prompting the agent to use the safe
project improvement system.

The default workflow is:

```text
inspect -> characterize -> verify setup -> audit -> backlog -> one patch -> verify
```

`references/protocol.md` is the canonical workflow. This README is the practical
user guide; if the two ever disagree, update the README to match the protocol.

## Use This Skill In Any Repo

### 1. Make the skill available

Use the smallest adoption mode that fits the target repository:

- **External Reference Mode**: keep this repository in the same workspace as the
  target repo and tell the agent to use it.
- **Repo-Local Guidance Mode**: copy only useful templates, such as `AGENTS.md`,
  `Makefile`, or `verify.sh`, into the target repo.
- **Vendored Skill Mode**: copy this full bundle into the target repo, usually
  under `skills/safe_project_improvement_system/`.
- **Hybrid Mode**: keep this full bundle external while adding lightweight local
  instructions in the target repo.

Use Hybrid Mode or Vendored Skill Mode when you want the optional enforcement
layer. External Reference Mode can guide an agent, but it cannot reliably
enforce target-repo behavior because the hook handler, policy, and Codex config
are not local to the repository being changed.

Vendoring this folder does not automatically register a native skill in every
coding tool. The practical requirements are that the files are present, local
instructions point to `SKILL.md`, and the prompt explicitly says to use the
system.

Do not blindly overwrite an existing `AGENTS.md`, `Makefile`, `verify.sh`, or
`pyproject.toml`. Merge or adapt templates carefully.

### 2. Choose the mode

| Mode | Use when | What the agent may do |
| --- | --- | --- |
| **Review Mode** | You want an audit, assessment, plan, or prioritized backlog. | Inspect files, run safe read-only checks, run existing verification when useful, and return findings. It must not edit files. |
| **Local Safe Refactor Mode** | You want one local improvement made safely. | Inspect, confirm or add verification, characterize risky behavior, apply one small patch, run verification, and stop. |
| **Full Automation Mode** | You explicitly approve branch, commit, push, pull request, and CI follow-up work. | Create a branch, patch, commit, push, wait for CI, and report. Use only after explicit approval. |

All modes consider a lightweight Requirements Ledger before audit, backlog,
patch, or Full Automation work. It is a short operational checklist extracted
from the user request, selected mode, repo-local instructions, skill rules,
approval boundaries, and user-provided audit/backlog context. The agent should
show it only when it affects scope, approval, backlog selection, Full
Automation, deferrals, conflicts, or explicit requirements/status reporting.

All modes pass through the Audit Scope Gate before findings, backlog, or patch
selection. The agent should state selected audit areas and explain why they
apply; skipped-area details belong only in the relevant skipped-area sections.
Readable audit-area blocks are the canonical audit format and are
mandatory for Review Mode, audit outputs, persistent backlog outputs, and run
reports that include audit findings. Checked areas with findings use the full
field block, checked areas with no material findings use the compact form, and
skipped areas are listed separately with reasons.
Tables may only be used for short metadata summaries, not detailed findings. A
trivial Local Safe Refactor Mode patch can report the selected audit area and
verification without printing full audit blocks unless the user requested review
or a backlog.

### 3. Paste a prompt

Use review mode when you want evidence and a backlog before edits:

```text
Use the safe project improvement system in review mode.
Inspect this repository, characterize current behavior, run all relevant audits,
and produce a prioritized backlog.
Do not edit files.
```

Use local safe refactor mode when you want one improvement implemented:

```text
Use the safe project improvement system in local safe refactor mode.
Inspect this repository, state the audit scope, confirm verification, and apply
one small safe patch.
Run verification and stop after one patch.
```

Use this when continuing from a backlog:

```text
Use the safe project improvement system in local safe refactor mode.
Take the next highest-priority backlog item, confirm characterization and
verification, apply only that patch, run verification, and stop.
```

Use this when a repo has no clear verification command:

```text
Use the safe project improvement system to add a minimal verification setup.
Prefer make verify.
Do not require live API calls, network services, or paid services.
Add characterization tests before risky refactors.
```

Use full automation only after approving branch, commit, push, pull request, and
CI work:

```text
Use the safe project improvement system in full automation mode.
Create a focused branch, confirm verification, make one small safe patch, commit,
push, wait for CI, and report the result.
Run the pre-publish gate before commit, push, or PR creation/update.
Stop if verification or CI fails.
```

Use this when the skill is vendored into the target repo:

```text
Use the vendored safe project improvement system under
skills/safe_project_improvement_system/.
Treat it as a development/support skill, not as a runtime component of this
application.
Do not replace existing local instruction files; merge or adapt carefully.
```

### 4. Expect the agent to stop safely

The agent should:

- inspect before editing
- track must-have requirements and deferrals in a short Requirements Ledger,
  showing it only when it materially affects the work or the user asks
- make audit scope visible before findings, backlog, or patch selection
- report Review Mode, audit, persistent backlog, and audit run-report findings
  using the required block-based audit format
- characterize current behavior before medium/high-risk changes
- keep each patch focused and small
- verify locally after each patch
- avoid live API keys, network calls, and paid services in normal tests
- avoid pushing, installing hooks, or adding strict CI without explicit approval
- stop after one patch unless the user asks for another

Default code style:

```text
Beginner/intermediate-friendly, PEP8, Google-style docstrings, type hints at
boundaries, clear inline workflow comments, small maintainable changes, Ruff
with pydocstyle for public docstrings.
```

## Audit Families

All modes use the same audit families when they produce findings or backlog
items:

- `Engineering Audits`
- `AI System Audits`

### Engineering Audits

These checks focus on whether the software is understandable, maintainable,
testable, and safe to change.

| Area | Example intent |
| --- | --- |
| General Software Architecture | Check whether modules, orchestration, business logic, UI code, file I/O, external service calls, config, and utilities are separated clearly enough to grow safely. AI-specific code should connect through clear application boundaries, but AI component design belongs under `AI Software Architecture`. |
| Function Responsibility | Find functions that do too many jobs, hide side effects, or have names that do not match behavior. |
| Error Handling | Look for swallowed exceptions, unclear messages, and user/API/file failures that crash instead of failing clearly. |
| Testability | Identify code that is hard to test because it is coupled to live services, environment variables, files, or UI frameworks. |
| Software Delivery Testing | Check the repository's Testing Portfolio: static checks, unit tests, integration tests, smoke tests, regression tests, characterization tests, and full verification. Distinguish tests that freeze existing behavior from tests that prove intended new behavior. |
| Reproducibility And Dependency Discipline | Check dependency files, Python version declarations, pinning or lock strategy, CI/local install alignment, and future breakage risk from floating requirements. |
| CI Maturity | Check whether baseline CI runs local verification without live secrets and whether stronger checks are proportional to repository maturity. |
| Data And JSON Validation | Check whether uploaded files, JSON, CSV, API responses, and model outputs are validated before moving through the system. |
| Artifact/File Collision Safety | Check whether generated and uploaded files can silently overwrite unrelated files and whether automatic names are collision-resistant when needed. |
| User-Controlled File/Path Safety | Check whether user-provided paths, uploads, artifact paths, and config paths are validated before sensitive use. |
| Repository Hygiene | Find generated files, caches, missing `.gitignore` rules, confusing duplicate files, or unclear dependency setup. |
| Process And Reviewer Evidence | Check whether setup, run commands, verification, run reports, commits, pull request bodies, known limitations, and reviewer evidence are accurate. |
| Security And Secrets | Look for hardcoded secrets, risky uploads, sensitive logs, external-resource risks, and prompt injection surfaces. |

### AI System Audits

These checks focus on prompts, model/API usage, RAG, agents, tools, and
multi-step AI automation.

| Area | Example intent |
| --- | --- |
| AI Software Architecture | Check whether provider adapters, prompt storage/wiring, model-call boundaries, deterministic logic, RAG/agent/workflow composition, and fake-client seams have clear ownership without duplicating focused AI checks. |
| Prompt Quality | Check whether prompt content has a clear task, audience, constraints, inputs, and expected output format. |
| Dynamic Prompting | Review how variables and user input are inserted into prompts, including injection risk and duplicated prompt construction. |
| Structured Output | Check whether model output should be validated JSON/schema instead of fragile free text. |
| LLM/API Integration | Review provider boundaries, credentials, model settings, retries, timeouts, token limits, and fake-client testability. |
| RAG And Retrieval | Check document loading, chunking, embeddings, retrieval quality, empty-result behavior, and fixture-based evaluation. |
| AI Evaluation And Testing | Check model-dependent behavior with deterministic fake-client tests, fixture-based evaluations, structured output validation, RAG grounding checks, agent/tool workflow checks, and optional live/model evals kept separate from normal verification. |
| Agents And Tools | Review whether an agent is justified, whether tools have clear names/inputs/outputs, and how failures are recovered. |
| Workflow Automation | Check multi-step AI/tool flows: triggers, idempotency, retries, failure branches, state transitions, approvals, concurrent runs, logs, run IDs, recovery, and reports. |
| Speech Pipelines | Review audio loading, transcription prompts, chunking, timestamps, generated audio validation, and safe output naming. |
| Cost And Usage | Check execution caps, retries, timeouts, token limits, high-cost opt-ins, visible limits, and proportional usage tracking. |

`AI System Audits` covers AI software architecture, prompts, model/API
integrations, RAG, agents, tools, speech, cost, and multi-step AI/tool
automation. `Workflow Automation` remains an audit area inside that family.

## Characterization And Verification

Characterization tests, also known as Golden Master or Snapshot tests, capture
the exact current behavior of existing software before refactoring. Michael
Feathers coined the term in *Working Effectively with Legacy Code*.

Their purpose is not to prove the behavior is correct. Their purpose is to
freeze observable legacy behavior so refactors can be made safely. If a change
breaks current output, side effects, errors, or other observable behavior, the
test fails before the change reaches production.

See `references/characterization.md` and `references/testing-strategy.md` for
the full policy.

Templates assume the target project declares the dependencies needed by its
normal verification command. If tests use `pytest`, prefer adding `pytest` to
the target repo's existing dev/test dependency location, such as
`pyproject.toml`, `requirements-dev.txt`, or a test extra. For very small
beginner repos without a dependency convention, adding
`python -m pip install pytest` to CI is acceptable as a temporary fallback.

## Templates And References

- `SKILL.md`: skill entry point and mode selection guidance.
- `references/protocol.md`: canonical workflow and required rules.
- `references/characterization.md`: characterization policy and examples.
- `references/testing-strategy.md`: verification and test roles.
- `references/patch-policy.md`: patch size, risk, and split criteria.
- `references/integration-into-other-repos.md`: adoption modes and boundaries.
- `references/agent-runtime-hooks.md`: optional Codex lifecycle hook enforcement
  layer for target repositories.
- `assets/AGENTS.template.md`: project-local agent rules.
- `assets/Makefile.template` and `assets/verify.sh.template`: minimal local
  verification.
- `assets/codex_hooks/`: portable hook handler, repo-local policy template,
  Codex config snippet, and ignored audit/state path template.
- `assets/development-skill-note.template.md`: note for repositories that need
  to document this system as a development/support skill.
- `assets/behavior-inventory-template.md`: worksheet for risky changes.
- `assets/patch-backlog-template.md`: actionable review backlog.
- `assets/run-report-template.md`: durable audit trail for reviews, full
  automation runs, medium/high-risk patches, failed verification, or persistent
  backlogs.

Use hook and CI templates only after explicit user approval.

## Maintaining This Repository

Repository verification should normally be:

```text
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
make verify
```

For this repository, `make verify` uses `.venv/bin/python` when present, falls
back to `python3` otherwise, compiles local scripts, runs Ruff, and checks that
the core docs still point back to the canonical protocol.

---

For quick technical review: this repository is best evaluated as reusable AI-assisted software engineering practice. It codifies my AI engineering approach into a skill that can help other projects apply safer review, verification, testing, and controlled improvement workflows.
