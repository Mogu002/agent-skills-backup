---
name: hostplan-evaluation-annotator
description: 当用户需要按 hostplan 评测手册标注或修订 checklist/CSV 评测任务时，使用这个技能；尤其是输入包含 type、query、name、requirement、action、review_notes、case_id 或 item_id，需要判断 keep/update/delete/add、去重、补漏、覆盖自检，或处理 workflow/dashboard 别名穷举的场景。NOT for 执行真实工作流创建、生成最终业务产物、或给 query 补充隐性产品需求。
---

# Hostplan Evaluation Annotator

这个技能用于完成 hostplan checklist 评测标注任务。核心目标不是把要求写得更细，而是让每道题的 `keep + update + add` requirement 能覆盖用户 `query` 中的全部显性需求，同时删掉重复、噪音和过指定内容。

## First Principles

每次标注前先固定三个概念：

- **显性需求**：`query` 字面明确提到的动作、对象、字段、条件、接收人、输出内容。
- **隐性需求**：行业默认期待但 `query` 没说的内容。本任务一律忽略，不要新增 requirement。
- **覆盖完整性**：一道题所有保留项串起来，能否回拼出 `query` 的全部显性需求点。

只评 checklist/plan，不评最终业务产物。不要因为某项“看起来不够详细”就补产品细节。

## Allowed Actions

对每一行只选择一个 `action`：

| action | 何时用 | 能改什么 |
|-|-|-|
| `keep` | 检查项合理，覆盖 query 的显性需求，且无重复/过指定/产物依赖 | 不动 |
| `update` | 需求点要保留，但描述过细、过窄、空泛、有产物依赖或顺序/name 不合适 | 改 `requirement`，必要时改 `name`、`item_order` |
| `delete` | 噪音、重复、别名穷举、用户未要求、只服务隐性需求 | 只改 `action=delete`，其他列保持原样 |
| `add` | query 明确要求但当前 checklist 漏掉 | 新增行并填写 `name`、`requirement`、`item_id`、`item_order` |

`add` 新行的 `item_id` 用 `<domain>_<case_id>_ADD001`、`ADD002` 递增。`item_order` 取能插入目标位置的数值，必要时可用小数。

## Default Workflow

1. 按 `domain + case_id` 收拢同一题所有行，读取 `type` 和 `query`。
2. 从 `query` 拆出显性需求清单，优先写成短编号，如 `N1 触发器`、`N2 条件`、`N3 动作/接收人`。
3. 如果是 workflow/dashboard，先检查 `name` 里是否出现多个不同的 `「XXX」` 前缀；若这些前缀只是同一个工作流/面板的不同命名，保留最贴合 query 的一组，其余整组 `delete`。
4. 对保留行逐行判定：是否对应某个显性需求；是否重复；是否过指定；是否包含产物依赖；是否空泛。
5. 对照显性需求清单补漏：漏掉的明确需求用 `add`，不要为隐性需求补行。
6. 做题级覆盖自检：把所有 `keep/update/add` 后的 requirement 串起来，必须能回拼 query 的全部显性需求点。
7. 可选核对顺序：有执行依赖且 `item_order` 明显不合理时，调整顺序或在 `review_notes` 写顺序建议。
8. 输出每行 `action` 时都给一句判断原因；为所有 `update/delete/add` 写简短 `review_notes`，说明可回填的修改原因。

## Priority Rules

按这个优先级抓问题：

1. **不重**：同一题里多条检查项表达同一件事，保留语义最清晰的一条，其余 `delete`。
2. **不漏**：query 明确要求但 checklist 没覆盖，必须 `add`。
3. **覆盖**：完成后做题级自检，保证保留项能覆盖全部显性需求。
4. **顺序**：有执行依赖才处理，是软约束。

### Workflow/Dashboard 别名穷举

识别信号：同一题 `name` 里有多个不同 `「XXX」` 前缀，但它们都指向 query 中同一个工作流或面板。

处理方式：

- 数出不同别名组。
- 选最贴合 query 的一组作为代表。
- 其余组整组 `delete`，无需逐行细判。
- `review_notes` 统一写：`别名穷举重复，保留「{代表组名}」组`。
- 如果 query 真的要求创建多个工作流/面板，不要按别名穷举删除。

## Risk Checklist

逐行判断时额外识别这些子问题：

