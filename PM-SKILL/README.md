# PM-SKILL

按产品经理的工作场景整理的技能索引，覆盖产品立项、原型交付、实验策略和协作工具。清单共 22 项，其中 11 项收录了可公开分发的上游文件，2 项收录了 GStack 的公开同名版本，9 项因未核实公开分发许可，仅列用途。

使用时打开所需技能的 `SKILL.md`。Agent Browser、Lark CLI 和 GStack 等技能依赖上游运行时或账号权限，安装方式见各自的上游项目。

## 探索想法

| 技能 | 什么时候用 | 本目录 |
| --- | --- | --- |
| Office Hours | 立项前验证用户痛点、现有替代方案与需求证据，找出值得先验证的最小切口。 | [GStack 公开同名版](gstack/office-hours/SKILL.md) |
| Plan CEO Review | 从负责人视角复审已有方案，评估用户价值与投入，判断该扩大、维持还是缩小范围。 | [GStack 公开同名版](gstack/plan-ceo-review/SKILL.md) |
| UG PRD Review | 预审增长激励 PRD，发现成本、收益、用户反馈和实验归因风险。 | 仅列用途 |
| Storyline | 为立项、汇报或提案梳理背景、目标与论证顺序，也可诊断已有文档的叙事。 | 仅列用途 |
| Guizang PPT Skill | 用杂志式或瑞士国际主义版式生成单文件 HTML 演示稿，适合立项答辩和产品介绍。 | [归藏 PPT](guizang-ppt-skill/SKILL.md) |

## 需求实现

| 技能 | 什么时候用 | 本目录 |
| --- | --- | --- |
| Brainstorming | 实现前逐步澄清需求和约束、比较可选方案，并形成供确认的设计。 | [Superpowers / Brainstorming](superpowers/skills/brainstorming/SKILL.md) |
| UI UX Pro Max | 为页面或应用选择视觉风格、配色、字体与布局，并获取适合所用技术栈的设计建议。 | [UI UX Pro Max](ui-ux-pro-max/SKILL.md) |
| Impeccable | 评审并打磨界面的视觉层级、信息架构、响应式布局、可访问性和动效。 | [Impeccable](impeccable/SKILL.md) |
| GSAP Skills | 用 GSAP 实现时间轴、滚动联动和组件动效，以及优化动画性能。 | [GSAP 技能集](gsap-skills/skills/) |
| Agent Browser | 自动打开、操作和截图网页，验证表单、交互流程和产品 Demo。 | [Agent Browser](agent-browser/SKILL.md) |

## 数据与实验

| 技能 | 什么时候用 | 本目录 |
| --- | --- | --- |
| ByteDance Aeolus | 查询 BI 数据集和看板、执行 SQL，或维护常用数据查询。 | 仅列用途 |
| ByteDance TEA | 查看事件元数据、分析用户行为路径，或查询和创建行为分析报表。 | 仅列用途 |
| ByteDance Libra | 管理 A/B 实验从创建到关闭的流程，查看指标与显著性。 | 仅列用途 |
| UG Num Strategy | 在预算和收益约束下设计激励门槛、奖励分配、成本模型与验证实验。 | 仅列用途 |
| AB Test Setup | 明确实验假设、变量、主指标、样本量和运行时长，形成可执行的 A/B 测试方案。 | [AB Test Setup](ab-test-setup/SKILL.md) |
| Experiment UX Guard | 在实验或灰度发布前排查体验差异、公平性感知和分批放量风险。 | 仅列用途 |

## 插件与基础工具

| 技能或工具 | 什么时候用 | 本目录 |
| --- | --- | --- |
| Product Proposal Agent | 把产品想法或零散材料加工成完整提案，覆盖需求澄清、评审和演示稿。 | 仅列用途 |
| Superpowers | 按阶段推进软件开发，覆盖设计、执行计划、测试、调试、代码审查与交付核验。 | [Superpowers 技能集](superpowers/skills/) |
| ByteDance Auth | 为需要访问内部数据平台的工具管理登录状态和认证。 | 仅列用途 |
| Lark CLI | 让 Agent 通过飞书 CLI 操作文档、多维表格、消息、任务、日历等协作资源。 | [飞书 CLI 技能集](lark-cli/skills/) |
| Find Skills | 按任务查找开放生态中的 Agent Skill，并安装选中的技能。 | [Find Skills](find-skills/SKILL.md) |
| Skill Creator | 从零编写或迭代 Skill，用评测和基准对比检查效果，并优化触发描述。 | [Skill Creator](skill-creator/SKILL.md) |

## 技能集子项

### GSAP Skills

