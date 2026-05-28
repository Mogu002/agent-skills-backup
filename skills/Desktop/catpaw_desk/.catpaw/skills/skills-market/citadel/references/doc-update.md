> ❌ **严禁调用 `updateDocument`**：该命令会将 Markdown 文本直接追加写入文档后端，导致文档出现重复 title、结构错乱，且**无法自动回滚**。所有文档内容编辑必须且只能通过下方的流程完成。

# 编辑/更新/插入新内容到学城文档指南

编辑/更新/插入新内容到学城文档是一个高危操作。学城文档的底层数据是基于 ProseMirror 生成的 JSON 结构，其中可能包含大量 Markdown 语法无法描述的特殊定制宏（如：包含合并单元格的表格，表格嵌套表格，特定的卡片、嵌入的第三方组件、文字颜色/背景色/对齐方式、展开卡片等）。

## 编辑路径：CitadelXML 安全更新（零数据丢失）

**CitadelXML** 使用标准 HTML 标签（`<p>`、`<h1>`–`<h6>`、`<table>` 等）加 `km-` 前缀扩展标签完整编码所有自定义宏节点，**100% 保留文档结构**，不会产生任何数据丢失。

> 📖 **CitadelXML 完整语法**（标签名、属性规则、编辑示例）：查看 [doc-xml-syntax.md](doc-xml-syntax.md)

### 完整工作流

```bash
# 第一步：获取文档 CitadelXML 内容（同时记录 stepVersion）
oa-skills citadel getDocumentXml --contentId <id> --output doc.xml

# 第二步：由 AI 编辑 doc.xml 文件

# 第三步：回传更新文档（强烈建议传入 stepVersion 以开启并发保护）
oa-skills citadel updateDocumentByXml --contentId <id> --file doc.xml --step-version <stepVersion>

# 可选：同时更新文档标题
oa-skills citadel updateDocumentByXml --contentId <id> --file doc.xml --step-version <stepVersion> --title "新标题"
```

#### 推荐给模型的执行指令

处理文档编辑时，优先遵循下面这段口令：

1. 先读取原始 XML，再在原文上做**最小改动**
2. 只改用户明确要求的内容，不重排、不润色、不统一格式、不改无关节点
3. 保留所有不理解的 `km-*` 标签节点，宁可原样保留，也不要猜测后重写
4. 复杂表格直接编辑 `<tr>`/`<td>`/`<th>` 内部内容，不要重建表格结构
5. 默认不改表格结构属性、资源 ID、图表配置、嵌入卡片参数
6. 回传前检查：`<km-title>` 仍在首位且内容为**纯文本**、标签全部闭合、没有把局部修改扩散到整篇文档
7. `<km-note>`/`<km-collapse>` 的标题必须是**一行普通文本**；正文放在对应的 content 子标签中
8. `<km-note>` 如果写了标题，默认按"展示标题"处理；不要生成"有标题但隐藏标题"的结构

---

### 编辑注意事项

1. **保留所有宏节点**：任何 `<km-*>` 标签节点，若不需要修改则原样保留
2. **不要修改资源标识**：`<km-drawio>`、`<km-minder>`、`<km-gantt>`、`<km-xtable>`、`<km-open-iframe>` 等节点的 `nodeId` / `src` / `attachmentId` 等标识默认必须保留
3. **扩展表格按 HTML 结构编辑**：使用标准 `<table>`、`<tr>`、`<th>`、`<td>` 标签，直接修改单元格内容即可
4. **不要随意改表格结构属性**：除非用户明确要求调整布局，否则保留 `colspan` / `rowspan` / `colwidth` / `textAlign` / `verticalAlign` / `bgColor` / `color`
5. **空单元格保留为空块**：允许 `<td>`/`<th>` 为空，转换时会自动补空 paragraph
6. **新增表格时第一行必须是表头行**：优先使用 `<th>`，不要首行全部写成 `<td>`
7. **新增表格默认使用自适应宽度**：新建表格必须使用 `responsive="true"`（自适应宽度），不要使用 `responsive="false"`（固定宽度）；新建表格的单元格不要指定 `colwidth` 属性，学城会根据内容自动分配列宽；只有在编辑已有固定宽度表格时才保留原有 `colwidth` 值
8. **脚注节点保留 ID**：`<km-footnote-item>` 的正文可改，但 `footnoteNodeId` / `nodeId` 必须原样保留
9. **块级图表配置按子标签保留**：`<km-data2chart>` 内部配置可按原文保留，不要擅自重写结构
10. **空行分隔块**：不同的块元素之间的 XML 格式保持一致，列表项之间不额外加空行
11. **行内节点不跨块**：所有行内节点（`<a>`、`<km-mention>` 等）必须在同一段落内，不能跨块
12. **不要扩大修改范围**：如果用户只要求替换一句话、一个标题、某个表格单元格，就不要把整段甚至整篇重新生成
13. **不要把等价语法来回转换**：例如不要把现有复杂表格改写成另一种表述，不要把现有宏节点改成纯文本占位
14. **宏标题只写首行**：`<km-note>`/`<km-collapse>` 标题只写一行；其余正文、补充段落写到对应的 content 子标签内
15. **`<km-title>` 只能是纯文本**：文档标题节点 `<km-title>` 的内容只能是普通文字，**不能**使用加粗、斜体、下划线、删除线等样式，也不能包含行内宏节点；写入 marks 会被自动剥除

