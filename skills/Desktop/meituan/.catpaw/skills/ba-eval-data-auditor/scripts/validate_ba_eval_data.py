#!/usr/bin/env python3
import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List

TASK_DIR_RE = re.compile(r"^ba-\d+$")
MEITUAN_PATH_RE = re.compile(r"/meituan/[^\s`<>()\]\[\"']+")
FILE_TAG_RE = re.compile(r"<file>(.*?)</file>")
AMBIGUOUS_RUBRIC_TOKENS = ["大致", "基本", "明显", "显著", "大幅", "小幅", "约", "左右", "可能", "较多", "较少"]
ANALYSIS_TASK_TOKENS = ["分析", "比较", "解释", "原因", "策略", "建议", "效果", "影响"]
OPEN_ANALYSIS_TASK_TOKENS = ["推断", "最可能发生了什么事件", "发生了什么事件", "因果链路", "因果链", "综合以上", "综合上述", "归因"]
COMPARISON_TASK_TOKENS = ["比较", "对比", "分别", "分城市", "分不同城市", "两个城市", "各城市"]
DWD_ONLY_DIMENSION_GROUPS = [
    ("品类", ["品类", "category"]),
    ("入口", ["入口", "entrance"]),
    ("商品", ["商品", "product_id", "product"]),
]
DWD_RISK_ACTION_TOKENS = [
    "驱动",
    "归因",
    "主要由",
    "主要来自",
    "带动",
    "拉动",
    "导致",
    "造成",
    "原因",
    "贡献",
    "比较",
    "对比",
    "排序",
    "排名",
    "最高",
    "最低",
    "最大",
    "最小",
    "首位",
]
DESCRIPTIVE_RUBRIC_BAD_PREFIX_RE = re.compile(r"^答案(?:内容)?需(?!(明确指出|提及|说明|描述|分析|判断|指出|包含|覆盖|体现|给出|分城市|分别|结合|识别|列出|要包含|能够体现|清楚说明))")
TOO_VAGUE_DESCRIPTIVE_RUBRIC_RE = re.compile(
    r"^答案(?:内容)?需(?:回答|表述|分析|结论|原因|策略|效果|判断)?(?:合理|准确|完整|清晰|充分|到位|正确|较好|良好)+(?:即可|就行|便可)?[。；;，, ]*$"
)
VAGUE_REQUIREMENT_TOKENS = ["合理", "准确", "完整", "清晰", "充分", "到位", "正确", "较好", "良好", "全面"]
CONCRETE_REQUIREMENT_HINTS = [
    "明确指出",
    "提及",
    "说明",
    "列出",
    "给出",
    "包含",
    "覆盖",
    "识别",
    "分城市",
    "分别",
    "比较",
    "对比",
    "原因",
    "策略",
    "效果",
    "事件",
    "链路",
    "城市",
    "对象",
    "时间段",
    "指标",
    "数值",
    "比例",
    "<file>",
]
ANTI_FOLLOWUP_PHRASES = [
    "不要问我任何问题",
    "不要让我做出进一步决策",
    "请你自行解决",
]
FORMAT_REQUIREMENT_TOKENS = [
    "颜色",
    "字体",
    "字号",
    "加粗",
    "小数位",
    "百分比",
    "百分数",
    "会计",
    "单元格格式",
    "填充",
    "透明度",
    "日期",
    "分数",
]
CELL_FORMAT_REQUIREMENT_TOKENS = ["百分比", "百分数", "分数", "会计", "日期"]
PROHIBITED_MODEL_FILE_OP_TOKENS = [
    "读取文件",
    "打开文件",
    "检查文件路径",
    "检查路径",
    "遍历文件夹",
    "判断文件是否存在",
    "查看文件内容",
]
ROW_COL_HINT_RE = re.compile(r"(?:[A-Z]{1,3}列|第?\d+行|首行|首列|单元格|sheet|Sheet)")
TASK_REQUIREMENT_RE = re.compile(r"任务要求：\s*(.+?)(?:\n\s*\n|$)", re.S)
BA_TEMPLATE_HINTS = [
    ("BA_INST_ROLE", "warning", "缺少 BA 固定角色说明：`你是一名专业商分分析师`"),
    ("BA_INST_DATASETTE", "warning", "缺少 Datasette SQL 接口说明或 URL 模板"),
    ("BA_INST_TABLES", "warning", "缺少 BA 固定表结构说明"),
    ("BA_INST_BROWSER", "warning", "缺少数据库在线浏览地址"),
    ("BA_INST_TASK", "warning", "缺少 `任务要求：` 段落"),
    ("BA_INST_FINAL_NOTE", "warning", "缺少 BA 模板中的直接回复/不要生成文件说明"),
]


