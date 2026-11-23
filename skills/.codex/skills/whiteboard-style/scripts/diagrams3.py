# -*- coding: utf-8 -*-
"""画板图源 3：bar-chart / line-chart / treemap / flywheel / photo-showcase"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import Canvas, THEMES, INK, SUB, MUTED, LINE, WHITE, tw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "svg")


def save(name, canvas):
    with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
        f.write(canvas.svg())


# ---------------------------------------------------------------- bar chart
def bar_chart():
    c = Canvas(1180, 620, "四种评测模式的首次通过率",
               "横向条形图：按通过率降序排列，标注绝对量与样本量，避免只给百分比")
    data = [("Standard", 88, 420), ("Pro", 81, 860), ("Lite", 74, 1240), ("小白", 62, 2100)]
    left, right = 220, 1040
    top = 160
    row = 82
    maxv = 100
    # 网格
    for tick in range(0, 101, 20):
        x = left + (right - left) * tick / maxv
        c.line(x, top - 22, x, top + row * len(data) - 26, color="#EEF0F3", sw=1)
        c.text(x, top - 30, "%d%%" % tick, 10.5, MUTED, 400)
    for i, (name, val, samples) in enumerate(data):
        y = top + i * row
        c.text(left - 18, y + 24, name, 13, INK, 600, anchor="end")
        c.text(left - 18, y + 44, "n=%s" % format(samples, ","), 10.5, MUTED, 400, anchor="end")
        w = (right - left) * val / maxv
        fill = THEMES["blue"][0] if i else THEMES["amber"][0]
        stroke = THEMES["blue"][1] if i else THEMES["amber"][1]
        c.rect(left, y, w, 34, fill=fill, stroke=stroke, rx=6, sw=1.2)
        c.text(left + w - 12, y + 22, "%d%%" % val, 12.5, INK, 700, anchor="end")
    c.line(left, top + row * len(data) - 26, right, top + row * len(data) - 26, color="#4E5969", sw=1.2)
    c.text(left, top + row * len(data) - 2, "首次通过率", 11, SUB, 500, anchor="start")
    c.rect(220, 496, 820, 66, fill="#FBFCFD", stroke="#E5E6EB", rx=12, sw=1)
    c.text(244, 524, "读法", 12, INK, 700, anchor="start")
    c.text(244, 546, "Standard 通过率最高但样本最小；小白模式样本大、通过率低，说明门槛设置偏严。", 11.5, SUB, 400, anchor="start")
    save("whiteboard_bar_chart", c)


# ---------------------------------------------------------------- line chart
def line_chart():
    c = Canvas(1180, 620, "评测通过率与判分一致性走势",
               "双折线同屏：通过率（左轴 %）与判分一致性（右轴 0-1），单位不同但趋势需要对照")
    months = ["1月", "2月", "3月", "4月", "5月", "6月"]
    pass_rate = [61, 64, 69, 72, 76, 81]
    consistency = [0.78, 0.81, 0.84, 0.86, 0.89, 0.91]
    left, right = 100, 1040
    top, bottom = 170, 470
    # 网格 + 左轴
    for i in range(0, 6):
        v = i * 20
        y = bottom - (bottom - top) * v / 100.0
        c.line(left, y, right, y, color="#EEF0F3", sw=1)
        c.text(left - 14, y + 4, "%d%%" % v, 10.5, MUTED, 400, anchor="end")
    # 右轴
    for i in range(0, 6):
        v = 0.7 + i * 0.06
        y = bottom - (bottom - top) * (v - 0.7) / 0.3
        c.text(right + 14, y + 4, "%.2f" % v, 10.5, MUTED, 400, anchor="start")

    def px(i):
        return left + (right - left) * i / (len(months) - 1)

    def py_pass(v):
        return bottom - (bottom - top) * v / 100.0

    def py_cons(v):
        return bottom - (bottom - top) * (v - 0.7) / 0.3

    # 面积
    pts = [(px(i), py_pass(v)) for i, v in enumerate(pass_rate)]
    area = pts + [(right, bottom), (left, bottom)]
    c.parts.append('<polygon points="%s" fill="#2563EB" fill-opacity="0.08"/>' % " ".join("%.1f,%.1f" % p for p in area))
    c.parts.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>'
                   % (" ".join("%.1f,%.1f" % p for p in pts), THEMES["blue"][1]))
    pts2 = [(px(i), py_cons(v)) for i, v in enumerate(consistency)]
    c.parts.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.6" stroke-dasharray="7 5" stroke-linejoin="round"/>'
                   % (" ".join("%.1f,%.1f" % p for p in pts2), THEMES["amber"][1]))
    for i, v in enumerate(pass_rate):
        c.circle(px(i), py_pass(v), 5, fill="#FFFFFF", stroke=THEMES["blue"][1], sw=2)
        c.text(px(i), py_pass(v) - 14, "%d%%" % v, 11, "#1F4BD8", 600)
    for i, v in enumerate(consistency):
        c.circle(px(i), py_cons(v), 4.5, fill="#FFFFFF", stroke=THEMES["amber"][1], sw=2)
    for i, m in enumerate(months):
        c.text(px(i), bottom + 26, m, 11, SUB, 500)

    c.legend(100, 520, [("通过率（左轴）", "blue"), ("判分一致性（右轴）", "amber")])
    c.note(100, 570, "口径：同一用例集在同版本平台重跑；一致性 = 两次判分一致样本 / 复检样本")
    save("whiteboard_line_chart", c)


# ---------------------------------------------------------------- treemap
def treemap():
    c = Canvas(1180, 640, "评测用例资产构成",
               "矩形树图：面积即用例数占比，大类内含子类；颜色只区分能力域，不表达数值")
    total = 2400
    # 外层区域
    x0, y0, w0, h0 = 40, 150, 780, 440
    c.rect(x0, y0, w0, h0, fill="#FBFCFD", stroke="#DEE0E3", rx=12, sw=1)
    blocks = [
        ("功能正确性", 38, ["单轮问答", "多轮任务"], "blue"),
        ("工具调用", 26, ["选择", "参数", "异常恢复"], "teal"),
        ("多轮对话", 18, ["上下文", "澄清"], "amber"),
        ("安全合规", 12, ["拒答", "越权"], "red"),
        ("性能与成本", 6, ["时延", "Token"], "purple"),
    ]
    # 面积按占比排布：内区 760x420，左列 38% 满高，右侧依次横切 26% / 18%，再竖切 12% / 6%
    ix, iy, iw, ih = x0 + 10, y0 + 10, w0 - 20, h0 - 20
    gap = 10
    lw = iw * 0.38
    c.rect(ix, iy, lw, ih, fill=THEMES["blue"][0], stroke=THEMES["blue"][1], rx=10, sw=1.4)
    c.text(ix + lw / 2, iy + 34, "功能正确性", 15, INK, 700)
    c.text(ix + lw / 2, iy + 58, "38% · 912 条", 11.5, SUB, 500)
    # 子块按条数切分高度：560 : 352 ≈ 61 : 39
    sub_y = iy + 78
    sub_w = lw - 24
    sub_avail = ih - 78 - 20
    sub_h1 = sub_avail * 560.0 / 912.0
    sub_h2 = sub_avail - sub_h1 - 10
    c.rect(ix + 12, sub_y, sub_w, sub_h1, fill="#FFFFFF", stroke=THEMES["blue"][1], rx=8, sw=1)
    c.text(ix + 12 + sub_w / 2, sub_y + sub_h1 / 2 - 4, "单轮问答", 12.5, INK, 600)
    c.text(ix + 12 + sub_w / 2, sub_y + sub_h1 / 2 + 18, "560 条", 11, SUB, 400)
    y2 = sub_y + sub_h1 + 10
    c.rect(ix + 12, y2, sub_w, sub_h2, fill="#FFFFFF", stroke=THEMES["blue"][1], rx=8, sw=1)
    c.text(ix + 12 + sub_w / 2, y2 + sub_h2 / 2 - 4, "多轮任务", 12.5, INK, 600)
    c.text(ix + 12 + sub_w / 2, y2 + sub_h2 / 2 + 18, "352 条", 11, SUB, 400)

    rx = ix + lw + gap
    rw = iw - lw - gap
    # 工具调用 26%
    avail = ih - 2 * gap
    th = avail * 0.26 / 0.62
    c.rect(rx, iy, rw, th, fill=THEMES["teal"][0], stroke=THEMES["teal"][1], rx=10, sw=1.4)
    c.text(rx + 16, iy + 32, "工具调用  26%", 14, INK, 700, anchor="start")
    c.text(rx + 16, iy + 56, "624 条 · 选择 / 参数 / 异常恢复", 11, SUB, 400, anchor="start")
    # 多轮 18%
    my = iy + th + gap
    mh = avail * 0.18 / 0.62
    c.rect(rx, my, rw, mh, fill=THEMES["amber"][0], stroke=THEMES["amber"][1], rx=10, sw=1.4)
    c.text(rx + 16, my + 32, "多轮对话  18%", 13, INK, 700, anchor="start")
    c.text(rx + 16, my + 56, "432 条", 11, SUB, 400, anchor="start")
    # 安全 12% / 性能 6%：同一横带内竖切
    sy = my + mh + gap
    sh = ih - (sy - iy)
    sw_ = rw * 0.12 / (0.12 + 0.06)
    c.rect(rx, sy, sw_ - gap / 2, sh, fill=THEMES["red"][0], stroke=THEMES["red"][1], rx=10, sw=1.4)
    c.text(rx + sw_ / 2 - gap / 4, sy + 32, "安全  12%", 13, INK, 700)
    c.text(rx + sw_ / 2 - gap / 4, sy + 56, "288 条", 11, SUB, 400)
    c.rect(rx + sw_ + gap / 2, sy, rw - sw_ - gap / 2, sh, fill=THEMES["purple"][0], stroke=THEMES["purple"][1], rx=10, sw=1.4)
    c.text(rx + sw_ + gap / 2 + (rw - sw_ - gap / 2) / 2, sy + 32, "性能 6%", 12, INK, 700)
    c.text(rx + sw_ + gap / 2 + (rw - sw_ - gap / 2) / 2, sy + 56, "144 条", 11, SUB, 400)

    # 右侧说明
    c.rect(850, 150, 290, 240, fill="#FBFCFD", stroke="#E5E6EB", rx=12, sw=1)
    c.text(872, 180, "结构健康度", 13, INK, 700, anchor="start")
    notes = ["工具调用仅 26%，异常路径偏少", "安全合规低于 15% 警戒线", "建议 Q3 补 200 条越权用例", "性能用例与线上流量不匹配"]
    y = 212
    for n in notes:
        c.circle(880, y - 4, 3, fill=THEMES["red"][1] if "建议" in n else THEMES["blue"][1],
                 stroke=THEMES["red"][1] if "建议" in n else THEMES["blue"][1], sw=1)
        c.text(892, y, n, 11, SUB, 400, anchor="start")
        y += 38
    c.note(40, 620, "口径：用例总量 2,400 条，按主能力域归类，跨域用例记在主域下；矩形面积按占比近似排布，块间间隙会带来微小偏差")
    save("whiteboard_treemap", c)


# ---------------------------------------------------------------- flywheel
def flywheel():
    c = Canvas(1080, 720, "评测质量飞轮",
               "五个环节首尾相接，每转一圈都会沉淀用例与口径；箭头方向即增益方向")
    cx, cy = 500, 400
    R = 200
    nodes = [
        ("定义口径", "维度 / 权重 / 门槛"),
        ("设计用例", "覆盖边界与异常"),
        ("批量执行", "调度 / 沙箱 / 重试"),
        ("判分归因", "硬伤优先，定位维度"),
        ("回流迭代", "失败样本进用例库"),
    ]
    n = len(nodes)
    positions = []
    for i in range(n):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        x = cx + R * math.cos(ang)
        y = cy + R * math.sin(ang)
        positions.append((x, y, ang))
    # 弧线箭头
    for i in range(n):
        x1, y1, a1 = positions[i]
        x2, y2, a2 = positions[(i + 1) % n]
        ar = R
        large = 0
        # 缩短弧段，避开节点圆
        start = a1 + 0.30
        end = a2 - 0.30 if i < n - 1 else a2 + 2 * math.pi - 0.30
        sx, sy = cx + ar * math.cos(start), cy + ar * math.sin(start)
        ex, ey = cx + ar * math.cos(end), cy + ar * math.sin(end)
        c.parts.append(
            '<path d="M %.1f %.1f A %d %d 0 %d 1 %.1f %.1f" fill="none" stroke="%s" stroke-width="2" marker-end="url(#arrow)"/>'
            % (sx, sy, ar, ar, large, ex, ey, LINE)
        )
    for i, ((x, y, ang), (name, desc)) in enumerate(zip(positions, nodes)):
        theme = ["blue", "teal", "amber", "purple", "green"][i]
        c.circle(x, y, 72, fill=THEMES[theme][0], stroke=THEMES[theme][1], sw=1.8)
        c.text(x, y - 6, name, 14, INK, 700)
        c.text(x, y + 18, desc, 9.8, SUB, 400)
    c.circle(cx, cy, 86, fill="#FFFFFF", stroke="#DEE0E3", sw=1.2)
    c.text(cx, cy - 10, "质量飞轮", 20, INK, 700)
    c.text(cx, cy + 16, "每圈沉淀一次资产", 10.5, SUB, 400)
    c.text(cx, cy + 34, "分数 → 归因 → 用例", 10.5, SUB, 400)

    c.rect(40, 630, 1000, 62, fill="#FBFCFD", stroke="#E5E6EB", rx=12, sw=1)
    c.text(64, 656, "飞轮转速指标", 12.5, INK, 700, anchor="start")
    c.text(64, 678, "单圈周期 2 周　·　失败用例回流率 68%　·　口径变更次数 4 次 / 季　·　复检一致性 0.91", 11.5, SUB, 400, anchor="start")
    save("whiteboard_flywheel", c)


# ---------------------------------------------------------------- photo showcase
def photo_showcase():
    c = Canvas(1200, 610, "评测平台三个核心界面",
               "图片占位展示：无外部素材时用渐变占位块 + 结构线表达版式，接入真实截图后可直接替换")
    cards = [
        ("评测工作台", "任务列表 / 进度 / 失败重试", "blue", 0),
        ("判分详情", "逐条轨迹 / 硬伤标记 / 归因", "teal", 1),
        ("报告输出", "分项得分 / 对比 / 改进建议", "amber", 2),
    ]
    x0, y0 = 40, 150
    cw, ch, gap = 356, 420, 26
    for i, (title, desc, theme, idx) in enumerate(cards):
        x = x0 + i * (cw + gap)
        c.rect(x, y0, cw, ch, fill="#FFFFFF", stroke="#DEE0E3", rx=14)
        # 缩略图占位（渐变 + 结构线）
        c.parts.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="10" fill="url(#g%d)"/>'
            % (x + 12, y0 + 12, cw - 24, 250, idx)
        )
        # 结构线（用线条表达版式，避免嵌套节点被判重叠）
        c.line(x + 28, y0 + 46, x + 124, y0 + 46, color="#FFFFFF", sw=10)
        for k in range(4):
            c.line(x + 28, y0 + 82 + k * 42, x + cw - 28, y0 + 82 + k * 42, color="#FFFFFF", sw=14)
        c.text(x + cw / 2, y0 + 292, title, 16, INK, 700)
        c.text(x + cw / 2, y0 + 318, desc, 11.5, SUB, 400)
        c.pill(x + cw / 2 - 38, y0 + 344, "界面 %d" % (i + 1), theme=theme, size=10.5)
        c.line(x + 12, y0 + 372, x + cw - 12, y0 + 372, color="#EEF0F3", sw=1)
        c.text(x + 16, y0 + 396, "替换方式：把 <img> 或截图上传到画板后覆盖占位块", 10, MUTED, 400, anchor="start")

    defs = ['<defs>']
    grads = [("g0", "#DBEAFE", "#93C5FD"), ("g1", "#CCFBF1", "#5EEAD4"), ("g2", "#FEF3C7", "#FCD34D")]
    for gid, a, b in grads:
        defs.append('<linearGradient id="%s" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>' % (gid, a, b))
    defs.append("</defs>")
    # 将 defs 插到根节点之后（位于箭头 marker 之后）
    c.parts.insert(1, "".join(defs))
    save("whiteboard_photo_showcase", c)


if __name__ == "__main__":
    bar_chart()
    line_chart()
    treemap()
    flywheel()
    # photo_showcase() 已废弃：SVG 画不出真实图片节点，photo-showcase 改走 DSL（assets/dsl/whiteboard_dsl_photo.json）
    print("ok")
