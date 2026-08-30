# AI System Audits

Use this reference for deeper review of prompts, model integrations, RAG,
agent/tool workflows, speech pipelines, and orchestrated automations. Keep
recommendations proportional to the project.

For AI-integrated projects, classify the architecture first with
`references/ai-architecture-taxonomy.md`. Use that classification to choose
focused AI System Audits. Do not create a separate `AI Testing` family; testing
and evaluation findings belong in the existing audit area that owns the
behavior.

For AI-enabled applications, separate three testing surfaces while auditing:
general software testing for non-AI code, deterministic AI integration testing
for AI wiring with fakes and fixtures, and nondeterministic AI behavior
evaluation with representative cases, rubrics, saved outputs, human review, or
optional evaluation platforms.

`AI Software Architecture` is the cross-cutting structure audit for AI systems.
Use it to decide whether AI-specific parts have clear ownership and boundaries.
Route detailed prompt, provider, retrieval, tool, workflow, speech, cost, and
evaluation findings to the focused areas below.

`Workflow Automation` is one audit area inside AI System Audits. It covers
multi-step AI/tool execution, retries, state transitions, approval points, logs,
run IDs, recovery paths, and cost controls.

Use each section heading below as a known `AI System Audits` area when writing
block-based audit findings. Checked areas with findings must use full field
blocks; checked areas with no material findings must use the compact
`No material findings.` form. Areas that are not relevant or not checked belong
only under `Skipped AI System Areas` with a reason.

## AI Software Architecture

Check:

- provider adapters, prompt storage/wiring, and model-call boundaries have clear
  ownership
- deterministic business logic is separated from model-dependent behavior
- the execution controller is clear: application code, model, or shared
- RAG, agent, tool, and workflow components compose through understandable
  interfaces
- dependency boundaries allow fake clients or fixtures without live services
- AI-specific structure can grow without scattering provider, prompt, or runtime
  concerns across unrelated code
- the chosen architecture is no more autonomous than the problem requires

Do not use this area for prompt wording, prompt variables, schemas/parsing,
provider settings, retries, timeouts, retrieval quality, tool contracts,
workflow recovery, budgets, or evaluation details. Route those findings to the
focused AI System audit areas.

Return:

- AI architecture summary
- architecture classification and controller
- component boundary problems
- model-dependent behavior that should be isolated
- minimal structure changes worth doing now
- focused audit areas that should own deeper follow-up

## Prompt Quality

Check:

- each prompt has a clear task, audience, constraints, and output format
- prompt inputs are explicit and separated from instructions
- zero-shot, one-shot, few-shot, or structured output is appropriate for the task
- prompt text is inspectable and not hidden inside unrelated application logic
- temperature, model choice, and determinism match the task

Return:

- prompt inventory
- current technique
- weaknesses
- minimal improved prompt examples
- what not to change

## Dynamic Prompting

Check:

- variables injected into prompts
- user input boundaries and injection risk
- duplicated prompt construction
- missing inputs and error handling
- whether prompt templates would improve maintainability

Return:

- current dynamic prompting pattern
- variables injected
- risks
- minimal improvements
- example template when useful

## Structured Output

Check:

- free text versus JSON-like text versus validated schema
- downstream dependencies on exact fields
- required and optional fields
- malformed JSON and validation error handling
- whether raw model output and parsed output are stored appropriately
- unsupported enum values, invented routes, partial responses, and contradictory
  responses are handled before downstream use

Return:

- current output format
- where structured output is needed
- schema weaknesses
- minimal validation improvements
- test cases for malformed or missing fields

## LLM/API Integration

Check:

- credentials loaded from environment or secrets manager
- model names, temperature, timeout, retry policy, and token limits
- provider response parsing
- rate limits, timeouts, empty responses, and malformed responses
- whether adding a provider would require broad code changes
- whether existing abstraction is too thin, too broad, or unnecessary

Return:

- integration assessment
- provider boundary problems
- minimal improvements
- optional future improvements
- tests with fake clients

## RAG And Retrieval

Check:

- document loading, cleaning, and deterministic file discovery
- chunk size, overlap, and boundary quality
- metadata, permissions, freshness, and source visibility survive ingestion and
  retrieval
- embeddings, vector store paths, rebuild commands, and cache invalidation
- top-k, filters, ranking, empty corpus, and no-match behavior
- whether retrieved context actually answers representative questions
- whether generation remains faithful to retrieved context, handles conflicting
  evidence, cites correctly, and expresses uncertainty when evidence is weak
- whether deterministic context assembly is enough instead of vector RAG

Return:

- current RAG/context pipeline
- chunking and retrieval risks
- grounding, citation, metadata, and freshness risks
- fixture corpus and test questions
- minimal improvements
- what would be over-engineering

## AI Evaluation And Testing

Check:

- model-dependent behaviors are inventoried before choosing tests
- general software behavior that is not AI-specific is covered by ordinary
  deterministic tests under `Engineering Audits`
- deterministic fake-client tests cover provider failures, parser behavior,
  prompt builders, workflow control, and other AI-adjacent behavior
- fake clients and mocks test the application's control of the AI workflow
  without mirroring implementation internals
- fixture-based evaluations cover representative inputs, expected fields,
  required sections, forbidden claims, source IDs, and edge cases
