---
name: llm-wiki-builder
description: 当用户想创建、脚手架化、迁移或初始化一个基于 Codex + Obsidian 的 LLM wiki，或想把方法文档落实成可用的本地知识库结构时，使用这个技能。NOT for 日常内容入库、查询或 lint 已存在的 wiki。
---

# LLM Wiki Builder

Use this skill to scaffold or migrate a Codex + Obsidian LLM wiki.

## Default Path

1. Read `操作文档.md` if present, otherwise read the user's current materials.
2. Create the minimal durable vault structure.
3. Add root instructions, schemas, and repo-scoped skills.
4. Stop before overwriting any existing user file with conflicting content.
