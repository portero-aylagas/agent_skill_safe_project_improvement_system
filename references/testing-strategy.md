# Testing Strategy

Verification should be normal, local, and repeatable.

## Preferred Verification

Prefer a single command:

```text
make verify
```

Useful default checks:

- compile/import check
- Ruff linting, including configured pydocstyle checks for public docstrings
- focused pytest suite
- smoke script for the main workflow
- additional lint only when already configured or explicitly added as low-risk
  setup

## Test Roles

Use tests for three related but different jobs:

- Characterization tests protect existing behavior before medium/high-risk
  changes.
- Patch tests prove the intended new behavior introduced by the current patch.
- Full verification runs the repository's normal checks after the patch to catch
  regressions outside the focused change.

For refactors, characterization and existing tests should usually keep the same
expected behavior. For intentional behavior changes, update or add tests only
when the new expectation is part of the patch.

## Test Purpose Classification

Every proposed test should be classified by purpose:

- Characterization test: captures current behavior before changing it.
- Patch test: proves intentional new behavior from the current patch.
- Regression test: prevents a known bug from returning.
- Unit test: checks isolated deterministic logic.
- Integration test: checks important wiring between modules.
- Smoke test: checks that a critical workflow starts and completes at a shallow
  level.
- Full verification: runs the repository's normal verification command after a
  patch.

A single pytest test may belong to more than one purpose. For example, a
characterization test can be implemented as an integration test, and a
regression test can also be a unit test.

Characterization tests are a test purpose, not a separate implementation type.
They can be implemented as unit tests, integration tests, smoke tests, golden
input/output fixtures, snapshot-style structured output checks, or temporary
manual checklists.

## Testing Portfolio

Do not blindly enforce the classic test pyramid. Use the cheapest stable test
that gives meaningful confidence.

Prefer:

- static checks for syntax, imports, formatting, linting, and simple correctness
  rules
- unit tests for deterministic pure logic
- integration tests for important module wiring
- smoke tests for critical workflows
- regression tests for bugs or fragile behavior already discovered
- characterization tests before medium/high-risk refactors

Avoid:

- tests that only assert that something is not `None`
- tests that duplicate implementation details
- tests that require live secrets, paid services, or uncontrolled network access
- broad E2E tests when a lower-level test gives equivalent confidence
- large generated test suites that increase maintenance without protecting
  important behavior

## Test Quality Gate

Before adding or approving a test, confirm:

- the test names the behavior it defends and the outcome expected
- the test would fail if the implementation silently no-oped
- the test has one clear reason to fail
- the assertions check externally visible behavior, public contracts, or
  important workflow state instead of implementation details
- setup, action, and assertions are separated clearly enough that hidden setup
  cannot make the assertion tautological
- fixtures are minimal, named for scenarios, and kept close to the test when
  practical
- mocks and fakes simplify unstable dependencies without mirroring the
  implementation so closely that both can be wrong together
- the test is deterministic without sleeps, wall-clock waits, uncontrolled
  network access, live services, retries, or shared mutable state

Cover negative paths and boundaries when they are relevant to the behavior:
empty, one, many, maximum, duplicate, concurrent, malformed, unauthorized, and
every meaningful error branch. If behavior is hard to test cleanly, treat that
as a design or testability issue instead of adding a brittle test.

## Minimal Python Setup

When no verification exists, add the smallest useful setup:

- `Makefile` with `verify`, `test`, and `compile`
- optional `scripts/verify.sh`
- optional `pyproject.toml` pytest and Ruff defaults
- focused tests under `tests/`

Do not install hooks or strict CI without explicit approval.

## Test Dependencies

If verification runs `pytest`, make sure the target repository installs it in
the same place it records other development or test dependencies. Prefer the
existing project convention:

- `pyproject.toml` development/test optional dependencies
- `requirements-dev.txt` or `requirements-test.txt`
- an existing dependency group managed by the project's package tool

For tiny beginner repos with no dependency convention, a CI step that runs
`python -m pip install pytest` is acceptable as a temporary setup patch. Do not
silently rely on undeclared local packages.

## AI/API Tests

Use fake clients or mocks:

- fake chat/completion client
- fake embedding client
- fake HTTP response object
- fixture JSON payloads
- deterministic prompt inputs

Normal tests must not require:

- live API keys
- network access
- paid services
- local vector stores that are not generated by the test

## AI Testing And Evaluation

Normal verification may include deterministic AI-adjacent tests using fakes,
mocks, fixtures, schema checks, and property checks.

