# -*- coding: utf-8 -*-
"""C 组：构成、流向与层级（12 类型，含 SVG 韦恩图）"""
from base import render_echarts, render_raw

CHARTS = {}

CHARTS["c1_rose_pie"] = render_echarts(
    "c1_rose_pie",
    "自然流量仍是第一来源，贡献 40% 曝光",
    "玫瑰饼图：用半径强化构成差异，精确比例仍在 tooltip / 图例中给出",
    """
  var option = {
    animation: false,
    tooltip: { trigger: "item", formatter: "{b}: {c} 万 ({d}%)" },
    legend: { bottom: 4, itemWidth: 10, itemHeight: 10, textStyle: { color: "#4b5563", fontSize: 12 } },
    series: [{
      type: "pie", radius: [26, 124], center: ["50%", "48%"], roseType: "radius",
      itemStyle: { borderColor: "#ffffff", borderWidth: 2 },
      label: { formatter: "{b}\\n{d}%", color: "#374151", fontSize: 11 },
      data: [
        { value: 40, name: "自然", itemStyle: { color: C.blue } },
        { value: 32, name: "投放", itemStyle: { color: C.teal } },
        { value: 18, name: "合作", itemStyle: { color: C.amber } },
        { value: 10, name: "转介绍", itemStyle: { color: C.purple } }
      ]
    }]
  };
""",
    height=400,
)

CHARTS["c2_multi_ring"] = render_echarts(
    "c2_multi_ring",
    "收入达成 82%，用户与留存仍有缺口",
    "多环进度仪表：三个同口径（%）目标达成率，不同量纲不共环",
    """
  var rings = [
    { name: "收入", value: 82, radius: ["74%", "86%"], color: C.blue },
    { name: "用户", value: 68, radius: ["58%", "70%"], color: C.teal },
    { name: "留存", value: 54, radius: ["42%", "54%"], color: C.amber }
  ];
  var option = {
    animation: false,
    title: { text: "目标达成率", left: "center", top: 2, textStyle: { fontSize: 14, fontWeight: 600, color: "#374151" } },
    tooltip: { trigger: "item", formatter: "{b}: {c}%" },
    legend: { bottom: 4, itemWidth: 10, itemHeight: 10, textStyle: { color: "#4b5563", fontSize: 12 } },
    series: rings.map(function (item) {
      return {
        name: item.name, type: "pie", radius: item.radius, center: ["50%", "50%"], silent: true,
        label: { show: false }, labelLine: { show: false },
        data: [
          { value: item.value, name: item.name, itemStyle: { color: item.color } },
          { value: 100 - item.value, name: "剩余", itemStyle: { color: "#e5e7eb" } }
        ]
      };
    }).concat([{
      type: "pie", radius: ["0%", "0%"], center: ["50%", "50%"], silent: true, label: { show: false },
      data: [{ value: 1, name: "收入 82% · 用户 68% · 留存 54%", itemStyle: { color: "transparent" } }]
    }])
  };
""",
    height=400,
)

CHARTS["c3_radar"] = render_echarts(
    "c3_radar",
    "当前团队在质量与增长上领先，效率是主要短板",
    "能力雷达图：5 个统一 100 分制维度，面积透明度用于表达覆盖范围",
    """
  var option = {
    animation: false,
    tooltip: {},
    legend: { bottom: 2, itemWidth: 10, itemHeight: 10, textStyle: { color: "#4b5563", fontSize: 12 } },
    radar: {
      radius: "62%", center: ["50%", "48%"],
      indicator: [
        { name: "策略", max: 100 }, { name: "执行", max: 100 }, { name: "增长", max: 100 },
        { name: "效率", max: 100 }, { name: "质量", max: 100 }
      ],
      axisName: { color: "#374151", fontSize: 12 },
      splitLine: { lineStyle: { color: "#e5e7eb" } },
      splitArea: { areaStyle: { color: ["#ffffff", "#f9fafb"] } },
      axisLine: { lineStyle: { color: "#e5e7eb" } }
    },
    series: [{
      type: "radar",
      data: [
        { name: "当前团队", value: [82, 76, 88, 69, 91], itemStyle: { color: C.blue }, areaStyle: { opacity: .20, color: C.blue }, lineStyle: { width: 2 } },
        { name: "目标水位", value: [85, 80, 85, 80, 88], itemStyle: { color: C.amber }, areaStyle: { opacity: .10, color: C.amber }, lineStyle: { width: 2, type: "dashed" } }
      ]
    }]
  };
""",
    height=400,
)

