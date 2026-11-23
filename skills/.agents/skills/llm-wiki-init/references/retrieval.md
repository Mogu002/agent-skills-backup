# 检索方案

检索是导航层，不是知识库的主存储。无论选择哪种方案，raw source、wiki Markdown、manifest 和契约都必须可以在没有索引服务时独立审阅和恢复。

## 默认：本地词法检索

适用于个人/小团队、Markdown 为主、数百个来源和数百页面以内的起点。

提供一个 Python 标准库脚本，至少支持：

```text
add <file> --title ... --url ... --collection ... --date ...
pending
search <query> [--raw]
context <query>
lint
status
```

推荐行为：

- `add` 复制来源、生成稳定 source ID、计算 SHA-256，并向受控 JSONL manifest 追加登记项。
- `search` 默认只搜已编译 wiki，中文使用连续片段/二元片段，英文按词切分；标题可加权。
- `context` 先返回相关 wiki 页面，再只回查这些页面声明的 raw sources。
- `lint` 检查来源哈希、未登记来源、frontmatter、source ID、断链和孤页。
- 索引无需持久化；每次从 Markdown 重建即可。

优势是零服务、可测试、可移植。限制是同义词和概念级召回较弱。不要把“未来可能规模很大”当成提前引入向量库的理由。

## 升级：qmd 或同类本地混合检索

仅在以下任一症状持续出现时采用：

- 页面达到数百到数千，词法检索经常漏掉用户已知存在的相关页面；
- 多语言、缩写、同义词使关键词难以表达；
- 已经有可维护的本地 embedding/索引环境；
- 用户明确要求 hybrid BM25/vector search 或 MCP 检索。

初始化时仍保留 `index.md` 和简单 fallback。记录索引重建命令、包含/排除路径、模型依赖和验证查询。索引不得成为唯一事实来源。

## 接入既有搜索系统

当团队已有企业搜索、数据库或文档平台时，先确认：

- 它搜索 raw、wiki 还是两者；
- Agent 能否取得稳定路径、source ID 和可引用片段；
- 权限是否与文件层一致；
- 索引延迟、删除、版本和断链如何处理；
- 系统不可用时的本地 fallback。

如果不能稳定回到 raw source，现有搜索只能作为候选召回器，不能作为证据层。

## 极小库：只用 index 和 `rg`

用户明确只想维护几十页、且不需要来源登记自动化时，可以使用 `index.md` + `rg`。仍建议保留 manifest/hash 和 lint；它们解决的是证据完整性，不是搜索规模。

## 选择记录

在 README 或配置中写清：

- 当前方案和选择理由；
- 搜索范围；
- 查询示例；
- 已知限制；
- 触发升级的可观察症状；
- 回退方式。
