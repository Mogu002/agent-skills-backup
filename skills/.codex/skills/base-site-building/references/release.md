# Base Site 发布与验收

常规发布只使用 `npx @lark-base-open/base-site-cli deploy`。CLI 内部固定执行：生成 Function metadata → 全量 SQL 校验并汇总失败项 → 根据依赖指纹安装必要依赖并构建 → 归档 → Functions 全量更新 → Artifact 上传与源码回读 → Preview 发布与状态轮询。存在任一 SQL 校验失败时不会安装依赖或执行 Page/FaaS build；依赖指纹未变化且对应 `node_modules` 仍存在时自动跳过 `npm ci`，但仍重新执行 build。仅在排障时使用 `--force-install` 强制重装或用 `--no-install` 无条件跳过安装。

## Preview

```bash
npx @lark-base-open/base-site-cli deploy
```

该命令通常需要约 30 秒到 1 分钟，中间不显示阶段进度。

成功结果包含制品大小、SHA-256、publish ID、`managementUrl` 和平台原样返回的 `appUrl`。CLI 把 Preview 凭据保存在被 Git 忽略的 `.base-site-cli/state/preview.json`，临时制品保存在同目录下的 `artifacts/`。

部署成功后提供 `managementUrl`、原始 `appUrl`、本次变更摘要和短验收清单，让用户尽快开始体验。Agent 不打开浏览器、不直调 Function，也不继续修改或发布；唯一允许的发布后配置收尾，是使用本次原始 `appUrl` 完成原生通知 workflow 的 Site 入口。用户需要在飞书登录态打开 `appUrl`，确认：

1. 路由不是 404/5xx；
2. HTML 与静态资源加载成功；
3. 页面出现本次版本内容；
4. SQL Function 能读取真实 Base 数据；
5. 平台支持 FaaS 时，从页面写入并由 SQL Function 回读同一记录。
6. 页面通过 `createArgusCsrfPlugin()` 加载 Argus Runtime；真实 JSSDK 写请求携带 `x-secsdk-csrf-token`，且端到端调用成功。

提示用户体验完成后回复“部署正式版”。

### 原生通知入口收尾

发布前逐个检查 `LarkMessageAction`，按固定优先级确定入口：用户明确要求进入多维表格时使用 `base_action`；用户明确要求通知纯展示、无需点击入口时使用 `informational`；其他所有与 Site 业务对象关联的通知一律使用 `site_action`。不得从通知正文足够完整或用户未指定跳转目标推断 `informational`。

1. Page 先实现通知对应的真实功能路由。新 `site_action` workflow 在 Preview 发布前不创建；不得用 `$.<trigger>.recordLink`、Base URL、`managementUrl` 或自行拼接 URL 兜底。
2. `deploy` 成功后只使用响应原样返回的 `preview.appUrl` 作为环境基址。新 workflow 直接在 `+workflow-create` 中把业务按钮配置为“该基址 + Page 已实现的通知对应功能路由 + workflow 上下文中的目标对象标识”；已有 workflow 才先 `+workflow-get`，再用完整定义执行 `+workflow-update`。例如访客接待通知进入当前访客登记详情，考试通知进入对应考试详情或答题页；不得只填裸 `appUrl`。
3. `informational` 只有在用户明确要求通知纯展示、无需任何点击入口时才允许 `btn_list=[]`，并必须记录用户原文。空按钮列表不代表原生通知不可点击，也不能证明它不会沿平台默认行为跳转 Base。
4. `base_action` 只在用户明确要求通知进入多维表格时使用；回读并记录该授权语义，不得将 Base `recordLink` 描述成 Site 入口。
5. 执行 `+workflow-enable`，随后 `+workflow-get` 回读全部 `LarkMessageAction`：核对入口策略、启用状态、按钮列表；`site_action` 还要确认业务按钮使用本次 `preview.appUrl`，并能从 URL 结构上定位到当前 Preview Site 中对应的功能与业务对象。任一条件不满足时立即执行 `+workflow-disable`，并把结果标记为 partial 或 blocked。
6. 在 Preview 交付清单中记录每个相关 workflow ID、入口策略、按钮字段路径，以及去掉 `preview.appUrl` 后的路由模板；没有按钮时记录平台默认跳转限制。Prod 切换必须复用这份清单，不得只更新碰巧记得的一个按钮。
7. 完成后立即交付 Preview；不得借此继续修改 Page、调用 Function 或发布 Prod。

## Prod

只有用户体验本次 Preview 后明确回复“部署正式版”，才执行：

```bash
npx @lark-base-open/base-site-cli deploy --production --yes
```

CLI 校验 Preview 记录、Site token 和 Artifact SHA-256，随后直接发布同一制品，不重建、不替换。`--yes` 只表示调用方已经取得本次 Prod 授权；不能用任务开始时笼统的“搭建并发布”代替，也不能由 Agent 自行验收后授权。

`deploy --production` 只发布 Site 制品，不会自动更新 Base workflow。Prod 发布成功后，只要 Preview 交付清单包含通知入口，就必须对清单中的每个 workflow 执行 `get` → 完整 `update` → `get`。`site_action` 使用响应原样返回的生产 `appUrl`，只替换环境基址，逐字保留对应的站内功能路由、动态对象参数、其他步骤和启用状态；`informational` 和 `base_action` 不改写入口语义，只复核按钮列表、平台限制或用户明确要求仍然成立。回读验收必须同时满足：每个 Site 业务 `openLink` 都以生产 `appUrl` 为基址、路由模板与 Preview 阶段一致、链接中不再出现 Preview 基址，且 workflow 启用状态未变化。`site_action` 不得退化为 Site 首页、Base 记录或 Site 管理后台。

Prod Site 发布成功但任一 workflow 更新或回读失败时，不要重新发布 Prod，也不要报告整体完成；明确告知用户“Prod 已发布，但通知入口切换未完成”，附上失败的 workflow ID 和脱敏错误，修复后重新执行 `get` → `update` → `get` 收尾。

## 发布状态

CLI 使用 publish 响应中的 `publishId`，并通过 query 调用 status：

```text
GET /open-apis/base/v3/sites/:site_token/publish_status?publishId=:publish_id
```

每 5 秒轮询，最多 3 分钟：`0/1` 继续，`10` 成功，`20` 失败，未知状态停止。使用响应原样返回的 `result.appUrl`，不拼接或改写。

## 故障证据

失败时保存环境、Site token、阶段、publish ID、脱敏响应和 LogID/Edge request ID。

写请求失败时先排除登录、权限和业务错误；若未加载 Argus Runtime 或请求缺少 `x-secsdk-csrf-token`，升级 JSSDK 并重新构建发布，不得手写 Token。
