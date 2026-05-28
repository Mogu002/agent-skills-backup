---
name: openclaw-install-assistant
description: 为无代码用户以无交互方式安装、升级或修复 OpenClaw。升级默认优先走更快更稳的 `openclaw update` 快路径；仅在首次安装、关键引导缺失或修复场景下才运行 installer / onboard。默认把 Friday 配置为首选模型，并以最小补丁方式把 `openclaw.json` 对齐到参考模板：优先保留已有 `meta`、`wizard`、`auth`、`agents.defaults.workspace`、`gateway.auth.token`、sessions 及其他非模板字段，仅在缺失时补齐；Friday provider 默认写入公用 APPID/API Key `2003426817264898139`。
---

# OpenClaw 安装技能

## 默认原则

- 参考 `openclaw.json` 是唯一模板；字段层级、字段名、模型 ID 大小写、默认 alias、顶层结构都必须和模板保持一致。
- 默认首选模型是 `friday/MiniMax-M2.7`。
- 默认只确保模板中的 `friday` provider 存在；不主动删除用户已有 provider，也不默认新增 `longCat`、`minimax-cn`、`hooks` 等模板之外字段。
- 默认保留已有 `meta`、`wizard`、`auth`、`agents.defaults.workspace`、`gateway.auth.token`、sessions，以及其他非模板字段；仅在缺失时补齐模板必需字段。
- 升级优先走 `openclaw update`；只有首次安装、CLI 不存在、关键引导缺失，或升级失败时，才回退到 installer / 包管理器。
- 只有首次安装、关键引导缺失，或用户明确要求重新初始化时，才运行 `openclaw onboard`。
- 除 `repair` 外，不要默认执行 `openclaw gateway install --force`。
- 除用户明确要求外，不要运行交互式 `openclaw onboard`。
- 不要为了拿 Dashboard URL 去启动一个可能常驻的 `openclaw dashboard` 前台进程；优先根据 `gateway.bind` 和 `gateway.port` 直接计算 URL。
- 若 `gateway status` 提示服务使用 version manager（如 `nvm`、`fnm`、`asdf`）里的 Node，优先改用官方 `install-cli.sh` 在 `~/.openclaw` 下安装本地前缀运行时，再重装 gateway service，让 LaunchAgent / systemd 指向 `~/.openclaw/tools/node...` 与 `~/.openclaw/lib/node_modules/openclaw/...`。
- 若 `doctor --fix` 因 bundled plugin runtime deps 失败，先批量确认缺失包里是否有 npm 上不存在的版本；若是发布包 manifest 版本漂移，先把对应 `dist/extensions/*/package.json` 中不存在的版本改为 npm 上存在的最近兼容版本，再重跑 `scripts/postinstall-bundled-plugins.mjs`。

## 分流

- `install`：`openclaw` 尚未安装，或用户明确要求首次安装。
- `upgrade`：`openclaw` 已安装，且用户未明确要求 `repair` / `migration`。
- `repair`：CLI 已安装，但 gateway、dashboard 或 config 异常。
- `migration`：用户明确提到 `clawdbot`、`moltbot` 或旧机器迁移。

## 预检

```bash
uname -s
if grep -qiE "(microsoft|wsl)" /proc/version 2>/dev/null; then echo "WSL"; fi
command -v openclaw >/dev/null && openclaw --version || echo "openclaw: not installed"
node -v 2>/dev/null || echo "node: not installed"
node -e 'const v=(process.versions.node||"0.0.0").split(".").map(Number); process.exit(v[0] > 22 || (v[0] === 22 && v[1] >= 14) ? 0 : 1)' >/dev/null 2>&1 && echo "node: ok" || echo "node: missing-or-too-old"
CONFIG_FILE_RAW="$(openclaw config file 2>/dev/null || echo "${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw/openclaw.json}")"
CONFIG_FILE="${CONFIG_FILE_RAW/#\~/$HOME}"
echo "$CONFIG_FILE"
openclaw config validate >/dev/null 2>&1 && echo "config: ok" || echo "config: needs-attention"
openclaw gateway status --require-rpc >/dev/null 2>&1 && echo "gateway: ok" || echo "gateway: needs-attention"
```

规则：