CHARTS["c4_funnel"] = render_echarts(
    "c4_funnel",
    "访问到付费整体转化 19%，后两级各流失约一半",
    "漏斗图：访问 → 付费 4 级转化，标签给出阶段值（以访问为 100%）",
    """
  var option = {
    animation: false,
    tooltip: { trigger: "item", formatter: "{b}: {c}%（以访问为 100）" },
    series: [{
      type: "funnel", top: 26, bottom: 18, left: "18%", right: "18%", minSize: "34%",
      label: { show: true, position: "inside", formatter: "{b}  {c}%", color: "#ffffff", fontSize: 13, fontWeight: 600 },
      labelLine: { show: false },
      itemStyle: { borderColor: "#ffffff", borderWidth: 2 },
      data: [
        { value: 100, name: "访问", itemStyle: { color: "#1e3a8a" } },
        { value: 72, name: "注册", itemStyle: { color: "#1d4ed8" } },
        { value: 38, name: "试用", itemStyle: { color: "#2563eb" } },
        { value: 19, name: "付费", itemStyle: { color: "#1e40af" } }
      ]
    }]
  };
""",
    height=390,
)

CHARTS["c5_gauge"] = render_echarts(
    "c5_gauge",
    "SLA 达成率 92%，处于健康区间",
    "仪表盘指针：0-100 刻度按业务阈值分档（<60 红 / 60-85 黄 / >85 绿）",
    """
  var option = {
    animation: false,
    series: [{
      type: "gauge", min: 0, max: 100, center: ["50%", "58%"], radius: "84%",
      axisLine: { lineStyle: { width: 18, color: [[0.6, "#ef4444"], [0.85, "#f59e0b"], [1, "#10b981"]] } },
      pointer: { width: 5, length: "72%", itemStyle: { color: "#374151" } },
      axisTick: { distance: -20, length: 6, lineStyle: { color: "#ffffff" } },
      splitLine: { distance: -20, length: 14, lineStyle: { color: "#ffffff", width: 2 } },
      axisLabel: { distance: 22, color: "#6b7280", fontSize: 11 },
      detail: { formatter: "{value}%", fontSize: 30, fontWeight: 700, color: "#0f172a", offsetCenter: [0, "62%"] },
      title: { offsetCenter: [0, "88%"], color: "#6b7280", fontSize: 13 },
      data: [{ value: 92, name: "SLA 达成率" }]
    }]
  };
""",
    height=360,
)

CHARTS["c6_sankey"] = render_echarts(
    "c6_sankey",
    "API 与企业合同贡献 89% 收入，云市场为增量入口",
    "桑基图：来源 → 交付形态 → 收入的流量结构，连线粗细即金额",
    """
  var option = {
    animation: false,
    tooltip: { trigger: "item", formatter: function (p) { return p.dataType === "edge" ? p.data.source + " → " + p.data.target + ": " + p.data.value + " 百万元" : p.name; } },
    series: [{
      type: "sankey", top: 24, bottom: 24, left: 12, right: 120, nodeGap: 14, nodeWidth: 14,
      emphasis: { focus: "adjacency" },
      lineStyle: { color: "gradient", opacity: .42, curveness: .5 },
      label: { color: "#1f2937", fontSize: 12, position: "right", formatter: function (p) { return p.value != null ? p.name + " " + p.value : p.name; } },
      data: [
        { name: "API 调用", itemStyle: { color: C.blue } },
        { name: "企业合同", itemStyle: { color: C.teal } },
        { name: "云市场", itemStyle: { color: C.amber } },
        { name: "推理服务", itemStyle: { color: "#93c5fd" } },
        { name: "训练服务", itemStyle: { color: "#5eead4" } },
        { name: "总收入", itemStyle: { color: "#1f2937" } }
      ],
      links: [
        { source: "API 调用", target: "推理服务", value: 72 },
        { source: "API 调用", target: "训练服务", value: 16 },
        { source: "企业合同", target: "推理服务", value: 36 },
        { source: "企业合同", target: "训练服务", value: 54 },
        { source: "云市场", target: "推理服务", value: 22 },
        { source: "推理服务", target: "总收入", value: 130 },
        { source: "训练服务", target: "总收入", value: 70 }
      ]
    }]
  };
""",
    height=390,
)

