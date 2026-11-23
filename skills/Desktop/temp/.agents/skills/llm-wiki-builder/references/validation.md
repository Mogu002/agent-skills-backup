# Validation

本文件定义 `llm-wiki-builder` 的最小验证闭环。

## Trigger Check

交付前，用下面三类说法检查 `description` 是否会命中：

1. “帮我搭一个 Codex + Obsidian 的 LLM wiki。”
2. “把这个操作文档变成一套 agent 能执行的建库 skill。”
3. “我要在另一台电脑上初始化同样的知识库脚手架。”

以下说法不应优先命中本 skill：

1. “把这篇文章入库到我的 wiki。”
2. “帮我 lint 一下现有知识库。”
3. “根据 wiki 回答我一个问题。”

## Dry-Run Standard

假设另一个 agent 只读新建的 `SKILL.md`，它应该立刻知道：

- 先读《操作文档.md》或当前材料
- 然后创建最小结构
- 不自动写入 `ideas/`
- 不混淆 builder skill 和日常 wiki skill

## Forward Test

若环境允许，至少做一轮轻量前向测试：

1. 用一句真实请求模拟建库任务。
2. 检查 skill 的默认第一步是否清楚。
3. 检查是否要求了不必要的 support files。
4. 检查交付是否能直接指导第一次 Ingest。

## Tightening Rules

如果验证时出现以下问题，先收紧再交付：

- `SKILL.md` 过长，变成教程文档
- 默认路径不清楚
- support files 只是重复主文件
- description 太泛，容易和日常 wiki skill 冲突
