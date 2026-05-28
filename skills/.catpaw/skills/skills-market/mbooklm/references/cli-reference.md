# MBookLM CLI 参考文档

## 命令格式

```
edi mbooklm <command> [options]
```

> 会话式常用说法、`nb help` / `nb --help` 的帮助卡内容见 [chat-quick-help.md](chat-quick-help.md)。本文件只放 CLI 参数、示例和输出格式。

## 帮助命令

```bash
edi mbooklm --help
edi mbooklm help
```

- `--help` 与 `help` 等价，均输出 CLI 帮助
- 若你要的是对话式说法（如「问 nb ...」「往 nb 加 ...」），优先参考 `chat-quick-help.md`

## 全局选项

| 选项 | 说明 |
|------|------|
| `--mis <mis>` | 指定 MIS 用户 ID（可选，默认读取环境） |
| `--raw` | 输出原始 JSON 到 stdout |
| `--clear-cache` | 清除认证缓存 |
| `--force-ciba` | 强制重新 CIBA 认证 |

## 命令关系（容易混淆）

- `getNotebook`：只查看笔记本元信息，如名称、来源数量
- `addGroupPermission`：给笔记本新增群权限，本期固定为"群 + 浏览"
- `listSources`：查看笔记本里有哪些文档
- `retryBatchSources`：对账某次批量 URL 导入结果，并恢复失败/缺失项
- `searchNotebookDocs`：先按关键词定位相关**文档**（返回文档列表）
- `getSourceContent`：读取某篇文档正文，`sourceId` 通常来自 `searchNotebookDocs`
- `sourceRetrieval`：返回语义切片（Chunk），**粒度比 `searchNotebookDocs` 更细**；适合 Agent 自主推理或内部 Memory 检索

**三条 RAG 链路**：

| 链路 | 命令 | 适用场景 |
|---|---|---|
| 问答（默认） | `mbooklmChat` | 用户问问题，透传服务端 AI 答案 |
| 文档检索 + 精读 | `searchNotebookDocs` → `getSourceContent` | 用户要找/看某篇原文 |
| 切片检索 | `sourceRetrieval` | 用户要"搜片段"，或 Agent 内部需要按相关性取材料后自行推理 |

## 执行与诊断要点

- `notebookId` 必须来自 `selectNotebookList` 或 `getNotebook`，不得自行构造
- `sourceId` 通常来自 `searchNotebookDocs`，默认不直接展示给用户
- 认证失败时优先执行 `edi mbooklm --clear-cache` 后重试；CIBA 仍需用户在大象 App 确认
- 成功判断以命令返回结果为准：
  - `createNotebook`：`notebookId` 非空
  - `addGroupPermission`：命令成功返回且无异常
  - `addSources`：`totalCount > 0`
  - `addContentSource`：成功返回字符串消息（当前为 `内容已成功添加`）
  - `addFileSources`：`successFiles` 非空
  - `searchNotebookDocs`：返回文档列表
  - `getSourceContent`：返回 `title` 和 `content`
  - `sourceRetrieval`：返回 `list` 非空

---

## `selectNotebookList`

查询当前用户所有笔记本列表。

**参数**: 无

**示例**:

```bash
edi mbooklm selectNotebookList
edi mbooklm selectNotebookList --raw
```

**输出（默认）**:
```
共 3 个笔记本：
  • 我的笔记  ID: abc123  [来源: 5]
  • 项目知识库  ID: def456  [来源: 12]
  • 他人分享的笔记  ID: ghi789  [来源: 8] [只读]
```

> - CLI 原始输出含 `notebookId`，Agent 展示时按输出规范过滤 ID、以 Markdown 链接呈现。
> - `[只读]` 标注表示该笔记本为他人分享、当前用户无编辑权限（`canEdit=false`），**无法执行 `addSources` / `addContentSource` / `addFileSources`**。

