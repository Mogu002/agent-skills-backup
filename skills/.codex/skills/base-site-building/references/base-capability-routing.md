# 原生 Base 能力发现与路由

当 `base-site-building` 无法确认某项功能时，使用本流程查询飞书多维表格本体能力。不要从 Base Site 文档未提及、Catalog 未展示或记忆中的旧版 CLI 推导“不支持”。

## 触发条件

能力归属无法确认时，在以下动作之前强制执行能力发现：

- 选择 Page、SQL Function、FaaS 或原生 Base 的实现归属；
- 删除、简化或降级一项用户需求；
- 声称多维表格、Base Site 或 `lark-cli` 不支持某项能力；
- 用 FaaS 模拟定时触发、记录变化触发、提醒、通知、权限控制等 Base 本体行为。

## 查询顺序

1. 把需求改写成一个能力动词和目标资源，例如“记录创建后通知人员字段中的用户”“按角色限制字段编辑”“提交公开表单”。
2. 运行 `lark-cli base --help`，从当前安装版本的 shortcut 列表查找相关资源；不要依赖旧版命令记忆。
3. 对候选命令运行 `lark-cli base +<shortcut> --help`，确认它支持 list/get/create/update/enable 等哪些动作、需要哪些 ID 和 JSON。
4. 已有 Base 先解析真实 `base_token`，再用只读命令确认资源和现状。优先从 `+base-block-list` 看 Base 内资源，再进入对应的 list/get；表、字段、视图和其他资源 ID 必须来自真实返回。
5. 当前环境提供 `lark-base` Skill 时，读取其快速路由和对应 reference 后再构造复杂 JSON。不得猜 workflow steps、dashboard data config、role config、字段或记录 CellValue。

最小发现命令：

```bash
lark-cli base --help
lark-cli base +base-block-list --help
lark-cli base +<candidate-shortcut> --help
```

已有 Base 的只读查询显式使用用户身份：

```bash
lark-cli base +url-resolve --url '<base-url>' --as user
lark-cli base +base-block-list --base-token '<base-token>' --as user
lark-cli base +<resource-list-or-get> ... --as user
```

## 能力路由

| 需求类别 | 优先检查的原生 Base 路由 |
| --- | --- |
| Base、表、字段、记录 | `+base-*`、`+table-*`、`+field-*`、`+record-*` |
| 查询、统计、派生值 | `+record-list`、`+record-search`、`+data-query`、`+field-create` / `+field-update` 的 formula 或 lookup |
| 视图与筛选展示 | `+view-*` |
| 表单与题目 | `+form-*`、`+form-questions-*` |
| 图表与仪表盘 | `+dashboard-*`、`+dashboard-block-*` |
| 定时、记录触发、提醒、通知 | `+workflow-*` |
| 角色与数据权限 | `+role-*`、`+advperm-*` |

这张表只用于定位候选命令，不代替当前 CLI 的 `--help`、目标资源的真实返回或 `lark-base` reference。

## 决策与实施

查询完成后只选择以下一种结论：

1. **原生 Base 实现**：能力由多维表格本体提供。通过 `lark-cli base +...` 配置，Site 只提供需要的交互页面。
2. **Base Site 实现**：能力属于页面交互、SQL 读取或由 Page 主动发起的即时业务写入，按 Page/SQL/FaaS 边界实现。
3. **组合实现**：例如 Page/FaaS 创建记录，原生 workflow 监听记录并通知；分别配置并独立验收两段链路。
4. **已证实的缺口或阻塞**：找不到当前 CLI 入口、命令明确不支持，或遇到权限或环境阻塞。准确描述为“当前 `lark-cli` 未暴露”“原生能力明确不支持”或“当前身份无权限”，不要互相替代。

组合实现中的通知必须保持入口意图一致。创建 workflow 前逐个把 `LarkMessageAction` 归入以下一种策略：

