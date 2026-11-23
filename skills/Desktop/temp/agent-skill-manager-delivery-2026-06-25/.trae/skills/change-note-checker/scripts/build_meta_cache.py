#!/usr/bin/env python3
"""为 rows.jsonl 中出现的每个目标 Base 构建元数据缓存。

输出 temp_data/meta/<base_token>.json:
{"accessible": true, "base_name": "...", "tables": [{"id", "name", "fields": [{"id","name","type"}]}]}
无法访问的 Base 输出 {"accessible": false, ...}。

也可传 --tokens 显式指定 token（逗号分隔）。
用法:
  python3 scripts/build_meta_cache.py [--rows temp_data/rows.jsonl]
"""
import argparse
import json
import os
import re
import subprocess
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(SKILL_ROOT, "temp_data")
META_DIR = os.path.join(TEMP_DIR, "meta")

BASE_LINK_RE = re.compile(r"larkoffice\.com/base/([A-Za-z0-9]+)")


def run_cli(args):
    proc = subprocess.run(args, capture_output=True, text=True)
    try:
        return json.loads(proc.stdout), proc.returncode, proc.stderr
    except json.JSONDecodeError:
        return None, proc.returncode, proc.stdout + proc.stderr


def collect_tokens(rows_path):
    tokens = []
    seen = set()
    with open(rows_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            bu = row.get("sample_url") or ""
            m = BASE_LINK_RE.search(bu)
            if m and m.group(1) not in seen:
                seen.add(m.group(1))
                tokens.append(m.group(1))
    return tokens


def build_one(token):
    cache = {"accessible": False, "base_name": None, "tables": []}

    resp, code, err = run_cli([
        "lark-cli", "base", "+base-get",
        "--base-token", token, "--format", "json",
    ])
    if code != 0 or not resp or not resp.get("ok"):
        return cache

    cache["accessible"] = True
    try:
        cache["base_name"] = resp["data"].get("name")
    except Exception:
        pass

    resp, code, _ = run_cli([
        "lark-cli", "base", "+table-list",
        "--base-token", token, "--format", "json",
    ])
    if code != 0 or not resp.get("ok"):
        return cache
    tables = resp["data"].get("tables", [])

    for t in tables:
        table_info = {"id": t["id"], "name": t.get("name"), "fields": []}
        resp, code, _ = run_cli([
            "lark-cli", "base", "+field-list",
            "--base-token", token, "--table-id", t["id"],
            "--format", "json",
        ])
        if code == 0 and resp.get("ok"):
            for fld in resp["data"].get("fields", []):
                table_info["fields"].append({
                    "id": fld.get("id"),
                    "name": fld.get("name"),
                    "type": fld.get("type"),
                })
        cache["tables"].append(table_info)
    return cache


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=os.path.join(TEMP_DIR, "rows.jsonl"))
    ap.add_argument("--tokens", default="", help="逗号分隔的 base token，优先于 rows 扫描")
    args = ap.parse_args()

    if args.tokens:
        tokens = [t.strip() for t in args.tokens.split(",") if t.strip()]
    else:
        tokens = collect_tokens(args.rows)

    os.makedirs(META_DIR, exist_ok=True)
    ok_n = 0
    for token in tokens:
        cache = build_one(token)
        out = os.path.join(META_DIR, f"{token}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        status = "可访问" if cache["accessible"] else "无法访问"
        n_tables = len(cache["tables"])
        print(f"{token} -> {status}，{n_tables} 张表，缓存: {out}")
        if cache["accessible"]:
            ok_n += 1
    print(f"共 {len(tokens)} 个 Base，{ok_n} 个可访问，{len(tokens) - ok_n} 个无法访问")


if __name__ == "__main__":
    main()
