#!/usr/bin/env python3
"""Fetch Bilibili native subtitles and render Markdown."""

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"
API = "https://api.bilibili.com"
VERSION = "0.4.0"
MEDIA_SUFFIXES = {".mp4", ".m4s", ".mp3", ".wav", ".mkv", ".webm"}


class SubtitleError(RuntimeError):
    def __init__(self, message: str, code: str = "EXTRACTION_ERROR"):
        super().__init__(message)
        self.code = code


@dataclass
class Field:
    number: int
    wire: int
    value: Optional[int] = None
    data: Optional[bytes] = None


def request_bytes(url: str, referer: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code in (412, 429):
            raise SubtitleError("B站限流，停止当前任务，稍后再续跑", "THROTTLED") from error
        raise


def api_json(path: str, params: dict, referer: str = "https://www.bilibili.com/") -> dict:
    raw = request_bytes(f"{API}{path}?{urllib.parse.urlencode(params)}", referer)
    payload = json.loads(raw)
    if payload.get("code") != 0:
        code = payload.get("code")
        if code in (-352, -412, -509):
            raise SubtitleError("B站限流，停止当前任务，稍后再续跑", "THROTTLED")
        if code == -101:
            raise SubtitleError("此接口需要浏览器登录态", "NOT_LOGGED_IN")
        raise SubtitleError(f"B站接口失败: {payload.get('message', code)}", f"BILI_{code}")
    return payload.get("data") or {}


def bvid_from(source: str) -> str:
    match = re.search(r"BV[0-9A-Za-z]{10}", source, re.IGNORECASE)
    if not match:
        raise SubtitleError("无法从输入识别 BV 号")
    return match.group(0)


def page_from(source: str, explicit: Optional[int]) -> int:
    if explicit is not None:
        return explicit
    try:
        value = urllib.parse.parse_qs(urllib.parse.urlsplit(source).query).get("p", ["1"])[0]
        return int(value)
    except (TypeError, ValueError):
        raise SubtitleError("分P参数 p 必须是正整数") from None


def video_info(source: str, page: Optional[int]) -> dict:
    bvid = bvid_from(source)
    selected_page = page_from(source, page)
    if selected_page < 1:
        raise SubtitleError("分P编号必须从 1 开始")
    data = api_json("/x/web-interface/view", {"bvid": bvid})
    pages = data.get("pages") or []
    if pages and selected_page > len(pages):
        raise SubtitleError(f"分P编号超出范围，共 {len(pages)} P")
    selected = pages[selected_page - 1] if pages else data
    cid = selected.get("cid") or data.get("cid")
    if not cid:
        raise SubtitleError("视频元数据缺少 CID")
    title = data.get("title") or bvid
    if len(pages) > 1 and selected.get("part"):
        title = f"{title} - P{selected_page} {selected['part']}"
    return {
        "bvid": data.get("bvid") or bvid,
        "aid": data.get("aid"),
        "cid": cid,
        "title": title,
        "duration": selected.get("duration") or data.get("duration"),
        "page": selected_page,
    }


def read_varint(payload: bytes, offset: int) -> tuple[int, int]:
    value = shift = 0
    while offset < len(payload):
        byte = payload[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
        if shift > 63:
            raise SubtitleError("Protobuf varint 过长")
    raise SubtitleError("Protobuf varint 不完整")


def decode_message(payload: bytes) -> list[Field]:
    fields, offset = [], 0
    while offset < len(payload):
        key, offset = read_varint(payload, offset)
        number, wire = key >> 3, key & 7
        if number < 1:
            raise SubtitleError("Protobuf 字段编号无效")
        if wire == 0:
            value, offset = read_varint(payload, offset)
            fields.append(Field(number, wire, value=value))
        elif wire in (1, 5):
            size = 8 if wire == 1 else 4
            end = offset + size
            if end > len(payload):
                raise SubtitleError("Protobuf fixed 字段不完整")
            fields.append(Field(number, wire, data=payload[offset:end]))
            offset = end
        elif wire == 2:
            size, offset = read_varint(payload, offset)
            end = offset + size
            if end > len(payload):
                raise SubtitleError("Protobuf bytes 字段不完整")
            fields.append(Field(number, wire, data=payload[offset:end]))
            offset = end
        else:
            raise SubtitleError(f"不支持的 Protobuf wire type: {wire}")
    return fields


def field_bytes(fields: list[Field], number: int) -> Optional[bytes]:
    return next((field.data for field in fields if field.number == number and field.wire == 2), None)


def field_text(fields: list[Field], number: int) -> Optional[str]:
    value = field_bytes(fields, number)
    return value.decode("utf-8") if value is not None else None


def field_int(fields: list[Field], number: int) -> Optional[int]:
    return next((field.value for field in fields if field.number == number and field.wire == 0), None)


def protobuf_tracks(payload: bytes) -> list[dict]:
    top = decode_message(payload)
    data = field_bytes(top, 1)
    if not data:
        return []
    tracks = []
    for field in decode_message(data):
        if field.number != 3 or field.wire != 2 or not field.data:
            continue
        item = decode_message(field.data)
        language, url = field_text(item, 3), field_text(item, 5)
        if language and url:
            tracks.append({
                "id": field_int(item, 1),
                "id_str": field_text(item, 2),
                "lan": language,
                "lan_doc": field_text(item, 4),
                "subtitle_url": url,
            })
    return tracks


def anonymous_tracks(info: dict) -> tuple[list[dict], str, int]:
    referer = f"https://www.bilibili.com/video/{info['bvid']}/"
    try:
        legacy = api_json("/x/player/wbi/v2", {"bvid": info["bvid"], "cid": info["cid"]}, referer)
    except SubtitleError as error:
        if error.code in ("THROTTLED", "NOT_LOGGED_IN"):
            raise
        legacy = {}
    tracks = legacy.get("subtitle", {}).get("subtitles", [])
    if tracks:
        return tracks, "legacy_json", 0
    params = {
        "oid": info["cid"], "pid": info["aid"], "context_ext": '{"video_type":1}',
        "type": 1, "cur_production_type": 0, "preferred_language": "ai-zh", "playlist_switch": 0,
    }
    url = f"{API}/x/v2/subtitle/web/view?{urllib.parse.urlencode(params)}"
    for attempt in range(4):
        tracks = protobuf_tracks(request_bytes(url, referer))
        if tracks:
            return tracks, "protobuf", attempt + 1
        if attempt < 3:
            time.sleep(0.3)
    return [], "protobuf", 4


def choose_track(tracks: list[dict], language: Optional[str]) -> dict:
    if not tracks:
        raise SubtitleError("没有原生字幕轨")
    if language:
        track = next((item for item in tracks if item.get("lan") == language), None)
        if not track:
            available = ", ".join(str(item.get("lan")) for item in tracks)
            raise SubtitleError(f"没有请求的字幕语言 {language}；可用轨道: {available}")
        return track
    for preferred in ("ai-zh", "zh-CN", "zh-Hans", "zh"):
        track = next((item for item in tracks if item.get("lan") == preferred), None)
        if track:
            return track
    return tracks[0]


def resolve_subtitle_url(url: str) -> str:
    url = "https:" + url if url.startswith("//") else url
    parsed = urllib.parse.urlsplit(url)
    if parsed.hostname == "subtitle.bilibili.com":
        cipher = urllib.parse.unquote(parsed.path.lstrip("/"))
        # ponytail: current web-player fallback; prefer browser-captured final JSON if Bilibili changes it.
        keys = (
            ('nP](wOFRvU.+<fjS{jn-!$D|Dz&",zT`', '=CFxYRn{.y|uVyO$uh&sikph?N.ilF/`'),
            ('Bn"q~|albg@]Go~ACgyDvKnd+)_D}^&J?', "Cu~L!xs~f^&r@'vh=q]q{eeng*sEg^kp#J"),
        )
        for prefix, seed in keys:
            key = seed + "bilibili"
            plain = "".join(chr(ord(char) ^ ord(key[index % len(key)])) for index, char in enumerate(cipher))
            if plain.startswith(prefix):
                url = urllib.parse.urlunsplit(("https", "aisubtitle.hdslb.com", plain[len(prefix):], parsed.query, ""))
                break
        else:
            raise SubtitleError("未知的字幕地址混淆格式；请捕获播放器最终字幕 JSON")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or not (
        parsed.hostname.endswith(".hdslb.com") or parsed.hostname.endswith(".bilibili.com")
    ):
        raise SubtitleError("字幕地址不属于允许的 B站 HTTPS 域名")
    return url


def normalize_body(payload: dict) -> list[dict]:
    body = payload.get("body") or payload.get("subtitles") or []
    if not body:
        raise SubtitleError("字幕正文为空")
    result, previous = [], -1.0
    for index, item in enumerate(body, 1):
        try:
            start, end = float(item["from"]), float(item["to"])
        except (KeyError, TypeError, ValueError):
            raise SubtitleError(f"第 {index} 条字幕时间无效") from None
        if start < previous or end < start:
            raise SubtitleError(f"第 {index} 条字幕时间轴无效")
        result.append({"from": start, "to": end, "content": str(item.get("content", "")).strip()})
        previous = start
    return result


def stamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def render_markdown(
    info: dict,
    language: str,
    language_name: str,
    payload: dict,
    body: list[dict],
    timestamps: bool,
) -> str:
    ai = language.startswith("ai-") or str(payload.get("type", "")).lower() == "aisubtitle"
    source = "B站 AI 自动生成字幕" if ai else "B站原生字幕"
    frontmatter = [
        "---", f"title: {json.dumps(info['title'], ensure_ascii=False)}",
        f"source: https://www.bilibili.com/video/{info['bvid']}/", f"bvid: {info['bvid']}",
        f"aid: {info['aid']}", f"cid: {info['cid']}", f"page: {info['page']}",
        f"language: {language}", f"language_name: {json.dumps(language_name, ensure_ascii=False)}",
        f"subtitle_source: {json.dumps(source, ensure_ascii=False)}", f"segment_count: {len(body)}",
        f"video_duration_seconds: {info['duration']}", "---", "", f"# {info['title']}", "",
        f"> 以下内容来自{source}，未经人工校对。", "", "## 字幕", "",
    ]
    if timestamps:
        lines = [
            f"- [{stamp(item['from'])}–{stamp(item['to'])}] {item['content'].replace(chr(10), ' ')}"
            for item in body
        ]
    else:
        lines = [f"- {item['content'].replace(chr(10), ' ')}" for item in body]
    return "\n".join(frontmatter + lines) + "\n"


def render_json_subtitles(body: list[dict], timestamps: bool) -> list[dict]:
    if timestamps:
        return body
    return [{"content": item["content"]} for item in body]


def self_check() -> None:
    sample = bytes.fromhex("0a381a36087b12033132331a0561692d7a682206e4b8ade696872a1e2f2f61697375627469746c652e6864736c622e636f6d2f6578616d706c65")
    tracks = protobuf_tracks(sample)
    assert tracks[0]["lan"] == "ai-zh"
    assert tracks[0]["subtitle_url"] == "//aisubtitle.hdslb.com/example"
    assert bvid_from("https://www.bilibili.com/video/BV1234567890/?p=2") == "BV1234567890"
    assert stamp(3661.5) == "01:01:01.500"
    sample_info = {"title": "test", "bvid": "BV1234567890", "aid": 1, "cid": 2, "page": 1, "duration": 3}
    sample_body = [{"from": 1.0, "to": 2.0, "content": "字幕文本"}]
    plain = render_markdown(sample_info, "zh-CN", "中文", {}, sample_body, timestamps=False)
    timestamped = render_markdown(sample_info, "zh-CN", "中文", {}, sample_body, timestamps=True)
    assert "- 字幕文本" in plain and "[00:00:01.000" not in plain
    assert "- [00:00:01.000–00:00:02.000] 字幕文本" in timestamped
    assert render_json_subtitles(sample_body, timestamps=False) == [{"content": "字幕文本"}]
    assert render_json_subtitles(sample_body, timestamps=True) == sample_body
    original_api_json, original_request_bytes, original_sleep = api_json, request_bytes, time.sleep
    responses = iter((b"\n\x00", b"\n\x00", sample))
    try:
        globals()["api_json"] = lambda *args, **kwargs: {"subtitle": {"subtitles": []}}
        globals()["request_bytes"] = lambda *args, **kwargs: next(responses)
        time.sleep = lambda _: None
        retried, path, attempts = anonymous_tracks({"bvid": "BV1234567890", "cid": 1, "aid": 2})
        assert retried[0]["lan"] == "ai-zh"
        assert path == "protobuf" and attempts == 3
    finally:
        globals()["api_json"], globals()["request_bytes"], time.sleep = original_api_json, original_request_bytes, original_sleep
    print(json.dumps({"ok": True, "self_check": True}, ensure_ascii=False))


def redact_error(error: Exception) -> str:
    text = str(error)
    text = re.sub(r"(?i)auth_key=[^&\s'\"]+", "auth_key=<redacted>", text)
    return re.sub(r"https?://(?:subtitle\.bilibili\.com|aisubtitle\.hdslb\.com)/\S+", "<redacted-subtitle-url>", text)


def main() -> int:
    parser = argparse.ArgumentParser(description="B站原生字幕转 Markdown；默认不保留时间戳")
    parser.add_argument("source", nargs="?", help="B站视频 URL 或 BV 号")
    parser.add_argument("-o", "--output", help="Markdown 输出路径")
    parser.add_argument("--page", type=int, help="分P编号；默认读取 URL 的 p 参数或使用 1")
    parser.add_argument("--language", help="字幕语言，如 ai-zh；默认优先 AI 中文")
    parser.add_argument("--metadata-file", help="浏览器捕获的 /x/v2/subtitle/web/view 二进制响应")
    parser.add_argument("--subtitle-json", help="浏览器捕获的最终字幕 JSON")
    parser.add_argument("--json-output", help="可选：保存规范化字幕 JSON；默认同样不含时间戳")
    parser.add_argument("--timestamps", action="store_true", help="保留每条字幕的起止时间；仅在用户明确要求时使用")
    parser.add_argument("--overwrite", action="store_true", help="允许覆盖已存在的输出文件")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return 0
    if not args.source or not args.output:
        parser.error("source 和 --output 必填")

    output = Path(args.output).expanduser().resolve()
    json_output = Path(args.json_output).expanduser().resolve() if args.json_output else None
    existing = [path for path in (output, json_output) if path and path.exists()]
    if existing and not args.overwrite:
        raise SubtitleError("输出文件已存在；请改用新文件名，或在用户明确允许后传 --overwrite")

    info = video_info(args.source, args.page)
    referer = f"https://www.bilibili.com/video/{info['bvid']}/"
    track = {"lan": args.language or "unknown", "lan_doc": ""}
    acquisition_path, metadata_attempts = "browser_final_json", 0
    if args.subtitle_json:
        payload = json.loads(Path(args.subtitle_json).read_text(encoding="utf-8"))
        payload_language = str(payload.get("lang") or payload.get("language") or "unknown")
        if not args.language:
            track["lan"] = f"ai-{payload_language}" if str(payload.get("type", "")).lower() == "aisubtitle" else payload_language
    else:
        if args.metadata_file:
            tracks = protobuf_tracks(Path(args.metadata_file).read_bytes())
            acquisition_path = "browser_protobuf"
        else:
            tracks, acquisition_path, metadata_attempts = anonymous_tracks(info)
        if not tracks:
            print(json.dumps({
                "ok": False, "status": "browser_required", "bvid": info["bvid"], "cid": info["cid"],
                "metadata_attempts": metadata_attempts,
                "reason": "匿名字幕接口未返回字幕轨；请捕获 B站播放器原生字幕网络响应",
            }, ensure_ascii=False))
            return 3
        track = choose_track(tracks, args.language)
        url = resolve_subtitle_url(str(track.get("subtitle_url", "")))
        try:
            payload = json.loads(request_bytes(url, referer))
        except urllib.error.HTTPError as error:
            if error.code == 403:
                raise SubtitleError("字幕签名已过期；请重新获取一次字幕元数据") from error
            raise

    body = normalize_body(payload)
    language = str(track.get("lan") or payload.get("lang") or "unknown")
    output.parent.mkdir(parents=True, exist_ok=True)
    content = render_markdown(
        info, language, str(track.get("lan_doc") or ""), payload, body, timestamps=args.timestamps
    )
    secret_markers = bool(re.search(r"auth_key|SESSDATA|subtitle\.bilibili|aisubtitle\.hdslb", content, re.IGNORECASE))
    if secret_markers:
        raise SubtitleError("输出包含敏感字幕地址标记，已停止写入")
    output.write_text(content, encoding="utf-8")
    if json_output:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_subtitles = render_json_subtitles(body, timestamps=args.timestamps)
        json_output.write_text(
            json.dumps({**info, "language": language, "subtitles": json_subtitles}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    duration_delta = abs(body[-1]["to"] - float(info["duration"])) if info.get("duration") else None
    warning = None
    if duration_delta is not None and duration_delta > 30:
        warning = "最后字幕时间与视频时长相差超过 30 秒"
    print(json.dumps({
        "ok": True, "skill_version": VERSION, "output": str(output), "bvid": info["bvid"],
        "cid": info["cid"], "page": info["page"], "subtitle_count": len(body), "language": language,
        "acquisition_path": acquisition_path, "metadata_attempts": metadata_attempts,
        "first_timestamp": body[0]["from"], "last_timestamp": body[-1]["to"],
        "video_duration": info.get("duration"), "duration_delta": duration_delta,
        "count_matches": len(re.findall(r"^- ", content, re.MULTILINE)) == len(body),
        "timeline_valid": True, "secret_markers": secret_markers,
        "timestamps_in_output": args.timestamps,
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "warning": warning, "media_downloaded": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SubtitleError, urllib.error.URLError, json.JSONDecodeError, OSError) as error:
        print(json.dumps({"ok": False, "code": getattr(error, "code", "EXTRACTION_ERROR"),
                          "error": redact_error(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2) from error
