# 逐题核验规则（单题、无状态）

本文件是单道题的完整核验规则。处理一题时只携带本题信息：`item_id`、`note`（对应样张变动说明全文）、目标 base token 及其元数据缓存文件路径。**不引用、不假设其他题目的任何信息。**

## 1. 判定总原则

- **只有找到明确反证，才把一个条目标记为错误。**
- 无法证实也无法证伪的声明（典型：无明确范围的开放集合、未给出判定标准的"模板"），**不判错、不写进讥评**。
- 不打总分、不写"不确定"列表、不输出核验过程。最终只产出：有哪些条目错了（如有）。
- 存疑时倾向"无问题"。误判一条正确说明为错误，比漏判危害更大——因为写回的讥评会被当作人工复核的直接线索。

## 2. 解析变动说明

先把 `note` 拆成**原子声明**，每条约等于一个可核验事实。常见结构（实际文本可能混用中英文、markdown、换行）：

- 表定位：`【要在 达人表 tblJnaNZB5X7rLFi 新增】…`
- 字段声明：`字段「In-depth Background Dossier」(fld flddyqziTs,text,单条 ~1k token,全英)`
- 指定记录集合：`A-label anchor (共 8 位,rid=recA,recB,…) 用 A 模板,dossier 必须显式出现关键词: Nordic / …`
- 显式清单：`3 位 A-anchor 类目字段刻意设为「美食」`
- 数量声明：`共 8 位`、`~450 位 baseline`
- 开放集合：`全表其余 ~450 位 anchor 用通用兜底 dossier,不含北欧语义`
- 跨表：同样的声明出现在第二张/第三张表段落中，分别归属到对应表。

注意 `fld flddyqziTs` 这类写法里字段 ID 是第二个 token（flddyqziTs），不要把字面量 "fld" 当成 ID。

## 3. 各类声明的核验方法

### 3.1 表与字段结构（名称 + ID 必须同时精确一致）

先查元数据缓存 `temp_data/meta/<token>.json`，不够再用 `lark-cli base +field-list` 实时补查。

- 表：声明中的表名必须能在 tables 中找到，且 `tbl...` ID 与该表 ID **完全一致**。表名对 ID 错、ID 对表名错、两者都找不到——均判错。
- 字段：字段名、`fld...` ID、类型（text/number/select 等）必须与该表实际字段三者同时吻合。任一不符判错。注意"新增字段"的声明：字段当前不存在 = 明确反证。
- 字段长度/token/词数类约束（如"单条 ~1k token"）：属于约数口径。若说明里出现明确数字要求，抽查指定记录的实际长度，偏差超 ±10% 才判错；无法可靠估算 token 数时不判。

### 3.2 指定 rid 集合（100% 逐条核验）

对显式列出的每个 rid：

1. **存在性**：用 `lark-cli base +record-get --record-id <rid>`（可重复传入，分批每批 ≤100 个）。rid 不存在 → 该条判错，讥评中列出全部缺失 rid。
2. **读全文核对关键词**：对存在的记录，100% 读取声明所针对字段的完整内容，逐个核对"必须显式出现"的关键词：
   - 英文关键词不区分大小写，按子串/词形匹配（`Nordic` 命中 `nordic`；`citation` 命中 `citations`）。
   - 任一必需关键词在该记录中缺失 → 判错，讥评指明是哪些 anchor（用 rid 或说明给出的名称）缺哪些关键词。
3. **叙事性要求**（如"叙述至少一次因证据不足公开拒稿"）：指定 rid 是封闭集合且已读全文，内容中明确不存在相应叙事 = 明确反证，判错；语义模糊到无法判定则不判。
4. "用 A 模板"这类标签：若该模板在本题上下文中可由紧随其后的关键词/特征列表操作化，按列表核对；若没有任何可核对的定义，不判。

### 3.3 数量与清单

- **精确数字**（`共 8 位`、`3 位刻意设为美食`）：必须精确一致。用 `+record-list --filter-json` 或 `+record-search` 按声明可识别的条件计数。声明同时给出 rid 清单时，以逐条核对为准。
- **约数**（`~450`、`约`、`左右`）：实际值落在声明值 ±10% 内即视为吻合。
- **显式列举的清单**：按列举内容逐条核对，每条不符都独立判错（例如清单里 3 个 rid 中 1 个的类目字段不是"美食"，即该条错）。
- 计数条件无法映射到真实字段（说明用了自创标签而表里没有对应数据列）→ 无法核验，不判错。

### 3.4 开放集合（全表搜索 + 少量抽样）

