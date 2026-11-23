# 初始化蓝图

本蓝图描述最小职责和一致性要求。目录名与字段名可以按用户确认结果调整，但不能只改文档而遗漏脚本、测试或 Agent 契约。

## 推荐目录

```text
<root>/
├── AGENTS.md                 # 薄的任务路由与常驻不变量
├── README.md                 # 人类入口、命令和首条来源示例
├── raw/
│   ├── manifest.jsonl        # 受控来源注册表：身份、路径、URL、日期、哈希
│   ├── sources/              # 登记后不可变，可按来源渠道分层
│   └── assets/               # 来源附件，推荐 assets/<source_id>/
├── wiki/
│   ├── index.md              # 当前内容地图
│   ├── log.md                # append-only 操作时间线
│   ├── open-questions.md     # 冲突、薄弱证据和未知信息
│   ├── sources/              # 每个 raw source 的结构化摘要
│   ├── concepts/             # 跨来源概念页
│   └── syntheses/            # 值得长期保留的比较、分析或决策
├── schemas/
│   ├── write.md              # 新增来源、摄取、更新与沉淀
│   ├── query.md              # 库内问答与证据回查
│   └── maintenance.md        # lint、矛盾、过时、孤页治理
├── references/               # 仅放 schema 按条件加载的细节
├── scripts/
│   └── llmwiki.py            # 或用户确认的等价确定性工具
└── tests/
    ├── test_agent_contract.py
    └── test_llmwiki.py
```

如果目标 Agent 不使用 `AGENTS.md`，生成它认可的等价入口；多入口文件应共享同一事实来源，避免复制后漂移。

## 根契约

根契约保持短小，只包含所有任务都需要的内容：

1. raw source 的不可变性；
2. wiki 是可维护综合而非原始证据；
3. 非常识性事实就近引用 raw source；
4. 来源观点、Agent 推断、用户判断和未知信息的区分；
5. 冲突与证据缺口进入 open questions；
6. index 是当前地图，log 只追加历史；
7. 优先更新已有页面，避免近义重复；
8. 按任务加载 write/query/maintenance schema 的路由表；
9. schema 缺失或不可读时停止对应阶段。

不要把全部页面模板、命令帮助和维护细节塞进根契约。

## Schema 路由

### Write

用于新增来源、摄取、创建/更新页面和沉淀回答。至少规定：

- source 命名、collection、ID、SHA-256 和 manifest；
- 页面 frontmatter；
- 摄取时先读 index、相关页面和 open questions；
- 一条新证据如何路由到来源页、已有 concept、新 concept 或 open question；
- 写入后同步 index、双链、frontmatter 和 append-only log；
- 运行 pending 与 lint。

### Query

任何可能与库内主题相关的知识性问题都先检索本地 wiki，用户不必说“基于知识库”。至少规定：

- 先读 index，再用 context/search 路由；
- 影响结论的主张回查 raw source；
- `draft`、`disputed`、`stale` 页面强制回查；
- 证据不足时不以模型记忆冒充库内事实；
- 回答后才判断是否值得沉淀；
- 未经用户要求或同意，不写 wiki。

### Maintenance

只在明确巡检时加载。至少区分：

- 确定性错误：哈希、manifest、frontmatter、断链、重复 source ID；
- 语义问题：矛盾、过时、重复、错误抽象、证据薄弱；
- “发现”与“已修复”；
- 删除/合并前的证据和入链检查；
- 修复后重新 lint 并追加 log。

## 来源清单

推荐 JSONL 每行一个对象：

```json
{"id":"src_a1b2c3d4e5f6","title":"LLM Wiki","path":"raw/sources/github/karpathy/2026-04-04-llm-wiki.md","url":"https://gist.github.com/...","collection":"github/karpathy","source_date":"2026-04-04","added_at":"<ISO-8601 import time>","verification":"verified","sha256":"..."}
```

要求：

- ID 稳定且唯一，推荐由内容 SHA-256 前 12 位派生；
- path 是仓库根相对路径；
- `source_date` 表示来源发布日期/事件日期，`added_at` 表示导入时间；
- 内容去重优先于文件名去重；
- 常规导入只追加 manifest 记录；合法路径迁移是显式、可审计的例外，必须同步 manifest、引用和 log，且不得改变 ID/hash；
- AI 生成、二手转述等来源可用 `verification: unverified` 标记；它们在核验前不能单独支撑 `reviewed` 页面；
- 未登记文件由 lint 报告，不擅自删除。

## 页面契约

推荐 frontmatter：

```yaml
---
title: 人类可读标题
type: source | concept | synthesis
status: draft | reviewed | disputed | stale
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources:
  - src_a1b2c3d4e5f6
tags:
  - lowercase-tag
---
```

来源页额外包含：

```yaml
source_id: src_a1b2c3d4e5f6
source_hash: <sha256>
collection: github/karpathy
source_date: YYYY-MM-DD
```

正文规则：

- 使用标题表达页面职责，不用文件名承担全部语义；
- 关键主张附近用相对 Markdown link 指回 raw source；
- 页面之间使用目标笔记工具支持、且仓库可解析的链接；
- concept 综合多来源，不复制粘贴来源摘要；
- synthesis 明确问题、结论、依据、限制和待验证项；
- 无足够来源时不要建立“空壳概念页”。

## 特殊页面

### `wiki/index.md`

按页面类型或稳定领域列出所有可发现页面，每项包含链接和一句摘要。每次 ingest 或页面职责变化时更新。

### `wiki/log.md`

只追加，使用可解析标题：

```markdown
## [YYYY-MM-DD] init | Wiki initialized
## [YYYY-MM-DD] ingest | <source title>
## [YYYY-MM-DD] query | <persisted result>
## [YYYY-MM-DD] lint | <scope>
```

### `wiki/open-questions.md`

每项记录问题、触发证据、当前状态、需要的来源或用户决策。问题解决后保留结论或移动到 resolved 区，不静默删除历史。

## README

必须让新用户在几分钟内完成：

1. 查看状态；
2. 添加第一条 source；
3. 让 Agent 摄取 pending source；
4. 基于 wiki 提问；
5. 运行 lint；
6. 在 Obsidian 或编辑器中浏览。

同时说明 raw/wiki/schema 三层、命名约定、当前检索方案与升级条件。

## 最小测试

确定性工具至少覆盖：

- 同内容去重；
- collection 路径校验和目录深度；
- 日期与 slug 命名；
- manifest/hash 一致性；
- pending 到 processed 的状态变化；
- 中英文或目标语言搜索；
- context 优先 wiki、再回查声明的 raw source；
- 缺字段、未知 source ID、断链、孤页与 raw 篡改；
- 根契约仍保持薄路由，schema/reference 链接存在。

## 初始化安全

- 创建前列出将新增、保留、冲突的路径。
- 已存在文件默认保留；需要改写时展示差异并取得用户确认。
- 不把测试样例混入真实 raw sources。
- 不自动抓取用户未批准的外部内容。
- 不安装 qmd、embedding 模型或其他依赖，除非用户已确认相应检索方案。
- 不把绝对本机路径、账号、token 或临时目录写入模板。