**输出（--raw）**:
```json
[
  {
    "notebookId": "abc123",
    "name": "我的笔记",
    "sourceCount": 5,
    "sessionId": "sess-xxx",
    "createMis": "fanshifeng",
    "role": 0,
    "canEdit": true
  },
  {
    "notebookId": "def456",
    "name": "项目知识库",
    "sourceCount": 12,
    "sessionId": "sess-zzz",
    "createMis": "zhangsan",
    "role": 2,
    "canEdit": true
  },
  {
    "notebookId": "ghi789",
    "name": "他人分享的笔记",
    "sourceCount": 8,
    "sessionId": "sess-yyy",
    "createMis": "lisi",
    "role": 3,
    "canEdit": false
  }
]
```

**`canEdit` 字段说明**：

| `canEdit` | `role` | 含义 | 可执行写操作 |
|---|---|---|---|
| `true` | `0` | 自己创建的笔记本 | ✅ |
| `true` | `2` | 他人分享且有编辑权限 | ✅ |
| `false` | `3` | 他人分享的只读笔记本 | ❌ |

---

## `getNotebook`

根据笔记本 ID 查询详情（名称、来源数量等）。

**必填参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--notebookId` | string | ✅ | 笔记本唯一标识符，从 selectNotebookList 获取 |

**示例**:

```bash
edi mbooklm getNotebook --notebookId "abc123"
edi mbooklm getNotebook --notebookId "abc123" --raw
```

**输出（默认）**:
```
笔记本名称: 我的笔记
笔记本 ID: abc123
来源数量: 5
```

> CLI 原始输出含 `笔记本 ID`，Agent 展示时按输出规范过滤，仅展示名称和来源数量。

**输出（--raw）**:
```json
{
  "notebookId": "abc123",
  "name": "我的笔记",
  "sourceCount": 5,
  "sessionId": "sess-yyy"
}
```

---

## `createNotebook`

创建新笔记本。

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--name` | string | ✅ | 笔记本名称 |
| `--icon` | string | ❌ | 笔记本图标，默认 `zhishiku` |

**示例**:

```bash
edi mbooklm createNotebook --name "项目知识库"
edi mbooklm createNotebook --name "技术文档" --icon "zhishiku"
```

**输出（默认）**:
```
✅ 笔记本创建成功
名称: 项目知识库
笔记本 ID: new-id-xxx
```

---

## `addGroupPermission`

给笔记本新增群权限。本期仅支持“群 + 浏览权限”，底层调用 notebook 服务端真实接口。

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--notebookId` | string | ✅ | 笔记本 ID |
| `--groupId` | string | ✅ | 大象群 ID |

**服务端真实契约**:
- 路径：`POST /v1/api/notebooks/permissions/add`
- 请求体中除 `notebookId`、`groupId` 外的展示性字段由底层处理，上层无需关心
- `principalType=1` 表示群，`role=3` 表示浏览权限（VIEWER）

**示例**:

```bash
edi mbooklm addGroupPermission \
  --notebookId "abc123" \
  --groupId "123456"
```

**输出（默认）**:
```
✅ 群权限已开通
群名称: AI 项目群
群 ID: 123456
权限: 浏览
```

**输出（--raw）**:
```json
{
  "notebookId": "abc123",
  "targetType": "group",
  "targetId": "123456",
  "targetName": "无权限查看群名称",
  "permission": "browse"
}
```

---

## `deleteNotebook`

删除指定笔记本。这是高风险操作，建议仅在 skill 层完成二次确认后再调用。该命令通过 notebook 项目的 HTTP 接口执行，不走 MCP。

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--notebookId` | string | ✅ | 要删除的笔记本 ID，从 selectNotebookList / getNotebook 获取 |

**注意**:
- 默认仅支持删除本人创建的笔记本
- 对分享给我的只读笔记本（`canEdit=false`）应直接拒绝
- 对非本人创建但可编辑的协作笔记本，也应默认拒绝并提示前往官网确认
- CLI 本身不做交互式确认；二次确认应在 skill 会话层完成

