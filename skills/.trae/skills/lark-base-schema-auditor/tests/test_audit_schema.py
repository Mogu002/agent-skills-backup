import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "audit_schema.py"
SPEC = importlib.util.spec_from_file_location("audit_schema", SCRIPT_PATH)
assert SPEC and SPEC.loader
AUDITOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDITOR
SPEC.loader.exec_module(AUDITOR)


class AuditSchemaTest(unittest.TestCase):
    def test_extracts_target_and_requirements_from_record_list_envelope(self):
        payload = {
            "ok": True,
            "data": {
                "fields": ["Target Base", "Schema"],
                "data": [
                    [
                        "[Example](https://example.larkoffice.com/base/base_token)",
                        "【Table】Survey\n1. Name（文本）\n2. Status（单选：Open/Done）",
                    ]
                ],
                "record_id_list": ["rec_example"],
            },
        }

        result = AUDITOR.extract_source_inputs(payload, "Target Base", "Schema")

        self.assertEqual(
            result["target_url"],
            "https://example.larkoffice.com/base/base_token",
        )
        self.assertEqual(result["record_id"], "rec_example")
        self.assertEqual(
            [field["canonical_type"] for field in result["requirements"]],
            ["text/plain", "select/single"],
        )

    def test_semantic_mapping_finds_two_specialized_number_mismatches(self):
        requirements = """【Table】Survey
1. 受访者姓名（文本）
2. 所属用户群组（群组）
3. 宝宝年龄段（单选：孕期/0-1岁/1-3岁/3-6岁）
4. 月均母婴消费（货币）
5. 关注品类（多选：奶粉/纸尿裤/辅食/玩具/服饰）
6. 调研进度（进度）
7. 所在地区（地理位置）
8. 登记日期（日期）
9. 满意度评分（评分 & NPS）
10. 联系电话（电话号码）"""
        fields = [
            {"id": "f1", "name": "User Group", "type": "group_chat", "multiple": True},
            {
                "id": "f2",
                "name": "Survey Progress",
                "type": "number",
                "style": {"type": "plain"},
            },
            {"id": "f3", "name": "Registration Date", "type": "datetime"},
            {"id": "f4", "name": "Location", "type": "location"},
            {
                "id": "f5",
                "name": "Contact Phone",
                "type": "text",
                "style": {"type": "phone"},
            },
            {"id": "f6", "name": "Respondent Name", "type": "text"},
            {
                "id": "f7",
                "name": "Categories",
                "type": "select",
                "multiple": True,
            },
            {
                "id": "f8",
                "name": "Monthly Spending",
                "type": "number",
                "style": {"type": "currency"},
            },
            {"id": "f9", "name": "Baby Age", "type": "select", "multiple": False},
            {
                "id": "f10",
                "name": "Satisfaction",
                "type": "number",
                "style": {"type": "plain"},
            },
        ]
        mapping = {
            "受访者姓名": "Respondent Name",
            "所属用户群组": "User Group",
            "宝宝年龄段": "Baby Age",
            "月均母婴消费": "Monthly Spending",
            "关注品类": "Categories",
            "调研进度": "Survey Progress",
            "所在地区": "Location",
            "登记日期": "Registration Date",
            "满意度评分": "Satisfaction",
            "联系电话": "Contact Phone",
        }

        result = AUDITOR.audit_schema(requirements, fields, mapping)

        self.assertFalse(result["compliant"])
        self.assertEqual(result["summary"]["matched"], 8)
        self.assertEqual(result["summary"]["type_mismatches"], 2)
        mismatches = {
            item["expected_name"]: item["actual_type"]
            for item in result["fields"]
            if item["status"] == "type_mismatch"
        }
        self.assertEqual(
            mismatches,
            {
                "调研进度": "number/plain",
                "满意度评分": "number/plain",
            },
        )

    def test_extra_fields_are_strict_by_default_and_can_be_allowed(self):
        requirements = "1. Name（文本）"
        fields = [
            {"id": "f1", "name": "Name", "type": "text"},
            {"id": "f2", "name": "Notes", "type": "text"},
        ]

        strict = AUDITOR.audit_schema(requirements, fields)
        relaxed = AUDITOR.audit_schema(requirements, fields, allow_extra=True)

        self.assertFalse(strict["compliant"])
        self.assertTrue(relaxed["compliant"])
        self.assertEqual(strict["summary"]["unexpected"], 1)

    def test_option_check_is_opt_in(self):
        requirements = "1. Status（单选：Open/Done）"
        fields = [
            {
                "id": "f1",
                "name": "Status",
                "type": "select",
                "multiple": False,
                "options": [{"name": "Open"}, {"name": "Closed"}],
            }
        ]

        type_only = AUDITOR.audit_schema(requirements, fields)
        with_options = AUDITOR.audit_schema(requirements, fields, check_options=True)

        self.assertTrue(type_only["compliant"])
        self.assertFalse(with_options["compliant"])
        self.assertEqual(with_options["summary"]["option_mismatches"], 1)

    def test_unknown_requirement_type_is_not_silently_accepted(self):
        result = AUDITOR.audit_schema(
            "1. Workflow（流程）",
            [{"id": "f1", "name": "Workflow", "type": "not_support"}],
        )

        self.assertFalse(result["compliant"])
        self.assertEqual(result["summary"]["unsupported_requirements"], 1)

    def test_duplicate_actual_mapping_is_rejected(self):
        with self.assertRaisesRegex(
            AUDITOR.AuditInputError,
            "mapped to more than one requirement",
        ):
            AUDITOR.audit_schema(
                "1. First（文本）\n2. Second（文本）",
                [{"id": "f1", "name": "Shared", "type": "text"}],
                {"First": "Shared", "Second": "Shared"},
            )

    def test_missing_explicit_mapping_target_is_rejected(self):
        with self.assertRaisesRegex(AUDITOR.AuditInputError, "was not found"):
            AUDITOR.audit_schema(
                "1. Name（文本）",
                [{"id": "f1", "name": "Actual Name", "type": "text"}],
                {"Name": "Typo"},
            )

    def test_cli_returns_one_for_completed_audit_with_differences(self):
        source = {
            "ok": True,
            "data": {
                "fields": ["Target", "Requirements"],
                "data": [
                    [
                        "https://example.larkoffice.com/base/base_token",
                        "1. Progress（进度）",
                    ]
                ],
                "record_id_list": ["rec_example"],
            },
        }
        actual = {
            "ok": True,
            "data": {
                "fields": [
                    {
                        "id": "f1",
                        "name": "Progress",
                        "type": "number",
                        "style": {"type": "plain"},
                    }
                ]
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "source.json"
            actual_path = root / "actual.json"
            source_path.write_text(json.dumps(source), encoding="utf-8")
            actual_path.write_text(json.dumps(actual), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "audit",
                    "--record-file",
                    str(source_path),
                    "--target-field",
                    "Target",
                    "--requirements-field",
                    "Requirements",
                    "--actual-file",
                    str(actual_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(json.loads(completed.stdout)["summary"]["type_mismatches"], 1)
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
