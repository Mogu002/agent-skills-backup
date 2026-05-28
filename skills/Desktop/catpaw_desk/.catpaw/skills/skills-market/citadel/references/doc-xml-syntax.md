# CitadelXML 格式语法参考

CitadelXML 是学城文档的 XML 编辑格式，用于在 AI 编辑场景下替代 CitadelMD，具有以下优势：

- 使用标准 HTML 标签（`p`, `h1-h6`, `ul`, `ol`, `table`），AI 预训练知识直接适用
- 使用 `km-` 前缀的扩展标签（`km-collapse`, `km-note`）表达学城专属宏
- XML 嵌套结构直观，更方便AI进行编辑
- 完整保留 `nodeId` 等关键属性，确保回传后文档结构完全还原

## 获取与回传流程

```bash
# 第一步：获取文档 XML（同时获取 stepVersion 用于并发保护）
oa-skills citadel getDocumentXml --contentId <id> --output doc.xml

# 第二步：由 AI 编辑 doc.xml 文件

# 第三步：回传更新文档
oa-skills citadel updateDocumentByXml --contentId <id> --file doc.xml

# 可选：同时更新文档标题
oa-skills citadel updateDocumentByXml --contentId <id> --file doc.xml --title "新标题"

# 可选：并发保护（传入 getDocumentXml 返回的 stepVersion）
oa-skills citadel updateDocumentByXml --contentId <id> --file doc.xml --step-version 42
```

## 根节点

整个文档以 `<km-doc>` 为根节点：

```xml
<km-doc>
  <km-title nodeId="uuid-xxx">文档标题</km-title>
  <h1 nodeId="uuid-yyy">第一章</h1>
  <p nodeId="uuid-zzz">段落内容</p>
</km-doc>
```

## 编辑规则（必须遵守）

### 基本原则

1. **每次编辑必须重新拉取**：禁止基于对话记忆中的旧内容直接发起覆盖写入
2. **先读后改**：必须先 `getDocumentXml`，禁止凭空生成整篇文档内容覆盖回传
3. **最小改动**：只修改用户明确要求的那几处；无关节点、属性、顺序一律保持原样
4. **保留 nodeId**：所有已有节点的 `nodeId` 属性必须保留；新增节点可省略 `nodeId`（系统自动生成）
5. **不做格式化重写**：禁止把整篇内容"重新整理"为另一种等价写法

### 文档标题

- `<km-title>` 必须是 `<km-doc>` 的**第一个子节点**，有且只有一个
- 修改文档标题时，需同时修改 `<km-title>` 内容 AND 在 `updateDocumentByXml` 传 `--title` 参数

```xml
<km-title nodeId="uuid-xxx">我的文档标题</km-title>
```

## 块级节点

### 段落

```xml
<p nodeId="uuid-xxx">普通段落内容</p>

<!-- 带对齐和缩进 -->
<p nodeId="uuid-xxx" align="center" indent="1">居中缩进段落</p>
```

### 标题（h1-h6）

```xml
<h1 nodeId="uuid-xxx">一级标题</h1>
<h2 nodeId="uuid-xxx">二级标题</h2>
<h3 nodeId="uuid-xxx">三级标题</h3>
```

### 列表

```xml
<!-- 无序列表 -->
<ul nodeId="uuid-xxx">
  <li nodeId="uuid-yyy">
    <p nodeId="uuid-zzz">列表项内容</p>
  </li>
  <li nodeId="uuid-aaa">
    <p nodeId="uuid-bbb">另一个列表项</p>
  </li>
</ul>

<!-- 有序列表 -->
<ol nodeId="uuid-xxx">
  <li nodeId="uuid-yyy">
    <p nodeId="uuid-zzz">第一项</p>
  </li>
</ol>

<!-- 任务列表：必须在 <ul> 上写 data-task-list="true"，在 <li> 上写 data-checked -->
<!-- ⚠️ 禁止使用 <km-task-list> 或 <km-task-item> 等非标准形式 -->
<ul data-task-list="true" nodeId="uuid-xxx">
  <li data-checked="false" nodeId="uuid-yyy">
    <p nodeId="uuid-zzz">未完成任务</p>
  </li>
  <li data-checked="true" nodeId="uuid-aaa">
    <p nodeId="uuid-bbb">已完成任务</p>
  </li>
</ul>
```