| 入口策略 | 适用场景 | 必须满足 |
| --- | --- | --- |
| `site_action` | 除下列两个明确授权场景外，所有与 Site 业务对象关联的通知 | Page 先实现真实功能路由；通知提供显式 `openLink`，使用发布返回的 `appUrl`、该路由和最小稳定对象标识 |
| `informational` | 用户明确要求通知纯展示、无需任何点击入口 | `btn_list=[]`；记录用户原文，并披露原生通知仍可能沿平台默认行为跳转 Base |
| `base_action` | 用户明确要求从通知进入多维表格 | 只在该明确要求下使用 Base `recordLink` 或 Base URL，不得描述成 Site 入口 |

不得因为通知正文已经包含业务信息或用户未指定跳转目标，就推断为 `informational`。访客登记后通知被访人固定属于 `site_action`：Page 必须提供当前登记详情路由，消息按钮必须进入该路由；即使通知正文已包含访客姓名、公司和来访事由也不例外。`lark-base` workflow 文档里的 `$.<trigger>.recordLink` 是通用 Base 记录链接示例，不适用于 `site_action`。此类 `LarkMessageAction.data.btn_list[].btn_action=openLink` 必须进入与通知动作对应、由 Page 已实现的站内功能路由，并通过路径或查询参数携带直接定位目标业务对象所需的最小稳定标识。例如考试发布通知应进入该考试的详情或答题路由，而不是 Site 首页。`base-site deploy` 原样返回的 `appUrl` 只作为当前环境的可信基址；不得指向 `recordLink`、Base URL、Site `managementUrl`，也不得根据 Site token 自行拼接 Preview/Prod 地址。

`btn_list=[]` 只说明没有显式按钮，不代表原生通知不可点击，也不能证明通知整卡不会沿平台默认行为跳转 Base。当前暴露的 workflow 配置没有关闭该默认入口的字段。用户要求任何点击都不得进入 Base 时，原生 `LarkMessageAction` 不能直接视为满足要求；继续执行能力发现，若找不到可完全控制链接的通知方案，则记录为平台阻塞，不能用 `informational` 绕过要求。

新 `site_action` workflow 在 Preview 发布前不创建。Preview 发布后基于返回的真实 `appUrl`、代码中已经存在的功能路由和 workflow 上下文中的对象标识，一次性构造最终按钮链接，直接执行 `+workflow-create`、`+workflow-enable` 和 `+workflow-get`。只有修改已有 workflow 时才先读取完整定义，只替换按钮链接，再执行全量 `+workflow-update` 和回读。不得发明页面未实现的路径，也不得使用裸 `appUrl`。Prod 发布不会触发 Base workflow 自动迁移；发布后必须按记录逐个更新已有 workflow，只替换为生产 `appUrl`，保留功能路由、动态对象参数、其他步骤和启用状态。

能力发现默认只读。新建系统中，用户要求的非破坏性原生 Base 配置属于建站范围，可在 `init` 返回真实 Base token 后执行；基于已有 Base 时，创建或修改原生配置前先确认它在用户授权的修改范围内。删除资源、关闭 workflow、关闭高级权限或改变已有角色权限前必须取得明确授权。

复杂 create/update 必须遵守对应 shortcut 的 `--help` 和 `lark-base` reference。更新要求完整配置时先 get，再 read-modify-write；支持 delta update 时提交最小合法 payload。完成写入后使用 list/get 回读，workflow 等有启停状态的资源还要核对实际状态。Site 通知要逐个回读 `LarkMessageAction`：`site_action` 核对每个业务 `openLink` 最终使用当前发布环境的平台返回 `appUrl` 作为基址，并指向通知对应的真实功能路由及目标对象，而不是 Site 首页、Base 或管理后台；`informational` 和 `base_action` 分别核对存在用户明确要求纯展示或进入多维表格的原文。任一链接、对象标识、入口策略或回读不一致时立即执行 `+workflow-disable`，并把交付标记为 partial 或 blocked；不得把 Site 发布成功等同于整体交付完成。Prod 阶段还要确认 Site 链接不再含 Preview 基址。

## 交付证据

交付时把原生 Base 配置纳入资源和验收清单，至少报告资源类型、名称、真实 ID、启用状态和它与 Site 的衔接点。若记录缺口，附上实际查询过的命令、当前 CLI 版本或帮助输出结论，以及阻塞属于平台、CLI 覆盖还是权限；不得只写“Skill 没提到”或“没找到”。
