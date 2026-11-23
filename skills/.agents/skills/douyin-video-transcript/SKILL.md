---
name: douyin-video-transcript
description: 当用户提供抖音/Douyin 视频 URL、视频 ID 或本地音视频，要求在 macOS 本地生成带分段时间戳的 SRT、TXT、JSON 或 Markdown 字幕时使用；默认先判断视频是否含持续变化的画面烧录字幕，命中后使用 Apple Vision OCR，否则使用 sherpa-onnx INT8 Paraformer 音频转写。NOT for B站原生字幕、只检查抖音是否提供原生字幕文件、云端 ASR、实时直播字幕、Windows/Linux，或用户已提供文本而只需总结。
compatibility: macOS 13+；Bash、Python 3.10+、Xcode Command Line Tools、网络和约 1 GB 可用磁盘。Apple Vision 路径不支持 Windows/Linux。
metadata:
  version: 1.0.0
---

# Douyin Video Transcript

把抖音 URL、视频 ID 或本地音视频转换为可回读的 `SRT + TXT + JSON + Markdown`。默认只在本地处理：视频有可用烧录字幕时读取画面；否则转写音轨。

## 默认流程

1. 从 `SKILL.md` 的绝对路径解析同目录 `scripts/`，不要假设存在 `$SKILL_DIR`。
2. 先检查环境：

   ```bash
   bash "<skill目录>/scripts/bootstrap.sh" --check
   ```

3. 检查失败且用户要求执行转录时安装；只读诊断不得自动安装：

   ```bash
   bash "<skill目录>/scripts/bootstrap.sh" --install
   ```

   安装内容为 FFmpeg/FFprobe、隔离 Python 环境、固定版本 `yt-dlp`、`sherpa-onnx`、INT8 Paraformer、Silero VAD，并把本 Skill 的 Apple Vision Swift 程序编译到隔离前缀；全部置于隔离前缀，不改写系统 Python。

4. 默认执行自动分流：

   ```bash
   bash "<skill目录>/scripts/transcribe.sh" "$SOURCE" \
     --output-dir "$OUTPUT_DIR" \
     --title "$TITLE"
   ```

5. 输出存在时默认停止；只有用户明确允许覆盖才传 `--overwrite`。脚本只覆盖已知产物，不删除目录内其他文件。
6. 完成后回读 `decision.json`、验证器摘要和 `transcript.md`。机器结果必须标注为自动识别，不能描述为人工校对稿。

## 自动分流规则

`--engine auto` 是默认值，并由脚本强制执行：

1. 音频源或没有视频流：直接走 Paraformer。
2. 视频源：从底部 35% 区域均匀抽样约 48 帧，先运行 Apple Vision OCR 探测。
3. 长视频只有同时满足以下条件才走全量 Vision：有效文字帧达到最低覆盖率（默认 15%）、至少出现 3 种规范化文本、固定单一文本没有主导结果。短视频按时长降低最小变化数。
4. 全量 Vision 结果仍需通过字幕数量与覆盖率质量门槛；探测失败、OCR 失败或结果过稀时，`auto` 自动降级 Paraformer 并记录原因。
5. 固定水印、片头标题或零星贴纸不应单独触发 Vision。成功完成 OCR 抽样时，`decision.json` 必须记录路由、原因、样本数、文字覆盖率和唯一文本数；没有视频流、探测执行失败或显式覆盖时只记录可获得的字段。

这是启发式判断，不是烧录字幕的数学证明。已知字幕位置不在底部时，用 `--crop-ratio` 扩大区域；自动判断错误时用 `--engine vision` 或 `--engine paraformer` 显式覆盖。

## 输入与平台路径

### 抖音 URL 或视频 ID

脚本接受抖音 URL 和 15–25 位纯数字 ID；纯 ID 或带 `modal_id` 的精选页链接会规范化为 `https://www.douyin.com/video/<ID>`，再由隔离安装的 `yt-dlp` 下载视频。烧录字幕是视频像素，因此不能只下载音频。

匿名下载失败且抖音要求新鲜 Cookie 时：

