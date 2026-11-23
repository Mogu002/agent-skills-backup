# Base Site 代码开发手册

本文负责 Page、SQL Function 和 FaaS 的代码边界与 ABI。搭建和发布命令见 [Skill 主流程](../SKILL.md)，SQL 方言与类型见 [SQL Function 专项](sql-function.md)，工程取舍见 [风格手册](style-guide.md)。

## 阅读路径

- [Base Site 代码开发手册](#base-site-代码开发手册)
  - [阅读路径](#阅读路径)
  - [工程结构](#工程结构)
  - [Function 调用契约](#function-调用契约)
  - [Page 调用](#page-调用)
  - [自动化实现边界](#自动化实现边界)
  - [FaaS 开发](#faas-开发)
    - [远程调用与写入链路设计](#远程调用与写入链路设计)
    - [下游错误归一化](#下游错误归一化)
    - [写入行（记录）](#写入行记录)
      - [Site Records 写入协议](#site-records-写入协议)
      - [创建实现示例](#创建实现示例)
  - [Base 读写协议](#base-读写协议)

## 工程结构

```text
project/
├── page/
├── sql/<functionId>/{main.sql,meta.json}
└── server-functions/functions/<functionId>/{index.ts,meta.json}
```

SQL 与 FaaS 的 `functionId` 在 Site 内全局唯一，匹配 `/^[A-Za-z0-9_-]+$/`；SQL ID 长度为 1～64。不同 FaaS Function 目录独立构建，不跨目录 import。Page 和 `server-functions/` 分别维护自己的 npm 工程与 `package-lock.json`。

## Function 调用契约

ABI 是 Page、Site loader 与 Function 之间固定的数据边界。两类 Function 都通过 `invokeFunction({projectId,functionId,params})` 调用，但 `params` 类型不同：

`projectId` 使用当前 Site token，`functionId` 使用源码目录名；两者都是工程常量。

| Function | `params` | 实现 | 结果 |
|---|---|---|---|
| SQL | 按 `$1`、`$2` 排列的数组 | `main.sql` + `meta.json` | 一层 `{data:{rows},code,msg}` |
| FaaS | 业务对象 | `index.ts` + `meta.json` | 一层 `{data,code,msg}`，`data` 是 handler 业务数据 |

SQL 示例：

```ts
await invokeFunction<{ rows: unknown[] }>({
  projectId: PROJECT_ID,
  functionId: 'listTasks',
  params: ['待处理'],
})
```

FaaS 创建操作示例：

```ts
await invokeFunction<{ created: boolean }>({
  projectId: PROJECT_ID,
  functionId: 'createTask',
  params: { title: '准备评审', status: '待处理' },
})
```

公开 HTTP body 分别是 `{"params":[...]}` 和 `{"params":{...}}`。SDK 使用当前 Site 用户身份，页面不保存后台凭证。

## Page 调用

默认 Page 的 `page/index.html` 需要把 `<title>` 设置为本次生成的 Site 名称，不留空。

默认 Page 必须引用并渲染 `page/src/components/floating-button/index.tsx` 中的 `FloatingButton` 组件，并显式传入 `language` 参数。

涉及人员搜索或人员选择的页面，优先引用 `page/src/components/UserSelectorEditor` 和 `page/src/components/UserSelectorPanel` 等 `page/src/components/` 下的人员组件；只有现有组件无法满足交互契约时才做局部扩展。

业务请求集中在 operation/runtime client，不散落在组件中：

```ts
import { invokeFunction } from '@lark-base-open/base-site-js'

interface SqlRows<TRow> {
  rows: TRow[]
  columns?: unknown[]
  row_count?: number
  log_id?: string
}
```

浏览器 SDK 对 SQL 和 FaaS 都只返回一层 `{data,code,msg}`。`invokeFunction<TData>` 的 `TData` 只描述当前 operation 约定的顶层 `data`：SQL 通常是 ResultJSON，FaaS 则以各 handler 的业务结果为准，不能统一假设存在 `recordId`。页面只检查一次顶层 `code`，再按 operation 契约校验 `data`；不得写成 `invokeFunction<FaasHandlerResult<TData>>`，也不得对 `result.data` 二次解包。否则后端已经写入成功时，页面仍可能误报失败。

运行时业务数据在边界处校验，不能只依赖 TypeScript 泛型。`projectId`、`functionId` 和所有路由是工程常量；用户输入只进入已声明的业务参数。

SDK `fetch` 只用于固定、allow-listed、SQL 不覆盖的非 Base 只读 OpenAPI。Page 发起的 Base 业务读取和写入仍分别走 SQL Function 与 FaaS。

## 自动化实现边界

代码实现前复核需求拆解结果：Page 主动提交且需要服务端校验的即时业务写入可以实现为 FaaS；定时、记录变化触发、提醒、通知等自动化优先使用原生多维表格能力，不创建 FaaS Function，也不从 Page 调用 FaaS 模拟自动化。

无法确认一项需求是否由原生 Base 支持时，必须先执行[原生 Base 能力发现与路由](base-capability-routing.md)：查询当前 `lark-cli base` shortcut、对应命令帮助和目标 Base 的真实资源，再决定由原生 Base、Base Site 或两者组合实现。未完成该查询前不得记录能力缺口；查询后仍受限时，必须区分原生能力缺口、当前 CLI 覆盖缺口和权限或环境阻塞。

## FaaS 开发

每个由 Page 主动发起的写入 operation 的目录：

```text
server-functions/functions/<functionId>/
├── index.ts
└── meta.json
```

```json
{ "name": "创建任务", "description": "校验输入并创建一条任务记录" }
```

loader 读取 HTTP `req.body.params`，把这个业务对象作为 handler 第一个参数 `rawParams`；第二个参数是 runtime context：

```ts
interface FunctionContext {
  fetch: typeof fetch
  invokeFunction(request: {
    projectId: string
    functionId: string
    params: unknown[]
  }): Promise<unknown>
}

interface FaasHandlerResult<T> {
  data: T | null
  code: number
  msg: string
}

export default async function handler(
  rawParams: unknown,
  context: FunctionContext,
): Promise<FaasHandlerResult<unknown>> {
  const input = parseCreateTask(rawParams)
  // 执行业务写入。
  return { data: { title: input.title }, code: 0, msg: 'success' }
}
```

`rawParams` 已经是业务对象。输入校验失败返回稳定业务码、`data:null` 和可读 `msg`。`FaasHandlerResult` 只描述 handler 的返回约定，不得作为页面 `invokeFunction` 的泛型参数。

### 远程调用与写入链路设计

实现前先按设计结果确认一致性、部分成功、重试语义和远程调用依赖。以一次 Page/FaaS operation 为边界列出 SQL Function、`context.fetch` 和写入 OpenAPI；标记哪些输入在 operation 开始时已经确定、哪些必须等待前一步响应。默认使用满足业务语义的最少远程等待阶段：

- 同表多条创建、更新或删除合并到一个 batch 请求，单批不超过 200 条。
- 同一 operation 调用多个 SQL Function 或 FaaS Function 时，输入已确定、互不依赖，且并发不改变一致性或部分成功语义的调用尽量并发；只有真实响应依赖才串行。
- 多个无副作用读取或请求的参数已经确定且互不依赖时，先启动全部 Promise，再在共同消费结果处等待；存在真实响应依赖时才串行。
- 原始 Promise 仍可能 reject 且需要知道每一路结果时使用 `Promise.allSettled`；helper 已把异常归一化为结构化结果时可以使用 `Promise.all`。
- 写前 SQL 只用于服务端必须确认的权限、关键状态或其他可信数据；写后 SQL 回读用于验收或明确要求的业务校验，不作为每次生产写入的默认步骤。
- 页面状态仅可用于允许弱一致性的非安全敏感计算。用户身份、权限、租户隔离、支付、库存、额度等约束不得信任页面传值。
- 多路写入返回值区分全部成功、部分成功和全部失败，并携带已取得的 record ID 与安全错误信息。非幂等创建结果未知时不自动整体重试。
- 需要事务、唯一约束、条件更新或原子 compare-and-set 才能保证正确性的 operation，在当前 Base 能力下标记为不支持，不使用多次远程请求模拟。

无依赖的多路写入可以采用：

```ts
const writes = await Promise.allSettled([
  updatePrimaryRecord(context, input),
  createAuditRecord(context, input),
])

return summarizeWrites(writes)
```

性能敏感的 operation 记录总耗时和各远程调用耗时；只使用成功业务请求评价写入性能，鉴权失败、参数失败和平台凭证缺失只用于诊断。日志和返回值不得包含 token、cookie 或请求凭证。

### 下游错误归一化

FaaS 调用 Base OpenAPI 或其他 Site Function 时，把当前 operation 的业务结果与下游诊断分开：

- 顶层 `code` 和 `msg` 表达稳定、面向调用方的业务语义，不直接使用上游错误码，也不把技术细节拼进 `msg`。
- 成功或部分成功的业务结果保留在 `data`；仅在失败或部分成功时，把失败步骤放入 `data.errors`。
- 上游只返回错误摘要时原样保留经清理的摘要和 LogID，不猜测或拼造不存在的校验详情。

```ts
type DownstreamErrorKind =
  | 'openapi'
  | 'function'
  | 'transport'
  | 'invalid_response'

interface DownstreamError {
  source: 'base_openapi' | 'site_function'
  step: string
  kind: DownstreamErrorKind
  operation: string
  httpStatus?: number
  code?: number
  msg: string
  logId?: string
  retryable: boolean
}

type DownstreamOutcome<T> =
  | { ok: true; value: T }
  | { ok: false; error: DownstreamError }
```

下游 helper 捕获预期失败并返回 `DownstreamOutcome<T>`，业务 handler 再汇总各步骤；代码自身的非预期异常仍由 handler 最外层捕获并返回通用错误，不向页面泄漏原始异常或堆栈。分类规则固定为：

- Base OpenAPI 返回合法 JSON 且含非零数值 `code`：`openapi`；
- Site Function 返回合法 envelope 且含非零数值 `code`：`function`；
- `fetch` reject、超时、连接中断等未取得合法响应：`transport`；
- 非 JSON、缺少约定字段，或成功响应缺少预期结果：`invalid_response`。

错误对象只允许返回诊断所需的白名单字段。`msg` 取上游安全摘要，去除首尾空白并限制在 300 字符内；`logId` 优先取响应 `x-tt-logid`，可回退 `x-request-id`，限制在 128 字符内。不得返回 URL、请求 body、完整响应、完整 headers、stack、token、cookie 或其他凭证。对于 `context.invokeFunction`，只从其合法返回 envelope 中提取同等字段。

`retryable` 同时取决于错误和写入语义，不能只看 HTTP 状态。明确幂等的固定字段更新或删除遇到 transport、408、429 或 5xx 时可以标记为可重试；非幂等创建出现 transport 或结果未知时必须为 `false`，除非业务已有稳定幂等键和去重机制。页面不得仅因为 `retryable: true` 自动重提，仍按 operation 契约决定交互。

多路写入的顶层业务码至少区分输入无效、部分成功、下游全部失败和内部异常，并在同一 operation 内保持稳定。全部成功时省略 `errors`；部分成功时返回已完成结果、失败步骤和明确的后续动作，避免用户重复提交已经成功的非幂等写入。

Site invoke 网关在 handler 返回前产生的 504、运行时崩溃或加载失败无法被上述结构捕获。排查这类错误时保留 invoke HTTP 响应自身的 `x-tt-logid`，不要伪装成某次 OpenAPI 调用错误。

### 写入行（记录）

FaaS 使用 `context.fetch` 调用 Site 绑定表的固定写入接口；只使用线上 origin：

| 目标 | Origin |
|---|---|
| Online | `https://open.feishu.cn` |

#### Site Records 写入协议

FaaS 只使用以下三个固定路由，均为 `POST`，请求头为
`Content-Type: application/json; charset=utf-8`：

```http
/open-apis/base/v3/sites/:site_token/tables/:table_id/records/batch_create
/open-apis/base/v3/sites/:site_token/tables/:table_id/records/batch_update
/open-apis/base/v3/sites/:site_token/tables/:table_id/records/batch_delete
```

请求体必须严格使用对应结构，不混用普通 Base OpenAPI、MCP 或其他 batch 接口的字段：

| operation | 请求体 | 成功时 `data.record_id_list` 的语义 |
|---|---|---|
| `batch_create` | `{"create_records":[{字段名: CellValue}, ...]}` | 与 `create_records` 按位置一一对应的新记录 ID |
| `batch_update` | `{"update_records":{"rec_xxx":{字段名: CellValue}, ...}}` | 已提交更新的记录 ID，顺序与 `update_records` 的 key 顺序一致 |
| `batch_delete` | `{"record_id_list":["rec_xxx", ...]}` | 已提交删除的记录 ID，顺序与请求一致 |

三个请求体都是 strict JSON Schema：不接受表格中未列出的额外顶层字段；每批必须包含
1～200 条记录。record ID 必须匹配 `^rec[A-Za-z0-9]{1,11}$`；删除列表不允许重复，
更新映射的 key 自然唯一。Site `batch_update` 使用 `update_records` 为不同记录分别提交
patch；不要混用 MCP 工具层 `patch_records_batch` 的 `record_id_list + patch` 请求结构。

三种写入的成功 HTTP body 都只有一层 OpenAPI envelope：

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "record_id_list": ["rec_xxx"]
  },
  "meta": {}
}
```

`batch_create` 的 `data` 还可能包含被忽略的只读或不支持字段；未忽略任何字段时
`ignored_fields` 不存在：

```json
{
  "record_id_list": ["rec_xxx"],
  "ignored_fields": [
    {
      "id": "fld_xxx",
      "name": "创建时间",
      "reason": "READONLY: created_at field is auto-created by the system."
    }
  ]
}
```

成功响应中的记录 ID 固定读取 `body.data.record_id_list`。不得递归遍历整个响应寻找字符串，
不得猜测或兼容 `record_id`、`recordId`、`records[].id` 等未约定结构，也不得把
`data.record_id_list` 当作 handler 自定义返回的 `recordId`。创建数量必须与
`create_records.length` 一致；更新和删除返回的 ID 必须与本次请求目标一致。响应缺失、
类型不符、数量或目标不一致时按 `invalid_response` 处理，非幂等创建不得自动重试。

可复用的严格解析器：

```ts
interface IgnoredRecordField {
  id: string
  name: string
  reason: string
}

interface SiteRecordsWriteData {
  record_id_list: string[]
  ignored_fields?: IgnoredRecordField[]
}

interface SiteRecordsWriteEnvelope {
  code: number
  msg: string
  data: SiteRecordsWriteData
  meta?: unknown
}

function parseSiteRecordsWriteData(
  value: unknown,
): SiteRecordsWriteData | undefined {
  if (typeof value !== 'object' || value === null) return undefined
  const envelope = value as Record<string, unknown>
  if (envelope.code !== 0) return undefined
  if (typeof envelope.data !== 'object' || envelope.data === null) {
    return undefined
  }
  const data = envelope.data as Record<string, unknown>
  const recordIdPattern = /^rec[A-Za-z0-9]{1,11}$/
  if (
    !Array.isArray(data.record_id_list) ||
    data.record_id_list.length === 0 ||
    data.record_id_list.length > 200 ||
    data.record_id_list.some(
      (recordId) =>
        typeof recordId !== 'string' || !recordIdPattern.test(recordId),
    ) ||
    new Set(data.record_id_list).size !== data.record_id_list.length
  ) {
    return undefined
  }
  return {
    record_id_list: data.record_id_list as string[],
    ...(Array.isArray(data.ignored_fields)
      ? { ignored_fields: data.ignored_fields as IgnoredRecordField[] }
      : {}),
  }
}
```

该 helper 只负责成功 payload 的固定结构；HTTP 失败、非零业务码和错误摘要仍按
[下游错误归一化](#下游错误归一化)处理。

#### 创建实现示例

```ts
const OPENAPI_ORIGIN = 'https://open.feishu.cn'
const response = await context.fetch(
  `${OPENAPI_ORIGIN}/open-apis/base/v3/sites/${encodeURIComponent(SITE_TOKEN)}` +
    `/tables/${encodeURIComponent(TABLE_ID)}/records/batch_create`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify({
      create_records: [
        {
          任务名称: input.title,
          状态: input.status,
          截止时间: input.dueAt,
        },
      ],
    }),
  },
)

const body: unknown = await response.json().catch(() => null)

if (
  !response.ok ||
  typeof body !== 'object' ||
  body === null ||
  !('code' in body) ||
  body.code !== 0
) {
  const logId =
    response.headers.get('x-tt-logid') ??
    response.headers.get('x-request-id') ??
    undefined
  const upstreamCode =
    typeof body === 'object' &&
    body !== null &&
    'code' in body &&
    typeof body.code === 'number'
      ? body.code
      : undefined
  const rawUpstreamMsg =
    typeof body === 'object' &&
    body !== null &&
    'msg' in body &&
    typeof body.msg === 'string'
      ? body.msg.trim().slice(0, 300)
      : ''
  const upstreamMsg =
    rawUpstreamMsg || response.statusText || `OpenAPI HTTP ${response.status}`
  const isOpenApiError =
    typeof upstreamCode === 'number' && upstreamCode !== 0

  return {
    data: {
      created: false,
      errors: [
        {
          source: 'base_openapi',
          step: 'createTask',
          kind: isOpenApiError ? 'openapi' : 'invalid_response',
          operation: 'batch_create',
          httpStatus: response.status,
          ...(typeof upstreamCode === 'number'
            ? { code: upstreamCode }
            : {}),
          msg: upstreamMsg,
          ...(logId ? { logId: logId.trim().slice(0, 128) } : {}),
          retryable: false,
        },
      ],
    },
    code: 50201,
    msg: '创建任务失败',
  }
}

const created = parseSiteRecordsWriteData(body)
if (!created || created.record_id_list.length !== 1) {
  return {
    data: {
      created: true,
      errors: [
        {
          source: 'base_openapi',
          step: 'createTask',
          kind: 'invalid_response',
          operation: 'batch_create',
          msg: '创建成功但响应中的记录 ID 数量不符合请求',
          retryable: false,
        },
      ],
    },
    code: 50202,
    msg: '任务已创建，但无法确认记录 ID',
  }
}

const [recordId] = created.record_id_list
return { data: { created: true, recordId }, code: 0, msg: 'success' }
```

FaaS 写入 Base 时，必须调用目标环境的 `/open-apis/base/v3/sites/:site_token/tables/:table_id/records/batch_*` 接口；使用与页面 `projectId` 相同的 Site token，不传 Base token，并检查 HTTP 状态和业务码。

需要读 Base 时调用固定 SQL Function：

```ts
const result: unknown = await context.invokeFunction({
  projectId: PROJECT_ID,
  functionId: 'findTaskById',
  params: [input.recordId],
})
```

确需写前查重、权限范围、状态检查或写后查询时复用固定 SQL Function；可以在一次查询中完成的检查不拆成多个串行调用。前一个 SQL 返回的关联 ID 仅用于定位后一个 SQL 的记录时，优先把关联查询下推为一个 SQL Function。

## Base 读写协议

同一个字段在创建 schema、SQL 读取和 OpenAPI 写入时使用三套不同但相关的数据结构：

| Field JSON | SQL 读取 | OpenAPI CellValue |
|---|---|---|
| `text` | `TEXT` string | string |
| `number` | `DOUBLE` number | finite number |
| 单选 `select` | `OPTION` string | 合法选项名 string |
| 多选 `select` | `COLLECTION<OPTION>` | 合法选项名 string[] |
| `datetime` | `TIMESTAMP` 毫秒 number | `YYYY-MM-DD HH:mm:ss` |
| `checkbox` | `BOOL` boolean | boolean |
| 单/多 `user` | `USER` / `COLLECTION<USER>` | `[{"id":"ou_xxx"}]` |
| 单/多 `group_chat` | `GROUP` / `COLLECTION<GROUP>` | `[{"id":"oc_xxx"}]` |
| `link` | `COLLECTION<RECORD_ID>` | `[{"id":"rec_xxx"}]` |
| `attachment` | `COLLECTION<FILE>` | Base Site 暂不支持上传 |
| `location` | `UNSUPPORTED` | `{"lng":number,"lat":number}` |
| 公式、lookup、系统字段 | 推导类型或 `UNSUPPORTED` | 只读 |

写入时 `null` 清空字段，`[]` 表示空集合，省略字段表示不修改。选项名、用户/群 ID 和关联 record ID 必须来自真实数据。

Site 行写入只使用 [Site Records 写入协议](#site-records-写入协议)中的三个固定路由。

创建一行或多行时，`create_records` 中每一项是字段到 cell value 的映射，不同记录可以填写不同字段：

```json
{
  "create_records": [
    {
      "任务名称": "客户回访",
      "状态": "待处理",
      "负责人": [{ "id": "ou_xxx" }]
    }
  ]
}
```

更新时把以 record ID 为 key 的字段 patch 放入 `update_records`：

```json
{
  "update_records": {
    "rec_xxx": { "状态": "已完成" },
    "rec_yyy": { "状态": "进行中", "备注": "处理中" }
  }
}
```

删除时传入 record ID 列表：

```json
{
  "record_id_list": ["rec_xxx", "rec_yyy"]
}
```

检查 HTTP 状态和外层业务码后，还必须按固定成功响应协议校验
`data.record_id_list`；需要后续写入、关联或回读时，只使用该字段中的记录 ID。

单批最多 200 条。附件上传协议当前未接入 Base Site；需要附件的项目明确记录限制，经用户同意可暂用图片 URL。