### 引用块

```xml
<blockquote nodeId="uuid-xxx">
  <p nodeId="uuid-yyy">引用内容</p>
</blockquote>
```

### 代码块

> ⚠️ **必须使用 `<pre><code>` 格式**，禁止写成 `<km-code-block>` 或 `<code-block>` 等其他形式。

```xml
<!-- language / title / theme 均不能省略，必须显式写出 -->
<pre language="TypeScript" title="代码块" theme="xq-light" nodeId="uuid-xxx"><code>const hello = "world";
console.log(hello);</code></pre>

<!-- 自定义标题示例 -->
<pre language="Python" title="示例代码" theme="xq-light" nodeId="uuid-yyy"><code>print("hello")</code></pre>
```

> **`code_block` 属性约束**：
> - `language` **不能为 `null`**，未指定时必须使用字符串 `"Plain Text"`
> - `theme` **不能为 `null`**，未指定时必须使用字符串 `"xq-light"`
> - `title` 必须是一行纯文本，不能包含换行符；未指定时使用 `"代码块"`
> - ⚠️ **`language` 大小写必须严格匹配**，例如必须写 `"Mermaid"` 而非 `"mermaid"`，`"Plain Text"` 而非 `"plain text"`，`"JavaScript"` 而非 `"javascript"`
> - 支持的 `language` 枚举值（共 40 种）：
>   `Plain Text`、`JavaScript`、`Java`、`JSON`、`Shell`、`HTML`、`PlantUML`、`Mermaid`、
>   `C`、`C++`、`C#`、`CSS`、`Dart`、`Elm`、`Go`、`Groovy`、`HTTP`、`JSX`、`Kotlin`、
>   `LaTeX`、`Lua`、`Markdown`、`Nginx`、`Objective-C`、`Perl`、`PHP`、`PowerShell`、
>   `Python`、`R`、`Ruby`、`Sass`、`Scala`、`SQL`、`Stylus`、`TypeScript`、`Swift`、
>   `Vue.js Component`、`XML`、`YAML`、`Mindmap`

### 分割线

```xml
<hr nodeId="uuid-xxx" />
```

### 表格

⚠️ **编辑表格时，禁止修改 `colspan` / `rowspan` / `colwidth` / `textAlign` / `verticalAlign` / `bgColor` / `color` / `numCell` 等结构属性**，除非用户明确要求改布局。

**新建表格规则**：
- 默认使用 `responsive="true"`（自适应宽度），不要使用 `responsive="false"`（固定宽度）。
- 新建表格的单元格（`<th>`/`<td>`）**不要指定 `colwidth` 属性**，学城会根据内容自动计算列宽。
- 只有在复制或编辑已有固定宽度表格时，才保留原有的 `colwidth` 值。
- **新建表格时，每个单元格（`<th>`/`<td>`）必须显式加上 `numCell="0"` 属性**，无论是否合并单元格，一律写 `numCell="0"`。遗漏会导致列宽计算异常。

```xml
<!-- 新建自适应宽度表格（推荐，不指定 colwidth，每格带 numCell="0"） -->
<table borderWidth="1" responsive="true" nodeId="uuid-xxx">
  <tr nodeId="uuid-row1">
    <th numCell="0" nodeId="uuid-th1">列标题1</th>
    <th numCell="0" nodeId="uuid-th2">列标题2</th>
  </tr>
  <tr nodeId="uuid-row2">
    <td numCell="0" nodeId="uuid-td1">单元格1</td>
    <td numCell="0" nodeId="uuid-td2">单元格2</td>
  </tr>
</table>

<!-- 带合并单元格的新建表格 -->
<table borderWidth="1" responsive="true" nodeId="uuid-xxx">
  <tr nodeId="uuid-row1">
    <td colspan="2" numCell="0" nodeId="uuid-td1">跨两列的单元格</td>
  </tr>
  <tr nodeId="uuid-row2">
    <td numCell="0" nodeId="uuid-td2">普通单元格</td>
    <td numCell="0" nodeId="uuid-td3">普通单元格</td>
  </tr>
</table>
```

