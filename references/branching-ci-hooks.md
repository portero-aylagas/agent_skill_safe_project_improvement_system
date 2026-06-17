# Branching, CI, and Hooks

Use this reference only when the user explicitly asks for branch, hook, CI,
commit, push, or full automation work.

## Approval Boundary

Do not do these without explicit authorization:

- create or switch branches for automation
- install pre-commit hooks
- add strict CI gates
- commit
- push
- open pull requests

## Branching

Before creating a branch:

- inspect current status
- identify unrelated changes
- avoid overwriting user work
- choose a short descriptive branch name

Keep each branch focused on one improvement.

## Hooks

Start with low-risk hooks only:

- trailing whitespace
- end-of-file fixer
- JSON validity
- YAML validity

Make formatters and strict linters opt-in unless the project already uses them.
Installing hooks changes local developer behavior, so ask first.

Git/pre-commit hooks are separate from Codex lifecycle hooks. Git hooks catch
low-level local file hygiene, while Codex hooks can block observable agent tool
actions before or during a session. Use `references/agent-runtime-hooks.md` for
the portable Codex hook enforcement layer.

## CI

Default CI should run:

```text
make verify
```

CI must not require live secrets for normal checks. Use fake clients and local
fixtures. Live integration checks should be separate, clearly named, and gated by
explicit secrets.

Keep CI proportional to repository maturity. For non-trivial apps, consider
type checking, coverage, dependency audit, or AI/evaluation smoke tests when
they provide real review value. Do not force heavy production CI on small
projects.

## Commit And Pull Request Structure

- One pull request may contain multiple commits.
- One commit should map to one coherent remediation area.
- Independent findings should normally be separate commits.
- Documentation or run-report commits should be separate when generated.
- If several findings are combined, explain why they are inseparable.
- Pull request bodies must include a real summary of the actual remediation and
  verification.
- Reject fake issue references, placeholder metadata, and inaccurate review
  evidence.

## Full Automation Checklist

1. Confirm explicit approval.
2. Create branch.
3. Add or confirm verification.
4. Add characterization before risky changes.
5. Make one patch.
6. Run local verification.
7. Run the pre-publish gate.
8. Commit only relevant files.
9. Push.
10. Wait for CI.
11. Report result and next backlog item.

## Pre-Publish Gate

Before commit, push, or pull request creation/update, confirm:

- all selected findings are mapped to code, tests, docs, or explicit deferral
- Requirements Ledger must-have items are satisfied or explicitly deferred
- run report exists when required
- commit strategy is explicit
- patch size/scope thresholds are respected or justified
- pull request body has real summary and verification
- pull request body contains no fake issue references or placeholder metadata
- CI result is checked after push
- final handoff happens only after process artifacts are complete
