#!/usr/bin/env python3
"""
计算飞书多维表格评测/质检准确率（总体 + 按人员分人），可选按目标表格式写入。

用法：
  # 只统计打印
  python3 calc_accuracy.py       --base-token <base_token>       --table-id  <table_id>

  # 标注准确率：统计并写入目标表
  python3 calc_accuracy.py       --base-token <base_token> --table-id <table_id>       --write-base-token <target_base_token>       --write-table-id  <target_table_id>       --eval-type 标注       --parent-project Decision       --source-url "https://bytedance.larkoffice.com/base/<token>?table=<tbl>&view=<view>"

  # 质检准确率：默认按 reviewer 字段候选（审核人员/审核人）自动找字段
  python3 calc_accuracy.py       --base-token <base_token> --table-id <table_id>       --eval-type 质检

输出：
  1. 总体 + 分人 两张表格；
  2. 若给了 --write-base-token / --write-table-id：
     - 拼装成目标表列（日期/类型/父项目/子项目/作业表URL/总数/通过/保留后/修改/异常/正确率/人员）
     - 打印将要写入的行；
     - 未加 --dry-run 时调用 lark-cli base +record-batch-create 写入。

正确率规则：
    标注：错误数 = count(通过-修改后) + count(异常)
         正确率 = (总数 - 错误数) / 总数
    质检：错误数 = count(通过-保留一轮结果)
         正确率 = (总数 - 错误数) / 总数

人员字段支持三种类型：
  - user 字段：单元格 = [{id, name}]，直接取 open_id
  - select 字段（含脏值）：单元格 = ["季鑫鑫"] 之类的字符串；
    脚本会用 lark-cli contact +search-user 逐一验证是否是真实用户，
    非真人的选项（如 "decision 错题"/"image.png"/"permission agent"）会被自动过滤。
  - text 字段：单元格 = "季鑫鑫"；走与 select 相同的人名校验/解析路径

reviewer 字段名默认按类型自动选择：
  - 标注：优先 `评测人员`，其次 `评测人`
  - 质检：优先 `审核人员`，其次 `审核人`

目标表新增字段说明（由 agent 在调用脚本前确定，脚本只做透传写入）：
  - 父项目（--parent-project）：agent 根据 Base 名意图识别，不靠脚本猜测
  - 子项目（--sub-project）：默认 <Base名> - <源表表名>
  - 作业表URL（--source-url）：源表的完整飞书分享链接

依赖：lark-cli（已登录），Python 3.8+，无第三方库。
"""

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
from collections import defaultdict

EVAL_CONFIGS = {
    "标注": {
        "error_options": {"通过-修改后", "异常"},
        "reviewer_fields": ["评测人员", "评测人"],
        "reviewer_label": "评测人员",
    },
    "质检": {
        "error_options": {"通过-保留一轮结果"},
        "reviewer_fields": ["审核人员", "审核人"],
        "reviewer_label": "审核人员",
    },
}

TARGET_FIELDS = [
    "日期", "类型", "父项目", "子项目", "作业表URL",
    "总数", "通过", "保留后", "修改", "异常",
    "正确率", "人员",
]

# 行中各字段在 TARGET_FIELDS 中的索引（便于 write_target_rows 提取显示）
_IDX_DATE = 0
_IDX_TYPE = 1
_IDX_PARENT = 2
_IDX_SUB = 3
_IDX_URL = 4
_IDX_TOTAL = 5
_IDX_PASS = 6
_IDX_KEEP = 7
_IDX_MODIFY = 8
_IDX_ABNORMAL = 9
_IDX_ACCURACY = 10
_IDX_USER = 11


def _lark_env() -> dict:
    env = os.environ.copy()
    env["LARKSUITE_CLI_NO_UPDATE_NOTIFIER"] = "1"
    env["LARKSUITE_CLI_NO_SKILLS_NOTIFIER"] = "1"
    return env