## 学城扩展节点（km- 前缀）

### 折叠块（collapse）

```xml
<km-collapse active="true" nodeId="uuid-xxx" titleNodeId="uuid-t" contentNodeId="uuid-c">
  <km-title>折叠标题</km-title>
  <km-content>
    <p nodeId="uuid-yyy">折叠内容段落</p>
  </km-content>
</km-collapse>
```

### 提示块（note）

`type` 可选值：`info`（信息，蓝色）/ `note`（警示，黄色）/ `warning`（注意，红色）/ `tip`（提示，绿色）

```xml
<km-note type="warning" nodeId="uuid-xxx" titleNodeId="uuid-t" contentNodeId="uuid-c">
  <km-title>注意</km-title>
  <km-content>
    <p nodeId="uuid-yyy">这是一条警告信息</p>
  </km-content>
</km-note>
```

### 图片

```xml
<img src="https://km.sankuai.com/api/file/cdn/xxx" name="图片名称" width="800" height="600" nodeId="uuid-xxx" />
```

⚠️ **禁止直接填写非学城图片 URL**。必须先调用 `uploadImageToDocument` 上传，再使用返回的 URL。

### 附件

```xml
<km-attachment src="https://km.sankuai.com/api/file/cdn/xxx" name="文件名.pdf" size="12345" nodeId="uuid-xxx" />
```

### 视频

```xml
<km-video src="https://km.sankuai.com/api/file/cdn/xxx" name="视频名称.mp4" width="640" height="480" nodeId="uuid-xxx" />
```

### 音频

```xml
<km-audio src="https://km.sankuai.com/api/file/cdn/xxx" name="音频名称.mp3" nodeId="uuid-xxx" />
```

### Draw.io 流程图

```xml
<km-drawio src="https://km.sankuai.com/api/file/cdn/xxx?contentType=0" width="800" height="600" nodeId="uuid-xxx" />
```

### 思维导图（minder）

```xml
<km-minder src="https://km.sankuai.com/api/file/cdn/xxx" width="800" height="600" nodeId="uuid-xxx" />
```

### LaTeX 数学公式

```xml
<!-- 块级公式：必须使用 <km-latex>，禁止写成 <km-latex-block> -->
<km-latex nodeId="uuid-xxx">E = mc^2</km-latex>

<!-- 行内公式（在段落内使用） -->
<p nodeId="uuid-p"><km-latex-inline nodeId="uuid-xxx">E = mc^2</km-latex-inline></p>
```

### Markdown 嵌入块

> ⚠️ **内容必须用 `<![CDATA[...]]>` 包裹**，否则 Markdown 中的特殊字符（如 `<`、`>`、`&`）会导致 XML 解析错误。

```xml
<km-markdown nodeId="uuid-xxx"><![CDATA[
## 标题

这里是 Markdown 内容
]]></km-markdown>
```

### HTML 嵌入块

> ⚠️ **内容必须用 `<![CDATA[...]]>` 包裹**，否则 HTML 标签会被当作 XML 元素解析，导致内容丢失。

```xml
<km-html nodeId="uuid-xxx"><![CDATA[
<div style="color:red">自定义 HTML</div>
]]></km-html>
```

### PlantUML 图表

> ⚠️ **内容必须用 `<![CDATA[...]]>` 包裹**，否则 PlantUML 语法中的特殊字符会导致 XML 解析错误。

```xml
<km-plantuml width="400" height="300" nodeId="uuid-xxx"><![CDATA[
@startuml
A -> B : 消息
@enduml
]]></km-plantuml>
```

### 目录（catalog）

```xml
<km-catalog style="none" nodeId="uuid-xxx" />
```