**示例**:

```bash
edi mbooklm deleteNotebook --notebookId "abc123"
edi mbooklm deleteNotebook --notebookId "abc123" --raw
```

**输出（默认）**:
```
🗑️ 笔记本已删除
名称: 项目知识库
笔记本 ID: abc123
```

**输出（--raw）**:
```json
{
  "notebookId": "abc123"
}
```

> 服务端删除接口通常返回空 `data`；CLI 会至少补回 `notebookId` 作为原始结果，默认展示中的名称来自删除前查询到的笔记本信息。

---

## `addSources`

向笔记本批量添加文档 URL 作为知识来源，支持学城（km.sankuai.com）链接及公网网页。

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--notebookId` | string | ✅ | 笔记本 ID，从 selectNotebookList 获取 |
| `--urls` | json-array | ✅ | 文档 URL 列表（学城链接或公网网页），JSON 格式，最多 100 个 |

**注意**:
- `urls` 必须为 JSON 数组字符串，支持学城（km.sankuai.com）链接及公网网页
- 来源添加为异步流程，解析完成后才能用于问答
- 单次超过 100 个 URL 会被截断
- `totalCount=0` 表示所有 URL 均无效（不存在/无权限/已存在/格式错误/非公开可访问网址）

**示例**:

```bash
edi mbooklm addSources \
  --notebookId "abc123" \
  --urls '["https://km.sankuai.com/collabpage/111","https://km.sankuai.com/collabpage/222"]'
```

**输出（默认）**:
```
添加完成，共入库 2 个文档
来源处于「处理中」状态，解析完成后可用于问答。
```

> 说明：这里的“入库成功”只表示来源记录已写入笔记本；后续解析、切片和向量化仍是异步过程。若用户关心“这批链接最后哪些成功、哪些还在处理、哪些失败了”，应继续执行 `listSources` 或 `retryBatchSources`。

**输出（--raw）**:
```json
{
  "totalCount": 2,
  "limitExceeded": false
}
```

---

## `addContentSource`

向笔记本添加文本内容作为知识来源。与 `addSources` 不同，`addContentSource` 接受已有的字符串内容（而非 URL），适用于用户直接提供文字/笔记/代码片段等场景。

**使用边界**：
- 适用于用户直接提供字符串内容，以及 `.md` / `.txt` 文件已被宿主平台或上游转成可直接读取正文的场景
- 若用户提供的是 `PDF / Word` 附件、本地文件或文件路径，不应优先使用本命令

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--notebookId` | string | ✅ | 笔记本 ID，从 selectNotebookList 获取 |
| `--content` | string | ✅ | 要添加的文本内容，单次一条 |

**注意**:
- `content` 接受字符串内容，不支持 URL
- 推荐使用结构化文本（如 Markdown）以获得更好的阅读和问答效果，但不是必需
- 来源添加为异步流程，解析完成后才能用于问答
- 单次只能添加一条内容（不同于 `addSources` 的批量 URL）
- 成功时默认返回字符串消息 `内容已成功添加`
- 若服务端返回失败，则 CLI 会输出失败原因

**示例**:

```bash
edi mbooklm addContentSource \
  --notebookId "abc123" \
  --content "项目发布流程：1. 代码审核 2. 测试通过 3. 合并主干 4. 触发 CI/CD"
```

**输出（默认）**:
```
✅ 内容已成功添加
来源处于「处理中」状态，解析完成后可用于问答。
```

**输出（--raw）**:
```json
"内容已成功添加"
```

---

## `listSources`

查询指定笔记本下已添加的所有来源记录。默认一次拉取全部（`pageSize=5000`，笔记本来源上限亦为 5000）。

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--notebookId` | string | ✅ | 笔记本 ID，从 selectNotebookList 获取 |

**示例**:

```bash
edi mbooklm listSources --notebookId "abc123"
edi mbooklm listSources --notebookId "abc123" --raw
```

**输出（默认）**:
```
共 3 条来源：
  • 项目架构设计文档  https://km.sankuai.com/collabpage/111
  • 技术方案评审文档  https://km.sankuai.com/collabpage/222
  • 上线操作手册  [处理中]
    https://km.sankuai.com/collabpage/333
