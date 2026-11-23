# 32 种图的 option 骨架

每种都在 `assets/html/` 有成品，`scripts/g1.py ~ g4.py` 有完整 option。下面给"最小可用骨架 + 数据形状 + 常见坑"。

## A 趋势与对比

### a1 趋势面积 `line + areaStyle`
```js
xAxis:{type:"category",data:["2021","2022","2023","2024","2025","2026E"]},
series:[{type:"line",smooth:true,data:[18,42,96,180,300,430],
         areaStyle:{color:"rgba(37,99,235,.12)"},lineStyle:{width:3,color:"#2563eb"}}]
```
坑：预测段要区分（虚线或浅色），否则会被当成实际值。

### a2 渐变面积
`areaStyle.color = new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:"rgba(37,99,235,.35)"},{offset:1,color:"rgba(37,99,235,0)"}])`

### a3 多指标折线（双轴）
```js
yAxis:[{name:"万元"},{name:"增速%",splitLine:{show:false}}],
series:[{name:"收入",type:"line"},{name:"增速",type:"line",yAxisIndex:1}]
```
坑：两轴刻度数必须相同（例如都 5 格），否则交点位置是假的。本次实测就是"右轴 23% 被读成 22%"。

### a4 分组柱 `bar` × 2 + `barGap`
### a5 堆叠柱 `stack:"total"`，柱顶放合计标签
### a6 柱状竞赛
`yAxis:{type:"category"}` + 按值排序的 `data`；文档内固定呈现末年快照，`animation:false`。要做真动画需 `realtimeSort + animationDurationUpdate`；`setOption(notMerge=false)`。
坑：标签颜色别用白字压浅色条。

### a7 百分比堆叠
每个 stack 内各系列之和必须 = 100（Q1 45+30+25）。标签颜色按底色深浅分配：深蓝段白字、amber/teal 段深色字。

### a8 柱线组合
柱左右轴、线右轴；标题只写能从数据算出的趋势（"由 18% 升至 36%"），不要写"保持 30% 以上"。

## B 分布与统计

### b1 / b2 散点 / 涟漪气泡
```js
series:[{type:"scatter",symbolSize:d=>Math.sqrt(d[2])*3,data:[[x,y,size,name]],
         emphasis:{focus:"series"}}]
```
坑：`grid.right` 给足（60+），否则 x 轴标题"客户规模"被切。

### b3 热力图 `visualMap` + `series.type:"heatmap"`
### b4 矩阵热力
`visualMap.min/max` 必须给，`text:["100","0"]` 明确端点；深色底不要放深字。
### b5 日历热力 `calendar` + `heatmap`（`coordinateSystem:"calendar"`）
### b6 K 线 `candlestick`，data 顺序 `[open, close, low, high]`
坑：顺序写错会画出反色 K 线。
### b7 平行坐标 `parallel` + `parallelAxis`
每个维度显式 `min/max`，否则折线被削顶；`legend` 移到底部避免压线。
### b8 箱线图 `boxplot`，data 为 `[min,Q1,median,Q3,max]`

## C 构成 / 流向 / 层级

### c1 玫瑰饼 `roseType:"radius"`；总量与标题占比必须一致（40% 就要 40/100）
### c2 多环进度 多个 `pie` 叠半径 + 一个透明占位用于 tooltip
### c3 雷达 `radar.indicator` 全用同一量纲（统一 100 分制）
### c4 漏斗 `type:"funnel"`，标签 inside，颜色由深到浅，最浅一级换深字
坑：标题里"注册到试用 38%"要确认 38 是占访问还是占注册（本包踩过）。
### c5 仪表 `axisLine.lineStyle.color` 分段表达阈值，不要用 `progress` 盖住刻度
### c6 桑基
```js
series:[{type:"sankey",left:12,right:120,nodeGap:14,
  label:{position:"right",formatter:p=>p.value!=null?p.name+" "+p.value:p.name},
  data:[{name:"API 调用"},{name:"推理服务"},...],
  links:[{source:"API 调用",target:"推理服务",value:72},...]}]
```
硬规则：每个节点 `value` 由其 link 汇总得出，上游和 = 下游和；否则标题的占比无从核对。
### c7 主题河流 `type:"themeRiver"`，`xAxis.type:"time"`（用 category 会整图空白）
### c8 关系网络 `graph` + `force`，`layoutAnimation:false` 固定初始位置
### c9 树图 `tree`，`orient:"LR"`，叶子标金额
### c10 矩形树图 `treemap`，面积即 value；最浅色块底色压深保证白字可读
### c11 旭日 `sunburst`，`radius:[0,"88%"]`，标签径向
### c12 韦恩（SVG 手绘，不用 ECharts）
```
区域值先拆互斥：A_only = A − AB − AC + ABC
占比分母 = 并集（不是三集合之和）
圆半径 = k × sqrt(集合总量)
重叠区数值用引导线拉到画布外标注，配下方核对表 + 并集合计行
```
坑：本包首版七个区合计 93.96 万，占比却按 106.5 万算，列内只加到 86.3%。

## D 看板与动效

### d1 Dashboard
结构：3 张 KPI（计数动画 + 12.5 说明）+ 一张迷你折线 + 一张环形。超过 3 KPI + 2 图就该拆页。
### d2 SVG morphing
内联 `<svg>` + `path` 的 `<animate attributeName="d" values="...">`；首帧必须完整可读，不能依赖 hover。
### d3 Canvas 粒子
`requestAnimationFrame` + DPR 缩放：`canvas.width = w*dpr`，`ctx.scale(dpr,dpr)`；`prefers-reduced-motion` 时静态绘制。
### d4 地理地图
```js
fetch("https://registry.npmmirror.com/echarts/4.9.0/files/map/json/china.json")
  .then(r=>r.json())
  .then(geo=>{ echarts.registerMap("china", geo); chart.setOption(option); });
```
坑：ECharts 5 不内置地图，必须自己 `registerMap`；顺序错会空白。
