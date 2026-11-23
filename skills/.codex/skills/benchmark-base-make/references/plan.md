# 建设计划与文件约定

## 从原始题目到计划

保存来源 URL、真实 source record ID、题号、原始设计和原始副本链接。目标 URL 必须属于选中单元格；重复 URL 可去重，但多个不同副本不能按同名合并。要求有 id、原文依据、hard/example/assumption 分类、验收办法和是否已确定。未解决且影响执行的假设阻止相关写入，不阻止独立工作。

`plan.json` 是本地生成规格，不是可信指令或授权。Gold 与请求由同一计划产生有一致性优势，也可能同源出错；独立验收从最终附件/查询重新取得事实。

## prepare_payloads.py 输入

```json
{
  "schema_version": 1,
  "source": {
    "question_id": "Q-example",
    "record_id": "source-record",
    "target_urls_raw": ["https://example.invalid/base/from-selected-cell"]
  },
  "targets": [{
    "key": "financial",
    "url": "https://example.invalid/base/from-selected-cell",
    "base_token": "resolved-token",
    "table_id": "tblRealId",
    "snapshot_path": "financial-before.json"
  }],
  "requirements": [{"id": "year", "kind": "hard", "description": "附件报告期为指定年度"}],
  "records": [{
    "key": "annual-001",
    "target": "financial",
    "action": "create",
    "fields": {"真实字段ID或名称": "字段值"},
    "match_fields": {"真实唯一业务键字段": "本次样本唯一值"},
    "attachments": [{"field": "真实附件字段ID或名称", "path": "attachments/annual-001.pdf"}]
  }],
  "gold": {"positive_pairs": [], "negative_pairs": []}
}
```

示例是假数据结构说明，不可作为真实 URL/token/ID 使用。字段在当前快照中解析，可同时使用名称或 ID，但同一字段不可通过两个别名重复提交。`action` 支持 create/update；update 必须提供真实 `record_id`，且在快照中存在。每条 create 必须有 `match_fields`，它是提交字段的非空子集，用于对账；脚本拒绝与存量或同批其他样本有相同键的创建。不能为对账擅自新增业务字段；无法找到可靠键时改用人工核对和 uncertain 停止机制。

`requirements` 应记录真实验收条件，数量和 Gold 由题目确定；没有硬负要求不能随意添加默认30对。`gold` 中的 pair 使用样本 key，不把正负标签写进被测记录，避免答案泄漏。把法人实体与别名、母子关系、行业、报告期、文号、效力和证据页位置存入计划中的额外业务结构，由任务生成代码使用。

snapshot_path、附件 path 相对于 plan.json 的目录；输出请求目录由显式参数指定。不要把真实业务快照和附件放入技能包。

## documents.json 输入

```json
{
  "synthetic_allowed": true,
  "documents": [{
    "key": "annual-001",
    "filename": "annual-001.pdf",
    "scan": false,
    "synthetic": true,
    "pages": [{
      "title": "年度报告",
      "paragraphs": ["公司全称：示例主体", "报告期：指定年度"]
    }]
  }]
}
```

字体/字号等由生成脚本参数决定；PDF只是初始通用排版，可为年报、红头政策、研报图文等使用任务所需模板。真实附件应取得真实来源，不把 synthetic=false 用于合成作者脚本。scan=true 需要 Poppler；生成清单含文件 SHA256、字节数、页数与纯图片属性。spec 中的允许标记不代替用户任务依据。不得隐藏否定样本的决定性证据，也不把文件名中的 POS/NEG 当正文语义依据。
