# Workflow

本文件描述 `bytetech-article-reader` 的默认读取流程。

## Goal

在 ByteTech 文章无法被直接抓取时，优先找到其内嵌的真实 Feishu doc token，并直接拉取 markdown 正文；只有在 token 还拿不到时，才借助用户现有浏览器登录态继续发现入口。

## Step 1: Prefer The Real Doc Over The Outer Shell

先判断是否已经拥有以下任一信息：

- Feishu `docx/wiki` URL
- 可用的真实 Feishu doc token
- 已经确认正文本体就在 Feishu 文档里

如果有，直接走：

- `lark-cli docs +fetch --api-version v2 --doc <token> --doc-format markdown`

不要继续在 ByteTech 外层页面里抄正文。

## Step 2: Light Probe The ByteTech Page

先尝试最轻路径：

- `web` 打开页面
- 或一次轻量 `curl`
- 如果已经拿到了 HTML、片段文本或 iframe URL，运行 `scripts/extract_feishu_doc.mjs`

目标不是在这里读完整正文，而是判断：

- 页面是不是授权页 / 登录壳
- 是否能直接看到真实 Feishu doc 线索
- 锚点里的 token 是否只是站内映射

## Step 3: Detect When Direct Read Is Not Enough

以下信号说明直读失败，应升级到 Chrome：

- 页面标题、正文或脚本明显是飞书授权页 / 登录页
- HTML 只有前端壳，正文为空或严重缺失
- 链接返回的内容与文章标题明显不符
- 页面需要用户现有会话、Cookie 或浏览器登录态
- 你仍然没有拿到真实 Feishu doc token

## Step 4: Claim Existing Chrome Tab

Chrome 路径在这里的主要用途是**发现真实 token**，不是长期留在页面里手工摘正文。

优先顺序：

1. 列出用户已打开标签页
2. 找 URL 精确或片段匹配的文章页
3. 认领该标签页
4. 只在没有匹配标签页时再考虑新开页

推荐使用 [`scripts/chrome_helpers.mjs`](../scripts/chrome_helpers.mjs) 中的 helper：

- `bootstrapChromeBrowser`
- `findMatchingOpenTab`
- `claimMatchingTab`

## Step 5: Extract The Embedded Feishu Doc URL Or Token

在 Chrome 中优先找这些线索：

- 自定义组件里的 iframe `src`
- Shadow DOM 里的 `docx/...` URL
- `my.feishu.cn/docx/...` 或 `*.larkoffice.com/docx/...` 这类真实文档地址

一旦拿到真实 token，立即退出“页面抄正文”路线。

推荐把找到的 URL 或片段文本交给：

- `node scripts/extract_feishu_doc.mjs --text '<iframe src or raw snippet>' --pretty`
- `cat page.html | node scripts/extract_feishu_doc.mjs --stdin --pretty`

## Step 6: Fetch Markdown From Lark CLI

拿到真实 token 后，改走：

- `lark-cli docs +fetch --api-version v2 --doc <token> --doc-format markdown`

如果成功，正文来源以 CLI 输出为准。

## Step 7: Use Visible Content Only As Fallback

只有在真实 token 暂时仍拿不到时，才退回到页面可见内容提取。

默认优先级：

1. 页面标题和元信息
2. 可见段落
3. 截图辅助确认
4. 局部文本窗口抽取

避免：

- 全页 `innerText` 直接当正文
- 把相关推荐、右侧作者卡片、树状目录混进结论
- 盲目抓整页 DOM 后硬总结

## Step 8: Extract for Purpose

如果目标是总结：

- 提取主题
- 关键论点
- 作者的主结论
- 适用边界

如果目标是 wiki ingest：

- 建 source card
- 只提炼 1-2 个 durable insight
- 更新 log / index

## When to Stop

满足以下任一条件即可停止加深读取：

- 已经拿到真实 Feishu markdown 正文
- 已经能稳定复述文章核心论点
- 已经有足够证据支撑 source card 和 practice/concept
- 继续提取只会增加噪声，而不会提高判断质量
