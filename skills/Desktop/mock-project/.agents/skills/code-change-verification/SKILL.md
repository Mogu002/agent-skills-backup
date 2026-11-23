---
name: code-change-verification
description: Verify code changes in mock-project before handoff, including focused tests, type checking, and reporting remaining risks.
---

# Code change verification

Use the smallest checks that cover the changed behavior, then run the complete project checks before final handoff when shared runtime behavior changed.

## Workflow

1. Inspect the changed files and identify affected behavior.
2. Run the relevant Vitest file while iterating.
3. Run `npm run build` for TypeScript validation.
4. Run `npm test` before handoff when source or shared configuration changed.
5. Report the commands run, results, and any behavior that was not exercised.

Read [references/test-matrix.md](references/test-matrix.md) when deciding which checks cover a change.

