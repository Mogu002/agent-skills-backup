# -*- coding: utf-8 -*-
"""B 组：分布与统计（8 类型）"""
from base import render_echarts

CHARTS = {}

CHARTS["b1_scatter_bubble"] = render_echarts(
    "b1_scatter_bubble",
    "高增长客户集中在 80-180 规模区间",
    "散点 / 气泡图：x 为客户规模，y 为增速，气泡面积为收入体量（万元）",
    """
  var DATA = [
    [50, 18, 30, "客户 A"], [120, 32, 80, "客户 B"], [90, 12, 45, "客户 C"],
    [160, 28, 120, "客户 D"], [210, 9, 60, "客户 E"], [70, 24, 26, "客户 F"], [140, 15, 95, "客户 G"]
  ];
  var option = {
    animation: false,
    tooltip: { formatter: function (p) { return p.data[3] + "<br/>规模: " + p.data[0] + "<br/>增速: " + p.data[1] + "%<br/>收入: " + p.data[2] + " 万元"; } },
    grid: { left: 62, right: 62, top: 34, bottom: 48 },
    xAxis: { type: "value", name: "客户规模", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
    yAxis: { type: "value", name: "增速%", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563", formatter: "{value}%" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
    series: [{
      type: "scatter",
      symbolSize: function (d) { return Math.max(10, Math.sqrt(d[2]) * 2.2); },
      data: DATA, itemStyle: { color: C.blue, opacity: .72 },
      label: { show: true, position: "top", fontSize: 11, color: "#4b5563", formatter: function (p) { return p.data[3]; } }
    }]
  };
""",
    height=400,
)

CHARTS["b2_ripple_scatter"] = render_echarts(
    "b2_ripple_scatter",
    "重点客户 D 是唯一规模与增速双高样本",
    "涟漪气泡散点：普通样本静态散点，重点样本用 effectScatter 高亮，气泡大小映射收入",
    """
  var normal = [[50, 18, 30, "客户 A"], [120, 32, 80, "客户 B"], [90, 12, 45, "客户 C"], [210, 9, 60, "客户 E"], [70, 24, 26, "客户 F"], [140, 15, 95, "客户 G"]];
  var highlights = [[160, 42, 120, "重点客户 D"]];
  var option = {
    animation: false,
    tooltip: { formatter: function (p) { return p.data[3] + "<br/>规模: " + p.data[0] + "<br/>增速: " + p.data[1] + "%<br/>收入: " + p.data[2] + " 万元"; } },
    grid: { left: 62, right: 66, top: 34, bottom: 48 },
    xAxis: { type: "value", name: "客户规模", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
    yAxis: { type: "value", name: "增速%", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563", formatter: "{value}%" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
    series: [
      { type: "scatter", symbolSize: function (d) { return Math.max(10, Math.sqrt(d[2]) * 2.2); }, data: normal, itemStyle: { color: "#93c5fd", opacity: .85 } },
      { type: "effectScatter", symbolSize: function (d) { return Math.max(16, Math.sqrt(d[2]) * 2.2); }, rippleEffect: { scale: 2.6, brushType: "stroke" }, data: highlights, itemStyle: { color: C.amber }, label: { show: true, formatter: function (p) { return p.data[3]; }, position: "right", color: "#b45309", fontWeight: 600 } }
    ]
  };
""",
    height=400,
)

CHARTS["b3_heatmap"] = render_echarts(
    "b3_heatmap",
    "工作日晚间与周一上午是请求高峰",
    "热力图：星期 × 时段的任务提交密度（次/千次），必须保留 visualMap 让颜色可解释",
    """
  var hours = ["0-6", "6-9", "9-12", "12-15", "15-18", "18-21", "21-24"];
  var days = ["Mon", "Tue", "Wed", "Thu", "Fri"];
  var raw = [
    [12, 48, 86, 54, 72, 64, 30], [10, 44, 78, 50, 68, 58, 26], [9, 42, 74, 46, 64, 55, 24],
    [11, 45, 80, 49, 70, 60, 28], [14, 52, 90, 58, 76, 70, 34]
  ];
  var data = [];
  for (var y = 0; y < days.length; y++) for (var x = 0; x < hours.length; x++) data.push([x, y, raw[y][x]]);
  var option = {
    animation: false,
    tooltip: { position: "top", formatter: function (p) { return days[p.data[1]] + " " + hours[p.data[0]] + ": " + p.data[2]; } },
    grid: { left: 62, right: 26, top: 26, bottom: 66 },
    xAxis: { type: "category", data: hours, axisLabel: { color: "#4b5563" }, splitArea: { show: true } },
    yAxis: { type: "category", data: days, axisLabel: { color: "#4b5563" }, splitArea: { show: true } },
    visualMap: { min: 0, max: 100, orient: "horizontal", left: "center", bottom: 8, textStyle: { color: "#6b7280" }, inRange: { color: ["#eff6ff", "#93c5fd", "#2563eb", "#1e3a8a"] } },
    series: [{ type: "heatmap", data: data, label: { show: true, fontSize: 10, color: "#1f2937" }, itemStyle: { borderColor: "#ffffff", borderWidth: 2 } }]
  };
""",
    height=380,
)

