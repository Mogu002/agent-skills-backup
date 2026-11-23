---
name: connect-coconut-to-codex
description: 在 macOS 或 Linux 上把本机 Coconut 的 OpenAI Responses 反代接入 Codex Desktop/CLI，同时保留 ChatGPT 登录和原生模型，或同步、修复 Coconut 模型目录与公开命名时使用。NOT for 仅使用已经接入的模型、开发 Coconut 服务本身、通用 MCP/API 接入或替换全部 Codex Provider。
---

# Connect Coconut to Codex

目标是让原生 Codex 模型和 Coconut 模型出现在同一个 picker 中。Codex 继续使用内置 `openai` Provider；Codex Router 只接管本地 base URL、合并目录并按模型 slug 分流。

## 默认策略

- 已安装 Router：复用现有稳定 checkout、Provider 和后台服务，只同步模型与修复状态。
- 未安装 Router：先做只读预检，取得写用户配置和安装服务的授权后，再从审阅过的稳定 checkout 安装。
- Coconut 地址或启动方式不明确：定位其配置、日志或监听端口；仍不唯一时询问用户，不猜端口或启动命令。
- 默认不执行 billed/live 推理；只有用户明确同意消耗额度后才运行 `test-model --live --yes`。
- 完成后让用户完全退出并重开 Codex；不要替用户终止 Codex 进程。

## 不变量

- 不设置全局 `model_provider = "coconut"`，不覆盖 Codex 登录或原生模型配置。
- Coconut 上游模型 ID 保存在 `upstreamModel`；公开 slug 使用 `coconut/<去掉一次 coconut- 前缀的 ID>`。
- 不从聊天、命令参数、日志或仓库读取/输出 token。需要凭据时使用 Router 的隐藏本地提示。
- 遇到未知 Router、已有但无托管标记的 `openai_base_url` / `model_catalog_json`、端口占用或无法验证的配置所有权时停止，不强行接管。
- 写入前取得所需用户级目录权限；只修改 Router 托管块和 Router 自有状态。

## 工作流

### 1. 只读预检

确认 Codex、Git、Node.js 22.19+，以及 `uv` 或 Python 3.10+。检查 Router 是否已安装在当前机器的稳定 checkout；若存在，先读取该 checkout 的 `AGENTS.md` 和命令帮助。

确认 Coconut 提供 OpenAI Responses 接口和模型目录。不要把完整响应或潜在凭据输出到聊天；只检查 HTTP 状态、模型 ID、上下文窗口和推理档位。Coconut 的模型目录可能要求 Codex 风格 User-Agent：从 Router checkout 的 `package.json` 读取当前版本，并用 `User-Agent: codex-router/<version>` 探测 `${COCONUT_BASE_URL}/models`。

如果无 User-Agent 返回 400、带该 User-Agent 返回 200，这是可兼容状态；注册 Provider 时固定同一个非敏感请求头。

### 2. 安装或复用 Codex Router

新安装必须使用稳定 checkout，不从临时目录运行服务，也不执行未经审阅的 `curl | sh`。macOS/Linux 的默认稳定位置为 `~/.local/share/codex-router`。读取仓库安装说明后，使用无 smoke test、无托盘的最小安装，例如：

```sh
./install.sh --target codex --auto --providers custom --no-tray
```

安装器应保留现有设置和 ChatGPT 登录。安装输出若暴露了用户未要求的自定义模型或图像桥接，只关闭/隐藏相关 Router 功能；不要删除用户项目或凭据。

### 3. 注册 Coconut

先检查 `coconut` 通用 Provider 是否已经存在。存在时复用或精确编辑，避免重复添加；不存在时注册：

```sh
./bin/model-router codex providers generic add coconut \
  --name Coconut \
  --base-url "${COCONUT_BASE_URL}" \
  --adapter openai-responses \
  --allow-private \
  --header "User-Agent=codex-router/<version>"
```

随后运行只读连通性检查：

```sh
./bin/model-router codex providers generic test coconut --json
```

只有 Coconut 实际要求 Bearer 时才用 Router 的 `providers generic credential coconut set` 隐藏提示；不要为了满足字段而伪造或在聊天中传递密钥。

### 4. 发布模型

从实时 `/models` 目录选择用户要求的模型。按相同的 `supported_reasoning_levels` 分组调用 curation，保持每个模型真实的推理档位和目录提供的上下文窗口：

```sh
./bin/curate-models coconut --models id1,id2 --efforts low,medium,high --apply
```

不要把一个模型的 `xhigh`、`max`、图片或工具能力推断给其他模型。增量同步时保留已有手工元数据，只添加或显式移除目标模型。

### 5. 规范公开名称

Router curation 默认会生成 `coconut/coconut-*`。解析本 Skill 目录下的脚本路径，先预览，再在用户已授权改名时执行：

```sh
node scripts/normalize-coconut-slugs.mjs
node scripts/normalize-coconut-slugs.mjs --apply
```

脚本只处理 `provider: "coconut"` 且 `upstreamModel` 以 `coconut-` 开头的用户模型。它保留上游 ID，迁移当前默认模型、picker 可见性和公告状态，写前生成逐文件备份。若预览包含非 Coconut 文件或意外模型，停止。

改名后按当前安装方式重新运行 Router 安装/发布命令，以重建 merged catalog 和 gateway routes；不要手工编辑生成的 `merged-models.json` 或 `litellm.yaml`。

### 6. 验证

必须运行：

```sh
./bin/model-router codex doctor
node scripts/normalize-coconut-slugs.mjs --check
```

回读 merged catalog，确认：

- 原生 GPT 模型仍在；
- Coconut 条目数量与所选模型一致；
- 没有 `coconut/coconut-*`；
- 每条公开 slug 能映射到原始 `upstreamModel`；
- 当前默认模型若是 Coconut，已迁移到新 slug；
- Router 后台服务健康。

只有用户授权额度后，先选一个代表模型运行低成本普通回复测试；需要工具能力时再运行完整兼容测试：

```sh
./bin/test-model coconut/<model> --live --yes --quick --effort=medium
./bin/test-model coconut/<model> --live --yes --effort=medium
```

成功后通知用户完全退出并重开 Codex，新建任务检查 picker。未逐个实测的模型必须明确说明。

## 恢复

命名脚本会为每个被写文件创建 `backup-coconut-slugs-*` 备份；验证失败时停止服务发布并从对应备份恢复，再运行安装器和 doctor。完整卸载使用 checkout 文档规定的 `./bin/model-router codex uninstall`，不要手工删除 Codex 配置片段、LaunchAgent 或凭据目录。
