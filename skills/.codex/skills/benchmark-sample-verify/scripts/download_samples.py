"""Download record attachments to a local dir so they can be opened with Read.

Usage:
  python scripts/download_samples.py --base-token <copy> --table-id <tbl> \
    --field-id <attachment field_id> --record-id REC1 --record-id REC2 \
    --out-dir temp_data/att

Note: lark-cli --output only accepts a relative path inside the current dir.
Run this from the skill root so temp_data/ resolves correctly.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import run_lark


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-token", required=True)
    ap.add_argument("--table-id", required=True)
    ap.add_argument("--record-id", action="append", required=True)
    ap.add_argument("--field-id", default=None, help="limit to one attachment field (optional)")
    ap.add_argument("--out-dir", default="temp_data/att")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    out_rel = args.out_dir if args.out_dir.startswith("./") else "./" + args.out_dir

    for rid in args.record_id:
        call = [
            "base", "+record-download-attachment",
            "--base-token", args.base_token,
            "--table-id", args.table_id,
            "--record-id", rid,
            "--output", out_rel + "/",
            "--overwrite",
            "--format", "json",
            "--as", "user",
        ]
        try:
            resp = run_lark(call)
            for d in resp["data"].get("downloaded", []):
                print(f"{rid} <- {d.get('name')} ({d.get('size_bytes')} B) -> {d.get('saved_path')}")
        except Exception as e:
            print(f"{rid} -> ERROR: {e}")


if __name__ == "__main__":
    main()
