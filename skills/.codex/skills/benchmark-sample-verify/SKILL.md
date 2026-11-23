---
name: benchmark-sample-verify
description: 以主控飞书多维表格每行的【指令+样张设计思路+考察点】为真值，核对【考察数据表的副本】里多个 Base 副本是否真的实现了设计意图（表/字段/行数/正负样本/Gold行/多模态附件内容），把错误条目压缩写回【机评-2】并在【检查结果-2】标有问题，全吻合则写无问题、机评留空。适用于样张设计核验、副本质检、benchmark 样张验收、机评回填等场景。不用于样张修复或改数据。
author: benchmark-sample-verify
---

# Benchmark 样张设计意图核验

以主控表每行的真值三件套核对副本 Base 是否按设计做出来了。**一行一题、无状态**，每题独立判定，只读副本、只回填主控表两个字段。核验的本质是回答一句话：**副本里有没有按设计思路把 表/字段/行数/正负样本/Gold 行/附件内容 真的做出来。**

## 核心口径（与用户约定，不要偏离）

1. **真值来源**：每行的【指令】+【样张设计思路】+【考察点】三者合起来是真值。设计思路描述"应该做成什么样"，指令是给 Agent 的任务，考察点是要考的能力。
2. **只核不改**：对副本 Base 一律只读，绝不修改副本数据。只回写主控表【机评-2】和【检查结果-2】两个字段，其它列（含【修改人】【备注】【参考答案】等）一律不碰。
3. **判定与回填**：
   - 有问题 → 【检查结果-2】写 `有问题`，【机评-2】写**压缩的错误原文/定位**（编号分条，只留关键结论，不写过程）。
   - 全吻合 → 【检查结果-2】写 `无问题`，【机评-2】**留空**。
   - 目标副本无法访问 → 【机评-2】注明"未能核验"及原因，【检查结果-2】不臆断。
4. **声称 ≠ 事实**：设计思路里的任何声称（"纯图 PDF""OCR 有错字""副本01 是某库"）都必须用工具实测验证，**不能照单全信**。实测与声称冲突时，以实测为准。
5. **口径分歧交用户**：遇到"做对了但放错位置""考点强度低于声称"这类非黑白问题，先给出事实，再请用户定调（有问题 / 无问题），不自行拍板。

## 背景知识：这批题的结构与已知坑

副本复制后 table_id/record_id 全部重生成、field_id 通常保留。核验前先解析真值与副本，再逐项实测。三个已被实战验证的坑和完整判据见 [verify-rules.md](references/verify-rules.md)，**每次核验前必读**。一句话预警：

- **坑1 副本编号 ≠ 库语义顺序**：别信"副本01=设计思路里的第一个库"。必须逐个 `table-list` 打开副本看真实表名，找出真考察库（常在副本08/18/19，01/02 多为陪跑库）。
- **坑2 读字段会漏判**：凡"从 PDF/图片读内容判断"的题，判据常藏在附件像素里（表里没这列），**必须下载附件亲眼看**。
- **坑3 实测优先**：判断"是否纯图 PDF"以 `extract_text()` 返回为准，不靠字节特征猜；"OCR 是否设陷阱"要抽图核对，不信声称。

## 工作流程

### 1. 解析主控表与真值

```bash
lark-cli base +url-resolve --url "<主控Base链接>" --as user --format json
```

取 `base_token`、`table_id`、`view_id`。再拉取待核验行（含指令/设计思路/考察点/副本链接/现有检查结果）：

```bash
python scripts/fetch_rows.py --base-token <主控base_token> --table-id <tbl> --mode empty
```

`--mode empty` 只取【检查结果-2】为空的行（断点续跑，默认口径）；`--mode all` 全量重核；`--rows Q113,Q71` 指定题号。输出 `temp_data/rows.jsonl`，每行含 record_id / 题号 / instruction / design / focus / copy_links（解析出的 base_token 列表）/ 现有检查结果与机评。

### 2. 定位真考察库（坑1）

对该行每个副本 base_token 逐个列表，看真实表名、行数、rev：

```bash
python scripts/probe_copies.py --tokens <token1> <token2> <token3>
```

