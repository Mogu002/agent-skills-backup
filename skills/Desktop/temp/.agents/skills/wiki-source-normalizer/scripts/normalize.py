#!/usr/bin/env python3
"""Source Markdown normalizer (deterministic pass).

用途
----
把已获取的来源文档做**确定性格式归一**，作为它进入 LLM wiki 入库前的前置清洗。
本脚本只做标签级 / 空白级的机械转换，不做语义判断（哪段是噪声、哪个粗体行
该升成标题由调用它的 Agent 按 references 处理）。

它尤其擅长飞书 / Lark docx / wiki 导出的 Markdown——这类文件通常混杂 CCM 私有
HTML 片段：`<table>+<colgroup>+<tbody>+<tr>+<td>` 表格、`<cite doc-id=...>`
文档/用户引用、`<callout emoji=...>`、`<bitable>`、`<whiteboard>`、
`<readonly-block>`、`<figure><source>` 附件、`<grid>/<column>` 排版，以及
`<b>/<br/>/<blockquote>/<ol>/<ul>` 富文本标签。这些标签在 GFM 渲染时会被吞掉
或错乱。脚本用容错 HTMLParser 把整篇当作 fragment 解析成节点树，再按语义转成
Markdown 等价物：

- `<table>` → GFM 表（简单结构）或标签化 bullet 块（含嵌套列表/图片时），
  支持 rowspan/colspan 展开与启发式表头识别
- `<callout>` → `> emoji ...` 引用
- `<cite>` → `《标题》`（doc/wiki/bitable）或 `@姓名`（user 类型）
- `<bitable>/<whiteboard>/<readonly-block>` → `_[飞书 XX 嵌入]_` 占位
- `<figure><source>` → `[附件下载](href)`
- `<img>` → 标准 `![alt](url)`；无 http(s) URL 时退化为 `_[图片: alt]_`
- `<ul>/<ol>/<li>` → Markdown 列表（保留嵌套缩进）
- `<b>` → `**...**`；`<br/>` → 硬换行；`<blockquote>` → `> ...`
- `<title>` → 提到文件首行作为 `# 标题`
- 其它未知标签（含 `<grid>/<column>/<colgroup>/<thead>/<tbody>` 等）透传子节点

所有可见文本、URL、图片 alt 全部保留；输出经过空行折叠与行末空格清理，幂等。

自包含
------
仅依赖 Python 标准库，可在任意 Agent 环境运行，不依赖任何 wiki 仓库或外部脚本。

CLI
---
    python3 normalize.py <input.md> [output.md]
    python3 normalize.py <input_dir> <output_dir>

单文件模式省略 output 会打到 stdout；目录模式递归遍历 *.md，源目录只读。
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path


VOID_TAGS = {
    "br", "img", "col", "source", "hr", "input",
    "bitable", "whiteboard", "readonly-block", "cite",
}

# --------------------------------------------------------------------------- #
# Tiny DOM builder
# --------------------------------------------------------------------------- #


class Node:
    __slots__ = ("tag", "attrs", "text", "children")

    def __init__(self, tag=None, attrs=None, text=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.text = text
        self.children = []


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]

    def _push(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)
        return node

    def handle_starttag(self, tag, attrs):
        self._push(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data:
            self.stack[-1].children.append(Node(text=data))


def parse_fragment(html_text: str) -> Node:
    builder = TreeBuilder()
    builder.feed(html_text)
    builder.close()
    return builder.root


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def inline_text(node: Node) -> str:
    """Render a node subtree as inline Markdown (no block breaks)."""
    return _render(node, block=False).strip()


def render_block(node: Node) -> str:
    return _render(node, block=True)


def _render(node: Node, block: bool) -> str:
    parts = []
    for child in node.children:
        parts.append(_render_one(child, block=block))
    return "".join(parts)


def _render_one(node: Node, block: bool) -> str:
    if node.text is not None:
        return node.text

    tag = node.tag
    a = node.attrs

    if tag == "b":
        inner = inline_text(node)
        return f"**{inner}**" if inner else ""
    if tag == "u":
        return inline_text(node)
    if tag == "code":
        inner = inline_text(node)
        return f"`{inner}`" if inner else ""
    if tag == "br":
        return "\n" if block else " "
    if tag == "p":
        inner = _render(node, block=block).strip()
        return f"{inner}\n\n" if block else inner
    if tag in ("h4", "h5"):
        prefix = "#" * (4 if tag == "h4" else 5)
        inner = inline_text(node)
        return f"\n{prefix} {inner}\n\n"
    if tag == "blockquote":
        inner = _render(node, block=True).strip()
        quoted = "\n".join(f"> {line}" if line else ">" for line in inner.splitlines())
        return f"\n{quoted}\n\n"
    if tag == "callout":
        emoji = a.get("emoji", "").strip()
        inner = _render(node, block=True).strip()
        head = f"> {emoji} " if emoji else "> "
        lines = inner.splitlines() or [""]
        quoted = "\n".join((head if idx == 0 else "> ") + line for idx, line in enumerate(lines))
        return f"\n{quoted}\n\n"
    if tag == "a":
        text = inline_text(node)
        href = a.get("href", "").strip()
        if not text and href:
            return href
        if href:
            return f"[{text}]({href})"
        return text
    if tag == "img":
        alt = a.get("alt", a.get("name", "")).strip()
        href = a.get("href") or a.get("src") or ""
        alt = alt.replace("\n", " ")
        if href.startswith("http"):
            return f"![{alt}]({href})"
        # src-only token images: keep alt as a note
        if alt:
            return f"_[图片: {alt}]_"
        return ""
    if tag == "cite":
        title = a.get("title", "").strip()
        user_name = a.get("user-name", "").strip()
        if a.get("type") == "user" and user_name:
            return f"@{user_name}"
        if title:
            return f"《{title}》"
        return ""
    if tag == "bitable":
        title = a.get("title", "多维表格")
        return f"_[飞书多维表格嵌入: {title}]_"
    if tag == "whiteboard":
        return "_[飞书画板嵌入]_"
    if tag == "readonly-block":
        href = a.get("href", "").strip()
        return f"[录屏]({href})" if href else "_[嵌入内容]_"
    if tag == "figure":
        # Look for source child with href
        for child in node.children:
            if child.tag == "source" and child.attrs.get("href"):
                href = child.attrs["href"]
                return f"[附件下载]({href})"
        return ""
    if tag == "source":
        href = a.get("href", "").strip()
        return f"[附件下载]({href})" if href else ""
    if tag in ("ul", "ol"):
        return render_list(node, ordered=(tag == "ol"))
    if tag == "li":
        # Handled by parent list renderer, but guard when standalone
        return inline_text(node)
    if tag in ("colgroup", "col", "thead", "tbody", "column", "grid"):
        return _render(node, block=block)
    if tag == "table":
        return render_table(node)
    if tag == "title":
        return ""  # handled at file level

    # Unknown tag: fall back to inner content
    return _render(node, block=block)


def render_list(node: Node, ordered: bool, indent: int = 0) -> str:
    lines = []
    number = 1
    for child in node.children:
        if child.tag != "li":
            continue
        marker = f"{number}. " if ordered else "- "
        content = render_li_content(child)
        pad = "  " * indent
        if not content:
            lines.append(f"{pad}{marker}")
        else:
            first, *rest = content.splitlines()
            lines.append(f"{pad}{marker}{first}")
            for line in rest:
                lines.append(line)
        number += 1
    return "\n" + "\n".join(lines) + "\n\n"


def render_li_content(li: Node) -> str:
    """Render an <li> body, keeping nested lists as indented sublists."""
    pieces = []
    pending_inline = []

    def flush_inline():
        if pending_inline:
            text = "".join(pending_inline).strip()
            if text:
                pieces.append(text)
            pending_inline.clear()

    for child in li.children:
        if child.tag in ("ul", "ol"):
            flush_inline()
            sub = render_list(child, ordered=(child.tag == "ol"), indent=1)
            pieces.append(sub.strip("\n"))
        else:
            pending_inline.append(_render_one(child, block=False))
    flush_inline()

    if not pieces:
        return ""
    # First piece: inline; subsequent pieces (usually nested lists) go on new lines.
    body = pieces[0]
    for extra in pieces[1:]:
        body += "\n" + indent_block(extra, "  ")
    return body


def indent_block(text: str, prefix: str) -> str:
    return "\n".join((prefix + line) if line else line for line in text.splitlines())


# --------------------------------------------------------------------------- #
# Tables → Markdown
# --------------------------------------------------------------------------- #


def rows_in_order(node: Node) -> list[Node]:
    out = []

    def walk(n: Node):
        for child in n.children:
            if child.tag == "tr":
                out.append(child)
            elif child.tag in ("thead", "tbody"):
                walk(child)

    walk(node)
    return out


def cell_content(cell: Node) -> str:
    text = _render(cell, block=True)
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def cell_inline(cell: Node) -> str:
    text = cell_content(cell)
    lines = [line for line in text.splitlines() if line.strip()]
    return " / ".join(lines)


def is_simple_row(row: Node) -> bool:
    for cell in row.children:
        if cell.tag not in ("td", "th"):
            continue
        for child in cell.children:
            if child.tag in ("ul", "ol", "table", "blockquote", "br", "p", "img"):
                return False
        # If cell text is long (>120 chars) or has embedded newlines, treat as complex
        text = cell_content(cell)
        if "\n" in text or len(text) > 120:
            return False
    return True


def render_table(node: Node) -> str:
    rows = rows_in_order(node)
    if not rows:
        return ""

    max_cols = max(sum(int(c.attrs.get("colspan", 1)) for c in r.children if c.tag in ("td", "th")) for r in rows)
    if max_cols == 0:
        return ""

    simple = all(is_simple_row(r) for r in rows)
    if simple and max_cols >= 2:
        return render_markdown_table(rows, max_cols)
    return render_block_table(rows, max_cols)


def render_markdown_table(rows: list[Node], cols: int) -> str:
    header_row = rows[0]
    header_cells = [c for c in header_row.children if c.tag in ("td", "th")]
    header = [cell_inline(c).replace("|", "\\|") for c in header_cells]
    while len(header) < cols:
        header.append("")
    body_rows = rows[1:]
    matrix = expand_rowspan(body_rows)
    body: list[str] = []
    for cells in matrix:
        rendered = [cell_inline(c).replace("|", "\\|") for c in cells]
        while len(rendered) < cols:
            rendered.append("")
        body.append("| " + " | ".join(rendered) + " |")
    if not header and not body:
        return ""
    sep = "| " + " | ".join(["---"] * cols) + " |"
    lines = ["| " + " | ".join(header) + " |", sep, *body]
    return "\n" + "\n".join(lines) + "\n\n"


def expand_rowspan(rows: list[Node]) -> list[list[Node]]:
    """Return a matrix of cell Nodes with rowspan/colspan expanded.

    Missing cells produced by rowspan continuation are set to a dummy empty
    Node so downstream row rendering can preserve alignment.
    """
    matrix: list[list[Node]] = []
    pending: dict[int, tuple[Node, int]] = {}  # col_idx -> (cell, remaining_rows)

    for row in rows:
        cells = [c for c in row.children if c.tag in ("td", "th")]
        col = 0
        expanded: list[Node] = []
        cell_iter = iter(cells)
        while True:
            # Fill from any pending rowspan first
            while col in pending:
                cell, remaining = pending[col]
                expanded.append(cell)
                colspan = int(cell.attrs.get("colspan", 1) or 1)
                if remaining - 1 <= 0:
                    del pending[col]
                else:
                    pending[col] = (cell, remaining - 1)
                col += colspan
            try:
                cell = next(cell_iter)
            except StopIteration:
                break
            rowspan = int(cell.attrs.get("rowspan", 1) or 1)
            colspan = int(cell.attrs.get("colspan", 1) or 1)
            expanded.append(cell)
            if rowspan > 1:
                pending[col] = (cell, rowspan - 1)
            col += colspan
        matrix.append(expanded)
        # Advance pending rowspans that were not touched in this row
        for k in list(pending.keys()):
            if k >= col:
                cell, remaining = pending[k]
                if remaining - 1 <= 0:
                    del pending[k]
                else:
                    pending[k] = (cell, remaining - 1)
    return matrix


def looks_like_header_row(cells: list[Node], cols: int) -> bool:
    """Return True if the row cells look like a header (short, all bold, all filled)."""
    if len(cells) < cols:
        return False
    if cols < 2:
        return False
    for cell in cells:
        text = cell_content(cell)
        if "\n" in text or len(text) > 40 or not text.strip():
            return False
        # Every child must be a <b> wrapper or plain text (whitespace); tolerate <p> around <b>.
        if not cell_is_bold_only(cell):
            return False
    return True


def cell_is_bold_only(cell: Node) -> bool:
    saw_bold = False
    for child in cell.children:
        if child.text is not None:
            if child.text.strip():
                return False
            continue
        if child.tag == "b":
            saw_bold = True
            continue
        if child.tag == "p":
            if not cell_is_bold_only(child):
                return False
            saw_bold = True
            continue
        return False
    return saw_bold


def render_block_table(rows: list[Node], cols: int) -> str:
    header_cells: list[str] = []
    header_row: Node | None = None
    if rows:
        first = rows[0]
        first_cells = [c for c in first.children if c.tag in ("td", "th")]
        if first_cells and all(c.tag == "th" for c in first_cells):
            header_row = first
            header_cells = [cell_inline(c) for c in first_cells]
        elif looks_like_header_row(first_cells, cols):
            header_row = first
            header_cells = [cell_inline(c) for c in first_cells]

    body_rows = rows[1:] if header_row is not None else rows
    matrix = expand_rowspan(body_rows)

    blocks: list[str] = []
    for cells in matrix:
        cell_texts = [cell_content(c) for c in cells]
        if not cell_texts:
            continue
        if not any(t.strip() for t in cell_texts):
            continue

        items: list[str] = []
        if header_cells and len(cell_texts) <= len(header_cells):
            for idx, text in enumerate(cell_texts):
                label = header_cells[idx] if idx < len(header_cells) else ""
                items.append(format_labeled_item(label, text) if label else format_bullet_item(text))
        elif cols == 2 and len(cell_texts) >= 2:
            label = cell_texts[0].strip()
            value = cell_texts[1]
            if not label:
                items.append(format_bullet_item(value))
            else:
                items.append(format_labeled_item(label, value))
        else:
            for idx, text in enumerate(cell_texts):
                items.append(format_labeled_item(f"列{idx + 1}", text))
        blocks.append("\n".join(items).strip())
    body = "\n\n".join(b for b in blocks if b.strip())

    if header_cells:
        cleaned = [strip_bold_markers(h).strip() for h in header_cells]
        header_line = "**表头**：" + " | ".join(cleaned)
        return "\n" + header_line + "\n\n" + body + "\n\n"
    return "\n" + body + "\n\n"


def format_labeled_item(label: str, text: str) -> str:
    text = text.strip()
    label = strip_bold_markers(label).strip()
    if not text:
        return f"- **{label}**："
    if text.lstrip().startswith("- "):
        # Cell starts with a bullet list — put the label on its own line and
        # keep the list indented underneath.
        indented = indent_block(text, "  ")
        return f"- **{label}**：\n{indented}"
    if "\n" in text:
        first, *rest = text.splitlines()
        lines = [f"- **{label}**：{first}"]
        for line in rest:
            lines.append(f"  {line}" if line else "")
        return "\n".join(lines)
    return f"- **{label}**：{text}"


def strip_bold_markers(value: str) -> str:
    return re.sub(r"\*\*", "", value)


def format_bullet_item(text: str) -> str:
    text = text.strip()
    if not text:
        return "-"
    if "\n" in text:
        first, *rest = text.splitlines()
        lines = [f"- {first}"]
        for line in rest:
            lines.append(f"  {line}" if line else "")
        return "\n".join(lines)
    return f"- {text}"


# --------------------------------------------------------------------------- #
# File processing
# --------------------------------------------------------------------------- #


def convert_document(text: str) -> str:
    # Normalize encoding artefacts before parsing.
    text = text.replace("\ufeff", "")  # BOM
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")  # zero-width

    # Extract & convert <title>...</title> as top-level H1 replacement
    title_match = re.search(r"<title>(.*?)</title>", text, flags=re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    if title_match:
        text = text[:title_match.start()] + text[title_match.end():]

    # Parse everything with our tolerant tree builder. Markdown parts survive
    # because non-HTML text becomes text nodes.
    tree = parse_fragment(text)
    body = render_block(tree)

    # Post-processing
    body = collapse_blank_lines(body)
    body = strip_trailing_spaces(body)

    if title:
        body = f"# {title}\n\n{body.lstrip()}"

    return body.rstrip() + "\n"


def collapse_blank_lines(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse adjacent bold end/start markers created by concatenated <b> tags.
    text = re.sub(r"\*\*\*\*", "", text)
    return text


def strip_trailing_spaces(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines())


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage:\n"
            "  normalize.py <input.md> [output.md]\n"
            "  normalize.py <input_dir> <output_dir>",
            file=sys.stderr,
        )
        return 2

    src = Path(argv[1])
    dst = Path(argv[2]) if len(argv) >= 3 else None

    if src.is_dir():
        if dst is None:
            print("directory mode requires an output directory", file=sys.stderr)
            return 2
        for path in sorted(src.rglob("*.md")):
            rel = path.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(convert_document(path.read_text(encoding="utf-8")), encoding="utf-8")
            print(f"normalized {rel}", file=sys.stderr)
        return 0

    if not src.is_file():
        print(f"input not found: {src}", file=sys.stderr)
        return 2

    cleaned = convert_document(src.read_text(encoding="utf-8"))
    if dst is None:
        sys.stdout.write(cleaned)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(cleaned, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
