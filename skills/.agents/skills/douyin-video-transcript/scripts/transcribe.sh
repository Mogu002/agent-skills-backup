#!/usr/bin/env bash
set -euo pipefail
unset PYTHONHOME PYTHONPATH

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PREFIX="${XDG_DATA_HOME:-${HOME}/.local/share}/douyin-video-transcript"
OUTPUT_DIR="./douyin-transcript-output"
TITLE="Douyin video transcript"
ENGINE="auto"
COOKIES_BROWSER=""
CROP_RATIO="0.35"
OCR_FPS="2"
OCR_MIN_COVERAGE="0.15"
PROBE_SAMPLES="48"
THREADS="4"
OVERWRITE=0
KEEP_AUDIO=0
DRY_RUN=0
SOURCE=""

usage() {
  cat <<'EOF'
Usage: transcribe.sh SOURCE [options]

SOURCE may be a Douyin URL/video ID or a local audio/video file.

Options:
  --output-dir DIR              Output directory (default: ./douyin-transcript-output)
  --title TEXT                  Markdown title
  --engine auto|vision|paraformer
  --cookies-from-browser NAME   Explicitly use yt-dlp browser cookies
  --crop-ratio NUMBER           Bottom video fraction for OCR (default: 0.35)
  --ocr-fps NUMBER              Full Vision OCR frame rate (default: 2)
  --ocr-min-coverage NUMBER     Detection/quality threshold (default: 0.15)
  --probe-samples NUMBER        Approximate uniformly sampled frames (default: 48)
  --threads NUMBER              Paraformer CPU threads (default: 4)
  --prefix DIR                  Isolated toolchain prefix
  --overwrite                   Overwrite only known transcript outputs
  --keep-audio                  Keep normalized.wav when Paraformer is selected
  --dry-run                     Validate tools/options and print the plan
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then usage; exit 0; fi
[[ $# -gt 0 ]] || { usage >&2; exit 2; }
SOURCE="$1"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
    --title) TITLE="${2:-}"; shift 2 ;;
    --engine) ENGINE="${2:-}"; shift 2 ;;
    --cookies-from-browser) COOKIES_BROWSER="${2:-}"; shift 2 ;;
    --crop-ratio) CROP_RATIO="${2:-}"; shift 2 ;;
    --ocr-fps) OCR_FPS="${2:-}"; shift 2 ;;
    --ocr-min-coverage) OCR_MIN_COVERAGE="${2:-}"; shift 2 ;;
    --probe-samples) PROBE_SAMPLES="${2:-}"; shift 2 ;;
    --threads) THREADS="${2:-}"; shift 2 ;;
    --prefix) PREFIX="${2:-}"; shift 2 ;;
    --overwrite) OVERWRITE=1; shift ;;
    --keep-audio) KEEP_AUDIO=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$ENGINE" == "auto" || "$ENGINE" == "vision" || "$ENGINE" == "paraformer" ]] || {
  echo "--engine must be auto, vision, or paraformer" >&2; exit 2;
}
if [[ -z "$OUTPUT_DIR" || "$OUTPUT_DIR" == "/" || "$OUTPUT_DIR" == "$HOME" ]]; then
  echo "Unsafe --output-dir: $OUTPUT_DIR" >&2; exit 2
fi
PYTHON="$PREFIX/venv/bin/python"
YTDLP="$PREFIX/venv/bin/yt-dlp"
VISION_OCR="$PREFIX/bin/vision-ocr"
FFMPEG="$PREFIX/bin/ffmpeg"
FFPROBE="$PREFIX/bin/ffprobe"
MODEL_DIR="$PREFIX/models/sherpa-onnx-paraformer-zh-small-2024-03-09"
MODEL="$MODEL_DIR/model.int8.onnx"
TOKENS="$MODEL_DIR/tokens.txt"
VAD="$PREFIX/models/silero_vad.onnx"
ffmpeg_usable() {
  "$1" -hide_banner -formats 2>&1 | grep -Eq '^[[:space:]]*[D.]?E[[:space:]]+image2([,[:space:]]|$)' &&
    "$1" -hide_banner -formats 2>&1 | grep -Eq '^[[:space:]]*[D.]?E[[:space:]]+wav([,[:space:]]|$)' &&
    "$1" -hide_banner -filters 2>&1 | grep -Eq '[[:space:]]crop[[:space:]]'
}
for file_path in "$PYTHON" "$YTDLP" "$VISION_OCR" "$FFMPEG" "$FFPROBE"; do
  [[ -x "$file_path" ]] || { echo "Missing runtime: $file_path. Run scripts/bootstrap.sh --install" >&2; exit 3; }
