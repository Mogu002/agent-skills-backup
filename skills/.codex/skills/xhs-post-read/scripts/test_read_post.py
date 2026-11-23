#!/usr/bin/env python3

import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).parent))
from read_post import ReadError, load_initial_state, post_data, reject_error_page, select_note  # noqa: E402


def main() -> None:
    note_id = "6411cf99000000001300b6d9"
    state = {
        "note": {
            "noteDetailMap": {
                note_id: {
                    "note": {
                        "noteId": note_id,
                        "title": "fixture",
                        "desc": "brace } and the word undefined stay intact",
                        "type": "video",
                        "user": {"userId": "u1", "nickname": "reader"},
                        "imageList": [
                            {"urlDefault": "https://img.example/1.jpg"},
                            {"urlPre": "https://img.example/2.jpg"},
                        ],
                        "video": {
                            "media": {
                                "stream": {
                                    "h264": [
                                        {
                                            "masterUrl": "https://video.example/720.mp4",
                                            "backupUrls": [],
                                            "width": 1280,
                                            "height": 720,
                                        },
                                        {
                                            "masterUrl": "https://video.example/1080.mp4",
                                            "backupUrls": ["https://video.example/backup.mp4"],
                                            "width": 1920,
                                            "height": 1080,
                                        },
                                    ]
                                }
                            }
                        },
                    },
                    "comments": "undefined",
                }
            }
        }
    }
    html = (
        "<script>window.__INITIAL_STATE__="
        + json.dumps(state, ensure_ascii=False).replace('"undefined"', "undefined")
        + ";</script>"
    )
    url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token=secret"
    result = post_data(select_note(load_initial_state(html), url), url)
    assert result["content"] == "brace } and the word undefined stay intact"
    assert result["source_url"] == f"https://www.xiaohongshu.com/explore/{note_id}"
    assert result["image_urls"] == [
        "https://img.example/1.jpg",
        "https://img.example/2.jpg",
    ]
    assert result["video_urls"][0] == "https://video.example/1080.mp4"
    try:
        reject_error_page("https://www.xiaohongshu.com/login?redirectPath=x")
    except ReadError:
        pass
    else:
        raise AssertionError("login redirect was not rejected")


if __name__ == "__main__":
    main()
