# -*- coding: utf-8 -*-
"""D 组：Dashboard / SVG 动效 / Canvas / 地理可视化"""
from base import render_raw

CHARTS = {}

DASHBOARD = """
  <style>
    .kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px; }
    .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px 16px; background: linear-gradient(180deg,#fbfdff,#f7f9fc); }
    .label { color: #6b7280; font-size: 12.5px; letter-spacing: .3px; }
    .num { font-size: 26px; font-weight: 700; margin-top: 8px; color: #0f172a; font-variant-numeric: tabular-nums; }
    .delta { margin-top: 6px; color: #059669; font-size: 12px; }
    .panels { display: grid; grid-template-columns: 1.35fr 1fr; gap: 12px; }
    .panel { border: 1px solid #eef1f5; border-radius: 10px; padding: 10px 12px 4px; }
    .pt { font-size: 13px; color: #374151; font-weight: 600; margin: 2px 0 6px; }
    .mini { width: 100%; height: 190px; }
  </style>
  <div class="kpis">
    <div class="card"><div class="label">ARR</div><div class="num" id="k1">0</div><div class="delta">同比 +42%</div></div>
    <div class="card"><div class="label">企业客户</div><div class="num" id="k2">0</div><div class="delta">同比 +18%</div></div>
    <div class="card"><div class="label">API 调用</div><div class="num" id="k3">0</div><div class="delta">同比 +27%</div></div>
  </div>
  <div class="panels">
    <div class="panel"><div class="pt">近 6 个月收入（百万元）</div><div class="mini" id="c1"></div></div>
    <div class="panel"><div class="pt">渠道结构（%）</div><div class="mini" id="c2"></div></div>
  </div>
  <script src="https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js"></script>
  <script>
  (function () {
    var data = [{ el: "k1", v: 300, unit: " 亿" }, { el: "k2", v: 1200, unit: " 家" }, { el: "k3", v: 86, unit: " B" }];
    var start = null;
    function tick(ts) {
      if (!start) start = ts;
      var p = Math.min(1, (ts - start) / 900);
      data.forEach(function (d) { document.getElementById(d.el).textContent = Math.round(d.v * p).toLocaleString() + d.unit; });
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);

    if (typeof echarts === "undefined") { return; }
    var c1 = echarts.init(document.getElementById("c1"));
    c1.setOption({
      animation: false,
      grid: { left: 44, right: 12, top: 12, bottom: 24 },
      xAxis: { type: "category", data: ["1月", "2月", "3月", "4月", "5月", "6月"], axisLabel: { color: "#6b7280", fontSize: 10 }, axisLine: { lineStyle: { color: "#e5e7eb" } } },
      yAxis: { type: "value", axisLabel: { color: "#6b7280", fontSize: 10 }, splitLine: { lineStyle: { color: "#f1f5f9" } } },
      series: [{ type: "line", smooth: true, symbolSize: 6, data: [32, 41, 48, 52, 61, 68], lineStyle: { width: 2.5, color: "#2563eb" }, itemStyle: { color: "#2563eb" }, areaStyle: { color: "rgba(37,99,235,.12)" } }]
    });
    var c2 = echarts.init(document.getElementById("c2"));
    c2.setOption({
      animation: false,
      tooltip: { trigger: "item", formatter: "{b}: {c}%" },
      series: [{ type: "pie", radius: ["46%", "72%"], center: ["50%", "52%"], label: { fontSize: 10, color: "#4b5563", formatter: "{b}\\n{c}%" }, labelLine: { length: 6, length2: 6 },
        data: [
          { value: 45, name: "自然", itemStyle: { color: "#2563eb" } },
          { value: 32, name: "投放", itemStyle: { color: "#14b8a6" } },
          { value: 23, name: "合作", itemStyle: { color: "#f59e0b" } }
        ] }]
    });
    window.addEventListener("resize", function () { c1.resize(); c2.resize(); });
  })();
  </script>
"""
CHARTS["d1_dashboard"] = render_raw("经营总览 Dashboard：ARR 300 亿、企业客户 1,200 家", DASHBOARD)

