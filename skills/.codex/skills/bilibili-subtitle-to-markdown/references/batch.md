# 收藏夹批量采集

适用于“把这个收藏夹的视频字幕都保存下来”“先列目录，再采集选定数量”“继续上次批量任务”。只保存字幕和元数据，不下载音视频、不改变收藏。视频默认只采 P1；用户要全分P时，另按视频元数据逐P调用单视频入口，不把 P1 当整部视频。

## 默认路径

从当前 `SKILL.md` 的绝对路径解析 `scripts/batch.py`，不依赖固定安装目录。`SOURCE` 是收藏夹正整数 ID，或带 `fid=` 的收藏夹 URL；`OUTPUT_DIR` 遵循当前工作区产物规则。在 personal-wiki 中写到 `raw/inbox/`，采集后由独立 ingest 流程登记，不能自动生成 wiki 页面。

```bash
python3 "<skill目录>/scripts/batch.py" "$SOURCE" --output-dir "$OUTPUT_DIR"
```

流程：匿名 GET `/x/v3/fav/resource/list`，参数 `media_id`、`pn`、`ps=40`、`platform=web`；每页落盘后再读下一页，直到 `has_more=false`。然后对普通视频按 BV 去重，串行调用同目录 `extract.py`，相邻视频之间等待 1 秒。已有成功项只有在文件 SHA-256、BV、CID、P1、字幕条数和验证报告一致时跳过。

常用选项：

- `--list-only`：只保存收藏目录。完整列出时退出 0，尚未读全时退出 3。
- `--max-pages 1 --limit 2`：本次仅新列一页、最多尝试两个视频；只是有意限量，不能宣称全收藏夹完成。
- 相同命令、相同目录：续读 `next_page`，继续未尝试的视频；成功项不重新抓取。
- `--retry-failed`：稍后恢复失败、待浏览器或上次限流的条目；每条最多重试一次，遇到新限流仍停止。
- `--timestamps`：仅在用户明确需要时间轴时使用；续跑时须保持相同选项。
- `--help`：查看完整接口。

`batch-state.json` 保存收藏夹 ID、原始标题、作者、发布时间、简介、来源 URL、分页完整性、每项状态和成功校验报告。正文为 `BV号.P1.md`。每读一页、每完成一个视频都原子更新状态。失败、无字幕、失效条目不混作成功；条目类型非普通视频记为 `unsupported`。列表读到末页但去重后的条目数与 `media_count` 不符时，仍是 `list_complete=false`，可能有隐藏条目或分页期间变动。

退出 0 表示本次任务范围完整完成，3 表示部分完成或等待补采，2 表示输入或状态错误。每次 stdout 输出最终 JSON，stderr 输出逐视频进度。`ok=true`（非 `--list-only`）要求列表完整且每一项字幕保存成功；最后必须报告 `expected_count`、`listed`、`counts`、`stopped`，不只报告生成文件数。

## 登录或私密收藏夹：浏览器页回退

匿名接口拒绝、返回登录要求或读取盲区时，按当前浏览器 Skill 连接用户已有登录态，打开目标收藏夹页面。先查看页面确认收藏夹和登录情况。浏览器不可用、未登录或无访问权时停止并说明；不读、复制或导出 Cookie。`THROTTLED` 必须停止整个任务，不能换浏览器身份继续请求。

用浏览器自己的 `evaluate` 执行以下函数，每次只读 `batch-state.json.next_page` 指定的一页。它只发固定域名的 GET，使用浏览器内部登录态；不要把本机 Python 变成携带导出 Cookie 的客户端。浏览器工具若不支持这类读取，则捕获页面自身加载的相同接口响应，再包装成下述格式，不绕过浏览器工具限制。

