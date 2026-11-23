# -*- coding: utf-8 -*-
"""画板图源 2：fishbone / funnel / pyramid / milestone / comparison"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import Canvas, THEMES, INK, SUB, MUTED, LINE, WHITE, tw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "svg")


def save(name, canvas):
    with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
        f.write(canvas.svg())


# ---------------------------------------------------------------- fishbone
def fishbone():
    c = Canvas(1320, 720, "评测分数偏低的根因拆解",
               "鱼骨图：主骨指向结果，四类原因分列上下；每个分支只保留可验证的具体事实")
    spine_y = 400
    c.line(120, spine_y, 1010, spine_y, color="#4E5969", sw=2.4)
    # 鱼头
    c.rect(1010, spine_y - 66, 250, 132, fill=THEMES["red"][0], stroke=THEMES["red"][1], rx=14)
    c.text(1135, spine_y - 18, "评测分数偏低", 16, INK, 700)
    c.text(1135, spine_y + 8, "通过率低于 70%", 12, SUB, 400)
    c.text(1135, spine_y + 34, "争议样本占比 9%", 12, SUB, 400)

    groups = [
        ("用例质量", ["边界样本缺失", "难度分布失衡", "参考答案过期"], "blue", True, 230),
        ("判分规则", ["硬伤定义模糊", "权重拍脑袋", "裁判模型漂移"], "teal", True, 520),
        ("执行环境", ["工具沙箱超时", "并发抢占资源", "轨迹截断"], "amber", False, 300),
        ("模型与提示词", ["系统提示过长", "工具描述含糊", "缺少少样本"], "purple", False, 620),
    ]
    for name, causes, theme, up, x in groups:
        tip_x = x + 150
        tip_y = spine_y - 190 if up else spine_y + 190
        c.line(x, spine_y, tip_x, tip_y, color=THEMES[theme][1], sw=2)
        c.rect(x - 82, tip_y - 26, 164, 44, fill=THEMES[theme][0], stroke=THEMES[theme][1], rx=10)
        c.text(x, tip_y - 2, name, 13, INK, 700)
        # 分支小骨
        for k, cause in enumerate(causes):
            t = 0.35 + k * 0.2
            bx = x + (tip_x - x) * t
            by = spine_y + (tip_y - spine_y) * t
            c.line(bx, by, bx + 26, by, color=THEMES[theme][1], sw=1.2)
            anchor_x = bx + 30
            c.text(anchor_x, by + 4, cause, 11.5, SUB, 400, anchor="start")

    c.rect(40, 626, 1240, 62, fill="#FBFCFD", stroke="#E5E6EB", rx=12, sw=1)
    c.text(64, 652, "优先处理", 12.5, INK, 700, anchor="start")
    c.text(64, 674, "① 重写硬伤定义并给出正反例　② 用例难度按 3:5:2 重建　③ 判分一致性抽检从 100 条提到 300 条", 11.5, SUB, 400, anchor="start")
    save("whiteboard_fishbone", c)


# ---------------------------------------------------------------- funnel
def funnel():
    c = Canvas(1240, 700, "从候选模型到正式上线的五级漏斗",
               "每层给出绝对量与相对上一层的转化率；最大流失点用唯一强调色标注")
    stages = [
        ("候选模型", 1200, 100, ""),
        ("通过准入测试", 864, 72, "72.0%"),
        ("通过全量评测", 518, 60, "59.9%"),
        ("进入灰度", 259, 50, "50.0%"),
        ("正式上线", 130, 39, "50.2%"),
    ]
    top, h, gap = 150, 78, 14
    cx = 470
    for i, (name, val, pct, conv) in enumerate(stages):
        y = top + i * (h + gap)
        half_top = 300 * (pct / 100.0)
        next_pct = stages[i + 1][2] if i + 1 < len(stages) else pct * 0.62
        half_bottom = 300 * (next_pct / 100.0)
        color = THEMES["red"] if i == 2 else THEMES["blue"]
        c.parts.append(
            '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s" fill-opacity="0.9" stroke="#FFFFFF" stroke-width="2"/>'
            % (cx - half_top, y, cx + half_top, y, cx + half_bottom, y + h, cx - half_bottom, y + h, color[1])
        )
        c.text(cx, y + h / 2 + 2, name, 14, "#FFFFFF", 700)
        c.text(cx, y + h / 2 + 22, "%s 个" % format(val, ","), 11.5, "#FFFFFF", 500)
        if conv:
            c.text(cx + 330, y + h / 2 + 2, "转化 %s" % conv, 13, SUB, 600, anchor="start")
            c.polyline([(cx + half_top + 8, y + 4), (cx + 316, y + h / 2)], color=LINE, sw=1, arrow=False)
        c.text(cx - 330, y + h / 2 + 6, "L%d" % (i + 1), 12, MUTED, 600, anchor="end")

    c.rect(830, 150, 366, 246, fill="#FBFCFD", stroke="#E5E6EB", rx=12, sw=1)
    c.text(852, 180, "关键结论", 13, INK, 700, anchor="start")
    lines = [
        "准入测试淘汰 28%，主要因为工具调用不达标",
        "全量评测再淘汰 40%，是最大流失环节",
        "灰度到上线转化 50.2%，回滚 4 次",
        "建议：把全量评测的失败用例回流到准入集",
    ]
    y = 210
    for ln in lines:
        c.circle(860, y - 4, 3, fill=THEMES["blue"][1], stroke=THEMES["blue"][1], sw=1)
        c.text(872, y, ln, 11.5, SUB, 400, anchor="start")
        y += 40

    c.note(40, 660, "口径：统计窗口 2026 Q1-Q3，同一模型多次提交只计首次结果")
    save("whiteboard_funnel", c)


# ---------------------------------------------------------------- pyramid
def pyramid():
    c = Canvas(1240, 700, "评测能力成熟度四层金字塔",
               "自下而上收敛：底座是数据与工具，塔尖是决策结论；每层给出可验收的判断标准")
    levels = [
        ("决策层", "用评测结论做发布决策", 0.30, "amber"),
        ("洞察层", "归因到能力维度，给出改进项", 0.52, "purple"),
        ("执行层", "稳定跑完批次，产出可复现报告", 0.74, "teal"),
        ("数据层", "用例、轨迹、判分结果可追溯", 0.96, "blue"),
    ]
    cx = 430
    top = 148
    h = 104
    gap = 12
    for i, (name, desc, ratio, theme) in enumerate(levels):
        y = top + i * (h + gap)
        half_top = 330 * (ratio - 0.18 if i else 0.10)
        half_top = max(half_top, 40)
        half_bottom = 330 * ratio
        c.parts.append(
            '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s" stroke="%s" stroke-width="1.6"/>'
            % (cx - half_top, y, cx + half_top, y, cx + half_bottom, y + h, cx - half_bottom, y + h,
               THEMES[theme][0], THEMES[theme][1])
        )
        c.text(cx, y + h / 2 - 2, name, 15, INK, 700)
        c.text(cx, y + h / 2 + 22, desc, 11.5, SUB, 400)
        c.text(cx - half_bottom - 18, y + h / 2 + 6, "L%d" % (4 - i), 12, MUTED, 600, anchor="end")

    c.rect(800, 148, 396, 300, fill="#FBFCFD", stroke="#E5E6EB", rx=12, sw=1)
    c.text(822, 178, "各层验收信号", 13, INK, 700, anchor="start")
    rows = [
        ("L4 决策层", "发布 / 不发布结论有一票否决位", "amber"),
        ("L3 洞察层", "每个失败项都能定位到维度与用例", "purple"),
        ("L2 执行层", "同批次重跑分数差异 < 1 分", "teal"),
        ("L1 数据层", "任一分数可回放到原始轨迹", "blue"),
    ]
    y = 214
    for tag, txt, theme in rows:
        c.pill(822, y - 16, tag, theme=theme, size=10.5)
        c.text(822, y + 22, txt, 11, SUB, 400, anchor="start")
        y += 60

    c.note(40, 660, "越靠下越强调可复现，越靠上越强调可解释；不要跳级建设")
    save("whiteboard_pyramid", c)


# ---------------------------------------------------------------- milestone
def milestone():
    c = Canvas(1560, 640, "2026 评测平台里程碑（截至 11 月）",
               "横向时间轴按 12 个月均匀排布；实心节点为硬里程碑，空心节点为检查点，红色竖线标注当前时间")
    axis_y = 340
    x0, x1 = 150, 1440
    step = (x1 - x0) / 11.0
    c.line(x0, axis_y, x1, axis_y, color="#4E5969", sw=2)
    c.pill(40, axis_y - 40, "2026 全年", theme="gray", size=10.5)

    def mx(month):
        return x0 + (month - 1) * step

    items = [
        (1, "评测口径 v1", ["维度 / 权重冻结", "硬伤清单发布"], True, "blue", True),
        (2, "平台内测", ["调度 + 沙箱可用", "10 个用例集接入"], True, "teal", False),
        (3, "全量评测跑通", ["覆盖 6 大能力域", "报告模板定稿"], True, "amber", True),
        (4, "灰度上线", ["两批放量", "回滚预案演练"], True, "purple", False),
        (5, "标准化输出", ["对外白皮书", "口径对齐业务方"], True, "blue", True),
        (6, "半年度复盘", ["问题清单闭环", "下半年规划"], False, "gray", False),
        (8, "多模态评测", ["图像 / 语音用例", "人工抽检机制"], True, "teal", True),
        (10, "裁判模型 v2", ["换模型对齐实验", "偏差收敛到 1 分内"], True, "purple", False),
        (12, "年度口径冻结", ["年度榜单发布", "明年口径预研"], True, "blue", True),
    ]

    # 月份刻度
    for m in range(1, 13):
        x = mx(m)
        c.line(x, axis_y - 4, x, axis_y + 4, color="#86909C", sw=1.2)
        c.text(x, axis_y + 28, "%d 月" % m, 10.5, SUB, 500)

    now_x = mx(11) + step * 0.34
    c.line(now_x, 120, now_x, 528, color=THEMES["red"][1], sw=1.4, dash="6 5")
    c.pill(now_x - 34, 104, "今天 11/12", theme="red", size=10.5)

    for month, title, lines, filled, theme, up in items:
        x = mx(month)
        if filled:
            c.circle(x, axis_y, 9, fill=THEMES[theme][1], stroke="#FFFFFF", sw=2)
        else:
            c.circle(x, axis_y, 9, fill="#FFFFFF", stroke=THEMES[theme][1], sw=2)
        c.line(x, axis_y - 12 if up else axis_y + 12, x, axis_y - 60 if up else axis_y + 60, color=LINE, sw=1.2)
        box_y = axis_y - 176 if up else axis_y + 66
        c.card(x - 109, box_y, 218, 112, title, lines, theme=theme, title_size=12)
    dx = 0

    c.note(40, 594, "排期口径：以可验收的交付物为准，不以工时占比表达；里程碑延误超过 5 个工作日需重排后续节点")
    save("whiteboard_milestone", c)


# ---------------------------------------------------------------- comparison
def comparison():
    c = Canvas(1320, 700, "四种评测模式的取舍",
               "对比矩阵：同一组验收维度横向比较，结论区给出默认推荐与例外条件")
    cols = [
        ("小白模式", "零配置开箱即用", "gray", ["自动生成用例", "单一总分", "人工复核可选", "1 小时内出结果"]),
        ("Lite", "轻量自定义", "teal", ["自选用例集", "总分 + 分项", "规则判分", "半天内出结果"]),
        ("Pro", "专业可编排", "blue", ["自定义维度权重", "硬伤 / 瑕疵分级", "裁判模型 + 规则", "支持批量对比"]),
        ("Standard", "标准化对外", "purple", ["固定口径与模板", "可审计的判分链", "双人复核", "报告可直接对外"]),
    ]
    x0, y0 = 40, 170
    cw, ch, gap = 300, 300, 16
    c.text(x0, 152, "维度", 12, SUB, 700, anchor="start")
    for i, (name, tagline, theme, items) in enumerate(cols):
        x = x0 + i * (cw + gap)
        c.rect(x, y0, cw, ch, fill="#FFFFFF", stroke=THEMES[theme][1], rx=14, sw=1.4)
        c.rect(x, y0, cw, 64, fill=THEMES[theme][0], stroke=THEMES[theme][1], rx=14, sw=1.2)
        c.text(x + cw / 2, y0 + 30, name, 16, INK, 700)
        c.text(x + cw / 2, y0 + 52, tagline, 11, SUB, 400)
        yy = y0 + 92
        for it in items:
            c.text(x + 18, yy, "·", 13, THEMES[theme][1], 700, anchor="start")
            c.text(x + 32, yy, it, 11.5, SUB, 400, anchor="start")
            yy += 34
        score = ["1", "2", "3", "5"][i]
        c.text(x + cw / 2, y0 + ch - 26, "适用复杂度  %s / 5" % score, 11, MUTED, 500)

    c.rect(40, 500, 1240, 150, fill="#FBFCFD", stroke="#E5E6EB", rx=14, sw=1)
    c.text(64, 530, "选择建议", 13, INK, 700, anchor="start")
    rules = [
        ("默认", "Pro：需要归因和批量对比的团队，默认走 Pro，避免口径反复。", "blue"),
        ("例外 1", "只做冒烟验证 → 小白模式，1 小时内拿到方向性结论。", "gray"),
        ("例外 2", "对外交付或合规审计 → Standard，报告需双人复核并留判分链。", "purple"),
    ]
    y = 558
    for tag, txt, theme in rules:
        c.pill(64, y - 14, tag, theme=theme, size=10)
        c.text(150, y, txt, 11.5, SUB, 400, anchor="start")
        y += 30
    save("whiteboard_comparison", c)


if __name__ == "__main__":
    fishbone()
    funnel()
    pyramid()
    milestone()
    comparison()
    print("ok")
