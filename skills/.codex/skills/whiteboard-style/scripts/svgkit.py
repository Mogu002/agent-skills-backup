# -*- coding: utf-8 -*-
"""极简 SVG 绘图工具：飞书画板 svg-parser 兼容（无 filter/mask/clipPath/pattern）。"""

INK = "#1F2329"
SUB = "#646A73"
MUTED = "#8F959E"
LINE = "#BBBFC4"
WHITE = "#FFFFFF"

THEMES = {
    "blue": ("#F0F4FC", "#3370FF", "#1F4BD8"),
    "green": ("#DFF5E5", "#2EA121", "#1F7A18"),
    "amber": ("#FEF1CE", "#FF8800", "#9A5B00"),
    "red": ("#FEE3E2", "#F54A45", "#B3261E"),
    "purple": ("#F0E9FF", "#7F3BF5", "#5B21B6"),
    "gray": ("#F5F6F7", "#DEE0E3", "#4E5969"),
    "teal": ("#DBF5F0", "#14B8A6", "#0F766E"),
}

CJK = 1.0
LAT = 0.58


def tw(text, size):
    """估算文本宽度：CJK 按 1em，拉丁按 0.58em。"""
    w = 0.0
    for ch in text:
        w += (CJK if ord(ch) > 0x2E80 else LAT) * size
    return w


def esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


class Canvas:
    def __init__(self, w, h, title="", subtitle=""):
        self.w, self.h = w, h
        self.parts = []
        self.parts.append('<rect x="0" y="0" width="%d" height="%d" fill="#FFFFFF"/>' % (w, h))
        if title:
            self.text(40, 52, title, 26, INK, weight=700, anchor="start")
        if subtitle:
            self.text(40, 80, subtitle, 13, SUB, weight=400, anchor="start")

    # ---------- primitives ----------
    def text(self, x, y, s, size=14, color=INK, weight=400, anchor="middle", opacity=1.0):
        self.parts.append(
            '<text x="%.1f" y="%.1f" font-size="%s" font-weight="%s" fill="%s" text-anchor="%s" opacity="%s">%s</text>'
            % (x, y, size, weight, color, anchor, opacity, esc(s))
        )

    def rect(self, x, y, w, h, fill=WHITE, stroke=LINE, rx=10, sw=1.2, opacity=1.0):
        self.parts.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s" stroke="%s" stroke-width="%s" opacity="%s"/>'
            % (x, y, w, h, rx, fill, stroke, sw, opacity)
        )

    def line(self, x1, y1, x2, y2, color=LINE, sw=1.4, dash=None):
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        self.parts.append(
            '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"%s/>'
            % (x1, y1, x2, y2, color, sw, d)
        )

    def polyline(self, pts, color=LINE, sw=1.4, dash=None, arrow=True):
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        path = " ".join("%.1f,%.1f" % p for p in pts)
        self.parts.append(
            '<polyline points="%s" fill="none" stroke="%s" stroke-width="%s"%s%s/>'
            % (path, color, sw, d, ' marker-end="url(#arrow)"' if arrow else "")
        )

    def circle(self, cx, cy, r, fill=WHITE, stroke=LINE, sw=1.4):
        self.parts.append(
            '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="%s"/>'
            % (cx, cy, r, fill, stroke, sw)
        )

    def pill(self, x, y, label, theme="blue", size=11, padx=10, h=22):
        fill, stroke, fg = THEMES[theme]
        w = tw(label, size) + padx * 2
        self.rect(x, y, w, h, fill=fill, stroke=stroke, rx=h / 2, sw=1)
        self.text(x + w / 2, y + h / 2 + size * 0.36, label, size, fg, 600)
        return w

    # ---------- composite ----------
    def card(self, x, y, w, h, title, lines=(), theme="gray", badge=None, title_size=14):
        fill, stroke, fg = THEMES[theme]
        self.rect(x, y, w, h, fill=fill, stroke=stroke, rx=12)
        cy = y + 24
        if badge:
            self.text(x + 14, cy + 4, badge, 10.5, fg, 700, anchor="start")
            cy += 18
        self.text(x + w / 2, cy + 4, title, title_size, INK, 700)
        cy += 14
        for ln in lines:
            cy += 17
            self.text(x + w / 2, cy, ln, 11.5, SUB, 400)
        return x + w / 2

    def arrow_head_def(self):
        return (
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            'markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="%s"/></marker></defs>'
            % LINE
        )

    def legend(self, x, y, items):
        """items: [(label, theme)]"""
        cur = x
        for label, theme in items:
            fill, stroke, _ = THEMES[theme]
            self.rect(cur, y - 10, 12, 12, fill=fill, stroke=stroke, rx=3, sw=1)
            self.text(cur + 18, y, label, 11.5, SUB, 500, anchor="start")
            cur += 18 + tw(label, 11.5) + 22

    def note(self, x, y, s, size=11):
        self.text(x, y, s, size, MUTED, 400, anchor="start")

    def svg(self):
        head = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (
            self.w, self.h, self.w, self.h)
        return head + self.arrow_head_def() + "".join(self.parts) + "</svg>"
