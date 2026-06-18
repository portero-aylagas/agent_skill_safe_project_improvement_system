# Patch Backlog

## Requirements Ledger Snapshot

| Requirement | Source | Must/Should | Planned Evidence Or Verification | Status Or Deferral |
| --- | --- | --- | --- | --- |
| Prove a target repo can adopt the workflow | Fixture purpose | Must | `make verify` | Satisfied |

Engineering Audits: checked verification setup and test coverage for this
fixture.

## Verification Setup

No material findings.

Evidence:

- `Makefile` and `verify.sh` both run compile, Ruff, and unittest checks.

Verification:

- `make verify`

## Skipped Engineering Areas

- Runtime architecture: fixture is intentionally minimal.

AI System Audits: no AI-system areas selected because this target repo has no
AI/API workflow.

## Skipped AI System Areas

- AI Software Architecture: no AI system is present.
- Prompt And Context Quality: no prompts are present.

## Backlog Items

### P001

- Priority: 1
- Audit Family: Engineering Audits
- Audit Area: Verification Setup
- Severity: Info
- Risk: Low
- Finding: The fixture needs a small behavior surface with characterization.
- Proposed Patch: Add calculator behavior and characterization tests.
- Characterization: `tests/test_calculator.py`
- Verification: `make verify`
- Status: Done