| 技能 | 用途 |
| --- | --- |
| [gsap-core](gsap-skills/skills/gsap-core/SKILL.md) | 使用 tween、缓动、回调和动画控制 API。 |
| [gsap-frameworks](gsap-skills/skills/gsap-frameworks/SKILL.md) | 将 GSAP 接入前端框架，在生命周期内管理动画。 |
| [gsap-performance](gsap-skills/skills/gsap-performance/SKILL.md) | 降低动画的布局与渲染开销，处理响应式和减少动态效果的偏好。 |
| [gsap-plugins](gsap-skills/skills/gsap-plugins/SKILL.md) | 按目标效果选择并注册 GSAP 插件。 |
| [gsap-react](gsap-skills/skills/gsap-react/SKILL.md) | 用 `useGSAP` 在 React 组件中组织动画和清理逻辑。 |
| [gsap-scrolltrigger](gsap-skills/skills/gsap-scrolltrigger/SKILL.md) | 实现滚动触发、进度联动和固定区块。 |
| [gsap-timeline](gsap-skills/skills/gsap-timeline/SKILL.md) | 编排多个动画的顺序、重叠与标签位置。 |
| [gsap-utils](gsap-skills/skills/gsap-utils/SKILL.md) | 使用映射、插值、取整和循环等工具函数。 |

### Superpowers

| 技能 | 用途 |
| --- | --- |
| [brainstorming](superpowers/skills/brainstorming/SKILL.md) | 澄清需求、比较方案并确认设计。 |
| [diagnosing-superpowers](superpowers/skills/diagnosing-superpowers/SKILL.md) | 诊断插件安装、技能发现或工作流触发问题。 |
| [dispatching-parallel-agents](superpowers/skills/dispatching-parallel-agents/SKILL.md) | 让多个 Agent 并行处理相互独立的任务。 |
| [executing-plans](superpowers/skills/executing-plans/SKILL.md) | 按现有计划推进实现，并在检查点复核结果。 |
| [finishing-a-development-branch](superpowers/skills/finishing-a-development-branch/SKILL.md) | 在开发结束后核验测试并处理分支集成或清理。 |
| [receiving-code-review](superpowers/skills/receiving-code-review/SKILL.md) | 核实审查意见后决定并落实修正。 |
| [requesting-code-review](superpowers/skills/requesting-code-review/SKILL.md) | 在交付前发起代码审查并提供变更上下文。 |
| [subagent-driven-development](superpowers/skills/subagent-driven-development/SKILL.md) | 按计划逐项委派实现，并复核规格与代码质量。 |
| [systematic-debugging](superpowers/skills/systematic-debugging/SKILL.md) | 通过证据和可复现步骤定位故障根因。 |
| [test-driven-development](superpowers/skills/test-driven-development/SKILL.md) | 先用失败测试表达预期，再实现并重构。 |
| [using-git-worktrees](superpowers/skills/using-git-worktrees/SKILL.md) | 用 Git worktree 创建隔离的开发目录。 |
| [using-superpowers](superpowers/skills/using-superpowers/SKILL.md) | 识别当前任务应启用的 Superpowers 技能。 |
| [verification-before-completion](superpowers/skills/verification-before-completion/SKILL.md) | 在汇报完成前用最新测试和检查结果验证交付。 |
| [writing-plans](superpowers/skills/writing-plans/SKILL.md) | 把设计拆成包含文件、步骤和验收方式的实现计划。 |
| [writing-skills](superpowers/skills/writing-skills/SKILL.md) | 编写、更新并验证可复用的 Agent 技能。 |

### Lark CLI

