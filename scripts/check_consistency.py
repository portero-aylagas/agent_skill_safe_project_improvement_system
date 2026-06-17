"""Check that the skill repository's docs stay internally consistent."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = "inspect -> characterize -> verify setup -> audit -> backlog -> one patch -> verify"

REQUIRED_PATHS = [
    ".github/workflows/verify.yml",
    ".gitignore",
    "Makefile",
    "README.md",
    "SKILL.md",
    "pyproject.toml",
    "requirements-dev.txt",
    "agents/openai.yaml",
    "scripts/check_consistency.py",
    "references/protocol.md",
    "references/audit-matrix.md",
    "references/branching-ci-hooks.md",
    "references/characterization.md",
    "references/coding-standards.md",
    "references/engineering-audits.md",
    "references/ai-workflow-audits.md",
    "references/integration-into-other-repos.md",
    "references/patch-policy.md",
    "references/testing-strategy.md",
    "references/ai-integration-quality.md",
    "references/agent-runtime-hooks.md",
    "assets/AGENTS.template.md",
    "assets/codex_hooks/__init__.py",
    "assets/codex_hooks/codex-config-snippet.template.toml",
    "assets/codex_hooks/gitignore.template",
    "assets/codex_hooks/safe-project-policy.template.json",
    "assets/codex_hooks/safe_project_hook.py",
    "assets/Makefile.template",
    "assets/behavior-inventory-template.md",
    "assets/development-skill-note.template.md",
    "assets/github-actions-verify.template.yaml",
    "assets/patch-backlog-template.md",
    "assets/pre-commit-config.template.yaml",
    "assets/pyproject.template.toml",
    "assets/verify.sh.template",
    "assets/run-report-template.md",
    "examples/review-mode.md",
    "examples/local-safe-refactor.md",
    "examples/install-verification.md",
    "tests/test_safe_project_hook.py",
]

WORKFLOW_DOCS = [
    "README.md",
    "SKILL.md",
    "references/protocol.md",
    "assets/AGENTS.template.md",
]

CANONICAL_POINTER_DOCS = [
    "README.md",
    "SKILL.md",
    "assets/AGENTS.template.md",
]

AGENTS_TEMPLATE_REQUIREMENTS = [
    "Default to beginner/intermediate-friendly code unless this repository already",
    "Use `references/patch-policy.md` for patch-size thresholds and split criteria.",
    "Public modules, classes, and functions should have concise Google-style",
]

PROTOCOL_REQUIREMENTS = [
    "Do not make code changes during inspection.",
    "Characterization is mandatory before medium/high-risk changes",
    "Normal verification must not require live API keys",
    "Do not push, install hooks, or add strict CI unless explicitly authorized",
    "Use fake clients/mocks for AI/API tests.",
    "When reviewing software engineering quality, assess conformance to",
    "`references/coding-standards.md`",
]

AUDIT_SCOPE_REQUIREMENTS = [
    "## Audit Scope Gate",
    "selected audit families and areas",
    "that skipped audit areas, if any, are listed only in the relevant skipped-area",
    "`Engineering Audits`",
    "`AI System Audits`",
    "Group findings by audit family, then audit area, then severity.",
    "Readable block-based audit reporting is the canonical audit/report format.",
    "Do not use wide Markdown tables for audit findings",
    "## Skipped Engineering Areas",
    "## Skipped AI System Areas",
    "Tables may only be used for short metadata summaries, not detailed findings.",
    "Pass through the Audit Scope Gate",
]

CODING_STANDARDS_REQUIREMENTS = [
    "Use these standards when reviewing, editing, refactoring, or installing",
    "Implementation work should be beginner/intermediate-friendly",
    "Use comments as a comprehension tool, not decoration.",
    "Include public module, class, and function docstrings in software engineering",
    "Prefer Ruff pydocstyle checks for gradual enforcement",
]

PATCH_POLICY_REQUIREMENTS = [
    "It touches more than 5 files.",
    "It changes more than 250 non-generated lines.",
    "It changes dependencies, lockfiles, packaging, or runtime versions.",
    "It changes a public API, CLI contract, schema, prompt contract, or persisted",
]

TESTING_STRATEGY_REQUIREMENTS = [
    "Characterization tests protect existing behavior before medium/high-risk",
    "Ruff linting, including configured pydocstyle checks for public docstrings",
    "Patch tests prove the intended new behavior introduced by the current patch.",
    "Full verification runs the repository's normal checks after the patch",
    "intentional behavior change that needs a deliberate test update",
]

RUN_ARTIFACT_REQUIREMENTS = [
    "Use `assets/run-report-template.md` when a run needs a durable audit trail.",
    "the mode is full automation",
    "verification fails",
    "For low-risk local patches, the final chat report is usually enough.",
]

DEEP_AUDIT_REQUIREMENTS = [
    "references/engineering-audits.md",
    "references/ai-workflow-audits.md",
    "references/coding-standards.md",
    "Review mode always loads `references/protocol.md`",
    "Deep audit references are optional. In review mode, load",
    "AI System Audits",
    "AI Software Architecture",
    "AI System references",
    "except where the protocol requires one for the",
    "safe refactor mode unless the patch directly",
    "Prompt technique: zero-shot, few-shot, or structured output chosen deliberately.",
    "UI/backend separation: callbacks validate inputs and call clean backend",
]

RUNTIME_HOOK_REQUIREMENTS = [
    "Codex lifecycle hooks enforce observable agent-session actions.",
    "Hooks are not a complete security boundary.",
    "unified execution paths may not always",
    "`assets/codex_hooks/`",
    "`codex_hooks` as a stable feature",
    "[[hooks.PreToolUse]]",
    "type = \"command\"",
    "Hybrid Mode or Vendored Skill Mode",
    "reliably enforce target-repo",
]


def read_text(relative_path: str) -> str:
    """Read a repository file as UTF-8 text.

    Args:
        relative_path: Path relative to the repository root.

    Returns:
        File contents decoded as UTF-8 text.
    """
    return (ROOT / relative_path).read_text(encoding="utf-8")


def check_required_paths() -> list[str]:
    """Check that required skill files exist.

    Returns:
        Human-readable consistency errors.
    """
    errors = []
    for relative_path in REQUIRED_PATHS:
        if not (ROOT / relative_path).is_file():
            errors.append(f"missing required file: {relative_path}")
    return errors


def check_trailing_whitespace() -> list[str]:
    """Check that required repository text files have no trailing whitespace.

    Returns:
        Human-readable consistency errors.
    """
    errors = []
    for relative_path in REQUIRED_PATHS:
        path = ROOT / relative_path
        if not path.is_file():
            continue
        for line_number, line in enumerate(read_text(relative_path).splitlines(), 1):
            if line.endswith((" ", "\t")):
                errors.append(f"{relative_path}:{line_number} has trailing whitespace")
    return errors


def check_workflow_phrase() -> list[str]:
    """Check that summary docs keep the canonical workflow phrase.

    Returns:
        Human-readable consistency errors.
    """
    errors = []
    for relative_path in WORKFLOW_DOCS:
        if WORKFLOW not in read_text(relative_path):
            errors.append(f"missing canonical workflow phrase: {relative_path}")
    return errors


def check_canonical_pointers() -> list[str]:
    """Check that summary docs point readers back to the protocol.

    Returns:
        Human-readable consistency errors.
    """
    errors = []
    for relative_path in CANONICAL_POINTER_DOCS:
        text = read_text(relative_path)
        if "references/protocol.md" not in text:
            errors.append(f"missing protocol pointer: {relative_path}")
    return errors


def check_protocol_requirements() -> list[str]:
    """Check that the protocol keeps core safety requirements.

    Returns:
        Human-readable consistency errors.
    """
    protocol = read_text("references/protocol.md")
    errors = []
    for requirement in PROTOCOL_REQUIREMENTS:
        if requirement not in protocol:
            errors.append(f"protocol missing requirement: {requirement}")
    return errors


def check_audit_scope_requirements() -> list[str]:
    """Check that mode-wide audit scope and reporting guidance stays present.

    Returns:
        Human-readable consistency errors.
    """
    docs = {
        "references/protocol.md": read_text("references/protocol.md"),
        "SKILL.md": read_text("SKILL.md"),
        "README.md": read_text("README.md"),
        "assets/AGENTS.template.md": read_text("assets/AGENTS.template.md"),
        "examples/review-mode.md": read_text("examples/review-mode.md"),
        "assets/patch-backlog-template.md": read_text(
            "assets/patch-backlog-template.md"
        ),
        "assets/run-report-template.md": read_text("assets/run-report-template.md"),
    }
    protocol = docs["references/protocol.md"]
    errors = []
    for requirement in AUDIT_SCOPE_REQUIREMENTS:
        if requirement not in protocol:
            errors.append(f"protocol missing audit scope requirement: {requirement}")
    for relative_path, text in docs.items():
        if "Engineering Audits" not in text:
            errors.append(f"{relative_path} missing Engineering Audits wording")
        if "AI System Audits" not in text:
            errors.append(f"{relative_path} missing AI System Audits wording")
    block_docs = {
        "references/protocol.md": protocol,
        "examples/review-mode.md": docs["examples/review-mode.md"],
        "assets/patch-backlog-template.md": docs["assets/patch-backlog-template.md"],
        "assets/run-report-template.md": docs["assets/run-report-template.md"],
    }
    required_block_fields = [
        "- Severity: High | Medium | Low | Info",
        "- Finding: <finding>",
        "- Evidence / Location: <files, functions, commands>",
        "- Recommended Action: <action>",
        "- Verification: <test, command, review method>",
        "No material findings.",
        "Evidence:",
        "Verification:",
        "## Skipped Engineering Areas",
        "## Skipped AI System Areas",
    ]
    disallowed_old_audit_markers = [
        "Checked" + ": Yes",
        "Severity" + ": None",
        "Recommended Action" + ": None",
        "Severity: High | Medium | Low | Info | " + "None",
        "Finding: <finding or " + '"No material findings">',
        'or "' + "N/A" + '"',
        "skipped audit families " + "and areas",
        "Audit families and areas " + "skipped:",
    ]
    disallowed_finding_table_marker = (
        "| Audit Area | " + "Checked" + "? | Severity | Finding |"
    )
    for relative_path, text in block_docs.items():
        for field in required_block_fields:
            if field not in text:
                errors.append(f"{relative_path} missing audit block field: {field}")
        for marker in disallowed_old_audit_markers:
            if marker in text:
                errors.append(
                    f"{relative_path} still uses old audit marker: {marker}"
                )
        if disallowed_finding_table_marker in text:
            errors.append(f"{relative_path} still uses a findings table")
    return errors


def check_coding_standards_requirements() -> list[str]:
    """Check that coding standards keep review and readability rules.

    Returns:
        Human-readable consistency errors.
    """
    coding_standards = read_text("references/coding-standards.md")
    errors = []
    for requirement in CODING_STANDARDS_REQUIREMENTS:
        if requirement not in coding_standards:
            errors.append(f"coding standards missing requirement: {requirement}")
    return errors


def check_patch_policy_requirements() -> list[str]:
    """Check that patch-policy thresholds remain documented.

    Returns:
        Human-readable consistency errors.
    """
    patch_policy = read_text("references/patch-policy.md")
    errors = []
    for requirement in PATCH_POLICY_REQUIREMENTS:
        if requirement not in patch_policy:
            errors.append(f"patch policy missing threshold: {requirement}")
    return errors


def check_agent_policy() -> list[str]:
    """Check that the OpenAI agent config keeps implicit invocation disabled.

    Returns:
        Human-readable consistency errors.
    """
    agent_config = read_text("agents/openai.yaml")
    if "allow_implicit_invocation: false" not in agent_config:
        return ["agents/openai.yaml must keep allow_implicit_invocation: false"]
    return []


def check_testing_strategy_requirements() -> list[str]:
    """Check that the testing strategy keeps its core test categories.

    Returns:
        Human-readable consistency errors.
    """
    testing_strategy = read_text("references/testing-strategy.md")
    errors = []
    for requirement in TESTING_STRATEGY_REQUIREMENTS:
        if requirement not in testing_strategy:
            errors.append(f"testing strategy missing requirement: {requirement}")
    return errors


def check_run_artifact_requirements() -> list[str]:
    """Check that run artifact guidance and template sections stay present.

    Returns:
        Human-readable consistency errors.
    """
    protocol = read_text("references/protocol.md")
    report_template = read_text("assets/run-report-template.md")
    errors = []
    for requirement in RUN_ARTIFACT_REQUIREMENTS:
        if requirement not in protocol:
            errors.append(f"protocol missing run artifact requirement: {requirement}")
    if "## Metadata" not in report_template or "## Verification" not in report_template:
        errors.append("run report template missing required sections")
    return errors


def check_deep_audit_requirements() -> list[str]:
    """Check that deep audit loading rules and core sections stay present.

    Returns:
        Human-readable consistency errors.
    """
    skill = read_text("SKILL.md")
    audit_matrix = read_text("references/audit-matrix.md")
    engineering = read_text("references/engineering-audits.md")
    ai_workflow = read_text("references/ai-workflow-audits.md")
    errors = []
    for requirement in DEEP_AUDIT_REQUIREMENTS:
        if requirement not in skill and requirement not in audit_matrix:
            errors.append(f"missing deep audit requirement: {requirement}")
    if (
        "## General Software Architecture" not in engineering
        or "## Error Handling" not in engineering
        or "## Testability" not in engineering
    ):
        errors.append("engineering audits missing core sections")
    if (
        "## AI Software Architecture" not in ai_workflow
        or "## Prompt Quality" not in ai_workflow
        or "## RAG And Retrieval" not in ai_workflow
    ):
        errors.append("AI System audits missing core sections")
    if "# AI System Audits" not in ai_workflow:
        errors.append("AI workflow audit reference missing AI System Audits title")
    return errors


def check_agents_template_requirements() -> list[str]:
    """Check that installed agent rules keep key local guidance.

    Returns:
        Human-readable consistency errors.
    """
    agents_template = read_text("assets/AGENTS.template.md")
    errors = []
    for requirement in AGENTS_TEMPLATE_REQUIREMENTS:
        if requirement not in agents_template:
            errors.append(f"AGENTS template missing requirement: {requirement}")
    return errors


def check_runtime_hook_requirements() -> list[str]:
    """Check that portable runtime hook guidance and templates stay present.

    Returns:
        Human-readable consistency errors.
    """
    reference = read_text("references/agent-runtime-hooks.md")
    config_template = read_text("assets/codex_hooks/codex-config-snippet.template.toml")
    policy_template = read_text("assets/codex_hooks/safe-project-policy.template.json")
    errors = []
    for requirement in RUNTIME_HOOK_REQUIREMENTS:
        if requirement not in reference and requirement not in config_template:
            errors.append(f"runtime hook guidance missing requirement: {requirement}")
    try:
        import json

        policy = json.loads(policy_template)
    except ValueError as error:
        errors.append(f"runtime hook policy template invalid JSON: {error}")
    else:
        for key in (
            "mode",
            "verification_command",
            "protected_paths",
            "allowed_approval_gates",
            "audit_log",
            "state_file",
        ):
            if key not in policy:
                errors.append(f"runtime hook policy template missing key: {key}")
    return errors


def main() -> int:
    """Run all repository consistency checks.

    Returns:
        Process exit code: 0 when checks pass, 1 when any check fails.
    """
    errors = []
    errors.extend(check_required_paths())
    errors.extend(check_trailing_whitespace())
    errors.extend(check_workflow_phrase())
    errors.extend(check_canonical_pointers())
    errors.extend(check_protocol_requirements())
    errors.extend(check_audit_scope_requirements())
    errors.extend(check_coding_standards_requirements())
    errors.extend(check_patch_policy_requirements())
    errors.extend(check_testing_strategy_requirements())
    errors.extend(check_run_artifact_requirements())
    errors.extend(check_deep_audit_requirements())
    errors.extend(check_agent_policy())
    errors.extend(check_agents_template_requirements())
    errors.extend(check_runtime_hook_requirements())

    if errors:
        print("Consistency check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
