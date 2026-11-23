#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import browser_cookie3
from scrapling.fetchers import DynamicFetcher


LARK_DOMAINS = ("feishu.cn", "larkoffice.com", "larksuite.com")


def fail(error, output=None):
    result = {"ok": False, "error": error}
    if output:
        Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 1


parser = argparse.ArgumentParser()
parser.add_argument("url")
parser.add_argument("--output")
parser.add_argument("--cookie-db")
parser.add_argument("--timeout", type=int, default=60_000)
args = parser.parse_args()

target = urlparse(args.url)
if target.scheme != "https" or not target.path.startswith("/record/") or not target.hostname or not target.hostname.endswith(LARK_DOMAINS):
    sys.exit(fail("invalid_record_url", args.output))

try:
    jar = browser_cookie3.chrome(cookie_file=args.cookie_db) if args.cookie_db else browser_cookie3.chrome()
except Exception:
    sys.exit(fail("cookie_read_failed", args.output))

cookies = [
    {
        "name": cookie.name,
        "value": cookie.value,
        "domain": cookie.domain,
        "path": cookie.path,
        "secure": bool(cookie.secure),
    }
    for cookie in jar
    if cookie.domain.endswith(LARK_DOMAINS) and not cookie.is_expired()
]
if not cookies:
    sys.exit(fail("no_lark_cookies", args.output))


def wait_for_record(browser_page):
    browser_page.wait_for_function(
        "location.pathname.startsWith('/record/') && ['详情', '詳細'].some(label => document.body.innerText.includes(label))",
        timeout=args.timeout,
    )


page = DynamicFetcher.fetch(
    args.url,
    cookies=cookies,
    google_search=False,
    page_action=wait_for_record,
    timeout=args.timeout,
    retries=1,
)
text = str(page.get_all_text(separator="\n", strip=True))
final = urlparse(page.url)
ok = final.hostname == target.hostname and final.path.startswith("/record/") and any(
    label in text for label in ("详情", "詳細")
)
links = list(dict.fromkeys(
    page.urljoin(str(href))
    for href in page.css("a::attr(href)").getall()
    if str(href).startswith(("http://", "https://", "/"))
))
result = {
    "ok": ok,
    "error": None if ok else "authentication_required",
    "status": page.status,
    "final_url": page.url,
    "title": str(page.css("title::text").get() or ""),
    "text": text,
    "links": links,
}
payload = json.dumps(result, ensure_ascii=False, indent=2)
if args.output:
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload)
else:
    print(payload)
sys.exit(not ok)