```

> 若来源来自 `addContentSource`，默认输出也可能只显示标题或摘要而不带 URL，这属于正常情况。
>
> 默认展示面向用户统一使用中文状态：`已成功`、`处理中`、`解析失败`；URL 来源以 Markdown 链接呈现标题，内容来源若无 URL 则直接展示标题或摘要。仅在 `--raw` 输出中保留服务端原始状态枚举。

**输出（--raw）**:
```json
{
  "list": [
    {
      "url": "https://km.sankuai.com/collabpage/111",
      "title": "项目架构设计文档",
      "status": "ACTIVE"
    },
    {
      "url": "https://km.sankuai.com/collabpage/333",
      "title": "上线操作手册",
      "status": "PROCESSING"
    }
  ],
  "hasMore": false,
  "curLastId": 5150,
  "totalCount": 3
}
```

**状态说明（对用户展示）**:
- `已成功`：解析完成，可用于问答
- `处理中`：解析处理中，暂不可用于问答
- `解析失败`：解析失败，可尝试重新 `addSources`（URL 来源）或 `addContentSource`（内容来源）

---

## `retryBatchSources`

对账本次批量 URL 导入结果，并执行最小范围恢复：
- 对当前笔记本中状态为 `FAILED/ERROR` 的本次来源，调用服务端重试接口
- 对本次 URL 列表里存在、但当前笔记本中找不到的 `missing` 项，默认只汇报，不自动重新执行 `addSources`
- 对仍处于 `PROCESSING` 的来源只做提示，不自动重试

**适用场景**:
- 用户说「刚才那批导入有几条没进来」
- 用户说「帮我看这批链接哪些失败了，再帮我重试」
- 用户发现导入数量和笔记本来源数对不上，希望对账并恢复

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--notebookId` | string | ✅ | 笔记本 ID |
| `--urls` | json-array | ✅ | 本次批量导入的原始 URL 列表 |
| `--submittedAt` | number | ❌ | 本次提交时间（Unix 毫秒时间戳），传入后可缩小对账时间窗 |
| `--retryMissing` | boolean | ❌ | 是否自动重新导入 `missing` URL；默认 `false`，仅在用户明确要求时开启 |

**注意**:
- 这是一个**恢复命令**，不会替代正常的 `addSources`
- 若拿不到本次原始 URL 列表，就无法准确识别 `missing` 项
- 只会重试当前笔记本里已经存在且状态为 `FAILED/ERROR` 的来源
- `PROCESSING` 项默认不动，避免对仍在处理的来源重复触发
- `missing` 项默认只汇报不自动处理，避免把“重试失败来源”误变成“重新新增来源”
- 若用户问“刚才那批结果怎么样 / 现在还有失败吗 / 别用缓存再查一次”，必须先重新执行 `listSources` 获取最新状态，不能直接复述旧结论

**示例**:

```bash
edi mbooklm retryBatchSources \
  --notebookId "abc123" \
  --urls '["https://km.sankuai.com/collabpage/111","https://km.sankuai.com/collabpage/222"]' \
  --submittedAt "1712640000000"
```

**输出（默认）**:
```
本次批量导入对账完成，共 196 条输入 URL，在笔记本中匹配到 191 条来源。
✅ 已成功：180 条
⏳ 处理中：8 条
❌ 解析失败：3 条（已发起重试 3 条）
🔍 笔记本中未找到：5 条（默认未自动重新提交）
```

**输出（--raw）**:
```json
{
  "inputCount": 196,
  "activeSources": [],
  "processingSources": [],
  "failedSources": [],
  "missingUrls": [],
  "retriedSourceIds": [],
  "retriedMissingUrls": [],
  "retryErrors": []
}
```

