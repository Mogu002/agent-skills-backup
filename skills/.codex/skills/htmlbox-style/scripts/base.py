# -*- coding: utf-8 -*-
"""HTMLBox 统一骨架渲染器（遵循 lark-htmlbox 固定骨架约束）。"""

CDN = "https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js"

TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="{cdn}"></script>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; background: #ffffff; color: #1f2937; }}
  #wrap {{ width: 100%; padding: 14px 18px 16px; }}
  .hd {{ padding: 2px 2px 10px; border-bottom: 1px solid #eef1f5; margin-bottom: 6px; }}
  .hd h1 {{ margin: 0; font-size: 17px; font-weight: 650; color: #111827; letter-spacing: .2px; }}
  .hd p {{ margin: 6px 0 0; font-size: 12.5px; color: #6b7280; line-height: 1.5; }}
  #chart {{ width: 100%; height: {height}px; }}
  #st {{ min-height: 20px; font-size: 13px; color: #6b7280; text-align: center; padding: 6px 12px; }}
</style>
</head>
<body>
<div id="wrap">
  <div class="hd"><h1>{title}</h1><p>{subtitle}</p></div>
  <div id="chart"></div>
  <div id="st" role="status">加载中...</div>
</div>
<script>
(function boot() {{
  var st = document.getElementById("st") || document.getElementById("status");
  function setStatus(text) {{ if (st) st.textContent = text || ""; }}

  if (typeof echarts === "undefined") {{
    setStatus("图表库加载中...");
    return setTimeout(boot, 150);
  }}

  var chart = echarts.init(document.getElementById("chart"));
  try {{
{js}
    chart.setOption(option, true);
    setStatus("");
  }} catch (err) {{
    setStatus("图表渲染失败: " + (err && err.message ? err.message : String(err)));
    console.error(err);
  }}

  window.addEventListener("resize", function () {{ chart.resize(); }});
}})();
</script>
</body>
</html>
"""

PALETTE_JS = """
  var C = { blue: "#2563eb", green: "#10b981", amber: "#f59e0b", red: "#ef4444", purple: "#8b5cf6", teal: "#14b8a6", slate: "#64748b" };
"""


def render_echarts(name, title, subtitle, js, height=420):
    body = (PALETTE_JS + js).strip("\n")
    body = "\n".join("    " + line if line.strip() else line for line in body.split("\n"))
    html = TEMPLATE.format(title=title, subtitle=subtitle, cdn=CDN, height=height, js=body)
    return html


def render_raw(title, html_body, height=520):
    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; background: #ffffff; color: #111827; }}
  #wrap {{ width: 100%; padding: 14px 18px 16px; }}
  .hd {{ padding: 2px 2px 10px; border-bottom: 1px solid #eef1f5; margin-bottom: 12px; }}
  .hd h1 {{ margin: 0; font-size: 17px; font-weight: 650; color: #111827; }}
  .hd p {{ margin: 6px 0 0; font-size: 12.5px; color: #6b7280; line-height: 1.5; }}
  #st {{ min-height: 18px; font-size: 12px; color: #9ca3af; text-align: center; padding-top: 8px; }}
</style>
</head>
<body>
<div id="wrap">
  <div class="hd"><h1>{title}</h1><p>结构：标题说明 + 自适应主体（静态 SVG / Canvas，无外部脚本依赖）+ 状态节点 #st</p></div>
{body}
  <div id="st" role="status"></div>
</div>
</body>
</html>
""".format(title=title, body=html_body)
