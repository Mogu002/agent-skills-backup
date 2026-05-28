---
name: model-eval-qc
description: 当用户想对当前项目下批量模型评测结果包做质检、复核打分是否正确、定位误判原因、统计各模型错误类型，或基于 `task.yaml`、`rubrics.md`、`score.md`、`openai_messages.json` 产出质检结论时，使用这个技能。适用于 `ba-0xx/model_outputs/...` 这类评测结果目录。NOT for 重新跑模型评测或改写任务答案本身。
---

# Model Eval QC

用于批量质检当前仓库下的模型评测结果包，重点做两件事：
- 复核 `score.md` 中的打分模型是否判对
- 归因每个模型/任务的失败原因，区分为分析错误、工具调用错误、输出截断或其他原因

这个 skill 默认面向当前工作区这类目录结构：
- `ba-0xx/task.yaml`：任务描述
- `ba-0xx/solution/rubrics.md`：评分标准
- `ba-0xx/model_outputs/<model>/<run>/score.md`：评分结果
- `ba-0xx/model_outputs/<model>/<run>/openai_messages.json`：工具调用与对话轨迹

## 何时使用

当用户提到以下意图时使用：
- “给这批模型评测结果做质检”
- “看打分模型有没有打错”
- “分析每个模型错因”
- “统计哪些是工具调用错、哪些是分析错”
- “批量复核 `score.md` / `openai_messages.json`”

## 关键姿态

开始前先默认以下原则：
- **先抽样校准，再批量扩展**：先挑 1-3 个任务、覆盖多个模型，校准你的复核框架，再扩大范围。
- **以 rubric 为准，不以你主观偏好为准**：只判断交付结果是否满足 `rubrics.md`，不要把“更好答案”当成“必须答案”。
- **分开两个问题**：先判断 `score.md` 是否判对，再判断模型本身为什么错。不要把评分错误和模型错误混在一起。
- **优先复用脚本做结构化清点**：先用脚本汇总 run 清单、评分摘要、轨迹信号，再把 LLM 判断用在需要语义裁决的地方。
- **不要一次性通读全部长日志**：先看 manifest 摘要和关键片段，只有出现争议时再下钻原始日志。

## 默认工作流

### 1. 先确认范围

默认以当前工作区为根目录，扫描所有 `ba-*` 任务包。
如果用户指定了任务或模型子集，优先按用户范围过滤。

优先确认：
- 质检范围：全量 / 指定 `ba-0xx` / 指定模型
- 目标输出：抽样报告 / 全量统计 / 错因分布 / 典型 case
- 是否需要真正“复核打分”，还是只做“错因归类”

### 2. 生成结构化清单

先运行：

```bash
python skills/model-eval-qc/scripts/build_qc_manifest.py --root . --output /tmp/model-eval-qc-manifest.json
```

常用变体：

```bash
python skills/model-eval-qc/scripts/build_qc_manifest.py --root . --task ba-001
python skills/model-eval-qc/scripts/build_qc_manifest.py --root . --model 'chat-*' --limit 20
```

这个脚本会输出每个 run 的最小必要摘要，包括：
- 任务、模型、run 路径
- `score.md` 中记录的总分、`all_pass`、逐 rubric pass/fail 与原因预览
- `rubrics.md` 的 rubric 数量与 id
- `openai_messages.json` 的 assistant/tool 轮次、工具名、空工具输出计数、最终答案预览
- 缺失文件或解析失败信号

如果脚本输出异常，再回头检查目录结构或单文件格式。

### 3. 先做脚本级初筛

先根据 manifest 给 run 打上“需优先人工/LLM 复核”的信号，典型包括：
- `score.md` / `openai_messages.json` / `rubrics.md` 缺失
- `score_parse_error` 或 `message_parse_error` 非空
- `empty_tool_output_count > 0`
- `missing_final_answer = true`
- 最终答案很短，或明显只停留在中间分析步骤
- rubric fail reason 与最终答案预览看起来矛盾

这一步的目标不是下结论，而是缩小 LLM 精读范围。

### 4. 复核打分是否正确

对每个待复核 run，按以下顺序判断：
1. 读 `task.yaml`，明确任务要求与交付形态
2. 读 `solution/rubrics.md`，把 rubric 拆成可检查断言
3. 看 `openai_messages.json` 中**最后一个有效 assistant 答案**，把它当作被评分对象
4. 对照 `score.md` 的每条 rubric 判断：
   - 该条 rubric 实际应不应该过
   - 评分模型给出的 `pass` 是否正确
   - `reason` 是否引用了真实答案内容，而不是脑补
