#!/usr/bin/env python3
"""Preview and apply safe template adoption into a target repository.

This installer copies selected repo-local guidance templates into another
repository without overwriting existing files. If a destination already exists
and differs from the template, the script prints a unified diff so the caller
can merge the files manually.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class TemplateSpec:
    """Describe one installable template and its destination path."""

    name: str
    source: Path
    destination: Path
    description: str


@dataclass(frozen=True)
class InstallOutcome:
    """Record the result of evaluating a single template installation."""

    template: TemplateSpec
    status: str
    destination: Path
    diff: str = ""
    message: str = ""


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

TEMPLATE_CATALOG: dict[str, TemplateSpec] = {
    "agents": TemplateSpec(
        name="agents",
        source=ASSETS / "AGENTS.template.md",
        destination=Path("AGENTS.md"),
        description="Repo-local agent rules.",
    ),
    "makefile": TemplateSpec(
        name="makefile",
        source=ASSETS / "Makefile.template",
        destination=Path("Makefile"),
        description="Minimal verification entry point.",
    ),
    "verify-sh": TemplateSpec(
        name="verify-sh",
        source=ASSETS / "verify.sh.template",
        destination=Path("verify.sh"),
        description="Shell wrapper for local verification.",
    ),
    "pyproject": TemplateSpec(
        name="pyproject",
        source=ASSETS / "pyproject.template.toml",
        destination=Path("pyproject.toml"),
        description="Beginner-friendly pytest and Ruff defaults.",
    ),
    "skill-note": TemplateSpec(
        name="skill-note",
        source=ASSETS / "development-skill-note.template.md",
        destination=Path("docs/development-skill-note.md"),
        description="Development/support skill note.",
    ),
    "backlog": TemplateSpec(
        name="backlog",
        source=ASSETS / "patch-backlog-template.md",
        destination=Path("docs/patch-backlog.md"),
        description="Review and backlog template.",
    ),
    "run-report": TemplateSpec(
        name="run-report",
        source=ASSETS / "run-report-template.md",
        destination=Path("docs/run-report.md"),
        description="Durable run report template.",
    ),
    "behavior-inventory": TemplateSpec(
        name="behavior-inventory",
        source=ASSETS / "behavior-inventory-template.md",
        destination=Path("docs/behavior-inventory.md"),
        description="Behavior inventory worksheet.",
    ),
    "hook-handler": TemplateSpec(
        name="hook-handler",
        source=ASSETS / "codex_hooks" / "safe_project_hook.py",
        destination=Path("assets/codex_hooks/safe_project_hook.py"),
        description="Portable Codex lifecycle hook handler.",
    ),
    "hook-runner": TemplateSpec(
        name="hook-runner",
        source=ASSETS / "codex_hooks" / "run_safe_project_hook.sh",
        destination=Path("assets/codex_hooks/run_safe_project_hook.sh"),
        description="Environment-detecting shell runner for the Codex hook.",
    ),
    "hook-policy": TemplateSpec(
        name="hook-policy",
        source=ASSETS / "codex_hooks" / "safe-project-policy.template.json",
        destination=Path(".codex/safe-project-policy.json"),
        description="Repo-local safe-project hook policy.",
    ),
    "hook-config": TemplateSpec(
        name="hook-config",
        source=ASSETS / "codex_hooks" / "codex-config-snippet.template.toml",
        destination=Path(".codex/config.toml"),
        description="Codex hook config snippet for trusted target repos.",
    ),
}

PRESETS: dict[str, tuple[str, ...]] = {
    "repo-local": ("agents", "makefile", "verify-sh", "pyproject"),
    "docs": ("skill-note", "backlog", "run-report", "behavior-inventory"),
    "codex-hooks": ("hook-handler", "hook-runner", "hook-policy", "hook-config"),
    "all-safe": tuple(TEMPLATE_CATALOG.keys()),
}


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the template installer."""
    parser = argparse.ArgumentParser(
        description=(
            "Preview or apply safe project improvement templates to a target repo."
        )
    )
    parser.add_argument(
        "--target",
        type=Path,
        help="Path to the target repository root.",
    )
    parser.add_argument(
        "--template",
        action="append",
        dest="templates",
        choices=sorted(TEMPLATE_CATALOG),
        help="Install one template by name. May be repeated.",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS),
        action="append",
        help="Install one safe preset. May be repeated.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Install the full safe template set.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write missing files to the target repository.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available templates and exit.",
    )
    return parser


def list_templates() -> str:
    """Return a human-readable inventory of installable templates."""
    lines = ["Available templates:"]
    for name in sorted(TEMPLATE_CATALOG):
        spec = TEMPLATE_CATALOG[name]
        lines.append(f"- {name}: {spec.destination} ({spec.description})")
    lines.append("")
    lines.append("Presets:")
    for name in sorted(PRESETS):
        lines.append(f"- {name}: {', '.join(PRESETS[name])}")
    return "\n".join(lines)


def validate_target_root(target_root: Path) -> None:
    """Validate that the target root is an existing directory."""
    if not target_root.exists():
        raise ValueError(f"Target does not exist: {target_root}")
    if not target_root.is_dir():
        raise ValueError(f"Target is not a directory: {target_root}")


