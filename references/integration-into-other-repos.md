# Integration Into Other Repositories

Use this note when deciding how to apply the safe project improvement system to
another repository.

## Modes

### External Reference Mode

Use the skill from its original repository when the agent can read both
repositories in the same workspace.

This mode can guide behavior, but it cannot reliably enforce target-repo
behavior because repo-local hook configuration, policy, and audit state are not
installed in the target repository.

### Repo-Local Guidance Mode

Copy only a small subset of templates such as `AGENTS.md`, `Makefile`, and
`verify.sh`.

This mode provides local guidance, not the full skill bundle.

### Vendored Skill Mode

Copy the full skill bundle into the target repository, typically under:

```text
skills/safe_project_improvement_system/
```

Use this when the target repository needs traceability or local availability for
future agent sessions.

Use this mode when portable Codex lifecycle hook enforcement should travel with
the target repository.

### Hybrid Mode

Keep the full skill external while also adding small repo-local instructions in
the target repository.

Use this mode when the target repository needs local enforcement policy and
hooks, but the full reference bundle can stay external.

## Optional Enforcement Layer

For enforcement, install or vendor the portable hook bundle, then adapt
`.codex/safe-project-policy.json` in the target repository. Read
`references/agent-runtime-hooks.md` before enabling it.

Preview the files first:

```text
python scripts/install_templates.py --target /path/to/target --preset codex-hooks
```

Apply only missing hook files after review:

```text
python scripts/install_templates.py --target /path/to/target --preset codex-hooks --apply
```

This preset installs:

- `assets/codex_hooks/safe_project_hook.py`: portable hook handler
- `assets/codex_hooks/run_safe_project_hook.sh`: environment-detecting hook
  runner
- `.codex/safe-project-policy.json`: repo-local policy
- `.codex/config.toml`: Codex hook config for a trusted target repo

Use the Python command for the current support-repo environment when running the
installer. The installed hook runner uses `SAFE_PROJECT_PYTHON` or `PYTHON` when
set, then an active virtualenv, common local environment directories, `uv`,
`poetry`, `pipenv`, `hatch`, and finally `python3` or `python`.

Do not install hooks automatically. Hook installation changes local agent
behavior and must be an explicit target-repository decision.

Full Automation Mode also requires durable process artifacts:

- `.codex/safe-project-workflow.json`: machine-readable workflow state with
  stable item IDs such as `P001`
- `docs/patch-backlog.md`: persisted audit and backlog items
- `docs/run-report.md`: run report naming the active item, verification, commit,
  push, and deferrals

The workflow state file is session state and should be ignored. The report and
backlog files are durable project artifacts when enforcement is enabled.

## Native Skill Boundary

Vendoring this folder into another repository does not automatically register it
as a native skill in every coding tool.

The practical requirement is simpler:

- the files must be present
- local instructions should point to `SKILL.md`
- prompts should explicitly say to use the skill

## Existing File Safety

Do not blindly overwrite these files in the target repository:

- `AGENTS.md`
- `Makefile`
- `verify.sh`
- `pyproject.toml`

Merge or adapt carefully.

The helper script `scripts/install_templates.py` can preview selected
adoption templates and apply only missing files. It leaves existing files in
place and prints merge diffs when it encounters a conflict.

## Recommended Target-Repo Wording

When this system is used only to help develop another project, describe it as:

```text
development/support skill
```

Do not describe it as a runtime/project skill unless the target repository
explicitly integrates it into application behavior.
