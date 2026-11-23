"""Offline behavioral checks for favorites capture and resumable subtitle saves."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import batch
import extract


BV1, BV2 = "BV1234567890", "BVabcdefghij"


def page(number=1, items=(BV1,), more=False, total=1):
    return {"folder_id": "123", "page": number, "payload": {"code": 0, "data": {
        "info": {"id": 123, "media_count": total, "title": "收藏"}, "has_more": more,
        "medias": [{"id": n, "bvid": bvid, "type": 2, "title": bvid, "attr": 0}
                   for n, bvid in enumerate(items, 1)]}}}


def write_result(path, bvid):
    info = {"bvid": bvid, "cid": 42, "aid": 1, "page": 1, "duration": 4, "title": "测试"}
    text = extract.render_markdown(info, "zh", "中文", {}, [{"from": 0, "to": 4, "content": "正文"}], False)
    path.write_text(text, encoding="utf-8")
    return {"ok": True, "bvid": bvid, "cid": 42, "page": 1, "subtitle_count": 1,
            "count_matches": True, "timeline_valid": True, "timestamps_in_output": False,
            "secret_markers": False, "media_downloaded": False,
            "output_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


class BatchTests(unittest.TestCase):
    def test_folder_identity(self):
        self.assertEqual(batch.folder_id("https://space.bilibili.com/1/favlist?fid=123"), "123")
        for value in ("0", "../123", "https://evil.example/?fid=123", "https://space.bilibili.com/1/favlist"):
            with self.assertRaises(extract.SubtitleError):
                batch.folder_id(value)

    def test_paging_dedup_and_completeness(self):
        state = batch.new_state("123", False)
        batch.add_page(state, page(items=(BV1,), more=True, total=2))
        self.assertFalse(state["list_complete"])
        batch.add_page(state, page(2, (BV1, BV2), False, 2))
        self.assertTrue(state["list_complete"])
        self.assertEqual(len(state["entries"]), 2)

    def test_empty_middle_wrong_page_and_total_change(self):
        state = batch.new_state("123", False)
        for bad in (page(2), page(items=(), more=True)):
            with self.assertRaises(extract.SubtitleError):
                batch.add_page(state, bad)
        self.assertEqual(state["next_page"], 1)
        batch.add_page(state, page(more=True, total=2))
        with self.assertRaises(extract.SubtitleError):
            batch.add_page(state, page(2, (BV2,), False, 3))
        self.assertEqual(len(state["entries"]), 1)

    def test_hidden_items_and_unsupported_are_not_success(self):
        state = batch.new_state("123", False)
        batch.add_page(state, page(total=2))
        self.assertTrue(state["list_finished"])
        self.assertFalse(state["list_complete"])
        state = batch.new_state("123", False)
        value = page()
        value["payload"]["data"]["medias"][0]["type"] = 24
        batch.add_page(state, value)
        self.assertEqual(next(iter(state["entries"].values()))["status"], "unsupported")
        self.assertFalse(batch.summary(state)["ok"])

    @patch("batch.time.sleep")
    def test_limit_resume_and_modified_file(self, _sleep):
        state = batch.new_state("123", False)
        batch.add_page(state, page(items=(BV1, BV2), total=2))
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            def fake_run(args, **kwargs):
                target = Path(args[args.index("-o") + 1])
                bvid = extract.bvid_from(args[2])
                result = write_result(target, bvid)
                return SimpleNamespace(returncode=0, stdout=json.dumps(result), stderr="")
            with patch("batch.subprocess.run", side_effect=fake_run) as run:
                batch.run_videos(state, out, 1, False)
                self.assertEqual(run.call_count, 1)
                batch.run_videos(state, out, None, False)
                self.assertEqual(run.call_count, 2)
                self.assertTrue(batch.summary(state)["ok"])
                target = batch.output_path(out, BV1)
                target.write_text("changed", encoding="utf-8")
                batch.run_videos(state, out, None, False)
                self.assertEqual(run.call_count, 2)
                self.assertEqual(state["entries"][BV1]["status"], "conflict")
                self.assertEqual(target.read_text(), "changed")

    @patch("batch.time.sleep")
    def test_throttle_stops_queue_and_preserves_next(self, _sleep):
        state = batch.new_state("123", False)
        batch.add_page(state, page(items=(BV1, BV2), total=2))
        reply = SimpleNamespace(returncode=2, stdout="", stderr=json.dumps({"ok": False, "code": "THROTTLED"}))
        with tempfile.TemporaryDirectory() as temp, patch("batch.subprocess.run", return_value=reply) as run:
            self.assertEqual(batch.run_videos(state, Path(temp), None, False), "THROTTLED")
            self.assertEqual(run.call_count, 1)
            self.assertEqual(state["entries"][BV2]["status"], "pending")
            saved = json.loads((Path(temp) / "batch-state.json").read_text())
            self.assertEqual(saved["entries"][BV1]["status"], "throttled")

    @patch("batch.time.sleep")
    def test_existing_output_is_not_overwritten(self, _sleep):
        state = batch.new_state("123", False)
        batch.add_page(state, page())
        with tempfile.TemporaryDirectory() as temp, patch("batch.subprocess.run") as run:
            out = Path(temp)
            target = batch.output_path(out, BV1)
            target.write_text("existing", encoding="utf-8")
            batch.run_videos(state, out, None, False)
            run.assert_not_called()
            self.assertEqual(target.read_text(), "existing")
            self.assertEqual(state["entries"][BV1]["status"], "conflict")

    def test_browser_report_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            state = batch.new_state("123", False)
            batch.add_page(state, page())
            target = batch.output_path(out, BV1)
            result = write_result(target, BV1)
            report = out / "report.json"
            report.write_text(json.dumps(result))
            batch.import_results(state, out, [report])
            self.assertEqual(state["entries"][BV1]["status"], "ok")
            result["bvid"] = BV2
            report.write_text(json.dumps(result))
            with self.assertRaises(extract.SubtitleError):
                batch.import_results(state, out, [report])
            self.assertFalse(batch.verify_result({**result, "bvid": BV1}, target, BV1, True))

    def test_throttle_not_swallowed_by_subtitle_fallback(self):
        with patch("extract.api_json", side_effect=extract.SubtitleError("limit", "THROTTLED")), \
                patch("extract.request_bytes") as request:
            with self.assertRaises(extract.SubtitleError):
                extract.anonymous_tracks({"bvid": BV1, "cid": 42})
            request.assert_not_called()

    def test_cli_list_only_and_resumed_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            capture = out / "page.json"
            capture.write_text(json.dumps(page()))
            command = [sys.executable, str(Path(batch.__file__)), "123", "--output-dir", temp, "--list-only"]
            first = subprocess.run(command + ["--page-json", str(capture)], capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue(json.loads(first.stdout)["list_complete"])
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertFalse((out / ".batch.lock").exists())


if __name__ == "__main__":
    unittest.main()
