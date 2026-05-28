#!/usr/bin/env python3
"""Build a compact manifest for model-eval QC runs in this workspace."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any

JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan ba-* benchmark packages and emit a compact manifest for score QC."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Benchmark repository root. Auto-detected when omitted.",
    )
    parser.add_argument(
        "--task",
        default="*",
        help="Filter task ids with shell-style wildcards, e.g. ba-001 or ba-0*.",
    )
    parser.add_argument(
        "--model",
        default="*",
        help="Filter model directory names with shell-style wildcards.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Stop after emitting N runs. 0 means no limit.",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=280,
        help="Max characters kept for text previews.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the JSON manifest.",
    )
    return parser.parse_args()


def truncate(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_fenced_json(text: str) -> Any:
    match = JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError("No fenced JSON block found")
    return json.loads(match.group(1))


def parse_score(path: Path, preview_chars: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "recorded_score": None,
        "recorded_all_pass": None,
        "recorded_rubrics": [],
        "score_parse_error": None,
    }
    try:
        payload = extract_fenced_json(read_text(path))
        result["recorded_score"] = payload.get("score")
        result_json = payload.get("result_json") or {}
        result["recorded_all_pass"] = result_json.get("all_pass")
        rubrics = []
        for item in result_json.get("results") or []:
            rubrics.append(
                {
                    "rubric_id": item.get("rubric_id"),
                    "pass": item.get("pass"),
                    "reason_preview": truncate(str(item.get("reason", "")), preview_chars),
                }
            )
        result["recorded_rubrics"] = rubrics
    except Exception as exc:  # noqa: BLE001
        result["score_parse_error"] = str(exc)
    return result


def parse_rubrics(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "rubric_count": None,
        "rubric_ids": [],
        "rubric_parse_error": None,
    }
    try:
        payload = extract_fenced_json(read_text(path))
        result["rubric_count"] = len(payload)
        result["rubric_ids"] = [item.get("id") for item in payload if isinstance(item, dict)]
    except Exception as exc:  # noqa: BLE001
        result["rubric_parse_error"] = str(exc)
    return result


def parse_messages(path: Path, preview_chars: int) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "assistant_turns": 0,
        "nonempty_assistant_turns": 0,
        "tool_call_count": 0,
        "tool_message_count": 0,
        "empty_tool_output_count": 0,
        "tool_names": [],
        "missing_final_answer": True,
        "final_answer_length": 0,
        "final_answer_preview": "",
        "message_parse_error": None,
    }
    try:
        payload = json.loads(read_text(path))
        messages = payload.get("messages") or []
        tool_names: list[str] = []
        final_answer = ""
        for message in messages:
            role = message.get("role")
            if role == "assistant":
                summary["assistant_turns"] += 1
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    summary["nonempty_assistant_turns"] += 1
                    final_answer = content.strip()
                for call in message.get("tool_calls") or []:
                    summary["tool_call_count"] += 1
                    name = (((call or {}).get("function") or {}).get("name"))
                    if name:
                        tool_names.append(str(name))
            elif role == "tool":
                summary["tool_message_count"] += 1
                content = message.get("content")
                if isinstance(content, str) and content.strip() == "(no output)":
                    summary["empty_tool_output_count"] += 1
        summary["tool_names"] = sorted(set(tool_names))
        if final_answer:
            summary["missing_final_answer"] = False
            summary["final_answer_length"] = len(final_answer)
            summary["final_answer_preview"] = truncate(final_answer, preview_chars)
    except Exception as exc:  # noqa: BLE001
        summary["message_parse_error"] = str(exc)
    return summary


def looks_like_repo_root(path: Path) -> bool:
    if not path.is_dir():
        return False
    for child in path.iterdir():
        if child.is_dir() and child.name.startswith("ba-") and (child / "task.yaml").exists():
            return True
    return False


def detect_repo_root(explicit: Path | None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit.expanduser().resolve())
    cwd = Path.cwd().resolve()
    candidates.extend([cwd, *cwd.parents])
    script_path = Path(__file__).resolve()
    candidates.extend(script_path.parents)
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if looks_like_repo_root(candidate):
            return candidate
    raise SystemExit("Could not detect benchmark repo root. Pass --root explicitly.")


def iter_task_dirs(root: Path, task_pattern: str) -> list[Path]:
    task_dirs = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if not child.name.startswith("ba-"):
            continue
        if not fnmatch.fnmatch(child.name, task_pattern):
            continue
        if not (child / "task.yaml").exists():
            continue
        task_dirs.append(child)
    return task_dirs


def build_manifest(root: Path, task_pattern: str, model_pattern: str, limit: int, preview_chars: int) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    task_dirs = iter_task_dirs(root, task_pattern)
    for task_dir in task_dirs:
        rubrics_path = task_dir / "solution" / "rubrics.md"
        rubrics_info = parse_rubrics(rubrics_path) if rubrics_path.exists() else {
            "rubric_count": None,
            "rubric_ids": [],
            "rubric_parse_error": "Missing rubrics.md",
        }
        model_outputs_dir = task_dir / "model_outputs"
        if not model_outputs_dir.exists():
            continue
        for model_dir in sorted(model_outputs_dir.iterdir()):
            if not model_dir.is_dir() or not fnmatch.fnmatch(model_dir.name, model_pattern):
                continue
            for run_dir in sorted(model_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                score_path = run_dir / "score.md"
                message_path = run_dir / "openai_messages.json"
                score_info = parse_score(score_path, preview_chars) if score_path.exists() else {
                    "recorded_score": None,
                    "recorded_all_pass": None,
                    "recorded_rubrics": [],
                    "score_parse_error": "Missing score.md",
                }
                message_info = parse_messages(message_path, preview_chars) if message_path.exists() else {
                    "assistant_turns": 0,
                    "nonempty_assistant_turns": 0,
                    "tool_call_count": 0,
                    "tool_message_count": 0,
                    "empty_tool_output_count": 0,
                    "tool_names": [],
                    "missing_final_answer": True,
                    "final_answer_length": 0,
                    "final_answer_preview": "",
                    "message_parse_error": "Missing openai_messages.json",
                }
                run_record = {
                    "task_id": task_dir.name,
                    "model_name": model_dir.name,
                    "run_id": run_dir.name,
                    "paths": {
                        "task_yaml": str(task_dir / "task.yaml"),
                        "rubrics_md": str(rubrics_path),
                        "score_md": str(score_path),
                        "openai_messages_json": str(message_path),
                        "run_dir": str(run_dir),
                    },
                    "files_present": {
                        "task_yaml": (task_dir / "task.yaml").exists(),
                        "rubrics_md": rubrics_path.exists(),
                        "score_md": score_path.exists(),
                        "openai_messages_json": message_path.exists(),
                    },
                    **rubrics_info,
                    **score_info,
                    **message_info,
                }
                runs.append(run_record)
                if limit and len(runs) >= limit:
                    break
            if limit and len(runs) >= limit:
                break
        if limit and len(runs) >= limit:
            break

    return {
        "repo_root": str(root),
        "task_count": len(task_dirs),
        "run_count": len(runs),
        "filters": {
            "task": task_pattern,
            "model": model_pattern,
            "limit": limit,
        },
        "runs": runs,
    }


def main() -> int:
    args = parse_args()
    root = detect_repo_root(args.root)
    manifest = build_manifest(
        root=root,
        task_pattern=args.task,
        model_pattern=args.model,
        limit=args.limit,
        preview_chars=args.preview_chars,
    )
    output = json.dumps(manifest, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