```js
async ({ folderId, page }) => {
  if (!/^\d+$/.test(String(folderId)) || !Number.isInteger(page) || page < 1)
    throw new Error("需要收藏夹 ID 和正整数页码");
  const query = new URLSearchParams({ media_id: String(folderId), pn: String(page), ps: "40", platform: "web" });
  const response = await fetch(`https://api.bilibili.com/x/v3/fav/resource/list?${query}`, {
    credentials: "include", signal: AbortSignal.timeout(15000)
  });
  if ([412, 429].includes(response.status)) throw new Error("THROTTLED：停止任务，稍后续跑");
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const payload = await response.json();
  if ([-352, -412, -509].includes(payload.code)) throw new Error("THROTTLED：停止任务，稍后续跑");
  if (payload.code !== 0) throw new Error(`接口 code=${payload.code}；检查页面登录和访问权`);
  return { folder_id: String(folderId), page, payload };
}
```

只把返回的响应正文包装 JSON 保存为 `OUTPUT_DIR/favorites-page-N.json`，不要保存请求头、Cookie、浏览器存储或整份网络日志。导入并立即落盘：

```bash
python3 "<skill目录>/scripts/batch.py" "$SOURCE" --output-dir "$OUTPUT_DIR" \
  --page-json "$OUTPUT_DIR/favorites-page-N.json" --list-only
```

查看新的 `next_page` 后继续，页请求至少间隔 1 秒；直至列表完整或出现停止条件。`--page-json` 本次只处理传入的页，不自动读其余匿名页。若没有 `batch-state.json`，从第1页开始。采集过程中数量变化、空的中间页、ID不符或缺页时不声称完成。

## 单条字幕待浏览器补采

批量状态为 `browser_required` 时，使用主 Skill 已有的原生字幕网络响应回退。输出使用该条目的固定路径 `BV号.P1.md`。成功调用的 stdout 原样保存到报告文件，不手写成功字段或哈希：

```bash
python3 "<skill目录>/scripts/extract.py" "$VIDEO_URL" \
  --subtitle-json "$TEMP_JSON" -o "$OUTPUT_DIR/$BVID.P1.md" \
  > "$OUTPUT_DIR/$BVID.P1.result.json"
python3 "<skill目录>/scripts/batch.py" "$SOURCE" --output-dir "$OUTPUT_DIR" \
  --accept-result "$OUTPUT_DIR/$BVID.P1.result.json" --list-only
```

若任务使用 `--timestamps`，上述两个命令同样追加该参数。报告导入会核验 BV、CID、分P、字幕条数、时间轴标记和真实文件哈希，不能仅靠文件存在就标成功。完成后删除临时字幕响应文件。字幕确实不存在时报告缺失，不用简介、评论或 AI 摘要冒充字幕。

## 续跑与一致性边界

- 状态是一次收藏夹读取快照。继续同目录不会自动检查新增或移除收藏；要重新采集最新目录，使用新的输出目录，保留旧来源。长时间中断后，分页排序可能变化，应重新列出快照，不把跨天接上的分页视为稳定快照。
- 这里提炼了分页、本地缓存、去重、串行队列和部分完成语义；没有照搬源项目的账号写入、全量 ID 差分同步或删除缓存机制。
- 不覆盖已有 Markdown；记录缺失或哈希变化记为 `conflict`。异常退出后有文件但状态未写回时，可用真实的 `extract.py` 成功报告通过 `--accept-result` 补录；无报告则人工核查或换新目录。
- `.batch.lock` 防止同一目录并发执行。被强制终止后，先确认原进程已结束，再移除残留锁；不要给运行中的任务解锁。
- 结果带时长警告时要说明；截图、字幕、摘要属于不同证据类型，批量字幕完成不表示视频视觉内容也已保存。

## 实现证据

方法依据：MoonDigest 的[收藏夹分页](https://github.com/PathGao/MoonDigest/blob/91440fa672f3708b8f34d719add520e8491cc48d/extension/triage/triage-bg.js)、[快照同步](https://github.com/PathGao/MoonDigest/blob/91440fa672f3708b8f34d719add520e8491cc48d/extension/agent-sync.js)、[串行视频读取](https://github.com/PathGao/MoonDigest/blob/91440fa672f3708b8f34d719add520e8491cc48d/extension/agent-video.js)和[缓存差分逻辑](https://github.com/PathGao/MoonDigest/blob/91440fa672f3708b8f34d719add520e8491cc48d/extension/triage/triage-core.js)。本地 Python 入口独立实现工作流，不要求安装源项目扩展或 MCP；这些 B站 Web 接口并无稳定性承诺。