CHARTS["c7_theme_river"] = render_echarts(
    "c7_theme_river",
    "AI 主题热度持续扩张，办公主题趋于平稳",
    "主题河流图：三类主题 2026 年 1-6 月热度演化，时间粒度统一为月",
    """
  var months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"];
  var ai = [12, 18, 26, 31, 38, 46];
  var search = [10, 14, 20, 22, 24, 25];
  var office = [8, 13, 16, 17, 17, 18];
  var data = [];
  months.forEach(function (m, i) {
    data.push([m + "-01", ai[i], "AI"]);
    data.push([m + "-01", search[i], "搜索"]);
    data.push([m + "-01", office[i], "办公"]);
  });
  var option = {
    animation: false,
    tooltip: { trigger: "axis", axisPointer: { type: "line" } },
    legend: { top: 4, itemWidth: 10, itemHeight: 10, textStyle: { color: "#4b5563", fontSize: 12 } },
    singleAxis: { top: 56, bottom: 46, type: "time", axisLabel: { color: "#4b5563", formatter: "{MM}月" }, axisLine: { lineStyle: { color: "#e5e7eb" } }, splitLine: { show: false } },
    series: [{
      type: "themeRiver", data: data,
      label: { show: false },
      itemStyle: { opacity: .85 },
      color: [C.blue, C.teal, C.amber],
      emphasis: { itemStyle: { shadowBlur: 8, shadowColor: "rgba(0,0,0,.18)" } }
    }]
  };
""",
    height=390,
)

CHARTS["c8_graph_network"] = render_echarts(
    "c8_graph_network",
    "核心产品连接四类生态角色，云伙伴为二级节点",
    "关系网络图：force 布局，初始即清晰；节点大小表达影响力",
    """
  var option = {
    animation: false,
    tooltip: {},
    legend: { bottom: 2, itemWidth: 10, itemHeight: 10, textStyle: { color: "#4b5563", fontSize: 12 } },
    series: [{
      type: "graph", layout: "force", roam: false, draggable: true,
      force: { repulsion: 380, edgeLength: [80, 150], gravity: 0.06 },
      label: { show: true, color: "#374151", fontSize: 11, position: "bottom" },
      categories: [{ name: "核心" }, { name: "客户" }, { name: "伙伴" }],
      lineStyle: { color: "#cbd5e1", width: 1.5, curveness: .08 },
      data: [
        { name: "核心产品", symbolSize: 62, category: 0, itemStyle: { color: C.blue } },
        { name: "企业客户", symbolSize: 44, category: 1, itemStyle: { color: C.teal } },
        { name: "开发者", symbolSize: 40, category: 1, itemStyle: { color: C.teal } },
        { name: "云伙伴", symbolSize: 42, category: 2, itemStyle: { color: C.amber } },
        { name: "渠道商", symbolSize: 32, category: 2, itemStyle: { color: C.amber } }
      ],
      links: [
        { source: "核心产品", target: "企业客户" },
        { source: "核心产品", target: "开发者" },
        { source: "核心产品", target: "云伙伴" },
        { source: "云伙伴", target: "渠道商" }
      ]
    }]
  };
""",
    height=400,
)

CHARTS["c9_tree"] = render_echarts(
    "c9_tree",
    "收入按产品线三级拆分，API 推理为最大叶子",
    "树图 tree：从左到右的层级结构，适用于组织与产品拆分",
    """
  var data = {
    name: "总收入", value: 200,
    children: [
      { name: "API", value: 88, children: [{ name: "推理", value: 62 }, { name: "训练", value: 26 }] },
      { name: "企业合同", value: 90, children: [{ name: "推理", value: 48 }, { name: "训练", value: 42 }] },
      { name: "云市场", value: 22 }
    ]
  };
  var option = {
    animation: false,
    tooltip: { trigger: "item", formatter: "{b}: {c} 百万元" },
    series: [{
      type: "tree", data: [data], top: 14, bottom: 14, left: 70, right: 130,
      symbolSize: 8, orient: "LR", expandAndCollapse: false, initialTreeDepth: 3,
      label: { position: "right", color: "#374151", fontSize: 12, verticalAlign: "middle" },
      leaves: { label: { position: "right", color: "#4b5563" } },
      lineStyle: { color: "#cbd5e1", width: 1.4, curveness: .4 },
      itemStyle: { color: C.blue, borderColor: C.blue },
      emphasis: { focus: "descendant" }
    }]
  };
""",
    height=380,
)

