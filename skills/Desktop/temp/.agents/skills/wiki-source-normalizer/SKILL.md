---
name: wiki-source-normalizer
description: 当用户想把一份已获取的来源文档（飞书/Lark 导出、网页正文、粘贴文本、Markdown 或 HTML）在进入 LLM wiki 入库流程前做“格式标准化”——统一标题层级、清理残留 HTML 与排版噪声、规整表格/列表/链接，产出层级清晰、可直接交给 `llmwiki add` 的干净 Markdown 时，使用这个技能。NOT for 抓取或获取来源内容、对内容做摘要或提炼观点、生成 wiki 来源页、写入任何 wiki 仓库。
---

# Wiki Source Normalizer

用这个 skill 把**已经拿到的**原始来源，转成一份层级清晰、格式统一的“系统化标准化文档”，作为它进入 LLM wiki `raw/sources/` 之前的前置站。

它跑在上游 Agent 环境里，位置固定在管线中段：

```
抓取类 skill（如 bytetech-article-reader）  →  【本 skill：来源标准化】  →  llmwiki add + source-analysis
      拿到原始内容                              统一格式 / 层级              登记为不可变证据 + 编译理解
```

## Default Stance

- **忠实重排版，不解读**：只动结构、格式和噪声；不摘要、不按重要性重排、不注入推断、不补作者没写的结论。输出会成为未来的不可变 raw source，任何“理解”都属于下游 `source-analysis`，不属于这里。
- **内容零丢失**：实质文本、数据、数字、链接、引用必须原样保留。删除只针对**非内容外壳**（导航、页脚、cookie 横幅、相关推荐、TOC dump）；拿不准就保留并标记，不静默删。
- **确定性优先**：机械可自动化的清洗（HTML→MD、表格、空白、编码）交给 `scripts/normalize.py`；只有需要语义判断的层级/噪声问题才由 Agent 手工处理。
- **绝不编造**：没有真实 URL 的图片用占位符，不虚构标题党标题，不臆造日期或来源。
- **不越界到 wiki**：不写 wiki frontmatter、不产出核心观点/证据/局限、不碰任何 wiki 仓库文件。

## Use This Skill When

- 用户已经有了来源内容（本地文件、导出 md、粘贴文本、HTML），想在入库前把它整理成干净规范的 Markdown。
- 来源是飞书/Lark 导出，混杂了 `<table>`、`<cite>`、`<callout>`、`<figure>` 等 CCM 私有 HTML。
- 来源层级混乱：多个 H1、伪标题（纯粗体行、“一、二、三”）、跳级、噪声页眉页脚。
- 用户明确说“预处理 / 标准化 / 清洗格式 / 规范化这份来源，准备入库”。

## Do Not Use This Skill When

- 用户还没拿到内容，要你去抓取/下载/打开链接：那是抓取类 skill 的事（如 `bytetech-article-reader`）。
- 用户要的是摘要、观点提炼、核心结论、证据账本：那是入库后 `source-analysis` 的事。
- 用户要把文件真正 `add` 进 wiki、写来源页、改 wiki 仓库：转对应的 wiki 入库流程。

## Required Reading

开始前按顺序读取：

1. [`references/format-standard.md`](references/format-standard.md) —— “标准化文档”的目标契约（产出长什么样）。
2. [`references/cleaning-playbook.md`](references/cleaning-playbook.md) —— 分输入类型的清洗步骤与忠实性自检（怎么做）。
3. [`scripts/normalize.py`](scripts/normalize.py) —— 确定性清洗脚本，**执行**它完成机械转换（仅依赖 python3 标准库）。

## Default Workflow

1. **确认输入已获取**。若任务其实是“去拿 X”，停手并说明这属于抓取类 skill。
2. **确定性 pass**：对输入跑 `python3 scripts/normalize.py <in.md> <out.md>`（目录用 `<in_dir> <out_dir>`），完成 HTML→Markdown、表格、列表、空白与编码归一。
3. **结构 pass（判断）**：按 `format-standard.md` 修层级——保证唯一 H1、无跳级、把伪标题升成真标题、剔除非内容外壳。
4. **忠实性自检**：对照原文确认只动了结构/格式/噪声，实质内容、数据、链接零丢失（见 playbook 的自检清单）。
5. **产出**：干净 `.md` + 一段简短报告：建议的 `title / date / url / collection`（标为“建议，供下游 add 使用”）、剔除了哪些外壳、哪些地方存疑保留。元数据**不写进正文**，保持 raw source 纯净。
6. **交接**：提示该文件已可直接用于下游 `llmwiki add`，并给出建议命令参数，但本 skill 不执行入库。

## Key Gotchas

- 不要把“清洗”做成“改写”：一旦开始概括、合并段落、调整论述顺序，就已经污染了证据层。
- 不要因为觉得某段“不重要”就删；删除只允许针对可复现的非内容外壳。
- 不要给没有 http(s) URL 的图片编造链接；用 `_[图片: alt]_` 占位。
- 不要保留任何残留 HTML 标签；简单表转 GFM，复杂/嵌套表转标签化 bullet 块（脚本已实现）。
- 不要写 wiki frontmatter 或 `source_id`/`source_hash`：那些由入库 CLI 和 `source-analysis` 生成，这里写了反而冲突。
- 不要假设当前在 `Base_Knowledge` 仓库里：本 skill 自包含，`normalize.py` 不依赖任何外部脚本或仓库路径。
- 输出应**幂等**：再跑一遍 `normalize.py` 结果不变，也应能原样通过 wiki 自带的清洗步骤。

## Deliverable Standard

交付时至少给出：

- 一份符合 `format-standard.md` 的干净 Markdown（层级清晰、无残留 HTML、无排版噪声）。
- 建议元数据：`title / date / url / collection`，明确标注为“建议值，非既成事实”。
- 变更说明：剔除了哪些外壳、做了哪些结构调整、哪些地方存疑保留。
- 一句确认：内容实质、数据与链接未丢失，文件可直接进入下游 `llmwiki add`。
