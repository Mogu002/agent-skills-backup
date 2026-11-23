---
name: lark-eval-accuracy
description: "读取飞书多维表格中「审核结果 + 人员字段」并计算标注/质检准确率（总体 + 分人），再按目标表格式批量写入准确率汇总表。当用户给出 Base URL 或 base_token/table_id，需要统计标注准确率、质检准确率、看每个评测/审核人员的正确率，或希望把结果写入准确率总表时使用。人员字段支持 user、select、text；脚本会自动选择常见字段名并对文本/选项里的人名做 open_id 解析。NOT for 通用 Base 数据读取/写入/聚合查询（走 lark-base）；也不负责非「审核结果 + 人员字段」这套字段规约的自定义统计。"
---

# 飞书多维表格 - 准确率统计与写入

> **前置条件：** 认证 / scope / 登录态 → [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)；Base 通用规则 → [`../lark-base/SKILL.md`](../lark-base/SKILL.md)；写入 CellValue 规范 → [`../lark-base/references/lark-base-cell-value.md`](../lark-base/references/lark-base-cell-value.md)。所需 scope：读 `bitable:app:readonly`，写 `bitable:app`；文本 / 选项型人名解析为 open_id 需 `contact:user:readonly`。

## 处理姿态（先内化，再动手）

- **计算结果只信脚本**：所有总数、错误数、正确率只信 [scripts/calc_accuracy.py](scripts/calc_accuracy.py) 输出，禁止在对话里手算后直接报数。
- **先分清评测类型**：`标注` 和 `质检` 的正确率口径不同；在跑脚本前先确定 `--eval-type`，不要混用。
- **先识别 reviewer 字段，不猜空列**：标注默认找 `评测人员` → `评测人`；质检默认找 `审核人员` → `审核人`。常见情况是后一个同名近义字段为空。
- **总体总数不含空 reviewer**：`总数` 和正确率分母默认排除 `评测人员` / `审核人员` 为空的记录；不要把空 reviewer 行算进总体准确率。
- **不静默吞未知结果选项**：如果 `审核结果` 出现脚本未覆盖的新选项，停下来问用户如何计错，不要自行归到“通过”。
- **写目标表前先 `--dry-run`**：确认行数、人员、正确率、父/子项目后，再去掉 `--dry-run` 真正写入。
- **父项目由 agent 判断**：脚本只透传 `--parent-project`，不替你猜 `Decision / Workflow / Table ...`。

## 关键 gotchas（读了再动，不看会翻车）

1. **人员字段现在有三种合法类型**：`user`、`select`、`text` 都可能出现。`auto` 会先 `field-get` 探测；识别不出时再用 `--reviewer-field-type user|select|text` 强制指定。
2. **标注和质检的默认 reviewer 字段不同**：标注优先 `评测人员`，其次 `评测人`；质检优先 `审核人员`，其次 `审核人`。不要沿用标注字段名去跑质检表。
3. **质检表里常同时存在 `审核人员` 和 `审核人`**：`审核人` 可能只是历史字段或空列。脚本会按默认优先级自动选择；人工排障时也先看哪列真有值。
4. **select / text 型人员字段只信真人**：脚本会对每个名字调用 `contact +search-user --query <name>` 精确匹配 `name`；像 `image.png`、`0`、`decision 错题` 这类脏值会被过滤并出现在 skip 报表里。
5. **多人共审 = 每人各计一次**：user 多选会展开到每个 reviewer；text 一般是单值，select 也可能多选，脚本一律按“分人展开”口径统计。
6. **空 reviewer 记录默认只进 skip，不进总体**：哪怕 `审核结果` 有值，只要 reviewer 为空，就不进入总体 `总数` 和正确率分母；需要排障时可用 `--include-null` 看「未指派」桶，但总体口径仍不回收这些记录。
7. **`子项目` 是严格枚举 select**：目标表若缺少传入选项，飞书不会静默新建。脚本默认会自动追加；不想污染目标表时传 `--no-auto-add-option`。
8. **`正确率` 写目标表时必须是小数**：例如 90% 要写 `0.9` 而不是 `90%` 或 `90`。
9. **目标表 `人员` 字段只吃 open_id**：select / text 型人名必须先解析成 open_id；解析不到的整行不会写入，并会出现在 skip 报表中。

## 正确率规则（脚本内置，改规则改 `scripts/calc_accuracy.py`）

### 标注

| 审核结果 | 是否计错 | 写入列 |
|---|---|---|
| `通过` | 否 | `通过` |
| `通过-保留一轮结果` | 否 | `保留后` |
| `通过-修改后` | 是 | `修改` |
| `异常` | 是 | `异常` |

