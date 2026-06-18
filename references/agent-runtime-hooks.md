# Agent Runtime Hooks

Use this reference when adding portable enforcement for safe project improvement
inside a target repository.

## Enforcement Role

Codex lifecycle hooks enforce observable agent-session actions. They can block a
tool call before it runs, record evidence after a tool call completes, and check
whether the session can stop cleanly.

Hooks are not a complete security boundary. They cannot prove that an agent
understood a repository, and shell or unified execution paths may not always
expose every mutation with perfect fidelity. Treat hooks as one layer in a
defense-in-depth workflow:

- agent instructions describe the desired workflow
- Codex hooks block obvious workflow violations during the session
- Git hooks catch low-level local hygiene issues
- CI verifies final repository state in a clean environment
- tests and fake clients prove AI-adjacent behavior without live API keys

## Portable Bundle

The portable template bundle lives under `assets/codex_hooks/`:

- `safe_project_hook.py`: dependency-free Python handler
- `run_safe_project_hook.sh`: environment-detecting shell runner for the handler
- `safe-project-policy.template.json`: repo-local policy template
- `codex-config-snippet.template.toml`: Codex hook config snippet
- `gitignore.template`: ignored audit and state paths

Copy the handler and policy into a target repository only when that repository
opts into enforcement. Do not install or enable hooks automatically.

## Policy Location

The default policy path is:

```text
.codex/safe-project-policy.json
```

All repo-specific behavior belongs in that policy file:

- `mode`: default `local_safe_refactor`
- `verification_command`: default `make verify`
- `protected_paths`: path globs that need explicit approval
- `allowed_approval_gates`: opt-in approvals for commits, pushes, branch
  changes, hook installation, CI changes, live-service commands, and protected
  path edits
- `required_inspection_anchors`: evidence strings that must be observed before
  writes
- `live_service_env_vars` and `forbidden_live_service_commands`: commands and
  credentials that normal verification must avoid
- `audit_log` and `state_file`: JSONL audit and session state paths
- `workflow_state_file`: machine-readable Full Automation workflow state path,
  defaulting to `.codex/safe-project-workflow.json`
- `run_report` and `patch_backlog`: durable report artifact paths
- `require_durable_reports`: require report/backlog artifacts for hook-enforced
  non-Full-Automation modes

The audit and state files should be ignored by default:

```text
.codex/safe-project-audit.jsonl
.codex/safe-project-session-state.json
.codex/safe-project-workflow.json
```

The handler resolves these paths inside the target repository at runtime. When
the bundle is copied or vendored into another repo, approvals, audit entries,
inspection counters, write counters, and git snapshots are written to that
target repo's `.codex/` files, not to this support repository.

## Codex Config Shape

The hook snippet syntax was checked against the installed Codex CLI and public
OpenAI Codex source on 2026-06-17. The installed CLI reports
`codex_hooks` as a stable feature. The public config schema defines event groups
such as `[[hooks.SessionStart]]`, `[[hooks.PreToolUse]]`,
`[[hooks.PostToolUse]]`, `[[hooks.UserPromptSubmit]]`, and `[[hooks.Stop]]`,
each with command handlers:

```toml
[[hooks.PreToolUse]]
matcher = "*"
hooks = [
  { type = "command", command = "sh assets/codex_hooks/run_safe_project_hook.sh --event PreToolUse", timeout = 10 }
]
```

Project-local config, hooks, and exec policies apply only for trusted projects.
If a target repository is untrusted, enable trust deliberately before relying on
project-local hook config.

The runner uses `SAFE_PROJECT_PYTHON` or `PYTHON` when set, then an active
virtualenv, common local environment directories, `uv`, `poetry`, `pipenv`,
`hatch`, and finally `python3` or `python`. The hook handler itself is
dependency-free; the target repo's normal verification dependencies should be
installed through the repo's own dependency files.

## Event Responsibilities

