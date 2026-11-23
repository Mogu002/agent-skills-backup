# 固定骨架（复制即用）

`base.py` 里的 `render_echarts(name, title, subtitle, js, height)` 就是这份模板的代码版；直接改 `js` 即可。

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>一句话结论</title>
<script src="https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js"></script>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
         background: #ffffff; color: #1f2937; }
  #wrap { width: 100%; padding: 14px 18px 16px; }
  .hd { padding: 2px 2px 10px; border-bottom: 1px solid #eef1f5; margin-bottom: 6px; }
  .hd h1 { margin: 0; font-size: 17px; font-weight: 650; color: #111827; letter-spacing: .2px; }
  .hd p { margin: 6px 0 0; font-size: 12.5px; color: #6b7280; line-height: 1.5; }
  #chart { width: 100%; height: 380px; }         /* 显式高度，必填 */
  #st { min-height: 20px; font-size: 13px; color: #6b7280; text-align: center; padding: 6px 12px; }
</style>
</head>
<body>
<div id="wrap">
  <div class="hd"><h1>一句话结论（含一个能算出来的数字）</h1><p>副标题：口径 / 单位 / 时间窗口</p></div>
  <div id="chart"></div>
  <div id="st" role="status">加载中...</div>
</div>
<script>
(function boot() {
  var st = document.getElementById("st");
  function setStatus(t) { if (st) st.textContent = t || ""; }

  if (typeof echarts === "undefined") {          // CDN 还没到
    setStatus("图表库加载中...");
    return setTimeout(boot, 150);
  }

  var chart = echarts.init(document.getElementById("chart"));
  try {
    var C = { blue:"#2563eb", green:"#10b981", amber:"#f59e0b",
              red:"#ef4444", purple:"#8b5cf6", teal:"#14b8a6", slate:"#64748b" };
    var option = { /* 见 references/charts.md */ };
    chart.setOption(option, true);
    setStatus("");
  } catch (err) {
    setStatus("图表渲染失败: " + (err && err.message ? err.message : String(err)));
    console.error(err);
  }

  window.addEventListener("resize", function () { chart.resize(); });
})();
</script>
</body>
</html>
```

## 为什么这样写

| 设计 | 原因 |
|---|---|
| 库在 `<head>` 同步加载 | 嵌入 iframe 后 `DOMContentLoaded` 不一定触发，boot 轮询最稳 |
| `typeof echarts === "undefined"` 轮询 | CDN 抖动时先显示"加载中"，不是白屏 |
| `try/catch` 写 `#st` | option 写错（字段名、类型）时读者能看到原因，也方便自测定位 |
| `setOption(option, true)` | `notMerge`，避免同一容器复用旧 option 造成"鬼影" |
| 显式 `#chart` 高度 | 否则父容器高度为 0，整块塌掉 |
| `animation: false` | 截图/嵌入场景下动画会让第一帧读数不稳 |

## 库地址与回退

首选 `https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js`。
国内网络失败时按顺序换：`fastly.jsdelivr.net` → `gcore.jsdelivr.net` → `cdn.jsdelivr.net`（同一路径）。**不要把库下载进工作区替换**，交付物必须自包含 CDN 引用。

地图另需 GeoJSON，本包用 `https://registry.npmmirror.com/echarts/4.9.0/files/map/json/china.json` + `echarts.registerMap`。