### 内嵌多维表格（xtable）

```xml
<km-xtable xtableId="12345" nodeId="uuid-xxx" />
```

### 开放链接卡片（open_link / open_card）

```xml
<!-- open_link：带预览的链接卡片（块级），url 属性不能省略 -->
<km-open-link url="https://km.sankuai.com/collabpage/123" title="文档标题" nodeId="uuid-xxx" />

<!-- open_card：嵌入式内容卡片（块级），url 属性不能省略 -->
<km-open-card url="https://km.sankuai.com/collabpage/456" type="doc" nodeId="uuid-xxx" />
```

> ⚠️ **属性名必须是 `url`**，不能写成 `href`。
>
> ⚠️ **`url` 不能为空或 `null`**：`url` 为空的 `<km-open-link>` / `<km-open-card>` 节点会在前端渲染时崩溃。转换器已对原文中 `url`/`href` 均为空的旧节点做自动丢弃处理；AI 编辑时**不得**新增或保留 `url` 为空的此类节点。

### @提及用户

```xml
<km-mention name="张三" uid="user-uid-xxx" empId="emp-id-xxx" />
```

### 时间

```xml
<km-time date="1747036800000" />
<!-- 显示时间（精确到时分） -->
<km-time date="1747036800000" showTime="true" />
```

### 状态标签

```xml
<km-status pattern="default" color="blue" nodeId="uuid-xxx">进行中</km-status>
```

### Emoji

```xml
<km-emoji name="thumbsup" />
```

## 行内样式

### 基本格式

```xml
<strong>粗体</strong>
<em>斜体</em>
<u>下划线</u>
<del>删除线</del>
<code>行内代码</code>
<sub>下标</sub>
<sup>上标</sup>
```

### 颜色和字号

```xml
<!-- 文字颜色（推荐写法） -->
<span color="#ff0000">红色文字</span>

<!-- 背景颜色（推荐写法） -->
<span bg="#ffff00">黄色背景</span>

<!-- 字号（推荐写法） -->
<span font-size="18">大字号文字</span>
```

> **兼容写法**：系统同时支持 HTML 标准 `style` 属性，以下写法会被自动解析为对应 mark：
>
> ```xml
> <!-- style 兼容写法（与推荐写法等价） -->
> <span style="color: #ff0000">红色文字</span>
> <span style="background-color: #ffff00">黄色背景</span>
> <span style="font-size: 18px">大字号文字</span>
>
> <!-- 也可在一个 style 中写多个属性（自动拆分为多层 mark） -->
> <span style="color: #ff0000; background-color: #ffff00; font-size: 18px">组合样式</span>
> ```
>
> 推荐优先使用 `color`、`bg`、`font-size` 写法，更简洁。`style` 写法作为兼容方案，便于 AI 生成时直接沿用 HTML 习惯。

### 组合样式

**关键规则：每个 `<span>` 只能携带一个样式属性（`color`、`bg`、`font-size` 三选一）。多种样式必须用多层 `<span>` 嵌套，语义标签（`<strong>`、`<em>`、`<u>` 等）可与 `<span>` 混合嵌套。**

```xml
<!-- ✓ 正确：粗体 + 红色文字（语义标签在外，span 在内）-->
<strong><span color="#ff0000">粗体红色文字</span></strong>

<!-- ✓ 正确：粗体 + 斜体 + 黄色背景 -->
<strong><em><span bg="#ffff00">粗斜体黄背景</span></em></strong>

<!-- ✓ 正确：字号 + 颜色（两层 span，外大内色）-->
<span font-size="20"><span color="#0000ff">大号蓝色文字</span></span>

<!-- ✓ 正确：字号 + 颜色 + 背景色（三层 span）-->
<span font-size="20"><span color="#0000ff"><span bg="#ffff00">大号蓝字黄背景</span></span></span>

<!-- ✓ 正确：粗体 + 下划线 + 红色 -->
<strong><u><span color="#ff0000">粗体下划线红色</span></u></strong>
```

