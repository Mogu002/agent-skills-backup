---
name: ba-question-generator
description: BA评测出题专家。按L1/L2/L3分层框架，基于指定剧本数据为网约车业务分析场景生成评测题目，输出包含instruction和rubrics的Excel文件。触发场景：用户说"出题"、"生成评测题"、"BA评测"、"出L1/L2/L3题"、"生成题目"、"出几道题"，或希望为某个剧本/数据集生成评测题时使用。
---

# BA 评测出题专家 — 操作指南

为指定剧本数据生成 L1/L2/L3 分层评测题，输出 Excel 文件，每行一条 rubric，方便后续改造为 instruction + rubrics 的种子数据格式。

---

## 第一步：理解分层框架

在出题前，必须先明确三层框架的边界：

| 层级 | 任务类型 | 核心考察点 | 答案形态 | 评分方式 | 典型技能标签 |
|------|---------|-----------|---------|---------|------------|
| L1 | 精确计算 | 数据操作准确性 | 唯一数值或枚举 | 机器自动评分 | 指标查询、异动识别、精确计算、基期对比计算、LTV/CAC计算、ROI计算 |
| L2 | 结构化分析 | 分析框架的正确应用 | 有限开放，维度可穷举 | 人工评分，标准清晰 | 漏斗拆解、维度拆解、贡献度计算、AARRR、COHORT、RFM、VNOS、相关性分析、回归分析、AB实验结果分析 |
| L3 | 综合判断 | 业务洞察与决策质量 | 过程开放+结果唯一 / 过程有限开放+结果开放 | 人工评分，需业务经验 | 经营解读、策略建议、对标分析、A面B面、三高三低、STP定位、PSM+DID结论解读、AB实验设计 |

**出题原则**：
- L1 题必须有唯一正确答案，可从数据直接计算得出
- L2 题答案维度有限可穷举，考察框架应用是否完整
- L3 题考察综合判断，rubric 聚焦"必须提及的关键洞察"，而非唯一答案

---

## 第二步：了解 Rubric 格式规范

每条 rubric 的 `content` 字段是**评分说明**，不是答案本身，有四种固定写法：

| 写法 | 适用场景 | 示例 |
|------|---------|------|
| `唯一答案：<值>` | L1 精确计算，只有一个正确答案 | `唯一答案：71%` |
| `答案：<值或范围>` | L1/L2 有标准答案但允许小误差 | `答案：活跃司机数下降约71%（允许±3%误差）` |
| `答案需提及：<要点>` | L2/L3 需要覆盖某个分析维度 | `答案需提及：从供给侧和需求侧两个维度分别分析` |
| `答案需明确指出：<结论>` | L3 需要得出某个明确判断或结论 | `答案需明确指出：本次异动主要矛盾在供给侧` |

**禁止写法**：
- ❌ 不能写成"识别出XX"、"能够分析XX"（这是元描述，不是评分说明）
- ❌ 不能直接把期望答案本身当 content（content 是评分说明，要说明"答案应该是什么"）

---

## 第三步：出题流程

### 3.1 收集剧本信息

在出题前，先确认以下信息：
- 剧本名称和数据文件路径
- 剧本事件描述（什么时间段发生了什么）
- 可用的数据表和关键字段

### 3.2 按层级出题

**L1 出题要点**：
- 每道题对应一个可精确计算的指标
- 先自己计算出正确答案，再写 rubric
- instruction 要明确指定计算口径（如"第11-20天 vs 第1-10天"）
- 每道 L1 题通常只有 1-2 条 rubric

**L2 出题要点**：
- 考察框架应用：漏斗拆解、维度拆解、AARRR、COHORT 等
- instruction 要给出明确的分析框架要求
- rubric 覆盖框架的每个必要维度
- 每道 L2 题通常有 3-5 条 rubric

**L3 出题要点**：
- 考察综合判断：经营解读、策略建议、对标分析、AB实验设计等
- instruction 要给出具体的业务场景和决策背景
- rubric 聚焦"必须得出的关键结论"，允许答案路径多样
- 每道 L3 题通常有 4-7 条 rubric

### 3.3 题目数量建议

| 层级 | 建议题数 | 说明 |
|------|---------|------|
| L1 | 3-5 道 | 覆盖核心指标的精确计算 |
| L2 | 2-4 道 | 覆盖主要分析框架 |
| L3 | 2-4 道 | 覆盖经营解读、策略建议等综合判断 |

---

## 第四步：输出 Excel 文件

### 4.1 Excel 结构

输出文件包含**两个 Sheet**：

**Sheet 1：题目总览（overview）**

