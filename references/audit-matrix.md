# Audit Matrix

Use this matrix to choose relevant audits. Do not run every audit blindly. Deep
audit references are optional, except where the protocol requires one for the
review type. Load both engineering and AI System deep references only when the
repository clearly combines software architecture risks with
AI-system-specific risks.

Use these user-facing audit families in reports and backlog items:

- `Engineering Audits`
- `AI System Audits`

This matrix is the routing layer for choosing audit areas. After choosing an
area, use the `SKILL.md` Audit Drilldown guidance to enter the relevant deep
reference and inspect target-repo evidence before producing findings or patches.

For AI-integrated repositories, classify the architecture before choosing AI
audit areas. Use `references/ai-architecture-taxonomy.md` to identify who
controls execution, where nondeterminism enters, what state or side effects
exist, and which architecture-specific failure modes matter.

Architecture classification routes the audit; it is not a third audit family.

AI app quality combines three testing surfaces: general software testing for
non-AI deterministic behavior, deterministic AI integration testing for AI
wiring with fakes and fixtures, and nondeterministic AI behavior evaluation with
representative cases, rubrics, saved outputs, human review, or optional
evaluation platforms.

## Python Scripts and Packages

- Entry points: scripts, modules, CLI commands, notebooks converted to scripts.
- Imports: missing dependencies, circular imports, import-time side effects.
- Reproducibility and dependencies: dependency files, Python version, pinned or
  bounded requirements, lockfile expectations, install docs, and future
  breakage risk from floating libraries.
- CI maturity: local verification mirrored in CI without live secrets, with
  stronger checks added only when proportional.
- Configuration: environment variables, defaults, `.env.example`.
- Errors: clear exceptions, no swallowed failures, useful messages.
- Data handling: schemas, file paths, encoding, input validation.
- Artifact safety: generated or uploaded files cannot silently overwrite
  unrelated files, and automatic names are collision-resistant when needed.
- User-controlled file/path safety: paths and uploads are validated before use
  and do not expose arbitrary local files.
- Verification: compile/import checks, pytest, smoke tests.
- Software delivery testing: risk-based Testing Portfolio, characterization
  before risky refactors, patch tests for intentional behavior changes,
  regression tests for known bugs, smoke tests for critical workflows,
  integration tests for important module wiring, and avoidance of brittle
  low-value tests.
- Documentation: public module/class/function docstrings, comments that reduce
  cognitive load, clear run command, representative input, expected output,
  limitations, and fallback behavior when needed for review or handoff.
- Process evidence: setup, run reports, commit/PR evidence, known limitations,
  and rejection of fake issue references or placeholder metadata.

## AI Integration Projects

- Architecture classification: identify whether the project is a single LLM
  call, multi-call pipeline, branching workflow, deterministic tool workflow,
  RAG system, conversation/memory system, graph workflow, agent, agentic RAG,
  multi-agent system, human-in-the-loop system, or hybrid.
- AI Software Architecture: provider adapters, prompt wiring, model-call
  boundaries, deterministic logic, and fake-client seams are not scattered.
- Provider boundary: one place for model/API calls.
- Credentials: no required live keys for tests, no secrets committed.
- Prompt quality: named prompts, versionable text, clear inputs/outputs.
- Prompt technique: zero-shot, few-shot, or structured output chosen deliberately.
- Determinism: configurable temperature, stable fake-client tests.
- Failure modes: rate limits, timeouts, empty responses, malformed JSON.
- AI evaluation and testing: deterministic fake-client tests, representative
  fixtures, structured output validation, expected output properties,
  malformed/empty response cases, prompt-injection cases where relevant,
  trace/state checks for workflows, and live/model evaluation kept separate from
  normal verification.
- General software testing: non-AI logic, APIs, UI flows, data handling,
  persistence, configuration, and delivery checks stay under `Engineering
  Audits` even when the project contains AI behavior.
- Cost and safety: token limits, retries, step caps, opt-in high-cost modes,
  visible limits, and logging without sensitive data.

Route architecture-specific detail into existing areas:

- Single calls and multi-call pipelines: `Prompt Quality`, `Structured Output`,
  `LLM/API Integration`, and `AI Evaluation And Testing`.
- Branching, graph, and human-in-the-loop systems: `Workflow Automation`,
  `Structured Output`, `AI Evaluation And Testing`, and `Cost And Usage`.
- Deterministic tool workflows, agents, agentic RAG, and multi-agent systems:
  `Agents And Tools`, `Workflow Automation`, `RAG And Retrieval` where
  retrieval is involved, and `AI Evaluation And Testing`.
- RAG systems: `RAG And Retrieval`, `Structured Output`, `AI Evaluation And
  Testing`, and `Cost And Usage`.

## RAG Projects

- Corpus loading: deterministic file discovery and encodings.
- Chunking: documented size/overlap strategy.
- Embeddings: provider/config separated from retrieval logic.
- Retrieval: top-k, filtering, ranking, empty-result behavior.
- Evaluation: small fixture corpus with expected retrievals.
- Persistence: vector store paths, rebuild commands, cache invalidation.

## API Services

- Request validation and response schemas.
- Error status codes and error bodies.
- Dependency injection for clients and databases.
- Startup behavior without live optional services.
- Contract tests for public endpoints.
- Health checks that do not leak secrets.

## UI Projects

- Main user workflows and state transitions.
- UI/backend separation: callbacks validate inputs and call clean backend
  functions.
- Form validation and error display.
- Accessibility basics: labels, keyboard paths, contrast.
- Responsive layout for important views.
- API failure and loading states.
- Build or smoke verification.

## Workflow and Automation Projects

- Trigger conditions and idempotency.
- Error handling, retries, failure branches, and dead-letter paths.
- Explicit state transitions and human approval points for high-risk actions.
- Active run, session, concurrent workflow, stop, restart, and recovery behavior.
- Credential isolation.
- Dry-run or fake-service mode.
- Observability: logs, run IDs, summaries, and reports.
- Rollback or manual recovery notes.

## Backlog Prioritization

Rank findings by:

- user impact
- risk of regression
- ease of verification
- isolation of patch
- dependency on approvals or live services
