#!/usr/bin/env python3
"""Read one public Xiaohongshu post and print its text and media URLs as JSON."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ALLOWED_DOMAINS = (
    "xiaohongshu.com",
    "xhslink.com",
    "xhslink.cn",
    "rednote.com",
)
MAX_HTML_BYTES = 16 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class ReadError(RuntimeError):
    pass


def validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not any(
        host == domain or host.endswith(f".{domain}") for domain in ALLOWED_DOMAINS
    ):
        raise ReadError("expected a Xiaohongshu or RedNote post URL")


class AllowedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def load_cookies(path: str) -> http.cookiejar.CookieJar:
    cookie_path = Path(path).expanduser()
    try:
        raw = cookie_path.read_bytes()
    except OSError as exc:
        raise ReadError(f"could not read cookie file: {exc.strerror}") from None
    if len(raw) > 1024 * 1024:
        raise ReadError("cookie file is unexpectedly large")
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ReadError("cookie file is not valid JSON") from None
    entries = data.get("cookies") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise ReadError("cookie file must contain a JSON cookie array")

    jar = http.cookiejar.CookieJar()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name, value = entry.get("name"), entry.get("value")
        domain = str(entry.get("domain") or ".xiaohongshu.com").lower()
        cookie_host = domain.lstrip(".")
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        if not any(
            cookie_host == allowed or cookie_host.endswith(f".{allowed}")
            for allowed in ("xiaohongshu.com", "rednote.com")
        ):
            continue
        jar.set_cookie(
            http.cookiejar.Cookie(
                version=0,
                name=name,
                value=value,
                port=None,
                port_specified=False,
                domain=domain,
                domain_specified=True,
                domain_initial_dot=domain.startswith("."),
                path=str(entry.get("path") or "/"),
                path_specified=True,
                secure=bool(entry.get("secure", True)),
                expires=None,
                discard=True,
                comment=None,
                comment_url=None,
                rest={},
                rfc2109=False,
            )
        )
    if not list(jar):
        raise ReadError("cookie file contains no Xiaohongshu or RedNote cookies")
    return jar


def fetch_page(url: str, cookie_file: str | None = None) -> tuple[str, str]:
    validate_url(url)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
            "User-Agent": USER_AGENT,
        },
    )
    handlers: list[Any] = [AllowedRedirects()]
    if cookie_file:
        handlers.append(urllib.request.HTTPCookieProcessor(load_cookies(cookie_file)))
    try:
        response = urllib.request.build_opener(*handlers).open(request, timeout=20)
    except urllib.error.HTTPError as exc:
        raise ReadError(f"page request failed with HTTP {exc.code}") from None
    except urllib.error.URLError as exc:
        raise ReadError(f"page request failed: {exc.reason}") from None

    with response:
        final_url = response.geturl()
        validate_url(final_url)
        body = response.read(MAX_HTML_BYTES + 1)
        if len(body) > MAX_HTML_BYTES:
            raise ReadError("page is unexpectedly large")
        charset = response.headers.get_content_charset() or "utf-8"
        return final_url, body.decode(charset, errors="replace")


def extract_object(source: str, marker: str = "window.__INITIAL_STATE__") -> str:
    marker_at = source.find(marker)
    if marker_at < 0:
        raise ReadError("post data was not found; the page may require login or verification")
    equals_at = source.find("=", marker_at + len(marker))
    start = source.find("{", equals_at + 1)
    if equals_at < 0 or start < 0:
        raise ReadError("post data is malformed")

    depth = 0
    quote = ""
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise ReadError("post data is incomplete")


def replace_undefined(source: str) -> str:
    result: list[str] = []
    quote = ""
    escaped = False
    index = 0
    while index < len(source):
        char = source[index]
        if quote:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            result.append(char)
            index += 1
            continue
        if source.startswith("undefined", index):
            before = source[index - 1] if index else ""
            after_at = index + len("undefined")
            after = source[after_at] if after_at < len(source) else ""
            if not (before.isalnum() or before in "_$") and not (
                after.isalnum() or after in "_$"
            ):
                result.append("null")
                index = after_at
                continue
        result.append(char)
        index += 1
    return "".join(result)


def load_initial_state(html: str) -> dict[str, Any]:
    try:
        state = json.loads(replace_undefined(extract_object(html)))
    except json.JSONDecodeError as exc:
        raise ReadError(f"post data is not valid JSON: {exc.msg}") from None
    if not isinstance(state, dict):
        raise ReadError("post data has an unexpected shape")
    return state


def note_id_from_url(url: str) -> str:
    match = re.search(
        r"/(?:explore|discovery/item)/([0-9a-f]+)|/user/profile/[^/]+/([0-9a-f]+)",
        url,
        re.I,
    )
    return next((group for group in match.groups() if group), "") if match else ""


def reject_error_page(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.path.rstrip("/") == "/login":
        raise ReadError("the post requires login")
    if parsed.path.rstrip("/") == "/404":
        message = (urllib.parse.parse_qs(parsed.query).get("error_msg") or [""])[0]
        raise ReadError(message or "the post is unavailable")


def select_note(state: dict[str, Any], url: str) -> dict[str, Any]:
    detail_map = ((state.get("note") or {}).get("noteDetailMap") or {})
    if not isinstance(detail_map, dict):
        raise ReadError("the page does not contain a readable post")

    wanted = note_id_from_url(url)
    candidates: list[dict[str, Any]] = []
    for key, value in detail_map.items():
        note = value.get("note") if isinstance(value, dict) else None
        if not isinstance(note, dict):
            continue
        candidates.append(note)
        if key == wanted or str(note.get("noteId") or "") == wanted:
            return note
    if len(candidates) == 1:
        return candidates[0]
    raise ReadError("the requested post was not found in the page data")


def unique_urls(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.startswith(("http://", "https://")):
            continue
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def image_urls(note: dict[str, Any]) -> list[str]:
    urls: list[Any] = []
    for image in note.get("imageList") or []:
        if not isinstance(image, dict):
            continue
        urls.append(image.get("urlDefault") or image.get("urlPre") or image.get("url"))
        for info in image.get("infoList") or []:
            if isinstance(info, dict):
                urls.append(info.get("url"))
    return unique_urls(urls)


def video_urls(note: dict[str, Any]) -> list[str]:
    stream = (((note.get("video") or {}).get("media") or {}).get("stream") or {})
    choices: list[tuple[tuple[int, int, int], list[Any]]] = []
    for entries in stream.values() if isinstance(stream, dict) else []:
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict):
                continue
            score = (
                int(entry.get("width") or 0) * int(entry.get("height") or 0),
                int(entry.get("avgBitrate") or 0),
                int(entry.get("size") or 0),
            )
            choices.append(
                (score, [entry.get("masterUrl"), *(entry.get("backupUrls") or [])])
            )
    return unique_urls(
        [
            url
            for _, urls in sorted(choices, key=lambda item: item[0], reverse=True)
            for url in urls
        ]
    )


def post_data(note: dict[str, Any], final_url: str) -> dict[str, Any]:
    note_id = str(note.get("noteId") or note_id_from_url(final_url))
    if not note_id:
        raise ReadError("the post has no note ID")
    user = note.get("user") if isinstance(note.get("user"), dict) else {}
    host = (urllib.parse.urlparse(final_url).hostname or "").lower()
    domain = "www.rednote.com" if host.endswith("rednote.com") else "www.xiaohongshu.com"
    return {
        "source_url": f"https://{domain}/explore/{note_id}",
        "note_id": note_id,
        "title": str(note.get("title") or ""),
        "content": str(note.get("desc") or ""),
        "type": str(note.get("type") or ""),
        "author": {
            "id": str(user.get("userId") or ""),
            "name": str(user.get("nickname") or user.get("nickName") or ""),
        },
        "image_urls": image_urls(note),
        "video_urls": video_urls(note),
    }


def read_post(url: str, cookie_file: str | None = None) -> dict[str, Any]:
    final_url, html = fetch_page(url, cookie_file)
    reject_error_page(final_url)
    return post_data(select_note(load_initial_state(html), final_url), final_url)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="public Xiaohongshu or RedNote post URL")
    parser.add_argument("--cookies", help="optional local JSON cookie export")
    args = parser.parse_args()
    try:
        result = read_post(args.url, args.cookies)
    except ReadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
