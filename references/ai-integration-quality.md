# AI Integration Quality

Use this reference for projects that call models, tool APIs, embedding services,
RAG pipelines, or agent frameworks.

Use the three testing surfaces to keep implementation guidance separate from
verification guidance:

- general software testing for non-AI deterministic code
- AI integration testing for AI wiring with fakes, mocks, stubs, and fixtures
- AI behavior evaluation for nondeterministic model quality with representative
  cases, rubrics, saved outputs, human review, or optional evaluation platforms

This file focuses on integration implementation choices. Use
`references/testing-strategy.md` for the broader testing/evaluation strategy and
`references/ai-architecture-taxonomy.md` to classify the AI architecture before
selecting detailed audit areas.

## Provider Boundaries

- Keep external provider calls behind small wrappers.
- Pass clients into business logic rather than constructing them everywhere.
- Centralize model names, timeouts, retry policy, token limits, and temperature.
- Keep provider response parsing close to the provider boundary.
- Return plain project data structures from wrappers.

## Prompts

- Give important prompts stable names.
- Keep prompt inputs explicit.
- Document expected output format.
- Validate structured outputs.
- Characterize current prompt behavior before prompt changes.
- Avoid mixing prompt edits with unrelated refactors.

## Configuration

- Read credentials from environment variables or a secrets manager.
- Provide `.env.example` without real secrets.
- Make local tests pass with fake credentials or no credentials.
- Fail fast with clear messages when live mode needs missing configuration.

## RAG

- Keep loading, chunking, embedding, retrieval, and generation separately testable.
- Use a tiny fixture corpus for retrieval characterization.
- Test empty corpus and no-match behavior.
- Keep chunking parameters visible and documented.
- Avoid changing retrieval behavior and answer-generation prompts in one patch.

## Evaluation

AI testing and evaluation has three testing surfaces, with two execution modes:

- General software testing covers non-AI deterministic application behavior.
- AI integration testing covers AI wiring with fake clients, mocks, fixtures,
  schema checks, property checks, and workflow assertions.
- AI behavior evaluation covers model-dependent quality with representative
  cases, rubrics, saved outputs, human review, or optional external platforms.

Normal verification is deterministic and local: it uses the first two surfaces
and must not require live model calls, live API keys, paid services, or
uncontrolled network access. Live/model evaluation is explicit opt-in; it may
use real provider calls and involve cost, latency, nondeterminism, API keys, and
external services.

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

- fake clients for provider failures, retries, malformed responses, and workflow
  control in normal tests
- fixtures for representative inputs, edge cases, expected fields, required
  sections, forbidden claims, and source IDs
- schema and property checks for generated outputs
- retrieval fixtures for RAG retrieval and grounding behavior
- state or trace assertions for agent and workflow behavior
- saved outputs, manual review notes, explicit rubrics, or scoring results when
  claiming model quality was evaluated

Avoid:

- exact-match snapshots of nondeterministic free text unless output is
  deterministic or heavily structured
- vague LLM-as-judge checks without criteria
- live evals that run as part of normal verification by default
- claims that real model quality was verified without a real-model evaluation,
  approved saved output, human-reviewed fixture, or explicit scoring/rubric
  result

Use live evaluation only when explicitly authorized and when cost, latency,
credentials, and external-service behavior are understood.

### LangSmith And External Evaluation Platforms

LangSmith, OpenAI Evals, or similar platforms may be useful when the project
needs persistent datasets, experiment comparison across prompt/model/workflow
versions, trace inspection, LLM-as-judge scoring with explicit criteria, human
feedback, token/cost/latency visibility, or online monitoring.

These tools are optional. They must not be required for normal verification
unless the user explicitly approves external services. Normal verification
should remain local, deterministic, and runnable without live API keys.

Do not use LangSmith just because the project uses AI. Use it when there are
representative examples, clear criteria, repeated model-dependent behavior, and
a need to compare results over time.

Do not send sensitive user data, secrets, private documents, or production
traces to external evaluation platforms unless the project explicitly allows it.
Redact or minimize sensitive data where possible.

## Logging

- Log enough to debug provider failures.
- Do not log secrets, full credentials, or sensitive user data.
- Include request IDs or workflow IDs when available.
