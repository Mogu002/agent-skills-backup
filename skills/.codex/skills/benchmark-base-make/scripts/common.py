"""Shared local JSON, field normalization, and read-only CLI helpers."""
import json, os, pathlib, shutil, subprocess, tempfile
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo


def read_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def cli_prefix(raw=None):
    if raw:
        value = json.loads(raw)
        if not isinstance(value, list) or not value or not all(isinstance(x, str) and x for x in value):
            raise ValueError("--cli-prefix-json must be a nonempty string array")
        return value
    command = shutil.which("lark-cli")
    if not command:
        raise ValueError("lark-cli unavailable; supply --cli-prefix-json from your configured runtime")
    path = pathlib.Path(command)
    if os.name == "nt" and path.suffix.lower() in {".cmd", ".ps1", ".bat"}:
        runner = path.parent / "node_modules" / "@larksuite" / "cli" / "scripts" / "run.js"
        node = shutil.which("node")
        if runner.exists() and node:
            return [node, str(runner)]
        raise ValueError("Cannot resolve npm shim without shell; supply --cli-prefix-json")
    return [command]


class ReadCLI:
    ALLOWED = {"+field-list", "+record-list"}

    def __init__(self, prefix):
        self.prefix = prefix

    def call(self, args):
        if len(args) < 2 or args[0] != "base" or args[1] not in self.ALLOWED:
            raise ValueError("This helper permits only field-list and record-list")
        result = subprocess.run(self.prefix + args, shell=False, capture_output=True,
                                encoding="utf-8-sig", timeout=120)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "CLI read failed")
        body = json.loads(result.stdout)
        if body.get("ok") is not True:
            raise RuntimeError("CLI did not return a successful envelope")
        return body["data"]


def field_index(snapshot):
    by_id = {f["id"]: f for f in snapshot["fields"]}
    if len(by_id) != len(snapshot["fields"]):
        raise ValueError("Duplicate field IDs")
    names = {}
    for f in snapshot["fields"]:
        names.setdefault(f["name"], []).append(f["id"])
    def resolve(key):
        if key in by_id:
            return key
        ids = names.get(key, [])
        if len(ids) != 1:
            raise ValueError("Missing or ambiguous field: " + key)
        return ids[0]
    return by_id, resolve


def normalize(value, field, timezone=None):
    if value is None:
        return None
    kind = field["type"]
    if kind == "select":
        vals = value if isinstance(value, list) else [value]
        if not all(isinstance(x, str) for x in vals):
            raise ValueError("Selection contains non-string values")
        if not field.get("multiple"):
            if len(vals) != 1:
                raise ValueError("Single selection requires exactly one value")
            return vals[0]
        return sorted(vals)
    if kind == "datetime":
        if not isinstance(value, str):
            raise ValueError("Datetime must be an explicit string")
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if moment.tzinfo is None:
            if not timezone:
                raise ValueError("Naive datetime requires an observed table timezone")
            moment = moment.replace(tzinfo=ZoneInfo(timezone))
        return moment.timestamp()
    if kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Number must be a JSON number")
        return Decimal(str(value))
    if kind == "checkbox":
        if not isinstance(value, bool):
            raise ValueError("Checkbox must be boolean")
    if kind in {"user", "group_chat", "link"}:
        if not isinstance(value, list) or not all(isinstance(x, dict) and isinstance(x.get("id"), str) for x in value):
            raise ValueError("ID-based values require arrays of {id: ...}")
        return sorted(x["id"] for x in value)
    return value