- 原生 Windows PowerShell：优先建议 WSL2；若仍需 PowerShell，再用官方 PowerShell 安装命令。
- Node 最低要求 `22.14+`，推荐 `24`。
- 若输出 `node: missing-or-too-old`，优先让官方安装脚本自动处理 Node；只有用户明确要求手动装 Node 时，才改用 `brew install node`、NodeSource `24.x` 或 `fnm install 24`。

## upgrade

### 1) 默认升级快路径

已安装 OpenClaw 时，默认先走官方 update，而不是重新跑 installer：

```bash
openclaw update | cat
```

补充规则：

- `openclaw update` 是默认升级入口；它比重新跑 installer 更快，也更贴近官方推荐升级路径。
- 若用户只想预览本次升级，可改用 `openclaw update --dry-run | cat`。
- 若 `openclaw update` 失败，再回退到 installer 或用户指定的包管理器方式。
- 若用户明确要求切换 channel 或 tag，再追加 `--channel beta`、`--tag main` 等参数。

### 2) 回退安装方式

只有在 `openclaw` 未安装、`openclaw update` 不可用/失败，或用户明确要求时，才使用以下方式。

若目标是“让 gateway service 不依赖 nvm/fnm/asdf 路径”，优先使用官方 local-prefix 安装器，因为它会把 OpenClaw 与 Node 一起放到 `~/.openclaw` 下，更适合受管服务：

```bash
curl --retry 3 --retry-delay 2 --connect-timeout 10 -fsSL --proto '=https' --tlsv1.2 https://openclaw.ai/install-cli.sh | bash -s -- --json --prefix "$HOME/.openclaw" --version 2026.4.1
```

执行后，优先使用 `~/.openclaw/bin/openclaw` 或 `~/.openclaw/tools/node/bin/node` 对应的本地前缀安装，并重装 gateway service。

macOS / Linux / WSL2：

```bash
curl --retry 3 --retry-delay 2 --connect-timeout 10 -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard
```

Windows PowerShell：

```powershell
& ([scriptblock]::Create((iwr -useb https://openclaw.ai/install.ps1))) -NoOnboard
```

只有用户明确要求包管理器安装时，才改用：

```bash
npm install -g openclaw@latest
# or
pnpm add -g openclaw@latest
```

如果 `pnpm` 首次安装后需要批准构建脚本，再执行：

```bash
pnpm approve-builds -g
```

如果 `npm install -g` 因 `sharp` / `libvips` 失败，可兜底：

```bash
SHARP_IGNORE_GLOBAL_LIBVIPS=1 npm install -g openclaw@latest
```

### 3) 准备配置和保留字段

```bash
CONFIG_FILE_RAW="$(openclaw config file 2>/dev/null || echo "${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw/openclaw.json}")"
CONFIG_FILE="${CONFIG_FILE_RAW/#\~/$HOME}"
mkdir -p "$(dirname "$CONFIG_FILE")"
[ -f "$CONFIG_FILE" ] || printf '{}\n' > "$CONFIG_FILE"

EXISTING_GATEWAY_TOKEN="$(jq -r '.gateway.auth.token // empty' "$CONFIG_FILE" 2>/dev/null || true)"
EXISTING_GATEWAY_PORT="$(jq -r '.gateway.port // empty' "$CONFIG_FILE" 2>/dev/null || true)"
EXISTING_GATEWAY_BIND="$(jq -r '.gateway.bind // empty' "$CONFIG_FILE" 2>/dev/null || true)"
EXISTING_WORKSPACE="$(jq -r '.agents.defaults.workspace // empty' "$CONFIG_FILE" 2>/dev/null || true)"
EXISTING_FRIDAY_KEY="$(jq -r '.models.providers.friday.apiKey // empty' "$CONFIG_FILE" 2>/dev/null || true)"

GATEWAY_TOKEN="${EXISTING_GATEWAY_TOKEN:-$(openssl rand -hex 24)}"
GATEWAY_PORT="${EXISTING_GATEWAY_PORT:-18789}"
GATEWAY_BIND="${EXISTING_GATEWAY_BIND:-loopback}"
DEFAULT_WORKSPACE="${EXISTING_WORKSPACE:-$HOME/.openclaw/workspace}"
FRIDAY_KEY="${FRIDAY_KEY:-${EXISTING_FRIDAY_KEY:-2003426817264898139}}"
```