- `SessionStart`: create session state, read policy, record git branch, commit,
  and status. If the handler is enabled but policy is missing or invalid, fail
  closed.
- `PreToolUse`: block disallowed actions before execution, including Review Mode
  writes, Full Automation workflow transitions, commits, pushes, branch changes,
  hook installation, CI changes, protected-path edits, destructive shell
  commands, and live-service commands without explicit policy approval.
- `UserPromptSubmit`: record session-scoped approval gates from explicit user
  prompts. Valid prompts use this exact shape:

```text
SAFE-PROJECT APPROVE <gate> [until=session] REASON: <reason>
```

Supported gates match `allowed_approval_gates`: `commits`, `pushes`,
`branch_changes`, `hook_installation`, `ci_changes`,
`live_service_commands`, and `protected_path_edits`. A valid prompt stores the
gate, reason, timestamp, event index, and session scope in the current session
state, then appends a sanitized audit entry. Malformed prompts do not grant
approval. Session approvals do not edit static policy and expire with the Codex
session.
- `PostToolUse`: append sanitized audit events and update observed inspection,
  write, verification, branch, commit, push, and failure evidence.
- `Stop`: record final git status and block/report incomplete sessions where
  writes or changed files exist without successful verification after the first
  write, or where Full Automation items remain unfinished without explicit
  deferral.

## Full Automation Workflow State

When `mode` is `full_automation`, the hook requires durable workflow state at
`workflow_state_file` before writes, commits, pushes, or stop. The state file is
JSON and must contain audited/backlog items with stable IDs such as `P001`,
statuses, and at most one active item:

```json
{
  "branch": "safe-project/full-automation",
  "active_item": "P001",
  "items": [
    {
      "id": "P001",
      "status": "active",
      "verification": {
        "command": "make verify",
        "result": "passed"
      }
    }
  ]
}
```

The hook records successful verification on the active item, records commit SHA
evidence after `git commit`, and marks mapped items pushed after `git push`.
Commits are blocked unless exactly one item is active, verification passed after
the latest write, workflow state records that verification, and the run report
names the same item. Pushes are blocked unless each commit created in the
session maps to a workflow item with passed verification evidence.

Full Automation and policies with `require_durable_reports` validate report
structure by required headings and item IDs. They do not judge prose quality.
The required artifacts are `docs/run-report.md` and `docs/patch-backlog.md` by
default.

## Approval Precedence

For each approval gate, enforcement checks the target repo's static policy first
and then the current session state. A static `true` value in
`allowed_approval_gates` allows that gate for every session using that policy. A
`SAFE-PROJECT APPROVE ... [until=session]` prompt allows only the named gate for
the current Codex session. Approval for `commits` does not allow `pushes`,
branch changes, hook installation, CI edits, live-service commands, or protected
path edits.

## Shell Command Classification

`PreToolUse` classifies shell commands conservatively before execution. The
classifier splits commands into segments across `;`, `&&`, `||`, and `|` while
respecting shell quotes, then inspects each segment's executable and arguments.
It recognizes git commits, pushes, branch/history operations, common file
mutation commands, hook installation, CI paths, protected paths, and live-service
commands.

The classifier intentionally fails closed for shell forms that are hard to
reason about in a dependency-free portable hook. Redirection, command
substitution, heredoc and here-string syntax, unmatched quotes, inline Python
file writes, and unknown complex write-like commands are treated as risky and
blocked unless an applicable approval gate is active. This is a workflow
guardrail, not a shell sandbox; `Stop` still runs `git status --short` as the
final backstop for mutations the hook did not observe directly.

## Adoption Recommendation

Use Hybrid Mode or Vendored Skill Mode when enforcement matters. External
Reference Mode can guide an agent, but it cannot reliably enforce target-repo
behavior because the hook handler, policy file, and Codex config are outside the
target repo's local enforcement surface.

Keep Git/pre-commit hooks low-risk and optional. Default CI should run the same
normal verification command, usually `make verify`, without live secrets.
