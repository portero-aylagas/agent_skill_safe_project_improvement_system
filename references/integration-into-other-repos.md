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

For enforcement, copy or vendor the portable bundle from
`assets/codex_hooks/`, then adapt `.codex/safe-project-policy.json` in the
target repository. Read `references/agent-runtime-hooks.md` before enabling it.

Do not install hooks automatically. Hook installation changes local agent
behavior and must be an explicit target-repository decision.

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
