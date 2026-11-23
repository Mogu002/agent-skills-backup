#!/usr/bin/env python3
"""Deterministically compare a Lark Base field list with a textual schema."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class AuditInputError(ValueError):
    """Raised when an input cannot be audited without guessing."""


@dataclass(frozen=True)
class ExpectedField:
    name: str
    declared_type: str
    canonical_type: str | None
    options: tuple[str, ...]


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).casefold()


def normalize_type(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = normalized.replace("＆", "&")
    return re.sub(r"[\s_-]+", "", normalized)


TYPE_ALIASES = {
    normalize_type(alias): canonical
    for canonical, aliases in {
        "text/plain": ("文本", "text", "plain text"),
        "text/phone": ("电话号码", "电话", "phone", "phone number"),
        "text/email": ("邮箱", "email", "e-mail"),
        "text/barcode": ("条码", "barcode"),
        "text/url": ("超链接", "链接", "url", "hyperlink"),
        "number/plain": ("数字", "number"),
        "number/currency": ("货币", "currency"),
        "number/progress": ("进度", "progress"),
        "number/rating": (
            "评分",
            "评分&nps",
            "评分 & nps",
            "rating",
            "nps",
            "rating&nps",
            "rating & nps",
        ),
        "select/single": ("单选", "single select", "single-select"),
        "select/multiple": ("多选", "multi select", "multiple select", "multi-select"),
        "datetime": ("日期", "日期时间", "date", "datetime", "date time"),
        "user": ("人员", "用户", "person", "people", "user"),
        "group_chat": ("群组", "群聊", "group", "group chat"),
        "location": ("地理位置", "位置", "location"),
        "checkbox": ("复选框", "checkbox"),
        "link/one_way": ("单向关联", "one way relation", "one-way relation", "one way link"),
        "link/two_way": ("双向关联", "two way relation", "two-way relation", "two way link"),
        "attachment": ("附件", "attachment"),
        "formula": ("公式", "formula"),
        "lookup": ("查找引用", "lookup"),
        "auto_number": ("自动编号", "auto number"),
        "created_at": ("创建时间", "created time", "created at"),
        "updated_at": ("修改时间", "更新时间", "updated time", "updated at"),
        "created_by": ("创建人", "created by"),
        "updated_by": ("修改人", "updated by"),
    }.items()
    for alias in aliases
}


def split_declared_type(value: str) -> tuple[str, tuple[str, ...]]:
    parts = re.split(r"[:：]", value, maxsplit=1)
    declared_type = parts[0].strip()
    if len(parts) == 1:
        return declared_type, ()
    options = tuple(
        option.strip()
        for option in re.split(r"[/／、,，]", parts[1])
        if option.strip()
    )
    return declared_type, options


def parse_requirements(text: str) -> list[ExpectedField]:
    fields: list[ExpectedField] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = re.sub(r"^\s*(?:\d+\s*[.．、)]|[-*•])\s*", "", raw_line).strip()
        match = re.match(r"^(?P<name>.+)[（(](?P<type>[^()（）]+)[）)]\s*$", line)
        if not match:
            continue
        name = match.group("name").strip()
        declared_type, options = split_declared_type(match.group("type"))
        key = normalize_name(name)
        if key in seen:
            raise AuditInputError(f"duplicate requirement field: {name}")
        seen.add(key)
        fields.append(
            ExpectedField(
                name=name,
                declared_type=declared_type,
                canonical_type=TYPE_ALIASES.get(normalize_type(declared_type)),
                options=options,
            )
        )
    if not fields:
        raise AuditInputError("no requirement fields were parsed")
    return fields


def read_json(path: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AuditInputError(f"cannot read JSON from {path}: {error}") from error


def unwrap_success(payload: Any) -> Any:
    if isinstance(payload, dict) and payload.get("ok") is False:
        error = payload.get("error") or payload.get("message") or "unknown Lark CLI error"
        raise AuditInputError(f"Lark CLI returned an error: {error}")
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def extract_actual_fields(payload: Any) -> list[dict[str, Any]]:
    data = unwrap_success(payload)
    if isinstance(data, dict) and isinstance(data.get("fields"), list):
        fields = data["fields"]
    elif isinstance(data, list):
        fields = data
    else:
        raise AuditInputError("actual schema JSON does not contain a fields array")
    for index, field in enumerate(fields):
        if not isinstance(field, dict) or not isinstance(field.get("name"), str):
            raise AuditInputError(f"actual field at index {index} has no string name")
        if not isinstance(field.get("type"), str):
            raise AuditInputError(f"actual field {field['name']} has no string type")
    return fields


def cell_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(cell_text(item) for item in value)
    if isinstance(value, dict):
        for key in ("text", "value", "link", "url"):
            if key in value:
                return cell_text(value[key])
    if value is None:
        return ""
    return str(value)


def extract_source_inputs(
    payload: Any,
    target_field: str,
    requirements_field: str,
    record_index: int = 0,
) -> dict[str, Any]:
    data = unwrap_success(payload)
    if not isinstance(data, dict):
        raise AuditInputError("source record JSON has an invalid data object")
    names = data.get("fields")
    rows = data.get("data")
    if not isinstance(names, list) or not isinstance(rows, list):
        raise AuditInputError("source record JSON must contain fields and data arrays")
    if record_index < 0 or record_index >= len(rows):
        raise AuditInputError(f"record index {record_index} is outside the returned data")
    if not isinstance(rows[record_index], list) or len(rows[record_index]) != len(names):
        raise AuditInputError("source record row does not align with the fields array")

    values = dict(zip(names, rows[record_index]))
    missing = [name for name in (target_field, requirements_field) if name not in values]
    if missing:
        raise AuditInputError(f"source record is missing fields: {', '.join(missing)}")

    target_value = cell_text(values[target_field])
    urls = [
        url.rstrip(".,;!?，。；！？")
        for url in dict.fromkeys(re.findall(r"https?://[^\s)\]>]+", target_value))
    ]
    if len(urls) != 1:
        raise AuditInputError(
            f"target field {target_field} must contain exactly one HTTP(S) URL; found {len(urls)}"
        )
    requirements_text = cell_text(values[requirements_field]).strip()
    requirements = parse_requirements(requirements_text)
    record_ids = data.get("record_id_list")
    record_id = (
        record_ids[record_index]
        if isinstance(record_ids, list) and record_index < len(record_ids)
        else None
    )
    return {
        "schema_version": 1,
        "record_id": record_id,
        "target_url": urls[0],
        "requirements_text": requirements_text,
        "requirements": [
            {
                "name": field.name,
                "declared_type": field.declared_type,
                "canonical_type": field.canonical_type,
                "options": list(field.options),
            }
            for field in requirements
        ],
    }


def canonical_actual_type(field: dict[str, Any]) -> str:
    field_type = field["type"]
    style = field.get("style") if isinstance(field.get("style"), dict) else {}
    if field_type == "text":
        return f"text/{style.get('type') or 'plain'}"
    if field_type == "number":
        return f"number/{style.get('type') or 'plain'}"
    if field_type == "select":
        return "select/multiple" if field.get("multiple") is True else "select/single"
    if field_type == "link":
        return "link/two_way" if field.get("bidirectional") is True else "link/one_way"
    return field_type


def actual_options(field: dict[str, Any]) -> tuple[str, ...]:
    options = field.get("options")
    if not isinstance(options, list):
        return ()
    return tuple(
        option["name"]
        for option in options
        if isinstance(option, dict) and isinstance(option.get("name"), str)
    )


def load_mapping(path: str | None) -> dict[str, str]:
    if path is None:
        return {}
    payload = read_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("field_mapping"), dict):
        payload = payload["field_mapping"]
    if not isinstance(payload, dict):
        raise AuditInputError("mapping JSON must be an object of requirement name to actual name or ID")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in payload.items()):
        raise AuditInputError("mapping keys and values must be strings")
    return payload


def find_actual_field(
    selector: str,
    actual_fields: list[dict[str, Any]],
) -> tuple[int, dict[str, Any]] | None:
    by_id = [
        (index, field)
        for index, field in enumerate(actual_fields)
        if field.get("id") == selector
    ]
    if len(by_id) == 1:
        return by_id[0]
    key = normalize_name(selector)
    by_name = [
        (index, field)
        for index, field in enumerate(actual_fields)
        if normalize_name(field["name"]) == key
    ]
    if len(by_name) > 1:
        raise AuditInputError(
            f"actual field selector {selector!r} is ambiguous; map to a field ID instead"
        )
    return by_name[0] if by_name else None


def normalized_option_set(options: tuple[str, ...]) -> set[str]:
    return {normalize_name(option) for option in options}


def audit_schema(
    requirements_text: str,
    actual_fields: list[dict[str, Any]],
    mapping: dict[str, str] | None = None,
    *,
    check_options: bool = False,
    allow_extra: bool = False,
) -> dict[str, Any]:
    expected_fields = parse_requirements(requirements_text)
    mapping = mapping or {}
    expected_by_key = {normalize_name(field.name): field for field in expected_fields}
    unknown_mapping_keys = [
        key for key in mapping if normalize_name(key) not in expected_by_key
    ]
    if unknown_mapping_keys:
        raise AuditInputError(
            f"mapping contains unknown requirement fields: {', '.join(unknown_mapping_keys)}"
        )

    normalized_mapping: dict[str, str] = {}
    for key, value in mapping.items():
        normalized_key = normalize_name(key)
        if normalized_key in normalized_mapping:
            raise AuditInputError(f"mapping contains duplicate requirement field: {key}")
        normalized_mapping[normalized_key] = value
    used_actual: set[int] = set()
    details: list[dict[str, Any]] = []

    for expected in expected_fields:
        expected_key = normalize_name(expected.name)
        has_explicit_mapping = expected_key in normalized_mapping
        selector = normalized_mapping.get(expected_key, expected.name)
        matched = find_actual_field(selector, actual_fields)
        if matched is None:
            if has_explicit_mapping:
                raise AuditInputError(
                    f"mapped actual field {selector!r} for {expected.name} was not found"
                )
            details.append(
                {
                    "expected_name": expected.name,
                    "actual_name": None,
                    "expected_type": expected.canonical_type or expected.declared_type,
                    "actual_type": None,
                    "status": "missing",
                }
            )
            continue

        index, actual = matched
        if index in used_actual:
            raise AuditInputError(
                f"actual field {actual['name']} is mapped to more than one requirement"
            )
        used_actual.add(index)
        actual_type = canonical_actual_type(actual)
        status = "match"
        notes: list[str] = []
        if expected.canonical_type is None:
            status = "unsupported_requirement"
            notes.append(f"unsupported requirement type: {expected.declared_type}")
        elif expected.canonical_type != actual_type:
            status = "type_mismatch"
        elif check_options and expected.options:
            expected_options = normalized_option_set(expected.options)
            found_options = normalized_option_set(actual_options(actual))
            if expected_options != found_options:
                status = "options_mismatch"
                missing_options = sorted(expected_options - found_options)
                extra_options = sorted(found_options - expected_options)
                if missing_options:
                    notes.append(f"missing options: {', '.join(missing_options)}")
                if extra_options:
                    notes.append(f"unexpected options: {', '.join(extra_options)}")
        details.append(
            {
                "expected_name": expected.name,
                "actual_name": actual["name"],
                "actual_id": actual.get("id"),
                "expected_type": expected.canonical_type or expected.declared_type,
                "actual_type": actual_type,
                "status": status,
                "notes": notes,
            }
        )

    unexpected = [
        {
            "actual_name": field["name"],
            "actual_id": field.get("id"),
            "actual_type": canonical_actual_type(field),
        }
        for index, field in enumerate(actual_fields)
        if index not in used_actual
    ]
    counts = {
        "expected": len(expected_fields),
        "actual": len(actual_fields),
        "matched": sum(item["status"] == "match" for item in details),
        "type_mismatches": sum(item["status"] == "type_mismatch" for item in details),
        "option_mismatches": sum(item["status"] == "options_mismatch" for item in details),
        "missing": sum(item["status"] == "missing" for item in details),
        "unsupported_requirements": sum(
            item["status"] == "unsupported_requirement" for item in details
        ),
        "unexpected": len(unexpected),
    }
    compliant = (
        counts["matched"] == counts["expected"]
        and (allow_extra or not unexpected)
    )
    return {
        "schema_version": 1,
        "compliant": compliant,
        "settings": {
            "check_options": check_options,
            "allow_extra": allow_extra,
        },
        "summary": counts,
        "fields": details,
        "unexpected_fields": unexpected,
    }


def markdown_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    verdict = "PASS" if result["compliant"] else "FAIL"
    lines = [
        f"# Base schema audit: {verdict}",
        "",
        (
            f"Expected: {summary['expected']} | Actual: {summary['actual']} | "
            f"Matched: {summary['matched']} | Type mismatches: {summary['type_mismatches']} | "
            f"Option mismatches: {summary['option_mismatches']} | Missing: {summary['missing']} | "
            f"Unexpected: {summary['unexpected']}"
        ),
        "",
        "| Requirement field | Actual field | Expected type | Actual type | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in result["fields"]:
        cells = [
            item["expected_name"],
            item.get("actual_name") or "-",
            item["expected_type"],
            item.get("actual_type") or "-",
            item["status"],
        ]
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |")
    if result["unexpected_fields"]:
        lines.extend(["", "## Unexpected fields", ""])
        lines.extend(
            f"- {field['actual_name']} ({field['actual_type']})"
            for field in result["unexpected_fields"]
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser(
        "extract-inputs",
        help="Extract a target Base URL and textual requirements from one record-list response",
    )
    extract.add_argument("--record-file", required=True)
    extract.add_argument("--target-field", required=True)
    extract.add_argument("--requirements-field", required=True)
    extract.add_argument("--record-index", type=int, default=0)

    audit = subparsers.add_parser("audit", help="Compare requirements with a field-list response")
    audit.add_argument("--record-file", required=True)
    audit.add_argument("--target-field", required=True)
    audit.add_argument("--requirements-field", required=True)
    audit.add_argument("--record-index", type=int, default=0)
    audit.add_argument("--actual-file", required=True)
    audit.add_argument("--mapping-file")
    audit.add_argument("--check-options", action="store_true")
    audit.add_argument("--allow-extra", action="store_true")
    audit.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source = extract_source_inputs(
            read_json(args.record_file),
            args.target_field,
            args.requirements_field,
            args.record_index,
        )
        if args.command == "extract-inputs":
            print(json.dumps(source, ensure_ascii=False, indent=2))
            return 0

        result = audit_schema(
            source["requirements_text"],
            extract_actual_fields(read_json(args.actual_file)),
            load_mapping(args.mapping_file),
            check_options=args.check_options,
            allow_extra=args.allow_extra,
        )
        result["source"] = {
            "record_id": source["record_id"],
            "target_url": source["target_url"],
        }
        if args.format == "markdown":
            print(markdown_report(result))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["compliant"] else 1
    except AuditInputError as error:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": str(error),
                    },
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