def _run_lark(cmd: list, allow_error: bool = False) -> dict:
    proc = subprocess.run(cmd, capture_output=True, text=True, env=_lark_env())
    if proc.returncode != 0:
        if allow_error:
            try:
                return json.loads(proc.stderr)
            except Exception:
                return {"ok": False, "error": {"message": proc.stderr or proc.stdout}}
        sys.stderr.write((proc.stderr or "") + "\n" + (proc.stdout or "") + "\n")
        sys.exit(f"lark-cli 调用失败 (exit={proc.returncode}): {' '.join(cmd[:5])}...")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        sys.exit(f"无法解析 lark-cli 输出为 JSON: {e}\n原始输出: {proc.stdout[:500]}")
    if not payload.get("ok", True) and not allow_error:
        sys.exit(f"lark-cli 返回 ok=false: {payload.get('error')}")
    return payload


def fetch_base_name(base_token: str) -> str:
    payload = _run_lark([
        "lark-cli", "base", "+base-get",
        "--base-token", base_token, "--as", "user",
    ])
    return payload.get("data", {}).get("base", {}).get("name") or base_token


def fetch_table_name(base_token: str, table_id: str) -> str:
    payload = _run_lark([
        "lark-cli", "base", "+table-list",
        "--base-token", base_token, "--as", "user",
    ])
    tables = payload.get("data", {}).get("tables") or payload.get("data", {}).get("items") or []
    for t in tables:
        if t.get("id") == table_id or t.get("table_id") == table_id:
            return t.get("name") or table_id
    return table_id


def fetch_field_meta(base_token: str, table_id: str, field_name: str) -> dict:
    payload = _run_lark([
        "lark-cli", "base", "+field-get",
        "--base-token", base_token, "--table-id", table_id,
        "--field-id", field_name, "--as", "user",
    ], allow_error=True)
    if not payload.get("ok", True):
        return {}
    return payload.get("data", {}).get("field", {}) or {}


def resolve_reviewer_field(base_token: str, table_id: str,
                           eval_type: str, reviewer_field: str | None) -> tuple[str, dict]:
    if reviewer_field:
        meta = fetch_field_meta(base_token, table_id, reviewer_field)
        if not meta:
            sys.exit(f"源表未找到 reviewer 字段「{reviewer_field}」；请核对字段名。")
        return reviewer_field, meta

    candidates = EVAL_CONFIGS[eval_type]["reviewer_fields"]
    for name in candidates:
        meta = fetch_field_meta(base_token, table_id, name)
        if meta:
            return name, meta
    sys.exit(
        f"未找到 reviewer 字段；{eval_type} 默认依次查找 {candidates}.\n"
        f"请显式传 --reviewer-field 指定字段名。"
    )


def fetch_records(base_token: str, table_id: str,
                  result_field: str, reviewer_field: str) -> list:
    rows = []
    offset = 0
    while True:
        payload = _run_lark([
            "lark-cli", "base", "+record-list",
            "--base-token", base_token,
            "--table-id", table_id,
            "--field-id", result_field,
            "--field-id", reviewer_field,
            "--limit", "200",
            "--offset", str(offset),
            "--format", "json",
            "--as", "user",
        ])
        data = payload.get("data", {})
        matrix = data.get("data", []) or []
        headers = data.get("fields", []) or []
        if not headers:
            break
        try:
            i_result = headers.index(result_field)
            i_user = headers.index(reviewer_field)
        except ValueError:
            sys.exit(f"record-list 返回字段顺序异常: {headers}")
        for r in matrix:
            result_cell = r[i_result] if i_result < len(r) else None
            user_cell = r[i_user] if i_user < len(r) else None
            result_val = None
            if isinstance(result_cell, list) and result_cell:
                result_val = result_cell[0]
            elif isinstance(result_cell, str):
                result_val = result_cell
            rows.append((result_val, user_cell))
        if not data.get("has_more"):
            break
        offset += len(matrix) or 200
    return rows


