# Chrome 执行契约

## 运行方式

脚本是无依赖的 CUA REPL helper，不是终端 Chrome 驱动。先按 browser Skill 初始化绑定，读取实际接口说明、命名会话。用正常文件读取工具完整读 `scripts/chrome_evidence.js`，把内容作为 JavaScript 在 CUA REPL 顶层执行一次；不是在网页 evaluate 中加载，不使用浏览器控制台、动态执行网页代码或未暴露的文件/网络 API。无需 npm 安装。`module.exports` 只供离线 Node 测试使用。

参数中的 URL 必须取自本次 `await tab.url()` 并人工确认是用户指定产物；不可先盲用当前 URL 再当成身份验证。浏览器跳转或重定向后先观察、核对新 URL 再更新参数。`identityConfirmed:true` 是调用者已核对账号/租户的声明，不是独立认证保证。

```javascript
// tab 为按实际 CUA 文档建立的既有标签页绑定。
var ctx = {expectedUrl: await tab.url(), identityConfirmed:true};
nodeRepl.write(await doubaoChrome.open(tab, {...ctx, action:'fields'}));
// 读取新状态；必要时等待页面自身可见的加载完成信号，不固定 sleep 或盲重试。
// scopeSelector 必须来自刚观察的 DOM，定位唯一、可见且已加载的组件祖先。
var evidence = await doubaoChrome.collect(tab, {
  ...ctx, kind:'fields', object:'当前已确认的数据表',
  scopeSelector:'从实际 DOM 得到的字段列表容器选择器',
  expectedText:'本次列表实际显示的一个目标字段名'
});
nodeRepl.write(evidence);
```

不要把示意字符串当作真实 CSS。用已知可见元素的 DOM 祖先定位合适容器；不读取 React/运行时私有模型。提取数组的 scope 是条目共同祖先（不是条目自身）。`one()` 要求唯一、可见；root 文本要匹配 `expectedText` 且不处于加载状态。页面残留多个面板时不改成 `.first()` 消除歧义，应重新定位。

## 原子导航动作

`open(tab,{...ctx,action,...参数})` 只执行一个 allowlisted 动作，返回当前 URL 和新 snapshot。点击完成不等于加载完成；由 Agent 看返回状态再继续。所有按钮/对象必须在最新 UI 中真实观察到；参数 name/id 不能由 Query 猜造。

| action | 参数/前提 | 下一步 |
|---|---|---|
| object | id：侧栏已读对象 ID，不带 DOM 前缀 | 核对 URL、对象及加载状态 |
| fields | 当前表工具栏可见字段配置 | collect fields |
| field_menu | name：字段列表中精确名称 | field_edit |
| field_edit | 当前菜单唯一编辑项 | 等详情加载，collect field_detail |
| field_cancel | 当前唯一取消按钮属于字段编辑面板 | 验证已关闭 |
| chart_menu | id：当前图表 DOM data-id；菜单按钮可见 | chart_config |
| chart_config | 当前菜单“配置” | collect chart_detail |
| workflow_step | name：当前画布节点精确名称 | collect workflow_step |
| share | 唯一分享按钮 | 检查高级权限状态 |
| permissions | 分享面板“查看”入口已存在 | 等高级权限 dialog |
| permission_target | name：dialog 内唯一角色/表名称 | collect permission |
| permission_close | dialog 的 CloseOutlined 按钮 | 验证退出且未保存 |
| form_editor | 分享表单的“编辑问卷” | 核对源 Base/table/view URL |
| form_settings | 编辑问卷的已观察设置图标 | collect form_settings |

没有动作对应的步骤，使用已文档化的 CUA 语义导航并即时观察；不要添加未经验证的通用 `click(selector)` 后门。不能为显露图表菜单而改布局。选中问题可读取必填控件，不能切换必填。脚本不会自动打开所有页面或迭代所有角色，不保证一条调用完成全库取证。

## 采集类型

