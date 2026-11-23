---
name: human-allocation
description: |
  按「紧急度 × 截止日期」把一批任务的人力分配算出来：给定题量、人效、紧急度(P0/P1/P2)、
  发布/截止时间和空闲人力池，输出所需人数 n*、选中的人、每人题量、预估交付时刻、是否可行、
  以及不可行时的建议截止时间。适用于标注/评测/众包/工单等"一批题分给几个人做"的排班场景。
  纯确定性计算，无外部依赖（仅标准库）。触发词：人力分配、派单、排班、算需要几个人、
  分配标注员、紧急度排期、headcount、allocate people。NOT for 需要连飞书/数据库实时拉人力池
  （本 skill 只吃已备好的 roster 数据）、生成飞书卡片或 IM 推送、以及跑机器学习排班模型。
---

# human-allocation（紧急度 × 截止日期驱动的人力分配）

把「一批任务要交给几个人、每人分多少、能不能按时交」这件事变成一个确定性函数。
从飞书标注机器人的 `human_allocation` 生产模块提取核心算法，剥掉了飞书 SDK、LLM、
文件存储、卡片渲染，任何 agent 只要能凑出 `task` + `roster` 两个 dict 就能直接调用。

## 何时用

- 有 Q 道题（或 N 个工单），要按紧急度和截止时间决定投入几个人、怎么分。
- 想知道「按现在的人力，这个 deadline 扛不扛得住」，扛不住时想要一个能扛的建议截止。
- 需要一个**可解释**的分配结果（每人多少题、多少工时、谁是组长），而不是黑盒推荐。

不适用（本 skill 不做，交给宿主）：

- 实时从飞书/数据库拉人力池 → 宿主先查好，整理成 `roster` 再传进来。
- 把结果渲染成飞书卡片、发 IM、写存储/去重 → 宿主拿返回的 `plan` 自己渲染。
- 机器学习/图神经网络排班 → 本 skill 是确定性公式，不含模型。

## 快速上手

```python
from allocate import allocate

task = {
    "task_name": "Building 批量标注",   # 用于关键词推断领域（也可直接传 domain）
    "workload": 50,                     # 题量 Q
    "urgency": "P0",                    # P0/P1/P2，也认 "高"/"中"
    "posted_at": "2026-07-03 10:00",    # 发布时刻
    "expected_delivery": "2026-07-03 19:00",  # 希望交付；只给日期也行
}
roster = [
    {"name": "小王", "capabilities": ["Building"],
     "hourly_efficiency": {"Building": 3.7},  # 每领域 题/h
     "busy_hours": 0.0},                       # 已占用工时（跨任务并发保护用）
    # ... 更多人
]

res = allocate(task, roster)                    # 可选 cfg=..., domain_leads=...
plan = res["plan"]
print(plan["n_star"], plan["q_per_person"], plan["feasible"])
```

CLI 自检 / 当 demo 看：`python allocate.py`

## 输入契约

**task**（dict）：
| key | 含义 | 备注 |
|---|---|---|
| `workload` | 题量 Q | 数字或含数字的字符串 |
| `urgency` | 紧急度 | `P0`/`P1`/`P2`，或 `高`/`中`；识别不了当 P2 |
| `posted_at` | 发布时刻 | `YYYY-MM-DD HH:MM`；缺省用当前时间 |
| `expected_delivery` | 希望交付 | 带时间直用；只给日期则对齐 `posted_at` 的时刻 |
| `task_name`/`requester`/`task_link` | 领域推断素材 | 关键词命中 → 领域 |
| `domain` | 直接指定领域 | 给了就不做关键词推断 |

**roster**（list[dict]），每人：`name`（或 `person:{name,open_id}`）、`capabilities`（领域列表）、
`hourly_efficiency`（`{领域: 题/h}`）、`busy_hours`（已占用工时，默认 0）。

**cfg**（可选 dict，覆盖 `DEFAULT_CONFIG` 的部分键）、**domain_leads**（可选 `{领域: [组长名]}`）。

## 核心算法（一句话与公式）

> **n\* = max( ⌈W ÷ T⌉ , 每档最低人数 )**，紧急度越高，缓冲留得越多、越早预警超期风险。

- `W = Q ÷ v_top`（可选叠加质检工时），`T` = 工作日历感知的可用工时（跳周末/节假日、减午休）。
- `n*` 先算「够用即可」的 `⌈W/T⌉`，再兜底到 `min_people_p{0,1,2}`（默认都是 3）。
- 缓冲 `b`（P0=50%/P1=25%/P2=0%）**不再翻倍人数**，只反映在 `target = T×(1−b)` 上：
  `t_actual > target` 就把 `feasible` 标 False 做超期风险提示。
- 选人：占用少优先、同档人效降序；每领域至多一位组长占评测名额，多领域组长题量份额减半；
  尽量留 1 个新手名额。题量 `Σqᵢ = Q` 守恒，余数按份额降序发放。
- 池子全上也扛不住（`⌈W/T⌉ > 池`）→ `reason="hard_infeasible"`，并反算一个能扛的
  `recommended_deadline` 给需求方。

> ⚠️ 与仓库里 `人力分配逻辑.md` / README 写的 `n*=⌈W÷(T×(1−b))⌉` **不同**。本 skill 复刻的是
> **线上实际运行**的代码语义（`⌈W/T⌉` 兜底 min_people），文档是旧版公式，以代码为准。

## 输出契约

`allocate()` 返回 `{available, domain, top, candidates, plan}`；不可用时 `{available:False, reason, ...}`。
常见 `reason`：`empty_roster` / `no_capability_match`（有领域但没人会）。

`plan` 关键字段：`n_star`、`n_star_formula`（未兜底的数学值）、`q_per_person`、`feasible`、
`t_actual`（并行最慢人决定的真实交付耗时）、`t_avg`（整体粗估）、`eta_actual_at`、`target_hours`、
`recommended_deadline`、`remaining_domain_free`（本领域还能立刻接活的人数）、
`chosen`（每人 `name/hourly/assigned_q/assigned_hours/role/is_lead`）。

## 配置（cfg 可覆盖）

`buffer_p0/p1/p2`、`min_people_p0/p1/p2`、`work_hours`（默认 `10:00-12:00,13:00-19:00`）、
`holidays`、`default_hourly`(3.0)、`monthly_missing_hourly`(4.0)、`qc_speed_ratio`(1.5)、
`qc_included_in_time`(False)、`busy_threshold_hours`(8.0)。全部见 `allocate.py` 顶部 `DEFAULT_CONFIG`。

## 边界与已知简化（ponytail）

- 领域关键词表内置了原项目的 10 个领域（Building/Table/Dashboard/...）。换业务领域时改
  `_DOMAIN_KEYWORDS`，或直接在 `task["domain"]` 里指定，绕过推断。
- `deadline_for_hours` 最多向后推 60 个工作日；工作量大到这之外，`recommended_deadline` 返回 None。
- 只做**单任务**分配。多任务竞争同一人力池时，宿主按优先级 `P = w_u·U + w_d·D` 排序后逐个调用，
  并把已派出的人的 `busy_hours` 累加回 roster（本 skill 靠 `busy_hours ≥ 阈值` 做跨任务并发保护）。

## 自检

```bash
python allocate.py
```

10 个内存断言：工作日历（含跨周末/节假日）、领域推断、紧急度归一与缓冲档位、复刻设计文档示例、
无匹配领域、硬不可行 + 建议截止、多领域组长题量减半、题量守恒。不联网、无副作用。
