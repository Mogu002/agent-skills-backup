---
name: change-note-checker
description: 核验飞书多维表格中"对应样张变动说明"字段的内容是否与它指向的目标 Base 真实结构和数据一致。给定一个带 table 和 view 的主控 Base 链接，逐题（一行一题、无状态）解析【修改样张（已创建副本）】字段中的副本 Base 链接、对照该目标 Base 检查变动说明，仅把错误条目的原文压缩写回【机评-2】并在【检查结果-2】写"有问题"；全部吻合则写"无问题"，机评-2 留空；目标 Base 无法访问时只在机评-2 注明未能核验。适用：样张变动说明检查、变动说明核对、机评回填、样张核查、批量核验变动条目。
author: lijiahao.vsat
---

# 样张变动说明核验

对主控表视图内的每一行：解析【修改样张（已创建副本）】字段指向的副本目标 Base，逐条核对 `对应样张变动说明` 中的声明，把结果回写 `机评-2` 与 `检查结果-2`。

## 核心口径（与用户约定）

1. 只回写 `机评-2`、`检查结果-2` 两个字段，不动其他列。
2. **只认明确反证**：找到与声明矛盾的事实才算错误；无法证实也无法证伪的开放集合条目不判错。
3. `机评-2` 只放**错误条目的原文压缩**（保持原意、保留表名/字段名/ID/rid 等定位坐标），编号分条；不加证据、打分、总评。
4. 表名与 table_id、字段名与 field_id **必须同时精确一致**，任一不符即错。
5. 数量：精确数字必须一致；约数（~/约/左右）允许 ±10%；显式清单逐条核对。
6. 指定 rid 100% 逐条读全文核对；开放集合用全表关键词搜索 + 至多 10 条抽样，搜到反例才判错。
7. 每题独立、无状态，不携带上一题的上下文；同一目标 Base 的表/字段元数据可跨题缓存复用。
8. 运行范围默认只处理 `检查结果-2` 为空的行；用户要求"全量重跑"时处理视图全部行。覆盖写幂等，中途失败可直接续跑。

## 工作流程

### 1. 解析主控表链接

从用户给的 Base 链接取 base_token / table_id / view_id：

```bash
lark-cli base +url-resolve --url "<base链接>" --format json
```

### 2. 拉取待检查行

脚本通过 `bash` 工具直接执行，调用时设置 **include_secrets=true**（lark-cli 需要注入的访问凭证）。

```bash
python3 scripts/fetch_source_rows.py \
  --base-token <主控base_token> --table-id <tbl> --view-id <vew> \
  --mode empty
```

`--mode empty`（默认）只保留 `检查结果-2` 为空的行；全量重跑用 `--mode all`。输出 `temp_data/rows.jsonl`，每行含 record_id / item_id / sample_url / note。

### 3. 构建目标 Base 元数据缓存

从 rows.jsonl 提取去重后的目标 base token，一次性探查表、字段并缓存（多个题目指向同一 Base 时复用，避免重复探查）：

```bash
python3 scripts/build_meta_cache.py
```

输出 `temp_data/meta/<token>.json`；无法访问的 Base 标记 `accessible: false`。

### 4. 逐题核验（无状态，3–5 题并发）

以**子代理**方式执行，每个子代理只处理一道题、互不共享上下文：

- 每波发起 **3–5 个** general 子代理（单条消息内并发多个 agent 调用）；波次串行推进。
- 每个子代理任务中必须完整嵌入 [references/check-rules.md](references/check-rules.md) 的内容（子代理看不到本 skill，规则要直接写进任务描述），并提供：
  - `record_id`、`item_id`、`note` 全文、目标 base token；
  - 元数据缓存文件绝对路径 `temp_data/meta/<token>.json`，要求优先读缓存、不够再实时调用 lark-cli；
  - 明确返回格式：单个 JSON 对象 `{record_id, item_id, status, critique}`，无其他文字。
- 子代理执行 lark-cli 命令同样需要凭证——任务描述中注明其 bash 调用设置 include_secrets=true。
- 元数据缓存命中 `accessible: false` 的题可直接按 inaccessible 返回，无需再发起核验。

子代理返回后，把 JSON 逐行汇总写入 `temp_data/results.jsonl`（由主代理统一写文件，避免并发追加冲突）。status 取值：

| status | 含义 | 回写效果 |
|---|---|---|
| `ok` | 变动说明每条都对得上（含 note 为空） | 检查结果-2="无问题"，机评-2 清空 |
| `problem` | 存在明确反证的错误条目 | 检查结果-2="有问题"，机评-2=压缩错误条目 |
| `inaccessible` | 修改样张字段为空/链接无法解析 / 目标 Base 无权限或已删除 | **检查结果-2 留空不写**，机评-2 注明未能核验 |

### 5. 回写结果

```bash
python3 scripts/write_back.py \
  --base-token <主控base_token> --table-id <tbl>
```

串行分批回写（每批 100 条，≤200 上限），遇 `1254291` 写冲突自动等待重试；失败会中止并提示，重跑同一命令即可，不产生重复数据。回写完成后抽查 2–3 条用 `+record-get` 读回确认。

### 6. 汇总报告

使用 `lark-doc` skill 创建一份飞书文档作为汇总报告，内容包含：

- 运行范围：视图总行数、本次处理行数、运行模式（空行/全量）、主控 Base 链接；
- 结果统计：有问题 / 无问题 / 未能核验各多少条；
- 有问题题目清单：ID + 机评-2 全文（按 ID 排序）；
- 未能核验题目清单：ID + 原因。

文档创建后把链接返回给用户，并在对话中给出三档统计数字。

## 异常处理

- 【修改样张（已创建副本）】字段为空或链接不含 base token：按 inaccessible 处理，机评-2 写 `修改样张链接无法解析，未能核验`。
- 单题核验中 lark-cli 持续报错（非权限问题）：该题按 inaccessible 返回并在机评-2 注明实际原因，不阻塞整批。
- 子代理返回非法 JSON：让其按 schema 重新返回一次；仍失败则该题暂不写入 results.jsonl，留在下一轮空行模式处理。

## 资源说明

- [scripts/fetch_source_rows.py](scripts/fetch_source_rows.py)：分页拉取视图题目行
- [scripts/build_meta_cache.py](scripts/build_meta_cache.py)：目标 Base 表/字段元数据缓存
- [scripts/write_back.py](scripts/write_back.py)：结果串行回写（只写两个目标字段）
- `references/check-rules.md`：单题核验完整规则（嵌入子代理任务）
- `temp_data/`：rows.jsonl、meta/、results.jsonl 等运行时中间产物，已在 .skillignore 中忽略
