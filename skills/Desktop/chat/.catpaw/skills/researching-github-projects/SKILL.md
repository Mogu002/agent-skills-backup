---
name: researching-github-projects
description: 当用户想根据关键词、目标领域、子模块或技术方向在 GitHub 跨仓库检索相关项目，并直接调用网页搜索、页面抓取、GitHub issue/PR/discussion 检索能力，用 README、源码、示例、测试和社区讨论等证据判断项目与目标是否匹配、相关或可借鉴时，使用这个技能。适用于开源方案调研、技术选型、竞品扫描、实现参考收集、项目清单梳理，以及先把宽泛需求拆成细粒度模块再分别检索的场景。NOT for 仅在单一已知仓库中查 issue/PR/discussion 的狭义问题。
---

# Researching GitHub Projects

这个技能用于把“按领域找 GitHub 项目”做成一个有证据的研究流程，而不是只返回几个仓库名。

## Default Stance

- 先从用户上下文推断领域、目标和约束；只有在确实阻塞检索时才补问最少信息。
- 先拆模块，再搜仓库；不要只拿原始关键词做一次宽搜。
- 先工具检索，再人工判断；优先用搜索和抓取拿证据，不凭印象下结论。
- 先看 README 建立候选池，再用源码、示例、测试和 issue 交叉验证。
- 不把 star 数当作匹配度；证据优先于热度。
- 最终要给“为什么相关”的证据，而不只是链接列表。

## Use This Skill When

- 用户说“帮我找 GitHub 上做 X 的项目/开源方案/实现”
- 用户给一个关键词和领域，想找相关仓库、案例、issue 讨论或参考实现
- 用户想把宽泛方向拆成细粒度模块后分别找项目
- 用户在做技术选型、竞品调研、方案探索、实现借鉴或生态扫描

## Tool Routing

默认按下面的工具路由执行；如果用户已经给了 GitHub URL，就跳过宽搜，直接抓取页面。

- `mcp_tool_friday_universal_search_web_search`
  - 用于跨仓库宽搜、按模块窄搜、补充 issue/PR/discussion 入口页。
  - 查询里优先加入 `site:github.com`，并把 `repo`, `readme`, `example`, `issue`, `discussion`, `pull request` 这些证据词带进去。
- `web_fetch`
  - 用于读取具体 GitHub 页面内容，例如仓库主页、README 页面、示例目录、测试目录、issue 页面、PR 页面、discussion 页面。
  - 当搜索结果已经给出具体 URL 时，直接抓取，不要再次做同义重复搜索。
- `context7-github-search` skill
  - 当已经锁定一个或少数几个仓库，且重点是 issue/PR/discussion 的定向检索时，优先激活这个 skill。
  - 如果环境中没有这个 skill 或不足以覆盖当前仓库，再退回网页搜索 + 页面抓取。
- `task` / `explorer-agent`
  - 当模块很多、需要并行搜索多个技术方向时，可把“搜候选仓库”和“搜社区讨论”拆成并行子任务。
  - 只在搜索规模明显偏大时使用，避免为简单检索增加开销。

## Workflow

1. Clarify the search target
   - 提取目标能力、应用领域、输入输出、约束、偏好语言/框架、运行环境、成熟度要求。
   - 先判断“长程”语义：
     - 时间跨度长：周期性任务、定时任务、后台常驻、长期监控、长期维护状态、跨会话持续执行
     - 步骤链长：单次任务步骤很多，但可能在较短时间内完成
   - 把用户原话拆成：核心问题、领域限定、排除项、验收标准。
   - 如果用户只给了宽泛方向，先自己推断一个合理默认边界，再继续。

2. Decompose the domain into modules
   - 读取 `references/decomposition-and-rubric.md`。
   - 把大词拆成 3-8 个可检索模块，优先按以下角度拆：核心能力、上下游流程、关键组件、基础设施、开发者体验、运维/治理。
   - 如果目标是“时间跨度长”的长程任务，优先补这些模块：scheduler、cron、timer、workflow orchestration、durable execution、checkpoint、resume、state persistence、background worker、monitoring、retry、reconciliation。
   - 为每个模块补充同义词、常见别名、缩写、上下位词和相邻概念。
   - 若某模块本身太大，继续拆到“可以直接构造搜索 query”的粒度。

3. Build layered queries and choose tools
   - 读取 `references/decomposition-and-rubric.md` 里的 query 模板和工具化执行规则。
   - 对整体领域先做宽搜，再按模块窄搜。
   - 每个模块至少准备三类 query：
     - 问题域词：用户目标、业务场景、行业术语
     - 实现词：library, sdk, framework, example, starter, boilerplate, benchmark, plugin
     - 证据词：readme, docs, example, demo, issue, discussion, test
   - 宽搜阶段默认调用 `mcp_tool_friday_universal_search_web_search`；当用户已提供仓库 URL 或搜索结果已出现明确仓库页时，直接转 `web_fetch`。
   - 如果结果噪音大，就加入排除词；如果结果太少，就退回同义词或上位概念。