---

## `mbooklmChat`

基于指定笔记本的知识来源进行智能问答（RAG）。

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--notebookId` | string | ✅ | 笔记本 ID，从 selectNotebookList 获取，不可自行构造 |
| `--query` | string | ✅ | 用户问题 |

**注意**:
- 仅支持「基于笔记本知识库」的问答，不适用于通用问答
- 必须先通过 `selectNotebookList` 获取有效的 `notebookId`
- 回答后附带「📚 参考来源」列表（stderr）：优先输出文档级 URL（已去掉段落锚点 `#b-xxx` 并按文档去重）；若参考来源没有 URL，则退化为标题；Agent 展示时截断至最多 3 条

**示例**:

```bash
edi mbooklm mbooklmChat \
  --notebookId "abc123" \
  --query "这个项目的核心架构是什么？"
```

**输出（默认）**:
```
该项目采用三层架构设计，分别为表现层、业务逻辑层和数据访问层...

📚 参考来源（2 条）：
  • https://km.sankuai.com/collabpage/111
  • https://km.sankuai.com/collabpage/222
```

---

## `searchNotebookDocs`

在指定笔记本的来源文档中进行 RAG 语义检索，返回最相关的文档列表。默认输出仅展示标题；如需手动衔接 `getSourceContent`，可通过 `--raw` 获取 `sourceId`。

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--notebookId` | string | ✅ | 笔记本 ID，从 selectNotebookList 获取 |
| `--query` | string | ✅ | 自然语言检索关键词 |

**注意**:
- 返回的是文档列表，**不返回文档正文**
- 默认输出仅展示标题，不展示 `sourceId`
- 若要手动调用 `getSourceContent`，请使用 `--raw` 获取 `sourceId`
- Agent 展示时应将 `sourceId` 保存在上下文中，以便用户说「看这篇」时自动触发 `getSourceContent`，无需再追问

**示例**:

```bash
edi mbooklm searchNotebookDocs \
  --notebookId "abc123" \
  --query "发布流程"
```

**输出（默认）**:
```
共找到 3 篇相关文档：
  • Spring AI Agents 接入手册
  • MCP（模型上下文协议）
  • MDP小确幸31 - MDP-AI Agent 开发指南
如需获取某篇全文，请基于该检索结果继续执行 getSourceContent（可通过 --raw 查看 sourceId）。
```

> 默认输出不展示 `sourceId`；若你是手动使用 CLI 并需要衔接 `getSourceContent`，请改用 `--raw`。

**输出（--raw）**:
```json
{
  "list": [
    {
      "notebookId": "abc123",
      "notebookTitle": "MDP",
      "sourceId": 446,
      "sourceTitle": "Spring AI Agents 接入手册"
    },
    {
      "notebookId": "abc123",
      "notebookTitle": "MDP",
      "sourceId": 437,
      "sourceTitle": "MCP（模型上下文协议）"
    }
  ]
}
```

---

## `getSourceContent`

根据来源 ID 获取笔记本中指定文档的完整正文内容。`sourceId` 通常从 `searchNotebookDocs --raw` 的结果中取得；在 Agent 会话里，若已有上一轮检索结果，也可基于标题继续表达为「获取 xxx 全文」「查 xxx 内容」；若没有上一轮检索结果但用户直接点名某篇标题，Agent 应先执行 `searchNotebookDocs` 定位，再衔接 `getSourceContent`。

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--notebookId` | string | ✅ | 笔记本 ID，从 selectNotebookList 获取 |
| `--sourceId` | string | ✅ | 来源 ID，从 `searchNotebookDocs --raw` 结果中取，**不得自行构造** |

