# Decomposition And Rubric

在使用 `researching-github-projects` 时，先把用户输入从“大方向”拆成“可检索模块”，再用统一 rubric 评估候选仓库。

## 1. Input Normalization

先从用户请求里抽取这些要素：

- `goal`: 想找完整项目、底层库、案例实现、生态工具，还是 issue 讨论
- `domain`: 业务领域或技术领域，例如 RAG、低代码、支付风控、浏览器自动化
- `constraints`: 语言、框架、平台、部署方式、许可证、维护状态、规模要求
- `output`: 想要候选清单、对比结论、最佳推荐，还是模块化生态图
- `exclude`: 明确不要的方向、已有方案、冲突技术栈
- `time_horizon`: 用户说的“长程”更偏时间跨度长，还是步骤链长

如果用户没说清，可先推断一个默认版本并在结果里显式写出假设。

### Time-horizon disambiguation

遇到“long-horizon / 长程 / 长期任务”时，先区分两种含义：

- `time-extended`: 任务要跨较长时间持续执行，例如周期性调度、长期监控、后台常驻、跨会话恢复、长期状态维护
- `step-extended`: 单次任务的步骤链很长，但通常在一次连续会话里完成

如果用户提到以下特征，默认按 `time-extended` 处理：

- 定时执行 / cron / schedule
- 长期运行 / daemon / worker
- checkpoint / resume / durable / persistence
- 监控、巡检、对账、补偿、重试、状态对齐

## 2. Domain Decomposition Heuristics

优先从以下 6 个角度拆模块；不是每次都要用满，但至少选 3 个角度检查一遍。

### A. Core capability

目标系统最核心的能力是什么？

- 例：检索、排序、生成、编排、同步、审计、可视化、监控、推理、支付、推荐
- 如果是 `time-extended` 长程任务，优先考虑：调度、持久化状态、恢复执行、重试补偿、事件驱动、巡检监控

### B. Workflow stages

从端到端流程拆分。

- 输入采集
- 预处理 / 清洗 / 解析
- 核心执行引擎
- 存储 / 索引 / 缓存
- 输出分发 / 展示 / 回调
- 评估 / 监控 / 运维

### C. Technical components

从关键部件拆分。

- SDK / API
- CLI / UI / dashboard
- plugin / adapter / connector
- schema / config / rule engine
- benchmark / evaluation / observability

### D. Ecosystem layers

从生态位拆分。

- 主框架
- 官方示例
- 社区插件
- 行业落地项目
- 工具链与脚手架

### E. User and scenario variants

从使用场景拆分。

- 个人开发 vs 团队协作
- 本地部署 vs 云服务
- 实时 vs 离线
- 研究原型 vs 生产就绪
- 通用场景 vs 某垂直行业

### F. Pain points

从痛点或 issue 高频词拆分。

- 性能
- 兼容性
- 扩展性
- 易用性
- 稳定性
- 成本
- 安全 / 合规

## 3. Query Construction Patterns

每个模块至少准备一组主 query 和两组扩展 query。
优先把 query 设计成“可直接喂给搜索工具”的形式，而不是只停留在抽象关键词。

### Query pattern 1: domain + module + implementation

```text
automation browser plugin framework
rag evaluation benchmark example
payment risk rule engine sdk
```

### Query pattern 2: domain + scenario + evidence

```text
rag finance demo
browser automation test example
recommendation system issue cold start
```

### Query pattern 3: module + synonym + ecosystem term

```text
connector adapter integration
policy engine rule engine workflow
vector search embedding retrieval
```

### Query expansion checklist

对每个核心词，补这些变体：

- 同义词：`retrieval`, `search`, `lookup`
- 缩写：`llmops`, `rag`, `etl`, `ocr`
- 上位词：`workflow`, `platform`, `framework`
- 下位词：`adapter`, `plugin`, `cli`, `starter`
- 相邻词：`benchmark`, `playground`, `cookbook`, `template`
- 维护词：`actively maintained`, `production ready`, `archived`

如果用户要找的是 `time-extended` 长程任务，再优先扩这些词：

- `cron`, `scheduler`, `scheduled job`, `background worker`
- `durable execution`, `checkpoint`, `resume`, `state persistence`
- `monitoring`, `watcher`, `polling`, `reconciliation`
- `retry`, `backoff`, `orchestration`, `temporal`, `airflow`, `dagster`

### Query pruning checklist

结果太杂时，优先增加：

- 语言或框架：`python`, `typescript`, `go`, `react`, `spring`
- 平台：`kubernetes`, `ios`, `android`, `chrome extension`
- 场景：`enterprise`, `realtime`, `self-hosted`
- 排除词：`-awesome`, `-tutorial`, `-deprecated`

## 4. Tool-First Execution

默认执行顺序是：先搜索，再抓取，再复核。

### A. Broad discovery with web search

优先使用 `mcp_tool_friday_universal_search_web_search` 做 GitHub 宽搜或模块窄搜。

