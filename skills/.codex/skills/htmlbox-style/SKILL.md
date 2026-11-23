---
name: htmlbox-style
description: 生成文档内嵌的交互式图表（单文件 HTML），覆盖趋势/对比、分布/统计、构成/流向/层级、看板与动效四大类。当用户要「把数据画成图」「做占比/交集/转化图」「一张看板看全指标」「图要和表格数字对得上」时使用；需要人继续编辑的结构图请走 whiteboard-style。
---

# 数据图表风技能（htmlbox-style）

目标：**一张图说一句能被数据验证的结论**。图只是证据，标题是论点。

适用：折线/面积/柱/堆叠/散点/气泡/热力/日历/箱线/K 线/雷达/漏斗/桑基/河流/旭日/树图/韦恩/仪表/看板/粒子/地图。
不适用：需要拖拽编辑的架构与流程（→ `whiteboard-style`）。

## 一、先定三件事

1. **一句话结论**：标题写结论，不写"XX 图"。例：`访问到付费整体转化 19%`，不是 `转化漏斗图`。
2. **一个主指标**：一张图只回答一个问题；两个量纲不同才允许双轴。
3. **数据口径**：分母是谁、去重规则、时间窗口，写在副标题里。

## 二、输出形态（固定，不要自创）

单文件 HTML，ECharts 走 CDN，容器高度固定，自带状态节点：

```html
<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>一句话结论</title>
<script src="https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js"></script>
<style>…body/#wrap/.hd/#chart/#st…</style>
</head><body>
<div id="wrap">
  <div class="hd"><h1>一句话结论</h1><p>副标题：口径与单位</p></div>
  <div id="chart"></div>
  <div id="st" role="status">加载中...</div>
</div>
<script>(function boot(){ … echarts 未就绪则 150ms 后重试；try/catch 写状态；resize 监听 … })()</script>
</body></html>
```

完整骨架见 `references/skeleton.md`，直接复制即可（`base.py` 里的 `render_echarts` 就是它的代码化）。

三条硬规则：
- `#chart` 必须有显式高度（按图类型 330–560），否则嵌入文档会塌成 0。
- 开启 `try/catch` + `#st` 状态：白屏时读者看到原因，而不是空白。
- 静态汇报图 `animation: false`；只做"看起来会动"的图（竞赛、粒子）例外。

## 三、样式令牌

```js
var C = { blue:"#2563eb", green:"#10b981", amber:"#f59e0b", red:"#ef4444",
          purple:"#8b5cf6", teal:"#14b8a6", slate:"#64748b" };
```

- 页面字族：`-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif`
- 标题 17/650 `#111827`；副标题 12.5 `#6b7280`；轴文字 11–12 `#4b5563`；网格线 `#eef1f5`。
- 卡片/容器：白底，不画边框；一张图最多 3 个色系，其余用灰阶。
- **文字对比度**：浅底（amber `#f59e0b`、teal `#14b8a6`）上的数值标签必须用深色（`#7c2d12` / `#083344`），白字只放在深色块上。这一条是本项目返工最多的点。

## 四、32 种图按四组选型

**A 趋势与对比（8）**：面积、渐变面积、多指标折线、分组柱、堆叠柱、柱状竞赛、百分比堆叠、柱线组合。
**B 分布与统计（8）**：散点、涟漪气泡、热力图、矩阵热力、日历热力、K 线、平行坐标、箱线图。
**C 构成 / 流向 / 层级（12）**：玫瑰饼、多环进度、雷达、漏斗、仪表、桑基、主题河流、关系网络、树、矩形树图、旭日、韦恩。
**D 看板与动效（4）**：KPI Dashboard、SVG morphing、Canvas 粒子、地理地图。

选型口诀：
- 问"随时间怎么变" → 折线/面积；问"谁大谁小" → 横向条；问"结构占比" → 饼/环/堆叠（≤5 类）。
- 问"从哪来到哪去" → 桑基（节点必须带数值）；问"重叠多少" → 韦恩（占比按并集算）；问"层级怎么拆" → 树/旭日/树图。
- 问"分布形状" → 箱线/散点；问"两维交叉强度" → 热力；问"一屏看全" → Dashboard（≤3 KPI + 2 图，多了就拆）。

每种图的 option 骨架与数据形状见 `references/charts.md`，可运行实现见 `scripts/g1.py ~ g4.py`。

## 五、数据必须自证（最容易翻车的地方）

- 标题里的每个数字，都要能从图里算出来：`89%` 就要有 88+90=178/200。
- 堆叠柱：每根合计 100%；漏斗：转化率分母是上一层；韦恩：七个互斥区 + 并集合计。
- 桑基：上游之和 = 下游之和，节点标签输出 `名称 + 数值`，否则读者无法核对。
- 双轴：两轴格数相同，避免"看起来交叉"的伪结论。
- 时间轴上的"今天"必须是真实日期。

## 六、校验流程（不截图不算完成）

```bash
# 1) 本地渲染色 + console
python3 html_vision.py - <<'EOF'
{"task":"检查：是否空图/报错；标签是否裁切重叠；数值与标题是否一致；对比度是否可读。给出 no issue 或具体问题。",
 "url":"file:///abs/path/x.html"}
EOF
# 2) 按结论改代码 → 只重测受影响的那几张 → 再全量过一遍
```

- 有 console 报错必须修（CDN 失败、option 非法、字段不存在）。
- 截图里"看起来空"通常不是数据错，是 `xAxis.type` / `series.type` 不匹配或容器高度为 0。
- 验收清单见 `references/verify.md`。

## 七、放进文档

```xml
<html5-block path="@assets/x.html"></html5-block>
```

或用 `--content @doc.xml` 创建文档、`html5-block` 自动上传渲染。文件路径用相对路径（相对文档 XML 所在目录）。

## 八、边界

- 3D、飞线、WebGL 依赖（`echarts-gl`）不在本包内：需要时显式引入并单独验证，不要假设可用。
- 地图需要 GeoJSON：本包示例从 `echarts@4.9.0` 的 `map/json/china.json` fetch 后 `registerMap`，离线环境请本地化该文件。
- 一屏超过 6 个图就不是 HTMLBox 该干的事，改成看板页面（走前端技能）。