**注意**:
- `sourceId` 虽然在 `searchNotebookDocs` 返回时是数字，但传参时需以字符串形式传入（CLI 自动处理）
- 返回的 `content` 为文档完整正文，Agent 应原样透传给用户，不得重新排版或改写
- 在 Agent 会话中，若用户说「获取 xxx 全文」「查 xxx 内容」，有上一轮检索结果时可用标题片段去匹配并取得对应 `sourceId`；若没有上一轮检索结果，则应先执行 `searchNotebookDocs` 再读取正文
- `id` 字段（来源 ID）属于内部字段，展示时不需要输出给用户

**示例**:

```bash
edi mbooklm getSourceContent \
  --notebookId "abc123" \
  --sourceId "446"
```

**输出（默认，stderr 为标题行，stdout 为正文）**:
```
标题: Spring AI Agents 接入手册
Spring AI Agents 接入手册--Claude 默认使用的 apiKey...
（文档完整正文）
```

> CLI 将标题输出到 stderr，正文输出到 stdout。Agent 展示时以 Markdown 标题形式呈现标题，正文原样透传，`id` 不展示。

**输出（--raw）**:
```json
{
  "id": 446,
  "title": "Spring AI Agents 接入手册",
  "content": "Spring AI Agents 接入手册--Claude 默认使用的 apiKey..."
}
```

---

## `sourceRetrieval`

在指定笔记本的来源文档中进行 **切片级语义检索**，返回与查询最相关的文档切片（Chunk）列表，每条切片附带相关性分数。与 `searchNotebookDocs`（返回文档列表）不同，本命令返回的是文档内部的细粒度片段。CLI 默认会直接展示这些切片；在 Agent 工作流中，也可把它们当作原材料继续整合、推理或摘要。

**适用场景**：
- 用户明确要求「找几段」「搜有没有提到 XX 的片段」
- Agent 将笔记本作为 Memory / 知识库，需要按相关性取原始材料后自行推理

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--notebookId` | string | ✅ | 笔记本 ID，从 selectNotebookList 获取 |
| `--query` | string | ✅ | 自然语言检索关键词 |

**注意**:
- 返回的是切片列表，**不是完整文档正文**；若用户要全文，应走 `getSourceContent`
- `score` 越高表示与 query 越相关；Agent 可按分数过滤低质量切片（建议阈值：score < 0.3 的切片可忽略）
- `sourceId` 默认不展示给用户，但 Agent 内部可用于后续衔接 `getSourceContent`
- 若需要全文作为上下文，直接用 `getSourceContent` 而非本命令

**示例**:

```bash
edi mbooklm sourceRetrieval \
  --notebookId "abc123" \
  --query "发布流程审批步骤"
```

**输出（默认）**:
```
找到 3 个相关切片：

[1] Spring AI Agents 接入手册（相关性: 0.92）
发布前需要通过 CI/CD 流水线审批，包含以下步骤：1. 代码 Review...

[2] MDP小确幸31 - MDP-AI Agent 开发指南（相关性: 0.78）
审批节点由发布管理员配置，支持单人和多人会签两种模式...

[3] MCP（模型上下文协议）（相关性: 0.61）
发布触发条件：分支合并到 master 后自动触发流水线...
```

> 默认输出含序号、`sourceTitle`、相关性分数和 `chunkContent`，不展示 `sourceId`。在 Agent 工作流中，可按需将这些切片继续整合后再输出给用户。

**输出（--raw）**:
```json
{
  "list": [
    {
      "chunkContent": "发布前需要通过 CI/CD 流水线审批，包含以下步骤：1. 代码 Review...",
      "score": 0.92,
      "sourceId": 446,
      "sourceTitle": "Spring AI Agents 接入手册",
      "notebookId": "abc123",
      "notebookTitle": "MDP"
    },
    {
      "chunkContent": "审批节点由发布管理员配置，支持单人和多人会签两种模式...",
      "score": 0.78,
      "sourceId": 437,
      "sourceTitle": "MDP小确幸31 - MDP-AI Agent 开发指南",
      "notebookId": "abc123",
      "notebookTitle": "MDP"
    }
  ]
}
```

**成功判断**：返回 `list` 非空。若 `list` 为空数组，说明未找到相关切片，可尝试换关键词或检查笔记本来源状态。

---

## `addFileSources`

向笔记本上传本地文件作为知识来源。与 `addSources`（URL）和 `addContentSource`（文本字符串）不同，`addFileSources` 接受本地文件路径，通过 REST API 上传到平台后注册为来源。

**使用边界**：
- 当用户提供的是 `PDF / Word` 附件、本地文件或文件路径时，应优先使用本命令
- Markdown / TXT 文件仅在用户明确要求“按文件上传 / 不要读取内容”时，优先使用本命令；否则允许直接走 `addContentSource`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--notebookId` | string | ✅ | 笔记本 ID，从 selectNotebookList 获取 |
| `--files` | string / json-array | ✅ | 本地文件路径，支持三种传入方式（见示例） |
| `--displayNames` | string / json-array | ❌ | 与 `files` 一一对应的显示名/原始文件名；提供后优先用于笔记本来源标题 |

