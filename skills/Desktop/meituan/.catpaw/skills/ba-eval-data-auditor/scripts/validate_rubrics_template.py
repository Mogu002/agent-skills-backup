#!/usr/bin/env python3
import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List

TASK_DIR_RE = re.compile(r"^ba-\d+$")
EXPECTED_HEADER = "# Rubrics"
EXPECTED_PASS_RULE = "> **通过标准：所有 rubric 均须满足，该任务才算通过。任一 rubric 不通过，则该任务整体判定为不通过。**"
EXPECTED_PATH_SECTION = "## 文件读取路径"
EXPECTED_ITEM_KEYS = ("id", "content", "weight")


@dataclass
class Issue:
    severity: str
    code: str
    message: str


@dataclass
class Report:
    target: str
    path: str
    errors: List[Issue]
    warnings: List[Issue]

    def as_dict(self) -> dict:
        return {
            "target": self.target,
            "path": self.path,
            "errors": [asdict(item) for item in self.errors],
            "warnings": [asdict(item) for item in self.warnings],
        }


@dataclass
class FenceBlock:
    lang: str
    body: str
    start_line: int
    end_line: int


class RubricsTemplateValidator:
    def __init__(self) -> None:
        self.scanned = 0

    def validate_root(self, root: Path) -> List[Report]:
        reports: List[Report] = []
        for rubrics_path in self._iter_rubrics_files(root):
            reports.append(self.validate_file(rubrics_path))
        return reports

    def _iter_rubrics_files(self, root: Path) -> Iterable[Path]:
        if root.is_file():
            if root.name != "rubrics.md":
                raise ValueError("root file must be named rubrics.md")
            yield root
            return

        direct_file = root / "rubrics.md"
        if direct_file.is_file():
            yield direct_file
            return

        matched_children = []
        for child in sorted(root.iterdir()):
            if not child.is_dir() or not TASK_DIR_RE.match(child.name):
                continue
            rubrics_path = child / "rubrics.md"
            if rubrics_path.is_file():
                matched_children.append(rubrics_path)

        if matched_children:
            yield from matched_children
            return

        for rubrics_path in sorted(root.rglob("rubrics.md")):
            yield rubrics_path

    def validate_file(self, rubrics_path: Path) -> Report:
        self.scanned += 1
        report = Report(
            target=rubrics_path.parent.name,
            path=str(rubrics_path),
            errors=[],
            warnings=[],
        )

        try:
            raw_text = rubrics_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            report.errors.append(Issue("error", "RUBRICS_ENCODING", "文件不是 UTF-8 文本"))
            return report

        text = raw_text.replace("\r\n", "\n")
        if not text.strip():
            report.errors.append(Issue("error", "RUBRICS_EMPTY", "文件为空"))
            return report

        self._check_fixed_template(report, text)
        return report

    def _check_fixed_template(self, report: Report, text: str) -> None:
        lines = text.split("\n")
        nonempty_lines = [line.strip() for line in lines if line.strip()]
        if not nonempty_lines:
            report.errors.append(Issue("error", "RUBRICS_EMPTY", "文件为空"))
            return

        if nonempty_lines[0] != EXPECTED_HEADER:
            report.errors.append(
                Issue("error", "RUBRIC_HEADER", f"首个非空行必须是 `{EXPECTED_HEADER}`，当前为 `{nonempty_lines[0]}`")
            )

        if len(nonempty_lines) < 2 or nonempty_lines[1] != EXPECTED_PASS_RULE:
            report.errors.append(
                Issue("error", "RUBRIC_PASS_RULE", "通过标准说明必须使用固定文案，并紧跟在标题后")
            )

        if len(nonempty_lines) < 3 or nonempty_lines[2] != EXPECTED_PATH_SECTION:
            report.errors.append(
                Issue("error", "RUBRIC_PATH_SECTION", "`## 文件读取路径` 必须作为第三个非空行出现")
            )

        blocks = self._extract_fence_blocks(lines)
        path_blocks = [block for block in blocks if block.lang == "path"]
        json_blocks = [block for block in blocks if block.lang == "json"]

        if len(path_blocks) != 1:
            report.errors.append(
                Issue("error", "RUBRIC_PATH_BLOCK", f"`path` 代码块数量必须为 1，当前为 {len(path_blocks)}")
            )
        if len(json_blocks) != 1:
            report.errors.append(
                Issue("error", "RUBRIC_JSON_BLOCK", f"`json` 代码块数量必须为 1，当前为 {len(json_blocks)}")
            )

        if path_blocks and json_blocks:
            path_block = path_blocks[0]
            json_block = json_blocks[0]
            path_section_line = self._find_line_number(lines, EXPECTED_PATH_SECTION)
            if path_section_line == -1 or self._previous_nonempty_line_number(lines, path_block.start_line) != path_section_line:
                report.errors.append(
                    Issue("error", "RUBRIC_PATH_ORDER", "`path` 代码块必须紧跟在 `## 文件读取路径` 段落后")
                )
            if path_block.start_line >= json_block.start_line:
                report.errors.append(
                    Issue("error", "RUBRIC_BLOCK_ORDER", "`path` 代码块必须出现在 `json` 代码块之前")
                )
            if any(line.strip().startswith(("-", "*")) for line in path_block.body.splitlines() if line.strip()):
                report.errors.append(
                    Issue("error", "RUBRIC_PATH_SYNTAX", "文件读取路径应逐行直写，不要写成列表项")
                )
            self._check_no_extra_content(report, lines, path_block, json_block, path_section_line)
            self._check_json_payload(report, json_block.body)

    def _check_no_extra_content(
        self,
        report: Report,
        lines: List[str],
        path_block: FenceBlock,
        json_block: FenceBlock,
        path_section_line: int,
    ) -> None:
        allowed_nonempty_lines = {1, 2, 3, path_section_line, path_block.start_line, path_block.end_line, json_block.start_line, json_block.end_line}
        for line_no in range(path_block.start_line + 1, path_block.end_line):
            allowed_nonempty_lines.add(line_no)
        for line_no in range(json_block.start_line + 1, json_block.end_line):
            allowed_nonempty_lines.add(line_no)

        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            if line_no == 2 and stripped == EXPECTED_PASS_RULE:
                allowed_nonempty_lines.add(line_no)
                continue
            if line_no in allowed_nonempty_lines:
                continue
            report.errors.append(
                Issue("error", "RUBRIC_EXTRA_CONTENT", f"第 {line_no} 行存在模板外内容：`{stripped[:40]}`")
            )
            return

    def _check_json_payload(self, report: Report, body: str) -> None:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            report.errors.append(Issue("error", "RUBRIC_JSON_PARSE", f"`json` 代码块无法解析：{exc.msg}"))
            return

        if not isinstance(payload, list):
            report.errors.append(Issue("error", "RUBRIC_JSON_TYPE", "`json` 代码块顶层必须是数组"))
            return

        if not payload:
            report.errors.append(Issue("error", "RUBRIC_JSON_EMPTY", "rubrics 数组不能为空"))
            return

        seen_ids: set[str] = set()
        for index, item in enumerate(payload, start=1):
            if not isinstance(item, dict):
                report.errors.append(
                    Issue("error", "RUBRIC_ITEM_TYPE", f"第 {index} 条 rubric 必须是对象，当前为 `{type(item).__name__}`")
                )
                continue

            item_keys = tuple(item.keys())
            missing = [key for key in EXPECTED_ITEM_KEYS if key not in item]
            extra = [key for key in item_keys if key not in EXPECTED_ITEM_KEYS]
            if missing:
                report.errors.append(
                    Issue("error", "RUBRIC_ITEM_FIELD", f"第 {index} 条 rubric 缺少字段：{'、'.join(f'`{key}`' for key in missing)}")
                )
                continue
            if extra:
                report.errors.append(
                    Issue("error", "RUBRIC_ITEM_EXTRA_FIELD", f"第 {index} 条 rubric 存在多余字段：{'、'.join(f'`{key}`' for key in extra)}")
                )
            if item_keys[: len(EXPECTED_ITEM_KEYS)] != EXPECTED_ITEM_KEYS:
                report.warnings.append(
                    Issue("warning", "RUBRIC_ITEM_KEY_ORDER", f"第 {index} 条 rubric 建议按 `id`、`content`、`weight` 的顺序书写")
                )

            rubric_id = item.get("id")
            content = item.get("content")
            weight = item.get("weight")

            if not isinstance(rubric_id, str) or not re.fullmatch(r"\d{2}", rubric_id):
                report.errors.append(
                    Issue("error", "RUBRIC_ID_FORMAT", f"第 {index} 条 rubric 的 `id` 必须是两位字符串，如 `01`")
                )
            elif rubric_id in seen_ids:
                report.errors.append(Issue("error", "RUBRIC_ID_DUPLICATE", f"rubric id `{rubric_id}` 重复"))
            else:
                seen_ids.add(rubric_id)

            if not isinstance(content, str) or not content.strip():
                report.errors.append(Issue("error", "RUBRIC_CONTENT", f"第 {index} 条 rubric 的 `content` 必须是非空字符串"))

            if not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight <= 0:
                report.errors.append(Issue("error", "RUBRIC_WEIGHT", f"第 {index} 条 rubric 的 `weight` 必须为正数"))

    def _extract_fence_blocks(self, lines: List[str]) -> List[FenceBlock]:
        blocks: List[FenceBlock] = []
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if not line.startswith("```"):
                index += 1
                continue

            raw_lang = line[3:].strip().split()[0] if line[3:].strip() else ""
            start_line = index + 1
            index += 1
            body_lines: List[str] = []
            while index < len(lines) and lines[index].strip() != "```":
                body_lines.append(lines[index])
                index += 1

            if index >= len(lines):
                blocks.append(FenceBlock(lang=raw_lang.lower(), body="\n".join(body_lines), start_line=start_line, end_line=len(lines)))
                break

            end_line = index + 1
            blocks.append(FenceBlock(lang=raw_lang.lower(), body="\n".join(body_lines), start_line=start_line, end_line=end_line))
            index += 1
        return blocks

    def _find_line_number(self, lines: List[str], expected: str) -> int:
        for line_no, line in enumerate(lines, start=1):
            if line.strip() == expected:
                return line_no
        return -1

    def _previous_nonempty_line_number(self, lines: List[str], before_line_no: int) -> int:
        for index in range(before_line_no - 2, -1, -1):
            if lines[index].strip():
                return index + 1
        return -1