公式：`正确率 = 1 - (count(通过-修改后) + count(异常)) / 总数`。其中 `总数` 不包含 reviewer 为空的记录。

### 质检

| 审核结果 | 是否计错 | 写入列 |
|---|---|---|
| `通过` | 否 | `通过` |
| `通过-保留一轮结果` | **是** | `保留后` |
| `通过-修改后` | 否 | `修改` |
| `异常` | 否 | `异常` |

公式：`正确率 = 1 - count(通过-保留一轮结果) / 总数`。其中 `总数` 不包含 reviewer 为空的记录。

## 默认工作流

1. **提取源表 / 目标表信息**：从 URL 里取 `/base/<base_token>` 和 `?table=<table_id>`，并保留完整源表 URL 给 `--source-url`。
2. **先确定评测类型**：明确这次是 `标注` 还是 `质检`，因为 reviewer 默认字段和正确率口径都依赖 `--eval-type`。
3. **检查字段元信息**：至少核对 `审核结果` 选项，以及脚本自动选中的 reviewer 字段名 / 类型。
4. **识别父项目**：先读目标表 `父项目` 现有选项，再根据源 Base 名判断应该写哪个选项；不要把这个判断外包给脚本。
5. **先跑 dry-run**：看总体、分人、skip 报表，以及将要写入的行。
6. **确认后正式写入**：dry-run 无误后去掉 `--dry-run`。

## 常用命令

```bash
# 只统计标注准确率（默认优先找 评测人员 / 评测人）
python3 ./scripts/calc_accuracy.py \
  --base-token <base_token> --table-id <table_id> \
  --eval-type 标注

# 只统计质检准确率（默认优先找 审核人员 / 审核人）
python3 ./scripts/calc_accuracy.py \
  --base-token <base_token> --table-id <table_id> \
  --eval-type 质检

# 质检准确率 + 写入目标表（先 dry-run）
python3 ./scripts/calc_accuracy.py \
  --base-token <src_base_token> --table-id <src_table_id> \
  --write-base-token <dst_base_token> --write-table-id <dst_table_id> \
  --eval-type 质检 \
  --parent-project Decision \
  --source-url "https://bytedance.larkoffice.com/base/<base_token>?table=<table_id>&view=<view_id>" \
  --date 2026-07-01 --dry-run
```

## 参数速查

| 参数 | 默认 | 说明 |
|---|---|---|
| `--base-token` / `--table-id` | 必填 | 源表 |
| `--result-field` | `审核结果` | 覆盖审核结果字段名 |
| `--reviewer-field` | 按 `eval-type` 自动选 | 标注默认 `评测人员` → `评测人`；质检默认 `审核人员` → `审核人` |
| `--reviewer-field-type` | `auto` | `auto` / `user` / `select` / `text` |
| `--include-null` | off | 把未指派 reviewer 的记录归到「未指派」桶用于排障，但不计入总体 `总数` / 正确率分母 |
| `--write-base-token` / `--write-table-id` | 都为空 | 目标准确率汇总表；两者必须成对提供 |
| `--eval-type` | `标注` | `标注` / `质检`，同时决定正确率口径和默认 reviewer 字段候选 |
| `--parent-project` | `""` | 父项目选项（由 agent 判断后透传） |
| `--sub-project` | `<Base 名> - <源表表名>` | 覆盖 `子项目` |
| `--source-url` | `""` | 源表完整分享链接（含 `view`），写入 `作业表URL` |
| `--date` | 今天 | `YYYY-MM-DD`；写入 `日期` |
| `--dry-run` | off | 只打印不写入 |
| `--auto-add-option` | on | 目标表 `子项目` / `父项目` 缺选项时自动追加 |
| `--no-auto-add-option` | – | 关闭自动追加，缺选项就停下来报错 |

## 目标表字段约定

目标表列名/类型需对齐：

`日期` datetime · `类型` select · `父项目` select · `子项目` select · `作业表URL` text · `总数`/`通过`/`保留后`/`修改`/`异常` number · `正确率` number(百分比) · `人员` user。

## References

- [output-sample.md](references/output-sample.md)：完整输出样例（含分人表格与写入行预览）。
- [troubleshooting.md](references/troubleshooting.md)：字段脏值、选项预检、多人共审口径、CLI 报错等排障说明。
- 上游：[`../lark-base/references/lark-base-record-batch-create.md`](../lark-base/references/lark-base-record-batch-create.md) 是写入 payload 规范。
