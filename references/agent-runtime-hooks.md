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

The audit and state files should be ignored by default:

```text
.codex/safe-project-audit.jsonl
.codex/safe-project-session-state.json
```

## Codex Config Shape

The hook snippet syntax was checked against the installed Codex CLI and public
OpenAI Codex source on 2026-06-17. The installed CLI reports
`codex_hooks` as a stable feature. The public config schema defines event groups
such as `[[hooks.SessionStart]]`, `[[hooks.PreToolUse]]`,
`[[hooks.PostToolUse]]`, and `[[hooks.Stop]]`, each with command handlers:

```toml
[[hooks.PreToolUse]]
matcher = "*"
hooks = [
  { type = "command", command = "python assets/codex_hooks/safe_project_hook.py --event PreToolUse", timeout = 10 }
]
```

Project-local config, hooks, and exec policies apply only for trusted projects.
If a target repository is untrusted, enable trust deliberately before relying on
project-local hook config.

## Event Responsibilities

- `SessionStart`: create session state, read policy, record git branch, commit,
  and status. If the handler is enabled but policy is missing or invalid, fail
  closed.
- `PreToolUse`: block disallowed actions before execution, including Review Mode
  writes, commits, pushes, branch changes, hook installation, CI changes,
  protected-path edits, destructive shell commands, and live-service commands
  without explicit policy approval.
- `PostToolUse`: append sanitized audit events and update observed inspection,
  write, verification, and failure evidence.
- `Stop`: record final git status and block/report incomplete sessions where
  writes or changed files exist without successful verification after the first
  write.

## Adoption Recommendation

Use Hybrid Mode or Vendored Skill Mode when enforcement matters. External
Reference Mode can guide an agent, but it cannot reliably enforce target-repo
behavior because the hook handler, policy file, and Codex config are outside the
target repo's local enforcement surface.

Keep Git/pre-commit hooks low-risk and optional. Default CI should run the same
normal verification command, usually `make verify`, without live secrets.