def format_text(root: Path, reports: List[Report], scanned: int) -> str:
    error_count = sum(len(report.errors) for report in reports)
    warning_count = sum(len(report.warnings) for report in reports)
    problem_reports = [report for report in reports if report.errors or report.warnings]

    lines = [
        f"Scanned: {scanned}",
        f"Files with issues: {len(problem_reports)}",
        f"Errors: {error_count}",
        f"Warnings: {warning_count}",
        f"Root: {root}",
    ]

    if not problem_reports:
        lines.append("\nPASS: 所有 rubrics.md 均符合固定模板。")
        return "\n".join(lines)

    for report in problem_reports:
        lines.append(f"\n[{report.target}] {report.path}")
        for issue in report.errors:
            lines.append(f"  - ERROR {issue.code}: {issue.message}")
        for issue in report.warnings:
            lines.append(f"  - WARNING {issue.code}: {issue.message}")
    return "\n".join(lines)


def format_json(root: Path, reports: List[Report], scanned: int) -> str:
    payload = {
        "root": str(root),
        "scanned": scanned,
        "files_with_issues": sum(1 for report in reports if report.errors or report.warnings),
        "error_count": sum(len(report.errors) for report in reports),
        "warning_count": sum(len(report.warnings) for report in reports),
        "reports": [report.as_dict() for report in reports],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate rubrics.md files against the fixed markdown template.")
    parser.add_argument("--root", required=True, help="Root directory, task directory, or rubrics.md file to validate.")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "never"],
        default="error",
        help="Exit non-zero on errors, warnings, or never.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        print(f"ERROR: root does not exist: {root}", file=sys.stderr)
        return 2

    validator = RubricsTemplateValidator()
    try:
        reports = validator.validate_root(root)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(format_json(root, reports, validator.scanned))
    else:
        print(format_text(root, reports, validator.scanned))

    error_count = sum(len(report.errors) for report in reports)
    warning_count = sum(len(report.warnings) for report in reports)
    if args.fail_on == "never":
        return 0
    if args.fail_on == "warning" and (error_count or warning_count):
        return 1
    if args.fail_on == "error" and error_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
