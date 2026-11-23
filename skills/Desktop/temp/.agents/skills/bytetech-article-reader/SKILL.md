---
name: bytetech-article-reader
description: 当用户想读取 ByteTech 文章、提炼其正文，或把 `bytetech.info/articles/...` 链接转换成可直拉的飞书文档正文时，使用这个技能。默认先找真实 Feishu doc token，再用 `lark-cli docs +fetch` 拉正文。NOT for 已经拿到可直接读取的公开网页，或已经给出可用 Feishu docx/wiki token 的场景。
---

# ByteTech Article Reader

用这个 skill 处理 ByteTech 文章读取，尤其是“外层是 ByteTech 壳，正文实际在内嵌 Feishu doc 里”的情况。

## Default Stance

- 先走最轻的读取路径，不要一上来就接管浏览器。
- 默认目标不是“读 ByteTech 外层页面”，而是**找到它内嵌的真实 Feishu doc token**。
- 一旦拿到真实 doc token，优先直接用 `lark-cli docs +fetch --doc <token> --doc-format markdown` 拉正文。
- 只要直读结果落到授权页、登录页或空壳页面，再切换到用户现有 Chrome 会话找真实 token。
- 默认认领用户已经打开的目标文章标签页，而不是新开一个可能丢失登录态的页面。

## Use This Skill When

- 用户给的是 `bytetech.info/articles/...` 链接，希望你读文章、总结、入库或提炼方法。
- 你怀疑文章正文其实托管在 Feishu doc / wiki，而 ByteTech 只是外层壳。
- 直接 `curl` / `web` 打开只拿到飞书授权页、登录页或前端壳子。
- 用户浏览器里已经有目标文章或相关站点的登录态，需要借它找真实 doc token。

## Do Not Use This Skill When

- 用户给的是可以直接用 `web` 读取的公开网页。
- 用户已经给了飞书 `docx/wiki` token 或 URL，且内容本体就在飞书文档里。
- 用户只是要日常入库或 lint 已经读到本地的内容。

## Required Reading

开始前按顺序读取：

1. [`references/workflow.md`](references/workflow.md)
2. [`references/gotchas.md`](references/gotchas.md)
3. [`scripts/extract_feishu_doc.mjs`](scripts/extract_feishu_doc.mjs) 用于从文本、HTML 或 iframe URL 中提取真实 doc token
4. [`scripts/chrome_helpers.mjs`](scripts/chrome_helpers.mjs) 仅在需要接管 Chrome 找 token 时读取或导入

## Default Workflow

1. 先确认是否已经有真实 Feishu doc token 或 URL：
   - 如果有，直接走 `lark-cli docs +fetch`
   - 如果没有，再从 ByteTech 页面里找
2. 轻量探测 ByteTech 页面：
   - `web` / `curl` 看是否直接暴露真实 doc 线索
   - 不把锚点里的 `#doxcn...` 直接当成可用 token
   - 如已拿到页面文本、HTML 或 iframe URL，优先跑 `scripts/extract_feishu_doc.mjs`
3. 如果轻量探测不够，再切到 Chrome：
   - 优先认领已打开的目标标签页
   - 在页面里找内嵌 Feishu doc 的真实 `docx` URL 或 token
4. 一旦拿到真实 token，立即改走 `lark-cli docs +fetch --doc <token> --doc-format markdown`
5. 如有需要，再把抓到的 markdown 做轻量清洗，用于总结或入库。

## Key Gotchas

- 不要把“HTML 返回 200”误判为拿到了正文；先识别是不是飞书授权页。
- 不要把 ByteTech 锚点里的飞书 token 当成一定可直接 `lark-cli docs +fetch` 的稳定入口。
- 不要把“从可见页面抄正文”当默认路径；那现在只是兜底，不是主路。
- 不要依赖页面 `innerText` 全量 dump 来读整篇文章；它很容易混入侧栏、相关推荐和目录树噪声。
- 不要默认新开标签页；已有标签页通常已经有正确登录态和滚动位置。
- 如果已经找到了真实 Feishu doc token，就不要继续在 ByteTech 壳里硬抠正文。
- `scripts/extract_feishu_doc.mjs` 只认真实 Feishu/Lark `docx/wiki` URL，不会把 `#doxcn...` 误报成可直拉 token。

## Deliverable Standard

交付时至少应给出：

- 文章标题与来源
- 正文获取路径：是直接 doc 拉取，还是 Chrome 兜底发现 token
- 如果拿到了真实 token，输出本地 markdown 正文或其保存位置
- 2-6 条可靠关键结论（若用户要总结）
- 过程里遇到的访问边界或鉴权边界