def resolve_open_id(name: str) -> str:
    """通过 contact +search-user 精确匹配 name → open_id；找不到返回空串。

    contact +search-user 返回体里人名放在 `localized_name`（也可能是 `name`），
    两者都要匹配。多个候选时优先精确命中；命中失败则返回空串（脚本会记入 skip 报表）。
    """
    payload = _run_lark([
        "lark-cli", "contact", "+search-user",
        "--query", name, "--page-size", "10", "--as", "user",
    ], allow_error=True)
    if not payload.get("ok", True):
        return ""
    users = payload.get("data", {}).get("users", []) or []
    target = name.strip()
    for u in users:
        candidates = [u.get("localized_name"), u.get("name")]
        if any((c or "").strip() == target for c in candidates):
            return u.get("open_id") or ""
    return ""


def _as_reviewer_items(cell, field_type: str) -> list:
    if cell is None:
        return []
    if field_type == "user":
        if isinstance(cell, list):
            return cell
        if isinstance(cell, dict):
            return [cell]
        return []
    if isinstance(cell, list):
        return cell
    return [cell]


def normalize_reviewer(cell, field_type: str, name_to_oid: dict, verified_bad: set) -> list:
    """把源单元格标准化成 [{id, name}, ...]。

    field_type == 'user'：直接取 id/name。
    field_type in {'select', 'text'}：字符串走 name→open_id 解析；
        - 缓存命中则复用
        - 查不到则记入 verified_bad，返回 []
    """
    if field_type == "user":
        out = []
        for u in _as_reviewer_items(cell, field_type):
            if isinstance(u, dict) and u.get("id"):
                out.append({"id": u["id"], "name": u.get("name") or u["id"]})
        return out

    out = []
    for raw in _as_reviewer_items(cell, field_type):
        name = raw if isinstance(raw, str) else (raw.get("name") if isinstance(raw, dict) else None)
        if not name or not name.strip():
            continue
        name = name.strip()
        if name in verified_bad:
            continue
        if name in name_to_oid:
            oid = name_to_oid[name]
            if oid:
                out.append({"id": oid, "name": name})
            continue
        oid = resolve_open_id(name)
        name_to_oid[name] = oid
        if oid:
            out.append({"id": oid, "name": name})
        else:
            verified_bad.add(name)
    return out


def calc_metrics(buckets: dict, eval_type: str) -> dict:
    total = sum(buckets.values())
    error_options = EVAL_CONFIGS[eval_type]["error_options"]
    errors = sum(c for opt, c in buckets.items() if opt in error_options)
    pass_rate = (total - errors) / total if total else 0.0
    err_rate = errors / total if total else 0.0
    return {
        "total": total,
        "errors": errors,
        "pass_rate": pass_rate,
        "err_rate": err_rate,
        "buckets": buckets,
    }


def aggregate(records: list, include_null: bool, reviewer_field_type: str):
    """返回 (overall_buckets, per_user_dict, skipped_dirty)。

    约束：总体总数/正确率分母不包含 reviewer 为空的记录。
    若 include_null=True，这些记录只进入「未指派」桶用于排障，不计入 overall。
    """
    overall = defaultdict(int)
    per_user = {}
    skipped_dirty = defaultdict(int)
    name_to_oid: dict = {}
    verified_bad: set = set()
    for result, cell in records:
        if result is None:
            continue

        users = normalize_reviewer(cell, reviewer_field_type, name_to_oid, verified_bad)
        count_in_overall = bool(users)
        if not users:
            raw_items = _as_reviewer_items(cell, reviewer_field_type)
            if include_null:
                users = [{"id": "<未指派>", "name": "<未指派>"}]
            else:
                if raw_items:
                    for raw in raw_items:
                        if isinstance(raw, str):
                            skipped_dirty[raw] += 1
                        elif isinstance(raw, dict):
                            skipped_dirty[raw.get("name") or raw.get("id") or "<未知>"] += 1
                        else:
                            skipped_dirty[str(raw)] += 1
                else:
                    skipped_dirty["<空>"] += 1
                continue

        if count_in_overall:
            overall[result] += 1

        for u in users:
            uid = u.get("id") or "<未指派>"
            slot = per_user.setdefault(uid, {"user": u, "buckets": defaultdict(int)})
            slot["buckets"][result] += 1
    return overall, per_user, skipped_dirty


def fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%" if v is not None else "-"


def print_overall(overall: dict, eval_type: str):
    m = calc_metrics({k: v for k, v in overall.items() if k != "<空>"}, eval_type)
    print("== 总体 ==")
    parts = " | ".join(f"{k} {v}" for k, v in sorted(overall.items(), key=lambda x: -x[1]))
    print(f"总数 {m['total']} | {parts}")
    if eval_type == "质检":
        breakdown = f"通过-保留一轮结果 {overall.get('通过-保留一轮结果', 0)}"
    else:
        breakdown = (
            f"通过-修改后 {overall.get('通过-修改后', 0)} + "
            f"异常 {overall.get('异常', 0)}"
        )
    print(f"错误 {m['errors']}（{breakdown}） → 正确率 {fmt_pct(m['pass_rate'])} / 错误率 {fmt_pct(m['err_rate'])}")


def print_by_reviewer(per_user: dict, eval_type: str, reviewer_label: str):
    print(f"\n== 按{reviewer_label} ==")
    headers = [reviewer_label, "总数", "通过", "保留", "修改后", "异常", "错误数", "正确率"]
    print("{:<10} {:>4} {:>4} {:>4} {:>5} {:>4} {:>6} {:>7}".format(*headers))

    rows_out = []
    for uid, slot in per_user.items():
        m = calc_metrics(dict(slot["buckets"]), eval_type)
        rows_out.append((slot["user"], m, slot["buckets"]))
    rows_out.sort(key=lambda x: -x[1]["total"])
    for user, m, b in rows_out:
        name = user.get("name") or user.get("id", "<未知>")
        print("{:<10} {:>4} {:>4} {:>4} {:>5} {:>4} {:>6} {:>7}".format(
            name,
            m["total"],
            b.get("通过", 0),
            b.get("通过-保留一轮结果", 0),
            b.get("通过-修改后", 0),
            b.get("异常", 0),
            m["errors"],
            fmt_pct(m["pass_rate"]),
        ))


def print_skipped(skipped_dirty: dict, reviewer_label: str):
    if not skipped_dirty:
        return
    print(f"\n== 跳过的非人名/无效{reviewer_label}（select/text 脏值 or 空值）==")
    for name, cnt in sorted(skipped_dirty.items(), key=lambda x: -x[1]):
        print(f"  {name}	{cnt}")


def ensure_target_option(target_base: str, target_table: str,
                        field_name: str, option_name: str,
                        auto_add: bool, dry_run: bool = False) -> None:
    """确保目标表 select 字段包含 option_name；缺失时按 auto_add 决定是否自动追加。"""
    field = fetch_field_meta(target_base, target_table, field_name)
    if not field:
        sys.exit(f"目标表未找到字段「{field_name}」；请核对目标表列名与 TARGET_FIELDS。")
    if field.get("type") != "select":
        return
    existing = [o.get("name") for o in (field.get("options") or [])]
    if option_name in existing:
        return
    print(f"\n[预检] 目标表「{field_name}」未包含选项：{option_name}")
    if dry_run:
        if auto_add:
            print(f"[预检][dry-run] 若真正写入，将自动追加选项「{option_name}」")
        return
    if not auto_add:
        sys.exit(
            f"目标表「{field_name}」缺少选项「{option_name}」；\n"
            f"请手动追加该选项，或加参数 --auto-add-option 让脚本自动追加。\n"
            f"现有选项：{existing}"
        )
    new_options = [{"name": n} for n in existing] + [{"name": option_name}]
    payload = {
        "name": field.get("name") or field_name,
        "type": "select",
        "multiple": field.get("multiple", False),
        "options": new_options,
    }
    resp = _run_lark([
        "lark-cli", "base", "+field-update",
        "--base-token", target_base, "--table-id", target_table,
        "--field-id", field.get("id") or field_name,
        "--yes", "--as", "user",
        "--json", json.dumps(payload, ensure_ascii=False),
    ], allow_error=True)
    if not resp.get("ok", True):
        sys.exit(f"追加选项失败：{resp.get('error')}")
    print(f"[预检] 已自动追加选项「{option_name}」")


