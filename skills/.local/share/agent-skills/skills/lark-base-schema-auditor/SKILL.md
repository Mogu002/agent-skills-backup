---
name: lark-base-schema-auditor
description: "检查飞书 Base 数据表字段是否符合记录中的字段设计或 schema 要求，输出缺失、多余及类型差异。用户给出目标 Base 链接字段和检查标准字段，或要求核对多维表格字段类型时使用。NOT for 修改表结构、校验记录值或普通数据分析。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
---

# Lark Base Schema Auditor

把来源记录中的“目标 Base 链接”和“字段设计文本”解析出来，读取目标表的真实字段元数据，再用确定性脚本给出逐字段审计结果。整个流程只读。

## 输入与边界

最小输入：

1. 来源 Base URL；当前对话中最近一个无歧义的 Base URL 也可以。
2. 存放目标 Base 链接的字段名，例如“Base链接-副本”。
3. 存放检查标准的字段名，例如“数据表设计”。

记录选择按以下优先级处理：

1. 用户明确给出的 `record_id`。
2. 用户明确说“第一条”且 URL 带视图时，取该视图当前排序下第一条可见记录。
3. URL 带视图但用户未指定记录时，默认取第一条可见记录，并在结果中报告 `record_id`。
4. URL 不带视图时，用 `+base-block-list` 的 `records_count` 或 `+record-list --limit 2` 判断记录数；只有一条时使用该记录，有多条时询问记录，不猜测。

本 Skill 检查字段集合与字段类型。默认不检查记录值，也不要求单选/多选选项文本一致。用户明确要求检查选项时才启用精确选项检查；中英文翻译、同义词等语义选项对应关系需单独说明，不能伪装成脚本已验证。

以下请求不属于本 Skill：

- 创建、删除、重命名或修改字段：转 `lark-base`。
- 检查单元格内容、统计记录或生成业务分析：转 `lark-base` 的数据检索分析路径。
- 仅定位 Base、表或字段 ID，不做 schema 对照：使用 `lark-base-reader`。
- 没有 Base 上下文的通用数据建模建议。

## 执行前

1. 读取 `lark-base-reader` 的 `SKILL.md` 和它要求的只读 reference，按其规则解析 URL、身份和对象。
2. 进入表字段读取时再读取 `lark-base` 的 `SKILL.md`；不要展开写入分支。
3. 将本 Skill 目录下 `scripts/audit_schema.py` 的绝对路径记为 `AUDITOR`。
4. 创建临时工作目录保存 CLI JSON 与映射文件；完成后删除。不要把 Base 内容、URL 或 token 写回 Skill 包。

默认使用 `--as user`。遇到 `token_missing`、`need_user_authorization`、`missing_scopes` 或 `verify_failed` 时停止 Base 读取并转 `lark-shared`；不要静默切换身份。

## 默认工作流

### 1. 定位来源记录

先解析来源 URL：

```bash
lark-cli base +url-resolve --url "<source-url>" --as user --format json
```

确认返回的 `base_token`、`table_id`、`view_id` 和对象类型。没有 `table_id` 时使用 `+base-block-list`；只有唯一数据表时可直接采用，多表且目标不明确时询问用户。

读取来源表字段并确认用户给出的两个字段名真实存在：

```bash
lark-cli base +field-list --base-token "<source-base-token>" --table-id "<source-table-id>" --limit 200 --as user --format json
```

字段返回达到 200 个或带继续分页信号时继续按 `offset` 读取。字段名不存在或不唯一时列出最接近的真实名称并询问，不做模糊替换。

只投影两个必要字段。对于“第一条”或默认视图第一条：

```bash
lark-cli base +record-list --base-token "<source-base-token>" --table-id "<source-table-id>" --view-id "<source-view-id>" --field-id "<target-link-field>" --field-id "<requirements-field>" --limit 1 --as user --format json
```

将原始 JSON 保存为临时 `source-record.json`。已有明确 `record_id` 时改用 `+record-get`，仍只投影这两个字段：

```bash
lark-cli base +record-get --base-token "<source-base-token>" --table-id "<source-table-id>" --record-id "<record-id>" --field-id "<target-link-field>" --field-id "<requirements-field>" --as user --format json
```

先让脚本提取链接、标准与记录标识：

```bash
python3 "$AUDITOR" extract-inputs --record-file "<tmp>/source-record.json" --target-field "<target-link-field>" --requirements-field "<requirements-field>"
```

