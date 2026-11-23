# DSL 规范（需要图片或锁锚点连线时走这条）

DSL 是 JSON 描述的原生画板节点。它比 SVG 贵在两点：**真实图片节点**、**连线路由可以锁死**。只在需要这两点时用，纯结构图用 SVG 更快。

## 1. 文件骨架

```json
{ "version": 2, "nodes": [ { "type": "frame", ... } ] }
```

- `version` 必须是 `2`。
- 顶层 `nodes` 里既能放容器，也能放 `connector`；**connector 只能放顶层**，嵌进 frame.children 会失效。
- 尺寸三选一：固定数值、`"fit-content"`、不写（跟随父容器）。

## 2. frame（Flex 容器）

```json
{
  "type": "frame", "id": "root", "layout": "vertical", "gap": 20, "padding": 32,
  "width": 832, "height": "fit-content",
  "fillColor": "#FFFFFF", "borderWidth": 1, "borderColor": "#E5E6EB", "borderRadius": 16,
  "children": [ ... ]
}
```

- `layout`: `vertical` / `horizontal`；`gap` 子项间距；`padding` 支持单值或 `[top, right, bottom, left]`。
- 列宽一致靠 `width` 固定；行高随内容靠 `height: "fit-content"`。
- 卡片 = frame + 白底 + 1px 边 + `borderRadius: 12` + `padding: [0,0,12,0]`（图片贴顶时上/左右留 0）。

**坑**：给 `text` 节点写死 `height`（如 56）不会自动撑高，长文案会溢出。含文字节点的容器一律 `fit-content`，单行文本高度按 `字号 × 1.4` 给。

## 3. text

```json
{ "type": "text", "id": "title", "width": 768, "height": 32,
  "text": "一句话标题", "fontSize": 22, "textAlign": "center", "textColor": "#1F2329" }
```

字号阶梯与 SVG 路线一致：标题 22–24，卡片标题 14，说明 11–12，注脚 11（`#86909C`）。

## 4. image（必须先上传）

```json
{ "type": "image", "id": "img-1", "width": 240, "height": 160,
  "image": { "src": "<media_token>" } }
```

上传流程：

```bash
# 1) 图片必须上传到目标画板（parent-node = 画板 token），拿 file_token
lark-cli docs +media-upload --as user --parent-type whiteboard \
  --parent-node <board_token> --file photos/p1.jpg --format json
# 2) DSL 里 image.src 写这个 file_token；不要写 URL，也不要写网盘文件 token
# 3) 上传后比较文件大小 / 目检，确认三张不是同一张图
```

硬要求：3–6 张、**每张不同**、同一画板内 `width×height` 统一（推荐 240×160，3:2）、卡片 240×280、`gap: 24`。

## 5. connector

```json
{ "type": "connector", "id": "c1",
  "connector": { "from": "card-1", "to": "card-2", "fromAnchor": "right", "toAnchor": "left" } }
```

- `from` / `to` 写节点 `id`，锚点 `left|right|top|bottom`。
- 需要折线加 `"shape": "rightAngle"`（不同版本字段名可能是 `connectorStyle`，以 CLI 转换结果为准）。
- 放在顶层，且连线两端节点必须在同一画布坐标系里。

## 6. 落地命令

```bash
# 本地预览（PNG 只用于目检）
npx -y @larksuite/whiteboard-cli@^0.2.13 -i x.json -o x.png

# 转 OpenAPI 原生格式并写入空白画板
npx -y @larksuite/whiteboard-cli@^0.2.13 -i x.json --to openapi --format json \
  | lark-cli whiteboard +update --whiteboard-token <board> \
      --source - --input_format raw --idempotent-token <唯一串> --as user

# 已有内容的画板要 --overwrite，否则是追加（会把两版图叠在一起）
```

**踩过的坑**：先在文档里拿到画板 token 列表时，注意画板在文档中的**真实顺序**（SVG 段 → Mermaid 段 → DSL 段），写错序号会把图追加到别人的画板里；发现后需要用 `--overwrite` 把被污染的画板按原图源重建。

## 7. 两种典型图

| 图 | 文件 | 要点 |
|---|---|---|
| 图片卡片网格 | `assets/dsl/whiteboard_dsl_photo.json` | 3 卡横排，图片贴顶，标题 + 11px 说明，`fit-content` 撑高 |
| 三阶段数据流 | `assets/dsl/whiteboard_dsl_pipeline.json` | 三列 vertical frame + 4 根顶层 connector + rightAngle |