def build_target_rows(per_user: dict, sub_project: str, eval_type: str,
                      date_str: str, parent_project: str = "",
                      source_url: str = "") -> list:
    rows = []
    entries = []
    for uid, slot in per_user.items():
        m = calc_metrics(dict(slot["buckets"]), eval_type)
        entries.append((slot["user"], m, slot["buckets"]))
    entries.sort(key=lambda x: -x[1]["total"])

    for user, m, b in entries:
        user_cell = None
        if user and user.get("id") and user.get("id") != "<未指派>":
            user_cell = [{"id": user["id"]}]
        row = [
            date_str,           # 日期
            eval_type,          # 类型
            parent_project,     # 父项目（agent 传入，可能为空串）
            sub_project,        # 子项目
            source_url,         # 作业表URL（agent 传入，可能为空串）
            m["total"],         # 总数
            b.get("通过", 0),   # 通过
            b.get("通过-保留一轮结果", 0),  # 保留后
            b.get("通过-修改后", 0),         # 修改
            b.get("异常", 0),   # 异常
            round(m["pass_rate"], 4),  # 正确率
            user_cell,          # 人员
        ]
        rows.append(row)
    return rows


def write_target_rows(target_base_token: str, target_table_id: str,
                      rows: list, dry_run: bool):
    payload = {"fields": TARGET_FIELDS, "rows": rows}
    print("\n== 写入目标表 ==")
    print(f"目标: base={target_base_token} table={target_table_id}")
    print("字段顺序:", " | ".join(TARGET_FIELDS))
    for r in rows:
        who = ""
        if isinstance(r[_IDX_USER], list) and r[_IDX_USER]:
            who = r[_IDX_USER][0].get("id", "")
        print(
            f"  {r[_IDX_DATE]} | {r[_IDX_TYPE]} | 父={r[_IDX_PARENT]} | "
            f"子={r[_IDX_SUB]} | URL={r[_IDX_URL]} | "
            f"总数={r[_IDX_TOTAL]} 通过={r[_IDX_PASS]} 保留={r[_IDX_KEEP]} "
            f"修改={r[_IDX_MODIFY]} 异常={r[_IDX_ABNORMAL]} "
            f"正确率={r[_IDX_ACCURACY]} 人员={who}"
        )

    if dry_run:
        print("\n[dry-run] 未写入。去掉 --dry-run 才会真正写入。")
        return

    cmd = [
        "lark-cli", "base", "+record-batch-create",
        "--base-token", target_base_token,
        "--table-id", target_table_id,
        "--json", json.dumps(payload, ensure_ascii=False),
        "--as", "user",
    ]
    resp = _run_lark(cmd)
    created = resp.get("data", {}).get("record_id_list", [])
    print(f"写入成功：{len(created)} 条记录 → {created}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-token", required=True, help="源表 base_token")
    ap.add_argument("--table-id", required=True, help="源表 table_id")
    ap.add_argument("--result-field", default="审核结果")
    ap.add_argument("--reviewer-field",
                    help="reviewer 字段名；不传时按 eval-type 自动尝试默认候选")
    ap.add_argument("--reviewer-field-type", choices=["auto", "user", "select", "text"], default="auto",
                    help="reviewer 字段类型；auto = 通过 field-get 自动识别")
    ap.add_argument("--include-null", action="store_true",
                    help="包含未指派 reviewer 的记录（默认跳过）")

    ap.add_argument("--write-base-token", help="目标（准确率汇总）表 base_token；给了才写入")
    ap.add_argument("--write-table-id", help="目标表 table_id；配合 --write-base-token 使用")
    ap.add_argument("--eval-type", choices=["标注", "质检"], default="标注",
                    help="目标表 类型 字段（单选）")
    ap.add_argument("--parent-project", default="",
                    help="父项目选项（由 agent 根据 Base 名意图识别后传入；空串时不写入该列）")
    ap.add_argument("--sub-project",
                    help="目标表 子项目；不传时用 <Base名> - <源表表名>")
    # 兼容旧参数名 --project-name（映射到 sub-project）
    ap.add_argument("--project-name", dest="sub_project",
                    help="(已弃用) 等效于 --sub-project")
    ap.add_argument("--source-url", default="",
                    help="源表的完整飞书分享链接（含 view），填入目标表 作业表URL 列")
    ap.add_argument("--date", help="目标表 日期，格式 YYYY-MM-DD；不传时用今天")
    ap.add_argument("--dry-run", action="store_true",
                    help="仅打印将要写入的行，不真正写入")
    ap.add_argument("--auto-add-option", action="store_true", default=True,
                    help="目标表 select 字段缺少选项时自动追加（默认开启）")
    ap.add_argument("--no-auto-add-option", dest="auto_add_option",
                    action="store_false",
                    help="关闭自动追加选项（选项缺失时报错停下）")

    args = ap.parse_args()

    reviewer_field, reviewer_meta = resolve_reviewer_field(
        args.base_token, args.table_id, args.eval_type, args.reviewer_field
    )
    print(f"[info] reviewer 字段 = {reviewer_field}")

    if args.reviewer_field_type == "auto":
        ftype = reviewer_meta.get("type")
        if ftype not in ("user", "select", "text"):
            sys.exit(
                f"字段「{reviewer_field}」类型={ftype!r}，脚本仅支持 user / select / text。\n"
                f"用 --reviewer-field 换字段，或用 --reviewer-field-type 强制指定。"
            )
        print(f"[info] reviewer 字段类型 = {ftype}")
    else:
        ftype = args.reviewer_field_type

    records = fetch_records(args.base_token, args.table_id,
                            args.result_field, reviewer_field)
    overall, per_user, skipped_dirty = aggregate(records, args.include_null, ftype)

    reviewer_label = reviewer_field or EVAL_CONFIGS[args.eval_type]["reviewer_label"]
    print_overall(overall, args.eval_type)
    print_by_reviewer(per_user, args.eval_type, reviewer_label)
    print_skipped(skipped_dirty, reviewer_label)

    if args.write_base_token and args.write_table_id:
        if args.sub_project:
            sub_project = args.sub_project
        else:
            base_name = fetch_base_name(args.base_token)
            table_name = fetch_table_name(args.base_token, args.table_id)
            sub_project = f"{base_name} - {table_name}"
        print(f"\n[info] 子项目 = {sub_project}")
        if args.parent_project:
            print(f"[info] 父项目 = {args.parent_project}")
        if args.source_url:
            print(f"[info] 作业表URL = {args.source_url}")

        # 确保目标表 select 选项存在
        ensure_target_option(
            args.write_base_token, args.write_table_id,
            "子项目", sub_project, args.auto_add_option,
            dry_run=args.dry_run,
        )
        if args.parent_project:
            ensure_target_option(
                args.write_base_token, args.write_table_id,
                "父项目", args.parent_project, args.auto_add_option,
                dry_run=args.dry_run,
            )

        date_str = f"{args.date} 00:00:00" if args.date else _dt.date.today().strftime("%Y-%m-%d 00:00:00")
        rows = build_target_rows(per_user, sub_project, args.eval_type,
                                 date_str, args.parent_project, args.source_url)
        write_target_rows(args.write_base_token, args.write_table_id, rows, args.dry_run)
    elif args.write_base_token or args.write_table_id:
        sys.exit("必须同时提供 --write-base-token 与 --write-table-id")


if __name__ == "__main__":
    main()