5. 最后再判断总分 `score` / `all_pass` 是否与逐条 rubric 一致

复核时必须显式区分三种结论：
- **评分正确**：`score.md` 判断与 rubric 和最终答案一致
- **评分偏严/偏松**：逐条 rubric 某些 pass/fail 判错
- **证据不足**：日志缺失、最终答案缺失、rubric 歧义较大，无法稳健下结论

### 5. 归因模型错误原因

只有在确认“模型结果确实没满足 rubric”后，才进入错因分类。

默认使用以下一级分类，且每个失败 run 尽量只给一个**主因**，必要时再补“次因”：

- `分析错误`
  - 任务理解错、结论错、漏关键点、因果链错误
  - 做了工具查询，但最终结论仍与 rubric 不符
- `工具调用错误`
  - SQL/命令/工具参数错
  - 取数失败后未恢复
  - 使用了错误数据范围、错误字段、错误接口
  - 日志中明显出现空结果、报错、误读工具返回
- `输出截断`
  - 明显在回答未完成时停止
  - 日志最后停在中间分析或提纲
  - rubric 缺失点更像“没来得及说”而不是“不会分析”
- `其他原因`
  - rubric 歧义
  - 打分模型误判，但模型答案其实是对的
  - 上下文污染、格式约束冲突、路径缺失等不属于前三类的问题

### 6. 错因判定规则

按以下顺序判主因，避免混乱：

1. **先看有没有截断信号**
   - 最终答案突然中止
   - 没有真正的 final answer
   - 长时间工具链后只留下半成品结论
   - 若是，主因优先记为 `输出截断`

2. **再看工具链是否已把答案做坏**
   - 错日期、错 SQL、错字段、错误解析工具结果
   - 工具返回空值/报错后仍基于错误前提继续分析
   - 若核心结论直接建立在错误工具结果上，主因记为 `工具调用错误`

3. **最后看语义分析本身是否失败**
   - 数据和证据基本对，但总结错、漏关键点、建议方向错
   - 若是，主因记为 `分析错误`

4. **以上都不贴切时才用 `其他原因`**

## 重点 gotchas

- 不要把 `score.md` 里的 `reason` 当事实；它本身就是被质检对象。
- `openai_messages.json` 里可能有很多中间分析，**默认只以最后一个有效 assistant 答案作为最终交付**。
- 有些日志里 assistant 会输出空字符串后继续调用工具，不要把空字符串当最终答案。
- `(no output)` 这类 tool 返回通常是强信号，常对应命令失败、查询错误或管道写法问题。
- 若模型答案其实满足 rubric，但 `score.md` 判错，这个 run 的主问题通常是**评分错误**，不是模型分析错误。
- 若多个原因都成立，先给主因，再在备注中保留次因，避免一个 run 被打多个同级主标签。

## 推荐输出结构

做质检时，默认产出以下几层结果：
- **总体概览**：任务数、run 数、抽样/全量范围
- **评分复核结果**：评分正确数、疑似误判数、证据不足数
- **模型错因分布**：按模型统计 `分析错误` / `工具调用错误` / `输出截断` / `其他原因`
- **典型案例**：每类挑 1-3 个代表 run，说明证据链
- **后续建议**：给评分 prompt、执行框架、工具健壮性上的改进建议

建议表头字段：
- `task_id`
- `model_name`
- `run_id`
- `recorded_score`
- `qc_score_verdict`（correct / too_strict / too_lenient / inconclusive）
- `primary_failure_type`
- `secondary_failure_type`
- `evidence`

## 何时下钻原始日志

只有以下情况才需要精读 `openai_messages.json` 全文：
- `score.md` 的 fail 原因与最终答案预览冲突
- 需要判断到底是工具错误还是分析错误
- 怀疑有截断，但摘要不足以确认
- 需要提炼典型案例给用户展示

下钻时优先找：
- 最后几轮 assistant/tool 交互
- 首次出现空输出、报错、错误查询的地方
- 最终答案与中间结论不一致的地方

## 停止边界

以下情况不要继续自动扩写结论：
- 用户只要先写 skill，而不是立刻跑完整质检
- 缺少关键文件导致无法稳健复核
- 争议点本质上来自 rubric 歧义，且没有更多上下文可判

这时应清楚标注范围、证据和未决项，而不是强行给确定结论。
