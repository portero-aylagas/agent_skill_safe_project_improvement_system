"""Tests for the portable safe project Codex hook handler."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
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
