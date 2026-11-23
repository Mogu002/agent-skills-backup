# -*- coding: utf-8 -*-
"""A 组：趋势与对比（8 类型）"""
from base import render_echarts

CHARTS = {}

CHARTS["a1_trend_area"] = render_echarts(
    "a1_trend_area",
    "ARR 连续三年保持翻倍以上增长",
    "趋势折线 / 面积折线：2021-2026E 年经常性收入（亿元），2025 起为预测值",
    """
  var DATA = [
    { name: "2021", value: 1.2 }, { name: "2022", value: 3.8 }, { name: "2023", value: 8.5 },
    { name: "2024", value: 16.4 }, { name: "2025E", value: 28.9 }, { name: "2026E", value: 42.5 }
  ];
  var option = {
    animation: false,
    tooltip: { trigger: "axis", valueFormatter: function (v) { return v + " 亿元"; } },
    grid: { left: 58, right: 34, top: 46, bottom: 40 },
    xAxis: { type: "category", boundaryGap: false, data: DATA.map(function (d) { return d.name; }), axisLabel: { color: "#4b5563" } },
    yAxis: { type: "value", name: "亿元", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
    series: [{
      name: "ARR", type: "line", smooth: true, symbol: "circle", symbolSize: 8,
      data: DATA.map(function (d) { return d.value; }),
      lineStyle: { width: 3, color: C.blue }, itemStyle: { color: C.blue },
      areaStyle: { color: "rgba(37,99,235,.10)" },
      label: { show: true, position: "top", color: "#1d4ed8", fontSize: 12, formatter: "{c}" },
      markPoint: { symbolSize: 44, label: { fontSize: 11 }, data: [{ type: "max", name: "峰值" }] }
    }]
  };
""",
    height=400,
)

CHARTS["a2_gradient_area"] = render_echarts(
    "a2_gradient_area",
    "MAU 半年增长 113%，5 月后进入加速区间",
    "渐变面积折线图：周活跃用户（万人），渐变仅服务趋势层级，不遮挡网格与标签",
    """
  var DATA = [120, 132, 151, 184, 210, 256];
  var option = {
    animation: false,
    tooltip: { trigger: "axis", valueFormatter: function (v) { return v + " 万人"; } },
    grid: { left: 58, right: 34, top: 46, bottom: 40 },
    xAxis: { type: "category", boundaryGap: false, data: ["1月", "2月", "3月", "4月", "5月", "6月"], axisLabel: { color: "#4b5563" } },
    yAxis: { type: "value", name: "万人", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
    series: [{
      name: "MAU", type: "line", smooth: true, symbol: "circle", symbolSize: 8, data: DATA,
      lineStyle: { width: 3, color: C.blue }, itemStyle: { color: C.blue },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: "rgba(37,99,235,.38)" }, { offset: 1, color: "rgba(37,99,235,.03)" }
      ]) },
      label: { show: true, position: "top", color: "#1d4ed8", fontSize: 12 }
    }]
  };
""",
    height=400,
)

CHARTS["a3_multi_line"] = render_echarts(
    "a3_multi_line",
    "收入与用户同步上行，转化率 Q4 提升到 23%",
    "多指标平滑折线：规模类走左轴（万元 / 千人），转化率走右轴（%），图例与轴名标注单位",
    """
  var option = {
    animation: false,
    tooltip: { trigger: "axis" },
    legend: { top: 4, itemWidth: 12, itemHeight: 8, textStyle: { color: "#4b5563", fontSize: 12 } },
    grid: { left: 58, right: 62, top: 64, bottom: 40 },
    xAxis: { type: "category", data: ["Q1", "Q2", "Q3", "Q4"], axisLabel: { color: "#4b5563" } },
    yAxis: [
      { type: "value", name: "规模", min: 0, max: 300, interval: 60, nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
      { type: "value", name: "转化率%", min: 0, max: 25, interval: 5, nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563", formatter: "{value}%" }, splitLine: { show: false } }
    ],
    series: [
      { name: "收入(万元)", type: "line", smooth: true, data: [120, 168, 214, 280], lineStyle: { width: 3, color: C.blue }, itemStyle: { color: C.blue } },
      { name: "用户(千人)", type: "line", smooth: true, data: [80, 116, 152, 198], lineStyle: { width: 3, color: C.green }, itemStyle: { color: C.green } },
      { name: "转化率", type: "line", smooth: true, yAxisIndex: 1, data: [12, 16, 18, 23], lineStyle: { width: 3, color: C.amber }, itemStyle: { color: C.amber } }
    ]
  };
""",
    height=410,
)

