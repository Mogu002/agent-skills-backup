"""Fetch rows to verify from the master control table.

Usage:
  python scripts/fetch_rows.py --base-token <tbl base> --table-id <tbl> [--mode empty|all] [--rows Q113,Q71]

Output: temp_data/rows.jsonl, one JSON per row with parsed copy base_tokens.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import run_lark, parse_record_list, cell_text, extract_base_tokens

# Field names as they appear in the master table. Adjust here if the table renames columns.
F_QNO = "题号"
F_INSTRUCTION = "指令"
F_TABLES = "考察数据表名"
F_COPIES = "考察数据表的副本"
F_FOCUS = "考察点"
F_DESIGN = "样张设计思路"
F_RESULT = "检查结果-2"
F_MACHINE = "机评-2"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-token", required=True)
    ap.add_argument("--table-id", required=True)
    ap.add_argument("--mode", choices=["empty", "all"], default="empty")
    ap.add_argument("--rows", default="", help="comma-separated 题号, overrides --mode")
    ap.add_argument("--out", default="temp_data/rows.jsonl")
    args = ap.parse_args()

    resp = run_lark([
        "base", "+record-list",
        "--base-token", args.base_token,
        "--table-id", args.table_id,
        "--limit", "200",
        "--format", "json",
        "--as", "user",
    ])
    records, _ = parse_record_list(resp)

    want = set(x.strip() for x in args.rows.split(",") if x.strip())
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    n = 0
    with open(args.out, "w", encoding="utf-8") as fout:
        for rec in records:
            f = rec["fields"]
            qno = cell_text(f.get(F_QNO))
            result = cell_text(f.get(F_RESULT)).strip()
            if want:
                if qno not in want:
                    continue
            elif args.mode == "empty" and result:
                continue
            copies_raw = cell_text(f.get(F_COPIES))
            row = {
                "record_id": rec["record_id"],
                "题号": qno,
                "instruction": cell_text(f.get(F_INSTRUCTION)),
                "tables": cell_text(f.get(F_TABLES)),
                "focus": cell_text(f.get(F_FOCUS)),
                "design": cell_text(f.get(F_DESIGN)),
                "copy_links_raw": copies_raw,
                "copy_tokens": extract_base_tokens(copies_raw),
                "cur_result": result,
                "cur_machine": cell_text(f.get(F_MACHINE)),
            }
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {n} rows -> {args.out}")


if __name__ == "__main__":
    main()