| 技能 | 用途 |
| --- | --- |
| [lark-approval](lark-cli/skills/lark-approval/SKILL.md) | 查询、发起和处理审批。 |
| [lark-apps](lark-cli/skills/lark-apps/SKILL.md) | 开发、部署和管理飞书妙搭应用。 |
| [lark-attendance](lark-cli/skills/lark-attendance/SKILL.md) | 查询个人考勤打卡记录。 |
| [lark-base](lark-cli/skills/lark-base/SKILL.md) | 管理多维表格的数据、视图、表单和工作流。 |
| [lark-calendar](lark-cli/skills/lark-calendar/SKILL.md) | 查询空闲时间、排日程和预订会议室。 |
| [lark-contact](lark-cli/skills/lark-contact/SKILL.md) | 查询通讯录人员及其标识。 |
| [lark-doc](lark-cli/skills/lark-doc/SKILL.md) | 读取、创建和编辑飞书云文档。 |
| [lark-drive](lark-cli/skills/lark-drive/SKILL.md) | 管理云盘文件、文件夹、权限及文档导入导出。 |
| [lark-event](lark-cli/skills/lark-event/SKILL.md) | 订阅并消费飞书实时事件。 |
| [lark-im](lark-cli/skills/lark-im/SKILL.md) | 搜索、收发消息以及管理群聊。 |
| [lark-mail](lark-cli/skills/lark-mail/SKILL.md) | 搜索、撰写和管理飞书邮件。 |
| [lark-markdown](lark-cli/skills/lark-markdown/SKILL.md) | 创建、编辑、上传和比较 Markdown 文件。 |
| [lark-meeting](lark-cli/skills/lark-meeting/SKILL.md) | 查询历史会议及会议纪要、妙记等产物。 |
| [lark-note](lark-cli/skills/lark-note/SKILL.md) | 按会议纪要 ID 查询纪要详情与原始记录。 |
| [lark-okr](lark-cli/skills/lark-okr/SKILL.md) | 管理目标、关键结果与进展。 |
| [lark-openapi-explorer](lark-cli/skills/lark-openapi-explorer/SKILL.md) | 查找并调用 CLI 尚未封装的飞书 OpenAPI。 |
| [lark-shared](lark-cli/skills/lark-shared/SKILL.md) | 配置 CLI、管理登录与账号权限。 |
| [lark-sheets](lark-cli/skills/lark-sheets/SKILL.md) | 读取和编辑电子表格、公式、格式与图表。 |
| [lark-skill-maker](lark-cli/skills/lark-skill-maker/SKILL.md) | 将飞书 CLI 操作或流程封装为自定义技能。 |
| [lark-slides](lark-cli/skills/lark-slides/SKILL.md) | 创建和编辑飞书幻灯片。 |
| [lark-task](lark-cli/skills/lark-task/SKILL.md) | 管理待办、清单、协作者和任务进度。 |
| [lark-whiteboard](lark-cli/skills/lark-whiteboard/SKILL.md) | 读取、导出和更新飞书画板。 |
| [lark-wiki](lark-cli/skills/lark-wiki/SKILL.md) | 管理知识空间、页面节点和文档层级。 |
| [lark-workflow-meeting-summary](lark-cli/skills/lark-workflow-meeting-summary/SKILL.md) | 将一段时间内的会议纪要汇总为报告。 |
| [lark-workflow-standup-report](lark-cli/skills/lark-workflow-standup-report/SKILL.md) | 汇总指定日期的日程和未完成待办。 |

## 上游版本与许可

Office Hours 和 Plan CEO Review 使用 GStack 的公开同名版本，与清单里介绍的中文版关系未核实。AB Test Setup 保留上游改名为 `ab-testing` 前的版本。Brainstorming 随 Superpowers 收录，两个条目共用同一份文件。

| 本目录 | 固定的上游提交 | 许可 |
| --- | --- | --- |
| [`gstack/`](gstack/) | [garrytan/gstack@`8143a91809b2`](https://github.com/garrytan/gstack/tree/8143a91809b2305da6ffa7486923008b72d337e6) | MIT |
| [`guizang-ppt-skill/`](guizang-ppt-skill/) | [op7418/guizang-ppt-skill@`93d21bf4a73a`](https://github.com/op7418/guizang-ppt-skill/tree/93d21bf4a73a851907a6eb00acbf30618236667a) | AGPL-3.0 |
| [`superpowers/`](superpowers/) | [obra/superpowers@`22f0b463e7a5`](https://github.com/obra/superpowers/tree/22f0b463e7a5e579904dd6211a520321035526f7) | MIT |
| [`ui-ux-pro-max/`](ui-ux-pro-max/) | [nextlevelbuilder/ui-ux-pro-max-skill@`281e4537afb1`](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/281e4537afb11333ac9947783779aaf314ebfbf2) | MIT |
| [`impeccable/`](impeccable/) | [pbakaus/impeccable@`b49177d32788`](https://github.com/pbakaus/impeccable/tree/b49177d32788f2dc585c42831d845dacf1ebed2c) | Apache-2.0 |
| [`gsap-skills/`](gsap-skills/) | [greensock/gsap-skills@`aed9cfd32777`](https://github.com/greensock/gsap-skills/tree/aed9cfd3277740755f6bfc1155c7aa645403b760) | MIT |
| [`agent-browser/`](agent-browser/) | [vercel-labs/agent-browser@`d2dfc782ccdd`](https://github.com/vercel-labs/agent-browser/tree/d2dfc782ccdd79d25a9b4f0acced9321789cecb8) | Apache-2.0 |
| [`ab-test-setup/`](ab-test-setup/) | [coreyhaines31/marketingskills@`f3990f7f99ae`](https://github.com/coreyhaines31/marketingskills/tree/f3990f7f99ae63b9e26eaa61114f60e0408742ff) | MIT |
| [`lark-cli/`](lark-cli/) | [larksuite/cli@`c5fbf1a52df7`](https://github.com/larksuite/cli/tree/c5fbf1a52df77d5cb9cac2b1501770b2fb9af7d2) | MIT |
| [`find-skills/`](find-skills/) | [vercel-labs/skills@`57217cf86ba3`](https://github.com/vercel-labs/skills/tree/57217cf86ba38148a57af9e90d14a4c049558330) | MIT |
| [`skill-creator/`](skill-creator/) | [anthropics/skills@`e4bb5d960d87`](https://github.com/anthropics/skills/tree/e4bb5d960d87126ff3b3a8af1a104b7db67560ba) | Apache-2.0 |
