# CLI Reading Paths

本文件只覆盖 Base 的只读检查路径。若任务变成创建、修改、批量写入、聚合分析或回答业务结论，停止继续，转读 `lark-base`。

## 1. 先定位 Base 与当前对象

用户给的是 Base URL：

```bash
lark-cli base +url-resolve --url "<base-url>" --as user
```

用户给的是标题或关键词：

```bash
lark-cli base +title-resolve --title "<keyword>" --as user
```

这一层通常只拿：

- `base_token`
- 当前 URL 命中的 `table_id` / `view_id`
- `resource_type`

到这里就应停下来问自己：

- 用户只要当前 Base token 或当前表 ID 吗？
- 还是要左侧栏全部对象？
- 还是要继续读某张表 / 某个 dashboard？

遇到这些错误，不继续读 Base，改读 `lark-shared`：

- `token_missing`
- `need_user_authorization`
- `missing_scopes`
- `verify_failed`

## 2. 列出左侧栏对象

如果目标是“这个 Base 里到底有什么”，先跑：

```bash
lark-cli base +base-block-list --base-token <base_token> --as user
```

这一步是左侧栏对象的主入口，通常能列出：

- `table`
- `dashboard`
- `workflow`
- `docx`
- `folder`

拿到结果后，先记录：

- `id`
- `name`
- `type`
- `parent_id`

如果用户只想知道“有哪些表 / 看板 / 工作流”和它们的 ID，到这里就可以结束。

## 3. 表读取分支

只有在已经确认目标是 `table` 时，才继续下钻。先转读 `lark-base`，再按需使用这些最小命令：

字段：

```bash
lark-cli base +field-list --base-token <base_token> --table-id <table_id> --as user
```

记录样例或内部诊断：

```bash
lark-cli base +record-list --base-token <base_token> --table-id <table_id> --as user
```

单条记录回查：

```bash
lark-cli base +record-get --base-token <base_token> --table-id <table_id> --record-id <record_id> --as user
```

规则：

- 用户要字段结构，先读 `+field-list`，不要先拉记录。
- 用户要视图配置，再去 `lark-base` 展开 `+view-*`，不要在本文件里继续抄完整 view 命令表。
- 用户要全量统计、TopN、归因、聚合结论，不要靠本地读取一页记录手工推断；转回 `lark-base` 的 `base:assistant` 路径。

## 4. Dashboard 读取分支

如果 `+base-block-list` 已经拿到：

- dashboard 名称
- dashboard block id

且用户只要“看板在不在、叫什么、ID 是多少”，到这里就停止。

如果用户还要 dashboard 的内部 block、图表配置或 CLI 级别结果：

- 转读 `lark-base`
- 只展开它的 dashboard 相关 reference

如果 CLI 返回空、信息不全，或者用户要：

- 真实渲染图表标题
- 统计卡数值
- 排行榜可见内容
- 看板实际切换入口
- 截图级证据

就转读 `ego-browser`，走已登录浏览器分支。

浏览器分支的判断标准：

- 以 URL / 当前对象变化来确认是否真的切入 dashboard
- 以页面已渲染的统计卡、图表标题、可见文本来确认内容
- 下方组件不在首屏时，继续检查内部滚动容器，而不是只看主页面滚动

## 5. 身份与权限分支

优先用 `--as user` 读取用户自己的 Base。

若 `user` 身份报缺 scope、授权失效或提示需要登录：

- 停止当前 Base 读取
- 转读 `lark-shared`

若尝试 `--as bot`：

- 只能把它当兜底验证，不当默认路径
- `app_scope_not_applied` 属于应用侧未申请 scope，不是用户重新点授权就能解决

## 6. 停止条件

出现以下任一条件时，结束本 skill 的读取链：

- 已拿到用户要的 token / block id / 对象清单
- 任务已经进入建表、改表、建 dashboard、建 workflow、写记录
- 用户要的是分析结论而不是元数据
- CLI 进入盲区，且需要转浏览器或转认证恢复
