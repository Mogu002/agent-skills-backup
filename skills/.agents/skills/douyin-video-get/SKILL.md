---
name: douyin-video-get
description: 下载抖音/Douyin 视频文件到本地。当用户给出抖音视频链接、分享短链或视频 ID，要求下载、保存、获取视频原文件，或为后续转写/剪辑/归档取得本地 mp4 时使用。通过本机 ego-browser 的真实登录会话抓取媒体流，不依赖第三方解析接口或请求签名算法，抗抖音风控升级。NOT for B 站及其他平台视频、抖音直播流、仅做字幕转写（转写用 douyin-video-transcript）、或用户已提供本地文件。
---

# Douyin Video Get

用本机 **ego-browser** 的真实登录会话打开视频页，让浏览器自己算请求签名，从网络里抓取
正在播放的媒体流并下载合并为单个 mp4。这是目前最抗抖音风控的取流方式。

## 何时用这个方法

抖音视频真实地址必须经过动态签名 `a_bogus` 才能从 Web 接口取得，f2 / yt-dlp 等工具自带
的签名实现会随抖音升级而失效（表现为 `aweme/detail` 持续 403）。本方法不自己算签名——签名由
用户真实浏览器生成，只要网页版能正常播放该视频，就能取到流，因此默认优先于解析类工具。

- 需要**最高画质**（浏览器通常给到 4K/HEVC 分离流）或**稳定可复用**→ 用本方法。
- 只是想要字幕/逐字稿 → 用 `douyin-video-transcript`（它内部下载失败时，可先用本方法取得
  mp4，再把本地文件交给它转写）。

## 默认流程

一条命令完成取流、下载、合并：

```bash
bash "<skill目录>/scripts/get-douyin.sh" "<抖音链接或视频ID>" "<输出目录>"
```

成功时脚本在最后一行打印 `OUTPUT=<mp4绝对路径>`。脚本做了什么：

1. 把分享短链或纯数字 ID 规范化为 `https://www.douyin.com/video/<id>`。
2. 用 ego-browser 打开页面并触发播放，从 Resource Timing 抓取 `douyinvod.com` 的
   DASH 流（优先按 `bt=` 比特率取最高的视频轨 + 音频轨；没有分离流时回退到单段 mp4）。
3. 通过页面同会话 `page.fetch` 下载各流（带正确 Referer/Cookie）。
4. 用 ffmpeg `-c copy` 把视频轨和音频轨无损合并为 `<video_id>.mp4`。

## 前置条件与边界

- **仅 macOS/本机，需已安装并登录 ego-browser**；首次用请先在 ego-browser 里登录抖音。
- 需要 `ffmpeg` 和 `python3`（标准库即可）。缺失时脚本以退出码 3 报错。
- ego-browser 的 Node 运行时**不继承 shell 环境变量**，所以输入由 wrapper 以 JSON 注入脚本，
  不要改成用 env 传参。
- 页面跳到登录/验证页时脚本返回 `login_or_verify_required` 并保留页面（`keep:["p1"]`），
  让用户在浏览器里完成登录后重试；**不要尝试绕过验证码或登录墙**。
- 抓不到流（`no_stream_captured`）通常是播放未真正开始：可重试一次；仍失败则该视频可能有
  特殊保护，停止并说明，不要伪造结果。

## 完成验证

- 存在非空 `OUTPUT` mp4；用 `ffprobe` 确认同时有 video 与 audio 流且时长 > 0。
- 需要字幕时，把该 mp4 交给 `douyin-video-transcript` 做转写，不要用本 skill 产出字幕。

## 退出码

`0` 成功 ｜ `2` 参数错误 ｜ `3` 缺依赖 ｜ `4` 抓流失败 ｜ `5` 合并失败。

## 合规

仅用于用户自身可访问、已授权的内容与个人合规用途。下载受版权或平台条款限制的内容前，由用户
负责确认授权；涉及登录态的操作只在用户明确许可下进行。
