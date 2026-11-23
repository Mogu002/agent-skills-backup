# Scaffold Workflow

本文件描述 `llm-wiki-builder` 的默认建库步骤。

## Goal

从一份 LLM wiki 方法说明出发，创建一个可在 Codex + Obsidian 中直接使用的本地知识库脚手架。

## Minimal Output

默认至少创建这些内容：

```text
<vault>/
├── AGENTS.md
├── index.md
├── log.md
├── todo.md
├── schemas/
│   ├── entity-schema.md
│   ├── ingest-workflow.md
│   ├── query-workflow.md
│   └── lint-workflow.md
├── sources/
├── concepts/
├── craft/
├── qa/
├── ideas/
└── .agents/skills/llm-wiki/
    └── SKILL.md
```

如果用户提供的材料已经明确了更多领域，如 `writing/`、`learning/`、`repos/`，再继续扩展。

## Build Steps

1. 先检查目标目录是否已有 `AGENTS.md`、`index.md`、`.agents/skills/` 或明显的 Obsidian vault 痕迹。
2. 如果已有同名关键文件，不覆盖，改为读取并基于现状补齐缺口。
3. 创建根目录规则：
   - `AGENTS.md`
   - `index.md`
   - `log.md`
   - `todo.md`
4. 创建 schema 文件，内容保持简洁但足以约束：
   - entity/frontmatter 规范
   - Ingest 工作流
   - Query 工作流
   - Lint 工作流
5. 创建目录边界：
   - `sources/` 保存原始资料
   - `concepts/` 保存概念页
   - `craft/` 保存工程经验
   - `qa/` 保存高价值问答
   - `ideas/` 仅保存用户主动输入的想法
6. 创建 repo-scoped `llm-wiki` skill，供日常入库和查询使用。
7. 更新 `index.md` 让它成为人机共读入口。
8. 在 `log.md` 追加初始建库记录。

## Writing Rules

- 优先 ASCII 文件名；中文可留在标题或正文中。
- 页面之间用 `[[wikilink]]`。
- frontmatter 保持稳定，避免每类页面各写一套不兼容字段。
- 重要结论要落文件，不只存在于对话里。

## Stop Conditions

出现以下情况时先停下：

- 用户目标路径已有明显完整 vault，且新旧结构冲突较大。
- 已有 skill 命名和当前打算创建的 skill 冲突。
- 用户要求覆盖已有文件，但未明确确认。
