# Engineering Audits

Use this reference when `audit-matrix.md` shows that a deeper engineering review
is useful. Do not run every audit blindly.

Use each section heading below as a known `Engineering Audits` area when writing
block-based audit findings. Checked areas with findings must use full field
blocks; checked areas with no material findings must use the compact
`No material findings.` form. Areas that are not relevant or not checked belong
only under `Skipped Engineering Areas` with a reason.

## General Software Architecture

Check:

- each file has a clear purpose
- orchestration is separated from business logic
- UI, file I/O, external service calls, config, and utilities have clear
  boundaries
- imports do not create avoidable coupling or circular dependencies
- the current structure can grow without hiding important behavior
- AI-specific code connects to the application through clear module boundaries

This audit checks general software structure. Provider adapters, prompt
storage/wiring, and model-dependent architecture belong under
`AI Software Architecture`. Prompt content quality, prompting technique, and
prompt variables belong under focused `AI System Audits`.

Return:

- current architecture summary
- structural problems by file
- minimal structure changes worth doing now
- changes that would be over-engineering

## Function Responsibility

Check:

- each function has one clear responsibility
- names match behavior
- inputs, outputs, and side effects are understandable
- public functions and classes have concise Google-style docstrings unless they
  are clearly private or internal
- comments explain workflow intent, assumptions, side effects, safety
  constraints, or non-obvious guards where code alone is not enough
- UI, file I/O, API calls, and business logic are not unnecessarily mixed
- functions are not too large, too tiny to be useful, or coupled to global state

Return:

- file/function
- current responsibility
- problem
- recommended action
- priority

## Error Handling

Check:

- broad, swallowed, or silent exceptions
- unclear error messages
- API, file, JSON/parsing, user-input, and environment-variable failures
- crash behavior versus graceful failure
- whether errors explain where and why the failure happened

Return:

- file/function
- failure scenario
- current behavior
- minimal fix
- test or smoke check to add

## Testability

Check:

- logic coupled to UI frameworks, files, environment variables, or live services
- functions that should be pure or easier to call directly
- where fakes, mocks, fixtures, or dependency injection are needed
- missing edge cases and regression checks

Return:

- testability diagnosis
- functions to refactor before testing
- suggested unit tests
- suggested integration or smoke tests
- smallest useful test plan

## Software Delivery Testing

Check:

- whether the repository has a clear local test or verification command
- whether existing tests protect real user-visible, API-visible, or workflow
  behavior
- whether tests are classified by purpose:
  - characterization tests for existing behavior before risky changes
  - patch tests for intentional new behavior
  - regression tests for known bugs or fragile behavior
  - unit tests for pure deterministic logic
  - integration tests for important wiring between modules
  - smoke tests for critical workflows
  - full verification for repository-wide checks after a patch
- whether tests are missing for core deterministic behavior
- whether risky refactors have characterization coverage before changes
- whether previous bugs have regression tests
- whether mocks, fakes, or fixtures are used only where they reduce fragility
- whether tests avoid live services, live API keys, paid services, and
  uncontrolled network access
- whether tests are too coupled to implementation details
- whether broad E2E tests are justified or unnecessarily brittle
- whether static checks, compile/import checks, linting, and type checks are
  part of verification when useful
- whether test failures are easy to diagnose

Return:

- current verification and test inventory
- test purpose classification
- protected behaviors
- unprotected high-risk behaviors
- recommended Testing Portfolio
- first safe test patch
- tests that would be low-value, brittle, redundant, or over-engineered

## Reproducibility And Dependency Discipline

Check:

- dependency files exist and setup instructions reference them
- Python version is declared in project metadata, docs, runtime files, or local
  instructions
- dependencies are pinned, bounded, locked, or their floating state is justified
- fast-moving libraries are not left completely floating without a reason
- lock files exist where appropriate, or their absence is explained
- CI install path matches the documented local install path
- normal verification can be reproduced by a new user
- requirements files are reviewed for future breakage risk from incompatible
  dependency releases

Return:

