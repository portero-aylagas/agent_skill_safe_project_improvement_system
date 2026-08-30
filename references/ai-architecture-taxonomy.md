# AI Architecture Taxonomy

Use this reference to classify AI-integrated software before choosing AI System
Audits or AI testing/evaluation work. The goal is routing, not a new audit
family.

## Core Distinction

Use three testing surfaces when deciding where a concern belongs:

- General software testing checks ordinary deterministic application behavior
  that is not AI-specific.
- AI integration testing checks that model/API/tool/RAG/workflow wiring behaves
  correctly with fakes, mocks, stubs, and fixtures.
- AI behavior evaluation checks whether nondeterministic model behavior is good
  enough with representative cases, rubrics, saved outputs, human review, or
  optional evaluation platforms.

Many findings have more than one surface. For example, a RAG pipeline's loading,
chunking, retrieval, and context assembly are integration concerns; expected
source IDs, grounding checks, unsupported-claim checks, and representative
examples are testing/evaluation concerns. Ordinary file parsing or API response
validation remains general software testing even when the app also uses AI.

## Classification Questions

Start with the execution controller:

- Application code controls the next step: deterministic workflow.
- The model controls the next step: agent.
- Code and model share control: hybrid workflow.

Then classify the system by:

- model calls: one, fixed multiple, or dynamic
- control flow: linear, branching, cyclic, or model-directed
- external knowledge: none, fixed context, retrieval, or tools
- state: stateless, conversational, persistent, or shared
- side effects: read-only, write operations, or irreversible actions
- human control: none, review, approval, or intervention

Prefer the least autonomous architecture that solves the problem:

```text
Known sequence -> deterministic pipeline
Known branches -> workflow or graph
Unknown tool choice -> agent
High-risk action -> human approval
```

## Architecture Ladder

### Single LLM Call

One model invocation inside otherwise deterministic software.

- Controller: application code.
- Integration focus: prompt/context construction, model settings, token limits,
  response parsing, validation, and fallback behavior.
- Testing/evaluation focus: input validation, rendered prompt checks, schema
  parsing, empty/malformed response cases, semantic quality on representative
  examples, and repeatability where it matters.
- Main risks: invalid output format, prompt ambiguity, unsupported content,
  latency/rate-limit failures, and silent model behavior changes.

### Multi-Call Pipeline

Several model calls run in a fixed, code-controlled sequence.

- Controller: application code.
- Integration focus: explicit intermediate artifacts, schema contracts between
  stages, provenance, retry boundaries, and per-stage usage visibility.
- Testing/evaluation focus: each call independently, every interface between
  calls, complete-pipeline behavior, and partial-completion or retry cases.
- Main risks: error propagation, accumulated hallucinations, lost context,
  misinterpreted intermediate output, higher latency/cost, and duplicate work
  during retries.

### Branching AI Workflow

An input is routed through one of several predetermined paths.

- Controller: application code, rules, classifier output, or structured model
  routing.
- Integration focus: route schema, fallback path, branch convergence, state
  consistency, and unsupported-route handling.
- Testing/evaluation focus: every branch, positive and negative routing cases,
  boundary and ambiguous cases, invalid route outputs, and fallback frequency.
- Main risks: wrong branch, missing fallback, unreachable branch, conflicting
  criteria, invented routes, and retry loops.

### Tool-Using Deterministic Workflow

Application code decides when and how tools run, even when a model extracts or
summarizes information around the tool call.

- Controller: application code.
- Integration focus: tool name, purpose, input and output schema, validation,
  error types, side effects, idempotency, and authorization.
- Testing/evaluation focus: valid and invalid tool inputs, empty results,
  timeouts, authentication failures, malformed responses, idempotency, and
  whether tool outputs reach the next stage correctly.
- Main risks: unsafe arguments, duplicated side effects, confusing empty-result
  versus failure behavior, and treating the model as an authorization boundary.

### RAG Systems

The system retrieves external information and supplies selected context to a
model for grounded generation.

- Controller: usually application code.
- Integration focus: source loading, cleaning, chunking, metadata, indexing,
  query processing, retrieval, filtering/reranking, context assembly, answer
  generation, and citation handling.
- Testing/evaluation focus: retrieval recall/precision/ranking, expected source
  IDs, no-match behavior, freshness, metadata filters, groundedness, citation
  correctness, conflicting evidence, and unsupported claims.