- **产物依赖**：requirement 写了具体函数名、布局坐标、默认主题、AI 自创字段名等。除非 query 点名，否则 `update` 成语义级要求。
- **过指定**：query 说得宽，requirement 卡得死，如未点名却要求特定图表类型、消息标题、字段展示格式。`update` 改宽。
- **空 requirement**：只有名称没有要求，如 `「XXX」创建`。`update` 补完整语义，或与上下文合并后 `delete` 当前行。
- **字面重复**：requirement 文本完全相同。通常保留前者，后者 `delete`。
- **语义重复**：文本不同但实际检查同一需求点。保留清晰者，其他 `delete`。

## Explaining Action Reasons

输出 action 时，原因要短、可审计、能回到 SOP 的判断步骤。用一句话说明：这行对应哪个显性需求，发现了什么问题，所以为什么选这个 action。

推荐格式：

```text
action_reason: 对应 N{编号}，{无风险/存在的问题}，因此 {keep/update/delete/add}。
review_notes: {删/改/加/顺序建议}：{可回填的简短原因}
```

原因写法按 action 区分：

| action | action_reason 写什么 | review_notes 写什么 |
|-|-|-|
| `keep` | 说明覆盖了哪个显性需求，且无重复、过指定、产物依赖 | 通常留空 |
| `update` | 说明需求点要保留，但原 requirement 过细、过窄、空泛、顺序/name 不合适或有产物依赖 | `改：移除产物依赖(具体函数名)`、`改宽：用户未指定消息标题`、`改：补完整语义` |
| `delete` | 说明对不上显性需求、重复、别名穷举或用户未要求 | `删：用户未要求`、`删：语义重复`、`别名穷举重复，保留「X」组` |
| `add` | 说明 query 的哪个显性需求没有被现有 checklist 覆盖 | `加：用户要求的字段未覆盖`、`加：缺少通知对象要求` |

不要输出长推理过程；原因只保留结论性证据。不要把 `sample_detail`、机器建议列或隐性需求当作原因。

### Preferred Review Notes Phrasing

针对高频的“创建项 requirement 只是标题复述或表述空泛”场景，优先使用更直白、可读性更高的 `review_notes` 表达。

- 推荐写法：`改：补成明确的创建要求，避免表述空泛`
- 不再优先使用：`改：补成可直接校验的工作流存在性要求`

适用信号：

- `name` 为 `「XXX」创建`
- `requirement` 只是重复 `name`，如 `「XXX」创建`
- `requirement` 是空泛病句，如 `XXX工作流的创建应「XXX」创建`

这类场景通常仍然是 `update`，并将 `requirement` 改为类似 `需创建「XXX」工作流。`
```

同时建议把 `update` 行中的示例：

```md
`改：移除产物依赖(具体函数名)`、`改宽：用户未指定消息标题`、`改：补完整语义`
```

更新为：

```md
`改：移除产物依赖(具体函数名)`、`改宽：用户未指定消息标题`、`改：补完整语义`、`改：补成明确的创建要求，避免表述空泛`
```
## Do Not

- 不要把 `sample_detail` 抄进 `requirement`。
- 不要修改 `domain`、`case_id`、`query`。
- 除 `add` 新行外，不要修改既有 `item_id`。
- 不要为隐性需求新增 requirement。
- 不要把所有 requirement 都加细节；方向是去重、补漏、改宽、覆盖。
- 不要把机器建议列当结论；`llm_status`、`llm_risk`、`recommended_fix`、`missing_requirements` 只能辅助参考。

## Output Expectations

如果用户给的是表格/CSV，输出可直接回填的行级变更：

- 保留原行标识，如 `case_id`、`item_id`、原 `name`。
- 明确 `action`。
- 每行给出一句 `action_reason`，解释 action 判断依据。
- 对 `update/add` 给出新 `name` 和新 `requirement`。
- 对 `delete/update/add` 给出可回填的 `review_notes`；`keep` 的 `review_notes` 通常留空。
- 最后给一段题级覆盖自检，列出显性需求是否都已覆盖。

如果用户只给 query 和候选 name/requirement，先按同一题处理，输出建议标注结果；不要凭空发明不存在的字段。

## References

- 读 [`references/workflow-example.md`](references/workflow-example.md) 查看一个 workflow 输入题的 dry-run 标注尺度。