@dataclass
class Issue:
    severity: str
    code: str
    message: str


@dataclass
class TaskReport:
    task: str
    path: str
    errors: List[Issue]
    warnings: List[Issue]

    def as_dict(self) -> dict:
        return {
            "task": self.task,
            "path": self.path,
            "errors": [asdict(item) for item in self.errors],
            "warnings": [asdict(item) for item in self.warnings],
        }


class Validator:
    def __init__(self) -> None:
        self.scanned = 0

    def validate_root(self, root: Path, only: set[str] | None = None) -> List[TaskReport]:
        reports: List[TaskReport] = []
        for task_dir in self._iter_task_dirs(root):
            if only and task_dir.name not in only:
                continue
            reports.append(self.validate_task(task_dir))
        return reports

    def _iter_task_dirs(self, root: Path) -> Iterable[Path]:
        for candidate in sorted(root.rglob("*")):
            if candidate.is_dir() and TASK_DIR_RE.match(candidate.name):
                yield candidate

    def validate_task(self, task_dir: Path) -> TaskReport:
        self.scanned += 1
        report = TaskReport(task=task_dir.name, path=str(task_dir), errors=[], warnings=[])

        instruction_path = task_dir / "instruction.md"
        rubrics_path = task_dir / "solution" / "rubrics.md"

        if not instruction_path.exists():
            report.errors.append(Issue("error", "STRUCT_MISSING_INSTRUCTION", "缺少 `instruction.md`"))
        if not rubrics_path.exists():
            report.errors.append(Issue("error", "STRUCT_MISSING_RUBRICS", "缺少 `solution/rubrics.md`"))

        instruction_text = self._read_text(instruction_path, report, "instruction") if instruction_path.exists() else None
        rubrics_text = self._read_text(rubrics_path, report, "rubrics") if rubrics_path.exists() else None

        if instruction_text:
            self._check_instruction(report, instruction_text)
        if rubrics_text:
            self._check_rubrics(report, rubrics_text)
            if instruction_text:
                self._check_cross_file(report, instruction_text, rubrics_text)

        return report

    def _read_text(self, path: Path, report: TaskReport, label: str) -> str | None:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            report.errors.append(Issue("error", f"{label.upper()}_ENCODING", f"`{path.name}` 不是 UTF-8 文本"))
            return None
        if not text.strip():
            report.errors.append(Issue("error", f"{label.upper()}_EMPTY", f"`{path.name}` 为空文件"))
            return None
        return text

    def _check_instruction(self, report: TaskReport, text: str) -> None:
        missing = [phrase for phrase in ANTI_FOLLOWUP_PHRASES if phrase not in text]
        if missing:
            report.errors.append(
                Issue(
                    "error",
                    "INST_ANTI_FOLLOWUP",
                    "缺少防追问指令片段：" + "、".join(f"`{item}`" for item in missing),
                )
            )

        local_paths = MEITUAN_PATH_RE.findall(text)
        for path in local_paths:
            wrapped = f"`{path}`" in text
            if not wrapped:
                report.warnings.append(
                    Issue("warning", "INST_PATH_NOT_CODE", f"本地路径 `{path}` 建议使用反引号包裹，保持代码条形式")
                )
            if not path.startswith("/meituan/"):
                report.errors.append(Issue("error", "INST_PATH_PREFIX", f"本地路径 `{path}` 应以 `/meituan/` 开头"))

        if self._looks_like_file_output_task(text) and not local_paths:
            report.errors.append(
                Issue(
                    "error",
                    "INST_OUTPUT_PATH_UNCLEAR",
                    "看起来要求输出/修改本地文件，但 instruction 中没有明确的 `/meituan/...` 文件或目录路径",
                )
            )

        ridehailing_table_block_ok = (
            "数据库共包含三张表" in text
            and "_dwd_order_detail" in text
            and "_dwd_driver_daily" in text
            and "_dwd_passenger_daily" in text
        )
        specialteam_table_block_ok = (
            "数据库共包含四张表" in text
            and "dwd_transaction.csv" in text
            and "dws_user_daily.csv" in text
            and "dws_stall_daily.csv" in text
            and "dws_platform_daily.csv" in text
        )

        ba_checks = [
            ("BA_INST_ROLE", "你是一名专业商分分析师" in text),
            ("BA_INST_DATASETTE", "Datasette SQL 查询接口" in text and "_shape=array" in text),
            ("BA_INST_TABLES", ridehailing_table_block_ok or specialteam_table_block_ok),
            ("BA_INST_BROWSER", "数据库在线浏览地址：" in text),
            ("BA_INST_TASK", "任务要求：" in text),
            (
                "BA_INST_FINAL_NOTE",
                "请直接回复答案" in text and "不要生成任何文件" in text,
            ),
        ]
        hint_map = {code: (severity, message) for code, severity, message in BA_TEMPLATE_HINTS}
        for code, passed in ba_checks:
            if not passed:
                severity, message = hint_map[code]
                report.warnings.append(Issue(severity, code, message))

    def _check_rubrics(self, report: TaskReport, text: str) -> None:
        if not re.search(r"(?m)^#\s+Rubrics\s*$", text):
            report.errors.append(Issue("error", "RUBRIC_HEADER", "缺少 `# Rubrics` 标题"))

        pass_rule_ok = "通过标准：所有 rubric 均须满足" in text and (
            "整体判定为不通过" in text or "整体判定为 FAIL" in text
        )
        if not pass_rule_ok:
            report.errors.append(Issue("error", "RUBRIC_PASS_RULE", "缺少规范的通过标准说明"))

        if "## 文件读取路径" not in text:
            report.errors.append(Issue("error", "RUBRIC_PATH_SECTION", "缺少 `## 文件读取路径` 段落"))

        path_bodies = self._extract_fence_bodies(text, expected_lang="path")
        if len(path_bodies) != 1:
            report.errors.append(
                Issue("error", "RUBRIC_PATH_BLOCK", f"`path` 代码块数量应为 1，当前为 {len(path_bodies)}")
            )
            path_lines: List[str] = []
        else:
            path_lines = [line.strip() for line in path_bodies[0].splitlines() if line.strip()]
            for path in path_lines:
                if not path.startswith("/meituan/"):
                    report.errors.append(
                        Issue("error", "RUBRIC_PATH_PREFIX", f"文件读取路径 `{path}` 应以 `/meituan/` 开头")
                    )
                if ".zip" in path.lower():
                    report.errors.append(Issue("error", "RUBRIC_PATH_ZIP", f"文件读取路径 `{path}` 不应引用 zip 文件"))
                if "*" in path and not path.endswith("/*"):
                    report.warnings.append(
                        Issue("warning", "RUBRIC_PATH_WILDCARD", f"文件读取路径 `{path}` 使用了通配符，建议仅使用目录级 `/*` 形式")
                    )
                if path.endswith("/") and "*" not in path:
                    report.warnings.append(
                        Issue("warning", "RUBRIC_PATH_DIRECTORY", f"文件读取路径 `{path}` 是目录，若能确定具体文件名则应改为文件路径")
                    )
            if len(path_lines) != len(set(path_lines)):
                report.warnings.append(Issue("warning", "RUBRIC_PATH_DUPLICATE", "文件读取路径中存在重复项"))

        json_bodies = self._extract_fence_bodies(text, expected_lang="json")
        if len(json_bodies) != 1:
            report.errors.append(
                Issue("error", "RUBRIC_JSON_BLOCK", f"`json` 代码块数量应为 1，当前为 {len(json_bodies)}")
            )
            return

        json_body = json_bodies[0]
        if re.search(r"\]\s*\[", json_body):
            report.errors.append(Issue("error", "RUBRIC_JSON_MULTI_ARRAY", "`json` 代码块中出现多个并列数组"))
            return

        try:
            payload = json.loads(json_body)
        except json.JSONDecodeError as exc:
            report.errors.append(Issue("error", "RUBRIC_JSON_PARSE", f"`json` 代码块无法解析：{exc.msg}"))
            return

        if not isinstance(payload, list):
            report.errors.append(Issue("error", "RUBRIC_JSON_TYPE", "`json` 代码块顶层必须是数组"))
            return

        if not payload:
            report.errors.append(Issue("error", "RUBRIC_JSON_EMPTY", "rubrics 数组不能为空"))
            return

        if len(payload) > 5:
            report.warnings.append(
                Issue("warning", "RUBRIC_TOO_MANY", f"rubrics 数量为 {len(payload)}，规范建议原则上不超过 5 条")
            )

        seen_ids: set[str] = set()
        file_refs_in_json: List[str] = []
        blank_count = None

        for index, item in enumerate(payload, start=1):
            if not isinstance(item, dict):
                report.errors.append(
                    Issue("error", "RUBRIC_ITEM_TYPE", f"第 {index} 条 rubric 不是对象，而是 `{type(item).__name__}`")
                )
                continue

            missing_fields = [field for field in ("id", "content", "weight") if field not in item]
            if missing_fields:
                report.errors.append(
                    Issue(
                        "error",
                        "RUBRIC_ITEM_FIELD",
                        f"第 {index} 条 rubric 缺少字段：" + "、".join(f"`{field}`" for field in missing_fields),
                    )
                )
                continue

            rubric_id = str(item["id"])
            content = str(item["content"])
            weight = item["weight"]

            if not re.fullmatch(r"\d{2}", rubric_id):
                report.warnings.append(
                    Issue("warning", "RUBRIC_ID_FORMAT", f"rubric id `{rubric_id}` 建议使用两位数字格式，如 `01`")
                )
            if rubric_id in seen_ids:
                report.errors.append(Issue("error", "RUBRIC_ID_DUPLICATE", f"rubric id `{rubric_id}` 重复"))
            seen_ids.add(rubric_id)

            if not content.strip():
                report.errors.append(Issue("error", "RUBRIC_CONTENT_EMPTY", f"rubric `{rubric_id}` 的 content 为空"))
            else:
                file_refs = FILE_TAG_RE.findall(content)
                file_exts = {Path(file_ref).suffix.lower() for file_ref in file_refs}
                if not re.match(r"^(唯一答案：|答案(?:内容)?需)", content):
                    report.warnings.append(
                        Issue(
                            "warning",
                            "BA_RUBRIC_PREFIX",
                            f"rubric `{rubric_id}` 的 content 建议以明确校验前缀开头，如 `唯一答案：`、`答案需` 或 `答案内容需`",
                        )
                    )
                elif self._is_descriptive_rubric(content) and DESCRIPTIVE_RUBRIC_BAD_PREFIX_RE.match(content):
                    report.errors.append(
                        Issue(
                            "error",
                            "BA_RUBRIC_BAD_WORDING",
                            f"rubric `{rubric_id}` 的描述型 content 句式不通或不够可判定，建议改成“答案需明确指出……”或“答案需提及……”这类直接描述核心要素的句式",
                        )
                    )
                if self._is_too_vague_descriptive_rubric(content):
                    report.warnings.append(
                        Issue(
                            "warning",
                            "BA_RUBRIC_TOO_VAGUE",
                            f"rubric `{rubric_id}` 的描述型 content 过于模糊，像“答案需分析合理”或“答案需结论完整”这类表述缺少可观察要点，建议改成可直接判定的要求句",
                        )
                    )
                ambiguous = [token for token in AMBIGUOUS_RUBRIC_TOKENS if token in content]
                if ambiguous:
                    report.warnings.append(
                        Issue(
                            "warning",
                            "RUBRIC_AMBIGUOUS",
                            f"rubric `{rubric_id}` 可能含模糊词：" + "、".join(f"`{token}`" for token in ambiguous),
                        )
                    )
                if any(token in content for token in PROHIBITED_MODEL_FILE_OP_TOKENS):
                    report.warnings.append(
                        Issue(
                            "warning",
                            "RUBRIC_MODEL_FILE_OP",
                            f"rubric `{rubric_id}` 不应要求模型自行检查路径或读取文件，应改为直接使用 `<file>...</file>` 引用内容",
                        )
                    )
                if "透明度" in content:
                    report.errors.append(Issue("error", "RUBRIC_TRANSPARENCY", f"rubric `{rubric_id}` 不应包含单元格透明度判断"))
                if content.count("<file>") > 2:
                    report.warnings.append(
                        Issue(
                            "warning",
                            "RUBRIC_NEEDS_SPLIT",
                            f"rubric `{rubric_id}` 可能同时判断了过多内容，建议进一步拆分",
                        )
                    )
                if ".zip" in content.lower():
                    report.errors.append(Issue("error", "RUBRIC_ZIP", f"rubric `{rubric_id}` 不应引用 zip 文件"))
                if ".csv" in file_exts and self._has_format_requirement(content):
                    report.warnings.append(
                        Issue(
                            "warning",
                            "RUBRIC_CSV_FORMAT",
                            f"rubric `{rubric_id}` 对 csv 文件提出了格式类要求，请确认是否应改用 xlsx 作为输出和参考答案格式",
                        )
                    )
                if ".xlsx" in file_exts:
                    if self._has_format_requirement(content) and not self._has_row_col_hint(content):
                        report.warnings.append(
                            Issue(
                                "warning",
                                "RUBRIC_XLSX_FORMAT_SCOPE",
                                f"rubric `{rubric_id}` 涉及 xlsx 格式判断，但未明确到列/行/单元格范围",
                            )
                        )
                    if "完全一致" in content and not self._has_format_requirement(content) and not any(token in content for token in ["数值", "内容"]):
                        report.warnings.append(
                            Issue(
                                "warning",
                                "RUBRIC_XLSX_COMPARE_SCOPE",
                                f"rubric `{rubric_id}` 比对 xlsx 时建议明确为“数值完全一致”或“内容完全一致”，避免把格式要求混入",
                            )
                        )
                    if any(token in content for token in CELL_FORMAT_REQUIREMENT_TOKENS) and "单元格格式" not in content:
                        report.warnings.append(
                            Issue(
                                "warning",
                                "RUBRIC_CELL_FORMAT_WORDING",
                                f"rubric `{rubric_id}` 涉及日期/百分比/分数/会计等格式时，建议明确写成“单元格格式”并给出具体要求",
                            )
                        )
                file_refs_in_json.extend(file_refs)

            if not isinstance(weight, (int, float)) or weight <= 0:
                report.errors.append(
                    Issue("error", "RUBRIC_WEIGHT", f"rubric `{rubric_id}` 的 weight 必须为正数，当前为 `{weight}`")
                )

        file_ref_set = set(file_refs_in_json)
        path_line_set = set(path_lines)
        if file_ref_set and not path_line_set:
            report.errors.append(Issue("error", "RUBRIC_FILE_REF_NO_PATH", "rubrics 使用了 `<file>`，但 `文件读取路径` 为空"))
        for file_ref in sorted(file_ref_set):
            if file_ref not in path_line_set:
                report.errors.append(
                    Issue(
                        "error",
                        "RUBRIC_FILE_REF_MISSING",
                        f"`<file>{file_ref}</file>` 没有出现在 `文件读取路径` 中",
                    )
                )
        for path in sorted(path_line_set):
            if path not in file_ref_set:
                report.warnings.append(
                    Issue(
                        "warning",
                        "RUBRIC_PATH_UNUSED",
                        f"文件读取路径 `{path}` 没有在 rubrics 的 `<file>` 引用中使用，请确认是否真的需要读取",
                    )
                )

        input_basenames = {
            Path(path).name
            for path in path_line_set
            if "/input/" in path and "*" not in path and Path(path).suffix
        }
        for path in sorted(path_line_set):
            if "/solution/" not in path or "*" in path:
                continue
            basename = Path(path).name
            if basename in input_basenames and "参考答案" not in basename:
                report.warnings.append(
                    Issue(
                        "warning",
                        "RUBRIC_SOLUTION_NAME_COLLISION",
                        f"solution 文件 `{basename}` 与 input 中存在重名，建议在 solution 文件名中加入“参考答案”以免混淆",
                    )
                )

    def _check_cross_file(self, report: TaskReport, instruction_text: str, rubrics_text: str) -> None:
        blank_count = instruction_text.count("______")
        json_bodies = self._extract_fence_bodies(rubrics_text, expected_lang="json")
        if len(json_bodies) != 1:
            return
        try:
            payload = json.loads(json_bodies[0])
        except json.JSONDecodeError:
            return
        if not isinstance(payload, list):
            return

        task_requirement = self._extract_task_requirement(instruction_text)
        rubric_contents = [str(item.get("content", "")) for item in payload if isinstance(item, dict)]
        joined_contents = "\n".join(rubric_contents)

        if blank_count > 0 and len(payload) != blank_count:
            report.warnings.append(
                Issue(
                    "warning",
                    "BA_FILL_BLANK_COUNT",
                    f"instruction 中有 {blank_count} 个填空槽，但 rubrics 有 {len(payload)} 条，请确认拆分粒度是否一致",
                )
            )

        if task_requirement:
            if "运营策略" in task_requirement and not any(token in joined_contents for token in ["运营策略", "策略"]):
                report.warnings.append(
                    Issue(
                        "warning",
                        "BA_RUBRIC_STRATEGY_DIMENSION",
                        "instruction 的任务要求明确要求回答“运营策略”，但 rubrics 未直接校验“策略/运营策略”这一答题维度，请确认是否把结论写死而遗漏题目要求",
                    )
                )
            if "正面" in task_requirement and "负面" in task_requirement and not any(token in joined_contents for token in ["正面", "负面"]):
                report.warnings.append(
                    Issue(
                        "warning",
                        "BA_RUBRIC_EFFECT_DIMENSION",
                        "instruction 的任务要求明确要求判断效果正负面，但 rubrics 未直接校验“正面/负面”这一答题维度，请确认是否遗漏题目要求",
                    )
                )
            self._check_rubric_strictness(report, task_requirement, rubric_contents)
            self._check_comparison_alignment(report, task_requirement, rubric_contents)
            self._check_open_analysis_prefix_alignment(report, task_requirement, rubric_contents)
            self._check_analysis_layers(report, task_requirement, rubric_contents)
            self._check_dwd_query_risk(report, instruction_text, task_requirement, rubric_contents)

    def _check_rubric_strictness(self, report: TaskReport, task_requirement: str, rubric_contents: List[str]) -> None:
        if not rubric_contents:
            return
        if not any(token in task_requirement for token in ANALYSIS_TASK_TOKENS + COMPARISON_TASK_TOKENS + OPEN_ANALYSIS_TASK_TOKENS):
            return
        if any(token in task_requirement for token in OPEN_ANALYSIS_TASK_TOKENS):
            return

        unique_answer_count = sum(1 for content in rubric_contents if content.startswith("唯一答案："))
        descriptive_count = sum(1 for content in rubric_contents if self._is_descriptive_rubric(content))
        if unique_answer_count == len(rubric_contents) and descriptive_count == 0:
            report.warnings.append(
                Issue(
                    "warning",
                    "BA_ANALYSIS_RUBRIC_TOO_STRICT",
                    "instruction 更像分析/比较题，但 rubrics 全部使用了 `唯一答案：`，可能把开放分析写死；请确认是否应改为 `答案需...`，或按逻辑层次拆分为可判定的分析要求",
                )
            )

    def _check_comparison_alignment(self, report: TaskReport, task_requirement: str, rubric_contents: List[str]) -> None:
        if not any(token in task_requirement for token in COMPARISON_TASK_TOKENS):
            return

        joined_contents = "\n".join(rubric_contents)
        if not any(token in joined_contents for token in ["比较", "对比", "分别", "分城市", "各城市", "北京", "上海", "城市"]):
            report.warnings.append(
                Issue(
                    "warning",
                    "BA_RUBRIC_COMPARE_DIMENSION",
                    "instruction 明确要求按城市/对象比较或分别分析，但 rubrics 未明显约束比较对象或分维度作答，请确认 instruction 与 rubrics 的逻辑是否自洽",
                )
            )

    def _check_open_analysis_prefix_alignment(self, report: TaskReport, task_requirement: str, rubric_contents: List[str]) -> None:
        if not any(token in task_requirement for token in OPEN_ANALYSIS_TASK_TOKENS):
            return
        if not rubric_contents:
            return

        unique_answer_count = sum(1 for content in rubric_contents if content.startswith("唯一答案："))
        descriptive_count = sum(1 for content in rubric_contents if re.match(r"^答案(?:内容)?需", content))
        if unique_answer_count == len(rubric_contents) and descriptive_count == 0:
            report.errors.append(
                Issue(
                    "error",
                    "BA_OPEN_ANALYSIS_UNIQUE_ANSWER",
                    "instruction 要求开放分析/归因推断（如推断事件、说明因果链路），但 rubrics 全部写成了 `唯一答案：`；开放分析部分至少应有一条 `答案需...` 或 `答案内容需...` rubric 直接校验分析维度",
                )
            )

    def _check_analysis_layers(self, report: TaskReport, task_requirement: str, rubric_contents: List[str]) -> None:
        if not any(token in task_requirement for token in ANALYSIS_TASK_TOKENS + OPEN_ANALYSIS_TASK_TOKENS):
            return

        layer_hits = {
            "fact": False,
            "analysis": False,
            "advice": False,
        }

        for content in rubric_contents:
            if any(token in content for token in ["指出", "识别", "明确指出", "城市", "时间段", "对象", "实施"]):
                layer_hits["fact"] = True
            if any(token in content for token in ["分析", "原因", "效果", "影响", "导致", "因为", "由于", "净收入", "需求端", "供给端"]):
                layer_hits["analysis"] = True
            if any(token in content for token in ["建议", "继续实施", "停止实施", "调整后再实施", "结论", "做法"]):
                layer_hits["advice"] = True

        if any(token in task_requirement for token in ["哪些城市", "哪些对象", "哪几个城市", "识别"]) and not layer_hits["fact"]:
            report.warnings.append(
                Issue(
                    "warning",
                    "BA_ANALYSIS_LAYER_FACT",
                    "分析题的任务要求包含识别对象/事实，但 rubrics 未明显覆盖“识别对象/事实”这一逻辑层次",
                )
            )
        if any(token in task_requirement for token in ["效果", "原因", "影响", "分析"]) and not layer_hits["analysis"]:
            report.warnings.append(
                Issue(
                    "warning",
                    "BA_ANALYSIS_LAYER_ANALYSIS",
                    "分析题的任务要求包含效果/原因/影响分析，但 rubrics 未明显覆盖“分析效果或原因”这一逻辑层次",
                )
            )
        if any(token in task_requirement for token in ["建议", "做法", "后续", "策略"]) and not layer_hits["advice"]:
            report.warnings.append(
                Issue(
                    "warning",
                    "BA_ANALYSIS_LAYER_ADVICE",
                    "分析题的任务要求包含结论/建议/策略做法，但 rubrics 未明显覆盖“结论或建议”这一逻辑层次",
                )
            )

        if len(rubric_contents) == 1 and sum(layer_hits.values()) >= 2:
            report.warnings.append(
                Issue(
                    "warning",
                    "BA_ANALYSIS_LAYER_SPLIT",
                    "分析题 rubrics 似乎把多个逻辑层次压在 1 条里，建议按“识别对象/事实”“分析效果或原因”“结论/建议”拆分",
                )
            )

    def _check_dwd_query_risk(
        self,
        report: TaskReport,
        instruction_text: str,
        task_requirement: str,
        rubric_contents: List[str],
    ) -> None:
        if "dwd_transaction.csv" not in instruction_text:
            return

        risk_text = "\n".join([task_requirement, *rubric_contents])
        hit_dimensions = [
            label
            for label, tokens in DWD_ONLY_DIMENSION_GROUPS
            if any(token in risk_text for token in tokens)
        ]
        if not hit_dimensions:
            return

        unique_answer_count = sum(1 for content in rubric_contents if content.startswith("唯一答案："))
        likely_full_scan = any(token in task_requirement for token in DWD_RISK_ACTION_TOKENS)
        all_unique = bool(rubric_contents) and unique_answer_count == len(rubric_contents)
        if not likely_full_scan and not all_unique:
            return

        dim_text = " / ".join(hit_dimensions)
        message = f"任务要求涉及 `{dim_text}` 等通常只能从 `dwd_transaction` 获取的明细维度"
        if likely_full_scan and all_unique:
            message += "，且同时带有“驱动/归因/比较/最高最低”等全量判定，rubrics 又全部使用了 `唯一答案：`"
        elif likely_full_scan:
            message += "，且同时带有“驱动/归因/比较/最高最低”等全量判定"
        else:
            message += "，rubrics 又全部使用了 `唯一答案：`"
        message += "；这类题在当前 Datasette 上容易因为 DWD 聚合查询触发 `SQL Interrupted`。请人工确认是否应改成 DWS 可支撑的问题、补充显式汇总结果，或把比较范围拆到可稳定验证的粒度。"
        report.warnings.append(Issue("warning", "BA_DWD_QUERY_RISK", message))

    def _is_descriptive_rubric(self, content: str) -> bool:
        return bool(re.match(r"^答案(?:内容)?需", content))

    def _is_too_vague_descriptive_rubric(self, content: str) -> bool:
        if not self._is_descriptive_rubric(content):
            return False
        if TOO_VAGUE_DESCRIPTIVE_RUBRIC_RE.match(content):
            return True

        stripped = re.sub(r"^答案(?:内容)?需", "", content).strip(" ：:，,。；;")
        if not stripped:
            return True
        if not any(token in stripped for token in VAGUE_REQUIREMENT_TOKENS):
            return False
        if any(token in stripped for token in CONCRETE_REQUIREMENT_HINTS):
            return False
        return len(stripped) <= 16

    def _extract_fence_bodies(self, text: str, expected_lang: str) -> List[str]:
        bodies: List[str] = []
        lines = text.splitlines()
        index = 0
        target_lang = expected_lang.lower()

        while index < len(lines):
            line = lines[index].strip()
            if not line.startswith("```"):
                index += 1
                continue

            raw_lang = line[3:].strip().split()[0] if line[3:].strip() else ""
            index += 1
            body_lines: List[str] = []
            while index < len(lines) and lines[index].strip() != "```":
                body_lines.append(lines[index])
                index += 1

            if raw_lang.lower() == target_lang and index < len(lines):
                bodies.append("\n".join(body_lines))

            index += 1

        return bodies

    def _has_format_requirement(self, content: str) -> bool:
        return any(token in content for token in FORMAT_REQUIREMENT_TOKENS)

    def _has_row_col_hint(self, content: str) -> bool:
        return bool(ROW_COL_HINT_RE.search(content))

    def _extract_task_requirement(self, text: str) -> str:
        match = TASK_REQUIREMENT_RE.search(text)
        if not match:
            return ""
        return re.sub(r"\s+", " ", match.group(1)).strip()

    def _looks_like_file_output_task(self, text: str) -> bool:
        positive_patterns = [
            r"输出[^。\n]{0,30}(文件|文件夹|目录)",
            r"生成[^。\n]{0,30}(文件|文件夹|目录)",
            r"创建[^。\n]{0,30}(文件|文件夹|目录)",
            r"修改[^。\n]{0,30}(文件|文件夹|目录)",
            r"保存[^。\n]{0,30}(文件|文件夹|目录)",
        ]
        negative_hints = ("不要", "无需", "不需要", "不必")
        for pattern in positive_patterns:
            for match in re.finditer(pattern, text):
                prefix = text[max(0, match.start() - 6):match.start()]
                if any(hint in prefix for hint in negative_hints):
                    continue
                return True
        return False