规则：

- `FRIDAY_KEY` 默认使用公用 APPID/API Key `2003426817264898139`；若配置里已有 `friday` key，则继续保留。
- 不要把 `workspace` 写成 `$(pwd)`。
- 不要每次都生成新 token；只有现有配置没有 token 时才生成。
- `gateway.port`、`gateway.bind`、`agents.defaults.workspace` 若已有值，优先保留原值；若缺失，再回退到模板默认值。

### 4) 仅在关键引导缺失时运行非交互 onboard

升级时不要默认每次都跑 onboarding。先判断关键引导字段是否缺失：

```bash
NEEDS_ONBOARD=0
jq -e '
  .models.providers.friday
  and .gateway.auth.token
  and .agents.defaults.workspace
  and .agents.defaults.model.primary
' "$CONFIG_FILE" >/dev/null 2>&1 || NEEDS_ONBOARD=1

if [ "$NEEDS_ONBOARD" -eq 1 ]; then
  openclaw onboard --non-interactive \
    --mode local \
    --auth-choice custom-api-key \
    --custom-base-url "https://aigc.sankuai.com/v1/openai/native" \
    --custom-model-id "MiniMax-M2.7" \
    --custom-api-key "$FRIDAY_KEY" \
    --custom-provider-id "friday" \
    --custom-compatibility openai \
    --secret-input-mode plaintext \
    --gateway-auth token \
    --gateway-token "$GATEWAY_TOKEN" \
    --gateway-port "$GATEWAY_PORT" \
    --gateway-bind "$GATEWAY_BIND" \
    --install-daemon \
    --accept-risk \
    --skip-skills
fi
```

规则：

- 首次安装时，`NEEDS_ONBOARD` 基本会是 `1`。
- 健康升级时，优先跳过 onboarding，避免重复初始化、减少耗时，并降低配置被二次覆盖的风险。
- 用户明确要求“重新初始化”时，可以无视 `NEEDS_ONBOARD` 直接执行该段。

### 5) 用最小补丁方式把配置对齐到参考模板

不要用 `jq -n` 全量重写整个 `openclaw.json`。应基于现有文件做最小补丁，仅确保模板关键字段存在且值正确，同时保留其他字段。