CHARTS["b4_matrix_heatmap"] = render_echarts(
    "b4_matrix_heatmap",
    "东区转化与留存双高，西区曝光强但转化偏弱",
    "矩阵热力图：区域 × 指标交叉对比（0-100 标准化分），颜色刻度统一",
    """
  var teams = ["北区", "东区", "南区", "西区"];
  var metrics = ["曝光", "点击", "转化", "留存"];
  var matrix = [
    [0, 0, 82], [1, 0, 67], [2, 0, 55], [3, 0, 73],
    [0, 1, 64], [1, 1, 88], [2, 1, 46], [3, 1, 69],
    [0, 2, 41], [1, 2, 52], [2, 2, 38], [3, 2, 57],
    [0, 3, 72], [1, 3, 91], [2, 3, 49], [3, 3, 66]
  ];
  var option = {
    animation: false,
    tooltip: { formatter: function (p) { return teams[p.data[0]] + " / " + metrics[p.data[1]] + ": " + p.data[2]; } },
    grid: { left: 68, right: 26, top: 26, bottom: 66 },
    xAxis: { type: "category", data: teams, axisLabel: { color: "#4b5563" }, splitArea: { show: true } },
    yAxis: { type: "category", data: metrics, axisLabel: { color: "#4b5563" }, splitArea: { show: true } },
    visualMap: { min: 0, max: 100, orient: "horizontal", left: "center", bottom: 8, itemWidth: 14, itemHeight: 90, text: ["100", "0"], textStyle: { color: "#6b7280" }, inRange: { color: ["#f0fdfa", "#99f6e4", "#5eead4", "#2dd4bf"] } },
    series: [{ type: "heatmap", data: matrix, label: { show: true, fontSize: 11, color: "#0f172a" }, itemStyle: { borderColor: "#ffffff", borderWidth: 2 } }]
  };
""",
    height=380,
)

CHARTS["b5_calendar_heatmap"] = render_echarts(
    "b5_calendar_heatmap",
    "全年 3 月与 10 月是任务提交双高峰",
    "全年日历热力图：2026 年每日任务量（次），日期区间与标题口径一致",
    """
  var year = "2026";
  var dayMs = 24 * 60 * 60 * 1000;
  var start = +new Date(year + "-01-01");
  var end = +new Date(year + "-12-31");
  var data = [];
  for (var t = start; t <= end; t += dayMs) {
    var date = echarts.format.formatTime("yyyy-MM-dd", t);
    var m = +date.slice(5, 7);
    var base = (m === 3 || m === 10) ? 62 : (m === 1 || m === 5) ? 38 : 26;
    var v = Math.max(4, Math.round(base + ((t / dayMs) % 9) * 3 + (m % 4) * 4));
    data.push([date, v]);
  }
  var option = {
    animation: false,
    tooltip: { formatter: function (p) { return p.data[0] + ": " + p.data[1] + " 次"; } },
    visualMap: { min: 0, max: 100, orient: "horizontal", left: "center", bottom: 6, textStyle: { color: "#6b7280" }, inRange: { color: ["#eff6ff", "#93c5fd", "#2563eb", "#1e3a8a"] } },
    calendar: { top: 30, left: 44, right: 26, cellSize: ["auto", 13], range: year, itemStyle: { borderWidth: 0.6, borderColor: "#ffffff" }, yearLabel: { show: true, color: "#374151", fontSize: 12 }, dayLabel: { color: "#6b7280", fontSize: 10 }, monthLabel: { color: "#6b7280", fontSize: 10 } },
    series: [{ type: "heatmap", coordinateSystem: "calendar", data: data }]
  };
""",
    height=300,
)