| 列名 | 说明 |
|------|------|
| 题号 | 格式：`ba-L1-01`、`ba-L2-01`、`ba-L3-01` |
| 层级 | L1 / L2 / L3 |
| 技能标签 | 如：指标查询、漏斗拆解、经营解读 |
| 剧本 | 剧本名称，如：case4_春节司机荒 |
| instruction | 完整的题目描述（含数据路径、任务要求） |
| rubric数量 | 该题的 rubric 条数（Excel 公式自动计算） |

**Sheet 2：Rubric 明细（rubrics）**

| 列名 | 说明 |
|------|------|
| 题号 | 与 Sheet1 对应 |
| 层级 | L1 / L2 / L3 |
| 技能标签 | 与 Sheet1 对应 |
| rubric_id | 格式：`01`、`02`、`03`（两位数字） |
| rubric_content | 评分说明，按四种写法规范填写 |
| weight | 权重，默认为 1 |

### 4.2 生成代码模板

使用 openpyxl 生成 Excel，参考以下模板：

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()

# Sheet 1: 题目总览
ws1 = wb.active
ws1.title = "题目总览"

headers1 = ["题号", "层级", "技能标签", "剧本", "instruction", "rubric数量"]
ws1.append(headers1)

# 设置表头样式
header_fill = PatternFill("solid", start_color="366092", end_color="366092")
header_font = Font(bold=True, color="FFFFFF", name="Arial")
for col in range(1, len(headers1) + 1):
    cell = ws1.cell(row=1, column=col)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# 设置列宽
col_widths1 = [12, 8, 16, 20, 80, 12]
for i, width in enumerate(col_widths1, 1):
    ws1.column_dimensions[get_column_letter(i)].width = width

# Sheet 2: Rubric 明细
ws2 = wb.create_sheet("Rubric明细")

headers2 = ["题号", "层级", "技能标签", "rubric_id", "rubric_content", "weight"]
ws2.append(headers2)

# 设置表头样式（同上）
for col in range(1, len(headers2) + 1):
    cell = ws2.cell(row=1, column=col)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# 设置列宽
col_widths2 = [12, 8, 16, 10, 80, 8]
for i, width in enumerate(col_widths2, 1):
    ws2.column_dimensions[get_column_letter(i)].width = width

# 填入数据后保存
wb.save("output.xlsx")
```

### 4.3 格式要求

- 表头：深蓝底色（#366092）+ 白色加粗字体
- 数据行：交替浅灰（#F2F2F2）和白色背景
- instruction 和 rubric_content 列：开启自动换行
- 所有单元格：垂直居中对齐
- 字体：Arial，正文 10pt
- 文件保存路径：`eva/` 目录下，文件名格式 `ba_questions_<剧本名>_<日期>.xlsx`

---

## 第五步：验证与交付

生成 Excel 后，执行以下检查：

```
- [ ] Sheet1 和 Sheet2 的题号完全对应，无遗漏
- [ ] 每道 L1 题的 rubric_content 使用"唯一答案："或"答案："写法
- [ ] 每道 L3 题的 rubric_content 使用"答案需提及："或"答案需明确指出："写法
- [ ] instruction 中的数据路径格式正确（如 /meituan/ba-L1-01/input/）
- [ ] weight 字段全部为数字 1（除非有特殊说明）
- [ ] Excel 文件可正常打开，无格式错误
```

完成后，告知用户文件路径，并简要说明各层级的出题思路。

---

## 快速参考：instruction 模板

### L1 instruction 模板
```
你是一名专业商分分析师。请仅基于给定输入数据完成计算，不使用任何外部信息。

输入数据所在地址：
/meituan/<题号>/input/

任务要求：
基于数据，计算<具体指标>。请给出精确数值，保留两位小数（如为百分比则保留一位小数）。

注意，请直接回复答案，不要问我任何问题。
```

### L2 instruction 模板
```
你是一名专业商分分析师。请仅基于给定输入数据和业务知识完成分析，不使用任何外部信息，也不要追问补充背景。

输入数据和业务知识所在地址：
/meituan/<题号>/input/

任务要求：
<具体分析框架要求，明确说明需要覆盖哪些维度>

注意，请直接回复答案，不要问我任何问题，也不要让我做出进一步决策。如果遇到任何问题和决策点，请你自行解决。
```

### L3 instruction 模板
```
你是一名专业商分分析师。请仅基于给定输入数据和业务知识完成网约车业务分析，不使用任何外部信息，也不要追问补充背景。

输入数据和业务知识所在地址：
/meituan/<题号>/input/

任务要求：
<具体业务场景描述 + 多点任务要求，每点用"第一/第二/第三"标注>

注意，请直接回复答案，不要问我任何问题，也不要让我做出进一步决策。如果遇到任何问题和决策点，请你自行解决。
```