1. 不读取、打印、导出或保存 Cookie。
2. 只有用户明确允许使用某个已登录浏览器时才增加 `--cookies-from-browser chrome`；也可使用 `yt-dlp` 支持的其他浏览器名。
3. 页面要求登录、验证码或权限确认时停止，让用户在浏览器完成；不得绕过。

### 本地文件

视频会先做 OCR 探测；本地纯音频直接走 Paraformer。用户源文件只读，下载媒体、抽帧和临时 WAV 位于 `mktemp` 目录并在退出时清理。

## 两条执行路径

### Apple Vision OCR

- 仅适用于 macOS 和画面中真实存在的烧录字幕。
- 默认以 2 fps 读取视频底部 35%，用 `VNRecognizeTextRequest` 的准确模式识别简体/繁体中文，再合并相邻近似文本。
- 2 fps 可能漏掉持续不足 0.5 秒的字幕；字幕不在默认区域时调整 `--crop-ratio`。

### sherpa-onnx + INT8 Paraformer

- FFmpeg 先生成 `16 kHz / mono / PCM s16le WAV`。
- Silero VAD 提供语音段起止时间；Paraformer 模型本身不提供词级时间戳。
- 适合普通话及部分中文方言，并支持夹杂英文；背景音乐、口音和专名仍可能造成错字。
- 默认 4 个推理线程，可用 `--threads` 调整。

## 输出契约

`OUTPUT_DIR` 成功后包含：

- `decision.json`：自动判断或显式覆盖的路由与原因；
- `transcript.srt`：分段时间轴；
- `transcript.txt`：纯文本；
- `transcript.json`：引擎、来源、时长、覆盖率和结构化分段；
- `transcript.md`：元数据、自动识别声明和带时间戳全文；
- `normalized.wav`：仅传 `--keep-audio` 且最终走 Paraformer 时生成。

中间文件先在临时目录生成并验证，通过后才复制到目标目录，避免失败时留下看似完整的半成品。

## 完成验证

只有同时满足以下条件才算完成：

- 五个默认产物存在且非空；
- JSON、SRT 和 Markdown 的字幕条数一致且至少一条；
- 时间非递减、`end >= start`，末条不超过媒体真实时长；
- `decision.json` 的路由与 `transcript.json` 引擎一致；
- Markdown 包含来源、引擎、字幕条数和自动识别声明；验证器输出该文件的 SHA-256 摘要；
- 连续相同文本达到 5 段且跨度达到 10 秒时验证失败，防止重复幻觉或合并链路异常；
- 产物不包含 Cookie、鉴权头、浏览器 profile 或临时签名查询串。

安装、修改或兼容性排查后运行：

```bash
python3 "<skill目录>/scripts/transcript_pipeline.py" self-check
bash "<skill目录>/scripts/transcribe.sh" ./example.mp4 --output-dir ./out --dry-run
```

## 停止与恢复

- 非 macOS：停止。
- 缺少 Homebrew：停止并给出官方安装提示；脚本不执行远程 Homebrew 引导命令。
- 缺少 `swiftc`：提示运行 `xcode-select --install` 后重试。
- 下载需要未授权登录、DRM、验证码或付费权限：停止，不绕过。
- Vision 与 Paraformer 都没有产生有效字幕：保留错误信息，不创建目标产物；由用户决定调整裁剪区域、强制引擎或改用其他路径。
- 任务是 B站字幕时改用 `bilibili-subtitle-to-markdown` Skill；只调查抖音原生字幕接口时不要下载媒体或启动本流程。

## 版本与供应链

固定版本为 `sherpa-onnx 1.13.5`、`numpy 2.3.3`、`yt-dlp 2026.8.19`，并使用官方 `sherpa-onnx-paraformer-zh-small-2024-03-09` INT8 模型和 `silero_vad.onnx`。模型仅从 `k2-fsa/sherpa-onnx` 官方 GitHub Release 下载并校验 SHA-256；Python 包仅从官方 PyPI HTTPS 源安装。抖音页面与下载策略没有稳定公开契约，兼容性失败时先在隔离环境验证新版 `yt-dlp`，通过回归后再更新固定版本。