典型声明："其余全部 baseline anchor 不含北欧语义""其他品牌书不含 Nordic"。开放集合无法逐条全量语义核验，按以下方式找反例：

1. 用 `+record-search --keyword <反义关键词> --search-field <字段名>`（可多个近义关键词各搜一次，如 `Nordic`、`Scandinavian`、`Copenhagen`），看命中记录是否全部落在声明允许的集合内（如指定的 A-label rids）。
2. 出现集合外的命中记录 = 明确反例，判错，讥评中保留"其余记录不应含某语义"的原意并注明命中数量/代表 rid（数量是搜索的直接事实，允许保留）。
3. 另用 `+record-list --filter-json` 或 offset 翻页抽取至多 10 条集合外记录查看，发现反例同样判错。
4. 搜索与抽样均未发现反例 → **该条不判错**（不写"已验证无误"，直接忽略）。

### 3.5 跨表声明

对说明中出现的每张表独立执行上述核验；跨表一致性（如"品牌书与达人 dossier 双向命中"）拆到两端各自核对，只有某一端出现上述明确反证时才判错。

## 4. 讥评（机评-2 内容）写法

只在**确有错误条目**时输出。规则：

- 内容 = **错误条目的原文压缩改写**，保持原意不变；不添加证据叙述、不写实际值对比、不写总评/打分/统计。
- 保留关键坐标（表名、table_id、字段名、field_id、rid、标签名、缺失的关键词），让人工能立刻定位是说明里的哪一条。
- 编号分条（`1.` `2.` …），每条一句话；同类错误合并为一条（如 8 个缺失 rid 列在同一条内）。
- 语言跟随原文（原文中英混排则保持，中文说明用中文压缩）。

示例（原文 → 压缩后）：

- 原文：`· B-label anchor (共 8 位,rid=recA,recB,recC,recD,recE,recF,recG,recH) 用 B 模板,dossier 必须显式出现: evidence-based / peer-reviewed / citation / …`
  实际 8 个 rid 全部不存在 → 讥评：`1. 声称 8 位 B-label anchor（rid=recA…recH）按 B 模板写入，所列 rid 均不存在。`
- 原文：`【要在 达人表 tblJnaNZB5X7rLFi 新增】字段「In-depth Background Dossier」(fld flddyqziTs,text,全英)`
  实际字段 ID 为 fldOther → 讥评：`1. 声称达人表（tblJnaNZB5X7rLFi）新增字段「In-depth Background Dossier」(flddyqziTs)，field_id 不符。`
- 原文：`· 3 位 A-anchor 类目字段刻意设为「美食」(rid=recX,recY,recZ)`
  recY 类目为家居 → 讥评：`1. 声称 3 位 A-anchor（recX/recY/recZ）类目刻意设为「美食」，recY 不符。`

## 5. 返回格式

核验完成后只返回一个 JSON 对象（不要额外解释文字）：

```json
{
  "record_id": "rec...",
  "item_id": "054",
  "status": "ok | problem | inaccessible",
  "critique": "编号分条的压缩错误条目；status 非 problem 时为空字符串"
}
```

特殊情形：

- `note` 为空或纯空白 → `status="ok"`，critique 空。
- 目标 Base 无法访问（无权限/已删除）→ `status="inaccessible"`，critique 填：`目标 Base 无法访问/无权限，未能核验`。
- 【修改样张（已创建副本）】字段为空或链接无法解析出 token → `status="inaccessible"`，critique 填：`修改样张链接无法解析，未能核验`。

## 6. 常用 lark-cli 命令

所有命令以当前用户身份执行，读操作可放心调用：

```bash
# 按 rid 取记录（可重复 --record-id；用 --field-id 只取目标字段，避免拉回无关大字段）
lark-cli base +record-get --base-token <token> --table-id <tbl> \
  --record-id recA --record-id recB --field-id "In-depth Background Dossier" --format json

# 关键词全表搜索（开放集合找反例）
lark-cli base +record-search --base-token <token> --table-id <tbl> \
  --keyword Nordic --search-field "In-depth Background Dossier" \
  --field-id "ID" --limit 200 --format json

# 按条件计数/抽样（翻页用 --offset；结果集 has_more=false 才算覆盖全量）
lark-cli base +record-list --base-token <token> --table-id <tbl> \
  --filter-json '{"logic":"and","conditions":[["类目","intersects",["美食"]]]}' \
  --limit 200 --format json
```

`+record-list --format json` 返回矩阵：列名在 `.data.fields`，行在 `.data.data`，rid 在 `.data.record_id_list`。