done
ffmpeg_usable "$FFMPEG" || {
  echo "Isolated FFmpeg lacks image2, WAV, or crop support. Rerun scripts/bootstrap.sh --install." >&2
  exit 3
}
for file_path in "$MODEL" "$TOKENS" "$VAD"; do
  [[ -s "$file_path" ]] || { echo "Missing model: $file_path. Run scripts/bootstrap.sh --install" >&2; exit 3; }
done
"$PYTHON" -c 'import sys
crop, fps, coverage = map(float, sys.argv[1:4])
samples, threads = map(int, sys.argv[4:])
assert 0 < crop <= 1 and fps > 0 and 0 < coverage <= 1
assert samples >= 1 and threads >= 1' \
  "$CROP_RATIO" "$OCR_FPS" "$OCR_MIN_COVERAGE" "$PROBE_SAMPLES" "$THREADS" 2>/dev/null || {
  echo "Invalid numeric option" >&2; exit 2;
}

if [[ ! -f "$SOURCE" && "$SOURCE" =~ ^[0-9]{15,25}$ ]]; then
  SOURCE="https://www.douyin.com/video/$SOURCE"
elif [[ ! -f "$SOURCE" && "$SOURCE" =~ modal_id=([0-9]{15,25}) ]]; then
  SOURCE="https://www.douyin.com/video/${BASH_REMATCH[1]}"