For AI-enabled applications, use three testing surfaces:

- General software testing: deterministic tests for ordinary application code,
  data handling, APIs, UI flows, configuration, persistence, and delivery.
- AI integration testing: deterministic tests for model/API/tool/RAG/workflow
  wiring using fakes, mocks, stubs, fixtures, fake model clients, fake tools, or
  fake retrievers.
- AI behavior evaluation: nondeterministic model-quality checks using
  representative cases, evaluation datasets, rubrics, saved outputs, human
  review, LangSmith, OpenAI Evals, or similar explicit opt-in tools.

AI app quality combines all three surfaces:

```text
general software quality
+ deterministic AI integration correctness
+ nondeterministic AI behavior evaluation
```

Do not create a separate top-level `AI Testing` audit family. Route non-AI
behavior to `Engineering Audits`, AI wiring to the focused `AI System Audits`
area that owns the component, and model-quality measurement to `AI Evaluation
And Testing`.

Normal verification must not require:

- live model calls
- live API keys
- paid services
- uncontrolled network access

Live/model evaluations are optional and should run through an explicit separate
command.

Use this rule:

```text
Fake clients test control.
Real models test quality.
Fixtures bridge the two.
```

Use this rule for optional external evaluation platforms:

```text
Local tests prove the AI system is wired correctly.
LangSmith evals help measure and track whether real AI behavior is good enough across examples and versions.
```

Prefer:

- fake-client tests for provider failures and workflow control
- schema checks for structured outputs
- property checks for generated text
- retrieval checks for RAG
- state/trace checks for agents and workflows
- explicit fixtures for representative cases

Avoid:

- exact-match snapshots of nondeterministic free text
- vague LLM-as-judge checks without criteria
- eval suites that require paid model calls by default
- large fixture sets before the workflow is stable

### AI Integration Tests

Use deterministic AI integration tests to prove control flow and wiring without
depending on real model quality.

Prefer:

- fake model clients for provider responses, timeouts, malformed responses, and
  retries
- fake embedding clients, retrievers, vector stores, and tool implementations
- fixture payloads for provider, tool, retrieval, transcript, or parser inputs
- prompt-rendering checks that assert required sections, variables, and
  instruction/data boundaries
- parser and schema tests for missing fields, invalid values, partial outputs,
  invented routes, and unsupported enum values
- workflow assertions for state transitions, branch routing, tool-call traces,
  approval gates, idempotency, and retry limits

These tests show that the application controls the AI capability correctly.
They do not prove that a real model answer is good enough.

### AI Behavior Evaluations

Use AI behavior evaluations when model-dependent quality matters and cannot be
proved with deterministic checks alone.

Prefer:

- small representative datasets with expected properties
- explicit rubrics for relevance, completeness, groundedness, safety, tone, or
  trajectory quality
- saved outputs or human-reviewed baselines for important flows
- repeated-run checks when stability matters
- LangSmith, OpenAI Evals, or similar tools only when the project needs
  persistent datasets, trace inspection, experiment comparison, judge scoring,
  human feedback, or production monitoring

Keep these evaluations separate from normal verification unless the user
explicitly approves live model calls, credentials, latency, cost, and data
retention.

### AI Testing Maturity

Use the lowest maturity level that gives meaningful confidence for the current
project and risk:

1. Define correct behavior.
2. Unit-test ordinary deterministic code.
3. Test tools and provider wrappers independently.
4. Smoke-test the model connection only when live credentials are explicitly
   approved.
5. Test structured output, tool-call arguments, and parsing.
6. Test orchestration with controlled dependencies.
7. Inspect representative traces for multi-step, tool, RAG, or agent behavior.
8. Build a small evaluation dataset.
9. Add deterministic evaluators where possible.
10. Add calibrated semantic evaluators only when deterministic checks are not
    enough.
11. Compare prompt, model, tool, workflow, or retrieval experiments.
12. Add regression gates for important failures.
13. Test nondeterminism and repeated runs when stability matters.
14. Inject likely failures: timeouts, malformed outputs, empty retrieval,
    invalid tool arguments, retries, and interrupted workflows.
15. Test security boundaries, prompt injection, tool-output injection, tenant
    isolation, and approval gates.
16. Test state, memory, persistence, resume, and multi-turn behavior.
17. Monitor production traces, failures, latency, tokens, cost, and drift.

At every AI architecture layer, consider components, interfaces, intermediate
state, complete execution paths, final output, failure behavior, security
boundaries, latency, and cost.

Architecture-specific emphasis:

