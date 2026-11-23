#!/usr/bin/env bash
set -euo pipefail
unset PYTHONHOME PYTHONPATH

SHERPA_VERSION="${SHERPA_VERSION:-1.13.5}"
NUMPY_VERSION="${NUMPY_VERSION:-2.3.3}"
YTDLP_VERSION="${YTDLP_VERSION:-2026.8.19}"
MODEL_NAME="sherpa-onnx-paraformer-zh-small-2024-03-09"
MODEL_ARCHIVE_SHA256="da92b3db5218c5be53aad53e57d1b6e63e7fc98a0e054fbdd6dbe18e9c6b1450"
MODEL_SHA256="3ef6c19369b912f7caf3cef8e545c5ccd1a33d9d7ec792a46668dc41c4b229ec"
TOKENS_SHA256="4b2d964e18b9cf139b473003b6698fb2ed9a2a5ec55b93daa677b28f578897aa"
VAD_SHA256="9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6"
MODEL_URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/${MODEL_NAME}.tar.bz2"
VAD_URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx"
MODE="check"
PREFIX="${XDG_DATA_HOME:-${HOME}/.local/share}/douyin-video-transcript"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PYTHON_COMMAND="${PYTHON_COMMAND:-python3}"

usage() {
  cat <<'EOF'
Usage: bootstrap.sh [--check|--install] [--prefix DIR]

--check    Verify FFmpeg, Apple Vision helper, Python environment and models
--install  Install missing Homebrew packages, Python packages and checked models
--prefix   Isolated install location

Overrides: PYTHON_COMMAND, SHERPA_VERSION, NUMPY_VERSION, YTDLP_VERSION
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) MODE="check"; shift ;;
    --install) MODE="install"; shift ;;
    --prefix) PREFIX="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$PREFIX" || "$PREFIX" == "/" || "$PREFIX" == "$HOME" ]]; then
  echo "Unsafe --prefix: $PREFIX" >&2
  exit 2
fi
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This Skill currently supports macOS only because the default OCR path uses Apple Vision." >&2
  exit 3
fi

sha256() { shasum -a 256 "$1" | awk '{print $1}'; }
verify_file() { [[ -s "$1" && "$(sha256 "$1")" == "$2" ]]; }
ffmpeg_usable() {
  [[ -x "$1" ]] &&
    "$1" -hide_banner -formats 2>&1 | grep -Eq '^[[:space:]]*[D.]?E[[:space:]]+image2([,[:space:]]|$)' &&
    "$1" -hide_banner -formats 2>&1 | grep -Eq '^[[:space:]]*[D.]?E[[:space:]]+wav([,[:space:]]|$)' &&
    "$1" -hide_banner -filters 2>&1 | grep -Eq '[[:space:]]crop[[:space:]]'
}

check_environment() {
  local missing=0
  for command_name in swiftc curl tar; do
    if command -v "$command_name" >/dev/null 2>&1; then
      printf 'ok   %s: %s\n' "$command_name" "$(command -v "$command_name")"
    else
      printf 'miss %s\n' "$command_name" >&2
      missing=1
    fi
  done
  if ffmpeg_usable "$PREFIX/bin/ffmpeg" && [[ -x "$PREFIX/bin/ffprobe" ]]; then
    printf 'ok   isolated FFmpeg/FFprobe\n'
  else
    printf 'miss full FFmpeg/FFprobe (image2, WAV and crop support required)\n' >&2
    missing=1
  fi
  if command -v "$PYTHON_COMMAND" >/dev/null 2>&1 && "$PYTHON_COMMAND" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    printf 'ok   python3: %s\n' "$(command -v "$PYTHON_COMMAND")"
  else
    printf 'miss Python >= 3.10\n' >&2
    missing=1
  fi
  for file_path in "$PREFIX/venv/bin/python" "$PREFIX/venv/bin/yt-dlp" "$PREFIX/bin/vision-ocr"; do
    if [[ -x "$file_path" ]]; then printf 'ok   %s\n' "$file_path"; else printf 'miss %s\n' "$file_path" >&2; missing=1; fi
  done
  if [[ -x "$PREFIX/venv/bin/python" ]] && "$PREFIX/venv/bin/python" -c \
    "import numpy, sherpa_onnx; assert numpy.__version__ == '$NUMPY_VERSION'; assert sherpa_onnx.__version__ == '$SHERPA_VERSION'"; then
    printf 'ok   sherpa-onnx %s + numpy %s\n' "$SHERPA_VERSION" "$NUMPY_VERSION"
  else
    printf 'miss pinned Python runtime\n' >&2
    missing=1
  fi
  if verify_file "$PREFIX/models/$MODEL_NAME/model.int8.onnx" "$MODEL_SHA256"; then
    printf 'ok   Paraformer INT8 model\n'
  else
    printf 'miss or checksum mismatch: Paraformer model\n' >&2
    missing=1
  fi
  if verify_file "$PREFIX/models/$MODEL_NAME/tokens.txt" "$TOKENS_SHA256"; then
    printf 'ok   Paraformer tokens\n'
  else
    printf 'miss or checksum mismatch: Paraformer tokens\n' >&2
    missing=1
  fi
  if verify_file "$PREFIX/models/silero_vad.onnx" "$VAD_SHA256"; then
    printf 'ok   Silero VAD\n'
  else
    printf 'miss or checksum mismatch: Silero VAD\n' >&2
    missing=1
  fi
  return "$missing"
}

