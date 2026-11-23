# 常见问题（troubleshooting）

主文件的「关键 gotchas」是"失败即事故"级；本文件收纳次一级、需要看到才处理的问题。

## 评测人员字段类

- **select 型评测人员，选项里混脏值**（`decision 错题`/`存疑`/`image.png`/`permission agent`/`调用了教程问答` …）：这是符合预期的建表现象，脚本会用 `contact +search-user` 对每个选项做精确 `name` 匹配，非真人的选项自动过滤，并在运行末尾单列「跳过的非人名/无效评测人员」明细。若某个真实人员被误判为脏值（如飞书没搜到、同名多人未命中精确匹配），需要人工介入：
  - 先手动跑 `lark-cli contact +search-user --query <name> --page-size 10 --as user` 看返回；
  - 如返回里有该人但 `name` 不精确，需在源表把选项改为规范中文名，或在脚本 `resolve_open_id` 里放宽匹配（谨慎）。
- **user 字段与 select 字段混用**：如果源表既有 user 型 `评测人员` 也有 select 型 `评测人`（或反过来），先用 `+field-get` 看每个字段的 `type` 再选定 `--reviewer-field`；不要靠字段名直觉判断。
- **同名多人**：`contact +search-user` 精确匹配 `name`；多个同名用户会随机取第一个。如果确认存在真实同名冲突，改成走 open_id 白名单或让评测人员改用工号/邮箱前缀区分。

## 结果聚合类

- **多人共审被重复计数**：脚本默认按多选展开（每人各计一次）。要换口径（仅取首个评测人员），改 `normalize_reviewer` 里 select/user 两条分支的截取逻辑。
- **结果选项名变化**：源表新增/改名选项（例如新增「通过-补录」），同步改脚本顶部的 `ERROR_OPTIONS` 和 `TARGET_COLUMN_MAP`。**不要**在对话里把新选项就地当"通过"处理。
- **`--include-null` 何时用**：仅当希望统计"未指派评测人员"这一桶时才加；默认跳过更贴近日常评测口径。

## 写入类

- **`子项目` / `父项目` 报 `not_found` (code 800030005)**：目标表严格枚举，不会静默新建。脚本默认 `--auto-add-option` 会先 `field-get` 读现有选项、缺失时用 `field-update` 全量 PUT 追加。若走 `--no-auto-add-option` 或权限不足追加失败，手动执行：
  ```bash
  lark-cli base +field-update --base-token <dst_base> --table-id <dst_table> \
    --field-id 子项目 --yes --as user \
    --json '{"name":"子项目","type":"select","multiple":false,"options":[{"name":"<原选项1>"},{"name":"<新选项>"}]}'
  ```
  注意：`field-update` 是全量 PUT，必须携带全部现有 options，否则会覆盖丢失。
- **`父项目` 选项判断失误**：`父项目` 由 agent 根据 Base 名意图识别后传入 `--parent-project`。如果写入了错误的父项目：
  1. 先确认 Base 名是否与预期一致（`lark-cli base +base-get --base-token <token> --as user --jq '.data.base.name'`）
  2. 再核对目标表 `父项目` select 选项列表，确认意图映射是否正确
  3. 不要试图让脚本自动推断父项目；如果映射关系不稳定，考虑在 SKILL 的 `端到端流程` 步骤 3 中加入明确的选项列表查询步骤
- **`作业表URL` 没写入或格式不对**：确认传入的是完整的飞书分享链接（含 `view` 参数），例如 `https://bytedance.larkoffice.com/base/<token>?table=<tbl>&view=<view>`。目标表 `作业表URL` 是 text 类型（url 样式），传空串时脚本写入空值。
- **`人员` 字段没写上**：
  - 源表若是 user 字段：值形如 `[{"id":"ou_..."}]`，直接透传即可；
  - 源表若是 select 字段：脚本走 `contact +search-user` 解析 `name → open_id`。若某位真人解析不到 open_id（如已离职、跨租户不可见），会计入 `verified_bad` 并把该人整行丢弃。想强制写入可以先 `contact +search-user` 拿到 open_id，再在脚本里加白名单映射。
- **写入 400 / 类型报错**：核对目标表列名与脚本 `TARGET_FIELDS` 是否一致；`正确率` 必须是 number（小数），不要传 `"90%"` 字符串；`日期` 传 `YYYY-MM-DD 00:00:00`。
- **单次超 200 行**：`+record-batch-create` 单批上限 200；分人聚合结果一般远低于此，如超出需在脚本里分批。

## CLI 类

- **`+search-user` 的 flag 名**：飞书 CLI 用 `--query`，**不是** `--keyword`。同时它没有 `--limit`，用 `--page-size`。
- **`+base-get` vs 旧 `+get`**：拿 Base 名走 `lark-cli base +base-get --base-token <t>`；某些历史文档里出现的 `base +get --base-token` 已下线，会报 `unknown flag: --base-token`。
- **`+data-query` 报 `unknown flag: --format`**：历史遗留提示。当前脚本已改用 `+record-list --format json`，若手动排障再遇到，直接读 stdout JSON 即可。
- **认证 / scope 问题**：走 [`../../lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 排查登录态和 `bitable` / `contact` 权限。