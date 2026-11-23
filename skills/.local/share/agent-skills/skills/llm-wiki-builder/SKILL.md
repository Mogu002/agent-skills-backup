---
name: llm-wiki-builder
description: 当用户想创建、脚手架化、迁移、补全运行层，或把一个基于 Codex + Obsidian 的 LLM wiki 落实成可实际使用的项目时，使用这个技能。也用于把已经跑通的 LLM wiki 建设过程沉淀成 repo-scoped skill。NOT for 日常内容入库、查询或 lint 已存在的 wiki。
---

# LLM Wiki Builder

Use this skill to scaffold, operationalize, or migrate a Codex + Obsidian LLM wiki.

## Default Path

1. Read `操作文档.md` if present, then read the current vault's `AGENTS.md`, `index.md`, and any existing runtime notes.
2. Preserve the minimal durable vault structure before adding anything new.
3. Wire the three practical entry points:
   - Obsidian as the human-side vault
   - Codex with repo-scoped wiki skills
   - a runtime launcher or preflight layer when no repo-local SessionStart hook exists
4. Validate the setup with one real dry-run or forward check, then update `log.md`, `index.md`, and `todo.md`.
5. When the rollout has been proven in the current project, keep this skill aligned with the real process rather than a generic template.

## Required Reading

- `references/three-entry-rollout.md`
- `references/validation.md`

## Gotchas

- Do not assume repo-local startup hooks exist just because the article or concept model mentions SessionStart.
- Do not overwrite user-authored notes or existing domain structure just to match a template.
- If host-level startup automation is unavailable or unverified, prefer a repo-local launcher over pretending the hook layer already exists.
- Keep daily wiki work in `llm-wiki`; this builder is for structure, migration, wiring, and rollout hardening.