4. Create a candidate repository pool
   - 用搜索工具先收集一批候选仓库，再逐个验证，不要找到一个就停止。
   - 优先覆盖不同层次：主项目、配套工具、示例仓库、生态插件、行业实现。
   - 记录每个仓库命中的模块，不要只做全局判断。
   - 对每个候选仓库至少保留一个可抓取 URL，方便后续 `web_fetch`。

5. Validate repository fit with README
   - 阅读 README 或主页介绍，判断它是否真的在解决目标问题。
   - 重点看：项目定位、支持场景、架构范围、特性边界、依赖前提、维护状态、最近更新、安装/快速开始、对比说明。
   - 识别以下信号：
     - 明确匹配：README 直接描述了目标能力或领域场景
     - 邻近相关：解决的是上游/下游问题，或提供关键配套能力
     - 弱相关噪音：只是包含关键词，但用途不对
   - README 结论必须记录成一句带证据的话。

6. Validate with source code, examples, and tests
   - 当 README 不够确定时，继续抓取源码目录、样例、测试、配置和 CLI/API 定义页面。
   - 优先用 `web_fetch` 读取仓库主页里已经暴露出的目录入口，或搜索结果里的具体代码/目录 URL。
   - 优先找这些证据：
     - `examples/`, `demo/`, `sample/`, `playground/`
     - `test/`, `tests/`, `spec/`, `fixtures/`
     - 关键模块名、接口名、命令行参数、配置项、适配器、插件点
     - 与目标领域直接相关的数据模型、工作流、集成方式
   - 判断标准：
     - 代码里是否真的实现目标能力，而不只是文案提到
     - 样例是否覆盖目标场景
     - 测试是否体现核心边界与真实用法
     - 代码结构是否说明这是主能力，而非附带能力

7. Validate with issues, PRs, and discussions
   - 先判断当前是“跨仓库找相关讨论”，还是“对单仓库做定向社区验证”。
   - 跨仓库时：继续使用 `mcp_tool_friday_universal_search_web_search`，查询里加入 `site:github.com` 与 `issues`, `pull`, `discussions` 等词。
   - 单仓库时：优先激活 `context7-github-search` skill；若不可用，再回退到网页搜索 + `web_fetch`。
   - 抓取 issue/PR/discussion 页面后，重点观察：
     - 社区是否真的在这个领域使用该项目
     - 是否有用户提出和目标场景一致的问题
     - 是否存在相关 roadmap、feature request、bug cluster、兼容性限制
     - 维护者是否持续回应，项目是否仍活跃
   - issue 既可以证明“相关”，也可以暴露“虽然相关但不适合”。

8. Score and classify each repository
   - 使用 `references/decomposition-and-rubric.md` 中的 rubric。
   - 至少从这几个维度评分：问题匹配度、模块覆盖度、代码证据强度、社区证据强度、维护状态、可复用价值。
   - 给每个仓库一个明确标签：
     - Exact match
     - Strongly related
     - Useful component
     - Inspiration only
     - Noise / discard

9. Synthesize the final answer
   - 先给结论，再给证据。
   - 按模块组织结果，而不是只按 star 数排序。
   - 对每个推荐仓库说明：解决什么、命中哪些模块、README 证据、源码/样例证据、issue 证据、风险点。
   - 若找不到完全匹配项目，要明确说明当前最接近的是哪几类项目，以及缺口在哪里。

## Output Shape

默认输出应包含：

- 目标拆解：核心目标、约束、拆出的模块
- 检索策略：用过哪些 query 类型、调用了哪些搜索/抓取工具、如何收窄范围
- 候选项目分组：按模块或相关性分组
- 重点仓库证据：README、源码/示例、issue/PR/discussion 的结论
- 最终判断：哪些是精确匹配，哪些只是组件级相关，哪些应剔除
- 风险与空白：维护风险、实现缺口、生态缺口、验证不足项

## Key Gotchas

- 不要只看仓库标题、描述或 star 数就下结论。
- 不要只用一个关键词搜到底；必须扩展同义词、模块词和行业术语。
- 不要把用户说的“长程任务”自动理解成“多步任务”；先区分时间跨度长 vs 步骤链长。
- 不要把 README 自述直接当真；关键结论要尽量用源码、样例或 issue 复核。
- 不要先抓页面再想问题；应先拆模块和构造 query，再决定抓哪些 URL。
- 不要因为 issue 多就判负面；需要区分活跃使用带来的讨论量和长期无人修复的问题堆积。
- 不要忽略示例仓库、awesome list、官方 demo、插件仓库；它们常常比主仓库 README 更接近落地场景。
- 当用户目标是一个完整系统时，不要强求单仓库全覆盖；允许输出“主项目 + 配套组件”的组合方案。

## Stop Conditions

只有满足以下条件才算完成：

- 已把宽泛目标拆成可检索模块
- 已实际调用搜索工具或直接抓取了足够页面，而不是只给理论方案
- 每个重点推荐仓库至少有一种 README 证据和一种附加证据
- 已明确区分精确匹配、邻近相关和噪音结果
- 最终答案能说明“为什么这些仓库值得看”