CHARTS["b6_candlestick"] = render_echarts(
    "b6_candlestick",
    "本周行情先抑后扬，周四放量长阳",
    "K 线蜡烛图：数据顺序 [open, close, low, high]，红涨绿跌与 A 股习惯一致",
    """
  var option = {
    animation: false,
    tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
    grid: { left: 58, right: 30, top: 32, bottom: 46 },
    xAxis: { type: "category", data: ["Mon", "Tue", "Wed", "Thu", "Fri"], axisLabel: { color: "#4b5563" }, axisLine: { lineStyle: { color: "#d1d5db" } } },
    yAxis: { scale: true, name: "价格", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
    series: [{
      type: "candlestick",
      data: [[20, 34, 18, 38], [34, 28, 26, 40], [28, 33, 24, 36], [33, 46, 31, 48], [46, 43, 40, 50]],
      itemStyle: { color: "#ef4444", color0: "#10b981", borderColor: "#ef4444", borderColor0: "#10b981" }
    }]
  };
""",
    height=380,
)

CHARTS["b7_parallel"] = render_echarts(
    "b7_parallel",
    "门店 3 客流与转化最优，门店 4 客单价高但转化弱",
    "平行坐标图：4 家门店在客流 / 客单价 / 转化率 / 复购率四个维度上的轮廓",
    """
  var option = {
    animation: false,
    tooltip: { trigger: "item" },
    parallelAxis: [
      { dim: 0, name: "客流", min: 600, max: 1700, nameTextStyle: { color: "#374151" } },
      { dim: 1, name: "客单价", min: 60, max: 150, nameTextStyle: { color: "#374151" } },
      { dim: 2, name: "转化率%", min: 8, max: 26, nameTextStyle: { color: "#374151" } },
      { dim: 3, name: "复购率%", min: 20, max: 40, nameTextStyle: { color: "#374151" } }
    ],
    parallel: { left: 62, right: 56, top: 74, bottom: 56, parallelAxisDefault: { type: "value", nameTextStyle: { color: "#374151" }, axisLabel: { color: "#6b7280" }, splitLine: { lineStyle: { color: "#eef1f5" } } } },
    series: [
      { name: "门店 1", type: "parallel", lineStyle: { width: 2, opacity: .55, color: C.blue }, data: [[1200, 86, 18, 32]] },
      { name: "门店 2", type: "parallel", lineStyle: { width: 2, opacity: .55, color: C.green }, data: [[980, 112, 14, 28]] },
      { name: "门店 3", type: "parallel", lineStyle: { width: 3, opacity: .95, color: C.amber }, data: [[1500, 75, 22, 36]] },
      { name: "门店 4", type: "parallel", lineStyle: { width: 2, opacity: .55, color: C.purple }, data: [[760, 134, 11, 25]] }
    ],
    legend: { bottom: 4, itemWidth: 12, itemHeight: 8, textStyle: { color: "#4b5563", fontSize: 12 } }
  };
""",
    height=430,
)

CHARTS["b8_boxplot"] = render_echarts(
    "b8_boxplot",
    "服务 B 延迟离散度最大，存在 240ms 长尾异常",
    "箱线图：数据顺序 [min, Q1, median, Q3, max]，异常点用 scatter 单独标注",
    """
  var option = {
    animation: false,
    tooltip: { trigger: "item" },
    grid: { left: 58, right: 30, top: 32, bottom: 46 },
    xAxis: { type: "category", data: ["服务 A", "服务 B", "服务 C"], axisLabel: { color: "#4b5563" } },
    yAxis: { type: "value", name: "ms", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
    series: [
      { name: "分布", type: "boxplot", data: [[20, 40, 62, 88, 130], [28, 52, 80, 118, 180], [16, 36, 58, 76, 112]], itemStyle: { color: "#dbeafe", borderColor: C.blue }, boxWidth: [18, 30] },
      { name: "异常", type: "scatter", data: [[1, 240]], symbolSize: 9, itemStyle: { color: C.red }, tooltip: { formatter: "服务 B 异常值: 240ms" }, label: { show: true, position: "right", formatter: "240ms", color: "#b91c1c", fontSize: 11 } }
    ]
  };
""",
    height=390,
)