`collect` 需要 `kind/object/scopeSelector/expectedText/expectedUrl/identityConfirmed`。`object` 应含可用 ID 与名称，以便同名对象区分。

| kind | 输出 | 声明的能力 capability |
|---|---|---|
| inventory | 当前挂载侧栏 ID、名称 | mounted_inventory |
| fields | 字段名、类型图标；不是完整类型 schema | field_names_icons |
| widgets | 当前 Dashboard 挂载组件 ID、class、文字、几何 | mounted_widgets |
| workflow_nodes | 当前画布节点文本和几何，不推导边 | visible_nodes |
| field_detail | 指定字段原生面板文本/控件；公式可在文本中 | field_panel |
| chart_detail | 指定图表配置面板文本/控件 | chart_panel |
| workflow_step | 指定节点的配置文本/引用/控件 | node_panel |
| permission | 当前高级权限 dialog；保留字段行与控件对应 | permission_panel |
| form | 分享页当前表单容器文本/控件；questions 含 DOM ID、题名、题序、星号、选项区域原文 | visible_form |
| form_settings | 表单设置面板文本与控件 | form_settings_panel |

panel 类返回 raw text 和 controls 数组，不臆造后台字段 ID。语义整理需引用原文/控件路径；snapshot 中星号不是后端校验成功证明。permissionFields 的 association=unresolved 时不可按全局数组序号猜行。按钮型 switch 可能无 aria-checked；脚本保留原始 class，以 `ud__switch-checked` 作为当前已验证 UI 的状态标志。未知控件 checked=null，不当 false；禁用与未选中分开。自定义 class 变动时停用相应解析并回归。

可复用的作用域候选（每次仍需核对当前 DOM）：侧栏 `#J-side-bar-scroll-container`；高级权限 `[role="dialog"]`；Form `.base-form-container_content`；Form 设置 `.form_setting_card.main`；工作流画布 `.gedit-playground`；节点详情 `.base-workflow-builder-step-form-container`。不要使用 `.gedit-flow-nodes-layer`：可能同时存在多个零尺寸层，脚本应拒绝而非强取第一个。字段与图表面板先从当前标题的 DOM 祖先定位唯一组件容器。

## 输出/缺口/评分

返回 evidence JSON：adapter/version/time/url/object/kind/scope、data、captureStatus、evidenceGaps、coverage。非空仅 `captured`；所有记录保守标 `partial`，因为只证明当前挂载范围。无 `human_eval_fields` 或分数。输入不合法、身份/URL不符、范围歧义、UI未加载或工具错误抛异常；由 Agent 记录失败/缺口并停止当前动作，不将失败解释为空产物。脚本不吞控制权异常，不在 finally 中继续点击。

按需将 JSON 用文件工具保存到每题的新输出目录；不要覆盖旧证据或输出 cookie/凭据。此 helper 不自行写文件、发请求、分页、调用 CLI。

固定未验证项：full_inventory_virtualization、full_schema、all_records、formula_results、all_widget_configs、chart_recalculation、visual_verification、complex_workflow_topology、workflow_execution、permission_effective_access、permission_conditional_rules、all_roles、form_conditional_logic、form_submission、source_field_types。每个 kind 返回相关缺口；未请求模块另记 not_requested，不等于 NA。一个缺口只有在 Query 要求它时阻塞正式评分；其他来源的等价可靠证据可以补齐，但保留来源和验证理由，不能删除原采集限制。

`reviewCoverage(evidence, requirements)` 做精确 object+kind+capability 对照。requirements 每项为 `{object,kind,capability}`，必须由 Query 推导；返回 missing 与 needs_semantic_review/evidence_gaps。未知 capability 永远缺证据，`mayAutoScore` 永远 false。调用者必须进一步逐验收点审查面板内容，不能以清单匹配代替正确性判断。

证据齐全后执行主 Skill 的计分；输出原样 human_eval_fields。证据不足：状态“待核验”、已确认事实、缺口表（人评维度/对象/所缺信息/原因/补证路径），不填最终分数、不把缺口变成零分或不涉及。
