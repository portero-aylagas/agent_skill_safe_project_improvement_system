"""Policy-driven Codex hook handler for safe project improvement sessions."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_POLICY_PATH = ".codex/safe-project-policy.json"
DEFAULT_AUDIT_PATH = ".codex/safe-project-audit.jsonl"
DEFAULT_STATE_PATH = ".codex/safe-project-session-state.json"
DEFAULT_WORKFLOW_STATE_PATH = ".codex/safe-project-workflow.json"
DEFAULT_RUN_REPORT_PATH = "docs/run-report.md"
DEFAULT_PATCH_BACKLOG_PATH = "docs/patch-backlog.md"
WORKFLOW_ITEM_ID_PATTERN = re.compile(r"^P\d{3}$")
FULL_AUTOMATION_REPORT_HEADINGS = [
    "Metadata",
    "Scope",
    "Requirements Ledger",
    "Backlog",
    "Patch Applied",
    "Pre-Publish Gate",
    "Verification",
    "Follow-Up",
]
BACKLOG_REPORT_HEADINGS = [
    "Requirements Ledger Snapshot",
    "Skipped Engineering Areas",
    "Skipped AI System Areas",
    "Backlog Items",
]
SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|token|secret|password|credential|authorization)", re.IGNORECASE
)
SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|"
    r"xox[baprs]-[A-Za-z0-9-]{12,})"
)
MAX_AUDIT_VALUE_CHARS = 600
MAX_AUDIT_LIST_ITEMS = 20
SUPPORTED_APPROVAL_GATES = {
    "commits",
    "pushes",
    "branch_changes",
    "hook_installation",
    "ci_changes",
    "live_service_commands",
    "protected_path_edits",
}
APPROVAL_PATTERN = re.compile(
    r"^\s*SAFE-PROJECT\s+APPROVE\s+"
    r"(?P<gate>[a-z_]+)"
    r"(?:\s+\[(?P<scope>until=session)\])?"
    r"\s+REASON:\s+(?P<reason>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class Decision:
    """Decision returned by policy evaluation."""

    allowed: bool
    reason: str = ""


@dataclass(frozen=True)
class CommandSegment:
    """One parsed shell command segment."""

    words: list[str]
    separator: str = ""


@dataclass(frozen=True)
class CommandAnalysis:
    """Conservative classification for one shell command."""

    segments: list[CommandSegment]
    paths: list[str]
    gates: set[str]
    write_action: bool = False
    read_action: bool = False
    live_service: bool = False
    risky_unknown: bool = False
    parse_error: str = ""


def main(argv: list[str] | None = None) -> int:
    """Run the hook handler as a Codex command hook.

    Args:
        argv: Optional command-line arguments. When omitted, `sys.argv` is used.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default=DEFAULT_POLICY_PATH)
    parser.add_argument("--event", default=None)
    args = parser.parse_args(argv)

    raw_input = sys.stdin.read()
    try:
        event = json.loads(raw_input or "{}")
    except json.JSONDecodeError as error:
        print_json(block_output(args.event or "Unknown", "invalid hook JSON input", str(error)))
        return 0

    cwd = Path(event.get("cwd") or os.getcwd()).resolve()
    event_name = args.event or event.get("hook_event_name") or "Unknown"

    try:
        policy = load_policy(cwd, args.policy)
    except ValueError as error:
        print_json(
            block_output(
                event_name, "safe project policy is missing or invalid", str(error)
            )
        )
        return 0

    state = load_state(cwd, policy)
    session = session_state(state, event)
    decision = handle_event(cwd, policy, state, session, event_name, event)
    append_audit(cwd, policy, event_name, event, decision)
    save_state(cwd, policy, state)

    if decision.allowed:
        print_json(allow_output(event_name))
    else:
        print_json(block_output(event_name, decision.reason))
    return 0


def load_policy(cwd: Path, policy_path: str) -> dict[str, Any]:
    """Load and validate repo-local policy.

    Args:
        cwd: Repository working directory supplied by Codex.
        policy_path: Policy file path, relative to `cwd` unless absolute.

    Returns:
        Parsed policy dictionary.

    Raises:
        ValueError: If enforcement is unavailable because policy is missing or
            invalid.
    """
    path = resolve_repo_path(cwd, policy_path)
    if not path.is_file():
        raise ValueError(f"expected policy file at {path}")
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: {error}") from error
    if not isinstance(policy, dict):
        raise ValueError("policy root must be a JSON object")
    if not policy.get("enabled", True):
        raise ValueError("policy disabled; remove the hook or enable policy explicitly")
    return apply_policy_defaults(policy)


def apply_policy_defaults(policy: dict[str, Any]) -> dict[str, Any]:
    """Return policy with conservative defaults filled in."""
    merged = {
        "mode": "local_safe_refactor",
        "verification_command": "make verify",
        "minimum_inspection_evidence": 2,
        "required_inspection_anchors": [],
        "audit_log": DEFAULT_AUDIT_PATH,
        "state_file": DEFAULT_STATE_PATH,
        "workflow_state_file": DEFAULT_WORKFLOW_STATE_PATH,
        "run_report": DEFAULT_RUN_REPORT_PATH,
        "patch_backlog": DEFAULT_PATCH_BACKLOG_PATH,
        "require_durable_reports": False,
        "protected_paths": [],
        "allowed_approval_gates": {},
        "live_service_env_vars": [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "AWS_ACCESS_KEY_ID",
            "GOOGLE_API_KEY",
        ],
        "forbidden_live_service_commands": [],
    }
    merged.update(policy)
    gates = {
        "commits": False,
        "pushes": False,
        "branch_changes": False,
        "hook_installation": False,
        "ci_changes": False,
        "live_service_commands": False,
        "protected_path_edits": False,
    }
    gates.update(merged.get("allowed_approval_gates") or {})
    merged["allowed_approval_gates"] = gates
    return merged