查询构造建议：

- 在 query 中加入 `site:github.com`
- 明确仓库意图词：`repo`, `repository`, `open source`, `framework`, `sdk`, `example`
- 明确证据词：`readme`, `demo`, `issue`, `discussion`, `pull request`, `test`
- 如有需要，再加语言、框架、平台、年份、维护状态

示例：

```text
site:github.com rag evaluation framework example
site:github.com browser automation chrome extension repo issue
site:github.com payment risk rule engine open source discussion
```

### B. Direct fetch when URL is known

当搜索结果已返回具体 GitHub 页面，或用户直接给出仓库 URL 时，立即切换到 `web_fetch`。

优先抓这些页面：

- 仓库主页
- README 所在页面
- `examples/`, `demo/`, `sample/`, `playground/` 目录页
- `test/`, `tests/`, `spec/` 目录页
- 关键 issue / PR / discussion 页面

### C. Community validation route

- 跨仓库找社区证据：继续使用 `mcp_tool_friday_universal_search_web_search`
- 已锁定单仓库且重点查 issue/PR/discussion：优先激活 `context7-github-search` skill
- 若没有专门 skill 或结果不足：回退为网页搜索 + `web_fetch`

### D. Parallelization rule

当模块数量较多，或需要同时覆盖“仓库发现”和“社区验证”两类搜索时，可以使用 `task` 的 `explorer-agent` 并行处理；否则保持单线程默认路径，避免无谓复杂度。

## 5. Evidence Checklist Per Repository


每个候选仓库至少过一遍以下检查。

### README evidence

- 是否明确描述目标问题或领域场景
- 是否列出关键特性，且与模块命中有关
- 是否说明边界、不支持项、依赖前提
- 是否有 quickstart、架构图、真实截图或 demo
- 是否有最近更新时间、版本、路线图、维护说明
- 如果目标是 `time-extended` 长程任务，是否明确提到调度、长时间运行、持久化、恢复、后台执行、周期性触发等能力

### Code and example evidence

- 是否存在与目标场景直接相关的代码路径
- 是否有示例、模板、测试、fixture、benchmark
- 是否能从代码结构看出该能力是主能力而非附属能力
- 是否有真实集成点、适配器或插件机制
- 如果目标是 `time-extended` 长程任务，优先找调度器、worker、checkpoint、state store、retry loop、recovery logic、timer/cron integration

### Community evidence

- issue/PR/discussion 是否讨论目标场景
- 是否存在成功使用、迁移、限制、替代方案讨论
- 维护者是否活跃回复
- 是否有长期悬而未决的关键问题

## 6. Scoring Rubric

用 0-3 打分，先定性，再汇总。

### A. Problem fit

- `3`: 直接解决目标问题，README 明确写出该场景
- `2`: 解决相邻问题，能覆盖目标的一大部分
- `1`: 只有局部组件价值
- `0`: 只是关键词碰巧相关

如果用户要找的是 `time-extended` 长程任务，则“多步但短时完成”的项目最多只能算 `2`，除非它明确支持长期执行、周期性触发或持久化恢复。

### B. Module coverage

- `3`: 覆盖多个核心模块
- `2`: 覆盖至少一个关键模块
- `1`: 只覆盖边缘模块
- `0`: 无法映射到模块

### C. Code evidence strength

- `3`: 有清晰源码路径 + 示例/测试支撑
- `2`: 有源码支撑但示例不足
- `1`: 只有 README 自述或零散代码
- `0`: 无法验证

### D. Community evidence strength

- `3`: issue/PR/discussion 明确显示真实使用与维护
- `2`: 有相关讨论，但证据不完整
- `1`: 讨论很少或相关性弱
- `0`: 无法判断或明显失活

### E. Maintenance

- `3`: 最近仍活跃，版本与提交持续更新
- `2`: 维护一般，但可用
- `1`: 更新较少，存在风险
- `0`: 已归档或明显停滞

### F. Reuse value

- `3`: 可直接拿来试用或深度借鉴
- `2`: 适合参考某个模块或架构
- `1`: 只能提供少量灵感
- `0`: 不建议投入时间

## 7. Classification Labels

根据评分和证据，给出一个最终标签：

- `Exact match`: 高度匹配，适合直接深入
- `Strongly related`: 不完全同类，但强相关且有高参考价值
- `Useful component`: 某个模块很有价值，适合作为组合方案的一部分
- `Inspiration only`: 可提供思路，但不建议作为主候选
- `Noise / discard`: 应剔除

## 8. Minimal Deliverable

输出时除了结论，还应显式说明本次用到了哪些工具、它们分别产出了什么证据。

最终至少输出这些内容：

- 用户目标与默认假设
- 模块拆解结果
- 关键 queries 的构造思路
- 每个重点仓库的证据与标签
- 为什么推荐 / 为什么剔除
- 当前检索盲区与后续建议