- dependency and Python version inventory
- floating or fragile requirements
- install path mismatches between docs, local verification, and CI
- lockfile or pinning recommendation proportional to project maturity
- verification command a new user can reproduce

## CI Maturity

Check:

- baseline CI runs the same normal verification expected locally
- normal CI does not require live secrets, paid services, or interactive setup
- stronger CI includes type checking, coverage, dependency audit, or eval smoke
  tests when appropriate for the repository
- CI expectations are proportional to project maturity
- non-trivial apps are not relying only on fragile or incomplete verification
- CI failure output gives enough evidence for a reviewer to act

Return:

- current CI entry points and commands
- local versus CI verification gaps
- secret or live-service risks in normal CI
- proportional next CI improvement
- checks that would be overkill for the current project

## Data And JSON Validation

Check:

- where JSON, CSV, API responses, uploaded files, or user-provided structured
  data enter the project
- required fields, types, nulls, malformed data, and unexpected fields
- whether invalid data can silently continue through the pipeline
- whether validation logic is mixed into UI, file I/O, or API calls
- whether simple validation functions are enough before adding schemas

Return:

- data entry points
- current validation approach
- failure scenarios
- minimal validation improvements
- test cases to add

## Artifact/File Collision Safety

Check:

- generated files, uploaded files, caches, reports, exports, and other artifacts
  cannot silently overwrite unrelated files
- timestamp-only naming is not used when collisions are plausible
- automatic filenames are collision-resistant when repeated or concurrent runs
  are plausible
- existing-file behavior is explicit: fail, version, prompt, or overwrite only
  with clear intent
- tests cover repeated/generated artifact naming when appropriate

Return:

- artifact creation points
- current naming and overwrite behavior
- collision or concurrency scenarios
- minimal safer naming or existence-check improvement
- repeated-run test or smoke check to add

## User-Controlled File/Path Safety

Check:

- user-provided paths, uploads, generated artifact paths, and config paths are
  validated before use
- unsafe path traversal or arbitrary local file access is prevented where
  relevant
- file existence and type checks happen before sensitive downstream use
- editable path fields cannot expose sensitive local files or generated state
- path handling is centralized enough to review and test

Return:

- user-controlled path entry points
- validation and normalization behavior
- local file exposure or traversal risks
- minimal containment or allowlist improvement
- tests for invalid, missing, unexpected, or traversal-like paths

## Repository Hygiene

Check:

- committed generated files, caches, virtual environments, and large temporary
  files
- `.gitignore` coverage
- dependency files and setup instructions
- duplicate, obsolete, or confusing files
- outputs that should be examples versus local artifacts

Return:

- files/folders that should stay
- files/folders to check before removing
- suggested `.gitignore` additions
- minimal cleanup plan

## Process And Reviewer Evidence

Check:

- clear project goal, setup, run command, and verification command
- required environment variables with examples, not real secrets
- setup, run, and verification instructions can be followed by a new reviewer
- decisions and known limitations are documented where useful
- public module, class, and function docstrings that explain purpose, inputs,
  outputs, side effects, and important assumptions where useful
- inline workflow comments that reduce cognitive load without restating syntax
- project structure and important modules explained where useful
- sample input, expected output, known limitations, and fallback behavior for
  API, file, or input failure when needed for review or demo
- Full Automation Mode creates required run reports
- pull request body and commit structure reflect actual remediation
- fake issue references, placeholder metadata, and inaccurate review evidence
  are rejected

Return:

- missing documentation sections
- confusing or outdated instructions
- minimal README improvements
- reviewer/demo clarity gaps that affect engineering verification
- missing run report, commit, pull request, or verification evidence

## Security And Secrets

Check:

- hardcoded API keys or committed `.env` files
- unvalidated uploads or external documents
- prompt injection risks when documents, URLs, or user text affect model calls
- sensitive data in logs, outputs, reports, or committed artifacts

This audit treats prompt injection as an application security boundary. Prompt
wording and model behavior belong under `AI System Audits`.

Return:

- security issue
- severity
- exact location
- minimal fix
- what is acceptable for a local project versus production
