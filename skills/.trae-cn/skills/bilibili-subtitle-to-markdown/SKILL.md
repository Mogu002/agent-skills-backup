---
name: bilibili-subtitle-to-markdown
description: 当用户提供 B站/Bilibili 视频 URL 或 BV 号，要求抓取或导出原生字幕、AI 字幕、带时间戳逐字稿、整理成本地 Markdown，或需要先取得视频文本再总结时使用。优先走 B站字幕接口，必要时利用已登录浏览器捕获播放器的原生字幕网络响应；不读取 vCaptions、不导出 Cookie、不下载音视频、不运行 ASR。NOT for 没有原生字幕时进行语音转写、只总结用户已提供的文本、其他视频平台，或明确要求操作 vCaptions 面板。
compatibility: Python 3.9+；联网；浏览器控制能力仅作为可选回退。
metadata:
  version: 0.2.0
---

# Bilibili Subtitle to Markdown

把一个 B站视频的原生字幕轨整理为带时间戳的 Markdown。抓取准确性指忠实保存 B站返回的字幕；不要把 AI 字幕描述为人工校对稿。

## 默认策略

1. 从 URL 或 BV 号确定视频；URL 有 `p=` 时选择对应分P，否则用 P1。
2. 从当前读取的 `SKILL.md` 绝对路径解析同目录下的 `scripts/extract.py`；不要假设环境存在 `$SKILL_DIR`。先运行匿名快路径：

   ```bash
   python3 "<skill目录>/scripts/extract.py" "$SOURCE" -o "$OUTPUT"
   ```

3. 按结果执行且不要临时改写脚本或手工调用 B站字幕接口：

   | 结果 | 动作 |
   |---|---|
   | `ok: true` | 按“验证”回读结果 |
   | `status: browser_required` 且有浏览器控制工具 | 执行“浏览器回退” |
   | `status: browser_required` 且没有浏览器控制工具 | 停止并说明当前环境缺少回退能力 |
   | 其他错误 | 报告错误；不要复制、打印或手工解密字幕 URL |
4. 默认优先 `ai-zh`；不存在时依次选择中文原生轨和第一条原生字幕轨。用户指定语言时传 `--language LANG`。
5. 没有任何原生字幕轨时停止并说明；不得擅自下载媒体或启动 ASR。
6. 输出文件已存在时默认停止；只有用户明确允许覆盖后才传 `--overwrite`。

输出路径由当前任务的产物目录规则决定，不要写进 Skill 目录。

## 跨沙箱交付

目标目录因沙箱或系统权限不可写时：

1. 在当前 Agent 明确可写的工作目录生成一个本次任务专用的暂存文件。
2. 抓取完成且结构化验证全部通过后，再用当前平台允许的文件操作把它复制到目标路径。
3. 目标文件已存在时不得静默覆盖；改用新文件名，或取得用户明确许可。
4. 分别计算暂存文件与目标文件的 SHA-256；只有哈希一致才算交付成功。
5. 哈希一致后删除仅为本次交付创建的暂存副本；不得删除用户原有文件。
6. 报告目标文件的实际字节数，不要估算大小。

## 浏览器回退

仅当匿名接口没有返回字幕轨时执行：

1. 按当前环境的浏览器控制 Skill 连接用户已有浏览器。用户没有指定浏览器时，优先能访问其现有 B站登录态的浏览器。
   如果当前工具集中没有浏览器控制或网络响应读取能力，立即停止；不得用临时 Python/curl 请求、禁用 TLS、复制混淆 URL 或修改本 Skill 代替浏览器回退。
2. 打开视频临时标签页；页面无需事先打开。不得读取或导出 Cookie、Local Storage、密码或浏览器配置。
3. 观察 B站播放器自己的网络资源，不读取 vCaptions 或其他扩展的 DOM。优先捕获：

   - 最终字幕 JSON：主机通常为 `aisubtitle.hdslb.com`；保存响应体到临时文件后运行：

     ```bash
     python3 "<skill目录>/scripts/extract.py" "$SOURCE" --subtitle-json "$TEMP_JSON" -o "$OUTPUT"
     ```

   - 若只有 `/x/v2/subtitle/web/view` 响应，保存其二进制响应体后运行：

     ```bash
     python3 "<skill目录>/scripts/extract.py" "$SOURCE" --metadata-file "$TEMP_PROTOBUF" -o "$OUTPUT"
     ```

4. 浏览器若只暴露元数据请求 URL，可用浏览器自身的响应读取能力取得响应体；不要把动态 URL、签名参数或字幕下载 URL写进命令、产物、对话或 trace。
5. 页面显示未登录或接口仍拒绝时，请用户在该浏览器登录后重试。不要切换到 Cookie 导出方案。
6. 完成后关闭临时标签页并删除临时响应文件。

播放器已经请求最终字幕 JSON 时优先使用它；本地解析 Protobuf 和混淆字幕地址只是回退，以降低 B站前端改版风险。

## 验证

只有同时满足以下条件才算完成：

- 脚本报告 `ok: true`、`subtitle_count > 0`、`count_matches: true`、`timeline_valid: true`、`secret_markers: false` 和 `media_downloaded: false`。
- 记录 `skill_version`、`acquisition_path`、`metadata_attempts`、`duration_delta` 和 `output_sha256`；不要输出底层字幕 URL。
- Markdown frontmatter 包含 `bvid`、`cid`、语言、字幕来源和条数。
- 每行字幕包含起止时间，时间非递减且 `to >= from`。
- 最后一条时间与视频时长没有明显矛盾；脚本给出警告时向用户说明。
- 输出目录没有新建 `.mp4`、`.m4s`、`.mp3`、`.wav`、`.mkv` 或 `.webm`。
- 产物不包含 Cookie、`SESSDATA`、`auth_key` 或完整签名 URL。

仅在安装、更新或兼容性排查时运行离线自检，不要为每个视频重复执行：

```bash
python3 "<skill目录>/scripts/extract.py" --self-check
```

## 停止与边界

- 视频不存在、无权访问或无原生字幕：停止，报告可观察到的原因。
- 签名 URL 返回 403：重新获取一次字幕元数据；仍失败则停止，不循环重试。
- Protobuf 字段或字幕地址混淆格式未知：优先捕获播放器最终 JSON；仍不可得则报告 B站接口兼容性变化。
- 用户明确要抓 vCaptions 面板、转写无字幕视频或处理其他平台时，不使用本 Skill。

## 证据与兼容性

流程来自真实端到端抓取、B站现行播放器接口响应，以及开源项目 `ccBilly-aipm/bilibili-ai-subtitle` 的 MIT 许可 Protobuf 字段映射。B站接口未公开承诺稳定；旧 JSON、当前 Protobuf和播放器最终响应组成有序回退，而不是长期固定的官方版本契约。
