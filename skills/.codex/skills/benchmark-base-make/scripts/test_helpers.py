"""Offline behavior tests. Uses fake reads and local PDFs; never accesses a live Base."""
import sys
sys.dont_write_bytecode = True
import argparse, copy, json, pathlib, tempfile, unittest
from common import write_json, normalize
from snapshot import collect
from prepare_payloads import prepare
from verify_snapshot import verify
from generate_attachments import generate

FONT = None
POPPLER = None


def fixture():
    return {"schema_version": 1, "target": {"base_token": "fake", "table_id": "tblFake"},
            "complete": True, "timezone": "Asia/Shanghai",
            "fields": [{"id": "f_name", "name": "名称", "type": "text"},
                       {"id": "f_kind", "name": "分类", "type": "select", "multiple": False,
                        "options": [{"name": "年度报告"}]},
                       {"id": "f_file", "name": "附件", "type": "attachment"}],
            "records": {"old": {"f_name": "原公司", "f_kind": ["年度报告"], "f_file": []}}}


class FakeCLI:
    def __init__(self, pages):
        self.pages, self.offsets = iter(pages), []
    def call(self, args):
        if args[1] == "+field-list":
            return {"fields": fixture()["fields"]}
        self.offsets.append(int(args[args.index("--offset") + 1]))
        return next(self.pages)


def page(ids, more):
    return {"field_id_list": ["f_name", "f_kind", "f_file"], "record_id_list": ids,
            "data": [[r, ["年度报告"], []] for r in ids], "has_more": more,
            "timezone": "Asia/Shanghai", "rev": 1}


