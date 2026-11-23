---
name: lark-base-reader
description: 当用户想读取、核验或定位飞书 Base 中的数据表、仪表盘及其对象 ID，或需要先判断应走 Base CLI、Base Assistant、认证恢复还是浏览器取证时，使用这个技能。它优先做对象定位和读取路径分流，并按需引导读取 `lark-base`、`lark-shared` 或 `ego-browser`；NOT for 新建或大规模修改 Base。
---

# Lark Base Reader

用于“先定位，再读取”的 Base 检查型任务。这个 skill 不替代 `lark-base`；它只负责把读取任务快速分流到正确入口，并避免一开始就展开整套 Lark CLI 命令。

## 何时使用

使用本 skill：

- 用户给出 `/base/` 链接，想知道里面有哪些表、仪表盘、工作流，或它们的真实 ID 是什么。
- 用户要读取某张表的字段、视图、样例记录，或想确认某个 dashboard 是否存在、入口在哪、标题是什么。
- 用户在做评测、核验或排障，需要先拿到 Base token、左侧栏对象清单、对象类型和可见证据。
- 用户不确定该先走 Base CLI、认证恢复，还是浏览器取证。

不要使用本 skill：

- 用户要新建 Base、创建完整 dashboard、搭 workflow、批量修改表结构：转 `lark-base`，由它继续分流到 `base:assistant` 或 Base CLI。
- 用户只是在处理登录态、scope、`auth login`、用户 / bot 身份问题：直接转 `lark-shared`。
- 用户要自然语言数据分析结论、聚合统计、归因报告：转 `lark-base`，按它的 `base:assistant` 路径处理。

## 默认立场

- 先确认目标是“Base 本体”“左侧栏对象”“单张表”，还是“仪表盘渲染结果”；不要一开始就铺开所有命令。
- 如果目标是整个业务系统、全库核验或 Building 产物评测，URL 定位后先读取完整左侧栏对象清单，再按实际对象进入各分支；单张表或单对象任务不扩读全库。
- 先用最小元数据命令定位对象，再决定是否下钻到字段、记录或 dashboard 细节。
- 用户只要对象 ID 时，拿到 `base_token`、`table_id`、`dashboard block id` 或 `workflow id` 就可以停止，不要过度读取记录。
- CLI 读不到 dashboard 内部图表或结果不完整时，不要直接判成“看板没有内容”；先切到浏览器降级链。
- 认证问题和对象读取问题分开处理：前者转 `lark-shared`，后者才继续留在本 skill / `lark-base`。

## 默认流程

1. 先读 [`references/cli-reading-paths.md`](references/cli-reading-paths.md)，按最小命令拿到 `base_token` 和对象类型。
2. 如果报 `token_missing`、`need_user_authorization`、`missing_scopes`、`verify_failed`，停止读取 Base，转读 `lark-shared`。
3. 如果目标是整个业务系统、全库核验或 Building 产物评测，运行 `+base-block-list` 获取完整对象清单，记录对象类型、名称、ID 和父级；再根据清单决定需进入的 Domain，不能只检查 URL 当前指向的对象。
4. 如果已经知道目标是表，再去读 `lark-base`，只展开 table / field / view / record 相关部分，并按读取 reference 的分页停止条件执行。
5. 如果已经知道目标是 dashboard：
   - 只要 dashboard 是否存在、名字和 ID：停在 `+base-block-list`
   - 需要 dashboard block、图表配置或 CLI 返回：转读 `lark-base` 的 dashboard 相关 reference
   - 需要真实渲染图表、统计卡、排行、页面入口证据：转读 `ego-browser`
6. 如果任务从“读取”变成“新建、修改、统计分析、问数回答”，停止扩写本 skill，直接转 `lark-base`。

## 渐进式披露规则

- 本 skill 只保留“先做什么、何时转向哪个 skill”的判断，不内嵌完整 CLI 目录。
- `references/cli-reading-paths.md` 只给读取场景的最小命令梯子；对象专属的完整命令、复杂 JSON 和写入规则都留在 `lark-base`。
- 不要在一开始同时展开 `lark-base`、`lark-shared`、`ego-browser` 三套说明；只有遇到对应分支时再去读。
- 如果当前任务已经在 `+url-resolve` 或 `+base-block-list` 处拿到充分答案，立即停止，不继续下钻。

## 高价值判断

- `+url-resolve` 只解决“这个 URL 当前落在哪个 Base / 当前对象”这一层；它不会列出左侧栏全部对象。
- 左侧栏对象清单的正入口是 `+base-block-list`，不是从 URL 猜所有 token。
- 对全库评测，`+url-resolve` 成功不代表对象发现完成；必须在 `+base-block-list` 返回完整清单后才开始逐对象核验。
- dashboard 的 URL 参数里即使写在 `table=` 上，也可能实际是 `blk...` dashboard block id；要按对象类型判断，不要只看参数名。
- `bot` 身份有时能 resolve URL，但不一定有 `base:block:read` 这类读取左侧栏对象的权限；不要默认 bot 兜底可用。
- 浏览器降级分支里，要用“URL / 当前对象变化 + 页面已渲染内容”来确认真的切进 dashboard，而不是只根据一次点击是否发生。

## 完成检查

- 已先定位 Base，再决定是否读取表、dashboard 或认证流程。
- 若任务覆盖整个业务系统或全库评测，已读取完整对象清单，而不是只检查入口 URL 当前对象。
- 只在需要时才展开 `lark-base`、`lark-shared`、`ego-browser`。
- 没把读取任务误扩成创建、修改或自然语言问数。
- 没把 CLI 盲区误判成“对象不存在”或“dashboard 为空”。
