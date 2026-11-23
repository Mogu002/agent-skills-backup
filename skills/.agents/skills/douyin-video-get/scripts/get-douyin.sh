#!/usr/bin/env bash
# get-douyin.sh — capture the highest-quality Douyin video via the user's real
# ego-browser session, then mux video+audio into a single mp4.
#
# Usage:   bash get-douyin.sh <douyin_url_or_video_page> [output_dir]
# Output:  <output_dir>/<video_id>.mp4   (prints: OUTPUT=<path>)
# Deps:    ego-browser (logged-in Douyin), ffmpeg, python3 (stdlib only)
# Exit:    0 ok | 2 bad args | 3 missing dep | 4 capture failed | 5 mux failed
set -euo pipefail

URL="${1:-}"
OUT_DIR="${2:-$(pwd)/douyin_out}"
[[ -n "$URL" ]] || { echo "usage: get-douyin.sh <url> [out_dir]" >&2; exit 2; }

command -v ego-browser >/dev/null || { echo "ego-browser not found" >&2; exit 3; }
command -v ffmpeg >/dev/null || { echo "ffmpeg not found (brew install ffmpeg)" >&2; exit 3; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

# Normalize a bare numeric ID or short share link to a canonical video page.
if [[ "$URL" =~ ^[0-9]{15,25}$ ]]; then
  URL="https://www.douyin.com/video/$URL"
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/douyin-get.XXXXXX")"
cleanup() { [[ -n "${WORK:-}" && -d "$WORK" ]] && rm -rf -- "$WORK"; }
trap cleanup EXIT
mkdir -p "$OUT_DIR"

# Raw streams download to a persistent staging dir (not the temp WORK dir, which
# is deleted on exit). Cleaned up after a successful mux.
STAGE="$OUT_DIR/.streams"
mkdir -p "$STAGE"

# Inject inputs into the capture script without shell-quoting hazards: prepend a
# line that sets globalThis.__IN from a JSON literal built by python3.
IN_JSON="$(python3 -c 'import json,sys; print(json.dumps({"url":sys.argv[1],"outDir":sys.argv[2]}))' "$URL" "$STAGE")"
RUN="$WORK/run.mjs"
printf 'globalThis.__IN = %s;\n' "$IN_JSON" > "$RUN"
cat "$SCRIPT_DIR/capture.mjs" >> "$RUN"

echo "Capturing stream via ego-browser..." >&2
# ego-browser routes all script console output to stderr, so capture combined
# output and isolate the single RESULT line. Diagnostics (plain lines) are kept
# for error reporting.
CAP_OUT="$(ego-browser nodejs < "$RUN" 2>&1)" || true

LINE="$(printf '%s\n' "$CAP_OUT" | grep '^RESULT ' | tail -1 | sed 's/^RESULT //')"
if [[ -z "$LINE" ]]; then
  echo "no result from capture; ego-browser diagnostics:" >&2
  printf '%s\n' "$CAP_OUT" | tail -8 >&2
  exit 4
fi

OK="$(printf '%s' "$LINE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("1" if d.get("ok") else "0")')"
if [[ "$OK" != "1" ]]; then
  REASON="$(printf '%s' "$LINE" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("reason","unknown"))')"
  echo "Capture failed: $REASON" >&2
  [[ "$REASON" == "login_or_verify_required" ]] && echo "Open Douyin in ego-browser and sign in, then retry." >&2
  exit 4
fi

VIDEO="$(printf '%s' "$LINE" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("video",""))')"
AUDIO="$(printf '%s' "$LINE" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("audio",""))')"
PROG="$(printf '%s' "$LINE" | python3 -c 'import json,sys; print("1" if json.load(sys.stdin).get("progressive") else "0")')"

# Derive video id for the output filename: prefer the id resolved by the browser
# (handles short links), then the URL path, then a timestamp.
VID="$(printf '%s' "$LINE" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("id",""))')"
[[ -n "$VID" ]] || VID="$(printf '%s' "$URL" | sed -nE 's#.*/video/([0-9]+).*#\1#p')"
[[ -n "$VID" ]] || VID="$(date +%s)"
OUT="$OUT_DIR/$VID.mp4"

if [[ "$PROG" == "1" || -z "$AUDIO" ]]; then
  # Single progressive/muxed file: copy as-is.
  cp "$VIDEO" "$OUT"
else
  ffmpeg -y -hide_banner -loglevel error -i "$VIDEO" -i "$AUDIO" -c copy "$OUT" \
    || { echo "ffmpeg mux failed" >&2; exit 5; }
fi

[[ -s "$OUT" ]] || { echo "output missing/empty" >&2; exit 5; }
rm -rf "$STAGE"
echo "OUTPUT=$OUT"
