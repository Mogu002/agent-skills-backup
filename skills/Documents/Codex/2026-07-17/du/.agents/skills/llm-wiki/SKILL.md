---
name: llm-wiki
description: Maintain this Obsidian-compatible personal LLM wiki. Use for ingest, query, proposal, approval, and lint tasks.
---

# Daily Wiki Skill

Read `AGENTS.md`, `index.md`, and relevant schemas before acting.

## Commands

- `入库 <source>`: preserve source, create new pages, propose edits to existing pages.
- `查询 <question>`: answer from indexed wiki and cite source pages.
- `生成 proposal`: describe edits without mutating existing wiki pages.
- `批准 proposal <file>`: apply an approved proposal and update index/log.
- `lint`: run `bash scripts/wiki.sh lint`.

## Hard boundary

Creating a genuinely new page is allowed without approval. Editing an existing page, changing its status, or changing links from it requires a proposal first.

