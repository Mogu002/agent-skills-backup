---
name: "lark-base-property-extractor"
description: "提取飞书多维表格字段属性并输出明细表。当用户给出 Base URL，要求查看/核对每个 table 的字段、类型、公式、lookup、关联、视图字段时使用。NOT for 写入或修改 Base。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# Lark Base Property Extractor

## Purpose

Use this skill to turn a Lark/Feishu Base URL into a field-property inventory.

Default output is a Markdown detail table covering every readable table in the Base:

- Base and table identifiers
- field name, field ID, field type
- formula expression, lookup source, link target, select options, number/date style
- visible fields and view metadata when the user asks for view-level checks
- confidence notes for properties that the CLI does not expose directly

This skill is read-only. Do not create, update, delete, or upsert records/fields/views.

## Default Workflow

1. Parse the user-provided URL.
   - Extract `/base/{token}` as `base_token`.
   - If the URL has `?table=tbl...`, treat it as a focus table only when the user asks for a single table.
   - If the user asks for "每个 table" or "全部表", ignore the query table parameter and enumerate all tables.
   - If the URL is `/wiki/{token}`, resolve it first with `lark-cli wiki +node-get`; continue only when the object is `bitable`.
2. Resolve the CLI path.
   - Prefer `lark-cli`.
   - If `lark-cli` is not in `PATH`, try `$HOME/.local/bin/lark-cli`.
   - Use `--as user` by default for user-owned Base resources.
3. Read Base identity.
   - Run `lark-cli base +base-get --base-token <base_token> --as user`.
   - Capture Base name, token, URL, revision, and advanced-permission flag when returned.
4. Enumerate tables.
   - Run `lark-cli base +table-list --base-token <base_token> --as user`.
   - For each returned table, run `lark-cli base +table-get --base-token <base_token> --table-id <table_id> --as user`.
   - Use only table names, field names, field IDs, and view names from real command output.
5. Extract field properties.
   - For every `fields[]` entry, preserve the raw `type`.
   - Preserve `style`, `defaultValue`, `options`, `multiple`, `expression`, `aggregate`, `from`, `select`, `where`, `link_table`, `bidirectional`, and `bidirectional_link_field_id` when present.
   - Translate common types for humans, but keep the raw type in the table.
6. Extract view properties when relevant.
   - Run `+view-list` or use `views[]` from `+table-get`.
   - For visible-field order, run `+view-get-visible-fields`.
   - For filters/sorts/groups, run `+view-get-filter`, `+view-get-sort`, and `+view-get-group` when the user asks for matching/validation.
7. Output a Markdown detail table.
   - Put mismatches or missing properties before broad summaries when the user asks for checking.
   - Do not claim full global conclusions from partial pages.
   - Clearly distinguish "CLI explicitly returned" from "inferred from formula/expression".

## Commands

Use these command shapes as the stable read path:

```bash
lark-cli base +base-get --base-token <base_token> --as user
lark-cli base +table-list --base-token <base_token> --as user
lark-cli base +table-get --base-token <base_token> --table-id <table_id> --as user
lark-cli base +view-list --base-token <base_token> --table-id <table_id> --as user
lark-cli base +view-get-visible-fields --base-token <base_token> --table-id <table_id> --view-id <view_id> --as user
lark-cli base +view-get-filter --base-token <base_token> --table-id <table_id> --view-id <view_id> --as user
lark-cli base +view-get-sort --base-token <base_token> --table-id <table_id> --view-id <view_id> --as user
```

If `lark-cli` is not found:

```bash
$HOME/.local/bin/lark-cli base +table-list --base-token <base_token> --as user
```

## Output Contract

For a full Base inventory, include these tables when data is available.

### Base Summary

| Base 名称 | Base Token | Revision | 高级权限 | URL |
|---|---|---:|---|---|

### Table Summary

| 表名 | Table ID | 主字段 | 字段数 | 视图数 | 备注 |
|---|---|---|---:|---:|---|

### Field Property Detail

| 表名 | 字段顺序 | 字段名 | Field ID | 原始类型 | 人类说明 | 字段格式/样式 | 公式/表达式 | 关联/Lookup/选项 | CLI 确认度 |
|---|---:|---|---|---|---|---|---|---|---|

Recommended mapping for `人类说明`:

| Raw type | Human description |
|---|---|
| `text` | 文本 |
| `number` | 数字；若 `style.type=currency`，说明为货币 |
| `datetime` | 日期/时间；保留 `style.format` |
| `select` | 单选或多选；看 `multiple` 与 `options` |
| `user` | 人员 |
| `group_chat` | 群聊 |
| `link` | 关联记录；保留目标表 ID 与双向关联信息 |
| `lookup` | Lookup；保留来源表、源字段、聚合方式与过滤条件 |
| `formula` | 公式；保留表达式 |
| `auto_number` | 自动编号；保留编号规则 |

### View Field Detail

| 表名 | 视图名 | View ID | 类型 | 筛选 | 排序 | 可见字段顺序 |
|---|---|---|---|---|---|---|

## Critical Gotchas

- Field type and field format are different concepts.
- For formula fields, CLI may return only `type=formula` and `expression`; it may not expose the UI "字段格式" such as 数字/文本/百分比.
- If formula format is absent from CLI output, write `CLI 未返回`; do not mark it as confirmed.
- You may infer result semantics from the expression, but label it as inferred, for example `推断为数值结果，非 CLI 明确返回字段格式`.
- For ordinary number fields, `style` can confirm currency/plain number, precision, percentage, and thousands separator when returned.
- A text field with `style.type=barcode` should be reported as `原始类型=text；样式=barcode`, not as a separate raw `barcode` type.
- Link cell values and link field IDs are relationship keys, not user-readable names. Use table/field metadata to explain relationships.
- `table=spec` or other non-`tbl...` URL parameters may be UI state or unsupported internal references. Confirm with `+table-list` before treating them as tables.
- `has_more=true` means the current result is not full data. For metadata inventory, prefer table/field/view metadata commands over record pages.

## Permission And Auth Handling

- Use `--as user` by default.
- If a command reports missing scope, `permission_violations`, or a hint for authorization, stop and use the Lark shared authorization flow instead of silently switching identity.
- If user identity has resource-level no-access and there is no authorization-recovery hint, retry once with `--as bot` only when appropriate; otherwise report the permission gap.
- Do not run interactive `auth` or `config` commands unless the user explicitly asks for setup.
- If credentials are provided by an external provider, `auth status` or `config show` may fail while normal read commands still work.

## Quality Bar

The answer is complete only when:

- Every table from `+table-list` is accounted for, unless the user asked for a single table.
- Every field from each `+table-get` response appears in the field detail table.
- Formula, lookup, select, link, auto-number, number style, and date style details are preserved when returned.
- Any property not returned by CLI is marked as not returned, not guessed.
- The final response states the read scope: Base token, tables included, and whether view-level details were read.