def resolve_template_names(
    template_names: Sequence[str] | None,
    preset_names: Sequence[str] | None,
    include_all: bool,
) -> list[str]:
    """Resolve the requested templates into a de-duplicated ordered list."""
    selected: list[str] = []

    if include_all:
        selected.extend(PRESETS["all-safe"])
    else:
        if preset_names:
            for preset_name in preset_names:
                selected.extend(PRESETS[preset_name])
        if template_names:
            selected.extend(template_names)

    if not selected:
        selected.extend(PRESETS["repo-local"])

    resolved: list[str] = []
    seen: set[str] = set()
    for name in selected:
        if name not in seen:
            resolved.append(name)
            seen.add(name)
    return resolved


def load_template_text(spec: TemplateSpec) -> str:
    """Load a template file from the repository assets directory."""
    return spec.source.read_text(encoding="utf-8")


def build_install_plan(target_root: Path, template_names: Sequence[str]) -> list[InstallOutcome]:
    """Compare selected templates against a target repository."""
    outcomes: list[InstallOutcome] = []
    for template_name in template_names:
        spec = TEMPLATE_CATALOG[template_name]
        destination = target_root / spec.destination
        source_text = load_template_text(spec)
        if not destination.exists():
            outcomes.append(
                InstallOutcome(template=spec, status="create", destination=destination)
            )
            continue

        if not destination.is_file():
            outcomes.append(
                InstallOutcome(
                    template=spec,
                    status="conflict",
                    destination=destination,
                    message="Destination exists but is not a regular file.",
                )
            )
            continue

        try:
            existing_text = destination.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            outcomes.append(
                InstallOutcome(
                    template=spec,
                    status="conflict",
                    destination=destination,
                    message="Destination exists but is not UTF-8 text.",
                )
            )
            continue

        if existing_text == source_text:
            outcomes.append(
                InstallOutcome(template=spec, status="identical", destination=destination)
            )
            continue

        diff = "".join(
            difflib.unified_diff(
                existing_text.splitlines(keepends=True),
                source_text.splitlines(keepends=True),
                fromfile=f"existing/{spec.destination}",
                tofile=f"template/{spec.destination}",
            )
        )
        outcomes.append(
            InstallOutcome(
                template=spec,
                status="conflict",
                destination=destination,
                diff=diff,
            )
        )
    return outcomes


def apply_install_plan(outcomes: Sequence[InstallOutcome], apply: bool) -> list[Path]:
    """Write missing template files when apply mode is enabled."""
    written: list[Path] = []
    if not apply:
        return written

    for outcome in outcomes:
        if outcome.status != "create":
            continue
        if outcome.destination.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing file: {outcome.destination}"
            )
        if outcome.destination.parent.exists() and not outcome.destination.parent.is_dir():
            raise NotADirectoryError(
                f"Destination parent is not a directory: {outcome.destination.parent}"
            )
        outcome.destination.parent.mkdir(parents=True, exist_ok=True)
        outcome.destination.write_text(
            load_template_text(outcome.template), encoding="utf-8"
        )
        written.append(outcome.destination)
    return written


def render_report(
    target_root: Path,
    template_names: Sequence[str],
    outcomes: Sequence[InstallOutcome],
    apply: bool,
    written: Sequence[Path],
) -> str:
    """Render the installer summary for humans."""
    lines = [
        "Safe Project Template Installer",
        f"Target: {target_root}",
        f"Mode: {'apply' if apply else 'preview'}",
        "",
        "Selected templates:",
    ]
    for template_name, outcome in zip(template_names, outcomes, strict=True):
        lines.append(
            f"- {template_name}: {outcome.destination} [{outcome.status}]"
        )
    if written:
        lines.append("")
        lines.append("Written files:")
        for path in written:
            lines.append(f"- {path}")

    conflicts = [outcome for outcome in outcomes if outcome.status == "conflict"]
    if conflicts:
        lines.append("")
        lines.append("Merge proposals:")
        for outcome in conflicts:
            lines.append(f"- {outcome.destination}")
            if outcome.message:
                lines.append(outcome.message)
            elif outcome.diff:
                lines.extend(outcome.diff.rstrip("\n").splitlines())
    if not apply:
        lines.append("")
        lines.append(
            "Preview only: rerun with --apply to write missing files after review."
        )
    return "\n".join(lines)


def validate_selection(template_names: Iterable[str]) -> None:
    """Ensure every selected template exists in the catalog."""
    for template_name in template_names:
        if template_name not in TEMPLATE_CATALOG:
            raise KeyError(f"Unknown template: {template_name}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the installer CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list:
        print(list_templates())
        return 0

    if args.target is None:
        parser.error("--target is required unless --list is used")

    target_root = args.target.resolve()
    try:
        validate_target_root(target_root)
    except ValueError as error:
        parser.error(str(error))

    template_names = resolve_template_names(args.templates, args.preset, args.all)
    validate_selection(template_names)

    outcomes = build_install_plan(target_root, template_names)
    try:
        written = apply_install_plan(outcomes, args.apply)
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(render_report(target_root, template_names, outcomes, args.apply, written))

    if any(outcome.status == "conflict" for outcome in outcomes):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