**支持的文件格式**：

| 格式 | 扩展名 |
|------|------|
| PDF | `.pdf` |
| Word | `.docx` `.doc` |
| Markdown | `.md` |
| 纯文本 | `.txt` |

**限制**：
- 本次上传文件**总大小最大 100MB**（与平台限制一致）
- 不支持的格式会在 `failedFiles` 中单独报告，不影响其他文件的上传
- 若本次上传文件**总大小超过 100MB**，则本批文件会**整体拒绝上传**，并统一在 `failedFiles` 中报告
- 来源添加为异步流程，解析完成后才能用于问答
- **仅 `canEdit=true` 的笔记本可上传文件**；`canEdit=false`（只读分享）的笔记本禁止调用此命令
- 若本地文件名已被上游改成时间戳，建议通过 `--displayNames` 传入用户原始文件名；否则笔记本来源标题默认取本地文件名

**示例**:

```bash
# 单个文件（字符串形式）
edi mbooklm addFileSources \
  --notebookId "abc123" \
  --files ./report.pdf

# 多个文件（JSON 数组形式）
edi mbooklm addFileSources \
  --notebookId "abc123" \
  --files '["./report.pdf", "./notes.md", "./spec.docx"]'

# 多个文件（多次传参形式）
edi mbooklm addFileSources \
  --notebookId "abc123" \
  --files report.pdf --files notes.md

# 本地文件名是时间戳时，显式指定笔记本里显示的原始文件名
edi mbooklm addFileSources \
  --notebookId "abc123" \
  --files '["/tmp/files/1709697600.pdf"]' \
  --displayNames '["浅谈人工智能.pdf"]'
```

**输出（默认）**:
```
📤 正在上传 2 个文件到笔记本...
✅ 2 个文件已成功加入笔记本（处理中，稍后可用于问答）
  • report.pdf
  • notes.md
```

```
📤 正在上传 2 个文件到笔记本...
✅ 1 个文件已成功加入笔记本（处理中，稍后可用于问答）
  • report.pdf
❌ 1 个文件失败：
  • invalid.xlsx — 不支持的文件类型 .xlsx（支持：pdf, docx, doc, txt, md）
```

**输出（--raw）**:
```json
{
  "totalCount": 1,
  "successFiles": ["report.pdf"],
  "failedFiles": [
    {
      "fileName": "invalid.xlsx",
      "reason": "不支持的文件类型 .xlsx（支持：pdf, docx, doc, txt, md）"
    }
  ]
}
```

**`failedFiles` 常见错误原因**：

| 错误原因 | 说明 |
|---|---|
| `文件不存在：<路径>` | 路径不正确或文件已删除 |
| `文件总大小 XXX MB 超过 100MB 限制` | 本次上传的文件总和超过平台限制 |
| `不支持的文件类型 .xxx（支持：pdf, docx, doc, txt, md）` | 格式不在支持列表内 |
| `文件上传 HTTP 错误 4xx/5xx` | 网络或服务端异常，可重试 |