把真实表名与设计思路要考的库名对齐，确定哪个副本是**真考察库**。编号错位本身可能就是一个"有问题"（由用户口径决定）。

### 3. 结构核验（表/字段/行数/正负样本）

对真考察库取字段 schema 和记录，按设计思路核对：

```bash
lark-cli base +field-list --base-token <考察库token> --table-id <tbl> --as user --format json
```

- 字段：设计思路点名的新增字段（如 receipt_img / scan_pdf / 记账主体）是否存在、类型对不对。
- 行数：是否匹配设计思路的规模档（100 行档 / 1000 行档）。
- 正负样本：按设计思路的分类字段统计分布（如 文档类型/物料类型/单据类型），数出正样本数、硬负样本数，和设计思路声称的"正N+硬负M"对齐。
- Gold 行：用 `--filter-json`（经 `@file` 传入，见坑4）筛出带关键附件/关键属性的候选行，核对数量与编号规律。

### 4. 多模态附件核验（坑2，用户要求抽样时必做）

凡考点是"从图片/PDF 读内容判断"，下载代表性附件亲眼核对：正样本、各类硬负样本各抽 1-2 个。

```bash
python scripts/download_samples.py --base-token <考察库token> --table-id <tbl> \
  --record-id <rec1> --field-id <附件field_id> --out-dir temp_data/att
```

下载后用 Read 工具直接看图/PDF，确认设计意图（如"实拍 vs 设计稿""抬头开错 vs 分公司""纯图扫描件""模糊脏数据"）是否真实做出来。PDF 是否"纯图无文字层"用 `python scripts/pdf_textcheck.py <pdf>` 实测（坑3）。

### 5. 判定并回填

汇总每题判定为 `有问题 / 无问题 / 未能核验`，机评-2 文案压缩分条。写文件后回填：

```bash
python scripts/write_back.py --base-token <主控base_token> --table-id <tbl>
```

回填只写【机评-2】【检查结果-2】，串行分批，遇 `1254291` 写冲突自动重试。完成后 `+record-get` 抽查 2-3 行读回确认。

### 6. 对话汇报

不生成飞书文档。报告：核了哪几题、各题判定与依据、发现的坑、回填了哪些行，附主控 Base 链接。核验过程中把观察、判断依据、发现的坑讲出来，不只给结论。

## 环境坑（Windows / PowerShell，必看）

- **JSON 参数别内联**：PowerShell 会吞掉单引号 JSON 的引号。`--filter-json` / `--json` 一律写进文件用 `@./相对路径.json` 传。
- **路径要相对且在 cwd 内**：lark-cli 的 `--output` / `@file` 只接受当前目录内的相对路径（如 `./temp_data/x.json`），绝对路径会被拒。
- **别用标准库同名脚本名**：工作目录放 `inspect.py` / `json.py` 等会遮蔽 Python 标准库导致诡异报错。脚本放 `scripts/` 子目录。
- **禁写 pycache**：跑 Python 前设 `PYTHONDONTWRITEBYTECODE=1`，否则沙箱可能拦截 `__pycache__` 写入。
- **lark-cli 读取用 `--as user`**；JSON 文件可能带 UTF-8 BOM，读取用 `encoding='utf-8-sig'`。
- `+record-list` 返回体是 `data.data`（二维数组，按 `data.field_id_list` 顺序）+ `data.record_id_list`，不是对象数组；解析见脚本。

## 资源说明

- [scripts/fetch_rows.py](scripts/fetch_rows.py)：拉取主控表待核验行并解析副本链接为 base_token 列表
- [scripts/probe_copies.py](scripts/probe_copies.py)：逐个副本列表真实表名/行数/rev，定位真考察库
- [scripts/download_samples.py](scripts/download_samples.py)：批量下载指定记录的附件到本地供 Read 看图
- [scripts/pdf_textcheck.py](scripts/pdf_textcheck.py)：实测 PDF 是否纯图无文字层（extract_text 为准）
- [scripts/write_back.py](scripts/write_back.py)：判定结果串行分批回写（仅【机评-2】【检查结果-2】）
- [references/verify-rules.md](references/verify-rules.md)：三大坑的完整判据与逐项核验清单，每次核验前必读
- `temp_data/`：rows.jsonl、附件、filter JSON 等中间产物
