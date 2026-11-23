---
name: lark-base-record-reader
description: Read and extract authenticated Feishu/Lark Base shared-record URLs whose path starts with /record/. Use when a user provides a record share link and wants its fields, text, or embedded links. Do not use for ordinary Base URLs that already expose app, table, and record IDs.
---

# Lark Base Record Reader

Use `scripts/read_record.py` to render the shared record with Scrapling and the current user's logged-in Chrome cookies.

## Boundaries

- A `/record/<share-token>` token is not a Minutes `minute_token` and is not accepted by `lark-cli minutes`.
- `lark-cli base` is preferable only when `app_token`, `table_id`, and `record_id` are already known. It cannot bootstrap those IDs from this share URL.
- Do not use Ego or another browser automation system for this workflow unless the user explicitly asks to change tools.
- Chrome cookies are credentials. Proceed only when the user explicitly authorizes using their logged-in Chrome cookies. Never print, persist, summarize, or return cookie values.

## Run

The script requires Python 3.10+, `scrapling[fetchers]`, `browser-cookie3`, and a Playwright Chromium installation. Reuse an environment that already has them. If they are missing, ask before downloading dependencies, then install only:

```bash
python3 -m venv work/lark-base-record-reader-venv
work/lark-base-record-reader-venv/bin/pip install "scrapling[fetchers]>=0.4.15" "browser-cookie3>=0.20.1"
work/lark-base-record-reader-venv/bin/playwright install chromium
```

Run the helper with the user-provided URL and write results under the current task's `work/` directory:

```bash
work/lark-base-record-reader-venv/bin/python <skill-dir>/scripts/read_record.py \
  "https://example.larkoffice.com/record/SHARE_TOKEN" \
  --output work/lark-base-record.json
```

Use `--cookie-db <path>` only when the user names a non-default Chrome profile. Do not inspect or guess among profiles without their direction.

## Interpret Results

- `ok: true`: the final URL remains a `/record/` page and rendered record content was captured. Read `text` and `links` to answer the user's request.
- `error: authentication_required`: cookies were absent, expired, or did not cover the tenant. Ask the user to sign in to the record in Chrome, then rerun once.
- `error: no_lark_cookies`: no relevant Chrome cookies were found. Stop and ask which Chrome profile to use.
- Do not retry repeated authentication failures or fall back to extracting Chrome's full cookie store.

Delete temporary result files after answering unless the user requested a saved artifact.