fi
IS_URL=0
[[ "$SOURCE" =~ ^https?:// ]] && IS_URL=1
if [[ "$IS_URL" -eq 0 && ! -f "$SOURCE" && "$DRY_RUN" -eq 0 ]]; then
  echo "Local source does not exist: $SOURCE" >&2; exit 4
fi

KNOWN_OUTPUTS=(decision.json transcript.srt transcript.txt transcript.json transcript.md)
[[ "$KEEP_AUDIO" -eq 0 ]] || KNOWN_OUTPUTS+=(normalized.wav)
if [[ "$OVERWRITE" -eq 0 ]]; then
  for name in "${KNOWN_OUTPUTS[@]}"; do
    [[ ! -e "$OUTPUT_DIR/$name" ]] || { echo "Output exists: $OUTPUT_DIR/$name (use --overwrite)" >&2; exit 5; }
  done
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf 'source=%s\noutput_dir=%s\nengine=%s\nprefix=%s\ncrop_ratio=%s\nocr_fps=%s\nocr_min_coverage=%s\nprobe_samples=%s\nthreads=%s\n' \
    "$SOURCE" "$OUTPUT_DIR" "$ENGINE" "$PREFIX" "$CROP_RATIO" "$OCR_FPS" "$OCR_MIN_COVERAGE" "$PROBE_SAMPLES" "$THREADS"
  [[ "$IS_URL" -eq 0 ]] || printf 'cookies_from_browser=%s\n' "${COOKIES_BROWSER:-none}"
  exit 0
fi

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/douyin-video-transcript.XXXXXX")"
cleanup() { [[ -n "${WORK_DIR:-}" && -d "$WORK_DIR" ]] && rm -rf -- "$WORK_DIR"; }
trap cleanup EXIT

MEDIA_PATH="$SOURCE"
SOURCE_LABEL="$(basename -- "$SOURCE")"
if [[ "$IS_URL" -eq 1 ]]; then
  download_args=(--no-playlist --no-progress --format "bestvideo*+bestaudio/best" --ffmpeg-location "$PREFIX/bin" \
    --output "$WORK_DIR/source.%(ext)s" --print "after_move:filepath")
  [[ -z "$COOKIES_BROWSER" ]] || download_args+=(--cookies-from-browser "$COOKIES_BROWSER")
  if ! MEDIA_PATH="$("$YTDLP" "${download_args[@]}" "$SOURCE")"; then
    echo "Media download failed. With explicit user approval, retry using --cookies-from-browser." >&2; exit 6
  fi
  SOURCE_LABEL="${SOURCE%%\?*}"
fi

DURATION="$("$FFPROBE" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$MEDIA_PATH" | head -1)"
[[ "$DURATION" =~ ^[0-9]+([.][0-9]+)?$ ]] || { echo "Could not determine media duration" >&2; exit 7; }
HAS_VIDEO=0
[[ -n "$("$FFPROBE" -v error -select_streams v:0 -show_entries stream=index -of csv=p=0 "$MEDIA_PATH" | head -1)" ]] && HAS_VIDEO=1
if [[ "$ENGINE" == "vision" && "$HAS_VIDEO" -eq 0 ]]; then
  echo "--engine vision requires a video stream" >&2; exit 7
fi

DECISION="$WORK_DIR/decision.json"
ROUTE="$ENGINE"

extract_frames() {
  local fps="$1" directory="$2"
  mkdir -p "$directory"
  "$FFMPEG" -hide_banner -loglevel error -y -i "$MEDIA_PATH" -an \
    -vf "fps=$fps,crop=iw:ih*$CROP_RATIO:0:ih*(1-$CROP_RATIO),scale=1280:-2" \
    -q:v 3 -f image2 "$directory/frame-%06d.jpg"
}

if [[ "$ENGINE" == "auto" ]]; then
  if [[ "$HAS_VIDEO" -eq 0 ]]; then
    ROUTE="paraformer"
    "$PYTHON" "$SCRIPT_DIR/transcript_pipeline.py" decision --output "$DECISION" \
      --route paraformer --reason no_video_stream
  else
    PROBE_FPS="$("$PYTHON" -c 'import sys; print(min(2.0, max(0.001, float(sys.argv[2]) / float(sys.argv[1]))))' "$DURATION" "$PROBE_SAMPLES")"
    PROBE_FRAMES="$WORK_DIR/probe-frames"
    PROBE_RAW="$WORK_DIR/probe.jsonl"
    if extract_frames "$PROBE_FPS" "$PROBE_FRAMES" && \
       "$VISION_OCR" "$PROBE_FRAMES" "$PROBE_FPS" "$PROBE_RAW"; then
      ROUTE="$("$PYTHON" "$SCRIPT_DIR/transcript_pipeline.py" probe "$PROBE_RAW" \
        --output "$DECISION" --duration "$DURATION" --min-coverage "$OCR_MIN_COVERAGE")"
    else
      ROUTE="paraformer"
      "$PYTHON" "$SCRIPT_DIR/transcript_pipeline.py" decision --output "$DECISION" \
        --route paraformer --reason vision_probe_failed
    fi
  fi
else
  "$PYTHON" "$SCRIPT_DIR/transcript_pipeline.py" decision --output "$DECISION" \
    --route "$ROUTE" --reason explicit_engine_override --override
fi

RESULT_DIR="$WORK_DIR/result-$ROUTE"
run_paraformer() {
  local result_dir="$1"
  local wav="$WORK_DIR/normalized.wav"
  "$FFMPEG" -hide_banner -loglevel error -y -i "$MEDIA_PATH" -vn -ac 1 -ar 16000 -c:a pcm_s16le -f wav "$wav"
  "$PYTHON" "$SCRIPT_DIR/transcript_pipeline.py" paraformer "$wav" \
    --model "$MODEL" --tokens "$TOKENS" --vad "$VAD" --output "$result_dir" \
    --source "$SOURCE_LABEL" --title "$TITLE" --duration "$DURATION" --threads "$THREADS"
}

if [[ "$ROUTE" == "vision" ]]; then
  FULL_FRAMES="$WORK_DIR/vision-frames"
  FULL_RAW="$WORK_DIR/vision.jsonl"
  if extract_frames "$OCR_FPS" "$FULL_FRAMES" && \
     "$VISION_OCR" "$FULL_FRAMES" "$OCR_FPS" "$FULL_RAW" && \
     "$PYTHON" "$SCRIPT_DIR/transcript_pipeline.py" vision "$FULL_RAW" \
       --output "$RESULT_DIR" --fps "$OCR_FPS" --crop-ratio "$CROP_RATIO" \
       --min-coverage "$OCR_MIN_COVERAGE" --source "$SOURCE_LABEL" --title "$TITLE" --duration "$DURATION"; then
    :
  elif [[ "$ENGINE" == "auto" ]]; then
    echo "Vision full OCR failed its execution/quality gate; falling back to Paraformer." >&2
    ROUTE="paraformer"
    RESULT_DIR="$WORK_DIR/result-paraformer"
    "$PYTHON" "$SCRIPT_DIR/transcript_pipeline.py" decision --output "$DECISION" \
      --route paraformer --reason vision_full_quality_gate_failed --preserve
    run_paraformer "$RESULT_DIR"
  else
    echo "Forced Vision OCR failed" >&2; exit 8
  fi
else
  run_paraformer "$RESULT_DIR"
fi

cp "$DECISION" "$RESULT_DIR/decision.json"
if [[ "$KEEP_AUDIO" -eq 1 && "$ROUTE" == "paraformer" ]]; then cp "$WORK_DIR/normalized.wav" "$RESULT_DIR/normalized.wav"; fi
"$PYTHON" "$SCRIPT_DIR/transcript_pipeline.py" validate --output "$RESULT_DIR"

mkdir -p "$OUTPUT_DIR"
for name in decision.json transcript.srt transcript.txt transcript.json transcript.md; do cp "$RESULT_DIR/$name" "$OUTPUT_DIR/$name"; done
if [[ "$KEEP_AUDIO" -eq 1 && "$ROUTE" == "paraformer" ]]; then cp "$RESULT_DIR/normalized.wav" "$OUTPUT_DIR/normalized.wav"; fi
printf 'Completed: %s (route=%s)\n' "$OUTPUT_DIR" "$ROUTE"
