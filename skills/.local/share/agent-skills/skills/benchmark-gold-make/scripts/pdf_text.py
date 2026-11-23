#!/usr/bin/env python3
"""Extract the text layer from PDFs that have one (real reports, ReportLab-generated
"pseudo-scans"). Scanned/image-only PDFs will return little/no text — fall back to
vision/OCR for those.

Why this script: the working directory may contain files (e.g. inspect.py) that
shadow the Python stdlib and break pypdf import. This strips cwd/'' from sys.path
before importing pypdf, so it runs correctly regardless of cwd.

Usage:
  python pdf_text.py <file-or-dir> [more ...] [--pages N] [--out out.json]

- <file-or-dir>: one or more PDF paths or directories (dirs are scanned for *.pdf)
- --pages N: only first N pages per file (default: all)
- --out PATH: write {filename: text} JSON (utf-8). If omitted, prints to stdout.
"""
import sys, os, glob, json, argparse

# Remove cwd / '' so a local inspect.py etc. cannot shadow stdlib / pypdf deps.
sys.path = [p for p in sys.path if p not in ("", os.getcwd())]

try:
    import pypdf  # noqa: E402
except Exception as e:  # pragma: no cover
    sys.stderr.write(f"pypdf import failed: {e}\n")
    sys.exit(2)


def extract(path, max_pages=None):
    try:
        reader = pypdf.PdfReader(path)
    except Exception as e:
        return f"<<ERROR opening: {e}>>"
    pages = reader.pages if max_pages is None else reader.pages[:max_pages]
    chunks = []
    for i, p in enumerate(pages):
        try:
            chunks.append(f"--- page {i+1} ---\n" + (p.extract_text() or ""))
        except Exception as e:
            chunks.append(f"--- page {i+1} ---\n<<ERROR: {e}>>")
    return "\n".join(chunks).strip()


def collect(targets):
    files = []
    for t in targets:
        if os.path.isdir(t):
            files += sorted(glob.glob(os.path.join(t, "*.pdf")))
        else:
            files.append(t)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--pages", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out = {}
    for f in collect(args.targets):
        out[os.path.basename(f)] = extract(f, args.pages)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fo:
            json.dump(out, fo, ensure_ascii=False, indent=1)
        print(f"extracted {len(out)} pdf(s) -> {args.out}")
    else:
        for name, txt in out.items():
            print(f"\n################ {name} ################\n{txt}")


if __name__ == "__main__":
    main()