- Main risks: bad chunking, stale or missing documents, irrelevant retrieval,
  lost metadata, context overload, unsupported synthesis, and citation mismatch.

### Conversation And Memory

The system preserves useful information across turns or sessions.

- Controller: application code and prompts, with model-dependent interpretation.
- Integration focus: memory type, state storage, summarization, correction
  handling, deletion, persistence, restart behavior, and user isolation.
- Testing/evaluation focus: retention, contradictions, stale facts, forgetting,
  cross-user isolation, context growth, summary accuracy, restart, and
  multi-turn prompt injection.
- Main risks: false memory, lost constraints, old data overriding new data,
  cross-user leakage, compressed summaries losing important facts, and
  persistent malicious instructions.

### Graph-Based Workflows

Stateful execution is represented as nodes and edges.

- Controller: graph definition with deterministic, model, retrieval, tool, or
  agent nodes.
- Integration focus: state schema, nodes, edges, conditional routing, entry
  point, termination, persistence, interruptions, and resume behavior.
- Testing/evaluation focus: node tests, edge and boundary-state routing tests,
  state updates/merges, persistence, resume, critical paths, failure paths,
  human-interruption paths, maximum-step behavior, and loop termination.
- Main risks: incorrect edge selection, corrupted state, duplicate execution
  after resume, infinite cycles, unreachable termination, and partial
  persistence.

### AI Agents

The model participates in deciding the execution path and may choose tools or
when to stop.

- Controller: model-directed, usually bounded by application runtime.
- Integration focus: tool inventory, tool schemas, runtime limits, state,
  final-answer extraction, approval gates, and traceability.
- Testing/evaluation focus: selected tool, tool arguments, call ordering,
  repeated calls, interpretation of tool results, stopping behavior, final
  synthesis, traced real-model cases, and trajectory datasets.
- Main risks: wrong or unnecessary tools, wrong arguments, missing tool calls,
  repeated loops, ignored tool output, fabricated results, premature
  termination, unsafe side effects, and excessive cost.

### Agentic RAG

The model decides whether, when, where, and how to retrieve information.

- Controller: model-directed retrieval inside an agent or hybrid workflow.
- Integration focus: retrieval tools, source permissions, query formulation,
  search limits, evidence sufficiency checks, citation behavior, and fallback
  when evidence is insufficient.
- Testing/evaluation focus: retrieval used when needed, retrieval avoided when
  unnecessary, correct source and query, bounded searches, useful results,
  evidence interpretation, faithful final answers, citations, and uncertainty.
- Main risks: no retrieval when required, unnecessary retrieval, wrong source,
  poor query generation, repeated searches, ignored evidence, and unsupported
  answers.

### Multi-Agent Systems

Multiple agents coordinate through supervision, routing, handoffs, parallel
work, review, or critique.

- Controller: model-directed or hybrid, often with orchestration code.
- Integration focus: agent roles, handoff contracts, shared state, delegation,
  aggregation, recursion limits, and failure containment.
- Testing/evaluation focus: each agent independently, handoff contracts, shared
  state consistency, coordination paths, final aggregation, and containment of
  failed or contradictory agents.
- Main risks: poor task decomposition, wrong delegation, duplicated work,
  contradictory outputs, communication loss, recursive delegation, deadlocks,
  cost growth, and weak aggregation.

### Human-In-The-Loop Systems

Human review, approval, editing, rejection, or intervention is required at
selected control points.

- Controller: shared between system and human reviewer.
- Integration focus: approval checkpoints, reviewer permissions, edited values,
  proposal freshness, interruption/resume behavior, audit history, and timeout
  handling.
- Testing/evaluation focus: approval enforcement, rejection blocking execution,
  edits being used, duplicate approval prevention, permission checks, audit
  completeness, timeout/abandonment behavior, and recovery after interruption.
- Main risks: action before approval, wrong reviewer, stale proposal approval,
  duplicated action on resume, lost approval state, and ignored human edits.

## Framework Routing

Framework names do not determine the architecture. Classify the execution model
first.

- LangChain can implement single calls, multi-call pipelines, RAG, tools, or
  agents. Test the architecture built with LangChain, not the library name.
- LangGraph usually deserves workflow and graph checks: state, nodes, edges,
  conditional routing, persistence, resume, interruptions, loop limits, and
  human approval points.
- LangSmith is optional observability/evaluation tooling. A trace explains one
  run; evaluation measures behavior across examples; monitoring detects
  production changes over time.
