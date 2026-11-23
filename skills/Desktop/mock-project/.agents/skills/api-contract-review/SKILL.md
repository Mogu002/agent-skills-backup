---
name: api-contract-review
description: Review additions or changes to mock-project HTTP endpoints for response consistency, compatibility, validation, and test coverage.
---

# API contract review

Review the affected endpoint and its callers before changing the public contract.

## Requirements

- Preserve the `{ data, error }` response envelope.
- Use stable lowercase snake-case error codes.
- Validate external input at the transport boundary.
- Treat removal or renaming of response fields as a compatibility change.
- Cover the success path and meaningful failure paths with tests.

Read [references/api-conventions.md](references/api-conventions.md) for the project response and status-code conventions.

