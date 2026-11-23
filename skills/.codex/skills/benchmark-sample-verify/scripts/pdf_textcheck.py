"""Test whether a PDF is a pure-image scan (no extractable text layer).

Decides 坑3-A by actual text extraction, NOT by byte heuristics like BT/ET/Tj,
which ReportLab leaves behind even for image-only pages.

Usage:
  python scripts/pdf_textcheck.py path/to/file.pdf
Exit summary: prints chars extracted per page and image xobject names.
Verdict: PURE-IMAGE if total extracted text is ~0 and pages carry images.
"""
import sys


def main():
    if len(sys.argv) < 2:
        print("usage: pdf_textcheck.py <pdf>")
        return
    path = sys.argv[1]
    try:
        from pypdf import PdfReader
    except Exception as e:
        print(f"pypdf import failed: {e}\nInstall with: pip install pypdf")
        return

    reader = PdfReader(path)
    total_chars = 0
    total_imgs = 0
    for i, pg in enumerate(reader.pages):
        txt = pg.extract_text() or ""
        total_chars += len(txt.strip())
        try:
            imgs = list(pg.images)
        except Exception:
            imgs = []
        total_imgs += len(imgs)
        print(f"page {i}: text={len(txt.strip())} chars, images={[im.name for im in imgs]}")

    verdict = "PURE-IMAGE (no text layer, has image)" if total_chars == 0 and total_imgs > 0 else (
        "HAS-TEXT-LAYER" if total_chars > 0 else "NO-TEXT-NO-IMAGE?")
    print(f"VERDICT: {verdict} | total_text_chars={total_chars} total_images={total_imgs}")


if __name__ == "__main__":
    main()
