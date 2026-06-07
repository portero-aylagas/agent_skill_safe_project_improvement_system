# Characterization

Characterization captures what the project currently does before changing it.

Characterization tests, also known as Golden Master or Snapshot tests, are
automated tests that record the exact, actual behavior of existing software.
Michael Feathers coined the term in *Working Effectively with Legacy Code*.

Their purpose is to freeze legacy behavior before refactoring, not to prove that
the behavior is correct. This matters because safe refactoring needs a safety
net: if an edit changes observable output, side effects, errors, files, logs, or
API responses unexpectedly, characterization tests fail before the change reaches
production.

## Rule

Characterization is mandatory before medium/high-risk changes.

It can be:

- automated tests
- smoke scripts
- golden input/output fixtures
- snapshots of stable structured outputs
- a repeatable manual checklist

Manual characterization is temporary and should become automated when practical.

## When It Is Required

Required before changing:

- validation behavior
- prompts or model parameters
- API wrappers and provider adapters
- configuration loading
- schemas or public interfaces
- RAG retrieval, chunking, embeddings, or ranking
- async/concurrency behavior
- architecture or module boundaries

Usually not required for:

- docs-only edits
- comments
- typo fixes
- formatting of isolated code with existing tests

## How to Characterize

1. Identify 2-5 important user workflows or API calls.
2. Capture representative inputs, including at least one edge case.
3. Record expected outputs, side effects, logs, files, or errors.
4. Prefer fake clients for external systems.
5. Add a verification command that can be run locally.

## AI/API Examples

Use fake clients that return deterministic responses:

```python
class FakeChatClient:
    def complete(self, prompt: str) -> str:
        return "fixed test response"
```

Avoid tests that need real credentials, network access, or paid services.

For AI-integrated behavior, characterization should prefer stable observable
properties over exact free-text snapshots: rendered prompt sections, schema
fields, retrieved source IDs, tool-call traces, state transitions, required
sections, and forbidden placeholders.

## Manual Checklist Template

```text
Behavior:
Input:
Expected output:
Expected side effects:
How to run:
Known limitations:
Date characterized:
```