### 结构约束速查（违反将导致 API 报错）

以下规则由转换器在提交前自动校验，AI 生成的 CitadelXML 必须遵守这些约束，否则文档无法保存。

#### 文档顶层结构（doc）

| 约束 | 规则 |
|------|------|
| `<km-title>` 必须存在 | 每篇文档必须有且只有一个 `<km-title>` 节点 |
| `<km-title>` 必须在首位 | `<km-title>` 必须是 `<km-doc>` 的第一个子节点，前面不能有任何其他内容 |
| `<km-title>` 内容为纯文本 | `<km-title>` 里只能有普通文字，**禁止**使用加粗、斜体、下划线、删除线或行内宏节点 |
| `<km-title>` 后必须有内容 | `<km-title>` 之后至少要有一个正文块（`<p>`/`<h1>`–`<h6>` 等） |
| `<km-appendix>` 最多一个 | 如果存在 `<km-appendix>`，全文只能出现一次；多余的会被自动丢弃 |
| `<km-footnote-list>` 最多一个且必须在最后 | 脚注列表只能出现一次，且必须是文档最后一个块节点；若在中间，会被自动移到末尾 |
| doc 直接子节点类型受限 | `<km-doc>` 下只能放块级节点（`<p>`/`<h1>`–`<h6>`/`<table>`/`<ul>`/`<ol>` 等）、`<km-xtable>`、`<km-appendix>`、`<km-footnote-list>`；**禁止**把 `<tr>` 直接放在 `<km-doc>` 下 |

#### 媒体与资源节点（必填属性）

| 节点 | 必填属性 | 说明 |
|------|----------|------|
| `<img>` | `src`（非空字符串）、`name`（字符串，可为空） | 图片 URL 和名称均不能缺失；`name` 可以是空字符串但不能省略 |
| `<km-audio>` | `src`（非空字符串） | 音频 URL 不能为空 |
| `<km-video>` | `src`（非空字符串） | 视频 URL 不能为空 |
| `<km-attachment>` | `src`（非空字符串） | 附件 URL 不能为空 |

#### 行内特殊节点（必填属性）

| 节点 | 必填属性 | 说明 |
|------|----------|------|
| `<km-mention>` | `uid`（非空字符串） | @用户的 uid 不能为空 |
| `<a>` | `href`（非空字符串） | 链接 URL 不能为空 |
| `<km-time>` | `date`（非零数字 或 非空字符串） | 毫秒时间戳或 `"YYYY-MM-DD"` 格式字符串 |
| `<km-emoji>` | `name`（非空字符串） | emoji 名称不能为空 |

#### 块级结构节点

| 节点 | 约束 |
|------|------|
| `<h1>`–`<h6>` | 层级必须是 **1-6**，不支持其他值 |
| `<td>`/`<th>` | `colwidth` 属性必须是**数组或 null**，不能是字符串或数字 |
| `<km-catalog>` | `style` 属性只能是 `none`/`number`/`circle`/`rect`/`point` 之一（或不填） |
| `<km-note>` | `type` 属性只能是 `info`/`note`/`warning`/`tip` 之一（或不填） |
| `<pre>` / `<code>` 块 | `title` 属性不能包含换行符，必须是一行普通文本 |
| `<km-note-title>`/`<km-collapse-title>` | 只能包含一行标题文字，不能换行；正文必须放到各自的 content 子节点中 |

#### 复杂宏节点（必填属性）

