"""Tests for the portable safe project Codex hook handler."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / "assets" / "codex_hooks" / "safe_project_hook.py"
POLICY_TEMPLATE = (
    ROOT / "assets" / "codex_hooks" / "safe-project-policy.template.json"
)

spec = importlib.util.spec_from_file_location("safe_project_hook", HOOK_PATH)
assert spec is not None
hook = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["safe_project_hook"] = hook
spec.loader.exec_module(hook)


class SafeProjectHookTests(unittest.TestCase):
    """Unit tests for hook policy decisions and state updates."""

    def base_policy(self) -> dict:
        """Return a conservative test policy."""
        return hook.apply_policy_defaults(
            {
                "enabled": True,
                "mode": "local_safe_refactor",
                "verification_command": "make verify",
                "minimum_inspection_evidence": 1,
                "required_inspection_anchors": ["README"],
                "protected_paths": [".env*", "pyproject.toml"],
                "allowed_approval_gates": {},
                "audit_log": ".codex/safe-project-audit.jsonl",
                "state_file": ".codex/safe-project-session-state.json",
            }
        )

    def base_session(self) -> dict:
        """Return session state with enough inspection evidence to write."""
        return {
            "inspection_events": 1,
            "inspection_anchors": ["README"],
            "write_count": 0,
            "event_index": 1,
            "verification_after_write": False,
        }

    def full_automation_policy(self) -> dict:
        """Return a Full Automation policy with approvals enabled for tests."""
        policy = self.base_policy()
        policy["mode"] = "full_automation"
        policy["allowed_approval_gates"]["commits"] = True
        policy["allowed_approval_gates"]["pushes"] = True
        policy["allowed_approval_gates"]["branch_changes"] = True
        return policy

    def write_policy(self, cwd: Path, policy: dict) -> None:
        """Write a test policy to the temporary repository."""
        codex_dir = cwd / ".codex"
        codex_dir.mkdir(exist_ok=True)
        (codex_dir / "safe-project-policy.json").write_text(
            json.dumps(policy), encoding="utf-8"
        )

    def write_workflow(
        self,
        cwd: Path,
        items: list[dict],
        active_item: str | None = None,
    ) -> None:
        """Write durable workflow state."""
        codex_dir = cwd / ".codex"
        codex_dir.mkdir(exist_ok=True)
        workflow = {"branch": "automation/test", "items": items}
        if active_item is not None:
            workflow["active_item"] = active_item
        (codex_dir / "safe-project-workflow.json").write_text(
            json.dumps(workflow), encoding="utf-8"
        )

    def write_reports(self, cwd: Path, item_id: str = "P001") -> None:
        """Write minimal durable reports with required headings and item IDs."""
        docs = cwd / "docs"
        docs.mkdir(exist_ok=True)
        (docs / "run-report.md").write_text(
            "\n".join(
                [
                    "# Safe Improvement Run Report",
                    "## Metadata",
                    "## Scope",
                    "## Requirements Ledger",
                    "## Backlog",
                    f"### {item_id}",
                    "## Patch Applied",
                    "## Pre-Publish Gate",
                    "## Verification",
                    "## Follow-Up",
                ]
            ),
            encoding="utf-8",
        )
        (docs / "patch-backlog.md").write_text(
            "\n".join(
                [
                    "# Patch Backlog",
                    "## Requirements Ledger Snapshot",
                    "## Skipped Engineering Areas",
                    "## Skipped AI System Areas",
                    "## Backlog Items",
                    f"### {item_id}",
                ]
            ),
            encoding="utf-8",
        )

    def pre_tool_event(self, tool_name: str, tool_input: object) -> dict:
        """Build a `PreToolUse` event."""
        return {
            "hook_event_name": "PreToolUse",
            "session_id": "test",
            "tool_name": tool_name,
            "tool_input": tool_input,
        }

    def post_tool_event(
        self, tool_name: str, tool_input: object, response: dict | None = None
    ) -> dict:
        """Build a `PostToolUse` event."""
        return {
            "hook_event_name": "PostToolUse",
            "session_id": "test",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_response": response or {"exit_code": 0},
        }

    def user_prompt_event(self, prompt: str, cwd: Path | None = None) -> dict:
        """Build a `UserPromptSubmit` event."""
        event = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "test",
            "prompt": prompt,
        }
        if cwd is not None:
            event["cwd"] = str(cwd)
        return event

    def test_review_mode_blocks_file_writes(self) -> None:
        """Review Mode blocks observed write actions."""
        policy = self.base_policy()
        policy["mode"] = "review"
        event = self.pre_tool_event("apply_patch", "*** Update File: app.py\n")

        decision = hook.evaluate_pre_tool(policy, self.base_session(), event)

        self.assertFalse(decision.allowed)
        self.assertIn("Review Mode", decision.reason)

    def test_local_safe_refactor_allows_write_after_inspection(self) -> None:
        """Local Safe Refactor Mode allows a write after required inspection."""
        policy = self.base_policy()
        event = self.pre_tool_event("apply_patch", "*** Update File: app.py\n")

        decision = hook.evaluate_pre_tool(policy, self.base_session(), event)

        self.assertTrue(decision.allowed)

    def test_write_before_inspection_is_blocked(self) -> None:
        """Writes are blocked until inspection count and anchors are present."""
        policy = self.base_policy()
        session = self.base_session()
        session["inspection_anchors"] = []
        event = self.pre_tool_event("apply_patch", "*** Update File: app.py\n")

        decision = hook.evaluate_pre_tool(policy, session, event)

        self.assertFalse(decision.allowed)
        self.assertIn("inspection", decision.reason)

    def test_commit_push_ci_and_hook_install_are_blocked_without_approval(self) -> None:
        """Approval-gated commands and path edits fail closed by default."""
        policy = self.base_policy()
        session = self.base_session()
        cases = [
            ("exec_command", {"cmd": "git commit -m change"}, "commits"),
            ("exec_command", {"cmd": "git push origin HEAD"}, "pushes"),
            ("exec_command", {"cmd": "pre-commit install"}, "Hook installation"),
            (
                "apply_patch",
                "*** Update File: .github/workflows/verify.yml\n",
                "CI file changes",
            ),
        ]

        for tool_name, tool_input, expected in cases:
            with self.subTest(expected=expected):
                event = self.pre_tool_event(tool_name, tool_input)
                decision = hook.evaluate_pre_tool(policy, session, event)
                self.assertFalse(decision.allowed)
                self.assertIn(expected.split()[0], decision.reason)

    def test_user_prompt_approval_persists_to_state_and_audit(self) -> None:
        """A valid approval prompt records session approval and sanitized audit."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            codex_dir = cwd / ".codex"
            codex_dir.mkdir()
            policy = self.base_policy()
            (codex_dir / "safe-project-policy.json").write_text(
                json.dumps(policy), encoding="utf-8"
            )
            event = self.user_prompt_event(
                "SAFE-PROJECT APPROVE commits [until=session] REASON: release commit",
                cwd,
            )

            stdin = sys.stdin
            try:
                sys.stdin = io.StringIO(json.dumps(event))
                with redirect_stdout(io.StringIO()):
                    exit_code = hook.main(["--event", "UserPromptSubmit"])
            finally:
                sys.stdin = stdin

            self.assertEqual(exit_code, 0)
            state = json.loads(
                (codex_dir / "safe-project-session-state.json").read_text(
                    encoding="utf-8"
                )
            )
            approvals = state["sessions"]["test"]["approvals"]
            self.assertEqual(approvals[0]["gate"], "commits")
            self.assertEqual(approvals[0]["reason"], "release commit")
            self.assertEqual(approvals[0]["scope"], "session")
            audit = (codex_dir / "safe-project-audit.jsonl").read_text(
                encoding="utf-8"
            )
            self.assertIn("UserPromptSubmit", audit)
            self.assertIn("Recorded session approval for commits", audit)

    def test_malformed_approval_prompt_does_not_grant_gate(self) -> None:
        """Malformed approval prompts are allowed as prompts but grant nothing."""
        session = self.base_session()
        event = self.user_prompt_event("SAFE-PROJECT APPROVE commits REASON")

        decision = hook.handle_event(
            Path.cwd(), self.base_policy(), {}, session, "UserPromptSubmit", event
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(session.get("approvals"), None)

    def test_session_approval_allows_only_matching_gate(self) -> None:
        """A session approval overlays only the matching static policy gate."""
        policy = self.base_policy()
        session = self.base_session()
        hook.record_user_prompt_approval(
            session,
            self.user_prompt_event(
                "SAFE-PROJECT APPROVE commits [until=session] REASON: local checkpoint"
            ),
        )

        commit = hook.evaluate_pre_tool(
            policy,
            session,
            self.pre_tool_event("exec_command", {"cmd": "git commit -m x"}),
        )
        push = hook.evaluate_pre_tool(
            policy,
            session,
            self.pre_tool_event("exec_command", {"cmd": "git push"}),
        )

        self.assertTrue(commit.allowed)
        self.assertFalse(push.allowed)
        self.assertIn("pushes", push.reason)

    def test_classifier_blocks_commit_then_push_without_matching_approvals(self) -> None:
        """Segmented git commit and push commands require both approvals."""
        policy = self.base_policy()
        session = self.base_session()
        hook.record_user_prompt_approval(
            session,
            self.user_prompt_event(
                "SAFE-PROJECT APPROVE commits [until=session] REASON: local checkpoint"
            ),
        )
        event = self.pre_tool_event(
            "exec_command", {"cmd": "git commit -m x && git push"}
        )

        decision = hook.evaluate_pre_tool(policy, session, event)

        self.assertFalse(decision.allowed)
        self.assertIn("pushes", decision.reason)

    def test_classifier_blocks_redirection(self) -> None:
        """Shell redirection is treated as a risky file mutation."""
        decision = hook.evaluate_pre_tool(
            self.base_policy(),
            self.base_session(),
            self.pre_tool_event("exec_command", {"cmd": "echo x > file"}),
        )

        self.assertFalse(decision.allowed)

    def test_classifier_blocks_inline_python_writes(self) -> None:
        """Inline Python file writes are treated as risky shell mutations."""
        decision = hook.evaluate_pre_tool(
            self.base_policy(),
            self.base_session(),
            self.pre_tool_event(
                "exec_command", {"cmd": "python -c \"open('x','w').write('y')\""}
            ),
        )

        self.assertFalse(decision.allowed)

    def test_classifier_blocks_pipe_to_tee(self) -> None:
        """Pipes into tee are classified as file mutations."""
        decision = hook.evaluate_pre_tool(
            self.base_policy(),
            self.base_session(),
            self.pre_tool_event("exec_command", {"cmd": "cat file | tee out"}),
        )

        self.assertFalse(decision.allowed)

    def test_classifier_blocks_unmatched_quotes(self) -> None:
        """Unmatched shell quotes fail closed as complex commands."""
        decision = hook.evaluate_pre_tool(
            self.base_policy(),
            self.base_session(),
            self.pre_tool_event("exec_command", {"cmd": "echo 'unterminated"}),
        )

        self.assertFalse(decision.allowed)

    def test_classifier_blocks_heredoc_like_input(self) -> None:
        """Heredoc syntax fails closed as complex command input."""
        decision = hook.evaluate_pre_tool(
            self.base_policy(),
            self.base_session(),
            self.pre_tool_event("exec_command", {"cmd": "cat <<EOF\nx\nEOF"}),
        )

        self.assertFalse(decision.allowed)

    def test_verification_after_write_satisfies_stop_gate(self) -> None:
        """A successful verification command after a write clears Stop blocking."""
        policy = self.base_policy()
        session = self.base_session()
        write_event = self.post_tool_event("apply_patch", "*** Update File: app.py\n")
        verify_event = self.post_tool_event("exec_command", {"cmd": "make verify"})

        hook.record_post_tool(policy, session, write_event)
        hook.record_post_tool(policy, session, verify_event)

        with tempfile.TemporaryDirectory() as tmp:
            decision = hook.evaluate_stop(Path(tmp), policy, session)

        self.assertTrue(decision.allowed)

    def test_full_automation_valid_flow_records_commit_push_and_stop(self) -> None:
        """Full Automation accepts active item, write, verify, commit, push, stop."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            policy = self.full_automation_policy()
            session = self.base_session()
            commit_sha = "a" * 40
            self.write_policy(cwd, policy)
            self.write_workflow(cwd, [{"id": "P001", "status": "active"}], "P001")
            self.write_reports(cwd)

            write = self.pre_tool_event("apply_patch", "*** Update File: app.py\n")
            self.assertTrue(hook.evaluate_pre_tool(policy, session, write, cwd).allowed)
            hook.record_post_tool(policy, session, write, cwd)
            hook.record_post_tool(
                policy,
                session,
                self.post_tool_event("exec_command", {"cmd": "make verify"}),
                cwd,
            )

            commit = self.pre_tool_event("exec_command", {"cmd": "git commit -m P001"})
            self.assertTrue(hook.evaluate_pre_tool(policy, session, commit, cwd).allowed)
            hook.record_post_tool(
                policy,
                session,
                self.post_tool_event(
                    "exec_command",
                    {"cmd": "git commit -m P001"},
                    {"exit_code": 0, "stdout": commit_sha},
                ),
                cwd,
            )

            push = self.pre_tool_event("exec_command", {"cmd": "git push origin HEAD"})
            self.assertTrue(hook.evaluate_pre_tool(policy, session, push, cwd).allowed)
            hook.record_post_tool(
                policy,
                session,
                self.post_tool_event("exec_command", {"cmd": "git push origin HEAD"}),
                cwd,
            )

            workflow = json.loads(
                (cwd / ".codex" / "safe-project-workflow.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(workflow["items"][0]["commit_sha"], commit_sha)
            self.assertEqual(workflow["items"][0]["status"], "pushed")
            self.assertTrue(hook.evaluate_stop(cwd, policy, session).allowed)

    def test_full_automation_blocks_commit_before_verification(self) -> None:
        """Commits are blocked until verification passes after the latest write."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            policy = self.full_automation_policy()
            session = self.base_session()
            session["write_count"] = 1
            session["last_write_index"] = 3
            self.write_workflow(cwd, [{"id": "P001", "status": "active"}], "P001")
            self.write_reports(cwd)

            decision = hook.evaluate_pre_tool(
                policy,
                session,
                self.pre_tool_event("exec_command", {"cmd": "git commit -m P001"}),
                cwd,
            )

            self.assertFalse(decision.allowed)
            self.assertIn("verification", decision.reason)

    def test_full_automation_blocks_commit_with_no_active_item(self) -> None:
        """A commit needs one active workflow item."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            policy = self.full_automation_policy()
            session = self.base_session()
            session["verification_after_write"] = True
            self.write_workflow(cwd, [{"id": "P001", "status": "open"}])
            self.write_reports(cwd)

            decision = hook.evaluate_pre_tool(
                policy,
                session,
                self.pre_tool_event("exec_command", {"cmd": "git commit -m P001"}),
                cwd,
            )

            self.assertFalse(decision.allowed)
            self.assertIn("exactly one", decision.reason)

    def test_full_automation_blocks_multiple_active_items(self) -> None:
        """Multiple active workflow items are ambiguous and blocked."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            policy = self.full_automation_policy()
            self.write_workflow(
                cwd,
                [
                    {"id": "P001", "status": "active"},
                    {"id": "P002", "status": "active"},
                ],
            )
            self.write_reports(cwd)

            decision = hook.evaluate_pre_tool(
                policy,
                self.base_session(),
                self.pre_tool_event("apply_patch", "*** Update File: app.py\n"),
                cwd,
            )

            self.assertFalse(decision.allowed)
            self.assertIn("multiple active", decision.reason)

    def test_full_automation_blocks_push_with_unmapped_commit(self) -> None:
        """Pushes require every session commit to be mapped to a workflow item."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            policy = self.full_automation_policy()
            session = self.base_session()
            session["workflow_commits"] = ["b" * 40]
            self.write_workflow(
                cwd,
                [
                    {
                        "id": "P001",
                        "status": "committed",
                        "commit_sha": "c" * 40,
                        "verification": {"result": "passed"},
                    }
                ],
            )
            self.write_reports(cwd)

            decision = hook.evaluate_pre_tool(
                policy,
                session,
                self.pre_tool_event("exec_command", {"cmd": "git push origin HEAD"}),
                cwd,
            )

            self.assertFalse(decision.allowed)
            self.assertIn("Missing", decision.reason)

    def test_full_automation_blocks_stop_with_incomplete_workflow(self) -> None:
        """Stop blocks unfinished items unless they are explicitly deferred."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            policy = self.full_automation_policy()
            self.write_workflow(cwd, [{"id": "P001", "status": "active"}], "P001")
            self.write_reports(cwd)

            decision = hook.evaluate_stop(cwd, policy, self.base_session())

            self.assertFalse(decision.allowed)
            self.assertIn("incomplete", decision.reason)

    def test_full_automation_blocks_missing_run_report(self) -> None:
        """Full Automation requires a durable run report."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            policy = self.full_automation_policy()
            self.write_workflow(cwd, [{"id": "P001", "status": "active"}], "P001")

            decision = hook.evaluate_pre_tool(
                policy,
                self.base_session(),
                self.pre_tool_event("apply_patch", "*** Update File: app.py\n"),
                cwd,
            )

            self.assertFalse(decision.allowed)
            self.assertIn("Missing durable run report", decision.reason)

    def test_full_automation_blocks_report_missing_ledger_section(self) -> None:
        """Report validation checks required headings."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            policy = self.full_automation_policy()
            self.write_workflow(cwd, [{"id": "P001", "status": "active"}], "P001")
            self.write_reports(cwd)
            report = cwd / "docs" / "run-report.md"
            report.write_text(
                report.read_text(encoding="utf-8").replace(
                    "## Requirements Ledger\n", ""
                ),
                encoding="utf-8",
            )

            decision = hook.evaluate_pre_tool(
                policy,
                self.base_session(),
                self.pre_tool_event("apply_patch", "*** Update File: app.py\n"),
                cwd,
            )

            self.assertFalse(decision.allowed)
            self.assertIn("Requirements Ledger", decision.reason)

    def test_full_automation_blocks_missing_backlog_item_id(self) -> None:
        """The persisted backlog must include at least one workflow item ID."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            policy = self.full_automation_policy()
            self.write_workflow(cwd, [{"id": "P001", "status": "active"}], "P001")
            self.write_reports(cwd)
            backlog = cwd / "docs" / "patch-backlog.md"
            backlog.write_text(
                backlog.read_text(encoding="utf-8").replace("### P001", ""),
                encoding="utf-8",
            )

            decision = hook.evaluate_pre_tool(
                policy,
                self.base_session(),
                self.pre_tool_event("apply_patch", "*** Update File: app.py\n"),
                cwd,
            )

            self.assertFalse(decision.allowed)
            self.assertIn("workflow item ID", decision.reason)

    def test_valid_minimal_durable_reports_pass(self) -> None:
        """A minimal report/backlog with required headings and item IDs passes."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            policy = self.full_automation_policy()
            workflow = {"items": [{"id": "P001", "status": "active"}]}
            self.write_reports(cwd)

            decision = hook.validate_durable_reports(cwd, policy, workflow)

            self.assertTrue(decision.allowed)

    def test_protected_paths_block_unless_allowed(self) -> None:
        """Protected paths require explicit policy approval."""
        policy = self.base_policy()
        event = self.pre_tool_event("apply_patch", "*** Update File: pyproject.toml\n")

        blocked = hook.evaluate_pre_tool(policy, self.base_session(), event)
        policy["allowed_approval_gates"]["protected_path_edits"] = True
        allowed = hook.evaluate_pre_tool(policy, self.base_session(), event)

        self.assertFalse(blocked.allowed)
        self.assertTrue(allowed.allowed)

    def test_audit_sanitizes_secrets_and_truncates_large_payloads(self) -> None:
        """Audit sanitization redacts secret fields and large strings."""
        payload = {
            "api_key": "sk-secretsecretsecret",
            "cmd": "echo " + "x" * 1000,
        }

        sanitized = hook.sanitize(payload)

        self.assertEqual(sanitized["api_key"], "[REDACTED]")
        self.assertIn("[truncated]", sanitized["cmd"])

    def test_policy_template_is_valid_json(self) -> None:
        """The policy template parses as JSON."""
        parsed = json.loads(POLICY_TEMPLATE.read_text(encoding="utf-8"))

        self.assertTrue(parsed["enabled"])

    def test_config_template_uses_verified_codex_hook_shape(self) -> None:
        """The config template keeps the current Codex hook table shape."""
        config = (
            ROOT
            / "assets"
            / "codex_hooks"
            / "codex-config-snippet.template.toml"
        ).read_text(encoding="utf-8")

        self.assertIn("[[hooks.PreToolUse]]", config)
        self.assertIn("[[hooks.UserPromptSubmit]]", config)
        self.assertIn('type = "command"', config)

    def test_docs_mention_hook_limitations(self) -> None:
        """Runtime hook docs mention shell or unified execution limitations."""
        text = (ROOT / "references" / "agent-runtime-hooks.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("unified execution paths may not always", text)

    def test_session_start_block_output_uses_stop_reason(self) -> None:
        """SessionStart blocks use the SessionStart output schema."""
        output = hook.block_output("SessionStart", "missing policy")

        self.assertEqual(output["continue"], False)
        self.assertEqual(output["stopReason"], "missing policy")
        self.assertNotIn("decision", output)


if __name__ == "__main__":
    unittest.main()