class WorkflowTests(unittest.TestCase):
    def test_complete_pagination_and_empty_more_rejected(self):
        cli = FakeCLI([page(["a", "b"], True), page(["c"], False)])
        result = collect(cli, "fake", "tblFake", 2)
        self.assertEqual(set(result["records"]), {"a", "b", "c"})
        self.assertEqual(cli.offsets, [0, 2])
        with self.assertRaises(ValueError):
            collect(FakeCLI([page([], True)]), "fake", "tblFake")

    def test_datetime_requires_observed_timezone_and_compares_instants(self):
        field = {"type": "datetime"}
        self.assertEqual(normalize("2024-01-01 09:00:00", field, "Asia/Shanghai"),
                         normalize("2024-01-01T01:00:00+00:00", field))
        with self.assertRaises(ValueError): normalize("2024-01-01 09:00:00", field)

    def test_duplicate_pagination_is_not_accepted(self):
        with self.assertRaises(ValueError):
            collect(FakeCLI([page(["a"], True), page(["a"], False)]), "fake", "tblFake")

    def plan(self):
        return {"schema_version": 1, "source": {"question_id": "Q-test", "record_id": "source",
                "target_urls_raw": ["from-source"]},
                "targets": [{"key": "test", "url": "from-source", "base_token": "fake",
                             "table_id": "tblFake", "snapshot_path": "before.json"}],
                "records": [{"key": "sample", "target": "test", "action": "create",
                             "fields": {"名称": "新公司", "分类": "年度报告"},
                             "match_fields": {"名称": "新公司"}}]}

    def test_target_selection_options_and_duplicate_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = pathlib.Path(temp); write_json(directory / "before.json", fixture())
            plan = self.plan()
            result = prepare(plan, directory)
            self.assertEqual(len(result[1]["test"]), 1)
            for broken in ["wrong-target", "unknown-option", "existing-key", "path-key", "duplicate-alias"]:
                bad = copy.deepcopy(plan)
                if broken == "wrong-target": bad["targets"][0]["url"] = "from-other-directory"
                if broken == "unknown-option": bad["records"][0]["fields"]["分类"] = "未注册选项"
                if broken == "existing-key":
                    bad["records"][0]["fields"]["名称"] = "原公司"; bad["records"][0]["match_fields"]["名称"] = "原公司"
                if broken == "path-key": bad["targets"][0]["key"] = "../../outside"
                if broken == "duplicate-alias": bad["records"][0]["fields"]["f_name"] = "重复别名"
                with self.subTest(broken=broken), self.assertRaises(ValueError): prepare(bad, directory)

    def test_allowlist_cannot_hide_unexpected_existing_changes(self):
        before = fixture(); after = copy.deepcopy(before)
        after["fields"].reverse()
        expect = {"expected_count": 1}
        self.assertEqual(verify(before, after, expect, pathlib.Path.cwd())["count"], 1)
        after["records"]["old"]["f_name"] = "意外改动"
        with self.assertRaises(ValueError): verify(before, after, expect, pathlib.Path.cwd())
        expect["allowed_existing_changes"] = {"old": ["f_name"]}
        with self.assertRaises(ValueError): verify(before, after, expect, pathlib.Path.cwd())
        expect["expected_records"] = {"old": {"f_name": "意外改动"}}
        self.assertEqual(verify(before, after, expect, pathlib.Path.cwd())["allowed_modified_records"], 1)

    def test_schema_change_and_unplanned_new_record_rejected(self):
        before = fixture(); after = copy.deepcopy(before)
        after["fields"][1]["options"].append({"name": "新口径"})
        with self.assertRaises(ValueError): verify(before, after, {"expected_count": 1}, pathlib.Path.cwd())
        after = copy.deepcopy(before); after["records"]["unplanned"] = after["records"]["old"].copy()
        with self.assertRaises(ValueError): verify(before, after, {"expected_count": 2}, pathlib.Path.cwd())

    def test_attachment_download_hash_and_retained_tokens(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp); local = root / "sample.pdf"; downloaded = root / "download.pdf"
            local.write_bytes(b"good"); downloaded.write_bytes(b"good")
            before = fixture(); after = copy.deepcopy(before)
            after["records"]["old"]["f_file"] = [{"file_token": "current", "name": "sample.pdf", "size": 4}]
            write_json(root / "receipt.json", {"ok": True, "data": {"downloaded": [{"file_token": "current",
                       "record_id": "old", "field_id": "f_file", "saved_path": str(downloaded)}]}})
            item = {"record_id": "old", "field_id": "f_file", "local_path": "sample.pdf", "exact_count": 1,
                    "downloaded_path": "download.pdf", "download_receipt_path": "receipt.json"}
            expect = {"expected_count": 1, "allowed_existing_changes": {"old": ["f_file"]}, "attachments": [item]}
            self.assertTrue(verify(before, after, expect, root)["attachment_checks"][0]["download_hash_verified"])
            downloaded.write_bytes(b"evil")
            with self.assertRaises(ValueError): verify(before, after, expect, root)
            downloaded.write_bytes(b"good")
            before["records"]["old"]["f_file"] = [{"file_token": "retained", "name": "older.pdf", "size": 9}]
            with self.assertRaises(ValueError): verify(before, after, expect, root)

    def test_actual_text_and_scan_generation_and_overflow(self):
        if not FONT or not POPPLER:
            self.skipTest("Pass --font-path and --poppler to exercise local PDF generation")
        with tempfile.TemporaryDirectory() as temp:
            page_spec = {"title": "评测年报", "paragraphs": ["公司全称：示例科技股份有限公司", "报告期：2024年度"]}
            spec = {"synthetic_allowed": True, "documents": [
                {"key": "text", "filename": "text.pdf", "synthetic": True, "scan": False, "pages": [page_spec]},
                {"key": "scan", "filename": "scan.pdf", "synthetic": True, "scan": True, "pages": [page_spec]}]}
            result = generate(spec, temp, FONT, POPPLER)
            self.assertFalse(result[0]["pure_image"]); self.assertTrue(result[1]["pure_image"])
            from pypdf import PdfReader
            self.assertIn("示例科技", PdfReader(pathlib.Path(temp) / "text.pdf").pages[0].extract_text())
            with self.assertRaises(ValueError): generate(spec, temp, FONT, POPPLER)
            bad = copy.deepcopy(spec); bad["documents"] = [{"key": "overflow", "filename": "overflow.pdf", "synthetic": True,
                      "pages": [{"title": "长文本", "paragraphs": ["不可裁切内容" * 2000]}]}]
            with self.assertRaises(ValueError): generate(bad, temp, FONT, POPPLER)
            self.assertFalse((pathlib.Path(temp) / "overflow.pdf").exists())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-path"); parser.add_argument("--poppler")
    args, remaining = parser.parse_known_args()
    FONT, POPPLER = args.font_path, args.poppler
    unittest.main(argv=[sys.argv[0]] + remaining)