CHARTS["a4_grouped_bar"] = render_echarts(
    "a4_grouped_bar",
    "企业合同渠道 2026 年反超 API 成为第一收入来源",
    "分组柱状图：2025 vs 2026 各渠道收入（百万元），同口径可直接比较",
    """
  var cats = ["API", "企业合同", "订阅", "合作伙伴"];
  var option = {
    animation: false,
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { top: 4, itemWidth: 12, itemHeight: 8, textStyle: { color: "#4b5563", fontSize: 12 } },
    grid: { left: 58, right: 26, top: 58, bottom: 44 },
    xAxis: { type: "category", data: cats, axisLabel: { color: "#4b5563" } },
    yAxis: { type: "value", name: "百万元", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
    series: [
      { name: "2025", type: "bar", barGap: "18%", data: [96, 78, 42, 24], itemStyle: { color: "#c7d2fe", borderRadius: [3, 3, 0, 0] }, label: { show: true, position: "top", color: "#4b5563", fontSize: 11 } },
      { name: "2026", type: "bar", data: [118, 132, 56, 33], itemStyle: { color: C.blue, borderRadius: [3, 3, 0, 0] }, label: { show: true, position: "top", color: "#1d4ed8", fontSize: 11 } }
    ]
  };
""",
    height=410,
)

CHARTS["a5_stacked_bar"] = render_echarts(
    "a5_stacked_bar",
    "季度收入结构稳定，企业合同占比逐季走高",
    "堆叠柱状图：各季度收入构成（百万元），各系列可相加，堆叠才成立",
    """
  var option = {
    animation: false,
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { top: 4, itemWidth: 12, itemHeight: 8, textStyle: { color: "#4b5563", fontSize: 12 } },
    grid: { left: 58, right: 26, top: 58, bottom: 44 },
    xAxis: { type: "category", data: ["Q1", "Q2", "Q3", "Q4"], axisLabel: { color: "#4b5563" } },
    yAxis: { type: "value", name: "百万元", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
    series: [
      { name: "API", type: "bar", stack: "total", data: [24, 27, 31, 36], itemStyle: { color: C.blue } },
      { name: "企业合同", type: "bar", stack: "total", data: [18, 24, 32, 42], itemStyle: { color: C.teal } },
      { name: "订阅", type: "bar", stack: "total", data: [10, 11, 13, 15], itemStyle: { color: C.amber, borderRadius: [3, 3, 0, 0] } }
    ]
  };
""",
    height=410,
)

CHARTS["a6_bar_race"] = render_echarts(
    "a6_bar_race",
    "渠道曝光排名：2026 年 B 渠道完成反超",
    "柱状竞赛 Bar Race：文档内固定呈现末年 2026 的排名（静态截图稳定，逐帧动画不在文档内播放）",
    """
  var frames = [
    { year: "2024", data: [["A 渠道", 120], ["B 渠道", 98], ["C 渠道", 76], ["D 渠道", 54]] },
    { year: "2025", data: [["A 渠道", 142], ["B 渠道", 131], ["C 渠道", 88], ["D 渠道", 61]] },
    { year: "2026", data: [["B 渠道", 176], ["A 渠道", 158], ["C 渠道", 120], ["D 渠道", 73]] }
  ];
  var frame = frames[2];
  var rows = frame.data.slice().sort(function (a, b) { return a[1] - b[1]; });
  var option = {
    animation: false,
    title: { text: "渠道曝光排名 " + frame.year, left: "center", top: 2, textStyle: { fontSize: 14, fontWeight: 600, color: "#374151" } },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: function (v) { return v + " 万次"; } },
    grid: { left: 92, right: 62, top: 46, bottom: 28 },
    xAxis: { type: "value", max: 200, axisLabel: { color: "#4b5563" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
    yAxis: { type: "category", data: rows.map(function (d) { return d[0]; }), axisLabel: { color: "#374151", fontWeight: 500 }, axisTick: { show: false }, axisLine: { show: false } },
    series: [{
      type: "bar", barWidth: 20, data: rows.map(function (d) { return d[1]; }),
      itemStyle: { color: C.blue, borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: "right", color: "#374151", fontWeight: 600, formatter: "{c} 万" }
    }]
  };
""",
    height=330,
)

