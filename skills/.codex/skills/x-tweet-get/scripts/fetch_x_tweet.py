#!/usr/bin/env python3
"""Fetch raw public X post JSON through certificate-independent fallbacks."""

import argparse
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


def parse_post_id(value: str) -> str:
    value = value.strip().replace("\\_", "_")
    if value.isdigit():
        return value

    match = re.search(r"https?://[^\s>)\]]+", value)
    candidate = match.group(0) if match else value
    if "://" not in candidate:
        candidate = "https://" + candidate

    parsed = urlsplit(candidate.rstrip(".,;"))
    host = (parsed.hostname or "").lower()
    for prefix in ("www.", "mobile."):
        if host.startswith(prefix):
            host = host[len(prefix) :]
    if host not in {"x.com", "twitter.com"}:
        raise ValueError("expected an x.com/twitter.com status URL or numeric post ID")

    parts = [part for part in parsed.path.split("/") if part]
    try:
        post_id = parts[parts.index("status") + 1]
    except (ValueError, IndexError) as exc:
        raise ValueError("URL does not contain /status/<POST_ID>") from exc
    if not post_id.isdigit():
        raise ValueError("post ID must be numeric")
    return post_id


def fetch_json(url: str, timeout: float) -> dict:
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "x-tweet-get/1.0"},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def returned_id(source: str, payload: dict) -> str:
    if source == "fxtwitter":
        return str((payload.get("tweet") or {}).get("id") or "")
    return str(payload.get("id_str") or "")


def get_post(post_id: str, lang: str, timeout: float) -> dict:
    endpoints = [
        ("fxtwitter", f"https://api.fxtwitter.com/status/{quote(post_id)}"),
        (
            "syndication",
            "https://cdn.syndication.twimg.com/tweet-result?"
            + urlencode({"id": post_id, "lang": lang, "token": "a"}),
        ),
    ]
    errors = []
    for source, url in endpoints:
        try:
            payload = fetch_json(url, timeout)
            actual_id = returned_id(source, payload)
            if actual_id != post_id:
                raise ValueError(f"returned post ID {actual_id or '<missing>'}")
            return {
                "source": source,
                "source_url": url,
                "requested_id": post_id,
                "visual_url": (
                    "https://platform.twitter.com/embed/Tweet.html?"
                    + urlencode({"id": post_id, "dnt": "true"})
                ),
                "data": payload,
            }
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{source}: {exc}")
    raise RuntimeError("all public JSON sources failed (" + "; ".join(errors) + ")")


def self_test() -> None:
    assert parse_post_id("12345") == "12345"
    assert parse_post_id("https://x.com/user_name/status/12345?s=46") == "12345"
    assert parse_post_id("[post](https://twitter.com/user/status/12345)") == "12345"
    assert returned_id("fxtwitter", {"tweet": {"id": "12345"}}) == "12345"
    assert returned_id("syndication", {"id_str": "12345"}) == "12345"
    try:
        parse_post_id("https://example.com/user/status/12345")
    except ValueError:
        pass
    else:
        raise AssertionError("unexpectedly accepted a non-X host")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a public X post as raw JSON with a second-domain fallback."
    )
    parser.add_argument("post", nargs="?", help="X/Twitter status URL or numeric post ID")
    parser.add_argument("--lang", default="en", help="syndication locale (default: en)")
    parser.add_argument("--timeout", type=float, default=20, help="seconds per request")
    parser.add_argument("--self-test", action="store_true", help="run offline checks")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("ok")
        return 0
    if not args.post:
        parser.error("post is required unless --self-test is used")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    try:
        post_id = parse_post_id(args.post)
        result = get_post(post_id, args.lang, args.timeout)
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