```bash
jq \
  --arg fk "$FRIDAY_KEY" \
  --arg gt "$GATEWAY_TOKEN" \
  --arg gp "$GATEWAY_PORT" \
  --arg gb "$GATEWAY_BIND" \
  --arg w "$DEFAULT_WORKSPACE" '
  .meta = (.meta // {}) |
  .wizard = (.wizard // {}) |
  .auth = (.auth // {}) |
  .auth.profiles = (.auth.profiles // {}) |
  .auth.profiles["anthropic:default"] = (.auth.profiles["anthropic:default"] // {
    "provider": "anthropic",
    "mode": "api_key"
  }) |
  .models = (.models // {}) |
  .models.mode = "merge" |
  .models.providers = (.models.providers // {}) |
  .models.providers.friday = {
    "baseUrl": "https://aigc.sankuai.com/v1/openai/native",
    "apiKey": $fk,
    "api": "openai-completions",
    "authHeader": true,
    "models": [
      {
        "id": "glm-5-turbo",
        "name": "glm-5-turbo",
        "reasoning": false,
        "input": ["text"],
        "contextWindow": 200000,
        "maxTokens": 8192,
        "compat": {
          "maxTokensField": "max_tokens"
        }
      },
      {
        "id": "MiniMax-M2.7",
        "name": "MiniMax-M2.7",
        "reasoning": false,
        "input": ["text"],
        "contextWindow": 200000,
        "maxTokens": 8192,
        "compat": {
          "maxTokensField": "max_tokens"
        }
      }
    ]
  } |
  .agents = (.agents // {}) |
  .agents.defaults = (.agents.defaults // {}) |
  .agents.defaults.model = (.agents.defaults.model // {}) |
  .agents.defaults.model.primary = "friday/MiniMax-M2.7" |
  .agents.defaults.models = (.agents.defaults.models // {}) |
  .agents.defaults.models["minimax/MiniMax-M2.5"] = {"alias": "Minimax"} |
  .agents.defaults.models["friday/MiniMax-M2.7"] = {"alias": "MiniMax"} |
  .agents.defaults.models["friday/glm-5-turbo"] = {"alias": "GLM"} |
  .agents.defaults.workspace = $w |
  .agents.defaults.contextPruning = (.agents.defaults.contextPruning // {
    "mode": "cache-ttl",
    "ttl": "1h"
  }) |
  .agents.defaults.compaction = (.agents.defaults.compaction // {
    "mode": "safeguard"
  }) |
  .agents.defaults.heartbeat = (.agents.defaults.heartbeat // {
    "every": "30m"
  }) |
  .agents.defaults.maxConcurrent = (.agents.defaults.maxConcurrent // 4) |
  .agents.defaults.subagents = (.agents.defaults.subagents // {
    "maxConcurrent": 8
  }) |
  .agents.list = (.agents.list // [{"id": "main"}]) |
  .messages = (.messages // {}) |
  .messages.ackReactionScope = "group-mentions" |
  .commands = (.commands // {}) |
  .commands.native = (.commands.native // "auto") |
  .commands.nativeSkills = (.commands.nativeSkills // "auto") |
  .commands.restart = (.commands.restart // true) |
  .commands.ownerDisplay = "raw" |
  .gateway = (.gateway // {}) |
  .gateway.port = (($gp | tonumber) // 18789) |
  .gateway.mode = "local" |
  .gateway.bind = $gb |
  .gateway.auth = (.gateway.auth // {}) |
  .gateway.auth.mode = "token" |
  .gateway.auth.token = $gt |
  .gateway.tailscale = (.gateway.tailscale // {
    "mode": "off",
    "resetOnExit": false
  }) |
  .skills = (.skills // {}) |
  .skills.install = (.skills.install // {}) |
  .skills.install.nodeManager = "npm" |
  . as $root |
  {
    "meta": $root.meta,
    "wizard": $root.wizard,
    "auth": $root.auth,
    "models": $root.models,
    "agents": $root.agents,
    "messages": $root.messages,
    "commands": $root.commands,
    "gateway": $root.gateway,
    "skills": $root.skills
  } + ($root | del(.meta, .wizard, .auth, .models, .agents, .messages, .commands, .gateway, .skills))
' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"

mkdir -p "$DEFAULT_WORKSPACE"
```

### 6) 严格格式要求

如果本次目标是“与参考模板完全一致”，则必须满足：

- 默认模型必须是 `friday/MiniMax-M2.7`，不能写成 `friday/minimax-m2.7`。
- `models.providers.friday.models` 必须包含 `glm-5-turbo` 和 `MiniMax-M2.7`。
- `agents.defaults.models` 的 alias 必须分别是 `Minimax`、`MiniMax`、`GLM`。
- 顶层必须包含 `messages.ackReactionScope = group-mentions`、`commands.ownerDisplay = raw`、`skills.install.nodeManager = npm`。
- 不要额外默认写入模板之外的 provider 或顶层字段；但若文件里本来就有其他字段，应继续保留，除非用户明确要求删除。

## install

首次安装时，按以下顺序执行：

1. 跑“预检”。
2. 用 installer 或用户指定的包管理器安装 CLI。
3. 执行“准备配置和保留字段”。
4. 运行“仅在关键引导缺失时运行非交互 onboard”中的 onboard 段。
5. 运行“用最小补丁方式把配置对齐到参考模板”。

## repair

先执行官方无交互诊断：

```bash
openclaw doctor --fix --non-interactive --yes --no-workspace-suggestions | cat
```

如果 gateway 仍不健康，再做服务级修复：

```bash
openclaw gateway install --force
openclaw gateway restart
sleep 2
openclaw gateway status --require-rpc | cat
```

如果 `gateway status` 仍提示服务使用 version manager 里的 Node，按下面步骤把受管服务切到本地前缀运行时：

```bash
curl --retry 3 --retry-delay 2 --connect-timeout 10 -fsSL --proto '=https' --tlsv1.2 https://openclaw.ai/install-cli.sh | bash -s -- --json --prefix "$HOME/.openclaw" --version 2026.4.1
~/.openclaw/bin/openclaw gateway install --force
~/.openclaw/bin/openclaw gateway restart
sleep 2
~/.openclaw/bin/openclaw gateway status --require-rpc | cat
```