CHARTS["a7_percent_stacked"] = render_echarts(
    "a7_percent_stacked",
    "自然流量占比下降 11pct，投放与合作补位",
    "百分比堆叠柱状：每季度合计 100%，tooltip 同步展示百分比口径",
    """
  var option = {
    animation: false,
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: function (v) { return v + "%"; } },
    legend: { top: 4, itemWidth: 12, itemHeight: 8, textStyle: { color: "#4b5563", fontSize: 12 } },
    grid: { left: 58, right: 26, top: 58, bottom: 44 },
    xAxis: { type: "category", data: ["Q1", "Q2", "Q3", "Q4"], axisLabel: { color: "#4b5563" } },
    yAxis: { type: "value", max: 100, name: "%", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563", formatter: "{value}%" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
    series: [
      { name: "自然流量", type: "bar", stack: "total", barWidth: 40, data: [45, 42, 38, 34], itemStyle: { color: C.blue }, label: { show: true, formatter: "{c}%", color: "#ffffff", fontSize: 11 } },
      { name: "投放", type: "bar", stack: "total", data: [30, 32, 35, 38], itemStyle: { color: C.teal }, label: { show: true, formatter: "{c}%", color: "#083344", fontSize: 11, fontWeight: 600 } },
      { name: "合作", type: "bar", stack: "total", data: [25, 26, 27, 28], itemStyle: { color: C.amber, borderRadius: [3, 3, 0, 0] }, label: { show: true, formatter: "{c}%", color: "#7c2d12", fontSize: 11, fontWeight: 600 } }
    ]
  };
""",
    height=400,
)

CHARTS["a8_combo"] = render_echarts(
    "a8_combo",
    "收入规模扩张，同比增速由 18% 升至 36%",
    "组合图：柱为收入（万元，左轴），线为同比增速（%，右轴）；仅因单位不同才使用双轴",
    """
  var option = {
    animation: false,
    tooltip: { trigger: "axis" },
    legend: { top: 4, itemWidth: 12, itemHeight: 8, textStyle: { color: "#4b5563", fontSize: 12 } },
    grid: { left: 58, right: 62, top: 60, bottom: 44 },
    xAxis: { type: "category", data: ["Q1", "Q2", "Q3", "Q4"], axisLabel: { color: "#4b5563" } },
    yAxis: [
      { type: "value", name: "万元", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563" }, splitLine: { lineStyle: { color: "#eef1f5" } } },
      { type: "value", name: "增速%", nameTextStyle: { color: "#6b7280" }, axisLabel: { color: "#4b5563", formatter: "{value}%" }, splitLine: { show: false } }
    ],
    series: [
      { name: "收入", type: "bar", barWidth: 36, data: [120, 160, 210, 280], itemStyle: { color: "#dbeafe", borderRadius: [3, 3, 0, 0] } },
      { name: "增速", type: "line", yAxisIndex: 1, smooth: true, symbolSize: 8, data: [18, 23, 31, 36], lineStyle: { width: 3, color: C.amber }, itemStyle: { color: C.amber }, label: { show: true, position: "top", color: "#b45309", fontSize: 11, formatter: "{c}%" } }
    ]
  };
""",
    height=410,
)
