---
name: base-site-building
description: 当用户希望以飞书多维表格为业务数据后端，从零或基于已有 Base 搭建、修改、发布、验收或排查完整 Base Site 业务系统时使用。通过 lark-cli 建模、读取和查询原生 Base 能力，并实现 Catalog、Base SQL、FaaS、Page 和发布链路；无法确认某项能力时也必须使用本 Skill 先完成能力发现。
---

# Base Site Building

把业务需求转成可维护、可验证、可上线的 Base Site。Site 资源与发布统一使用 `npx @lark-base-open/base-site-cli`；原生多维表格能力的发现与配置使用 `lark-cli base +...`。本 Skill 提供从需求建模到发布交付的完整主流程。

## 开始任务

- **新建系统**：自动判定 Base 来源，不向用户展示来源选择题。Prompt 未明确指定已有 Base 时默认从零创建；明确指定已有 Base 时复用该 Base。随后按本文 1～6 步执行。
- **修改系统**：先一次性获取 Site、binding、Catalog、源码和发布状态，再执行受影响阶段；保留需求外内容和用户未提交修改。
- **设计或评审**：读取 [风格手册](references/style-guide.md)，只分析和输出，不创建资源或发布。

新建系统时，开始先一次性完整读取本文、[代码开发手册](references/development.md)、[风格手册](references/style-guide.md)、[SQL Function 专项](references/sql-function.md) 和 [发布与验收](references/release.md)。需求包含本文无法确认、或不明显属于 Page/SQL/FaaS 的能力时，还必须读取[原生 Base 能力发现与路由](references/base-capability-routing.md)。默认从零设计 Base schema；只有 Prompt 明确指定已有 Base 时，才取得其 Base token 并由 `init` 读取全部表。随后都以 Site Catalog 为准执行开发。

正常开发只使用 SQL Function 专项明确列出的支持集。需要判断支持集之外的 SQL 语法是否可用、评审或排查 SQL，或者处理 SQL 编译与运行兼容失败时，再完整读取 [Base SQL 不支持能力](references/base-sql-unsupported.md)。

正常新建系统只执行一次 `init` 和一次 `deploy`。`init --schema` 负责创建 Base 和全部表；`init --base-token` 只读已有 Base，不创建或修改表。两种入口都会创建新 Site、在创建请求中绑定全部目标表、获取 Catalog 并生成 starter。`deploy` 负责依赖安装、production build、归档、SQL 编译校验、Functions 更新、Artifact 上传、源码回读、Preview 发布和状态轮询。项目级 `base-site-cli lark-cli -- ...` 只用于排查 Site 控制面请求；原生 Base 能力发现和配置直接使用 `lark-cli base +...`，不受此限制。

每个阶段先完整获取所需上下文，再连续完成该阶段。实现每个 Page/FaaS operation 前，先在内部规划中列出远程调用、每个调用的已知输入和响应依赖，不额外创建设计文件。能在一个 SQL Function 内完成的关联读取先合并；输入已经确定且无响应依赖的读取或请求同时启动，只在业务正确性、平台顺序或后一步确实需要前一步响应时串行。

## 无法确认能力时的强制路由

不要因为本文、Base Site CLI 或现有 Catalog 没有描述某项能力，就直接判断“多维表格不支持”或把需求降级。遇到以下任一情况，先执行[原生 Base 能力发现与路由](references/base-capability-routing.md)：

- 无法确认需求应由 Page、SQL Function、FaaS 还是原生 Base 实现；
- 需求涉及表和字段以外的能力，如视图、表单、仪表盘、工作流、提醒、通知、角色或高级权限；
- 准备把某项需求标记为不支持、能力缺口或本期无法实现；
- Base Site 的文档、CLI 或运行时没有对应入口，但该需求可能属于多维表格本体。

能力查询使用 `lark-cli base --help`、对应 shortcut 的 `--help`，以及目标 Base 的只读 list/get 命令；当前环境提供 `lark-base` Skill 时同时读取并遵守它。查询后按证据选择实现归属：原生 Base 已支持则通过 `lark-cli base +...` 配置；Base Site 已支持则使用 Page/SQL/FaaS；两边各承担一部分时组合实现。只有完成查询仍无法找到入口，才能记录缺口，并区分“原生能力不支持”“当前 lark-cli 未暴露该能力”和“权限或环境阻塞”，附上实际查询过的命令与结果。

