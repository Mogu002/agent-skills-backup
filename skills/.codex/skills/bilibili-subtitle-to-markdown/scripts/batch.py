#!/usr/bin/env python3
"""Read a favorites folder and save its native subtitles with resumable progress."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse

import extract


def folder_id(source):
    if source.isdecimal() and int(source) > 0:
        return str(int(source))
    url = urllib.parse.urlsplit(source)
    if url.scheme == "https" and url.hostname in ("space.bilibili.com", "www.bilibili.com"):
        value = urllib.parse.parse_qs(url.query).get("fid", [""])[0]
        if value.isdecimal() and int(value) > 0:
            return str(int(value))
    raise extract.SubtitleError("请提供正整数收藏夹 ID，或含 fid= 的 B站收藏夹链接", "BAD_INPUT")


def save_state(path, state):
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def new_state(fid, timestamps):
    return {"schema": 1, "folder_id": fid, "timestamps": timestamps, "next_page": 1,
            "list_finished": False, "list_complete": False, "expected_count": None, "entries": {}}


def add_page(state, wrapper):
    if str(wrapper.get("folder_id")) != state["folder_id"] or wrapper.get("page") != state["next_page"]:
        raise extract.SubtitleError("收藏夹 ID 或页码不匹配 batch-state.json 的 next_page", "BAD_PAGE")
    payload = wrapper.get("payload") or {}
    code = payload.get("code")
    if code != 0:
        reason = "THROTTLED" if code in (-352, -412, -509) else "BROWSER_REQUIRED"
        raise extract.SubtitleError(f"收藏夹读取失败，接口 code={code}", reason)
    data = payload.get("data") or {}
    info = data.get("info") or {}
    if str(info.get("id")) != state["folder_id"]:
        raise extract.SubtitleError("接口返回了其他收藏夹的数据", "BAD_PAGE")
    total = info.get("media_count")
    if not isinstance(total, int) or total < 0 or data.get("has_more") not in (True, False, 0, 1):
        raise extract.SubtitleError("收藏夹响应缺少总数或 has_more", "BAD_PAGE")
    if state["expected_count"] is not None and state["expected_count"] != total:
        raise extract.SubtitleError("分页期间收藏数量变化；请换新目录重新列出，已有字幕保留", "LIST_CHANGED")
    rows = data.get("medias") or []
    if not isinstance(rows, list) or (data["has_more"] and not rows):
        raise extract.SubtitleError("B站返回空的中间页；保留进度，不宣称列表完整", "PARTIAL_LIST")
    additions = {}
    for row in rows:
        bvid = row.get("bvid") or row.get("bv_id") or ""
        regular = row.get("type") == 2 and bool(re.fullmatch(r"BV[0-9A-Za-z]{10}", bvid))
        key = bvid if regular else f"{row.get('id')}:{row.get('type')}"
        if key == "None:None":
            raise extract.SubtitleError("收藏条目缺少可追踪 ID", "BAD_PAGE")
        additions[key] = {
            "bvid": bvid, "aid": row.get("id"), "type": row.get("type"), "title": row.get("title", ""),
            "author": (row.get("upper") or {}).get("name", ""), "pubdate": row.get("pubtime"),
            "description": row.get("intro", ""), "duration": row.get("duration"),
            "source": f"https://www.bilibili.com/video/{bvid}/?p=1" if regular else "",
            "status": "unsupported" if not regular else "unavailable" if row.get("attr", 0) else "pending",
        }
    state["expected_count"] = total
    state["folder_title"] = info.get("title", "")
    for key, row in additions.items():
        state["entries"].setdefault(key, row)
    state["next_page"] += 1
    state["list_finished"] = not bool(data["has_more"])
    state["list_complete"] = state["list_finished"] and len(state["entries"]) == total


def output_path(out, bvid):
    if not re.fullmatch(r"BV[0-9A-Za-z]{10}", bvid):
        raise extract.SubtitleError("状态文件中的 BV 号无效", "BAD_STATE")
    return out / f"{bvid}.P1.md"


def verify_result(result, path, bvid, timestamps):
    if not path.is_file() or path.is_symlink():
        return False
    content = path.read_text(encoding="utf-8")
    return (result.get("ok") is True and isinstance(result.get("cid"), int) and result["cid"] > 0
            and result.get("bvid") == bvid and result.get("page") == 1
            and result.get("subtitle_count", 0) > 0
            and all(result.get(k) is True for k in ("count_matches", "timeline_valid"))
            and all(result.get(k) is False for k in ("secret_markers", "media_downloaded"))
            and result.get("timestamps_in_output") is timestamps
            and result.get("output_sha256") == hashlib.sha256(path.read_bytes()).hexdigest()
            and re.search(rf"^bvid: {re.escape(bvid)}$", content, re.M) is not None
            and re.search(r"^page: 1$", content, re.M) is not None
            and re.search(rf"^cid: {result.get('cid')}$", content, re.M) is not None
            and len(re.findall(r"^- ", content, re.M)) == result["subtitle_count"])


def import_results(state, out, paths):
    for source in paths:
        result = json.loads(Path(source).read_text(encoding="utf-8"))
        bvid = result.get("bvid", "")
        entry = state["entries"].get(bvid)
        if not entry or not verify_result(result, output_path(out, bvid), bvid, state["timestamps"]):
            raise extract.SubtitleError("浏览器补采报告与目标文件、BV、分P或校验结果不匹配", "BAD_RESULT")
        entry.update(status="ok", result=result)
        entry.pop("error", None)


def run_videos(state, out, limit, retry_failed):
    attempts = 0
    for bvid, entry in state["entries"].items():
        status = entry["status"]
        if status == "ok":
            if not verify_result(entry["result"], output_path(out, bvid), bvid, state["timestamps"]):
                entry.update(status="conflict", error="已完成文件缺失或哈希变化；不覆盖，检查后换新目录")
            continue
        if status != "pending" and not (retry_failed and status in ("error", "browser_required", "throttled")):
            continue
        if limit is not None and attempts >= limit:
            break
        target = output_path(out, bvid)
        if target.exists() or target.is_symlink():
            entry.update(status="conflict", error="目标文件已存在且没有匹配的成功记录；可用 --accept-result 核验")
            save_state(out / "batch-state.json", state)
            continue
        if attempts:
            time.sleep(1)
        args = [sys.executable, str(Path(__file__).with_name("extract.py")), entry["source"], "-o", str(target)]
        if state["timestamps"]:
            args.append("--timestamps")
        attempts += 1
        try:
            completed = subprocess.run(args, capture_output=True, text=True, timeout=240)
            text = completed.stdout.strip() or completed.stderr.strip()
            result = json.loads(text)
            code = result.get("code")
            if completed.returncode == 0 and verify_result(result, target, bvid, state["timestamps"]):
                entry.update(status="ok", result=result)
                entry.pop("error", None)
            else:
                status = ("throttled" if code == "THROTTLED" else "browser_required"
                          if code == "NOT_LOGGED_IN" or result.get("status") == "browser_required" else "error")
                entry.update(status=status, error=result.get("reason") or result.get("error") or "产物验证未通过")
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            entry.update(status="error", error="单视频超时或脚本没有返回结构化结果")
        save_state(out / "batch-state.json", state)
        print(json.dumps({"bvid": bvid, "status": entry["status"]}, ensure_ascii=False), file=sys.stderr, flush=True)
        if entry["status"] == "throttled":
            return "THROTTLED"
    return None


def summary(state, stopped=None):
    counts = dict(Counter(entry["status"] for entry in state["entries"].values()))
    complete = state["list_complete"] and counts.get("ok", 0) == state["expected_count"]
    return {"ok": complete, "skill_version": extract.VERSION, "folder_id": state["folder_id"],
            "list_complete": state["list_complete"], "listed": len(state["entries"]),
            "expected_count": state["expected_count"], "next_page": state["next_page"],
            "counts": counts, "stopped": stopped, "media_downloaded": False}


def main():
    parser = argparse.ArgumentParser(description="批量保存 B站收藏夹的字幕；只读、串行、断点续跑，默认每视频 P1")
    parser.add_argument("source", help="收藏夹 ID 或含 fid= 的链接")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--list-only", action="store_true", help="只列收藏，不抓字幕")
    parser.add_argument("--max-pages", type=int, help="本次最多新读取几页收藏；默认直到列表末尾")
    parser.add_argument("--limit", type=int, help="本次最多尝试几个视频；默认所有待采集条目")
    parser.add_argument("--page-json", nargs="+", default=[], help="导入浏览器读取的页；本次不再匿名读其他页")
    parser.add_argument("--accept-result", nargs="+", default=[], help="导入补采成功的 extract.py stdout JSON")
    parser.add_argument("--retry-failed", action="store_true", help="重试失败、待浏览器和上次限流条目，每项至多一次")
    parser.add_argument("--timestamps", action="store_true")
    args = parser.parse_args()
    if any(value is not None and value < 1 for value in (args.max_pages, args.limit)):
        parser.error("--max-pages 和 --limit 必须为正整数")
    fid = folder_id(args.source)
    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    state_path = out / "batch-state.json"
    lock = out / ".batch.lock"
    try:
        handle = lock.open("x")
    except FileExistsError:
        raise extract.SubtitleError("该目录存在批量任务锁；先确认没有任务运行，异常退出的锁可手动移除", "LOCKED") from None
    try:
        with handle:
            handle.write(str(os.getpid()))
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else new_state(fid, args.timestamps)
        if state.get("schema") != 1 or state.get("folder_id") != fid or state.get("timestamps") != args.timestamps:
            raise extract.SubtitleError("输出目录的收藏夹或时间戳选项不同；请使用另一个目录", "BAD_STATE")
        stopped = None
        state.pop("last_error", None)
        try:
            import_results(state, out, args.accept_result)
            if args.page_json:
                for file in args.page_json:
                    if state["list_finished"]:
                        raise extract.SubtitleError("列表已读到末页，不能继续追加页面", "BAD_PAGE")
                    add_page(state, json.loads(Path(file).read_text(encoding="utf-8")))
                    save_state(state_path, state)
            elif not args.accept_result:
                pages = 0
                while not state["list_finished"] and (args.max_pages is None or pages < args.max_pages):
                    if pages:
                        time.sleep(1)
                    page = state["next_page"]
                    data = extract.api_json("/x/v3/fav/resource/list", {
                        "media_id": fid, "pn": page, "ps": 40, "platform": "web"})
                    add_page(state, {"folder_id": fid, "page": page, "payload": {"code": 0, "data": data}})
                    save_state(state_path, state)
                    pages += 1
            if not args.list_only:
                time.sleep(1)
                stopped = run_videos(state, out, args.limit, args.retry_failed)
        except (extract.SubtitleError, urllib.error.URLError) as error:
            stopped = getattr(error, "code", "NETWORK")
            state["last_error"] = {"code": stopped, "error": extract.redact_error(error)}
        save_state(state_path, state)
        report = summary(state, stopped)
        if args.list_only:
            report["ok"] = state["list_complete"] and stopped is None
            report["scope"] = "favorites_list"
        if stopped:
            report["error"] = state.get("last_error", {}).get("error", "B站限流，稍后再续跑")
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report["ok"] else 3
    finally:
        lock.unlink()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (extract.SubtitleError, OSError, ValueError) as error:
        print(json.dumps({"ok": False, "code": getattr(error, "code", "BATCH_ERROR"),
                          "error": extract.redact_error(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2) from error