目标状态：

- LaunchAgent / systemd 的 `ProgramArguments` 指向 `~/.openclaw/tools/node-v*/bin/node`。
- 入口脚本指向 `~/.openclaw/lib/node_modules/openclaw/dist/entry.js`。
- `gateway status --require-rpc` 不再提示 `nvm` / `fnm` / `asdf` 之类的 version manager 路径。

如果 `doctor --fix` 失败点是 bundled plugin runtime deps，则继续做依赖修复：

```bash
~/.openclaw/tools/node/bin/node ~/.openclaw/lib/node_modules/openclaw/scripts/postinstall-bundled-plugins.mjs 2>&1 | cat
```

若输出里仍有 `ETARGET` / `No matching version found`，说明某个 bundled plugin manifest 写了 npm 上不存在的版本。此时要：

1. 找到失败包属于哪个 `dist/extensions/*/package.json`。
2. 用 `npm view <pkg> version` 确认 npm 上实际存在的版本。
3. 把不存在的版本改成最近兼容且真实存在的版本。
4. 再次运行 `scripts/postinstall-bundled-plugins.mjs`。

例如当前 `2026.4.1` 的 `diagnostics-otel` 会把几组 OpenTelemetry 版本写成 npm 上不存在的值。优先使用 skill 资源脚本：`scripts/repair_bundled_runtime_deps.py`。

推荐用法：

```bash
python3 ~/.codex/skills/openclaw-install-assistant/scripts/repair_bundled_runtime_deps.py \
  --runtime-root "$HOME/.openclaw/lib/node_modules/openclaw" \
  --npm-bin "$HOME/.openclaw/tools/node/bin/npm"

python3 ~/.codex/skills/openclaw-install-assistant/scripts/repair_bundled_runtime_deps.py \
  --runtime-root "$HOME/.nvm/versions/node/v22.22.0/lib/node_modules/openclaw" \
  --npm-bin "$HOME/.nvm/versions/node/v22.22.0/bin/npm"
```

补充规则：

- 脚本会先应用内置的已知 manifest 修复，再按“隔离前缀 + 软链”方式补齐 direct deps。
- 隔离依赖树默认放在 `<runtime-root>/.bundled-runtime-deps/`。
- direct deps 会在 `<runtime-root>/node_modules/<dep>` 下改成指向隔离前缀的软链；transitive deps 留在隔离前缀里解析。
- 若只想先看将要做什么，先加 `--dry-run`。
- 除非用户明确要求手动逐条修，否则优先调用该脚本，而不是把长命令内联重写一遍。

脚本里的风险操作必须提前说明：

- 会修改已安装 OpenClaw 包里的 `dist/extensions/*/package.json`，目前内置的是 `diagnostics-otel` 的已知版本漂移修复。
- 会在 `<runtime-root>/.bundled-runtime-deps/` 下运行 `npm install`，写入新的隔离依赖树。
- 会删除并重建 `<runtime-root>/node_modules/<dep>` 下对应 direct deps 的现有目录或软链，然后替换成新的软链。
- 如果 `--runtime-root` 指错到非 OpenClaw 安装根，可能误改别的 `node_modules`；因此必须显式核对路径后再执行。
- 修复完成后必须再次验证 `openclaw --version`、`openclaw gateway status --require-rpc`，并重新枚举缺失依赖是否已清零。

如果脚本跑完仍报 `ETARGET` / `No matching version found`，先用 `npm view <pkg> version` 确认上游真实版本，再把对应修复映射补进脚本里的 `KNOWN_MANIFEST_FIXES`。

修复完成后，仍要重新执行：

1. “准备配置和保留字段”
2. “仅在关键引导缺失时运行非交互 onboard”
3. “用最小补丁方式把配置对齐到参考模板”

## migration

只有用户明确提到旧包名或旧机器迁移时，才执行本节。

清理旧全局包：

```bash
npm ls -g --depth=0 2>/dev/null | grep -E "clawdbot|moltbot" || true
pnpm ls -g --depth=0 2>/dev/null | grep -E "clawdbot|moltbot" || true
npm rm -g clawdbot moltbot
# or
pnpm remove -g clawdbot moltbot
# or
bun remove -g clawdbot moltbot
```