- optional live/model evaluations are explicit opt-ins and separate from normal
  verification
- structured outputs are validated for required fields, types, malformed
  responses, empty responses, partial responses, and contradictory responses
- prompt-rendering tests assert required contract pieces, variables, and
  instruction/data boundaries, not exact nondeterministic prose
- RAG retrieval and grounding checks use retrieval fixtures, expected source
  IDs, no-match cases, and unsupported-claim checks where relevant
- agent/tool workflows are checked with fake tools, fake model decisions,
  trace assertions, or state transition assertions where relevant
- RAG and agent workflow tests assert source IDs, selected routes, tool calls,
  state transitions, stopping behavior, retry limits, and failure handling where
  those behaviors are part of the contract
- prompt-injection or hostile document inputs are considered where user content
  or retrieved content can influence instructions
- cost and latency risks are visible for multi-call workflows
- architecture-specific evaluation is considered: routing for branches, state
  and paths for graphs, retrieval and grounding for RAG, trajectory and stopping
  for agents, delegation and aggregation for multi-agent systems, and approval
  enforcement for human-in-the-loop systems
- traces are used as evidence for complex execution, while evaluators decide
  whether behavior meets requirements
- important failures are converted into regression examples when safe and
  proportionate
- evaluation results are comparable between versions through fixtures, saved
  outputs, manual review notes, explicit rubrics, or scoring results
- optional external evaluation platforms, such as LangSmith or OpenAI Evals,
  are considered only when the project has representative examples, clear
  criteria, repeated model-dependent behavior, and a need to compare results
  over time
- LangSmith is treated as optional observability/evaluation tooling for
  datasets, experiment comparison, trace inspection, LLM-as-judge scoring,
  human review, cost/latency/token visibility, or online monitoring, not as a
  replacement for local deterministic tests
- claims about real model quality are backed by a real-model evaluation,
  human-reviewed saved output, approved fixture/golden output, or explicit
  scoring/rubric result
- evaluation expectations are proportional to the current project and do not
  require live API keys, network access, paid services, or a heavy platform for
  normal verification

Return:

- AI behavior inventory
- current AI test/eval surface
- architecture-specific testing emphasis
- deterministic tests to add
- fixture-based evaluations to add
- optional live/model evaluations
- whether optional external evaluation tracking is justified
- risks not worth testing yet
- first safe AI testing/evaluation patch
- what would be over-engineering

## Agents And Tools

Check:

- whether an agent is justified instead of a simpler chain or direct call
- tool names, descriptions, input types, and output usefulness
- prompt/tool/runtime separation
- final answer extraction
- debuggability of tool calls and model calls
- tool failures and recovery behavior
- selected tools, tool arguments, call ordering, repeated calls, interpretation
  of tool results, stopping behavior, and final synthesis are observable enough
  to evaluate
- agentic RAG distinguishes retrieval decisions, query quality, evidence
  sufficiency, citation behavior, and unnecessary retrieval
- multi-agent systems define roles, handoff contracts, shared state,
  aggregation, recursion limits, and failure containment

Return:

- agent architecture summary
- tool inventory
- trajectory, handoff, or aggregation risks where relevant
- problems by file/function
- minimal improvements
- whether to keep the agent design

## Workflow Automation

Check:

- trigger conditions, idempotency, retries, and failure branches
- explicit state, node responsibilities, and conditional routing
- branch coverage, invalid route behavior, branch convergence, and fallback
  paths where workflows route across predetermined paths
- graph state schema, node behavior, edge routing, persistence, interruptions,
  resume behavior, maximum-step behavior, and loop termination where relevant
- deterministic business rules separated from model calls
- human approval points for high-risk actions
- reviewer permissions, stale proposals, human edits, duplicate approval, audit
  history, timeout, and abandonment behavior for human-in-the-loop systems
- active run, session, and concurrent workflow behavior
- stop, restart, and recovery behavior
- workflow path tracking, logs, run IDs, and reports
- setup, credentials, and validation prompts or commands

Return:

- workflow summary
- state or node issues
- branch, graph, approval, and recovery issues where relevant
- reliability and traceability risks
- concurrency and recovery risks
- evidence gaps
- minimal improvements

## Speech Pipelines

Check:

- audio loading, recording, conversion, and cleanup
- long-audio chunking and timestamp handling
- prompted versus unprompted transcription where domain vocabulary matters
- generated audio validation before merging
- transcript and audio alignment
- safe output naming

Return:

- speech pipeline summary
- STT/TTS risks
- chunking and timestamp risks
- minimal improvements
- practical evaluation checks

## Cost And Usage

Check:

- whether the app makes enough model calls to justify usage tracking
- direct provider usage versus estimates
- stale hardcoded pricing
- total requests, tokens, cost, and visible budget warnings
- whether usage tracking is mixed into business logic
- max retries, max steps, timeouts, token limits, or equivalent caps for paid or
  looping AI workflows
- high-cost modes require explicit opt-in
- configured limits are visible enough for review and debugging
- invalid config values do not silently fall back to dangerous high limits
- cost and usage tracking are proportional to the project

Return:

- current usage tracking summary
- whether tracking is necessary
- inaccuracies or missing visibility
- missing execution caps or risky defaults
- minimal improvements
- what would be unnecessary for a small project
