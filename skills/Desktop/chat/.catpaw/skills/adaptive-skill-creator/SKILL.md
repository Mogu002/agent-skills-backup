---
name: adaptive-skill-creator
description: 当用户想创建、新建、编写、author、重构或优化任何 CatPaw/agent skill，改进 `SKILL.md`、触发描述或目录结构，或把可复用工作流、SOP、模板、评审经验沉淀成可维护 skill 时，使用这个技能。它作为创建 skill 的默认入口，并会根据现有资料、案例、项目上下文或既有流程细节的成熟度，自动选择合适的构建方式。
---
# Adaptive Skill Creator

这是一个用于创建、优化和沉淀 agent skill 的统一入口。
不要把它当成两份 skill 的简单拼接；先判断证据成熟度，再进入对应路径。

## Purpose

用这个 skill 来处理以下任务：
- 新建一个 agent skill
- 重构或整理已有 `SKILL.md`
- 优化 skill 的触发描述、结构和默认路径
- 把工作流、SOP、重复任务模式沉淀成可维护 skill

## Triage

先根据上下文判断当前属于哪种证据条件。
重点识别以下信号：
- 是否存在文档、代码、配置、schema、SOP、模板、示例等稳定材料
- 是否已有重复执行过的流程
- 是否存在 review 评论、失败案例、历史纠偏或稳定术语
- 当前目标是从零探索创建，还是沉淀已有实践

按以下规则默认分流：
- 如果用户明确提供了项目资料、SOP、样例、代码、已有文档，进入 `references/evidence-rich.md`
- 如果用户是在优化已有 `SKILL.md`、已有 skill 或已有稳定流程，进入 `references/evidence-rich.md`
- 如果用户明确提到反复出现的问题、review 意见、历史纠偏或失败案例，进入 `references/evidence-rich.md`
- 其他情况进入 `references/evidence-light.md`

安全偏置：
- 当两条路径看起来都能解释当前任务时，优先走 evidence-light
- 只有证据明确足够时，再升级到 evidence-rich

## Key Gotchas

在进入具体路径前，先避免这些高频错误：
- 证据不足时，不要臆造成熟 workflow；先交付最小可用版本
- 不要为了显得完整，预先创建多余的 `references/`、`scripts/` 或 `assets/`
- 不要把教程式背景知识堆进 `SKILL.md` 主文件
- 不要给很多平级方案；必须先给一个明确默认路径
- 不要把首次输出当成稳定版本；先完成最小验证闭环

## Default Workflow

按以下顺序工作：
1. 先用上面的 triage 规则判断当前请求属于 evidence-light 还是 evidence-rich
2. 读取对应参考文件：
   - `references/evidence-light.md`
   - `references/evidence-rich.md`
3. 按对应路径完成编写或改写工作
4. 最后读取 `references/shared-checklist.md`，完成统一收尾检查和最小验证闭环

## Shared Guardrails

无论走哪条路径，都遵守这些规则：
- `name` 必须合法且与目录一致
- `description` 必须以用户意图和触发条件为中心
- `SKILL.md` 主文件保持轻量，不要堆满细节
- support files 只在有明确用途时创建
- references 尽量保持一层直达，避免深层跳转
- skill 必须给出一个清晰默认路径，而不是很多平级选项
- 重要 gotchas 不应全部埋在可选 references 中
- 交付前至少完成一轮最小验证闭环，而不是把首次输出直接当成成品

## References

根据 triage 结果按需读取：
- `references/evidence-light.md`：适用于低证据、从零搭建、先求最小可用骨架的场景
- `references/evidence-rich.md`：适用于高证据、已有材料、已有流程、强调高质量沉淀的场景
- `references/shared-checklist.md`：两条路径共用的最终检查项和最小验证闭环
