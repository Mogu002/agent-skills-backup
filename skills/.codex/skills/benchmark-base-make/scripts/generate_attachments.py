"""Generate explicitly synthetic PDF fixtures locally; render scan PDFs without text layers."""
import argparse, hashlib, pathlib, shutil, subprocess, tempfile
from common import read_json, write_json


def generate(spec, output_dir, font_path=None, poppler=None, dpi=150, overwrite=False):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.lib.pagesizes import A4
    from pypdf import PdfReader
    if not 100 <= dpi <= 300:
        raise ValueError("Use scan DPI 100..300; difficulty changes require task justification")
    docs = spec["documents"]
    if not docs or spec.get("synthetic_allowed") is not True or any(d.get("synthetic") is not True for d in docs):
        raise ValueError("This authoring helper makes synthetic fixtures only; task authorization must be established separately")
    ids, names = set(), set()
    for d in docs:
        name = d["filename"]
        if d["key"] in ids or name in names or pathlib.Path(name).name != name or "/" in name or "\\" in name or not name.lower().endswith(".pdf"):
            raise ValueError("Unique keys and plain PDF filenames are required")
        if not d.get("pages"):
            raise ValueError("Document must have pages")
        ids.add(d["key"]); names.add(name)
    out = pathlib.Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not overwrite and any((out / d["filename"]).exists() for d in docs):
        raise ValueError("Output exists; review it before requesting --overwrite")
    renderer = poppler or shutil.which("pdftoppm")
    if any(d.get("scan") for d in docs) and not renderer:
        raise ValueError("Scan PDFs require configured pdftoppm; do not silently emit text PDFs")
    font = "FixtureCN"
    if font_path:
        pdfmetrics.registerFont(TTFont(font, str(font_path)))
    else:
        font = "STSong-Light"
        pdfmetrics.registerFont(UnicodeCIDFont(font))
    width, height = A4
    def lines(text, size):
        current = ""
        for char in text:
            if char == "\n":
                yield current; current = ""; continue
            if pdfmetrics.stringWidth(current + char, font, size) > width - 100:
                yield current; current = char
            else:
                current += char
        if current:
            yield current
    manifest = []
    with tempfile.TemporaryDirectory(prefix="fixture-render-", dir=out) as temp:
        work = pathlib.Path(temp)
        for index, doc in enumerate(docs):
            vector = work / f"{index}-vector.pdf"
            c = canvas.Canvas(str(vector), pagesize=A4)
            c.setAuthor("Synthetic benchmark fixture")
            c.setTitle(doc["pages"][0]["title"])
            for n, page in enumerate(doc["pages"], 1):
                y = height - 65
                for text, size, color in [(page["title"], 21, (.6, .05, .05) if page.get("red_head") else (.12, .16, .23))] + [(s, 12, (.12, .16, .23)) for s in page.get("paragraphs", [])]:
                    c.setFont(font, size); c.setFillColorRGB(*color)
                    for line in lines(text, size):
                        if y < 85:
                            raise ValueError("Page overflows; split content into explicit pages: " + doc["key"])
                        c.drawString(50, y, line); y -= size * 1.7
                    y -= 10
                c.setFont(font, 8); c.setFillColorRGB(.5, .08, .08)
                c.drawString(50, 38, "合成评测样张：主体、数据和政策内容为测试构造，不代表真实披露或官方文件")
                c.drawRightString(width - 50, 22, str(n)); c.showPage()
            c.save()
            final = work / f"{index}-final.pdf"
            if doc.get("scan"):
                prefix = work / f"{index}-page"
                r = subprocess.run([str(renderer), "-r", str(dpi), "-png", str(vector), str(prefix)], shell=False, capture_output=True, timeout=120)
                if r.returncode:
                    raise RuntimeError("Rendering failed: " + r.stderr.decode(errors="replace")[:500])
                images = [work / f"{index}-page-{j}.png" for j in range(1, len(doc["pages"]) + 1)]
                if not all(f.exists() for f in images):
                    # Poppler pads page numbers when the document has 10+ pages.
                    images = sorted(work.glob(f"{index}-page-*.png"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
                if len(images) != len(doc["pages"]):
                    raise ValueError("Rendered page count mismatch")
                scan = canvas.Canvas(str(final), pagesize=A4)
                for image in images:
                    scan.drawImage(str(image), 0, 0, width=width, height=height); scan.showPage()
                scan.save()
            else:
                shutil.copyfile(vector, final)
            reader = PdfReader(final)
            text = "".join(p.extract_text() or "" for p in reader.pages)
            if len(reader.pages) != len(doc["pages"]):
                raise ValueError("PDF page count mismatch")
            if doc.get("scan") and text.strip():
                raise ValueError("Expected pure-image PDF still has text")
            if not doc.get("scan") and not text.strip():
                raise ValueError("Text PDF has no extractable text")
            destination = out / doc["filename"]
            shutil.copyfile(final, destination)
            manifest.append({"key": doc["key"], "path": str(destination), "size": destination.stat().st_size,
                             "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                             "pages": len(reader.pages), "pure_image": not bool(text.strip()),
                             "synthetic": True, "visual_review": "pending", "independent_ocr": "not_run"})
    write_json(out / "attachment_manifest.json", manifest)
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", required=True); p.add_argument("--output-dir", required=True)
    p.add_argument("--font-path"); p.add_argument("--poppler"); p.add_argument("--dpi", type=int, default=150)
    p.add_argument("--overwrite", action="store_true")
    a = p.parse_args()
    manifest = generate(read_json(a.spec), a.output_dir, a.font_path, a.poppler, a.dpi, a.overwrite)
    print("Generated", len(manifest), "local PDFs; visual/OCR review remains separate")


if __name__ == "__main__":
    main()