- Single LLM call: schema, validation, model settings, and semantic quality.
- Multi-call pipeline: intermediate contracts, provenance, and retry boundaries.
- Branching workflow: routing accuracy, fallbacks, invalid routes, and branch
  convergence.
- RAG: retrieval quality, metadata filters, grounding, citations, and no-match
  behavior.
- Conversation and memory: retention, correction, deletion, isolation,
  summarization, and restart behavior.
- Graph workflow: node behavior, edge routing, state updates, persistence,
  resume, and loop limits.
- Agents and agentic RAG: trajectory, selected tools, tool arguments, evidence
  use, stopping behavior, and execution caps.
- Multi-agent systems: handoffs, shared state, coordination, aggregation,
  failure containment, and cost growth.
- Human-in-the-loop systems: approval enforcement, reviewer permissions, edited
  values, audit history, and recovery after interruption.

### Evaluation Datasets

Use datasets to turn remembered expectations and discovered failures into
repeatable cases. Keep early datasets small and representative.

Useful categories:

- happy paths
- boundary and ambiguous cases
- negative cases
- tool-specific cases
- adversarial or prompt-injection cases
- historical failures
- long, stateful, or multi-turn cases

Useful expectations:

- required behavior
- acceptable alternatives
- forbidden behavior
- expected tools, routes, or source IDs
- required evidence
- deterministic checks
- semantic rubric criteria

Record dataset, prompt, model, tool, retrieval, and evaluator versions when
results are compared across changes. Every meaningful AI failure should become a
regression example unless doing so would expose sensitive data or create a
maintenance burden larger than the risk.

### Optional External Evaluation Platforms

LangSmith, OpenAI Evals, or similar platforms may be useful when an
AI-integrated project needs persistent datasets, experiment comparison, trace
inspection for chains/agents/tools, LLM-as-judge scoring, human feedback,
token/cost/latency visibility, or online monitoring.

These tools are optional. They must not be required for normal verification
unless the user explicitly approves external services. Normal verification
should remain local, deterministic, and runnable without live API keys.

Use LangSmith when the project has repeated AI behavior worth comparing,
representative examples or a golden set, clear scoring criteria or rubrics,
multiple prompt/model/workflow versions to compare, traces that need inspection,
cost/latency/token usage worth tracking, or human or LLM-judge review needs.

Do not use LangSmith just because the project uses AI. Use it when there are
representative examples, clear criteria, repeated model-dependent behavior, and
a need to compare results over time.

Do not use LangSmith when the project only needs local correctness tests,
fake-client tests, schema validation, prompt rendering checks, simple regression
tests, or basic workflow smoke tests.

A golden set should usually contain representative inputs plus expected
properties, not necessarily exact full natural-language outputs. Useful
expected properties include required fields, forbidden claims, source IDs,
required sections, expected labels, or rubric criteria. Exact-match full
free-text comparison is usually brittle unless the output is deterministic or
heavily structured.

LLM-as-judge evaluation can be useful for subjective qualities such as
relevance, completeness, groundedness, tone, and pairwise comparison. It should
use explicit criteria or rubrics, be treated as a quality signal rather than
absolute truth, and not replace deterministic checks when deterministic checks
are possible.

Possible command conventions:

```text
make verify
```

For local deterministic verification.

```text
make eval-live
```

For optional live model evaluation.

```text
make eval-langsmith
```

Only if the project explicitly chooses LangSmith tracking.

Do not require these commands to exist in every project. LangSmith or external
evaluation platforms may involve API keys, network access, cost, data retention,
and external service availability. Do not send sensitive user data, secrets,
private documents, or production traces to external evaluation platforms unless
the project explicitly allows it. Redact or minimize sensitive data where
possible.

## Smoke Tests

Use smoke tests when the project has few tests:

- import the main module
- run CLI help
- run one small representative input
- confirm output type and key fields
- confirm graceful handling of a known failure input

Smoke tests are not a replacement for deeper tests, but they are a useful first
verification surface before refactoring.

## Test Naming

Name tests by behavior:

```text
test_summarizer_returns_text_for_valid_article
test_provider_wrapper_handles_timeout
test_retriever_returns_empty_list_for_empty_corpus
```

## Failure Policy

If verification fails:

1. Stop.
2. Identify whether the failure is pre-existing or caused by the patch.
3. Decide whether the failure is a regression, a pre-existing issue, or an
   intentional behavior change that needs a deliberate test update.
4. Report the command and failure summary.
5. Suggest the smallest next diagnostic or fix.