迁移整套状态目录，而不是只复制 `openclaw.json`：

```bash
# old machine
openclaw gateway stop
cd ~
tar -czf openclaw-state.tgz .openclaw

# new machine
cd ~
tar -xzf openclaw-state.tgz
openclaw doctor --fix --non-interactive --yes --no-workspace-suggestions | cat
openclaw gateway restart
openclaw status | cat
```

迁移完成后，仍要重新执行：

1. “准备配置和保留字段”
2. “仅在关键引导缺失时运行非交互 onboard”
3. “用最小补丁方式把配置对齐到参考模板”

## 验证与回报

每次完成安装、升级、修复或迁移后，都执行：

```bash
CONFIG_FILE_RAW="$(openclaw config file 2>/dev/null || echo "${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw/openclaw.json}")"
CONFIG_FILE="${CONFIG_FILE_RAW/#\~/$HOME}"
GATEWAY_PORT="$(jq -r '.gateway.port // 18789' "$CONFIG_FILE")"
GATEWAY_BIND="$(jq -r '.gateway.bind // "loopback"' "$CONFIG_FILE")"
if [ "$GATEWAY_BIND" = "loopback" ] || [ "$GATEWAY_BIND" = "127.0.0.1" ]; then
  DASHBOARD_URL="http://127.0.0.1:${GATEWAY_PORT}"
else
  DASHBOARD_URL="http://${GATEWAY_BIND}:${GATEWAY_PORT}"
fi

openclaw --version
openclaw config validate | cat
openclaw health | cat
openclaw gateway status --require-rpc | cat
printf '%s\n' "$DASHBOARD_URL"
jq -r '.agents.defaults.model.primary // "unset"' "$CONFIG_FILE"
jq -r '.agents.defaults.workspace // "unset"' "$CONFIG_FILE"
jq -r '.models.providers.friday.apiKey // "unset"' "$CONFIG_FILE"
jq -r '.models.providers.friday.models[].id' "$CONFIG_FILE"
jq -r '.messages.ackReactionScope // "unset"' "$CONFIG_FILE"
jq -r '.skills.install.nodeManager // "unset"' "$CONFIG_FILE"
```

补充规则：

- 只有在用户明确要求校验 provider 可用性或模型目录时，才额外执行 `openclaw models status | cat`。
- 如果 `openclaw health` 已经明确失败，再补充读取 `openclaw doctor | cat` 或 `openclaw doctor --fix ...`，不要先无谓扩大动作。
- 若用户要求“更稳的 gateway service”，验证时必须额外检查 `~/Library/LaunchAgents/ai.openclaw.gateway.plist`（或 systemd unit）是否已改为 `~/.openclaw/tools/node-v*/bin/node` + `~/.openclaw/lib/node_modules/openclaw/dist/entry.js`。
- 若用户要求“修复 bundled plugin runtime deps”，验证时必须再次枚举 `dist/extensions/*/package.json` 声明的依赖，确认对应安装根下 `node_modules` 已存在这些包；不能只看 `doctor` 是否退出 0。

完成后必须明确告诉用户：

- CLI 是否安装成功，以及版本号。
- Gateway 是否 running，RPC 是否可用。
- 配置文件路径。
- 默认模型是否已是 `friday/MiniMax-M2.7`。
- `friday` provider 是否已按模板写入 `glm-5-turbo` 与 `MiniMax-M2.7`。
- workspace 是什么。
- Dashboard URL 是什么。
- `messages.ackReactionScope` 是否已是 `group-mentions`。
- `skills.install.nodeManager` 是否已是 `npm`。
- 配置文件结构是否已与参考 `openclaw.json` 对齐。

## 官方链接

- Install: <https://docs.openclaw.ai/install>
- Updating: <https://docs.openclaw.ai/install/updating>
- Installer Internals: <https://docs.openclaw.ai/install/installer>
- CLI Automation: <https://docs.openclaw.ai/start/wizard-cli-automation>
- Onboard CLI: <https://docs.openclaw.ai/cli/onboard>
- Gateway CLI: <https://docs.openclaw.ai/cli/gateway>
- Migration Guide: <https://docs.openclaw.ai/install/migrating>