脚本要求目标字段恰好包含一个 HTTP(S) URL，并要求检查标准至少能解析出一个 `字段名（字段类型）` 条目。退出码 `2` 表示输入不确定或格式无效，此时停止并报告具体原因。

### 2. 定位目标表并读取完整字段

对脚本返回的 `target_url` 执行 `+url-resolve`。目标 URL 已指向数据表时使用返回的 `table_id`；只指向 Base 时执行：

```bash
lark-cli base +base-block-list --base-token "<target-base-token>" --as user --format json
```

选择规则：

- 只有一张数据表：直接使用。
- URL 指向明确数据表：使用该表。
- 多张表：只有表名与设计主题存在唯一明确对应时才采用；否则询问用户。
- 不要遍历并合并多张表的字段。

读取完整字段：

```bash
lark-cli base +field-list --base-token "<target-base-token>" --table-id "<target-table-id>" --limit 200 --as user --format json
```

将原始 JSON 保存为临时 `target-fields.json`。返回达到 200 个字段或带继续分页信号时继续按 `offset` 读取，并在审计前合并 `fields` 数组；不能拿第一页冒充完整 schema。

### 3. 建立字段语义映射

脚本只自动匹配规范化后同名字段。字段中英文不同或存在清晰同义关系时，由 Agent 创建临时 JSON 映射：

```json
{
  "字段映射中的要求字段": "目标表中的真实字段名"
}
```

映射规则：

- 先匹配同名字段，再处理翻译或语义等价名称。
- 只接受含义唯一明确的配对；不要按字段顺序强配。
- 一个实际字段只能映射给一个要求字段。
- 实际字段重名时，映射值改用 `field_id`。
- 无法确定的字段保持未映射，让脚本报告 `missing` 与 `unexpected`。

映射只解决字段名称，不改变类型判断。不要因为名字语义相近就把 `number/plain` 当成货币、进度或评分。

### 4. 运行确定性审计

默认严格检查字段集合，且只检查类型：

```bash
python3 "$AUDITOR" audit --record-file "<tmp>/source-record.json" --target-field "<target-link-field>" --requirements-field "<requirements-field>" --actual-file "<tmp>/target-fields.json" --mapping-file "<tmp>/mapping.json" --format json
```

按需开关：

- 用户明确要求选项文本也一致：增加 `--check-options`。
- 用户明确只检查标准中列出的字段、允许目标表有其他字段：增加 `--allow-extra`。
- 需要便于直接展示的表格：把 `--format json` 改为 `--format markdown`。

退出码：

- `0`：全部要求通过，且严格模式下没有多余字段。
- `1`：审计完成但存在差异；这是正常审计结果，不是工具故障。
- `2`：输入、映射或 JSON 无法可靠解析；不要继续猜测。

脚本按 `type + style + multiple/bidirectional` 区分字段类型。例如：

- 文本 / 电话号码 / Email / 条码分别是 `text/plain`、`text/phone`、`text/email`、`text/barcode`。
- 数字 / 货币 / 进度 / 评分分别是 `number/plain`、`number/currency`、`number/progress`、`number/rating`。
- 单选 / 多选分别是 `select/single`、`select/multiple`。
- 单向关联 / 双向关联分别是 `link/one_way`、`link/two_way`。

未知要求类型返回 `unsupported_requirement`，不能降级成文本或只比较顶层 `type`。

## 输出

先给结论，再给证据：

1. `通过` 或 `不通过`。
2. 来源 `record_id`、目标 Base 和目标表名称。
3. 要求字段数、实际字段数、匹配数、类型不符、缺失和多余数量。
4. 差异表：要求字段、实际字段、要求类型、实际类型、状态。
5. 若进行了语义映射，列出映射；不确定映射单独标记。
6. 明确说明是否检查了选项，以及字段分页是否完整。

只有实际执行脚本且获得退出码后才能声称通过。CLI 读取成功但脚本未运行，只能报告“已读取，尚未完成审计”。

## 停止条件

- 来源记录、目标链接、标准字段或目标数据表无法唯一确定。
- 权限或认证恢复未完成。
- 字段数超过当前已完整读取的范围。
- 标准格式无法解析，或要求类型不在脚本支持列表中。
- 用户要求写入修复；先结束审计并报告差异，再把修改请求交给 `lark-base`，不在本 Skill 内自动修表。
