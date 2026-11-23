"""紧急度 × 截止日期驱动的人力分配核心（确定性、纯标准库）。

从飞书标注机器人的 human_allocation 模块提取的可复用核心：只保留确定性算法，
剥离了飞书 SDK、LLM、文件存储、卡片渲染和图引擎等宿主耦合。

对外三个入口：
  available_hours(start, end, cfg)      -> 工作日历感知的可用工时 T
  deadline_for_hours(start, hours, cfg) -> 从 start 起累加 hours 工时后的时刻
  allocate(task, roster, cfg=None, ...) -> {available, domain, candidates, plan}

数据进、数据出，无任何副作用。config 是普通 dict，缺项走 DEFAULT_CONFIG。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, time, timedelta
from typing import Any

# ── 默认配置 ──────────────────────────────────────────────────────────────
# 紧急度越高，缓冲留得越多；min_people 是每档最低产出人数保障。
DEFAULT_CONFIG: dict[str, Any] = {
    "buffer_p0": 0.50, "buffer_p1": 0.25, "buffer_p2": 0.0,
    "work_hours": "10:00-12:00,13:00-19:00",   # 每日工时段，逗号分隔，减午休
    "holidays": [],                            # ["2026-10-01", ...] 跳过的非工作日
    "default_hourly": 3.0,                     # 领域未识别时的兜底人效（题/h）
    "monthly_missing_hourly": 4.0,             # 命中领域但缺人效数据时的兜底
    "min_people_p0": 3, "min_people_p1": 3, "min_people_p2": 3,
    "qc_speed_ratio": 1.5,                     # 质检人效 = 评测人效 × 此值
    "qc_included_in_time": False,              # 是否把质检工时计入 n*/feasible 判定
    "busy_threshold_hours": 8.0,               # 已占用工时 ≥ 此值视为"任务中"
}

# 关键词 → 能力领域（小写匹配）。task_name 里命中即推断领域。
_DOMAIN_KEYWORDS: dict[str, str] = {
    "building": "Building",
    "table": "Table", "多维表格": "Table", "bitable": "Table",
    "dashboard": "Dashboard", "仪表盘": "Dashboard",
    "permission": "Permission", "权限": "Permission",
    "workflow": "Workflow", "工作流": "Workflow",
    "analysis": "Analysis", "分析": "Analysis",
    "ai view": "AI View", "aiview": "AI View", "ai 视图": "AI View",
    "侧边栏": "侧边栏", "sidebar": "侧边栏",
    "decision": "Decision", "决策": "Decision",
    "form": "Form", "表单": "Form",
}


def _cfg(cfg: dict | None) -> dict:
    """浅合并到默认配置，缺项走默认值。"""
    merged = dict(DEFAULT_CONFIG)
    if cfg:
        merged.update({k: v for k, v in cfg.items() if v is not None})
    return merged


# ── 工作日历：可用工时 T ────────────────────────────────────────────────────
def _t(s: str) -> time:
    h, m = s.split(":", 1)
    return time(int(h), int(m))


def _parse_slots(spec: str) -> list[tuple[time, time]]:
    """解析 "10:00-12:00,13:00-19:00" → [(time,time),...]。"""
    slots: list[tuple[time, time]] = []
    for part in (spec or "").split(","):
        part = part.strip()
        if not part or "-" not in part:
            continue
        a, b = part.split("-", 1)
        try:
            t1, t2 = _t(a.strip()), _t(b.strip())
        except ValueError:
            continue
        if t1 < t2:
            slots.append((t1, t2))
    return slots


def _is_working_day(d: date, holidays: set[str]) -> bool:
    return d.weekday() < 5 and d.strftime("%Y-%m-%d") not in holidays


def _overlap_hours(wa: datetime, wb: datetime, sa: datetime, sb: datetime) -> float:
    lo, hi = max(wa, sa), min(wb, sb)
    return (hi - lo).total_seconds() / 3600.0 if hi > lo else 0.0


def available_hours(start_dt: datetime, end_dt: datetime, cfg: dict | None = None) -> float:
    """[start_dt, end_dt) 内的可用工时（h），跳过周末 + 节假日，减午休。end<=start → 0。"""
    if end_dt <= start_dt:
        return 0.0
    c = _cfg(cfg)
    slots = _parse_slots(c["work_hours"])
    if not slots:
        return 0.0
    hol = set(c["holidays"])
    total = 0.0
    cur, end_date = start_dt.date(), end_dt.date()
    while cur <= end_date:
        if _is_working_day(cur, hol):
            for t1, t2 in slots:
                total += _overlap_hours(start_dt, end_dt,
                                        datetime.combine(cur, t1), datetime.combine(cur, t2))
        cur += timedelta(days=1)
    return round(total, 4)


def deadline_for_hours(start_dt: datetime, hours_needed: float,
                       cfg: dict | None = None, max_days: int = 60) -> datetime | None:
    """从 start_dt 沿工作时段累加 hours_needed 后到达的时刻；累加不完（太大）→ None。"""
    if hours_needed <= 0:
        return start_dt
    c = _cfg(cfg)
    slots = _parse_slots(c["work_hours"])
    if not slots:
        return None
    hol = set(c["holidays"])
    remaining = float(hours_needed)
    cur = start_dt.date()
    for _ in range(max_days):
        if _is_working_day(cur, hol):
            for t1, t2 in slots:
                s = datetime.combine(cur, t1)
                e = datetime.combine(cur, t2)
                if cur == start_dt.date():
                    s = max(s, start_dt)
                if e <= s:
                    continue
                slot_h = (e - s).total_seconds() / 3600.0
                if slot_h >= remaining:
                    return s + timedelta(hours=remaining)
                remaining -= slot_h
        cur += timedelta(days=1)
    return None


# ── 输入解析 ────────────────────────────────────────────────────────────────
def infer_domain(task: dict) -> str | None:
    """从 task_name / requester 等字符串字段按关键词推断能力领域，命中即返回。"""
    parts = [str(task.get(k)) for k in ("task_name", "requester", "task_link")
             if isinstance(task.get(k), str)]
    hay = " ".join(parts).lower()
    if not hay:
        return None
    for kw, domain in _DOMAIN_KEYWORDS.items():
        if kw in hay:
            return domain
    return None


def _parse_workload(v: Any) -> float:
    """题量 Q：数字直取；字符串抽数字；失败 → 1.0（避免除零）。"""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        digits = "".join(ch for ch in v if ch.isdigit() or ch == ".")
        try:
            return float(digits) if digits else 1.0
        except ValueError:
            return 1.0
    return 1.0


def _urgency_key(u: Any) -> str:
    """归一到 P0/P1/P2。P0/P1/P2 直读；"紧急"/"高"→P0；"中"→P1；其它→P2。"""
    if not isinstance(u, str):
        return "P2"
    u = u.strip().upper()
    if u in ("P0", "P1", "P2"):
        return u
    if "紧急" in u or u == "高":
        return "P0"
    if u == "中":
        return "P1"
    return "P2"


def _urgency_bonus(u_key: str) -> float:
    return {"P0": 10.0, "P1": 5.0}.get(u_key, 0.0)


def _buffer_for(u_key: str, c: dict) -> float:
    v = {"P0": c["buffer_p0"], "P1": c["buffer_p1"]}.get(u_key, c["buffer_p2"])
    return max(0.0, min(0.99, v))


def _min_people_for(u_key: str, c: dict) -> int:
    v = {"P0": c["min_people_p0"], "P1": c["min_people_p1"]}.get(u_key, c["min_people_p2"])
    return max(1, v)


def _qc_coverage(u_key: str, Q: float) -> float:
    """质检覆盖率：P0 全检；否则按题量分段（<100 全检 / ≤500 六成 / 更多四成）。"""
    if u_key == "P0":
        return 1.0
    if Q < 100:
        return 1.0
    return 0.60 if Q <= 500 else 0.40


def _match_caps(caps: list[str] | None, domain: str | None) -> list[str]:
    """忽略大小写/空白比对能力领域，防手写差异误判。"""
    if not domain or not caps:
        return []
    key = domain.strip().casefold()
    return [d for d in caps if isinstance(d, str) and d.strip().casefold() == key]


def _extract_hourly(hourly: dict, domain: str | None) -> float:
    """取候选人在指定领域的小时人效；缺失/非法 → 0。大小写不敏感。"""
    if not domain or not isinstance(hourly, dict):
        return 0.0
    v = hourly.get(domain)
    if v is None:
        for k, val in hourly.items():
            if isinstance(k, str) and k.lower() == domain.lower():
                v = val
                break
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _hourly_with_fallback(cand: "Candidate", domain: str | None, c: dict) -> float:
    """领域未识别→default_hourly；命中但缺月度数据→monthly_missing_hourly。"""
    if not domain:
        return c["default_hourly"]
    hv = _extract_hourly(cand.hourly_efficiency, domain)
    return hv if hv > 0 else c["monthly_missing_hourly"]


def _parse_dt(v: Any, fallback: datetime | None = None) -> datetime | None:
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(v, fmt)
            except ValueError:
                continue
    return fallback


def _deadline_dt(task: dict, posted: datetime) -> datetime | None:
    """expected_delivery：带时间直用；仅日期时对齐 posted 的时刻（相对语义）。"""
    v = task.get("expected_delivery")
    if not isinstance(v, str):
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    try:
        d = datetime.strptime(v, "%Y-%m-%d").date()
    except ValueError:
        return None
    return datetime.combine(d, posted.time())


# ── 候选人 ──────────────────────────────────────────────────────────────────
@dataclass
class Candidate:
    open_id: str | None
    name: str
    capabilities: list[str]
    load_status: str            # "空闲" / "任务中"（busy_hours 派生）
    busy_hours: float
    hourly_efficiency: dict[str, Any]
    fit_score: float
    breakdown: dict[str, float]
    matched_capabilities: list[str]
    notes: list[str] = field(default_factory=list)


def _lead_domain_counts(domain_leads: dict[str, list[str]] | None) -> dict[str, int]:
    """每位组长负责几个领域（同名跨领域出现次数）。多领域组长派工份额减半。"""
    counts: dict[str, int] = {}
    for names in (domain_leads or {}).values():
        for n in names or []:
            if isinstance(n, str) and n:
                counts[n] = counts.get(n, 0) + 1
    return counts


def _build_candidates(roster: list[dict], domain: str | None, u_key: str,
                      Q: float, delivery_days: float | None, c: dict) -> list[Candidate]:
    """给每位候选人打分：能力 40 / 负载 25|5 / 人效 0-20 / 紧急度 / 交付风险（负）。"""
    urgency_bonus = _urgency_bonus(u_key)
    max_hourly = 0.0
    prepped: list[dict] = []
    for rec in roster or []:
        person = rec.get("person") or {}
        name = (person.get("name") if isinstance(person, dict) else None) \
            or rec.get("name") or str(person) or "-"
        open_id = person.get("open_id") if isinstance(person, dict) else rec.get("open_id")
        caps = rec.get("capabilities") or []
        if isinstance(caps, str):
            caps = [caps]
        busy_h = float(rec.get("busy_hours") or 0.0)
        hourly = rec.get("hourly_efficiency") or {}
        hv = _extract_hourly(hourly, domain)
        max_hourly = max(max_hourly, hv)
        prepped.append({
            "name": name, "open_id": open_id, "caps": list(caps),
            "busy": busy_h, "hourly": hourly, "hv": hv,
            "matched": _match_caps(caps, domain),
            "load": "任务中" if busy_h >= c["busy_threshold_hours"] else "空闲",
        })

    out: list[Candidate] = []
    for p in prepped:
        bd: dict[str, float] = {}
        notes: list[str] = []
        bd["capability"] = 40.0 if p["matched"] else 0.0
        bd["load"] = 25.0 if p["load"] == "空闲" else 5.0
        bd["hourly_efficiency"] = (p["hv"] / max_hourly * 20.0) if (max_hourly > 0 and p["matched"]) else 0.0
        bd["urgency"] = urgency_bonus if p["matched"] else 0.0
        risk = 0.0
        if delivery_days is not None and p["hv"] > 0 and p["matched"]:
            required = Q / p["hv"]
            window = delivery_days * 8.0
            if window > 0 and required > window:
                risk = -min(20.0, (required - window) / window * 15.0)
                notes.append(f"交付紧张：预估需 {required:.1f}h，窗口 {window:.1f}h")
        bd["delivery_risk"] = risk
        out.append(Candidate(
            open_id=p["open_id"], name=p["name"], capabilities=p["caps"],
            load_status=p["load"], busy_hours=p["busy"], hourly_efficiency=p["hourly"],
            fit_score=round(sum(bd.values()), 2),
            breakdown={k: round(v, 2) for k, v in bd.items()},
            matched_capabilities=p["matched"], notes=notes,
        ))
    return out


# ── 生产计划 ────────────────────────────────────────────────────────────────
def _build_plan(task: dict, matched: list[Candidate], all_cands: list[Candidate],
                domain: str | None, domain_leads: dict[str, list[str]] | None, c: dict) -> dict:
    u_key = _urgency_key(task.get("urgency"))
    b = _buffer_for(u_key, c)
    Q = _parse_workload(task.get("workload"))
    min_people = _min_people_for(u_key, c)
    qc_cov = _qc_coverage(u_key, Q)

    posted = _parse_dt(task.get("posted_at"), datetime.now())
    deadline = _deadline_dt(task, posted)
    T = available_hours(posted, deadline, c) if deadline else None

    # 领域最快人效 v_top（都没数据则兜底）
    v_top = 0.0
    for cand in matched:
        v_top = max(v_top, _hourly_with_fallback(cand, domain, c))
    v_top = v_top or c["default_hourly"]

    W_eval = Q / v_top
    v_qc = v_top * c["qc_speed_ratio"]
    W_qc = (Q * qc_cov) / v_qc if v_qc > 0 else 0.0
    W = W_eval + (W_qc if c["qc_included_in_time"] else 0.0)

    plan: dict = {
        "urgency": u_key, "buffer": b, "min_people": min_people, "qc_coverage": qc_cov,
        "Q": Q, "v_top": round(v_top, 3), "W": round(W, 3),
        "T": round(T, 3) if T is not None else None,
        "posted_at": posted.strftime("%Y-%m-%d %H:%M"),
        "deadline": deadline.strftime("%Y-%m-%d %H:%M") if deadline else None,
    }
    if T is None:
        plan.update({"n_star": None, "feasible": None, "reason": "no_expected_delivery"})
        return plan
    if T <= 0:
        plan.update({"n_star": None, "feasible": False, "reason": "no_available_hours (T<=0)"})
        return plan

    # 核心公式：n* = ⌈W / T⌉，再兜底到 min_people。"够用即可"，不为 buffer 翻倍人数；
    # buffer 只反映在 target = T·(1-b) 上，用于超期风险提示。
    n_star_formula = max(1, math.ceil(W / T))
    n_star = max(n_star_formula, min_people)

    # 跨任务并发保护：占用 ≥ 阈值的普通人硬排除（组长豁免，可并行）
    lead_counts = _lead_domain_counts(domain_leads)
    lead_names = set(lead_counts.keys())
    busy_thr = c["busy_threshold_hours"]

    def _bumped(cand: Candidate) -> bool:
        return cand.busy_hours >= busy_thr and cand.name not in lead_names

    matched = [cand for cand in matched if not _bumped(cand)]
    novice_pool = [cand for cand in all_cands if not cand.matched_capabilities and not _bumped(cand)]
    novice_pool.sort(key=lambda x: x.busy_hours)

    hard_ceiling = len(matched) + len(novice_pool)
    if n_star > hard_ceiling:
        t_full = W / hard_ceiling if hard_ceiling > 0 else float("inf")
        rec = deadline_for_hours(posted, t_full, c) if hard_ceiling > 0 else None
        plan.update({
            "n_star": hard_ceiling, "feasible": False,
            "reason": "hard_infeasible: 池内所有人加起来也无法在 T 内完成",
            "t_full": round(t_full, 3) if t_full != float("inf") else None,
            "recommended_deadline": rec.strftime("%Y-%m-%d %H:%M") if rec else None,
        })
        return plan

    # 至少留 1 个新手名额（有新手池且 n*≥2 时）
    novice_slots = 1 if novice_pool and n_star >= 2 else 0
    eval_from_matched = max(0, n_star - novice_slots)
    if eval_from_matched > len(matched):
        novice_slots = n_star - len(matched)
        eval_from_matched = len(matched)

    # 占用少优先，同档人效降序
    matched.sort(key=lambda x: (x.busy_hours, -_extract_hourly(x.hourly_efficiency, domain)))

    # 领域组长：只让其中一位占评测名额（占用少、负责领域少优先）
    leads_in = sorted([cand for cand in matched if cand.name in lead_names],
                      key=lambda x: (x.busy_hours, lead_counts.get(x.name, 1)))
    others = [cand for cand in matched if cand.name not in lead_names]
    picked_lead = leads_in[0] if leads_in and eval_from_matched > 0 else None
    lead_set = {picked_lead.name} if picked_lead else set()
    chosen_eval = ([picked_lead] if picked_lead else []) + others[:eval_from_matched - (1 if picked_lead else 0)]
    chosen_novice = novice_pool[:novice_slots]
    chosen = chosen_eval + chosen_novice

    # 题量切分：普通人份额 1.0；多领域组长（≥2 领域）0.5；保证 sum(q_i)==Q，余数按份额降序
    shares = [0.5 if (cand.name in lead_set and lead_counts.get(cand.name, 1) >= 2) else 1.0
              for cand in chosen]
    total_share = sum(shares) or 1.0
    raw = [int(Q) * s / total_share for s in shares]
    base = [int(x) for x in raw]
    remaining = int(Q) - sum(base)
    order = sorted(range(len(chosen)), key=lambda i: (raw[i] - base[i], shares[i]), reverse=True)
    q_split = base[:]
    for i in order[:remaining]:
        q_split[i] += 1
    q_per_person = max(q_split) if q_split else 0

    # 每人真实耗时 → t_actual 取并行 max（最慢那位决定交付时刻）
    per_person_hours: list[float] = []
    for i, cand in enumerate(chosen):
        v_i = _hourly_with_fallback(cand, domain, c)
        q_i = q_split[i] if i < len(q_split) else 0
        if v_i <= 0 or q_i <= 0:
            per_person_hours.append(0.0)
            continue
        t_eval = q_i / v_i
        t_qc = (q_i * qc_cov) / (v_i * c["qc_speed_ratio"]) if c["qc_speed_ratio"] > 0 else 0.0
        per_person_hours.append(t_eval + (t_qc if c["qc_included_in_time"] else 0.0))
    t_actual = max(per_person_hours) if per_person_hours else 0.0

    # 整体粗估 t_avg（按平均人效）
    chosen_v = [_hourly_with_fallback(cand, domain, c) for cand in chosen]
    v_avg = sum(chosen_v) / len(chosen_v) if chosen_v else c["default_hourly"]
    t_avg_eval = Q / (v_avg * n_star) if v_avg > 0 else 0.0
    t_avg_qc = (Q * qc_cov) / (v_avg * n_star * c["qc_speed_ratio"]) if c["qc_speed_ratio"] > 0 and v_avg > 0 else 0.0
    t_avg = t_avg_eval + (t_avg_qc if c["qc_included_in_time"] else 0.0)

    eta_actual = deadline_for_hours(posted, t_actual, c)
    target = T * (1 - b)
    feasible = t_actual <= target * 1.05  # 5% 松弛

    t_full = W / hard_ceiling if hard_ceiling > 0 else float("inf")
    rec_deadline = None
    if t_full > T and hard_ceiling > 0:
        r = deadline_for_hours(posted, t_full, c)
        rec_deadline = r.strftime("%Y-%m-%d %H:%M") if r else None

    normal_names = {cand.name for cand in all_cands} - lead_names
    chosen_names = {cand.name for cand in chosen}
    remaining_domain_free = sum(
        1 for cand in all_cands if cand.matched_capabilities
        and cand.name in normal_names and cand.name not in chosen_names
        and cand.busy_hours < busy_thr)

    plan.update({
        "n_star": n_star, "n_star_formula": n_star_formula,
        "target_hours": round(target, 3),
        "t_avg": round(t_avg, 3), "t_actual": round(t_actual, 3),
        "eta_actual_at": eta_actual.strftime("%Y-%m-%d %H:%M") if eta_actual else None,
        "q_per_person": q_per_person,
        "feasible": bool(feasible),
        "t_full": round(t_full, 3) if t_full != float("inf") else None,
        "recommended_deadline": rec_deadline,
        "remaining_domain_free": remaining_domain_free,
        "chosen": [
            {
                "name": cand.name, "open_id": cand.open_id,
                "hourly": _hourly_with_fallback(cand, domain, c),
                "load_status": cand.load_status, "busy_hours": round(cand.busy_hours, 2),
                "is_lead": cand.name in lead_set,
                "assigned_q": q_split[i] if i < len(q_split) else 0,
                "assigned_hours": round(per_person_hours[i], 2) if i < len(per_person_hours) else 0.0,
                "role": ("评测(新手)" if cand in chosen_novice
                         else ("评测+交叉质检(组长)" if cand.name in lead_set else "评测+交叉质检")),
            }
            for i, cand in enumerate(chosen)
        ],
    })
    return plan


# ── 对外主入口 ──────────────────────────────────────────────────────────────
def allocate(task: dict, roster: list[dict], cfg: dict | None = None,
             domain_leads: dict[str, list[str]] | None = None,
             history: list[dict] | None = None) -> dict:
    """人力分配：给任务算所需人数、选人、切题量、判可行性。

    task:    {task_name, workload(Q), urgency(P0/P1/P2/高/中), posted_at,
              expected_delivery, [domain]}
    roster:  [{name, [open_id], capabilities:[领域], hourly_efficiency:{领域:题/h},
              busy_hours}...]
    cfg:     覆盖 DEFAULT_CONFIG 的部分键；domain_leads: {领域: [组长名]}。
    返回:    {available, domain, candidates, plan} 或 {available:False, reason}。
    """
    c = _cfg(cfg)
    domain = task.get("domain") or infer_domain(task)
    u_key = _urgency_key(task.get("urgency"))
    Q = _parse_workload(task.get("workload"))
    delivery_days = None
    dv = _parse_dt(task.get("expected_delivery"))
    if dv:
        delivery_days = max(0.0, (dv.date() - date.today()).days)

    cands = _build_candidates(roster, domain, u_key, Q, delivery_days, c)
    if not cands:
        return {"available": False, "reason": "empty_roster", "domain": domain, "candidates": []}
    if domain and not any(x.matched_capabilities for x in cands):
        return {"available": False, "reason": "no_capability_match", "domain": domain,
                "candidates": [asdict(x) for x in cands]}

    cands.sort(key=lambda x: x.fit_score, reverse=True)
    top_score = cands[0].fit_score
    top = [x for x in cands if x.fit_score == top_score]

    matched = [x for x in cands if x.matched_capabilities] or (list(cands) if not domain else [])
    matched.sort(key=lambda x: _extract_hourly(x.hourly_efficiency, domain), reverse=True)
    plan = _build_plan({**task, "domain": domain}, matched, cands, domain, domain_leads, c) if matched else None

    return {
        "available": True, "domain": domain,
        "top": [asdict(x) for x in top],
        "candidates": [asdict(x) for x in cands],
        "plan": plan,
    }


# ── 自检 ────────────────────────────────────────────────────────────────────
def _selftest() -> None:
    # 1. 工作日历：整个工作日 = 8h（10-12 + 13-19）
    a, b = datetime(2026, 7, 6, 9, 0), datetime(2026, 7, 6, 20, 0)  # 周一
    assert abs(available_hours(a, b) - 8.0) < 1e-6, available_hours(a, b)

    # 2. 跨周末：周五 9:00 → 周一 20:00，跳过周六日 = 16h
    assert abs(available_hours(datetime(2026, 7, 3, 9, 0), datetime(2026, 7, 6, 20, 0)) - 16.0) < 1e-6

    # 3. 节假日跳过
    got = available_hours(datetime(2026, 10, 1, 9, 0), datetime(2026, 10, 2, 20, 0),
                          {"holidays": ["2026-10-01"]})
    assert abs(got - 8.0) < 1e-6, got

    # 4. deadline_for_hours：从周一 10:00 起 8h → 周一 19:00
    assert deadline_for_hours(datetime(2026, 7, 6, 10, 0), 8.0) == datetime(2026, 7, 6, 19, 0)

    # 5. 领域推断
    assert infer_domain({"task_name": "帮忙做一批 Dashboard 标注"}) == "Dashboard"
    assert infer_domain({"task_name": "工作流评测"}) == "Workflow"

    # 6. 紧急度归一 & 缓冲档位
    c = _cfg(None)
    assert (_urgency_key("P0"), _urgency_key("高"), _urgency_key("中"), _urgency_key("普通")) == ("P0", "P0", "P1", "P2")
    assert _buffer_for("P0", c) == 0.5 and _buffer_for("P1", c) == 0.25 and _buffer_for("P2", c) == 0.0

    # 7. 复现设计文档示例：Q=50, v=3.7, P0, 单日 8h 窗口 → n*=⌈50/3.7/8⌉=2，兜底到 min_people=3
    roster = [{"name": f"人{i}", "capabilities": ["Building"],
               "hourly_efficiency": {"Building": 3.7}, "busy_hours": 0.0} for i in range(17)]
    task = {"task_name": "Building 批量", "workload": 50, "urgency": "P0",
            "posted_at": "2026-07-03 10:00", "expected_delivery": "2026-07-03 19:00"}
    res = allocate(task, roster)
    assert res["available"] and res["domain"] == "Building"
    plan = res["plan"]
    assert plan["n_star_formula"] == 2, plan             # ⌈W/T⌉ = ⌈13.5/8⌉ = 2
    assert plan["n_star"] == 3, plan["n_star"]           # 兜底到 min_people=3
    assert sum(p["assigned_q"] for p in plan["chosen"]) == 50  # 题量守恒
    assert len(plan["chosen"]) == 3
    # feasible 是对 buffered target(T×(1-b)=4h)的严判：3 人各 ~4.6h > 4h → 触发风险提示，
    # 但 t_actual 仍远小于原始窗口 T=8h（真实能当日交付）。这是 shipped 语义，非 bug。
    assert plan["feasible"] is False, plan
    assert plan["t_actual"] < plan["T"], plan

    # 8. 无匹配领域 → no_capability_match
    r2 = allocate({"task_name": "Table 任务", "workload": 10, "urgency": "P2"},
                  [{"name": "甲", "capabilities": ["Dashboard"], "hourly_efficiency": {"Dashboard": 5}}])
    assert r2["available"] is False and r2["reason"] == "no_capability_match", r2

    # 9. 硬不可行：题量远超单人窗口 → feasible False + 给出可执行的建议截止时间
    r3 = allocate({"task_name": "Building 大单", "workload": 300, "urgency": "P0",
                   "posted_at": "2026-07-06 10:00", "expected_delivery": "2026-07-06 11:00"},
                  [{"name": "独苗", "capabilities": ["Building"], "hourly_efficiency": {"Building": 3}}])
    assert r3["plan"]["feasible"] is False and r3["plan"]["recommended_deadline"], r3["plan"]

    # 10. 多领域组长份额减半：组长负责 2 领域时应分到更少题
    leads = {"Building": ["组长A"], "Table": ["组长A"]}
    r4 = allocate({"task_name": "Building 单子", "workload": 30, "urgency": "P1",
                   "posted_at": "2026-07-06 10:00", "expected_delivery": "2026-07-07 19:00"},
                  [{"name": "组长A", "capabilities": ["Building"], "hourly_efficiency": {"Building": 4}, "busy_hours": 0.0},
                   {"name": "员工B", "capabilities": ["Building"], "hourly_efficiency": {"Building": 4}, "busy_hours": 0.0},
                   {"name": "员工C", "capabilities": ["Building"], "hourly_efficiency": {"Building": 4}, "busy_hours": 0.0}],
                  domain_leads=leads)
    chosen = {p["name"]: p["assigned_q"] for p in r4["plan"]["chosen"]}
    assert chosen.get("组长A", 99) <= min(v for k, v in chosen.items() if k != "组长A"), chosen
    assert sum(chosen.values()) == 30, chosen

    print("human-allocation: all self-tests passed ✅")


if __name__ == "__main__":
    _selftest()
