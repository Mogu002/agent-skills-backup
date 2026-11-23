#!/usr/bin/env python3
"""Probe burned-in subtitles, run Paraformer, render outputs, and validate them."""

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
import time
import wave
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path


PUNCTUATION_RE = re.compile(r"[\s，。！？、,.!?：:；;‘’“”\-—_()（）\[\]【】]")
TIME_RE = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s+-->\s+"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})$"
)


class TranscriptError(RuntimeError):
    pass


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def key(text: str) -> str:
    return PUNCTUATION_RE.sub("", text).lower()


def stamp(value: float, comma: bool = False) -> str:
    milliseconds = round(max(0, value) * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{',' if comma else '.'}{milliseconds:03d}"


def seconds(parts: tuple[str, ...]) -> float:
    hours, minutes, secs, milliseconds = map(int, parts)
    return hours * 3600 + minutes * 60 + secs + milliseconds / 1000


def similar(left: str, right: str) -> bool:
    a, b = key(left), key(right)
    return bool(a and b) and (a in b or b in a or SequenceMatcher(None, a, b).ratio() >= 0.84)


def frame_text(row: dict, min_confidence: float = 0.45) -> tuple[str, float]:
    candidates = []
    for item in row.get("observations", []):
        text = clean(str(item.get("text", "")))
        confidence = float(item.get("confidence", 0))
        center = float(item.get("x", 0)) + float(item.get("width", 0)) / 2
        width = float(item.get("width", 0))
        position_ok = (0.30 <= center <= 0.70 and width >= 0.05) or width >= 0.12
        if confidence >= min_confidence and len(key(text)) >= 2 and position_ok:
            candidates.append(item | {"text": text, "confidence": confidence})
    candidates.sort(key=lambda item: (-float(item.get("y", 0)), float(item.get("x", 0))))
    candidates = candidates[:2]
    return clean(" ".join(item["text"] for item in candidates)), max(
        (item["confidence"] for item in candidates), default=0.0
    )


def read_frames(path: Path) -> list[dict]:
    frames = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise TranscriptError(f"invalid Vision JSONL at line {line_number}") from error
        text, confidence = frame_text(row)
        frames.append({"time": float(row["timestamp"]), "text": text, "confidence": confidence})
    if not frames:
        raise TranscriptError("Vision produced no frame records")
    return frames


def burned_subtitle_decision(frames: list[dict], duration: float, min_coverage: float) -> dict:
    texts = [frame["text"] for frame in frames if frame["text"]]
    normalized = [key(text) for text in texts]
    counts = Counter(normalized)
    coverage = len(texts) / len(frames)
    unique = len(counts)
    dominant_ratio = max(counts.values(), default=0) / max(1, len(texts))
    longest = max((len(value) for value in normalized), default=0)

    if duration <= 6:
        accepted = coverage >= max(0.30, min_coverage) and unique >= 1 and longest >= 4
        reason = "short_video_text_coverage" if accepted else "short_video_insufficient_text"
    elif duration <= 15:
        accepted = coverage >= max(0.20, min_coverage) and unique >= 2
        reason = "short_video_changing_text" if accepted else "short_video_insufficient_changes"
    else:
        required_frames = max(3, math.ceil(len(frames) * min_coverage))
        accepted = len(texts) >= required_frames and unique >= 3 and dominant_ratio <= 0.80
        reason = "changing_bottom_text_detected" if accepted else "no_reliable_burned_subtitles"

    return {
        "route": "vision" if accepted else "paraformer",
        "reason": reason,
        "probe_frame_count": len(frames),
        "text_frame_count": len(texts),
        "text_frame_coverage": round(coverage, 4),
        "unique_text_count": unique,
        "dominant_text_ratio": round(dominant_ratio, 4),
        "minimum_coverage": min_coverage,
    }


def command_probe(args: argparse.Namespace) -> None:
    decision = burned_subtitle_decision(read_frames(args.raw), args.duration, args.min_coverage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(decision["route"])


def command_decision(args: argparse.Namespace) -> None:
    payload = {}
    if args.preserve and args.output.is_file():
        payload = json.loads(args.output.read_text(encoding="utf-8"))
    payload.update({"route": args.route, "reason": args.reason, "override": args.override})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge_vision_frames(frames: list[dict], fps: float) -> list[dict]:
    step = 1 / fps
    groups, current = [], []
    for frame in frames:
        if not frame["text"]:
            if current and frame["time"] - current[-1]["time"] > step:
                groups.append(current)
                current = []
            continue
        if current and frame["time"] - current[-1]["time"] <= step * 2 and similar(
            current[-1]["text"], frame["text"]
        ):
            current.append(frame)
        else:
            if current:
                groups.append(current)
            current = [frame]
    if current:
        groups.append(current)

    segments = []
    for group in groups:
        variants = Counter(item["text"] for item in group)
        text = max(variants, key=lambda value: (variants[value], len(key(value))))
        confidence = max(item["confidence"] for item in group)
        if len(key(text)) < 2 or (len(group) == 1 and confidence < 0.80 and len(key(text)) < 4):
            continue
        segments.append({
            "start": group[0]["time"],
            "end": group[-1]["time"] + step,
            "text": text,
            "frames": len(group),
            "confidence": round(confidence, 4),
        })
    return segments


def coverage_seconds(segments: list[dict], duration: float) -> float:
    if not segments or duration <= 0:
        return 0.0
    total, start, end = 0.0, segments[0]["start"], segments[0]["end"]
    for item in segments[1:]:
        if item["start"] <= end:
            end = max(end, item["end"])
        else:
            total += end - start
            start, end = item["start"], item["end"]
    return min(1.0, (total + end - start) / duration)


def clamp_segments(segments: list[dict], duration: float) -> list[dict]:
    result = []
    for item in segments:
        start = max(0.0, float(item["start"]))
        end = min(duration, float(item["end"]))
        text = clean(str(item["text"]))
        if start < duration and end >= start and text:
            result.append(item | {"start": start, "end": end, "text": text})
    return result


def write_outputs(output: Path, *, engine: str, method: str, source: str, title: str,
                  duration: float, segments: list[dict], details: dict) -> dict:
    segments = clamp_segments(segments, duration)
    if not segments:
        raise TranscriptError(f"{engine} produced no usable subtitle segments")
    output.mkdir(parents=True, exist_ok=True)
    coverage = coverage_seconds(segments, duration)
    payload = {
        "engine": engine,
        "method": method,
        "source": source,
        "language": "zh",
        "media_duration_seconds": duration,
        "subtitle_coverage": round(coverage, 4),
        "segment_count": len(segments),
        "details": details,
        "segments": segments,
    }
    (output / "transcript.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    blocks = []
    for index, item in enumerate(segments, 1):
        blocks.append(
            f"{index}\n{stamp(item['start'], True)} --> {stamp(item['end'], True)}\n{item['text']}"
        )
    (output / "transcript.srt").write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    (output / "transcript.txt").write_text(
        "\n".join(item["text"] for item in segments) + "\n", encoding="utf-8"
    )
    notice = (
        "本文由 Apple Vision 从视频画面的烧录字幕自动识别，未经逐句人工校对。"
        if method == "burned_subtitle_ocr"
        else "本文由 sherpa-onnx INT8 Paraformer 从音轨自动转写，未经逐句人工校对。"
    )
    lines = [
        "---",
        f"source: {json.dumps(source, ensure_ascii=False)}",
        f"engine: {json.dumps(engine, ensure_ascii=False)}",
        f"method: {json.dumps(method, ensure_ascii=False)}",
        "language: zh",
        f"subtitle_count: {len(segments)}",
        f"media_duration_seconds: {duration}",
        f"subtitle_coverage: {round(coverage, 4)}",
        f"generated_at: {json.dumps(datetime.now(timezone.utc).isoformat())}",
        "automatic_transcript: true",
        "---",
        "",
        f"# {title}",
        "",
        f"> {notice}",
        "",
        "## 带时间戳全文",
        "",
    ]
    lines.extend(f"- [{stamp(x['start'])} → {stamp(x['end'])}] {x['text']}" for x in segments)
    (output / "transcript.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def command_vision(args: argparse.Namespace) -> None:
    frames = read_frames(args.raw)
    segments = merge_vision_frames(frames, args.fps)
    payload = write_outputs(
        args.output, engine="Apple Vision VNRecognizeTextRequest",
        method="burned_subtitle_ocr", source=args.source, title=args.title,
        duration=args.duration, segments=segments, details={"fps": args.fps, "crop_ratio": args.crop_ratio},
    )
    unique = len({key(item["text"]) for item in payload["segments"]})
    if args.duration <= 6:
        quality_ok = unique >= 1 and payload["subtitle_coverage"] >= max(0.30, args.min_coverage)
    elif args.duration <= 15:
        quality_ok = unique >= 2 and payload["subtitle_coverage"] >= max(0.20, args.min_coverage)
    else:
        quality_ok = unique >= 3 and payload["subtitle_coverage"] >= args.min_coverage
    if not quality_ok:
        raise TranscriptError(
            f"Vision result failed quality gate: coverage={payload['subtitle_coverage']}, unique={unique}"
        )
    print(json.dumps({"segment_count": payload["segment_count"], "coverage": payload["subtitle_coverage"]}))


def command_paraformer(args: argparse.Namespace) -> None:
    try:
        import numpy as np
        import sherpa_onnx
    except ImportError as error:
        raise TranscriptError("sherpa-onnx and numpy are required; run bootstrap.sh --install") from error

    recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
        paraformer=str(args.model), tokens=str(args.tokens), num_threads=args.threads
    )
    config = sherpa_onnx.VadModelConfig()
    config.silero_vad.model = str(args.vad)
    config.silero_vad.threshold = 0.5
    config.silero_vad.min_silence_duration = 0.35
    config.silero_vad.min_speech_duration = 0.25
    config.silero_vad.max_speech_duration = 15
    config.sample_rate = 16_000
    vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=120)
    results = []
    started = time.monotonic()

    def decode_ready() -> None:
        while not vad.empty():
            segment = vad.front
            samples = np.asarray(segment.samples, dtype=np.float32)
            start = segment.start / config.sample_rate
            stream = recognizer.create_stream()
            stream.accept_waveform(config.sample_rate, samples)
            recognizer.decode_stream(stream)
            text = stream.result.text.strip()
            if text:
                results.append({
                    "start": start,
                    "end": start + len(samples) / config.sample_rate,
                    "text": text,
                })
            vad.pop()

    with wave.open(str(args.wav), "rb") as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, 16_000):
            raise TranscriptError("expected 16 kHz mono PCM s16le WAV")
        window = config.silero_vad.window_size
        while raw := source.readframes(window):
            samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
            if len(samples) < window:
                samples = np.pad(samples, (0, window - len(samples)))
            vad.accept_waveform(samples)
            decode_ready()
    vad.flush()
    decode_ready()
    elapsed = round(time.monotonic() - started, 3)
    payload = write_outputs(
        args.output, engine=f"sherpa-onnx {sherpa_onnx.__version__} + INT8 Paraformer",
        method="audio_asr", source=args.source, title=args.title, duration=args.duration,
        segments=results,
        details={"model": args.model.name, "vad": args.vad.name, "threads": args.threads, "elapsed_seconds": elapsed},
    )
    print(json.dumps({"segment_count": payload["segment_count"], "elapsed_seconds": elapsed}))


def parse_srt(path: Path) -> list[dict]:
    blocks = re.split(r"\r?\n\s*\r?\n", path.read_text(encoding="utf-8-sig").strip())
    subtitles, previous = [], -1.0
    for position, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if len(lines) < 3 or not (match := TIME_RE.match(lines[1].strip())):
            raise TranscriptError(f"invalid SRT block {position}")
        start, end = seconds(match.groups()[:4]), seconds(match.groups()[4:])
        text = clean(" ".join(lines[2:]))
        if start < previous or end < start or not text:
            raise TranscriptError(f"invalid SRT timeline/text at block {position}")
        subtitles.append({"start": start, "end": end, "text": text})
        previous = start
    return subtitles


def command_validate(args: argparse.Namespace) -> None:
    required = ["decision.json", "transcript.srt", "transcript.txt", "transcript.json", "transcript.md"]
    for name in required:
        if not (args.output / name).is_file() or not (args.output / name).stat().st_size:
            raise TranscriptError(f"missing or empty output: {name}")
    decision = json.loads((args.output / "decision.json").read_text(encoding="utf-8"))
    payload = json.loads((args.output / "transcript.json").read_text(encoding="utf-8"))
    srt = parse_srt(args.output / "transcript.srt")
    segments = payload.get("segments", [])
    if not segments or len(srt) != len(segments) or payload.get("segment_count") != len(segments):
        raise TranscriptError("JSON and SRT subtitle counts differ")
    markdown = (args.output / "transcript.md").read_text(encoding="utf-8")
    if f"subtitle_count: {len(segments)}" not in markdown or "automatic_transcript: true" not in markdown:
        raise TranscriptError("Markdown metadata does not match transcript")
    expected_route = "vision" if payload.get("method") == "burned_subtitle_ocr" else "paraformer"
    if decision.get("route") != expected_route:
        raise TranscriptError("decision route and transcript engine differ")
    duration = float(payload["media_duration_seconds"])
    if srt[-1]["end"] > duration + 0.001:
        raise TranscriptError("last subtitle exceeds media duration")

    longest_run = 1
    run_start, run = srt[0]["start"], 1
    for previous, current in zip(srt, srt[1:]):
        if key(previous["text"]) == key(current["text"]):
            run += 1
            if run >= 5 and current["end"] - run_start >= 10:
                raise TranscriptError("excessive consecutive repeated subtitles")
        else:
            longest_run = max(longest_run, run)
            run, run_start = 1, current["start"]
    longest_run = max(longest_run, run)
    digest = hashlib.sha256((args.output / "transcript.md").read_bytes()).hexdigest()
    print(json.dumps({
        "ok": True, "route": expected_route, "subtitle_count": len(segments),
        "timeline_valid": True, "longest_consecutive_identical": longest_run,
        "transcript_md_sha256": digest,
    }, ensure_ascii=False))


def command_self_check(_: argparse.Namespace) -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        changing = root / "changing.jsonl"
        fixed = root / "fixed.jsonl"

        def record(index: int, text: str) -> str:
            observations = [] if not text else [{
                "text": text, "confidence": 0.99, "x": 0.3, "y": 0.1, "width": 0.4, "height": 0.2,
            }]
            return json.dumps({"frame": f"{index:03d}.jpg", "timestamp": index, "observations": observations}, ensure_ascii=False)

        changing.write_text("\n".join(record(i, f"字幕第{i // 2}句") for i in range(12)) + "\n", encoding="utf-8")
        fixed.write_text("\n".join(record(i, "固定水印") for i in range(12)) + "\n", encoding="utf-8")
        assert burned_subtitle_decision(read_frames(changing), 120, 0.15)["route"] == "vision"
        assert burned_subtitle_decision(read_frames(fixed), 120, 0.15)["route"] == "paraformer"

        decision_path = root / "decision.json"
        decision_path.write_text('{"probe_frame_count": 12, "route": "vision"}\n', encoding="utf-8")
        command_decision(argparse.Namespace(
            output=decision_path, route="paraformer", reason="fallback", override=False, preserve=True
        ))
        assert json.loads(decision_path.read_text(encoding="utf-8"))["probe_frame_count"] == 12

        output = root / "out"
        payload = write_outputs(
            output, engine="Apple Vision VNRecognizeTextRequest", method="burned_subtitle_ocr",
            source="sample.mp4", title="Sample", duration=12,
            segments=merge_vision_frames(read_frames(changing), 1), details={"self_check": True},
        )
        assert payload["segment_count"] >= 3
        command_decision(argparse.Namespace(
            output=output / "decision.json", route="vision", reason="self_check", override=True, preserve=False
        ))
        command_validate(argparse.Namespace(output=output))
    print(json.dumps({"ok": True, "self_check": True}))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    commands = value.add_subparsers(dest="command", required=True)

    probe = commands.add_parser("probe")
    probe.add_argument("raw", type=Path)
    probe.add_argument("--output", type=Path, required=True)
    probe.add_argument("--duration", type=float, required=True)
    probe.add_argument("--min-coverage", type=float, default=0.15)
    probe.set_defaults(function=command_probe)

    decision = commands.add_parser("decision")
    decision.add_argument("--output", type=Path, required=True)
    decision.add_argument("--route", choices=("vision", "paraformer"), required=True)
    decision.add_argument("--reason", required=True)
    decision.add_argument("--override", action="store_true")
    decision.add_argument("--preserve", action="store_true")
    decision.set_defaults(function=command_decision)

    vision = commands.add_parser("vision")
    vision.add_argument("raw", type=Path)
    vision.add_argument("--output", type=Path, required=True)
    vision.add_argument("--fps", type=float, default=2)
    vision.add_argument("--crop-ratio", type=float, default=0.35)
    vision.add_argument("--min-coverage", type=float, default=0.15)
    vision.add_argument("--source", required=True)
    vision.add_argument("--title", required=True)
    vision.add_argument("--duration", type=float, required=True)
    vision.set_defaults(function=command_vision)

    paraformer = commands.add_parser("paraformer")
    paraformer.add_argument("wav", type=Path)
    paraformer.add_argument("--model", type=Path, required=True)
    paraformer.add_argument("--tokens", type=Path, required=True)
    paraformer.add_argument("--vad", type=Path, required=True)
    paraformer.add_argument("--output", type=Path, required=True)
    paraformer.add_argument("--source", required=True)
    paraformer.add_argument("--title", required=True)
    paraformer.add_argument("--duration", type=float, required=True)
    paraformer.add_argument("--threads", type=int, default=4)
    paraformer.set_defaults(function=command_paraformer)

    validate = commands.add_parser("validate")
    validate.add_argument("--output", type=Path, required=True)
    validate.set_defaults(function=command_validate)

    self_check = commands.add_parser("self-check")
    self_check.set_defaults(function=command_self_check)
    return value


def main() -> None:
    args = parser().parse_args()
    try:
        if hasattr(args, "min_coverage") and not 0 < args.min_coverage <= 1:
            raise TranscriptError("--min-coverage must be in (0, 1]")
        args.function(args)
    except (TranscriptError, OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