## 平台不变量

1. 只使用 `online` 环境。初始化显式传入 `--env online`；CLI、OpenAPI、Accounts、Site 管理后台和 Page 运行时都直接使用线上域名，并始终使用 `--as user` 身份。
2. 新建顺序固定为自动判定 Base 来源 → 默认从零设计完整 schema，或按 Prompt 明确指定的已有 Base 取得 token → CLI `init` → 读取 Catalog 并结合用户需求开发 → CLI `deploy` Preview → 交给用户体验并停止。用户确认效果后回复“部署正式版”，再执行 CLI `deploy --production --yes`。
3. 优先缩短用户首次体验时间。代码完成后尽快发布 Preview 并交给用户体验，以用户反馈驱动后续迭代。
4. Base 是业务事实源，`catalog.json` 是已绑定表的 schema 事实源。表名、字段名、ID、类型和选项以 Catalog 为准。
5. Base 读取使用 SQL Function；由 Page 主动发起的创建、更新和删除，通过 FaaS 调用目标环境的 Site 写入接口。Page 和 FaaS 均不传 Base token，禁止直接调用 Base OpenAPI。环境地址、鉴权机制及完整请求和响应协议见[代码开发手册](references/development.md#site-records-写入协议)。
6. Page 和 FaaS 只调用固定 operation。用户输入不能决定 SQL、URL、method、Base token、table ID、字段名、Function ID 或平台凭证。
7. Functions 更新是全量覆盖。修改已有 Site 时保留需求外 Function；删除 Base、表、字段、Function、binding 或 Site 前获得用户明确授权。
8. Preview 是常规发布的强制前置流程。发布成功后展示 Preview URL、Base URL 和限制，立即停止，不使用浏览器或 Function 直调代替用户体验。只有用户体验后明确回复“部署正式版”，才发布 Prod。
9. 浏览器 SDK 的 `invokeFunction<TData>` 对 SQL 和 FaaS 都只返回一层 `{data,code,msg}`；`TData` 只描述当前 operation 约定的顶层 `data`，不得套入 FaaS handler 的返回类型或二次解包。
10. FaaS 写入先确定一致性、部分成功和重试语义，再按已确认的业务要求设计最短远程调用链；不通过堆叠请求模拟 Base 不具备的事务能力。
11. FaaS 下游失败使用稳定业务码和 `data.errors` 白名单诊断分层返回；保留安全的上游 `code`、`msg`、LogID 和失败步骤，不透传完整请求、响应、headers、stack 或凭证。具体协议见[代码开发手册](references/development.md#下游错误归一化)。
12. 新建 Site 必须提供非空 `description`。优先使用用户原文；用户未提供时，根据已确认需求生成一句客观描述，概括使用对象和核心用途，不写营销口号、实现细节、目标环境或 Preview/Prod 发布状态。
13. 创建或修改 Page 时，必须保留 starter 中的 `createArgusCsrfPlugin()` 配置；不得复制插件实现或手写 `x-secsdk-csrf-token`。旧 Site 需升级 JSSDK 并重新构建发布。
14. 原生 workflow 为本 Site 发送通知时，按固定优先级确定每个 `LarkMessageAction` 的入口策略：用户明确要求进入多维表格时使用 `base_action`；用户明确要求通知纯展示、无需任何点击入口时才使用 `informational`；其他所有与 Site 业务对象关联的通知一律使用 `site_action`。不得因为通知正文已包含业务信息、用户未指定跳转目标或原生 workflow 更容易跳 Base，就推断为 `informational`。访客登记后通知被访人属于 `site_action`，即使正文已包含访客姓名、公司和来访事由，也必须提供进入当前访客登记详情的显式入口。`site_action` 必须提供显式 `openLink` 按钮，指向与通知业务动作对应的 Site 站内功能路由，并使用 workflow 上下文中的最小稳定标识直接定位目标对象；Page 必须先实现该路由，考试通知同理进入对应考试或答题页，而不是 Site 首页。平台发布结果原样返回的 `appUrl` 只作为当前环境的可信 Site 基址；禁止把裸 `appUrl` 作为按钮链接，禁止使用 Base `recordLink`、Base URL、Site 管理后台 `managementUrl` 或根据 Site token 猜测的地址。新 workflow 延后到 Preview 发布成功后创建，取得真实 `preview.appUrl` 后直接在 `+workflow-create` 中写入最终 Site 链接，再执行 `+workflow-enable` 和 `+workflow-get`；只有修改已有 workflow 才执行 `+workflow-get` → 完整 read-modify-write `+workflow-update` → `+workflow-enable` → `+workflow-get`。`informational` 可以使用 `btn_list=[]`，但必须记录用户明确要求纯展示的原文；空按钮不代表通知不可点击，也不能证明它不会沿平台默认行为跳转 Base。任一 Site 路由、对象标识、最终链接或回读不满足约束时，立即执行 `+workflow-disable`，并把交付标记为 partial 或 blocked；不得降级成 `informational` 或宣称通知完成。CLI 发布 Site 不会自动修改 Base workflow；Preview 和 Prod 每次发布后都必须显式完成对应环境的通知入口收尾。

## 1. 理解需求并判定 Base 来源

明确 Site 名称、Site 描述、用户角色、核心对象、对象关系、状态流转、页面任务和一条可验收的端到端路径。Site 描述用一句话概括使用对象和核心用途；通常只使用一个 Base。

不要询问用户选择数据来源，也不要展示“从零创建”与“使用已有 Base”的选项。按 Prompt 自动路由：

- **默认从零创建 Base**：Prompt 未明确指定已有 Base 时，直接根据需求设计完整 schema，每类核心对象一张表，再执行 `init --schema`。用户描述需要哪些业务表或字段属于建模需求，不代表存在已有 Base。
- **使用已有 Base**：仅当 Prompt 明确提供 Base token、Base 链接，或明确要求基于某个已有 Base 搭建时进入该路径。优先从 Prompt 解析 token；若明确指定了已有 Base 但无法取得 token，只补问 Base token，不再询问来源选择。随后执行 `init --base-token`。`init` 会只读列出该 Base 的全部表、创建并绑定新 Site、获取 Catalog；不得先复制 Base，也不得在初始化阶段创建、删除或修改已有表和字段。

已有 Base 路径不根据 prompt 猜测字段，默认将该 Base 的全部表绑定到新 Site；绑定全部表不代表页面需要暴露全部数据。初始化后先把 `catalog.json` 与用户需求逐项映射，确定需求实际使用的表、字段、关系和选项，再设计相应的页面与 operation。若 Catalog 缺少完成需求所必需的数据结构，先向用户说明缺口并取得修改 Base 的明确授权；未授权时按现有 Catalog 实现可支持范围。

例如 Todo 系统：

```text
Site 名称：Todo 管理
Site 描述：供个人集中创建、跟踪和完成日常任务
对象：任务
状态：待处理 → 进行中 → 已完成
页面：任务列表、创建任务、任务详情
查询：listTasks、getTask
写入：createTask、updateTaskStatus
验收：创建任务 → SQL 查到记录 → 更新状态 → SQL 查到新状态
```

常用 Field JSON：

| 业务数据         | Field JSON                                                                       |
| ---------------- | -------------------------------------------------------------------------------- |
| 标题、备注、电话 | `{"type":"text","name":"标题"}`                                                  |
| 数量、金额       | `{"type":"number","name":"金额"}`                                                |
| 单选状态         | `{"type":"select","name":"状态","multiple":false,"options":[{"name":"待处理"}]}` |
| 多标签           | `{"type":"select","name":"标签","multiple":true,"options":[{"name":"高优"}]}`    |
| 日期时间         | `{"type":"datetime","name":"截止时间","style":{"format":"yyyy-MM-dd HH:mm"}}`    |
| 布尔值           | `{"type":"checkbox","name":"已完成"}`                                            |
| 表间关系         | `{"type":"link","name":"关联任务","link_table":"任务"}`                          |
| 审计字段         | `created_at`、`updated_at`、`created_by`、`updated_by`                           |
| 附件             | `{"type":"attachment","name":"附件"}`；Base Site 暂不支持上传                    |

`datetime.style.format` 使用 Base 支持的固定枚举；当前可配置格式最多显示到分钟，底层时间值仍可保留秒级精度。

首个字段是表的主字段。公式和 lookup 是只读派生字段，只在结果需要长期展示在 Base 时使用。

## 2. 初始化 Base 与 Site

### 从零创建 Base

把全部表写入一个 schema 文件。这个文件是 `init` 的输入，不是平台请求缓存：

```json
{
  "tables": [
    {
      "name": "任务",
      "fields": [
        { "type": "text", "name": "任务名称" },
        {
          "type": "select",
          "name": "状态",
          "multiple": false,
          "options": [
            { "name": "待处理" },
            { "name": "进行中" },
            { "name": "已完成" }
          ]
        },
        {
          "type": "datetime",
          "name": "截止时间",
          "style": { "format": "yyyy-MM-dd HH:mm" }
        },
        { "type": "text", "name": "备注" }
      ]
    }
  ]
}
```

在项目目录执行初始化命令：

```bash
npx @lark-base-open/base-site-cli init . \
  --env online \
  --name 'Todo 管理' \
  --description '供个人集中创建、跟踪和完成日常任务' \
  --schema ./base-schema.json
```

### 使用已有 Base

取得已有 Base 的 `bas...` token 后执行：

```bash
npx @lark-base-open/base-site-cli init . \
  --env online \
  --name 'Todo 管理' \
  --description '供个人集中创建、跟踪和完成日常任务' \
  --base-token basxxxxxxxx
```

该命令调用只读 Base 接口获取 Base 信息并分页列出全部表，然后通过 Site 创建接口的 `baseBindings` 直接绑定这些表，最后从新 Site 获取 Catalog。它不会创建或修改 Base、表、字段和记录。

两种路径必须且只能传入 `--schema` 或 `--base-token` 之一，并始终传入非空 `--description`。`--env` 默认且只支持 `online`。从零路径连续建表会串行等待 2 秒。

成功结果的 `baseSource` 为 `created` 或 `existing`；新建 Base 位于 `created.base`，已有 Base 位于 `reused.base`，同时列出表、新建的 Site、binding 和工程文件。开始开发前确认以下产物：

```text
base-site.jsonc      # Site token 与 Base binding
base-schema.json     # 仅从零路径存在，是本次建库输入
catalog.json         # 已绑定数据表的真实 schema
page/                # React 页面
sql/                 # SQL Functions
server-functions/    # 服务端 FaaS Functions
.base-site-cli/      # 被 Git 忽略的 CLI 本地状态与临时制品
```

只从 `catalog.json` 读取表名、字段名、ID、选项和 SQL 类型，不根据建表输入猜测 Catalog 结果。

### Site 控制面调试

正常建站不直接调用项目级 `base-site-cli lark-cli -- ...`。仅排查 Site 控制面接口、授权或 LogID 时，进入包含 `base-site.jsonc` 的项目根目录执行：

```bash
npx @lark-base-open/base-site-cli lark-cli -- \
  api GET /open-apis/base/v3/sites/list \
  --params '{"pageSize":1}' --json
```

该命令校验当前目录的项目配置，并在线上环境原样运行后续参数；`api` 和 `base` 命令自动使用 `--as user`。它不是原生 Base 业务能力的唯一入口；能力发现与配置按[原生 Base 能力发现与路由](references/base-capability-routing.md)直接执行 `lark-cli base +...`。

## 3. 开发

读取 `catalog.json` 和 starter 源码，确定 operation 的固定输入与输出，然后在 `sql/`、`server-functions/` 和 `page/` 中完整实现 SQL、服务端 FaaS Functions 和 Page；不创建额外的 operation 设计文件。保持以下边界：

- Page 读取 Base 使用 SQL Function；
- Page 写入使用 FaaS；
- SQL 和 FaaS 调用都使用 `params`，但 SQL 是按 `$1`、`$2` 排列的数组，FaaS 是传给 handler `rawParams` 的业务对象；
- 页面不直接调用 Base records OpenAPI；
- 附件上传暂不支持，相关需求明确记录为平台限制。

实现代码前，对每个首屏加载和用户动作做一次远程调用拓扑检查：

1. 列出 SQL Function、FaaS Function、`context.fetch` 和写入 OpenAPI 调用，并标记每个调用在 operation 开始时已经具备的输入。
2. 如果后一个 SQL 的参数只是前一个 SQL 返回的关联 ID，先把关系下推到同一个 SQL Function；这种数据库内部关系不是保留两次远程调用的理由。
3. 如果多个无副作用读取的输入均已确定，先创建全部 Promise，再在共同消费结果的位置一次 `await Promise.all(...)`；不要按代码书写顺序连续等待。
4. 只有按需加载、权限或失败语义隔离、结果规模明显放大、SQL 方言无法表达，或后一步确实依赖前一步业务判断时才拆分，并在实现或交付说明中记录原因。

代码完成后直接进入 Preview 发布；依赖安装、production build 和服务端 SQL 校验由 `deploy` 统一执行。

## 4. 发布 Preview

在包含 `base-site.jsonc` 的目录执行唯一的发布命令：

```bash
npx @lark-base-open/base-site-cli deploy
```

`deploy` 通常需要约 30 秒到 1 分钟，中间不显示阶段进度。等待该命令返回最终结果；依赖安装、构建、校验和发布均由 CLI 内部完成。

成功后把平台原样返回的 Preview URL 和 Base URL 交给用户，提示用户在飞书登录态体验页面，然后立即停止。不要打开浏览器，也不要直调 SQL/FaaS 做运行态验收。

本次存在原生通知 workflow 时，先按入口策略完成发布收尾。`site_action` 只使用本次 `deploy` 原样返回的 `preview.appUrl`：新 workflow 此时才执行 `+workflow-create`，一次性把 `LarkMessageAction.data.btn_list[].link` 配成“该 `appUrl` + Page 已实现的对应功能路由 + workflow 中的目标对象标识”，再启用并回读；已有 workflow 才先 `+workflow-get`，用完整定义执行 `+workflow-update`，随后启用并回读。不得使用裸 `appUrl`、`recordLink`、Base URL、`managementUrl` 或猜测的 Preview URL。`informational` 必须有用户明确要求纯展示的原文，并回读确认没有按钮；`base_action` 必须有用户明确要求进入多维表格的原文。回读时逐个核对本次创建或修改的 `LarkMessageAction`，并在交付清单记录 workflow ID、入口策略、按钮字段路径和不含环境基址的路由模板。任一配置或回读不满足约束时立即执行 `+workflow-disable`，并把结果标记为 partial 或 blocked，不得报告通知或整体系统已完成。完成原生配置后再向用户交付 Preview 并停止；这不授权打开页面、直调 Function 或发布 Prod。

## 5. 等待用户体验

此前任务中的“搭建并发布”不包含 Prod 授权。用户没有明确回复“部署正式版”时，不继续调用接口、修改代码或发布。

## 6. 发布 Prod

用户体验后明确回复“部署正式版”，才执行：

```bash
npx @lark-base-open/base-site-cli deploy --production --yes
```

该命令读取 `.base-site-cli/state/preview.json`，校验本地 Artifact SHA-256 后直接把同一份已验证制品发布到 Prod，不重新构建或上传。没有 Preview 记录、Site token 不匹配或制品内容变化时停止。

Prod 发布 Site 本身不会自动更新 Base workflow。只要本次 Site 存在通知业务入口，无论当前链接看起来是否已正确，Prod 发布成功后都必须使用命令原样返回的生产 `appUrl`，按 Preview 交付清单逐个更新 workflow：只替换环境基址，逐字保留功能路由、动态对象参数、其他步骤和启用状态，然后回读确认所有 Site `openLink` 都以生产 `appUrl` 为基址，且不再包含 Preview 地址。任一 workflow 更新或回读失败时，必须明确报告“Prod 已发布，但通知入口切换未完成”，保留失败证据且不得把整体 Prod 交付报告为完成；不得通过重新发布 Prod 掩盖外部配置失败。

正式发布后交付 Site URL、Base URL、页面/表/operation 清单、用户已确认的 Preview，以及附件上传、FaaS 运行时等仍存在的平台限制。

## 修改已有 Site

保护未提交代码并一次性读取 `base-site.jsonc`、`catalog.json` 和现有源码。只实现需求差异并保留用户未要求修改的 Site 元数据；schema 或 binding 改变后刷新 Catalog。完成后重新执行 CLI `deploy`，等待用户确认 Preview，再发布 Prod。

## 失败与交付

环境、授权、生产数据边界或关键平台协议不可用时，停在受影响阶段，一次性汇总目标环境、method/path、脱敏响应和 LogID/Edge request ID。发布状态成功但访问 URL 返回 404/5xx 时，同时保留 URL、HTTP 状态和响应 LogID；不要猜替代协议、改写 URL、回退正式环境或用新资源掩盖错误。

Preview 交付至少包含管理后台链接、Site URL、Base URL、业务页面和 operation 清单、发布制品摘要，以及仍存在的平台限制。托管页面由用户在飞书登录态下体验。