| 节点 | 必填属性 | 说明 |
|------|----------|------|
| `<km-gantt>` | `id`（非空字符串） | 甘特图唯一标识，不能为空；**禁止**新建 `id` 或修改现有 `id` |
| `<km-drawio>` | `src`（非空字符串） | 图形数据存储地址；**禁止**清空此字段 |
| `<km-minder>` | `src`（非空字符串） | 脑图数据地址不能为空；**禁止**修改 `src` |
| `<km-open-link>` | `url`（非空字符串） | 链接卡片 URL 不能为空；**属性名必须是 `url`，禁止写成 `href`**；`url` 为空的旧节点转换时会被自动丢弃，AI 编辑时不得新增或保留 `url` 为空的节点 |
| `<km-open-card>` | `url`（非空字符串） | 卡片嵌入链接不能为空 |
| `<km-open-iframe>` | `src`、`nodeId`、`attachmentId` **三者不能同时为空** | 可以只有 `nodeId`+`attachmentId`（如 WPS Excel 等内嵌文档），但不能三个都空 |
| `<km-data2chart>` | `id`（非空字符串） | 图表唯一标识不能为空；**禁止**修改 `id` |

#### 容器节点结构约束

| 父节点 | 子节点要求 |
|--------|-----------|
| `<table>` | 只能包含 `<tr>`；**禁止** `<td>`/`<th>` 直接出现在 `<table>` 下 |
| `<tr>` | 只能包含 `<td>` 或 `<th>` |
| `<td>`/`<th>` | 只能包含块级节点（`<p>`/`<h1>`–`<h6>`/`<table>`/`<ul>`/`<ol>` 等） |
| `<ul>`/`<ol>` | 只能包含 `<li>` 或 `<km-task-item>` |
| `<km-task-list>` | 只能包含 `<km-task-item>` 或 `<li>` |
| `<li>`/`<km-task-item>` | 只能包含块级节点或 `<km-xtable>` |
| `<blockquote>`/`<km-collapse-content>`/`<km-note-content>` | 只能包含块级节点（`content` 不能为空，至少一个子节点） |
| `<km-collapse>` | 必须包含且只包含 `<km-title>`（标题）和 `<km-content>`（正文） |
| `<km-note>` | 必须包含且只包含 `<km-title>`（标题）和 `<km-content>`（正文） |
| `<km-title>` | 只能有**纯文本**子节点，且该节点**不能携带任何文字样式** |
| `<km-footnote-list>` | 只能包含 `<km-footnote-item>` |
| `<km-footnote-item>` | 只能包含 `<p>`（至少一个，不能为空） |
| `<ul>`/`<ol>`/`<km-task-list>`/`<blockquote>` | `content` **不能为空**，至少有一个子节点 |

#### 文字样式（marks）约束

| 约束 | 规则 |
|------|------|
| 样式类型必须合法 | 只支持 `strong`（加粗）/`em`（斜体）/`underline`/`strikethrough`/`code`/`color`/`backgroundcolor`/`font`/`sub`/`sup`/`quote` |
| `color` | XML 写法：`<span color="#hex">文字</span>`，`color` 属性不能为空 |
| `backgroundcolor` | XML 写法：`<span bg="#hex">文字</span>`，`bg` 属性不能为空 |
| `font`（字号） | XML 写法：`<span font-size="14">文字</span>`，`font-size` 属性不能为空 |
| `quote`（划词评论引用） | XML 写法：`<km-quote quoteId="xxx">文字</km-quote>`，`quoteId` 属性不能为空 |

### 常见禁令

- **禁止** 直接编辑底层 JSON 字符串
- **禁止** 在不了解宏含义时删除或改写 `<km-*>` 节点
- **禁止** 为了"更整洁"而重排整篇文档
- **禁止** 把复杂表格、脚注列表或图表配置重新写回 JSON 片段
- **禁止** 把表格内容（包括单元格文字、行内宏、居中布局）写成 JSON 字符串塞进 `<p>` 的文本节点——这会导致表格结构完全丢失
- **禁止** 自造任何非标准标签或属性来拼接不同格式的内容
- **禁止** 新增或保留 `url` 为空（`null` / 空字符串）的 `<km-open-link>` / `<km-open-card>` 节点——这类节点在前端渲染时会触发 `TypeError` 崩溃；文档中若已存在此类旧节点，转换器会自动丢弃，AI 不得重新写回

---

## 总结

| 命令 | 数据安全 | 推荐 |
|------|----------|------|
| `getDocumentXml` → 修改 → `updateDocumentByXml` | ✅ 完全安全 | ✅ **唯一推荐路径** |

**优先使用 CitadelXML 方式（`getDocumentXml` → 修改 → `updateDocumentByXml`）。保护用户的数据完整性是第一原则。**

**输出** 完成编辑后返回用户文档链接，让用户可以直接点击查看文档变更的内容