CHARTS["c10_treemap"] = render_echarts(
    "c10_treemap",
    "矩形树图：企业合同占比 45%，是最大收入块",
    "矩形树图 Treemap：面积即收入占比，标签直接标注金额",
    """
  var option = {
    animation: false,
    tooltip: { formatter: "{b}: {c} 百万元" },
    series: [{
      type: "treemap", roam: false, nodeClick: false, breadcrumb: { show: false },
      left: 4, right: 4, top: 8, bottom: 8, top: "8%", bottom: "6%",
      label: { show: true, color: "#ffffff", fontSize: 13, fontWeight: 600, formatter: "{b}\\n{c}" },
      upperLabel: { show: false },
      itemStyle: { borderColor: "#ffffff", borderWidth: 2, gapWidth: 2 },
      levels: [{ itemStyle: { borderWidth: 0, gapWidth: 3 } }],
      data: [
        { name: "企业合同", value: 90, itemStyle: { color: "#1d4ed8" } },
        { name: "API", value: 88, itemStyle: { color: "#3b82f6" } },
        { name: "云市场", value: 22, itemStyle: { color: "#0284c7" } }
      ]
    }]
  };
""",
    height=380,
)

CHARTS["c11_sunburst"] = render_echarts(
    "c11_sunburst",
    "旭日图：内环看产品线，外环看训练 / 推理结构",
    "旭日层级图 sunburst：同时表达层级路径与占比，标签沿径向旋转",
    """
  var data = [{
    name: "总收入", value: 200,
    itemStyle: { color: "#e5e7eb" },
    children: [
      { name: "API", value: 88, itemStyle: { color: "#bfdbfe" }, children: [
        { name: "推理", value: 62, itemStyle: { color: "#60a5fa" } },
        { name: "训练", value: 26, itemStyle: { color: "#93c5fd" } }
      ] },
      { name: "企业合同", value: 90, itemStyle: { color: "#99f6e4" }, children: [
        { name: "推理", value: 48, itemStyle: { color: "#2dd4bf" } },
        { name: "训练", value: 42, itemStyle: { color: "#5eead4" } }
      ] },
      { name: "云市场", value: 22, itemStyle: { color: "#fcd34d" } }
    ]
  }];
  var option = {
    animation: false,
    tooltip: { trigger: "item", formatter: "{b}: {c} 百万元" },
    series: [{
      type: "sunburst", radius: [0, "88%"], center: ["50%", "52%"], data: data,
      label: { rotate: "radial", color: "#1f2937", fontSize: 11, minAngle: 6 },
      itemStyle: { borderColor: "#ffffff", borderWidth: 1.5 },
      levels: [{}, { r0: "15%", r: "48%", label: { rotate: 0 } }, { r0: "48%", r: "78%" }]
    }]
  };
""",
    height=400,
)