def format_text(root: Path, reports: List[TaskReport], scanned: int) -> str:
    error_count = sum(len(report.errors) for report in reports)
    warning_count = sum(len(report.warnings) for report in reports)
    problem_reports = [report for report in reports if report.errors or report.warnings]

    lines = [
        f"Scanned: {scanned}",
        f"Tasks with issues: {len(problem_reports)}",
        f"Errors: {error_count}",
        f"Warnings: {warning_count}",
        f"Root: {root}",
    ]

    if not problem_reports:
        lines.append("\nPASS: 未发现结构性或格式性问题。")
        return "\n".join(lines)

    for report in problem_reports:
        lines.append(f"\n[{report.task}] {report.path}")
        for issue in report.errors:
            lines.append(f"  - ERROR {issue.code}: {issue.message}")
        for issue in report.warnings:
            lines.append(f"  - WARNING {issue.code}: {issue.message}")
    return "\n".join(lines)


def format_json(root: Path, reports: List[TaskReport], scanned: int) -> str:
    payload = {
        "root": str(root),
        "scanned": scanned,
        "tasks_with_issues": sum(1 for report in reports if report.errors or report.warnings),
        "error_count": sum(len(report.errors) for report in reports),
        "warning_count": sum(len(report.warnings) for report in reports),
        "reports": [report.as_dict() for report in reports],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate BA evaluation data instruction.md and rubrics.md files.")
    parser.add_argument("--root", required=True, help="Absolute or relative path to the BA root directory.")
    parser.add_argument("--only", action="append", default=[], help="Only validate the given ba-xxx task id. Can be repeated.")
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
    if not root.exists() or not root.is_dir():
        print(f"ERROR: root directory does not exist: {root}", file=sys.stderr)
        return 2

    only = set(args.only) if args.only else None
    validator = Validator()
    reports = validator.validate_root(root, only=only)

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
