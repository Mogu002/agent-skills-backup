# Three-Entry Rollout

Use this reference when the user wants a Codex + Obsidian LLM wiki that is not only scaffolded, but actually operable.

## Default Sequence

1. Read the vault's current `操作文档.md`, `AGENTS.md`, and `index.md`.
2. Confirm the minimal structure exists before adding new layers.
3. Treat the project as needing three practical entry points:
   - Obsidian for human reading and navigation
   - Codex for repo-scoped wiki skill execution
   - a runtime preflight or launcher layer for consistent startup
4. If a repo-local SessionStart hook is missing, add a launcher instead of inventing fake hook support.
5. Update durable notes so the operating model is discoverable from inside the vault.
6. Record rollout progress in `log.md`, and update `todo.md` to reflect what is now truly usable.

## What Counts As "Operationalized"

The wiki is more than a scaffold when:

- the vault has a stable root entry and schema
- repo-scoped skills exist for daily work and builder work
- there is a concrete way to enter the project consistently
- the current runtime boundary is documented instead of implied
- at least one real source has been ingested into durable notes

## Preferred Runtime Fallback

When no trusted repo-local hook system is available, prefer a launcher script that can:

- check critical project files
- open the vault in Obsidian
- launch Codex in the vault root
- give one shared status path for human and agent use