if [[ "$MODE" == "check" ]]; then
  check_environment
  exit $?
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required. Install it from https://brew.sh, then rerun." >&2
  exit 3
fi
packages=()
FFMPEG_SOURCE="$(command -v ffmpeg || true)"
if ! ffmpeg_usable "$FFMPEG_SOURCE"; then packages+=(ffmpeg); fi
if ! command -v "$PYTHON_COMMAND" >/dev/null 2>&1 || ! "$PYTHON_COMMAND" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
  packages+=(python)
fi
if ((${#packages[@]})); then brew install "${packages[@]}"; fi
hash -r
command -v swiftc >/dev/null 2>&1 || {
  echo "swiftc is required. Run 'xcode-select --install', then rerun." >&2
  exit 3
}

mkdir -p "$PREFIX/bin" "$PREFIX/models"
if ffmpeg_usable "$FFMPEG_SOURCE"; then
  FFPROBE_SOURCE="$(command -v ffprobe || true)"
else
  FFMPEG_SOURCE="$(brew --prefix ffmpeg)/bin/ffmpeg"
  FFPROBE_SOURCE="$(brew --prefix ffmpeg)/bin/ffprobe"
fi
ffmpeg_usable "$FFMPEG_SOURCE" && [[ -x "$FFPROBE_SOURCE" ]] || {
  echo "Installed FFmpeg lacks required image2, WAV, or crop capabilities." >&2
  exit 3
}
ln -sfn "$FFMPEG_SOURCE" "$PREFIX/bin/ffmpeg"
ln -sfn "$FFPROBE_SOURCE" "$PREFIX/bin/ffprobe"
PYTHON_VERSION="$("$PYTHON_COMMAND" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
VENV="$PREFIX/venv-py$PYTHON_VERSION"
"$PYTHON_COMMAND" -m venv "$VENV"
"$VENV/bin/python" -m pip install --disable-pip-version-check --index-url https://pypi.org/simple \
  "numpy==$NUMPY_VERSION" "sherpa-onnx==$SHERPA_VERSION" "yt-dlp==$YTDLP_VERSION"
ln -sfn "$VENV" "$PREFIX/venv"

swiftc -O "$SCRIPT_DIR/vision_ocr.swift" -o "$PREFIX/bin/vision-ocr"

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/douyin-video-bootstrap.XXXXXX")"
cleanup() { [[ -n "${WORK_DIR:-}" && -d "$WORK_DIR" ]] && rm -rf -- "$WORK_DIR"; }
trap cleanup EXIT

if ! verify_file "$PREFIX/models/$MODEL_NAME/model.int8.onnx" "$MODEL_SHA256" || \
   ! verify_file "$PREFIX/models/$MODEL_NAME/tokens.txt" "$TOKENS_SHA256"; then
  archive="$WORK_DIR/$MODEL_NAME.tar.bz2"
  curl --fail --location --retry 3 --output "$archive" "$MODEL_URL"
  verify_file "$archive" "$MODEL_ARCHIVE_SHA256" || { echo "Paraformer archive checksum mismatch" >&2; exit 4; }
  tar -xjf "$archive" -C "$PREFIX/models"
fi
if ! verify_file "$PREFIX/models/silero_vad.onnx" "$VAD_SHA256"; then
  curl --fail --location --retry 3 --output "$WORK_DIR/silero_vad.onnx" "$VAD_URL"
  verify_file "$WORK_DIR/silero_vad.onnx" "$VAD_SHA256" || { echo "Silero VAD checksum mismatch" >&2; exit 4; }
  cp "$WORK_DIR/silero_vad.onnx" "$PREFIX/models/silero_vad.onnx"
fi

check_environment
printf '\nReady. Prefix: %s\n' "$PREFIX"
