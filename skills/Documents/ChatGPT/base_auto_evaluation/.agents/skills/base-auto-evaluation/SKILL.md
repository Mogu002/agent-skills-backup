---
name: base-auto-evaluation
description: 当用户要从 CSV、Excel 或飞书 Base 批量评测飞书 Base 业务系统，运行或恢复评测批次、预览结构化结果、确认写入独立结果表、重试冻结写回或重新评测时，使用这个技能。
---

# Base Auto Evaluation

使用仓库自带的 `eval` CLI 编排批量评测。CLI 输出 JSON；以输出中的 `phase`、`batchId`、`nextCommand`、preview 和错误状态为准，不从终端文本猜测状态。

## 默认工作流

1. 在仓库根目录确认 `eval.config.json` 存在；不存在时提示用户从 `eval.config.example.json` 复制并填写真实模型、工具版本、浏览器和独立结果表配置。不要替用户猜 token、模型 ID 或凭据。
2. 确认 Node.js 24+，然后运行 `npm ci`（仅在依赖未安装时）、`npm run build` 和 `lark-cli auth status`。
3. 先执行只读映射预览：

   ```bash
   npm run eval -- map <source> --config <config>
   ```

   多 Sheet/表时根据输出让用户选择 `--resource <id>`。展示映射、代表行和错误。
4. 只有用户明确确认映射后，才执行：

   ```bash
   npm run eval -- map <source> --config <config> --resource <id> --confirm
   ```

   如果输出为 `collision_confirmation_required`，展示 Job Set/Artifact Base token 冲突；只有用户再次明确同意后，才执行输出给出的 `nextCommand`（含 `--confirm-collision`）。
5. 使用返回的 `batchId` 运行批次：

   ```bash
   npm run eval -- run <batch-id> --config <config>
   ```

   `run` 会执行当前 runnable jobs，并返回持久化 preview。
6. 如果任务进入 `waiting_auth`，让用户恢复 Lark 登录；确认登录恢复后执行：

   ```bash
   npm run eval -- resume <batch-id> --config <config> --auth-restored
   ```

   未确认登录恢复时，不添加 `--auth-restored`。
7. 可随时执行只读预览，不触发评测或写回：

   ```bash
   npm run eval -- preview <batch-id> --config <config>
   ```

8. 写回前先执行无确认的 schema/结果预览：

   ```bash
   npm run eval -- write <batch-id> --config <config>
   ```

   展示 eligible/skipped 任务以及 `missingFields`。只有用户明确确认批次结果后才添加 `--confirm`；只有用户同时明确确认创建所列字段后才添加 `--confirm-fields`。
9. 写回失败时区分：
   - 重发相同冻结结果：`retry-write <payload-id>`，不得重新评测。
   - 重新读取当前 Artifact：`rerun <job-id>`，它创建新 Attempt；随后执行返回的 resume 命令。不得覆盖旧 Attempt。

## 浏览器取证

- 默认顺序始终是 Lark CLI → 已认证主浏览器 → Ego Browser。
- `browser.runtimeModule` 配置存在时，CLI 加载该主浏览器运行时并复用对应登录态。
- 未配置主浏览器运行时时，CLI 会把主浏览器记录为 unavailable，再尝试 Ego；不得声称主浏览器取证成功。
- 如果用户明确要求主浏览器证据，先完成 runtime module 配置，不能以 Ego 结果冒充主浏览器结果。
- Lark CLI 已读到对象但关键 UI 内容为空时，按显式降级链继续浏览器取证，不直接判定对象未实现。

## 不可越过的边界

- `map` 预览不等于映射确认。
- Base token 冲突确认与普通映射确认是两次独立确认。
- `write` 结果确认与缺失字段创建确认是两次独立确认。
- 评测阶段只读 Artifact Base；任何结果表 mutation 只能由确认后的 write/retry-write 执行。
- 不自动运行 `purge-evidence`；仅在用户明确要求清理原始证据时执行。
- 不因部分证据缺失把已确认错误降为 unable；以 CLI 持久化结果为准。
- 不编辑 `requirements.md`、`design.md` 或规则文件来绕过运行错误。

## 完成标准

向用户报告：

- config 和 RuntimePin 是否匹配；
- batch ID、终态/非终态数量；
- score、coverage、primary issue、issue codes 和 blockers；
- 主浏览器/Ego 实际使用情况；
- write eligible/skipped 数量；
- 是否写回、pending payload 或新建 rerun Attempt。

若尚未获得必要确认、登录态或真实配置，停在对应阶段并给出下一条精确命令，不把“已生成预览”描述成“评测/写回已完成”。
