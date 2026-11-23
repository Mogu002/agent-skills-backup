# Dashboard Browser Evidence

仅在评测对象包含飞书多维表格仪表盘，且官方 CLI/OpenAPI 未返回完整组件或内部配置时读取本文件。目标是补齐评测证据，不是把网页私有接口当成稳定公共 API。

## 前置条件

- 用户已提供或授权访问目标 Base 链接。
- 浏览器中已有可访问该 Base 的登录会话。
- 浏览器控制能力可以定位并接管精确匹配的标签页；默认使用 `ego-browser nodejs`，并按 skill 的 task space 规则复用/创建隔离任务空间；若使用标准 Playwright/CDP，需要相应调试连接权限。
- 全程只执行读取、刷新和必要的悬浮查看；不编辑仪表盘、不改变筛选配置、不导出凭据。

## 证据链

### A. 官方读取基线

记录以下事实：

- Base token 与 URL 中的 table/dashboard 标识。
- CLI/OpenAPI 是否识别出 dashboard 对象。
- 返回的是完整组件、空数组、`blocks: []`、not found，还是其他错误。
- Base 的表、字段和记录数据是否可由公开接口正常读取。

官方读取不完整时，只能得出“公开读取未返回关键内容”；不能据此判定网页端为空。

### B. 已登录页面组件

使用 `ego-browser` 时，建议按以下只读顺序执行：`useOrCreateTaskSpace` → `openOrReuseTab` → `pageInfo` / `snapshotText` → `js` 读取 DOM 和前端状态 → `performance.getEntriesByType('resource')` 或 `cdp` 读取网络资源。为每个组件记录：

- 标题与组件类型：统计卡、趋势图、排名、表格、筛选器等。
- 可见值、单位、格式、图例、排名顺序和筛选器当前状态。
- 当前页面实际暴露的稳定 `data-*` 标识和类型 class；不要依赖元素位置或标签索引。
- 是否使用 Canvas。Canvas 无文本时，继续查请求响应、悬浮提示或截图，不得判空。

若页面出现 `.layout-item.dashboard-v2`，可将它作为已观察到的组件容器候选，但每次仍应先由最新 snapshot/DOM 验证选择器存在。

### C. 页面资源与数据链路

从页面已观察到的 resource/XHR/fetch 清单中筛选 dashboard、chart、clientvars、block_info、csr/config 等关键词。常见但非永久保证的路径形态包括：

```text
/space/api/v2/sheet/blocks/dashboard/web_ssr/charts?token={base_token}&tableID={dashboard_id}
/space/api/v1/bitable/{base_token}/clientvars?tableID={dashboard_id}...
/space/api/bitable/{base_token}/block_info?table={dashboard_id}
/base/csr/config?token={base_token}&isDashboard=true&table={dashboard_id}
```

必须以当前页面实际观察到的 URL 为准。不得把示例占位符替换成固定样本值并写回技能。

### D. 响应体读取

若运行时支持标准 Playwright，应在触发刷新前注册监听，避免错过早期请求。`ego-browser` 的默认实现可能只提供页面资源清单而不直接暴露 Playwright `page` 对象；此时优先使用 `js` 读取 `performance` 资源和页面前端状态，不要为了获取响应体而读取认证凭据：

```js
const responsePromise = page.waitForResponse(response => {
  const url = response.url();
  return url.includes('/dashboard/web_ssr/charts') && response.request().method() === 'GET';
});

await page.reload({ waitUntil: 'domcontentloaded' });
const response = await responsePromise;
const payload = await response.json();
```

从响应中按实际结构检查 dashboard client variables、data slices、snapshots、图表数量和组件配置。字段名可能变化，因此先记录顶层键和类型，再做范围受控的解析；不要整包输出可能包含无关数据的页面状态。

若标准 Playwright response 监听不可用，但 Chrome CDP 可用，可使用 Network 域观察对应 GET 响应并读取 response body。若两者都不可用，停在 DOM + resource 证据，不要通过读取 Cookie、localStorage 或认证头绕过限制。

## 评测映射

将浏览器证据映射回 query，而不是只报告“抓到了组件”：

- 组件存在性：标题、类型和组件标识共同证明。
- 指标口径：字段/指标、聚合方式、单位及显示结果共同证明。
- 维度与排序：轴、图例、排名条目或响应配置共同证明。
- 筛选与联动：筛选器配置和当前状态共同证明；只有筛选器名称不足以证明条件正确。
- 可用性：组件成功渲染且有与数据一致的结果；错误占位、空画布或明显异常值需要单独记录。

若只能看到最终数值而读不到内部配置，可以证明“当前渲染结果”，不能据此断言数据源、聚合或筛选配置正确。此时应输出 `无法评测` 或仅对已有明确证据的独立错误判 0。

## 停止条件

完成以下任一闭环后停止继续抓取：

1. 已取得足以覆盖 query 硬性约束的组件配置和渲染结果；或
2. DOM、资源、响应监听及截图/OCR均无法取得关键配置，已明确列出缺失证据；或
3. 浏览器没有所需登录态或控制权限，继续操作需要用户提供新权限。

结束浏览器任务时释放接管的用户标签页，并关闭仅为取证创建的临时标签页。
