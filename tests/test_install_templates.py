"""Tests for the safe template adoption installer."""

from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from scripts import install_templates


class InstallTemplatesTests(unittest.TestCase):
    """Verify the installer previews, applies, and preserves conflicts safely."""

    def test_default_selection_uses_repo_local_templates(self) -> None:
        """The installer falls back to the repo-local guidance preset."""
        selected = install_templates.resolve_template_names(None, None, False)

        self.assertEqual(
            selected, list(install_templates.PRESETS["repo-local"])
        )

    def test_apply_writes_missing_files_only(self) -> None:
        """Missing templates are written, and the source text is preserved."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)

            template_names = ["agents", "makefile"]
            outcomes = install_templates.build_install_plan(target, template_names)
            written = install_templates.apply_install_plan(outcomes, apply=True)

            self.assertEqual(
                [outcome.status for outcome in outcomes],
                ["create", "create"],
            )
            self.assertEqual(
                sorted(path.relative_to(target).as_posix() for path in written),
                ["AGENTS.md", "Makefile"],
            )
            self.assertEqual(
                (target / "AGENTS.md").read_text(encoding="utf-8"),
                (install_templates.ASSETS / "AGENTS.template.md").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertEqual(
                (target / "Makefile").read_text(encoding="utf-8"),
                (install_templates.ASSETS / "Makefile.template").read_text(
                    encoding="utf-8"
                ),
            )

    def test_codex_hooks_preset_installs_enforcement_files(self) -> None:
        """The hook preset places policy, handler, and Codex config files."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            template_names = install_templates.resolve_template_names(
                None, ["codex-hooks"], False
            )

            outcomes = install_templates.build_install_plan(target, template_names)
            written = install_templates.apply_install_plan(outcomes, apply=True)

            self.assertEqual(
                template_names,
                ["hook-handler", "hook-runner", "hook-policy", "hook-config"],
            )
            self.assertEqual([outcome.status for outcome in outcomes], ["create"] * 4)
            self.assertEqual(
                sorted(path.relative_to(target).as_posix() for path in written),
                [
                    ".codex/config.toml",
                    ".codex/safe-project-policy.json",
                    "assets/codex_hooks/run_safe_project_hook.sh",
                    "assets/codex_hooks/safe_project_hook.py",
                ],
            )
            self.assertIn(
                "run_safe_project_hook.sh",
                (target / ".codex" / "config.toml").read_text(encoding="utf-8"),
            )

    def test_conflicting_file_is_preserved_and_reported(self) -> None:
        """Existing files are not overwritten when a merge is required."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            existing = target / "AGENTS.md"
            existing.write_text("local guidance\n", encoding="utf-8")

            outcomes = install_templates.build_install_plan(target, ["agents"])
            written = install_templates.apply_install_plan(outcomes, apply=True)
            report = install_templates.render_report(
                target, ["agents"], outcomes, True, written
            )

            self.assertEqual([outcome.status for outcome in outcomes], ["conflict"])
            self.assertEqual(written, [])
            self.assertEqual(existing.read_text(encoding="utf-8"), "local guidance\n")
            self.assertIn("Merge proposals:", report)
            self.assertIn("--- existing/AGENTS.md", report)
            self.assertIn("+++ template/AGENTS.md", report)

    def test_list_does_not_require_target(self) -> None:
        """Template discovery works without a target repository."""
        stdout = StringIO()

        with redirect_stdout(stdout):
            exit_code = install_templates.main(["--list"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Available templates:", stdout.getvalue())

    def test_missing_target_is_rejected(self) -> None:
        """The CLI does not plan adoption against a missing target root."""
        stderr = StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
            install_templates.main(["--target", "/tmp/missing-safe-project-target"])

        self.assertEqual(context.exception.code, 2)
        self.assertIn("Target does not exist", stderr.getvalue())

    def test_apply_rechecks_destination_before_writing(self) -> None:
        """A stale create plan cannot overwrite a file created later."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            outcomes = install_templates.build_install_plan(target, ["agents"])
            destination = target / "AGENTS.md"
            destination.write_text("created during review\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                install_templates.apply_install_plan(outcomes, apply=True)

            self.assertEqual(
                destination.read_text(encoding="utf-8"), "created during review\n"
            )

    def test_existing_directory_destination_is_a_conflict(self) -> None:
        """A directory at a template destination is reported as a merge conflict."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / "AGENTS.md").mkdir()

            outcomes = install_templates.build_install_plan(target, ["agents"])
            report = install_templates.render_report(
                target, ["agents"], outcomes, False, []
            )

            self.assertEqual([outcome.status for outcome in outcomes], ["conflict"])
            self.assertIn("not a regular file", report)


if __name__ == "__main__":
    unittest.main()
