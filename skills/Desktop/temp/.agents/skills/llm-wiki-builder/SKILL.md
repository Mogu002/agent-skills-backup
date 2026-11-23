---
name: llm-wiki-builder
description: 当用户想创建、脚手架化、迁移或初始化一个基于 Codex + Obsidian 的 LLM wiki，或想把《操作文档.md》里的方法落实成可用的本地知识库结构时，使用这个技能。NOT for 日常内容入库、查询或 lint 已存在的 wiki。
---

# LLM Wiki Builder

用这个 skill 把一份关于 LLM wiki 的设计说明，落实成一个可用的本地 vault 和配套 agent 规则。

## Default Stance

- 先读现有材料，再创建文件；优先使用工作区中已经存在的《操作文档.md》作为事实来源。
- 默认交付最小可用但完整的第一版：目录结构、`AGENTS.md`、`index.md`、`log.md`、`schemas/`、repo-scoped skill。
- 不要把“如何使用 wiki”和“如何搭建 wiki”混成一个文件；构建用规则和日常使用规则分开。
- 不覆盖已有用户文件；若目标路径已有冲突，先汇报冲突并停下等待确认。

## Use This Skill When

- 用户要在一台新电脑上初始化 Codex + Obsidian LLM wiki。
- 用户要把一份方法论文档、SOP 或文章打包成“可让 agent 执行”的建库流程。
- 用户要为一个 vault 生成初始脚手架和触发规则。
- 用户要把“手工搭建过程”沉淀成可复用 skill。

## Do Not Use This Skill When

- 用户只是要往现有 wiki 里入库一篇文章。
- 用户只是要查询、整理或 lint 已经存在的 wiki。
- 用户只是要微调某个现有 `SKILL.md` 里的个别措辞，且不涉及整套建库流程。

## Required Reading

开始前按顺序读取：

1. 工作区中的《操作文档.md》；若不存在，再基于用户当前提供的材料继续。
2. [`references/scaffold.md`](references/scaffold.md)
3. [`references/validation.md`](references/validation.md)

## Default Workflow

1. 识别目标：确认这是“新建/迁移 wiki 脚手架”，不是日常入库任务。
2. 读取现有方法材料，提炼不可变约束：
   - `sources/` 与知识层分离
   - `ideas/` 只允许用户主动写入
   - `AGENTS.md` / schema / skill 要分层
   - 默认支持 Ingest / Query / Lint
3. 在目标目录创建最小可用结构和根规则文件。
4. 生成 repo-scoped builder 后续会依赖的 `llm-wiki` 使用 skill 或至少预留其目录。
5. 用一个代表性材料做 dry-run 级自测，确认另一位 agent 只读这些文件也知道第一步该做什么。
6. 汇报新增文件、冲突、以及用户下一步如何触发第一次 Ingest。

## Key Gotchas

- 不要直接把长篇背景文章原样塞进 `SKILL.md`；主文件只保留触发条件、默认路径和硬边界。
- 不要一开始创建过多领域目录；只有在材料明确支持时才扩展。
- 不要把 builder skill 写成日常 wiki skill；建库和用库是两类任务。
- 不要偷偷覆盖用户已有的 vault 文件、同步目录或 Git 结构。
- 如果材料足够，只推断一个默认路径，不平铺多个等权方案。

## Deliverable Standard

交付结果至少应让另一个 agent 在只读当前 vault 的情况下知道：

- 入口文件是什么
- 目录边界是什么
- 第一次 Ingest 应该怎么触发
- 哪些地方绝不能自动写入或重写
