# Gotchas

本文件沉淀 ByteTech 文章读取过程中暴露出的高频坑点，重点是"外层壳"和"真实正文入口"不要混淆。

## 1. `curl` 成功不代表文章可读

ByteTech 链接可能返回 200，但内容其实是飞书授权页或登录壳子。先看 `<title>`、正文和关键脚本，不要只看 HTTP 成功。

## 2. ByteTech URL 锚点里的 doc token 不可直拉（实测）

像 `#doxlgGN9dwF7kAeQZk7KyAq9ntb`、`#doxcn...` 这样的锚点看起来像飞书文档 token，**但 `lark-cli docs +fetch` 实测都会返回 `api_error code=1 Internal error`。**

它只是 ByteTech 站内做的"片段定位"映射，不是 docx 的标准 token。

→ 不要反复重试，也不要试 `--api-version v1` 当作绕过手段。直接走 `docs +search` 反查真实 docx/wiki URL。

## 3. `lark-cli docs +search` 是最便宜的真实 URL 发现路径

只要手里有文章标题或唯一关键词，就先 search，不要先接管浏览器：

```bash
lark-cli docs +search --query "<标题>" --page-size 5 --format pretty
```

返回 `type=DOCX`、url 是 `*.larkoffice.com/(docx|wiki)/<token>` 的就是正文入口。

## 4. Chrome 接管是兜底，不是默认路径

只有 `docs +search` 也定位不到时，才升级到 Chrome：

- 登录态已就绪
- iframe / 网络请求里能挖到 `*.larkoffice.com/docx/<token>` 这种真实 URL
- 优先认领已打开标签页，不要新开页

## 5. 一旦拿到真实 docx/wiki token，立刻停手

继续在 ByteTech 页面里用 DOM、截图或手工复制正文，只会增加噪声。立即走 `docs +fetch --api-version v2 --doc <token> --doc-format markdown`。

## 6. DOM 不是唯一真相

页面 `innerText` 全量 dump 会混入右侧作者卡、树形目录、推荐文章、底部专题列表。需要可见正文兜底时，用截图 + 局部抽取，不要单吃一个大文本串。

## 7. ByteTech 自身 API 需要登录态

`https://bytetech.info/api/articles/<id>` 直接 302 到登录页，纯 curl 没法拿元信息。
