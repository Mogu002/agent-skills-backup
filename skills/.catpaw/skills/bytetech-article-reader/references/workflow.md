# Workflow

本文件描述 `bytetech-article-reader` 的默认读取流程。

## Goal

把 ByteTech 文章读取转成"直接拉飞书 docx/wiki 正文"。最便宜的路径是按标题用 `lark-cli docs +search` 反查真实 URL，只有它定位不到时，才借助用户现有 Chrome 登录态发现入口。

## Step 1: Resolve The Title

确认手里是否有文章标题或唯一关键词。来源优先级：

1. 用户输入里给出的标题
2. ByteTech 页面 HTML 里的 `<title>` 或 `og:title`
3. 用户手边能问到的关键词

只要拿到一段可用于检索的文字，就直接跳到 Step 2。**不必再尝试解析 ByteTech 锚点里的 `#doxlg...` / `#doxcn...`，那个 token 不可直拉。**

## Step 2: Search The Real Doc

```bash
lark-cli docs +search --query "<标题或关键词>" --page-size 5 --format pretty
```

返回结果里挑：

- `type=DOCX`
- `url` 形如 `https://*.larkoffice.com/(docx|wiki)/<token>` 或 `https://my.feishu.cn/(docx|wiki)/<token>`
- 标题与目标文章一致

如果有多个相近结果，结合 `edit_time` 与标题精确匹配挑出来。

## Step 3: Fetch Markdown

```bash
lark-cli docs +fetch --api-version v2 --doc <token> --doc-format markdown
```

输出里 `data.document.content` 就是 markdown 正文。可以用 `jq` / `python` 抽出来直接落盘。

## Step 4: Chrome Fallback (Only If Step 2 Misses)

升级条件：

- `docs +search` 完全没命中，或所有结果都明显不是这篇
- 标题非常通用，搜出来一堆无关条目

执行：

1. 列出已打开标签页，优先认领 ByteTech 文章页（不新开）
2. 在页面里找内嵌 Feishu doc 的真实 URL：
   - iframe `src`、Shadow DOM 里的 `docx/...`
   - 网络请求里的 `*.larkoffice.com/docx/<token>` 或 `my.feishu.cn/docx/<token>`
3. 拿到真实 token 后回到 Step 3

参考 [`../scripts/chrome_helpers.mjs`](../scripts/chrome_helpers.mjs) 的 `bootstrapChromeBrowser` / `findMatchingOpenTab` / `claimMatchingTab`。

## Step 5: Use Visible Content Only As Last Resort

只有 Step 4 也拿不到真实 token 时，才退回到从页面可见正文里提取，并且：

- 优先标题、可见段落、截图局部抽取
- 不要全页 `innerText` 直接当正文
- 避免混入右侧作者卡、目录树、推荐列表

## Step 6: Extract For Purpose

- 总结类：主题、关键论点、作者主结论、适用边界
- 入库类：建 source card，提炼 1-2 个 durable insight，更新 log / index

## When To Stop

满足任一条件即可停止：

- 已经拿到完整 markdown 正文
- 已经能稳定复述文章核心论点
- 已经够支撑 source card 与下游 practice/concept
- 继续提取只会增加噪声
