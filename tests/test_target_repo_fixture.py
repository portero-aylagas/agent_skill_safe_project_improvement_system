"""End-to-end tests for the example target repository fixture."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "target_repo"
WORKFLOW = (
    "inspect -> characterize -> verify setup -> audit -> backlog -> one patch -> verify"
)


class TargetRepoFixtureTests(unittest.TestCase):
    """Verify the fixture demonstrates the complete safe-improvement loop."""

    def test_fixture_contains_local_adoption_artifacts(self) -> None:
        """The fixture includes guidance, verification, backlog, and report files."""
        expected_paths = [
            "README.md",
            "AGENTS.md",
            "Makefile",
            "verify.sh",
            "pyproject.toml",
            "docs/patch-backlog.md",
            "docs/run-report.md",
            "src/example_target/calculator.py",
            "tests/test_calculator.py",
        ]

        for relative_path in expected_paths:
            with self.subTest(relative_path=relative_path):
                self.assertTrue((FIXTURE / relative_path).is_file())

    def test_fixture_documents_safe_improvement_workflow(self) -> None:
        """Local artifacts make the workflow and skill boundary visible."""
        readme = (FIXTURE / "README.md").read_text(encoding="utf-8")
        agents = (FIXTURE / "AGENTS.md").read_text(encoding="utf-8")
        backlog = (FIXTURE / "docs" / "patch-backlog.md").read_text(
            encoding="utf-8"
        )
        report = (FIXTURE / "docs" / "run-report.md").read_text(encoding="utf-8")

        self.assertIn(WORKFLOW, readme)
        self.assertIn(WORKFLOW, agents)
        self.assertIn("development/support skill", readme)
        self.assertIn("one focused patch", agents)
        self.assertIn("## Backlog Items", backlog)
        self.assertIn("## Patch Applied", report)
        self.assertIn("## Verification", report)

    def test_fixture_make_verify_passes_in_isolated_copy(self) -> None:
        """The target repo's normal verification command succeeds end to end."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target_repo"
            shutil.copytree(FIXTURE, target)
            environment = os.environ.copy()
            python_path = Path(sys.executable)
            if not python_path.is_absolute():
                python_path = ROOT / python_path
            python = str(python_path.absolute())

            result = subprocess.run(
                ["make", f"PYTHON={python}", "verify"],
                cwd=target,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
