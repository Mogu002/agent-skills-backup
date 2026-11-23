---
name: bytetech-article-reader
description: 当用户想读取 ByteTech 文章、提炼其正文，或把 `bytetech.info/articles/...` 链接转换成可直拉的飞书文档正文时，使用这个技能。默认先用 `lark-cli docs +search` 按标题反查真实 docx/wiki URL，再用 `lark-cli docs +fetch` 拉正文；只有定位不到时才接管 Chrome。NOT for 已经拿到可直接读取的公开网页，或已经给出可用 Feishu docx/wiki token 的场景。
---

# ByteTech Article Reader

用这个 skill 处理 ByteTech 文章读取，尤其是“外层是 ByteTech 壳，正文实际在内嵌 Feishu doc 里”的情况。

## Default Stance

- 先走最轻的读取路径，不要一上来就接管浏览器。
- 默认目标不是“读 ByteTech 外层页面”，而是**找到它内嵌的真实 Feishu docx/wiki token**。
- **首选 `lark-cli docs +search` 按文章标题反查真实 docx/wiki URL，这是最便宜的路径。**
- 一旦拿到真实 docx/wiki token，立即用 `lark-cli docs +fetch --api-version v2 --doc <token> --doc-format markdown` 拉正文。
- 只有 `docs +search` 也定位不到时，才升级到 Chrome 接管标签页，抓 iframe src 或网络请求里的真实 URL。
- 默认认领用户已经打开的目标文章标签页，而不是新开一个可能丢失登录态的页面。

## Use This Skill When

- 用户给的是 `bytetech.info/articles/...` 链接，希望你读文章、总结、入库或提炼方法。
- 你怀疑文章正文其实托管在 Feishu doc / wiki，而 ByteTech 只是外层壳。
- 直接 `curl` / `web` 打开只拿到飞书授权页、登录页或前端壳子。

## Do Not Use This Skill When

- 用户给的是可以直接用 `web` 读取的公开网页。
- 用户已经给了飞书 `docx/wiki` token 或 URL，且内容本体就在飞书文档里。
- 用户只是要日常入库或 lint 已经读到本地的内容。

## Required Reading

开始前按顺序读取：

1. [`references/workflow.md`](references/workflow.md)
2. [`references/gotchas.md`](references/gotchas.md)
3. [`scripts/chrome_helpers.mjs`](scripts/chrome_helpers.mjs) 仅在 `docs +search` 也定位不到、需要接管 Chrome 时才读取或导入

## Default Workflow

1. **拿到文章标题**：从用户输入、ByteTech URL 的页面 `<title>`、或用户直接给的标题里取。
2. **首选 `docs +search` 反查**：

   ```bash
   lark-cli docs +search --query "<标题或关键词>" --page-size 5 --format pretty
   ```

   返回结果里 `type=DOCX`、`url` 形如 `https://*.larkoffice.com/(docx|wiki)/<token>` 的就是正文入口。
3. **直接 fetch 正文**：

   ```bash
   lark-cli docs +fetch --api-version v2 --doc <token> --doc-format markdown
   ```
4. **只有 search 没命中时才接管 Chrome**：
   - 优先认领已打开的目标标签页（不新开页）
   - 从 iframe src 或网络请求里抠出 `*.larkoffice.com/docx/<token>`
   - 拿到 token 后立即回到步骤 3
5. 如有需要，再把抓到的 markdown 做轻量清洗，用于总结或入库。

## Key Gotchas

- 不要把“HTML 返回 200”误判为拿到了正文；ByteTech 外层经常就是飞书授权页 HTML。
- **不要尝试用 ByteTech URL 锚点里的 `#doxlg...` / `#doxcn...` 作为 fetch token**——实测 `lark-cli docs +fetch` 会返回 `api_error code=1 Internal error`，不要重试。
- 不要默认接管浏览器：先 `docs +search`，便宜得多。
- 不要默认新开标签页；已有标签页通常已经有正确登录态。
- 拿到真实 docx/wiki token 后，立即停止在 ByteTech 壳里硬抠正文。
- 不要依赖页面 `innerText` 全量 dump；噪声很大。

## Deliverable Standard

交付时至少应给出：

- 文章标题与来源
- 正文获取路径：`docs +search` 命中、还是 Chrome 兜底
- 拿到的真实 docx/wiki token 与本地 markdown 保存位置
- 2-6 条可靠关键结论（若用户要总结）
- 过程里遇到的访问边界或鉴权边界