SVG_MORPH = """
  <style>
    .stage { width: 100%; padding: 4px 2px 0; }
    svg { display: block; width: min(100%, 780px); height: auto; margin: 0 auto; overflow: visible; }
    .flow-line { stroke-dasharray: 16 12; animation: dash 1.8s linear infinite; }
    .pulse { transform-box: fill-box; transform-origin: center; animation: pulse 2s ease-in-out infinite; }
    @keyframes dash { to { stroke-dashoffset: -56; } }
    @keyframes pulse { 0%,100% { transform: scale(1); opacity: .92; } 50% { transform: scale(1.06); opacity: 1; } }
    @media (prefers-reduced-motion: reduce) { .flow-line, .pulse { animation-duration: 6s; } }
  </style>
  <div class="stage">
    <svg viewBox="0 0 760 360" role="img" aria-label="业务信号从触达到转化的动态路径">
      <defs>
        <linearGradient id="flowGrad" x1="80" y1="0" x2="660" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0" stop-color="#2563eb"/><stop offset=".52" stop-color="#14b8a6"/><stop offset="1" stop-color="#f59e0b"/>
        </linearGradient>
        <linearGradient id="blobGrad" x1="390" y1="72" x2="640" y2="290" gradientUnits="userSpaceOnUse">
          <stop offset="0" stop-color="#dbeafe"/><stop offset="1" stop-color="#ccfbf1"/>
        </linearGradient>
      </defs>
      <path d="M86 214 C190 92 312 304 426 178 S604 92 652 216" fill="none" stroke="url(#flowGrad)" stroke-width="14" stroke-linecap="round" class="flow-line"/>
      <path fill="url(#blobGrad)" d="M444 104 C502 74 570 94 594 150 C620 211 574 272 502 272 C430 272 388 220 402 158 C409 130 422 115 444 104 Z">
        <animate attributeName="d" dur="5s" repeatCount="indefinite" values="
          M444 104 C502 74 570 94 594 150 C620 211 574 272 502 272 C430 272 388 220 402 158 C409 130 422 115 444 104 Z;
          M434 120 C490 78 562 80 606 140 C650 198 590 260 520 284 C448 308 388 238 390 170 C392 142 412 128 434 120 Z;
          M444 104 C502 74 570 94 594 150 C620 211 574 272 502 272 C430 272 388 220 402 158 C409 130 422 115 444 104 Z"/>
      </path>
      <g class="pulse"><circle cx="86" cy="214" r="29" fill="#eff6ff" stroke="#2563eb" stroke-width="3.5"/><text x="86" y="220" text-anchor="middle" font-size="15" font-weight="700" fill="#1d4ed8">触达</text></g>
      <g class="pulse" style="animation-delay:.25s"><circle cx="336" cy="252" r="33" fill="#f0fdfa" stroke="#14b8a6" stroke-width="3.5"/><text x="336" y="258" text-anchor="middle" font-size="15" font-weight="700" fill="#0f766e">互动</text></g>
      <g class="pulse" style="animation-delay:.5s"><circle cx="652" cy="216" r="31" fill="#fff7ed" stroke="#f59e0b" stroke-width="3.5"/><text x="652" y="222" text-anchor="middle" font-size="15" font-weight="700" fill="#b45309">转化</text></g>
      <text x="500" y="166" text-anchor="middle" font-size="20" font-weight="800" fill="#0f172a">高潜人群</text>
      <text x="500" y="194" text-anchor="middle" font-size="13" fill="#475569">路径形态随策略重心平滑变化</text>
    </svg>
  </div>
"""
CHARTS["d2_svg_morph"] = render_raw("业务信号流转：SVG path morphing 动态路径", SVG_MORPH)

