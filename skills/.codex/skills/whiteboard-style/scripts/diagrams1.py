# -*- coding: utf-8 -*-
"""画板图源 1：architecture / flowchart / organization / swimlane"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import Canvas, THEMES, INK, SUB, MUTED, LINE, WHITE, tw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "svg")
os.makedirs(OUT, exist_ok=True)


def save(name, canvas):
    with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
        f.write(canvas.svg())


# ---------------------------------------------------------------- architecture
def architecture():
    c = Canvas(1280, 810, "Agent 评测平台四层架构",
               "自上而下：接入 → 编排 → 能力 → 数据；同层组件等宽等高，跨层只保留主链路")
    layers = [
        ("接入层", [("Web 控制台", "控制台发起与看结果"), ("OpenAPI", "供外部系统程序化调用"),
                 ("CLI 与 SDK", "本地与 CI 内直接跑")], "blue"),
        ("编排层", [("任务调度", "排队、分片与重试"), ("用例加载", "按用例集拉取样本"),
                 ("并发执行", "沙箱内并行跑批"), ("结果聚合", "合并分项与硬伤")], "teal"),
        ("能力层", [("模型网关", "统一模型与配额入口"), ("工具沙箱", "隔离工具调用环境"),
                 ("判分器", "规则 + 裁判模型"), ("轨迹回放", "重放原始执行轨迹")], "amber"),
        ("数据层", [("用例库", "版本化用例集"), ("结果仓库", "分数与轨迹落库"),
                 ("指标看板", "趋势与横向对比")], "purple"),
    ]
    top = 112
    band_h = 138
    gap = 20
    left = 40
    band_w = 1200
    label_w = 112
    for i, (name, nodes, theme) in enumerate(layers):
        y = top + i * (band_h + gap)
        c.rect(left, y, band_w, band_h, fill="#FBFCFD", stroke="#E5E6EB", rx=14, sw=1)
        c.rect(left + 12, y + 12, label_w - 12, band_h - 24, fill=THEMES[theme][0], stroke=THEMES[theme][1], rx=10, sw=1)
        c.text(left + 12 + (label_w - 12) / 2, y + band_h / 2 - 6, name, 14, INK, 700)
        c.text(left + 12 + (label_w - 12) / 2, y + band_h / 2 + 16, "L%d" % (i + 1), 11, SUB, 500)

        area_x = left + label_w + 16
        area_w = band_w - label_w - 32
        n = len(nodes)
        node_gap = 16
        node_w = (area_w - node_gap * (n - 1)) / n
        for j, (node, desc) in enumerate(nodes):
            x = area_x + j * (node_w + node_gap)
            c.card(x, y + 22, node_w, band_h - 44, node, [desc], theme=theme, title_size=13.5)
            if i < len(layers) - 1:
                c.polyline([(x + node_w / 2, y + band_h - 22), (x + node_w / 2, y + band_h + 4),
                            (x + node_w / 2, y + band_h + gap - 22)], color=LINE, sw=1.3, arrow=True)

    c.legend(40, 778, [("接入", "blue"), ("编排", "teal"), ("能力", "amber"), ("数据", "purple")])
    c.note(980, 778, "同层组件可横向替换，跨层通过接口契约解耦")
    save("whiteboard_architecture", c)


# ---------------------------------------------------------------- flowchart
def flowchart():
    c = Canvas(1320, 620, "一次评测任务从提交到报告的完整链路",
               "主链路从左到右 6 步；失败与人工复核只做短回流，不打断主路径")
    steps = [
        ("提交任务", ["选择用例集", "指定模型与模式"], "blue"),
        ("校验用例", ["字段完整性", "权限与配额"], "blue"),
        ("并发执行", ["按用例切片", "失败自动重试"], "teal"),
        ("模型作答", ["工具调用", "多轮轨迹记录"], "teal"),
        ("自动判分", ["规则 + 裁判模型", "硬伤优先"], "amber"),
        ("生成报告", ["分数 / 归因", "对比与建议"], "green"),
    ]
    x0, y0 = 40, 170
    w, h, gap = 176, 118, 34
    centers = []
    for i, (title, lines, theme) in enumerate(steps):
        x = x0 + i * (w + gap)
        c.card(x, y0, w, h, title, lines, theme=theme)
        centers.append((x, y0, w, h))
        if i:
            px, py, pw, ph = centers[i - 1]
            c.polyline([(px + pw, y0 + h / 2), (x - 4, y0 + h / 2)], color=LINE, sw=1.6, arrow=True)
    # branch: 自动判分 -> 人工复核 -> 生成报告
    ax, ay, aw, ah = centers[4]
    bx, by, bw, bh = centers[5]
    c.card(ax + 20, y0 + 210, aw - 20, 92, "人工复核", ["争议样本抽检", "标注结论回流用例库"], theme="red")
    c.polyline([(ax + aw / 2, y0 + h), (ax + aw / 2, y0 + 206)], color=LINE, sw=1.4, dash="5 4", arrow=True)
    c.polyline([(ax + aw - 2, y0 + 256), (bx + bw / 2, y0 + 256), (bx + bw / 2, y0 + h + 6)],
               color=LINE, sw=1.4, dash="5 4", arrow=True)
    c.text(ax + aw / 2 + 8, y0 + h + 26, "争议样本", 10.5, MUTED, 400, anchor="start")
    # 回流
    c.polyline([(centers[1][0] + w / 2, y0 + h), (centers[1][0] + w / 2, y0 + 268),
                (centers[0][0] + w / 2, y0 + 268), (centers[0][0] + w / 2, y0 + h + 6)],
               color=LINE, sw=1.4, dash="5 4", arrow=True)
    c.text(centers[1][0] - 96, y0 + 262, "用例不合法：退回修改", 10.5, MUTED, 400, anchor="start")

    # 底部指标条
    c.rect(40, 452, 1240, 96, fill="#FBFCFD", stroke="#E5E6EB", rx=14, sw=1)
    c.text(64, 480, "链路关键指标", 13, INK, 700, anchor="start")
    metrics = [("任务成功率", "99.2%"), ("P95 端到端耗时", "8 分 40 秒"), ("判分一致性", "0.91"), ("失败重试命中", "76%")]
    for i, (k, v) in enumerate(metrics):
        x = 64 + i * 306
        c.text(x, 512, v, 22, "#1F4BD8", 700, anchor="start")
        c.text(x, 534, k, 11.5, SUB, 400, anchor="start")
    save("whiteboard_flowchart", c)


# ---------------------------------------------------------------- organization
def organization():
    c = Canvas(1240, 700, "评测团队组织与职责边界",
               "三层结构：目标层 → 职能层 → 执行小组；同级团队等宽，避免跨级汇报线")
    # 顶层
    c.rect(470, 108, 300, 84, fill=THEMES["blue"][0], stroke=THEMES["blue"][1], rx=14)
    c.text(620, 140, "评测委员会", 16, INK, 700)
    c.text(620, 164, "定义口径 · 裁决争议 · 发布结论", 11.5, SUB, 400)

    depts = [
        ("标准与规则组", ["评测维度设计", "硬伤 / 瑕疵判定", "版本化规则库"], "teal"),
        ("平台与工具组", ["评测平台建设", "自动化流水线", "数据与看板"], "amber"),
        ("执行与运营组", ["用例维护", "批次执行", "报告与复盘"], "purple"),
    ]
    dw, dh, gap = 340, 132, 40
    total = dw * 3 + gap * 2
    x0 = (1240 - total) / 2
    for i, (name, items, theme) in enumerate(depts):
        x = x0 + i * (dw + gap)
        c.card(x, 268, dw, dh, name, items, theme=theme, title_size=14)
        c.polyline([(620, 192), (620, 228), (x + dw / 2, 228), (x + dw / 2, 264)], color=LINE, sw=1.4, arrow=True)

    teams = [
        ("规则评审小组", "3 人 · 双周评审"),
        ("标签与用例小组", "4 人 · 按领域分包"),
        ("平台研发小组", "5 人 · 双周迭代"),
        ("数据运营小组", "2 人 · 日报口径"),
    ]
    tw_, th, tgap = 250, 84, 24
    tx0 = (1240 - (tw_ * 4 + tgap * 3)) / 2
    for i, (name, meta) in enumerate(teams):
        x = tx0 + i * (tw_ + tgap)
        c.rect(x, 470, tw_, th, fill="#FFFFFF", stroke="#DEE0E3", rx=10)
        c.circle(x + 22, 496, 5, fill=THEMES["blue"][1], stroke=THEMES["blue"][1], sw=1)
        c.text(x + 36, 500, name, 12.5, INK, 600, anchor="start")
        c.text(x + 36, 526, meta, 10.5, SUB, 400, anchor="start")
        c.polyline([(x + tw_ / 2, 400), (x + tw_ / 2, 466)], color=LINE, sw=1.1, dash="4 4", arrow=False)

    c.rect(40, 600, 1160, 62, fill="#FBFCFD", stroke="#E5E6EB", rx=12, sw=1)
    c.text(64, 626, "协作约定", 12.5, INK, 700, anchor="start")
    c.text(64, 648, "规则变更需标准组 + 平台组双签；批次执行由运营组发起；争议样本 24 小时内闭环", 11.5, SUB, 400, anchor="start")
    save("whiteboard_organization", c)


# ---------------------------------------------------------------- swimlane
def swimlane():
    c = Canvas(1320, 720, "评测平台建设：四个阶段 × 三条泳道",
               "泳道等高、标题固定在左侧；只保留跨泳道主链路，避免连线穿越卡片")
    lanes = [("产品", "blue"), ("算法", "teal"), ("工程", "amber")]
    cols = ["① 定义", "② 建设", "③ 验证", "④ 发布"]
    grid_x, grid_y = 168, 168
    col_w, row_h = 276, 150
    c.rect(grid_x, grid_y - 36, col_w * 4, 34, fill="#FBFCFD", stroke="#E5E6EB", rx=8, sw=1)
    for i, col in enumerate(cols):
        c.text(grid_x + i * col_w + col_w / 2, grid_y - 14, col, 12.5, SUB, 700)

    for i, (lane, theme) in enumerate(lanes):
        y = grid_y + i * row_h
        c.rect(40, y, grid_x - 56, row_h - 14, fill=THEMES[theme][0], stroke=THEMES[theme][1], rx=10, sw=1)
        c.text(40 + (grid_x - 56) / 2, y + row_h / 2 - 4, lane, 15, INK, 700)
        c.text(40 + (grid_x - 56) / 2, y + row_h / 2 + 18, "Lane %d" % (i + 1), 10.5, SUB, 400)
        c.rect(grid_x, y, col_w * 4, row_h - 14, fill="#FFFFFF", stroke="#EEF0F3", rx=8, sw=1)

    cards = {
        (0, 0): ("评测口径", "维度 / 权重 / 门槛"),
        (0, 1): ("用例设计", "覆盖 6 大能力域"),
        (0, 2): ("验收标准", "对齐业务目标"),
        (0, 3): ("发布说明", "口径变更记录"),
        (1, 1): ("判分策略", "规则 + 裁判模型"),
        (1, 2): ("一致性校准", "抽检 300 条样本"),
        (1, 3): ("基线模型", "版本冻结与对比"),
        (2, 1): ("平台实现", "调度 / 沙箱 / 报告"),
        (2, 2): ("压测与回放", "并发 200 任务"),
        (2, 3): ("灰度上线", "两批放量 + 回滚位"),
    }
    for (r, col), (title, sub) in cards.items():
        x = grid_x + col * col_w + 14
        y = grid_y + r * row_h + 16
        theme = lanes[r][1]
        c.card(x, y, col_w - 28, 104, title, [sub], theme=theme, title_size=12.5)

    # 主链路（仅跨泳道关键依赖）
    c.polyline([(grid_x + col_w - 20, grid_y + 68), (grid_x + col_w + 4, grid_y + 68)], color=LINE, sw=1.4, arrow=True)
    c.polyline([(grid_x + col_w * 2 - 20, grid_y + 68), (grid_x + col_w * 2 + 4, grid_y + 68)], color=LINE, sw=1.4, arrow=True)
    c.polyline([(grid_x + col_w * 2 + col_w / 2, grid_y + 126), (grid_x + col_w * 2 + col_w / 2, grid_y + row_h + 10)],
               color=LINE, sw=1.4, dash="5 4", arrow=True)
    c.polyline([(grid_x + col_w * 3 + col_w / 2, grid_y + row_h + 92), (grid_x + col_w * 3 + col_w / 2, grid_y + row_h * 2 + 10)],
               color=LINE, sw=1.4, dash="5 4", arrow=True)

    c.legend(40, 690, [("产品", "blue"), ("算法", "teal"), ("工程", "amber")])
    c.note(700, 690, "实线为主链路，虚线为跨泳道交付依赖")
    save("whiteboard_swimlane", c)


if __name__ == "__main__":
    architecture()
    flowchart()
    organization()
    swimlane()
    print("ok")