def load_state(cwd: Path, policy: dict[str, Any]) -> dict[str, Any]:
    """Load hook session state, returning an empty state when none exists."""
    path = resolve_repo_path(cwd, policy["state_file"])
    if not path.is_file():
        return {"sessions": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"sessions": {}}
    if not isinstance(state, dict):
        return {"sessions": {}}
    state.setdefault("sessions", {})
    return state


def save_state(cwd: Path, policy: dict[str, Any], state: dict[str, Any]) -> None:
    """Persist hook session state."""
    path = resolve_repo_path(cwd, policy["state_file"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def session_state(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Return mutable state for the current Codex session."""
    session_id = str(event.get("session_id") or "unknown-session")
    sessions = state.setdefault("sessions", {})
    session = sessions.setdefault(
        session_id,
        {
            "inspection_events": 0,
            "inspection_anchors": [],
            "write_count": 0,
            "last_write_index": 0,
            "verification_after_write": False,
            "event_index": 0,
            "failures": [],
            "approvals": [],
            "started_at": now_iso(),
        },
    )
    session.setdefault("approvals", [])
    session["event_index"] = int(session.get("event_index", 0)) + 1
    return session


def handle_event(
    cwd: Path,
    policy: dict[str, Any],
    state: dict[str, Any],
    session: dict[str, Any],
    event_name: str,
    event: dict[str, Any],
) -> Decision:
    """Update state and evaluate the current hook event."""
    if event_name == "SessionStart":
        record_session_start(cwd, policy, session)
        return Decision(True)
    if event_name == "PreToolUse":
        return evaluate_pre_tool(policy, session, event, cwd)
    if event_name == "UserPromptSubmit":
        return record_user_prompt_approval(session, event)
    if event_name == "PostToolUse":
        record_post_tool(policy, session, event, cwd)
        return Decision(True)
    if event_name == "Stop":
        return evaluate_stop(cwd, policy, session)
    state.setdefault("unknown_events", []).append(event_name)
    return Decision(True)


def record_session_start(cwd: Path, policy: dict[str, Any], session: dict[str, Any]) -> None:
    """Record repository state visible at session start."""
    session["policy_mode"] = policy["mode"]
    session["start_git"] = git_snapshot(cwd)


def evaluate_pre_tool(
    policy: dict[str, Any],
    session: dict[str, Any],
    event: dict[str, Any],
    cwd: Path | None = None,
) -> Decision:
    """Evaluate a `PreToolUse` event before Codex runs a tool."""
    repo = cwd or Path.cwd()
    tool_name = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input") or {}
    command = extract_command(tool_input)
    analysis = analyze_command(command, policy) if command else empty_command_analysis()
    changed_paths = extract_candidate_paths(tool_name, tool_input, command, analysis)
    write_action = is_write_action(tool_name, tool_input, command, analysis)
    workflow_decision = workflow_pre_tool_decision(
        repo, policy, session, command, analysis, write_action
    )
    if not workflow_decision.allowed:
        return workflow_decision

    if policy["mode"] == "review" and write_action:
        return Decision(False, "Review Mode blocks file and workspace writes.")
    if write_action and not inspection_gate_satisfied(policy, session):
        return Decision(False, "Writes are blocked until required inspection evidence exists.")
    if command:
        blocked_command = command_policy_decision(command, policy, session, analysis)
        if not blocked_command.allowed:
            return blocked_command
        if analysis.live_service and not gate_allowed(policy, session, "live_service_commands"):
            return Decision(False, "Live-service commands require explicit policy approval.")
    if touches_ci(changed_paths) and not gate_allowed(policy, session, "ci_changes"):
        return Decision(False, "CI file changes require explicit policy approval.")
    if touches_hook_installation(changed_paths, command, analysis) and not gate_allowed(
        policy, session, "hook_installation"
    ):
        return Decision(False, "Hook installation or hook config changes require approval.")
    if touches_protected_path(changed_paths, policy) and not gate_allowed(
        policy, session, "protected_path_edits"
    ):
        return Decision(False, "Protected path edits require explicit policy approval.")
    return Decision(True)


def record_user_prompt_approval(session: dict[str, Any], event: dict[str, Any]) -> Decision:
    """Record session-scoped approval gates from an explicit user prompt."""
    prompt = extract_prompt(event)
    if not prompt:
        return Decision(True)
    match = APPROVAL_PATTERN.match(prompt)
    if not match:
        return Decision(True)
    gate = match.group("gate").lower()
    scope = match.group("scope") or "until=session"
    reason = match.group("reason").strip()
    if gate not in SUPPORTED_APPROVAL_GATES or scope != "until=session" or not reason:
        return Decision(True)
    approval = {
        "gate": gate,
        "reason": reason,
        "timestamp": now_iso(),
        "event_index": session.get("event_index", 0),
        "scope": "session",
    }
    session.setdefault("approvals", []).append(approval)
    return Decision(True, f"Recorded session approval for {gate}.")


def extract_prompt(event: dict[str, Any]) -> str:
    """Extract a user prompt from known Codex hook payload shapes."""
    for key in ("prompt", "user_prompt", "message"):
        value = event.get(key)
        if isinstance(value, str):
            return value
    tool_input = event.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("prompt", "user_prompt", "message"):
            value = tool_input.get(key)
            if isinstance(value, str):
                return value
    return ""


def gate_allowed(
    policy: dict[str, Any], session: dict[str, Any], gate: str
) -> bool:
    """Return whether static policy or current session approval allows a gate."""
    if bool(policy["allowed_approval_gates"].get(gate)):
        return True
    for approval in session.get("approvals", []):
        if (
            isinstance(approval, dict)
            and approval.get("gate") == gate
            and approval.get("scope") == "session"
        ):
            return True
    return False


def command_policy_decision(
    command: str,
    policy: dict[str, Any],
    session: dict[str, Any],
    analysis: CommandAnalysis | None = None,
) -> Decision:
    """Return a decision for shell commands with explicit approval gates."""
    classified = analysis or analyze_command(command, policy)
    if "commits" in classified.gates and not gate_allowed(policy, session, "commits"):
        return Decision(False, "Git commits require explicit policy approval.")
    if "pushes" in classified.gates and not gate_allowed(policy, session, "pushes"):
        return Decision(False, "Git pushes require explicit policy approval.")
    if "branch_changes" in classified.gates and not gate_allowed(
        policy, session, "branch_changes"
    ):
        return Decision(False, "Git branch or history changes require explicit approval.")
    if "hook_installation" in classified.gates and not gate_allowed(
        policy, session, "hook_installation"
    ):
        return Decision(False, "Hook installation or hook config changes require approval.")
    if "ci_changes" in classified.gates and not gate_allowed(policy, session, "ci_changes"):
        return Decision(False, "CI file changes require explicit policy approval.")
    if "protected_path_edits" in classified.gates and not gate_allowed(
        policy, session, "protected_path_edits"
    ):
        return Decision(False, "Protected path edits require explicit policy approval.")
    if classified.risky_unknown and not any(
        gate_allowed(policy, session, gate) for gate in classified.gates
    ):
        detail = f" ({classified.parse_error})" if classified.parse_error else ""
        return Decision(
            False,
            "Complex or risky shell commands require an applicable approval gate"
            f"{detail}.",
        )
    return Decision(True)


def record_post_tool(
    policy: dict[str, Any],
    session: dict[str, Any],
    event: dict[str, Any],
    cwd: Path | None = None,
) -> None:
    """Record evidence from a completed tool call."""
    repo = cwd or Path.cwd()
    tool_name = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input") or {}
    tool_response = event.get("tool_response") or {}
    command = extract_command(tool_input)

    analysis = analyze_command(command, policy) if command else empty_command_analysis()

    if is_read_action(tool_name, tool_input, command, analysis):
        session["inspection_events"] = int(session.get("inspection_events", 0)) + 1
        update_inspection_anchors(policy, session, tool_input, command)
    publish_action = policy.get("mode") == "full_automation" and (
        is_git_commit_command(analysis) or is_git_push_command(analysis)
    )
    if is_write_action(tool_name, tool_input, command, analysis) and not publish_action:
        session["write_count"] = int(session.get("write_count", 0)) + 1
        session["last_write_index"] = session.get("event_index", 0)
        session["verification_after_write"] = False
    if command and command_matches_verification(command, policy["verification_command"]):
        if int(session.get("write_count", 0)) > 0:
            session["verification_after_write"] = command_succeeded(tool_response)
        record_workflow_verification(repo, policy, session, command, tool_response)
    record_workflow_git_evidence(repo, policy, session, command, tool_response)
    if not command_succeeded(tool_response):
        session.setdefault("failures", []).append(
            {"event_index": session.get("event_index", 0), "tool_name": tool_name}
        )


def evaluate_stop(cwd: Path, policy: dict[str, Any], session: dict[str, Any]) -> Decision:
    """Evaluate whether the session can end cleanly."""
    session["final_git"] = git_snapshot(cwd)
    workflow_decision = workflow_stop_decision(cwd, policy, session)
    if not workflow_decision.allowed:
        return workflow_decision
    wrote = int(session.get("write_count", 0)) > 0
    changed = bool(session["final_git"].get("status"))
    verified = bool(session.get("verification_after_write"))
    if (wrote or changed) and not verified:
        return Decision(
            False,
            "Session has changed files or observed writes without successful "
            "verification after the first write.",
        )
    return Decision(True)


def workflow_pre_tool_decision(
    cwd: Path,
    policy: dict[str, Any],
    session: dict[str, Any],
    command: str,
    analysis: CommandAnalysis,
    write_action: bool,
) -> Decision:
    """Enforce Full Automation workflow ordering before a tool runs."""
    if policy.get("mode") != "full_automation":
        return durable_report_decision(cwd, policy)
    workflow = load_workflow_state(cwd, policy)
    if workflow is None:
        return Decision(
            False,
            "Full Automation requires workflow state at "
            f"{policy['workflow_state_file']}. Create audited/backlog items first.",
        )
    structure = validate_workflow_structure(workflow)
    if not structure.allowed:
        return structure
    reports = validate_durable_reports(cwd, policy, workflow)
    if not reports.allowed:
        return reports

    if is_git_commit_command(analysis):
        return workflow_commit_decision(cwd, policy, session, workflow)
    if is_git_push_command(analysis):
        return workflow_push_decision(cwd, session, workflow)
    active_items = workflow_active_items(workflow)
    if write_action:
        if len(active_items) != 1:
            return Decision(
                False,
                "Full Automation writes require exactly one active workflow item. "
                "Set one item status to active and clear other active items.",
            )
    return Decision(True)


def durable_report_decision(cwd: Path, policy: dict[str, Any]) -> Decision:
    """Require durable reports for non-Full-Automation modes when enabled."""
    if not policy.get("require_durable_reports"):
        return Decision(True)
    workflow = load_workflow_state(cwd, policy) or {"items": []}
    return validate_durable_reports(cwd, policy, workflow)


def workflow_commit_decision(
    cwd: Path,
    policy: dict[str, Any],
    session: dict[str, Any],
    workflow: dict[str, Any],
) -> Decision:
    """Return whether a commit may be created for the active item."""
    active_items = workflow_active_items(workflow)
    if len(active_items) != 1:
        return Decision(
            False,
            "Commit blocked: exactly one workflow item must be active. "
            "Activate one P### item before committing.",
        )
    item = active_items[0]
    item_id = str(item["id"])
    if not bool(session.get("verification_after_write")):
        return Decision(
            False,
            "Commit blocked: run successful verification after the latest write "
            f"for active item {item_id}.",
        )
    verification = workflow_item_verification(item)
    if verification.get("result") != "passed":
        return Decision(
            False,
            "Commit blocked: workflow state must record passed verification "
            f"for active item {item_id}.",
        )
    if int(verification.get("event_index") or 0) < int(session.get("last_write_index", 0)):
        return Decision(
            False,
            "Commit blocked: workflow verification is older than the latest write. "
            f"Re-run {policy['verification_command']} and update {item_id}.",
        )
    report_text = read_optional_text(resolve_repo_path(cwd, policy["run_report"]))
    if item_id not in report_text:
        return Decision(
            False,
            f"Commit blocked: {policy['run_report']} must name active item {item_id}.",
        )
    return Decision(True)


def workflow_push_decision(
    cwd: Path, session: dict[str, Any], workflow: dict[str, Any]
) -> Decision:
    """Return whether all session commits are mapped before push."""
    local_commits = commits_created_in_session(cwd, session)
    mapped = workflow_mapped_commit_shas(workflow)
    missing = [sha for sha in local_commits if sha not in mapped]
    if missing:
        short = ", ".join(sha[:12] for sha in missing)
        return Decision(
            False,
            "Push blocked: every session commit must map to one workflow item "
            f"with verification evidence. Missing: {short}.",
        )
    unverified = [
        str(item["id"])
        for item in workflow_items(workflow)
        if item.get("commit_sha") in local_commits
        and workflow_item_verification(item).get("result") != "passed"
    ]
    if unverified:
        return Decision(
            False,
            "Push blocked: mapped commits need passed verification evidence for "
            + ", ".join(unverified)
            + ".",
        )
    return Decision(True)


def workflow_stop_decision(
    cwd: Path, policy: dict[str, Any], session: dict[str, Any]
) -> Decision:
    """Block incomplete Full Automation sessions at Stop."""
    if policy.get("mode") != "full_automation":
        return durable_report_decision(cwd, policy)
    workflow = load_workflow_state(cwd, policy)
    if workflow is None:
        return Decision(
            False,
            "Full Automation cannot stop without workflow state. Create "
            f"{policy['workflow_state_file']} or switch policy mode.",
        )
    structure = validate_workflow_structure(workflow)
    if not structure.allowed:
        return structure
    reports = validate_durable_reports(cwd, policy, workflow)
    if not reports.allowed:
        return reports
    incomplete = []
    report_text = read_optional_text(resolve_repo_path(cwd, policy["run_report"]))
    for item in workflow_items(workflow):
        status = str(item.get("status") or "").lower()
        item_id = str(item["id"])
        if status in {"done", "committed", "pushed", "completed"}:
            continue
        if status == "deferred" and item.get("deferral_reason") and item_id in report_text:
            continue
        incomplete.append(item_id)
    if incomplete:
        return Decision(
            False,
            "Full Automation session incomplete: finish or defer workflow items "
            + ", ".join(incomplete)
            + " in workflow state and run report.",
        )
    unmapped = [
        sha for sha in commits_created_in_session(cwd, session)
        if sha not in workflow_mapped_commit_shas(workflow)
    ]
    if unmapped:
        short = ", ".join(sha[:12] for sha in unmapped)
        return Decision(
            False,
            "Full Automation session has unmapped commits. Add commit evidence "
            f"to workflow items before stopping: {short}.",
        )
    return Decision(True)


def record_workflow_verification(
    cwd: Path,
    policy: dict[str, Any],
    session: dict[str, Any],
    command: str,
    tool_response: Any,
) -> None:
    """Record verification evidence for the active workflow item."""
    if policy.get("mode") != "full_automation":
        return
    workflow = load_workflow_state(cwd, policy)
    if workflow is None or not command_matches_verification(
        command, policy["verification_command"]
    ):
        return
    active_items = workflow_active_items(workflow)
    if len(active_items) != 1:
        return
    item = active_items[0]
    item["verification"] = {
        "command": command,
        "result": "passed" if command_succeeded(tool_response) else "failed",
        "event_index": session.get("event_index", 0),
        "timestamp": now_iso(),
    }
    save_workflow_state(cwd, policy, workflow)


def record_workflow_git_evidence(
    cwd: Path,
    policy: dict[str, Any],
    session: dict[str, Any],
    command: str,
    tool_response: Any,
) -> None:
    """Record branch, commit, and push evidence after successful git commands."""
    if policy.get("mode") != "full_automation" or not command or not command_succeeded(
        tool_response
    ):
        return
    workflow = load_workflow_state(cwd, policy)
    if workflow is None:
        return
    analysis = analyze_command(command, policy)
    snapshot = git_snapshot(cwd)
    if is_git_branch_change_command(analysis):
        workflow["branch"] = snapshot.get("branch") or workflow.get("branch")
    if is_git_commit_command(analysis):
        active_items = workflow_active_items(workflow)
        if len(active_items) == 1:
            commit_sha = snapshot.get("commit") or extract_commit_sha(tool_response)
            if commit_sha:
                active_items[0]["commit_sha"] = commit_sha
                active_items[0]["status"] = "committed"
                session.setdefault("workflow_commits", []).append(commit_sha)
    if is_git_push_command(analysis):
        mapped = set(workflow_mapped_commit_shas(workflow))
        for item in workflow_items(workflow):
            if item.get("commit_sha") in mapped:
                item["pushed"] = True
                if str(item.get("status") or "").lower() == "committed":
                    item["status"] = "pushed"
    save_workflow_state(cwd, policy, workflow)


def load_workflow_state(cwd: Path, policy: dict[str, Any]) -> dict[str, Any] | None:
    """Load the durable workflow state file."""
    path = resolve_repo_path(cwd, policy["workflow_state_file"])
    if not path.is_file():
        return None
    try:
        workflow = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"items": [], "invalid": "workflow state must be valid JSON"}
    if not isinstance(workflow, dict):
        return {"items": [], "invalid": "workflow state root must be an object"}
    return workflow


def save_workflow_state(
    cwd: Path, policy: dict[str, Any], workflow: dict[str, Any]
) -> None:
    """Persist the durable workflow state file."""
    path = resolve_repo_path(cwd, policy["workflow_state_file"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(workflow, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def validate_workflow_structure(workflow: dict[str, Any]) -> Decision:
    """Validate machine-readable Full Automation workflow state."""
    if workflow.get("invalid"):
        return Decision(False, str(workflow["invalid"]))
    items = workflow_items(workflow)
    if not items:
        return Decision(
            False,
            "Full Automation workflow state must contain audited/backlog items.",
        )
    seen: set[str] = set()
    for item in items:
        item_id = str(item.get("id") or "")
        if not WORKFLOW_ITEM_ID_PATTERN.match(item_id):
            return Decision(
                False,
                "Workflow items need stable IDs like P001. Fix the workflow state.",
            )
        if item_id in seen:
            return Decision(False, f"Workflow item ID {item_id} appears more than once.")
        seen.add(item_id)
        if not item.get("status"):
            return Decision(False, f"Workflow item {item_id} needs a status.")
    if len(workflow_active_items(workflow)) > 1:
        return Decision(
            False,
            "Workflow state has multiple active items. Leave exactly one active item.",
        )
    return Decision(True)


def validate_durable_reports(
    cwd: Path, policy: dict[str, Any], workflow: dict[str, Any]
) -> Decision:
    """Validate required report and backlog artifacts by structure."""
    if policy.get("mode") != "full_automation" and not policy.get(
        "require_durable_reports"
    ):
        return Decision(True)
    report_path = resolve_repo_path(cwd, policy["run_report"])
    backlog_path = resolve_repo_path(cwd, policy["patch_backlog"])
    if not report_path.is_file():
        return Decision(False, f"Missing durable run report at {policy['run_report']}.")
    if not backlog_path.is_file():
        return Decision(
            False, f"Missing durable patch backlog at {policy['patch_backlog']}."
        )
    report_text = report_path.read_text(encoding="utf-8")
    backlog_text = backlog_path.read_text(encoding="utf-8")
    missing_report = missing_headings(report_text, FULL_AUTOMATION_REPORT_HEADINGS)
    if missing_report:
        return Decision(
            False,
            f"{policy['run_report']} is missing required section(s): "
            + ", ".join(missing_report)
            + ".",
        )
    missing_backlog = missing_headings(backlog_text, BACKLOG_REPORT_HEADINGS)
    if missing_backlog:
        return Decision(
            False,
            f"{policy['patch_backlog']} is missing required section(s): "
            + ", ".join(missing_backlog)
            + ".",
        )
    item_ids = [str(item["id"]) for item in workflow_items(workflow)]
    if item_ids and not any(item_id in backlog_text for item_id in item_ids):
        return Decision(
            False,
            f"{policy['patch_backlog']} must include at least one workflow item ID.",
        )
    return Decision(True)


def workflow_items(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Return workflow items as mutable dictionaries."""
    raw_items = workflow.get("items") or workflow.get("backlog") or []
    if isinstance(raw_items, dict):
        items = []
        for item_id, item in raw_items.items():
            if isinstance(item, dict):
                item.setdefault("id", str(item_id))
                items.append(item)
        return items
    if isinstance(raw_items, list):
        return [item for item in raw_items if isinstance(item, dict)]
    return []


def workflow_active_items(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Return items marked active by status or active_item."""
    active_id = workflow.get("active_item")
    active = []
    terminal_statuses = {"done", "committed", "pushed", "completed", "deferred"}
    for item in workflow_items(workflow):
        status = str(item.get("status") or "").lower()
        if status == "active" or (
            active_id and item.get("id") == active_id and status not in terminal_statuses
        ):
            active.append(item)
    return active


def workflow_item_verification(item: dict[str, Any]) -> dict[str, Any]:
    """Return normalized verification evidence for a workflow item."""
    verification = item.get("verification")
    if isinstance(verification, dict):
        return verification
    if item.get("verification_result"):
        return {
            "result": item.get("verification_result"),
            "event_index": item.get("verification_event_index", 0),
        }
    return {}


def workflow_mapped_commit_shas(workflow: dict[str, Any]) -> set[str]:
    """Return commit SHAs mapped to workflow items with verification evidence."""
    mapped = set()
    for item in workflow_items(workflow):
        commit_sha = item.get("commit_sha")
        if commit_sha and workflow_item_verification(item).get("result") == "passed":
            mapped.add(str(commit_sha))
    return mapped


def missing_headings(text: str, headings: list[str]) -> list[str]:
    """Return headings absent from a markdown document."""
    found = {
        match.group(1).strip()
        for match in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, re.MULTILINE)
    }
    return [heading for heading in headings if heading not in found]


def is_git_commit_command(analysis: CommandAnalysis) -> bool:
    """Return whether analysis contains a git commit segment."""
    return any(segment.words[:2] == ["git", "commit"] for segment in analysis.segments)


def is_git_push_command(analysis: CommandAnalysis) -> bool:
    """Return whether analysis contains a git push segment."""
    return any(segment.words[:2] == ["git", "push"] for segment in analysis.segments)


def is_git_branch_change_command(analysis: CommandAnalysis) -> bool:
    """Return whether analysis contains a git branch/history segment."""
    branch_subcommands = {"checkout", "switch", "branch", "rebase", "merge", "reset"}
    return any(
        len(segment.words) > 1
        and segment.words[0] == "git"
        and segment.words[1] in branch_subcommands
        for segment in analysis.segments
    )


def commits_created_in_session(cwd: Path, session: dict[str, Any]) -> list[str]:
    """Return commits between session start and current HEAD when available."""
    start_commit = (session.get("start_git") or {}).get("commit")
    if isinstance(start_commit, str) and start_commit:
        try:
            result = subprocess.run(
                ["git", "rev-list", "--reverse", f"{start_commit}..HEAD"],
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            result = None
        if result and result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return [str(sha) for sha in session.get("workflow_commits", []) if sha]


def extract_commit_sha(tool_response: Any) -> str:
    """Extract a commit SHA from a tool response if present."""
    if not isinstance(tool_response, dict):
        return ""
    text = " ".join(
        str(tool_response.get(key) or "")
        for key in ("stdout", "stderr", "output", "message")
    )
    match = re.search(r"\b[0-9a-f]{40}\b", text)
    return match.group(0) if match else ""


def read_optional_text(path: Path) -> str:
    """Read a text file, returning empty text when absent."""
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def extract_command(tool_input: Any) -> str:
    """Extract a shell command string from a Codex tool input."""
    if isinstance(tool_input, dict):
        command = tool_input.get("cmd") or tool_input.get("command")
        if isinstance(command, str):
            return command.strip()
    return ""


def extract_candidate_paths(
    tool_name: str,
    tool_input: Any,
    command: str,
    analysis: CommandAnalysis | None = None,
) -> list[str]:
    """Extract likely file paths from tool input for path-based policy checks."""
    paths: list[str] = []
    if isinstance(tool_input, dict):
        for key in ("path", "file", "workdir"):
            value = tool_input.get(key)
            if isinstance(value, str):
                paths.append(value)
        patch = tool_input.get("patch") or tool_input.get("input")
        if isinstance(patch, str):
            paths.extend(extract_paths_from_patch(patch))
    if "apply_patch" in tool_name and isinstance(tool_input, str):
        paths.extend(extract_paths_from_patch(tool_input))
    if command:
        classified = analysis or analyze_command(command, apply_policy_defaults({}))
        paths.extend(classified.paths)
    return normalize_paths(paths)


def extract_paths_from_patch(patch: str) -> list[str]:
    """Extract file paths from an apply-patch style payload."""
    paths = []
    for line in patch.splitlines():
        for prefix in (
            "*** Add File: ",
            "*** Update File: ",
            "*** Delete File: ",
            "*** Move to: ",
            "+++ b/",
            "--- a/",
        ):
            if line.startswith(prefix):
                paths.append(line.removeprefix(prefix).strip())
    return paths


def is_write_action(
    tool_name: str,
    tool_input: Any,
    command: str,
    analysis: CommandAnalysis | None = None,
) -> bool:
    """Return whether a tool call appears to mutate files, git state, or config."""
    lowered_tool = tool_name.lower()
    if "apply_patch" in lowered_tool or "update_file" in lowered_tool:
        return True
    if not command:
        return False
    classified = analysis or analyze_command(command, apply_policy_defaults({}))
    return classified.write_action


def is_read_action(
    tool_name: str,
    tool_input: Any,
    command: str,
    analysis: CommandAnalysis | None = None,
) -> bool:
    """Return whether a tool call appears to inspect the repository."""
    lowered_tool = tool_name.lower()
    if any(name in lowered_tool for name in ("open", "fetch", "search", "read")):
        return True
    if not command:
        return False
    classified = analysis or analyze_command(command, apply_policy_defaults({}))
    return classified.read_action


def inspection_gate_satisfied(policy: dict[str, Any], session: dict[str, Any]) -> bool:
    """Return whether observed inspection evidence satisfies policy."""
    count = int(session.get("inspection_events", 0))
    if count < int(policy.get("minimum_inspection_evidence", 0)):
        return False
    seen = set(session.get("inspection_anchors", []))
    required = set(policy.get("required_inspection_anchors", []))
    return required.issubset(seen)


def update_inspection_anchors(
    policy: dict[str, Any], session: dict[str, Any], tool_input: Any, command: str
) -> None:
    """Record policy anchors whose text appeared in read evidence."""
    evidence = json.dumps(tool_input, sort_keys=True) + "\n" + command
    anchors = set(session.get("inspection_anchors", []))
    for anchor in policy.get("required_inspection_anchors", []):
        if anchor in evidence:
            anchors.add(anchor)
    session["inspection_anchors"] = sorted(anchors)


def command_matches_verification(command: str, verification_command: str) -> bool:
    """Return whether `command` runs the configured verification command."""
    return command.strip() == verification_command.strip()


def command_succeeded(tool_response: Any) -> bool:
    """Infer command success from a Codex tool response payload."""
    if not isinstance(tool_response, dict):
        return True
    for key in ("exit_code", "returncode", "code"):
        value = tool_response.get(key)
        if isinstance(value, int):
            return value == 0
    status = str(tool_response.get("status") or "").lower()
    if status:
        return status in {"success", "succeeded", "completed", "ok"}
    return True


def touches_ci(paths: list[str]) -> bool:
    """Return whether paths include CI workflow files."""
    return any(path.startswith(".github/workflows/") for path in paths)


def touches_hook_installation(
    paths: list[str], command: str, analysis: CommandAnalysis | None = None
) -> bool:
    """Return whether paths or command indicate hook installation/config changes."""
    hook_paths = (".git/hooks/", ".pre-commit-config.yaml", "pre-commit-config.yaml")
    if any(path.startswith(hook_paths) for path in paths):
        return True
    if analysis and "hook_installation" in analysis.gates:
        return True
    return "pre-commit install" in command.lower()


def touches_protected_path(paths: list[str], policy: dict[str, Any]) -> bool:
    """Return whether any path matches policy-protected globs."""
    protected = policy.get("protected_paths") or []
    return any(fnmatch.fnmatch(path, pattern) for path in paths for pattern in protected)


def is_live_service_command(command: str, policy: dict[str, Any]) -> bool:
    """Return whether command appears to call live services or expose live credentials."""
    lowered = command.lower()
    forbidden = [item.lower() for item in policy.get("forbidden_live_service_commands", [])]
    if any(item and item in lowered for item in forbidden):
        return True
    if any(env_var in command for env_var in policy.get("live_service_env_vars", [])):
        return True
    return any(token in lowered for token in ("curl ", "wget ", "openai ", "aws ", "gcloud "))


def empty_command_analysis() -> CommandAnalysis:
    """Return an empty command classification."""
    return CommandAnalysis(segments=[], paths=[], gates=set())


def analyze_command(command: str, policy: dict[str, Any]) -> CommandAnalysis:
    """Classify a shell command into segments, candidate paths, and approval gates."""
    segments, parse_error = split_command_segments(command)
    paths: list[str] = []
    gates: set[str] = set()
    write_action = False
    read_action = False
    risky_unknown = bool(parse_error)
    live_service = is_live_service_command(command, policy)
    if live_service:
        gates.add("live_service_commands")

    for segment in segments:
        words = segment.words
        if not words:
            continue
        executable = Path(words[0]).name
        if segment_has_complex_shell(command, words):
            risky_unknown = True
            write_action = True
            gates.add("protected_path_edits")
        paths.extend(word for word in words[1:] if looks_like_path(word))

        if executable == "git":
            read_action = True
            if len(words) > 1:
                subcommand = words[1]
                if subcommand == "commit":
                    gates.add("commits")
                    write_action = True
                elif subcommand == "push":
                    gates.add("pushes")
                    write_action = True
                elif subcommand in {
                    "checkout",
                    "switch",
                    "branch",
                    "rebase",
                    "merge",
                    "reset",
                }:
                    gates.add("branch_changes")
                    write_action = True
                elif subcommand in {"add", "mv", "rm", "restore"}:
                    write_action = True
            continue

        if executable == "pre-commit" and len(words) > 1 and words[1] == "install":
            gates.add("hook_installation")
            write_action = True
            continue

        if executable in {"tee", "touch", "mkdir", "rm", "mv", "cp", "install"}:
            write_action = True
            gates.add("protected_path_edits")
            paths.extend(word for word in words[1:] if not word.startswith("-"))
        elif executable in {"sed"} and "-i" in words:
            write_action = True
            gates.add("protected_path_edits")
        elif executable in {"python", "python3"} and "-c" in words:
            if python_inline_code_writes(words):
                write_action = True
                risky_unknown = True
                gates.add("protected_path_edits")
        elif executable in {"ls", "rg", "find", "cat", "pwd", "sed", "nl", "wc"}:
            read_action = True
        else:
            if command_segment_may_write(words):
                write_action = True
                risky_unknown = True
                gates.add("protected_path_edits")

    normalized_paths = normalize_paths(paths)
    if touches_ci(normalized_paths):
        gates.add("ci_changes")
    if touches_hook_installation(normalized_paths, command):
        gates.add("hook_installation")
    if touches_protected_path(normalized_paths, policy):
        gates.add("protected_path_edits")
    return CommandAnalysis(
        segments=segments,
        paths=normalized_paths,
        gates=gates,
        write_action=write_action,
        read_action=read_action,
        live_service=live_service,
        risky_unknown=risky_unknown,
        parse_error=parse_error,
    )


def split_command_segments(command: str) -> tuple[list[CommandSegment], str]:
    """Split shell command segments on common operators while respecting quotes."""
    if re.search(r"(^|\s)(<<|<<<)", command):
        return [CommandSegment(words=command.split())], "heredoc or here-string syntax"
    if "$(" in command or "`" in command:
        try:
            words = shlex.split(command)
        except ValueError as error:
            words = command.split()
            return [CommandSegment(words=words)], str(error)
        return [CommandSegment(words=words)], "command substitution"

    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError as error:
        return [CommandSegment(words=command.split())], str(error)

    segments: list[CommandSegment] = []
    current: list[str] = []
    separators = {";", "&&", "||", "|"}
    redirect_tokens = {">", ">>", "<", "2>", "2>>", "&>"}
    parse_error = ""
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in separators:
            if current:
                segments.append(CommandSegment(words=current, separator=token))
                current = []
            index += 1
            continue
        if token in redirect_tokens:
            parse_error = parse_error or "redirection"
            current.append(token)
            if index + 1 < len(tokens):
                current.append(tokens[index + 1])
                index += 2
                continue
        current.append(token)
        index += 1
    if current:
        segments.append(CommandSegment(words=current))
    return segments, parse_error


def segment_has_complex_shell(command: str, words: list[str]) -> bool:
    """Return whether parsed words include shell syntax this hook treats as risky."""
    if "$(" in command or "`" in command:
        return True
    return any(word in {">", ">>", "<", "2>", "2>>", "&>"} for word in words)


def python_inline_code_writes(words: list[str]) -> bool:
    """Return whether a python -c payload appears to write files."""
    try:
        code = words[words.index("-c") + 1]
    except (ValueError, IndexError):
        return True
    lowered = code.lower()
    return any(
        marker in lowered
        for marker in ("open(", ".write(", "pathlib", "write_text(", "write_bytes(")
    )


def command_segment_may_write(words: list[str]) -> bool:
    """Return whether an otherwise unknown segment contains obvious write markers."""
    lowered = " ".join(words).lower()
    return any(marker in lowered for marker in (" write", ".write(", "open("))


def git_snapshot(cwd: Path) -> dict[str, Any]:
    """Return a compact git branch, commit, and status snapshot."""
    snapshot: dict[str, Any] = {}
    commands = {
        "branch": ["git", "branch", "--show-current"],
        "commit": ["git", "rev-parse", "HEAD"],
        "status": ["git", "status", "--short"],
    }
    for key, command in commands.items():
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            snapshot[key] = ""
            continue
        snapshot[key] = result.stdout.strip()
    return snapshot


def append_audit(
    cwd: Path,
    policy: dict[str, Any],
    event_name: str,
    event: dict[str, Any],
    decision: Decision,
) -> None:
    """Append a sanitized JSONL audit event."""
    path = resolve_repo_path(cwd, policy["audit_log"])
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": now_iso(),
        "event": event_name,
        "session_id": event.get("session_id"),
        "tool_name": event.get("tool_name"),
        "allowed": decision.allowed,
        "reason": decision.reason,
        "input": sanitize(audit_input(event_name, event)),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def sanitize(value: Any) -> Any:
    """Redact secrets and truncate large audit payloads."""
    if isinstance(value, dict):
        sanitized = {}
        for key, child in list(value.items())[:MAX_AUDIT_LIST_ITEMS]:
            if SECRET_KEY_PATTERN.search(str(key)):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize(child)
        return sanitized
    if isinstance(value, list):
        return [sanitize(child) for child in value[:MAX_AUDIT_LIST_ITEMS]]
    if isinstance(value, str):
        redacted = SECRET_VALUE_PATTERN.sub("[REDACTED]", value)
        if len(redacted) > MAX_AUDIT_VALUE_CHARS:
            return redacted[:MAX_AUDIT_VALUE_CHARS] + "...[truncated]"
        return redacted
    return value


def audit_input(event_name: str, event: dict[str, Any]) -> Any:
    """Return the relevant event input payload for sanitized audit storage."""
    if event_name == "UserPromptSubmit":
        prompt = extract_prompt(event)
        if prompt:
            return {"prompt": prompt}
    return event.get("tool_input")


def allow_output(event_name: str) -> dict[str, Any]:
    """Return a Codex hook success output payload."""
    if event_name in {"PreToolUse", "PostToolUse", "UserPromptSubmit"}:
        return {"continue": True}
    return {"continue": True, "suppressOutput": True}


def block_output(
    event_name: str, reason: str, detail: str | None = None
) -> dict[str, Any]:
    """Return a Codex hook block output payload."""
    message = reason if detail is None else f"{reason}: {detail}"
    if event_name == "SessionStart":
        return {"continue": False, "stopReason": message}
    return {"continue": True, "decision": "block", "reason": message}


def print_json(payload: dict[str, Any]) -> None:
    """Write a JSON hook response to stdout."""
    print(json.dumps(payload, sort_keys=True))


def split_command(command: str) -> list[str]:
    """Split a shell command safely enough for policy heuristics."""
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def looks_like_path(value: str) -> bool:
    """Return whether a shell token looks like a repository path."""
    return "/" in value or value.startswith((".", "~")) or "." in Path(value).name


def normalize_paths(paths: list[str]) -> list[str]:
    """Normalize candidate paths for glob matching."""
    normalized = []
    for path in paths:
        clean = path.strip().strip("'\"")
        if not clean or clean.startswith("-"):
            continue
        normalized.append(clean.removeprefix("./"))
    return normalized


def resolve_repo_path(cwd: Path, path_text: str) -> Path:
    """Resolve an absolute or repo-relative path."""
    path = Path(path_text)
    if path.is_absolute():
        return path
    return cwd / path


def now_iso() -> str:
    """Return current UTC timestamp in stable ISO format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