**⚠️ 错误写法（只会识别第一个属性，其余被丢弃）：**

```xml
<!-- ✗ 错误：单个 span 不能同时写多个样式属性 -->
<span color="#ff0000" font-size="20">混合属性</span>
<!-- 实际效果：只应用 color，font-size 被忽略 -->

<!-- ✗ 错误：单个 span 不能同时写 color 和 bg -->
<span color="#ff0000" bg="#ffff00">颜色和背景</span>
<!-- 实际效果：只应用 color，bg 被忽略 -->
```

### 链接

```xml
<a href="https://example.com">链接文字</a>
<!-- 带 nodeId -->
<a href="https://km.sankuai.com/collabpage/123" nodeId="uuid-xxx">学城文档链接</a>
```

### 换行

```xml
段落内换行使用 <br /> 标签
```

## 常见编辑场景示例

### 在指定位置插入新段落

找到目标位置，在相邻节点之间插入（新增节点可省略 `nodeId`）：

```xml
<!-- 在 h2 标题后插入新段落 -->
<h2 nodeId="uuid-existing">现有标题</h2>
<p>新增的段落内容（无需 nodeId，系统自动生成）</p>
<p nodeId="uuid-next">原有的下一段</p>
```

### 修改段落内容

保留 `nodeId`，只修改文本内容：

```xml
<!-- 修改前 -->
<p nodeId="uuid-xxx">旧内容</p>

<!-- 修改后 -->
<p nodeId="uuid-xxx">新内容</p>
```

### 在表格单元格中添加内容

只修改目标单元格内容，保留所有结构属性（**包括 `numCell`，不要删除**）：

```xml
<td colspan="1" rowspan="1" numCell="0" textAlign="" verticalAlign="" bgColor="" color="" nodeId="uuid-td">
  <p nodeId="uuid-p">修改后的单元格内容</p>
</td>
```

### 修改文档标题

**必须同时做两件事**：
1. 修改 `<km-title>` 内的文字
2. `updateDocumentByXml` 时传 `--title "新标题"`

```xml
<!-- 修改 km-title 节点 -->
<km-title nodeId="uuid-title">新的文档标题</km-title>
```

```bash
oa-skills citadel updateDocumentByXml --contentId <id> --file doc.xml --title "新的文档标题"
```

## 与 CitadelMD 格式对比

| 特性 | CitadelXML（推荐） | CitadelMD |
|------|------------------|-----------|
| AI 理解准确率 | ✅ 高（标准HTML + 明确标签） | ⚠️ 中（自定义语法） |
| 嵌套深度处理 | ✅ 直观（XML嵌套） | ⚠️ 需计数 `:::` 层级 |
| 1.0旧版文档 | ❌ 不支持 | ✅ 支持（降级到HTML） |
| 适用场景 | 编辑、创建 2.0 文档 | 编辑、创建 2.0/1.0 文档 |

## 后端 Schema 约束（JSON 结构规则）

学城后端在接收文档时会进行严格的 Schema 校验。生成或编辑文档时必须遵守以下规则，否则提交会报错。

### 支持的节点类型

后端仅接受以下节点类型，**任何其他类型均会导致校验失败**：

| 分类 | 支持的类型 |
| --- | --- |
| 文档根节点 | `doc` |
| 块级节点 | `paragraph`, `heading`, `blockquote`, `code_block`, `horizontal_rule` |
| 列表 | `bullet_list`, `ordered_list`, `task_list`, `list_item`, `task_item` |
| 表格 | `table`, `table_row`, `table_cell`, `table_header` |
| 媒体 | `image`, `audio`, `video`, `attachment` |
| 折叠/提示 | `collapse`, `collapse_title`, `collapse_content`, `note`, `note_title`, `note_content` |
| 代码/公式 | `latex_block`, `markdown`, `html` |
| 嵌入内容 | `catalog`, `spaceupdate`, `page_tree`, `gantt`, `data2chart`, `calendar`, `plantuml`, `drawio`, `minder`, `xtable` |
| 卡片/链接 | `open_iframe`, `open_link`, `open_card` |
| 其他块级 | `appendix`, `not_support`, `control`, `doc_list_view`, `title`, `footnote_list`, `footnote_list_item` |
| 行内节点 | `text`, `hard_break`, `mention`, `link`, `time`, `status`, `emoji`, `latex_inline`, `footnote` |

