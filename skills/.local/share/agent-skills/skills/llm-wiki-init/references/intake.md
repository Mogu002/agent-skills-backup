# 初始化访谈

目标是用一轮结构化确认拿到足够信息，同时让没有知识库经验的用户可以直接采用推荐配置。

## 提问方法

先检查目标目录，把已有答案填入草案；只问未知或冲突项。将问题合并成一张配置表，并明确标出推荐选择。结尾告诉用户：

> 你可以回复“全部按推荐”，也可以只修改编号，例如“4 改成中文 slug，11 使用 qmd”。

不要要求用户先理解 RAG、BM25、frontmatter 等术语；用结果和代价解释选择。

## 推荐配置

以下是个人/小团队研究型知识库的默认起点。

| # | 设计项 | 推荐选择 | 示例与说明 |
|---|---|---|---|
| 1 | 使用场景 | 长期研究/学习；1-5 名使用者；Agent 写、用户审阅 | “持续整理 AI Agent 评测资料，并能回答跨文档问题” |
| 2 | source 来源 | 网页、论文、书籍摘录、会议纪要、个人笔记；网页默认保存内容快照，URL 只作元数据 | `web/`、`papers/arxiv/`、`books/`、`meetings/` |
| 3 | 可信度 | 原始/权威资料可作为证据；AI 生成 source 的 verification 默认 `unverified`，不能循环自证 | 外部聊天记录先进入 `notes/ai/`，核验后再支撑 reviewed 页面 |
| 4 | source 命名 | `YYYY-MM-DD-<semantic-slug>.<ext>`；完整标题存 manifest；ID 由内容哈希派生 | `2026-04-04-llm-wiki.md`，`src_a1b2c3d4e5f6` |
| 5 | source 层级 | 按来源渠道分 1-2 层，最多 3 层；不按主题分目录 | `raw/sources/github/karpathy/`，而不是 `raw/sources/ai/knowledge/` |
| 6 | wiki 层级 | `sources/`、`concepts/`、`syntheses/` 三类页面 | 来源摘要、跨来源概念、值得长期保留的比较/判断 |
| 7 | wiki 命名与语言 | 文件名 lowercase kebab-case；标题和正文用用户主要语言；Obsidian 根相对双链 | `concepts/knowledge-compilation.md`，标题可为“知识编译” |
| 8 | tags | lowercase kebab-case、单数、少而稳定；用命名空间表达必要维度 | `agent-evaluation`、`source-type/paper`；不把每个关键词都变成 tag |
| 9 | 页面证据 | frontmatter 声明 `type/status/sources/tags`；关键事实就近链接 raw source | `status: draft/reviewed/disputed/stale` |
| 10 | 运行方式 | 默认逐篇摄取并由用户看摘要；查询结果通过 gate 后才沉淀 | 高价值比较可进入 synthesis，普通问答留在聊天 |
| 11 | 检索 | 数百页内：`index.md` + 零依赖 Python 词法检索；出现真实漏召回后升级 qmd | 命令：`search`、`context`、`status`、`lint` |
| 12 | 附件 | `raw/assets/<source_id>/`；影响含义的图片需单独查看 | PDF 图表、扫描页、网页图片 |
| 13 | 隐私与版本 | local-first、Git 版本记录；敏感资料在导入前分类，不依赖 `.gitignore` 做访问控制 | 团队机密仓库应使用真实权限和加密存储 |
| 14 | Agent 契约 | Codex 用 `AGENTS.md`；Claude 用 `CLAUDE.md`；多 Agent 环境可生成等价入口 | 根文件只做路由，详细流程放 `schemas/` |

## 必须确认的内容

即使采用推荐配置，也要让用户看到并确认以下决策：

1. **知识库目标**：要积累什么知识，典型问题和成功标准是什么？
2. **用户与权限**：个人、团队还是公开；哪些内容禁止入库？
3. **来源范围**：允许哪些格式和渠道；网页是保存快照还是只存 URL？
4. **证据政策**：AI 摘要、个人判断、二手资料是否能作为证据，如何标记？
5. **命名语言**：文件 slug、页面标题、正文和 tags 使用什么语言？
6. **目录深度**：source 按渠道、组织、项目或其他稳定维度分层；wiki 需要哪些页面类型？
7. **检索选择**：推荐词法脚本、qmd、已有系统或用户指定方案？
8. **摄取节奏**：逐篇确认、批量处理还是自动队列？谁有最终审核权？
9. **引用粒度**：来源级、章节级还是 claim-level；哪些页面状态允许被引用？
10. **目标 Agent/工具**：Codex、Claude Code、其他 Agent、Obsidian、Git 和运行环境。

## 场景化补充问题

只在相关场景出现时提问：

- **高风险专业领域**：是否要求 primary-source-only、段落级引用、双人复核或 reviewed gate？
- **团队协作**：是否需要 PR review、页面所有权、单写者规则、访问权限和审计保留期？
- **大量 PDF/音视频**：是否需要 OCR、转录、sidecar 文本和原文件哈希？
- **已有资料迁移**：是否允许复制、重命名、生成快照；如何保留旧链接？
- **自动同步**：外部系统是只读 feeder、双向同步还是定期快照；失败和过期如何标记？
- **多语言**：是否保留原文语言、翻译标题、别名和跨语言检索？

## 配置确认模板

```markdown
## LLM Wiki 初始化配置草案

- 目标与典型问题：<...>
- 使用者与隐私：<...>
- sources：<类型、导入方式、证据级别>
- source 命名/ID：<...>
- source 目录：<...>
- wiki 页面/目录：<...>
- 页面与 tag 命名：<...>
- 引用/状态/冲突：<...>
- 摄取/查询/沉淀/巡检：<...>
- 检索：<默认方案及升级条件>
- Agent/浏览工具/版本控制：<...>
- 现有资料处理：<仅新增、迁移计划或无>

请回复“全部按推荐”，或指出要修改的项目。确认前我不会写入目标目录。
```
