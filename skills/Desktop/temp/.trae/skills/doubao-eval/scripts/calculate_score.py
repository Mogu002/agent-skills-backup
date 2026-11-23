#!/usr/bin/env python3
"""Deterministically calculate Doubao-Eval scores from reviewed ratings.

Usage:
    python3 scripts/calculate_score.py ratings.json --pretty
    printf '%s' '{"task_type":"create","dimensions":{...}}' |
      python3 scripts/calculate_score.py - --pretty

Accepted payloads:
    A single item, or {"items": [item, ...]} for a batch.

Each item contains:
    {
      "id": "optional-label",
      "task_type": "create" | "edit" | "data_analysis",
      "dimensions": {
        "table_design": 0 | 1 | "NA" | "/",
        ...
      }
    }

A dimension can instead be an object of named child ratings. Any child 0
collapses the dimension to 0; otherwise any applicable child 1 collapses it to
1; all children NA collapse it to NA. NA is only for structural
inapplicability, never missing evidence. This script calculates arithmetic; it
does not decide whether a rating is factually justified.

Create items may use "NA_QUERY" (or the Chinese alias
"不涉及（query要求）") only for artifact_richness when the Query explicitly
defines the complete artifact-type scope. It is excluded from scoring like NA
but retains its distinct human-evaluation label.

For create and edit items, configuration_correctness must contain all five
human-evaluation subdomains: workflow, dashboard, permission, form, and table.
Each scored item includes human_eval_fields with the exact flat labels and
status wording used by the human-evaluation form.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict, defaultdict
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path
from typing import Any, Mapping


RUBRICS: dict[str, OrderedDict[str, Decimal]] = {
    "create": OrderedDict(
        [
            ("table_design", Decimal("0.35")),
            ("data_reasonableness", Decimal("0.20")),
            ("configuration_correctness", Decimal("0.35")),
            ("artifact_richness", Decimal("0.10")),
        ]
    ),
    "edit": OrderedDict(
        [
            ("table_design", Decimal("0.40")),
            ("data_reasonableness", Decimal("0.20")),
            ("configuration_correctness", Decimal("0.40")),
        ]
    ),
    "data_analysis": OrderedDict([("instruction_following", Decimal("1.00"))]),
}

TASK_TYPE_ALIASES = {
    "create": "create",
    "创建": "create",
    "创建类": "create",
    "edit": "edit",
    "编辑": "edit",
    "编辑类": "edit",
    "data_analysis": "data_analysis",
    "analysis": "data_analysis",
    "数据分析": "data_analysis",
}

CONFIGURATION_SUBDOMAINS: OrderedDict[str, str] = OrderedDict(
    [
        ("workflow", "Workflow配置"),
        ("dashboard", "Dashboard 配置"),
        ("permission", "Permission配置"),
        ("form", "Form 配置正确"),
        ("table", "Table 配置正确"),
    ]
)

HUMAN_RATING_LABELS: dict[int | str, str] = {
    0: "有问题",
    1: "无问题",
    "NA": "不涉及",
    "NA_QUERY": "不涉及（query要求）",
}

QUERY_SCOPED_NA_ALIASES = ("NA_QUERY", "不涉及（query要求）")


class ScoreError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def decimal_string(value: Decimal) -> str:
    if value == 0:
        return "0"
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def display_decimal(value: Decimal, places: str) -> str:
    return format(value.quantize(Decimal(places), rounding=ROUND_HALF_UP), "f")


def normalize_task_type(raw: Any) -> str:
    if not isinstance(raw, str) or raw not in TASK_TYPE_ALIASES:
        raise ScoreError(
            "E_UNKNOWN_TASK_TYPE",
            f"task_type must be one of {sorted(TASK_TYPE_ALIASES)}",
        )
    return TASK_TYPE_ALIASES[raw]


def normalize_leaf(
    raw: Any, path: str, *, allow_query_scoped_na: bool = False
) -> int | str | None:
    allowed = "0, 1, 'NA', or '/'"
    if allow_query_scoped_na:
        allowed += ", plus 'NA_QUERY' or '不涉及（query要求）'"
    if isinstance(raw, bool):
        raise ScoreError(
            "E_INVALID_RATING",
            f"{path} must be {allowed}; booleans are not accepted",
        )
    if isinstance(raw, int) and raw in (0, 1):
        return raw
    if raw in ("NA", "/"):
        return None
    if raw in QUERY_SCOPED_NA_ALIASES:
        if allow_query_scoped_na:
            return "NA_QUERY"
        raise ScoreError(
            "E_QUERY_SCOPED_NA_NOT_ALLOWED",
            f"{path} may not use 'NA_QUERY' or '不涉及（query要求）'",
        )
    raise ScoreError("E_INVALID_RATING", f"{path} must be {allowed}")


def resolve_rating(
    raw: Any, path: str, *, allow_query_scoped_na: bool = False
) -> tuple[int | str | None, dict[str, int | str] | None]:
    if isinstance(raw, Mapping):
        if not raw:
            raise ScoreError("E_EMPTY_SUBDIMENSIONS", f"{path} must not be an empty object")
        children: dict[str, int | str] = {}
        resolved_children: list[int | None] = []
        for key, value in raw.items():
            if not isinstance(key, str) or not key:
                raise ScoreError("E_INVALID_SUBDIMENSION", f"{path} contains an invalid child name")
            child = normalize_leaf(value, f"{path}.{key}")
            resolved_children.append(child)
            children[key] = "NA" if child is None else child
        if 0 in resolved_children:
            return 0, children
        if 1 in resolved_children:
            return 1, children
        return None, children
    return normalize_leaf(
        raw, path, allow_query_scoped_na=allow_query_scoped_na
    ), None


def validate_configuration_subdomains(raw: Any, path: str) -> None:
    if not isinstance(raw, Mapping):
        raise ScoreError(
            "E_CONFIGURATION_SUBDOMAINS_REQUIRED",
            f"{path} must be an object containing {list(CONFIGURATION_SUBDOMAINS)}",
        )
    expected = set(CONFIGURATION_SUBDOMAINS)
    provided = set(raw)
    missing = sorted(expected - provided)
    unknown = sorted(provided - expected)
    if missing:
        raise ScoreError(
            "E_MISSING_CONFIGURATION_SUBDOMAIN",
            f"{path} is missing subdomains: {missing}",
        )
    if unknown:
        raise ScoreError(
            "E_UNKNOWN_CONFIGURATION_SUBDOMAIN",
            f"{path} has unknown subdomains: {unknown}",
        )


def human_rating(raw: int | str) -> str:
    return HUMAN_RATING_LABELS[raw]


def render_human_eval_fields(
    task_type: str,
    resolved: Mapping[str, int | str],
    child_ratings: Mapping[str, Mapping[str, int | str]],
    score: Decimal,
) -> OrderedDict[str, str]:
    configuration = child_ratings.get("configuration_correctness", {})
    fields: OrderedDict[str, str] = OrderedDict(
        [
            ("数据表设计", human_rating(resolved.get("table_design", "NA"))),
            ("数据合理性", human_rating(resolved.get("data_reasonableness", "NA"))),
        ]
    )
    for subdomain, label in CONFIGURATION_SUBDOMAINS.items():
        fields[label] = human_rating(configuration.get(subdomain, "NA"))
    fields["指令遵从【数据分析专有】"] = human_rating(
        resolved.get("instruction_following", "NA")
    )
    fields["产物丰富度【创建类题目专有】"] = human_rating(
        resolved.get("artifact_richness", "NA")
    )
    fields["最终分数"] = decimal_string(score)
    return fields


def score_item(item: Mapping[str, Any], index: int = 0) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise ScoreError("E_INVALID_ITEM", f"items[{index}] must be an object")
    task_type = normalize_task_type(item.get("task_type"))
    raw_dimensions = item.get("dimensions")
    if not isinstance(raw_dimensions, Mapping):
        raise ScoreError("E_INVALID_DIMENSIONS", f"items[{index}].dimensions must be an object")

    weights = RUBRICS[task_type]
    expected = set(weights)
    provided = set(raw_dimensions)
    missing = sorted(expected - provided)
    unknown = sorted(provided - expected)
    if missing:
        raise ScoreError("E_MISSING_DIMENSION", f"items[{index}] is missing dimensions: {missing}")
    if unknown:
        raise ScoreError("E_UNKNOWN_DIMENSION", f"items[{index}] has unknown dimensions: {unknown}")

    if task_type in ("create", "edit"):
        validate_configuration_subdomains(
            raw_dimensions["configuration_correctness"],
            f"items[{index}].dimensions.configuration_correctness",
        )

    resolved: OrderedDict[str, int | str] = OrderedDict()
    child_ratings: dict[str, dict[str, int | str]] = {}
    numerator = Decimal("0")
    denominator = Decimal("0")
    applicable: list[str] = []
    not_applicable: list[str] = []

    for dimension, weight in weights.items():
        rating, children = resolve_rating(
            raw_dimensions[dimension],
            f"items[{index}].dimensions.{dimension}",
            allow_query_scoped_na=(
                task_type == "create" and dimension == "artifact_richness"
            ),
        )
        if children is not None:
            child_ratings[dimension] = children
        if rating is None or rating == "NA_QUERY":
            resolved[dimension] = "NA_QUERY" if rating == "NA_QUERY" else "NA"
            not_applicable.append(dimension)
            continue
        resolved[dimension] = rating
        applicable.append(dimension)
        numerator += weight * Decimal(rating)
        denominator += weight

    if denominator == 0:
        raise ScoreError("E_NO_APPLICABLE_DIMENSIONS", f"items[{index}] has no applicable dimensions")

    with localcontext() as context:
        context.prec = 28
        score = numerator / denominator
        effective_weights = OrderedDict(
            (dimension, decimal_string(weights[dimension] / denominator))
            for dimension in applicable
        )

    result: dict[str, Any] = {
        "id": item.get("id", str(index + 1)),
        "task_type": task_type,
        "resolved_dimensions": resolved,
        "weights": OrderedDict((key, decimal_string(value)) for key, value in weights.items()),
        "applicable_dimensions": applicable,
        "not_applicable_dimensions": not_applicable,
        "effective_weights": effective_weights,
        "weighted_sum": decimal_string(numerator),
        "applicable_weight_sum": decimal_string(denominator),
        "score": decimal_string(score),
        "display_score": display_decimal(score, "0.01"),
        "score_percent": decimal_string(score * 100),
        "display_percent": display_decimal(score * 100, "0.01"),
        "rounded_integer_percent": int((score * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        "human_eval_fields": render_human_eval_fields(
            task_type, resolved, child_ratings, score
        ),
    }
    if child_ratings:
        result["child_ratings"] = child_ratings
    return result


def aggregate_scored_items(scored: list[dict[str, Any]]) -> dict[str, Any]:
    if not scored:
        raise ScoreError("E_EMPTY_BATCH", "items must contain at least one item")
    values = [Decimal(item["score"]) for item in scored]
    with localcontext() as context:
        context.prec = 28
        mean = sum(values, Decimal("0")) / Decimal(len(values))

    grouped: defaultdict[str, list[Decimal]] = defaultdict(list)
    for item, value in zip(scored, values):
        grouped[item["task_type"]].append(value)

    by_task_type: dict[str, Any] = {}
    for task_type in RUBRICS:
        task_values = grouped.get(task_type)
        if not task_values:
            continue
        task_mean = sum(task_values, Decimal("0")) / Decimal(len(task_values))
        by_task_type[task_type] = {
            "count": len(task_values),
            "score": decimal_string(task_mean),
            "display_percent": display_decimal(task_mean * 100, "0.01"),
        }

    return {
        "method": "macro_average_of_item_scores",
        "count": len(scored),
        "score": decimal_string(mean),
        "display_score": display_decimal(mean, "0.01"),
        "score_percent": decimal_string(mean * 100),
        "display_percent": display_decimal(mean * 100, "0.01"),
        "rounded_integer_percent": int((mean * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        "by_task_type": by_task_type,
    }


def score_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ScoreError("E_INVALID_PAYLOAD", "payload must be an object")
    if "items" in payload:
        items = payload["items"]
        if not isinstance(items, list):
            raise ScoreError("E_INVALID_BATCH", "items must be an array")
        scored = [score_item(item, index) for index, item in enumerate(items)]
        return {"ok": True, "items": scored, "aggregate": aggregate_scored_items(scored)}
    return {"ok": True, "item": score_item(payload)}


def load_payload(path: str) -> Any:
    try:
        if path == "-":
            return json.load(sys.stdin)
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScoreError("E_INPUT", str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calculate Doubao-Eval weighted scores")
    parser.add_argument("input", help="JSON file path, or '-' for stdin")
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    args = parser.parse_args(argv)
    try:
        result = score_payload(load_payload(args.input))
    except ScoreError as exc:
        json.dump(
            {"ok": False, "error": {"code": exc.code, "message": str(exc)}},
            sys.stderr,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
        )
        sys.stderr.write("\n")
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
