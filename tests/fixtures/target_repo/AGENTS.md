# Target Repo Agent Rules

Use the safe project improvement system as a development/support skill for this
fixture repository.

Follow this loop before and during changes:

```text
inspect -> characterize -> verify setup -> audit -> backlog -> one patch -> verify
```

- Inspect the repository before editing.
- Use `make verify` as the normal local verification command.
- Make one focused patch at a time.
- Do not push, install hooks, modify CI, or call live services without explicit
  approval.
