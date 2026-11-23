#!/usr/bin/env python3
"""把逐题结果串行回写到主控表，只写 机评-2 / 检查结果-2 两个字段。

输入 results.jsonl，每行:
  {"record_id":"rec...","item_id":"054","status":"ok|problem|inaccessible","critique":"..."}

回写规则:
  ok            -> 检查结果-2="无问题"，机评-2 清空(null)
  problem       -> 检查结果-2="有问题"，机评-2=精简后的错误条目
  inaccessible  -> 只写 机评-2（注明未能核验），检查结果-2 不动（留空）

单批最多 200 条；遇 1254291 写冲突短暂等待后重试。覆盖写幂等，可安全续跑。

用法:
  python3 scripts/write_back.py --base-token <token> --table-id <tbl> \
    --results temp_data/results.jsonl
"""
import argparse
import json
import os
import subprocess
import sys
import time

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(SKILL_ROOT, "temp_data")

FIELD_RESULT = "检查结果-2"
FIELD_CRITIQUE = "机评-2"
INACCESSIBLE_NOTE = "目标 Base 无法访问/无权限，未能核验"
CHUNK = 100
MAX_RETRY = 5


def build_fields(item):
    status = item["status"]
    if status == "ok":
        return {FIELD_RESULT: "无问题", FIELD_CRITIQUE: None}
    if status == "problem":
        critique = (item.get("critique") or "").strip()
        if not critique:
            raise ValueError(f"record {item.get('record_id')} 标记 problem 但 critique 为空")
        return {FIELD_RESULT: "有问题", FIELD_CRITIQUE: critique}
    if status == "inaccessible":
        # 只写 机评-2；检查结果-2 留空不写
        note = (item.get("critique") or "").strip() or INACCESSIBLE_NOTE
        return {FIELD_CRITIQUE: note}
    raise ValueError(f"未知 status: {status}")


def update_chunk(base_token, table_id, chunk, chunk_index):
    update_records = {}
    for item in chunk:
        update_records[item["record_id"]] = build_fields(item)
    body = {"update_records": update_records}

    # lark-cli 要求 @file 必须是当前工作目录内的相对路径，因此在 SKILL_ROOT 下运行
    os.makedirs(TEMP_DIR, exist_ok=True)
    payload_name = os.path.join("temp_data", f"_payload_{chunk_index}.json")
    payload_abs = os.path.join(SKILL_ROOT, payload_name)
    with open(payload_abs, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False)

    cwd_was = os.getcwd()
    os.chdir(SKILL_ROOT)
    try:
        for attempt in range(1, MAX_RETRY + 1):
            proc = subprocess.run([
                "lark-cli", "base", "+record-batch-update",
                "--base-token", base_token,
                "--table-id", table_id,
                "--json", f"@{payload_name}",
                "--format", "json",
            ], capture_output=True, text=True)
            try:
                resp = json.loads(proc.stdout)
            except json.JSONDecodeError:
                resp = None

            if proc.returncode == 0 and resp and resp.get("ok"):
                ignored = None
                try:
                    ignored = resp["data"].get("ignored_fields")
                except Exception:
                    pass
                return True, ignored

            err_text = proc.stdout + proc.stderr
            if "1254291" in err_text and attempt < MAX_RETRY:
                wait = 2 * attempt
                print(f"  写冲突(1254291)，{wait}s 后重试（第 {attempt} 次）")
                time.sleep(wait)
                continue
            return False, err_text
        return False, "超过最大重试次数"
    finally:
        os.chdir(cwd_was)
        try:
            os.unlink(payload_abs)
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-token", required=True)
    ap.add_argument("--table-id", required=True)
    ap.add_argument("--results", default=os.path.join(TEMP_DIR, "results.jsonl"))
    args = ap.parse_args()

    items = []
    with open(args.results, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    if not items:
        print("没有可回写的结果")
        return

    done = 0
    for i in range(0, len(items), CHUNK):
        chunk = items[i:i + CHUNK]
        ok, info = update_chunk(args.base_token, args.table_id, chunk, i // CHUNK)
        if not ok:
            sys.stderr.write(f"回写失败，中止于第 {i // CHUNK + 1} 批（record {chunk[0]['record_id']} 起）:\n{info}\n")
            sys.stderr.write("修正后重跑本命令即可，覆盖写幂等不会产生重复数据。\n")
            sys.exit(1)
        done += len(chunk)
        extra = ""
        if info:
            extra = f"，ignored_fields: {json.dumps(info, ensure_ascii=False)}"
        print(f"已回写 {done}/{len(items)}{extra}")
        time.sleep(1)

    print(f"全部回写完成: {done} 条")


if __name__ == "__main__":
    main()
