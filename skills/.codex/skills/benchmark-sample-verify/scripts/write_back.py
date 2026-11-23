"""Write verification verdicts back to the master table (机评-2 + 检查结果-2 only).

Input: a verdicts JSONL (default temp_data/verdicts.jsonl), each line:
  {"record_id": "...", "检查结果-2": "有问题|无问题|", "机评-2": "..."}
Only these two fields are written; empty string clears a cell.

Usage:
  python scripts/write_back.py --base-token <master base> --table-id <tbl> \
    [--verdicts temp_data/verdicts.jsonl] [--dry-run]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import run_lark

F_RESULT = "检查结果-2"
F_MACHINE = "机评-2"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-token", required=True)
    ap.add_argument("--table-id", required=True)
    ap.add_argument("--verdicts", default="temp_data/verdicts.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    updates = {}
    with open(args.verdicts, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            v = json.loads(line)
            rid = v["record_id"]
            fields = {}
            if F_RESULT in v:
                fields[F_RESULT] = v[F_RESULT]
            if F_MACHINE in v:
                # empty string clears the cell
                fields[F_MACHINE] = v[F_MACHINE] if v[F_MACHINE] else None
            updates[rid] = fields

    rids = list(updates.keys())
    print(f"{len(rids)} rows to update")
    if args.dry_run:
        print(json.dumps({"update_records": updates}, ensure_ascii=False, indent=2))
        return

    os.makedirs("temp_data", exist_ok=True)
    # batch in chunks of 100, serial
    for i in range(0, len(rids), 100):
        chunk = rids[i:i + 100]
        payload = {"update_records": {rid: updates[rid] for rid in chunk}}
        payload_path = f"temp_data/_wb_{i}.json"
        with open(payload_path, "w", encoding="utf-8") as pf:
            json.dump(payload, pf, ensure_ascii=False)
        rel = "./" + payload_path
        for attempt in range(5):
            try:
                resp = run_lark([
                    "base", "+record-batch-update",
                    "--base-token", args.base_token,
                    "--table-id", args.table_id,
                    "--json", "@" + rel,
                    "--format", "json",
                    "--as", "user",
                ])
                done = resp["data"].get("record_id_list", [])
                print(f"chunk {i}: updated {len(done)} rows")
                break
            except Exception as e:
                if "1254291" in str(e) and attempt < 4:
                    time.sleep(2 * (attempt + 1))
                    continue
                print(f"chunk {i}: ERROR {e}")
                break


if __name__ == "__main__":
    main()
