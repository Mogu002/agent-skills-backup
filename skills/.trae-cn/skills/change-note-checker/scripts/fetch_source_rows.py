#!/usr/bin/env python3
"""拉取主控表视图内的题目行，输出 temp_data/rows.jsonl。

每行 JSON: {record_id, item_id, sample_url, note, result, critique}
- sample_url 来自【修改样张（已创建副本）】字段
- result/critique 为已有的 检查结果-2 / 机评-2 内容。

用法:
  python3 scripts/fetch_source_rows.py \
    --base-token <token> --table-id <tbl> --view-id <vew> \
    --mode empty|all
"""
import argparse
import json
import os
import subprocess
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(SKILL_ROOT, "temp_data")

FIELD_ID = "ID"
FIELD_SAMPLE = "修改样张（已创建副本）"
FIELD_NOTE = "对应样张变动说明"
FIELD_RESULT = "检查结果-2"
FIELD_CRITIQUE = "机评-2"
PROJECT_FIELDS = [FIELD_ID, FIELD_SAMPLE, FIELD_NOTE, FIELD_RESULT, FIELD_CRITIQUE]


def run_cli(args):
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        raise RuntimeError(f"命令失败: {' '.join(args[:4])}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        sys.stderr.write(proc.stdout)
        raise


def is_empty(v):
    return v is None or (isinstance(v, str) and v.strip() == "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-token", required=True)
    ap.add_argument("--table-id", required=True)
    ap.add_argument("--view-id", required=True)
    ap.add_argument("--mode", choices=["empty", "all"], default="empty",
                    help="empty=仅 检查结果-2 为空的行（默认）；all=视图全量")
    ap.add_argument("--output", default=os.path.join(TEMP_DIR, "rows.jsonl"))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    all_rows = []
    offset = 0
    page_size = 200
    while True:
        cli_args = [
            "lark-cli", "base", "+record-list",
            "--base-token", args.base_token,
            "--table-id", args.table_id,
            "--view-id", args.view_id,
            "--limit", str(page_size),
            "--offset", str(offset),
            "--format", "json",
        ]
        for f in PROJECT_FIELDS:
            cli_args += ["--field-id", f]
        resp = run_cli(cli_args)
        data = resp["data"]
        cols = data["fields"]
        matrix = data["data"]
        rids = data["record_id_list"]
        for rid, raw in zip(rids, matrix):
            m = dict(zip(cols, raw))
            all_rows.append({
                "record_id": rid,
                "item_id": m.get(FIELD_ID),
                "sample_url": m.get(FIELD_SAMPLE),
                "note": m.get(FIELD_NOTE),
                "result": m.get(FIELD_RESULT),
                "critique": m.get(FIELD_CRITIQUE),
            })
        if not data.get("has_more"):
            break
        offset += len(matrix)

    if args.mode == "empty":
        selected = [r for r in all_rows if is_empty(r["result"])]
    else:
        selected = all_rows

    with open(args.output, "w", encoding="utf-8") as f:
        for r in selected:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"视图总行数: {len(all_rows)}；本次待检查: {len(selected)}；输出: {args.output}")


if __name__ == "__main__":
    main()
