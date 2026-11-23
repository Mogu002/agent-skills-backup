"""Probe each copy Base to reveal its real table name/rows/rev (defuses 坑1).

Usage:
  python scripts/probe_copies.py --tokens TOKEN1 TOKEN2 TOKEN3
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import run_lark


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", nargs="+", required=True)
    args = ap.parse_args()

    for tok in args.tokens:
        try:
            resp = run_lark([
                "base", "+table-list",
                "--base-token", tok,
                "--format", "json",
                "--as", "user",
            ])
            tables = resp["data"].get("tables", [])
            desc = "; ".join(
                f"{t.get('name')}(rows={t.get('records_count')},rev={t.get('rev')},id={t.get('id')})"
                for t in tables
            )
            print(f"{tok} -> {desc}")
        except Exception as e:
            print(f"{tok} -> ERROR: {e}")


if __name__ == "__main__":
    main()
