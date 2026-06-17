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
SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|token|secret|password|credential|authorization)", re.IGNORECASE
)
SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|"
    r"xox[baprs]-[A-Za-z0-9-]{12,})"
)
MAX_AUDIT_VALUE_CHARS = 600
MAX_AUDIT_LIST_ITEMS = 20


@dataclass(frozen=True)
class Decision:
    """Decision returned by policy evaluation."""

    allowed: bool
    reason: str = ""


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
            "started_at": now_iso(),
        },
    )
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
        return evaluate_pre_tool(policy, session, event)
    if event_name == "PostToolUse":
        record_post_tool(policy, session, event)
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
    policy: dict[str, Any], session: dict[str, Any], event: dict[str, Any]
) -> Decision:
    """Evaluate a `PreToolUse` event before Codex runs a tool."""
    tool_name = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input") or {}
    command = extract_command(tool_input)
    changed_paths = extract_candidate_paths(tool_name, tool_input, command)
    write_action = is_write_action(tool_name, tool_input, command)
    gates = policy["allowed_approval_gates"]

    if policy["mode"] == "review" and write_action:
        return Decision(False, "Review Mode blocks file and workspace writes.")
    if write_action and not inspection_gate_satisfied(policy, session):
        return Decision(False, "Writes are blocked until required inspection evidence exists.")
    if command:
        blocked_command = command_policy_decision(command, gates)
        if not blocked_command.allowed:
            return blocked_command
        if is_live_service_command(command, policy) and not gates["live_service_commands"]:
            return Decision(False, "Live-service commands require explicit policy approval.")
    if touches_ci(changed_paths) and not gates["ci_changes"]:
        return Decision(False, "CI file changes require explicit policy approval.")
    if touches_hook_installation(changed_paths, command) and not gates["hook_installation"]:
        return Decision(False, "Hook installation or hook config changes require approval.")
    if touches_protected_path(changed_paths, policy) and not gates["protected_path_edits"]:
        return Decision(False, "Protected path edits require explicit policy approval.")
    return Decision(True)


def command_policy_decision(command: str, gates: dict[str, bool]) -> Decision:
    """Return a decision for shell commands with explicit approval gates."""
    words = split_command(command)
    if words[:2] == ["git", "commit"] and not gates["commits"]:
        return Decision(False, "Git commits require explicit policy approval.")
    if words[:2] == ["git", "push"] and not gates["pushes"]:
        return Decision(False, "Git pushes require explicit policy approval.")
    branch_commands = {
        ("git", "checkout"),
        ("git", "switch"),
        ("git", "branch"),
        ("git", "rebase"),
        ("git", "merge"),
        ("git", "reset"),
    }
    if tuple(words[:2]) in branch_commands and not gates["branch_changes"]:
        return Decision(False, "Git branch or history changes require explicit approval.")
    return Decision(True)


def record_post_tool(
    policy: dict[str, Any], session: dict[str, Any], event: dict[str, Any]
) -> None:
    """Record evidence from a completed tool call."""
    tool_name = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input") or {}
    tool_response = event.get("tool_response") or {}
    command = extract_command(tool_input)

    if is_read_action(tool_name, tool_input, command):
        session["inspection_events"] = int(session.get("inspection_events", 0)) + 1
        update_inspection_anchors(policy, session, tool_input, command)
    if is_write_action(tool_name, tool_input, command):
        session["write_count"] = int(session.get("write_count", 0)) + 1
        session["last_write_index"] = session.get("event_index", 0)
        session["verification_after_write"] = False
    if command and command_matches_verification(command, policy["verification_command"]):
        if int(session.get("write_count", 0)) > 0:
            session["verification_after_write"] = command_succeeded(tool_response)
    if not command_succeeded(tool_response):
        session.setdefault("failures", []).append(
            {"event_index": session.get("event_index", 0), "tool_name": tool_name}
        )


def evaluate_stop(cwd: Path, policy: dict[str, Any], session: dict[str, Any]) -> Decision:
    """Evaluate whether the session can end cleanly."""
    session["final_git"] = git_snapshot(cwd)
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


def extract_command(tool_input: Any) -> str:
    """Extract a shell command string from a Codex tool input."""
    if isinstance(tool_input, dict):
        command = tool_input.get("cmd") or tool_input.get("command")
        if isinstance(command, str):
            return command.strip()
    return ""


def extract_candidate_paths(tool_name: str, tool_input: Any, command: str) -> list[str]:
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
        paths.extend(token for token in split_command(command) if looks_like_path(token))
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


def is_write_action(tool_name: str, tool_input: Any, command: str) -> bool:
    """Return whether a tool call appears to mutate files, git state, or config."""
    lowered_tool = tool_name.lower()
    if "apply_patch" in lowered_tool or "update_file" in lowered_tool:
        return True
    if not command:
        return False
    lowered = command.lower()
    write_markers = [
        ">",
        ">>",
        " tee ",
        "sed -i",
        "python -c",
        "python3 -c",
        "mkdir",
        "touch",
        "rm ",
        "mv ",
        "cp ",
        "git commit",
        "git push",
        "git checkout",
        "git switch",
        "git branch",
        "git reset",
        "git merge",
        "git rebase",
        "pre-commit install",
    ]
    return any(marker in f" {lowered} " for marker in write_markers)


def is_read_action(tool_name: str, tool_input: Any, command: str) -> bool:
    """Return whether a tool call appears to inspect the repository."""
    lowered_tool = tool_name.lower()
    if any(name in lowered_tool for name in ("open", "fetch", "search", "read")):
        return True
    if not command:
        return False
    words = split_command(command)
    return bool(words and words[0] in {"ls", "sed", "rg", "find", "cat", "git", "pwd"})


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


def touches_hook_installation(paths: list[str], command: str) -> bool:
    """Return whether paths or command indicate hook installation/config changes."""
    hook_paths = (".git/hooks/", ".pre-commit-config.yaml", "pre-commit-config.yaml")
    if any(path.startswith(hook_paths) for path in paths):
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
        "input": sanitize(event.get("tool_input")),
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
