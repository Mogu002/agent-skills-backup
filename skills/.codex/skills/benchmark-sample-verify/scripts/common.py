"""Common helpers for benchmark-sample-verify scripts.

Keep this importable without side effects. All lark-cli calls use --as user.
"""
import json
import os
import re
import subprocess
import sys

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")


def run_lark(args):
    """Run a lark-cli command, return parsed JSON dict. Raises on non-ok."""
    cmd = ["lark-cli"] + args
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    out = proc.stdout or ""
    # lark-cli prints JSON on stdout; strip any PowerShell CLIXML noise just in case
    out = out.strip()
    if not out:
        raise RuntimeError(f"empty output from: {' '.join(cmd)}\nstderr={proc.stderr}")
    data = json.loads(out)
    if not data.get("ok", True):
        raise RuntimeError(f"lark-cli error: {json.dumps(data.get('error'), ensure_ascii=False)}")
    return data


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def cell_text(v):
    """Flatten a Base cell value to plain text."""
    if v is None:
        return ""
    if isinstance(v, list):
        parts = []
        for it in v:
            if isinstance(it, dict):
                parts.append(it.get("text") or it.get("name") or it.get("en_name") or "")
            else:
                parts.append(str(it))
        return "".join(p for p in parts if p)
    return str(v)


def parse_record_list(resp):
    """record-list / record-get response -> list of dicts {record_id, fields:{name:value}}.

    Response shape: data.data is a 2D array aligned with data.field_id_list and
    data.fields (names); data.record_id_list holds record ids.
    """
    inner = resp["data"]
    rows = inner["data"]
    rids = inner["record_id_list"]
    names = inner.get("fields") or inner["field_id_list"]
    out = []
    for i, row in enumerate(rows):
        fields = {names[j]: row[j] for j in range(len(names))}
        out.append({"record_id": rids[i], "fields": fields})
    return out, inner


def extract_base_tokens(markdown_links):
    """From a text like '[name](https://.../base/TOKEN)\n...' pull base tokens in order."""
    return re.findall(r"/base/([A-Za-z0-9]+)", markdown_links or "")
