---
name: llm-wiki
description: Use when the user wants to ingest sources, query, maintain, or lint a Codex + Obsidian LLM wiki. Trigger on LLM wiki, Obsidian knowledge base, 入库, 知识库, 双链, wiki query, or wiki lint tasks.
---

# LLM Wiki

This skill maintains a local Obsidian-friendly LLM wiki.

## Required Reading

Before any wiki operation, read:

1. `AGENTS.md`
2. `index.md`
3. relevant files in `schemas/`
4. relevant directory-level `AGENTS.md`

## Default Workflow

Choose one path:

- Ingest: preserve a source, synthesize durable knowledge, and update links.
- Query: answer from the wiki, then optionally save durable conclusions.
- Lint: inspect coherence, fix safe issues, and report anything risky.

## Ingest Rules

- Save or update the source under `sources/`.
- Preserve provenance.
- Prefer updating an existing concept or practice page over creating duplicates.
- Do not auto-write into `ideas/`.
- Update `log.md` after durable changes.

## Query Rules

- Distinguish what the wiki already says from current inference.
- Save only conclusions likely to be reused.

## Lint Rules

- Check broken links, duplicates, stale pages, and source coverage gaps.
- Ask before destructive changes.