CANVAS = """
  <canvas id="cv" width="820" height="360" style="width:100%;height:auto;display:block;border-radius:10px;background:#0b1220"></canvas>
  <script>
  (function () {
    var cv = document.getElementById("cv");
    var ctx = cv.getContext("2d");
    var W = cv.width, H = cv.height;
    var nodes = [];
    for (var i = 0; i < 46; i++) {
      nodes.push({ x: (i * 137.5) % W, y: (i * 89.3) % H, vx: ((i % 5) - 2) * 0.22, vy: (((i * 3) % 5) - 2) * 0.18, r: 2 + (i % 3) });
    }
    function draw() {
      ctx.clearRect(0, 0, W, H);
      for (var i = 0; i < nodes.length; i++) {
        var a = nodes[i];
        for (var j = i + 1; j < nodes.length; j++) {
          var b = nodes[j];
          var dx = a.x - b.x, dy = a.y - b.y;
          var d = Math.sqrt(dx * dx + dy * dy);
          if (d < 130) {
            ctx.strokeStyle = "rgba(96,165,250," + (0.30 * (1 - d / 130)).toFixed(3) + ")";
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          }
        }
      }
      for (var k = 0; k < nodes.length; k++) {
        var n = nodes[k];
        ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = k % 7 === 0 ? "rgba(245,158,11,.95)" : "rgba(147,197,253,.92)";
        ctx.fill();
        n.x += n.vx; n.y += n.vy;
        if (n.x < 6 || n.x > W - 6) n.vx *= -1;
        if (n.y < 6 || n.y > H - 6) n.vy *= -1;
      }
    }
    draw();
    requestAnimationFrame(function loop() { draw(); requestAnimationFrame(loop); });
  })();
  </script>
"""
CHARTS["d3_canvas_particles"] = render_raw("Canvas 粒子网络：实时自绘的依赖关系", CANVAS)

GEO = """
  <script src="https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js"></script>
  <div id="chart" style="width:100%;height:420px"></div>
  <script>
  (function () {
    var st = document.getElementById("status");
    function setStatus(msg) { if (st) { st.textContent = msg; } }

    function render() {
      var chart = echarts.init(document.getElementById("chart"));
      var cities = [
        { name: "北京", value: [116.40, 39.90, 92] },
        { name: "上海", value: [121.47, 31.23, 88] },
        { name: "深圳", value: [114.06, 22.54, 76] },
        { name: "成都", value: [104.07, 30.57, 54] },
        { name: "西安", value: [108.95, 34.27, 38] },
        { name: "武汉", value: [114.31, 30.59, 46] }
      ];
      try {
        chart.setOption({
          animation: false,
          tooltip: { trigger: "item", formatter: function (p) { return p.name + ": " + p.value[2] + " 万次"; } },
          geo: {
            map: "china", roam: false, zoom: 1.15, top: 24, bottom: 24,
            itemStyle: { areaColor: "#f1f5f9", borderColor: "#cbd5e1", borderWidth: 0.8 },
            emphasis: { itemStyle: { areaColor: "#e2e8f0" }, label: { show: false } }
          },
          series: [{
            type: "effectScatter", coordinateSystem: "geo",
            symbolSize: function (v) { return Math.max(8, v[2] / 7); },
            rippleEffect: { scale: 2.4, brushType: "stroke" },
            itemStyle: { color: "#2563eb" },
            label: { show: true, position: "right", formatter: "{b}", color: "#374151", fontSize: 11 },
            data: cities
          }]
        });
        setStatus("");
      } catch (e) { setStatus("地图渲染失败: " + e.message); console.error(e); }
      window.addEventListener("resize", function () { chart.resize(); });
    }

    function boot() {
      if (typeof echarts === "undefined") { setStatus("图表库加载中..."); return setTimeout(boot, 150); }
      if (echarts.getMap("china")) { return render(); }
      setStatus("地图数据加载中...");
      fetch("https://registry.npmmirror.com/echarts/4.9.0/files/map/json/china.json")
        .then(function (r) { if (!r.ok) { throw new Error("HTTP " + r.status); } return r.json(); })
        .then(function (geo) { echarts.registerMap("china", geo); render(); })
        .catch(function (e) { setStatus("地图数据加载失败: " + e.message); console.error(e); });
    }
    boot();
  })();
  </script>
"""
CHARTS["d4_geo_map"] = render_raw("城市调用热度：中国地图 + 涟漪散点", GEO)