### 支持的 Mark 类型

| mark 类型 | 说明 | 必填 attrs |
| --- | --- | --- |
| `strong` | 加粗 | 无 |
| `em` | 斜体 | 无 |
| `underline` | 下划线 | 无 |
| `strikethrough` | 删除线 | 无 |
| `code` | 行内代码 | 无 |
| `color` | 文字颜色 | `color`（颜色值） |
| `backgroundcolor` | 背景色 | `color`（颜色值） |
| `font` | 字体大小 | `dataSize`（整数，px） |
| `sub` | 下标 | 无 |
| `sup` | 上标 | 无 |
| `quote` | 划词评论引用 | `quoteId`（字符串） |

### doc 根节点的 title 约束

`doc` 根节点对 `title` 有严格的位置和数量约束：

| 约束 | 说明 |
| --- | --- |
| **第一个子节点必须是 `title`** | `doc.content[0]` 必须是 `title` 节点，不能是 `heading`、`paragraph` 等 |
| **有且只有一个 `title`** | `title` 不能出现多次 |
| **`title` 之后至少有一个内容节点** | `title` 后面必须跟 `paragraph`、`heading` 等内容节点 |

> ❌ **常见错误**：用 `<h1>` / `heading` 代替 `<km-title>` 作为文档第一个节点。  
> `heading` 是正文内的标题样式（如章节标题），`title` 是文档元数据标题，**两者完全不同**，不能混用。

### content 数量约束

以下节点类型要求 `content` 不为空（AT_LEAST_ONE），否则后端会报错：

- `doc`：文档根节点，必须有至少一个子节点
- `bullet_list`、`ordered_list`、`task_list`：列表不能为空
- `blockquote`：引用块不能为空
- `collapse_content`：折叠块内容不能为空
- `note_content`：提示框内容不能为空
- `footnote_list`、`footnote_list_item`：脚注列表不能为空

### 子节点类型约束

| 父节点 | 允许的子节点类型 |
| --- | --- |
| `table` | 只能是 `table_row` |
| `table_row` | 只能是 `table_cell` 或 `table_header` |
| `bullet_list`、`ordered_list` | 只能是 `list_item` |
| `task_list` | 只能是 `task_item` |
| `collapse` | 必须包含 `collapse_title` 和 `collapse_content` |
| `note` | 必须包含 `note_title` 和 `note_content` |
| `footnote_list` | 只能是 `footnote_list_item` |

### text 节点规则

- `text` 节点**必须**包含 `text` 字段（字符串）
- `text` 节点**不应**包含 `content` 字段

## 注意事项

1. **仅支持 2.0 文档**：`getDocumentXml` / `updateDocumentByXml` 不支持学城 1.0 旧版文档（HTML 存储）；若文档是 1.0 格式，请改用 `getDocumentCitadelMd` / `updateDocumentByMd`
2. **nodeId 保留规则**：已有节点的 `nodeId` 必须保留；新增节点省略 `nodeId` 即可（系统自动分配）
3. **不要修改结构属性**：除非用户明确要求，禁止修改表格的 `colspan` / `rowspan` / `colwidth` / `numCell` 等布局属性；编辑已有单元格时必须保留原有 `numCell` 值
4. **附件类资源必须先上传**：图片、附件、视频、音频必须先通过对应的 `upload*ToDocument` 命令上传，不能直接填写外部 URL
5. **CDATA 内容不转义**：`km-markdown` / `km-html` / `km-plantuml` 节点内的内容使用 `<![CDATA[...]]>` 包裹，不需要 XML 转义
6. **新建表格单元格必须写 `numCell="0"`**：`<th>` 和 `<td>` 都必须显式加上此属性，遗漏会导致列宽计算异常