VENN_BODY = """
  <div style="width:100%;overflow:visible">
  <svg viewBox="0 0 900 660" width="100%" height="660" role="img" aria-label="三类曝光人群交集韦恩图" style="display:block">
    <rect x="0" y="0" width="900" height="660" fill="#ffffff"/>
    <circle cx="350" cy="250" r="148" fill="#2563eb" fill-opacity="0.24" stroke="#1d4ed8" stroke-width="2"/>
    <circle cx="560" cy="250" r="215" fill="#10b981" fill-opacity="0.20" stroke="#047857" stroke-width="2"/>
    <circle cx="455" cy="410" r="165" fill="#f59e0b" fill-opacity="0.20" stroke="#b45309" stroke-width="2"/>

    <text x="200" y="172" text-anchor="middle" font-size="15" font-weight="700" fill="#1e3a8a">达人曝光</text>
    <text x="200" y="193" text-anchor="middle" font-size="12" fill="#374151">集合 235,500</text>
    <text x="762" y="132" text-anchor="middle" font-size="15" font-weight="700" fill="#065f46">官号曝光</text>
    <text x="762" y="153" text-anchor="middle" font-size="12" fill="#374151">集合 497,700</text>
    <text x="455" y="608" text-anchor="middle" font-size="15" font-weight="700" fill="#92400e">职人曝光</text>
    <text x="455" y="629" text-anchor="middle" font-size="12" fill="#374151">集合 294,300</text>

    <text x="285" y="212" text-anchor="middle" font-size="13" font-weight="700" fill="#111827" style="paint-order:stroke;stroke:#ffffff;stroke-width:4">独占 187,600</text>
    <text x="285" y="231" text-anchor="middle" font-size="12" fill="#1f2937" style="paint-order:stroke;stroke:#ffffff;stroke-width:4">20.0%</text>

    <text x="662" y="212" text-anchor="middle" font-size="13" font-weight="700" fill="#111827" style="paint-order:stroke;stroke:#ffffff;stroke-width:4">独占 434,100</text>
    <text x="662" y="231" text-anchor="middle" font-size="12" fill="#1f2937" style="paint-order:stroke;stroke:#ffffff;stroke-width:4">46.2%</text>

    <text x="470" y="494" text-anchor="middle" font-size="13" font-weight="700" fill="#111827" style="paint-order:stroke;stroke:#ffffff;stroke-width:4">独占 236,400</text>
    <text x="470" y="513" text-anchor="middle" font-size="12" fill="#1f2937" style="paint-order:stroke;stroke:#ffffff;stroke-width:4">25.2%</text>

    <line x1="424" y1="96" x2="470" y2="60" stroke="#9ca3af" stroke-width="1"/>
    <text x="516" y="56" text-anchor="middle" font-size="12" fill="#1f2937">达人∩官号 23,600 · 2.5%</text>

    <line x1="316" y1="334" x2="238" y2="316" stroke="#9ca3af" stroke-width="1"/>
    <text x="150" y="312" text-anchor="middle" font-size="12" fill="#1f2937">达人∩职人 17,900 · 1.9%</text>

    <line x1="580" y1="356" x2="680" y2="332" stroke="#9ca3af" stroke-width="1"/>
    <text x="760" y="328" text-anchor="middle" font-size="12" fill="#1f2937">官号∩职人 33,600 · 3.6%</text>

    <text x="445" y="296" text-anchor="middle" font-size="12" font-weight="700" fill="#111827" style="paint-order:stroke;stroke:#ffffff;stroke-width:4">三者 6,400</text>
    <text x="445" y="315" text-anchor="middle" font-size="12" font-weight="700" fill="#111827" style="paint-order:stroke;stroke:#ffffff;stroke-width:4">0.7%</text>

    <text x="24" y="646" font-size="11" fill="#9ca3af">圆半径按集合总量开方定距，重叠区为近似几何；并集 939,600，数值与占比以标签和下表为准</text>
  </svg>
  </div>
  <table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:6px">
    <thead><tr>
      <th style="text-align:left;padding:6px 8px;border-bottom:1px solid #e5e7eb;color:#6b7280">互斥区域</th>
      <th style="text-align:right;padding:6px 8px;border-bottom:1px solid #e5e7eb;color:#6b7280">曝光量</th>
      <th style="text-align:right;padding:6px 8px;border-bottom:1px solid #e5e7eb;color:#6b7280">占并集</th>
    </tr></thead>
    <tbody>
      <tr><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6">达人独占</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #f3f4f6">187,600</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #f3f4f6">20.0%</td></tr>
      <tr><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6">官号独占</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #f3f4f6">434,100</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #f3f4f6">46.2%</td></tr>
      <tr><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6">职人独占</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #f3f4f6">236,400</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #f3f4f6">25.2%</td></tr>
      <tr><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6">达人 ∩ 官号</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #f3f4f6">23,600</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #f3f4f6">2.5%</td></tr>
      <tr><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6">达人 ∩ 职人</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #f3f4f6">17,900</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #f3f4f6">1.9%</td></tr>
      <tr><td style="padding:5px 8px;border-bottom:1px solid #f3f4f6">官号 ∩ 职人</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #f3f4f6">33,600</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #f3f4f6">3.6%</td></tr>
      <tr><td style="padding:5px 8px;border-bottom:1px solid #e5e7eb">三者交集</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #e5e7eb">6,400</td><td style="text-align:right;padding:5px 8px;border-bottom:1px solid #e5e7eb">0.7%</td></tr>
      <tr><td style="padding:6px 8px;font-weight:600">并集合计</td><td style="text-align:right;padding:6px 8px;font-weight:600">939,600</td><td style="text-align:right;padding:6px 8px;font-weight:600">100%（四舍五入）</td></tr>
    </tbody>
  </table>
"""

CHARTS["c12_venn"] = render_raw("三类曝光人群重叠稀疏，官号独占接近一半", VENN_BODY)
