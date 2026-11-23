# skillmgr 操作说明

先完成 SKILL.md 的入口/范围检查，只读取与当前任务有关的小节。下文命令中的大写参数来自实际查询或用户提供；沿用同一 `--home`/`--url`，不要照抄示例值。

## 标签

```bash
skillmgr skill list --json
skillmgr tag add SKILL_NAME automation document --dry-run --json
skillmgr tag add SKILL_NAME automation document --yes --json
skillmgr tag remove SKILL_NAME document --yes --json
skillmgr tag set SKILL_NAME automation --yes --json
```

1. 已有标签优先复用；“自动打标”默认增量 `tag add`，不把用户原有标签整套替换。标签基于实际描述/正文，不仅凭名字猜功能或可信来源。
2. 标签以 Skill 名称存储，对所有同名副本共享；`tag` 不支持 `--agent`。用户要求只改某个副本标签时说明限制，不扩大到全部副本。
3. 每个 Skill 最多 12 个去重标签，每个标签 1–32 个字符。达到上限时先提出清理/替换方案，不自动删除标签或截断语义。
4. `tag set` 会替换全部标签；不传标签则清空。只有明确授权替换/清空才使用它。`remove`/`set` 也先预览同一条命令再应用。
5. 批量处理先列明实际可见集合，逐项串行写入；冲突或失败时记录已完成部分，禁止绕过锁并行 PUT 配置。
6. 读取返回 `before`、`tags`，再用一次 `skill list --json` 回读受影响对象。回读不一致即报告未确认，不覆盖重试。

## 独立译文

适用于用户明确要求生成或更新 Agent Skill Manager App 中可切换的译文。译文存储在应用数据中，永远不覆盖原始 Skill。

```bash
skillmgr translation status SKILL_NAME --language zh-CN --json
skillmgr translation status SKILL_NAME --agent TARGET_ID --language zh-CN --file references/guide.md --json
skillmgr translation write SKILL_NAME --language zh-CN --file SKILL.md --input TRANSLATED_PATH --expect-sha256 SOURCE_SHA256 --dry-run --json
skillmgr translation write SKILL_NAME --language zh-CN --file SKILL.md --input TRANSLATED_PATH --expect-sha256 SOURCE_SHA256 --yes --json
```

1. `translation status` 默认中央库；翻译具体 Agent/项目副本时从 `target list` 取得 ID，并让 status、write、回读始终保留同一 `--agent`。目标语言仅支持 `en` / `zh-CN`，与 App 界面语言相互独立。
2. 只处理返回的 Markdown / MDX / Markdown 变体、TXT、RST、AsciiDoc 文件。代码、脚本、JSON、YAML、TOML 等配置文件不会进入列表，不要用 `file write` 或旁路文件为它们伪造译文。
3. 每个文件状态是 `missing`、`stale` 或 `current`。只翻译 missing；stale 返回当前原文、上次原文和旧译文，结合全文语境只更新变化影响的段落，保留未变段落的术语和语气。current 默认跳过。
4. 使用 status 返回的 `prompt` 作为 System Prompt。翻译自然语言正文；YAML frontmatter、围栏代码块、行内代码、命令、路径、占位符和链接目标保持原样。CLI 会确定性校验 frontmatter、代码与链接，不能靠修改校验规则绕过。
5. write 输入仍是该文件的完整译文，而不是 patch；`--expect-sha256` 是 status 返回的当前原文 Hash。先 dry-run，再在授权范围内 yes。若原文变化返回 CONFLICT，重新 status 并基于新的上下文重做变化部分，不能只刷新 Hash 提交旧译文。
6. 写后再次 status。全部文本文件为 current 时 App 显示最新译文；部分缺失或原文变化时显示过期状态，已保存旧译文仍可查看。原始 Skill 内容和版本历史不应变化。

## 正文编辑

适用于用户明确要求保存到原始 Skill 已有文件的修改。仅“翻译/摘要给我看”直接返回文本；需要 App 内可切换译文时走上一节，不能用 `file write` 覆盖原文。

```bash
skillmgr skill show SKILL_NAME --file SKILL.md --json
skillmgr file write SKILL_NAME --file SKILL.md --input INPUT_PATH --expect-sha256 HASH_FROM_SHOW --dry-run --json
skillmgr file write SKILL_NAME --file SKILL.md --input INPUT_PATH --expect-sha256 HASH_FROM_SHOW --yes --json
skillmgr skill show SKILL_NAME --file SKILL.md --json
```

1. 保存同一文件返回的 `data.sha256` 和原文。**不是整个目录的 `sourceHash`，也不是修改后内容的 Hash。** 若选了 `--agent TARGET_ID`，show、dry-run、write、回读必须全部保留。
2. 准备完整 UTF-8 新文本，通过工具写入输入文件，或 `--input -` 配合 stdin。它不是局部 patch 命令；只传片段会替换整个文件。
3. 修改默认保留 frontmatter 的 name/description。description 影响触发语义，用户没要求时不要重写。
4. `--input` 可以是已核验的本地路径；不要套用其他 CLI“输入只能相对路径”的限制。`--file` 才是 Skill 内部相对路径。只支持已有文本文件，每个文件/输入不超过 1 MiB；不得另建旁路文件或覆盖软链接来绕过限制。
5. 预览返回 `changed` 和新内容 Hash；它不是服务端生成的 diff，也没有自动备份预览产物。Agent 自行比较原文和拟写内容，在必要时展示差异。
6. 获得范围内授权后去掉 dry-run、加入 yes。冲突后重新读原文并重做修改决策；没有可用的 CLI `--force`。
7. 回读相同文件，核对正文及返回 Hash 是否匹配写入结果。后端会记录快照，但本 CLI 不提供历史回滚命令；需要回滚时指引桌面处理，不能承诺“一键自动撤销”。

## 导入与市场

### 已知来源

```bash
skillmgr import SOURCE_PATH --type local --dry-run --json
skillmgr import SOURCE_PATH --type local --yes --json
skillmgr import REPOSITORY_URL --type git --subdirectory SKILL_SUBDIR --branch BRANCH_OR_TAG --dry-run --json
skillmgr import PACKAGE_SPEC --type npm --dry-run --json
skillmgr import ARCHIVE_PATH --type zip --dry-run --json
```

1. `local` 是默认类型；Git 需要完整仓库 URL，仓库内技能用 `--subdirectory`。`--branch` 接受分支/标签，不声称支持任意 commit SHA；不要使用 `owner/repo@skill` 简写。
2. 来源路径/仓库/包必须由用户提供或外部检索得到并核验。只依靠市场排名不能判断安全；记录真实下载来源和许可信息，缺失就标注未知。
3. dry-run 会复制/下载、解析并暂存到 `.imports`，完成后清理，不是零网络/零磁盘。CLI 导入不执行 Skill 脚本，npm 使用 `pack --ignore-scripts`，但这不等于内容安全认证。
4. 检查 `data.name`、`content`、`origin`、`issues`。有 issues 则停止并说明；不自动修 frontmatter、重命名或删旧技能来绕过冲突。检查正文和用户任务相关的脚本风险，不执行它们。
5. dry-run 返回的 ticket 会被清理，不能拿票据继续提交。实际导入重新使用同一来源命令并将 dry-run 替换为 yes；分支/包可能变化，不能把预览 Hash 当最终版本保证。要求不可变版本但工具无法确保时先说明限制。
6. 导入只进入中央库，不自动对任何 Agent 启用。成功后 `skill show RETURNED_NAME --json` 回读名称和内容；目录存在/网络超时后先查询，避免重复导入。
7. 只有用户另有启用授权时才继续下一小节；导入许可不等于允许执行其中的脚本。

### 搜索/调研市场

- CLI 没有市场注册、搜索、排名或自动更新命令。用当前 Agent 可用的搜索/浏览/仓库工具核验候选；没有外部检索工具时索取来源，不生成虚构搜索结果。
- 调研结果包含能力、来源链接、兼容要求、许可/风险未知项，与本地库存对照后的重复情况。一般“推荐/对比”只产出报告，不执行下载或安装。
- 用户确认候选或明确授权“找一个并导入”后，将实际源解析成上面的 local/git/npm/zip 输入再预览、导入。市场网页 URL 不一定是可导入仓库 URL。
- 若用户明确指定 Vercel skills 或其他安装器，按该工具的流程处理，不替换成 skillmgr。若同时要求纳入管理器，先完成指定工具操作，再依据实际库存评估衔接，不声称两个管理器的来源记录自动同步。

## 启用范围

```bash
skillmgr target list --json
skillmgr skill list --json
skillmgr enable SKILL_NAME --agent TARGET_ID --dry-run --json
skillmgr enable SKILL_NAME --agent TARGET_ID --yes --json
skillmgr disable SKILL_NAME --agent TARGET_ID --dry-run --json
skillmgr disable SKILL_NAME --agent TARGET_ID --yes --json
skillmgr skill list --agent TARGET_ID --json
```

- 从 `target list` 的 `id/name/path/scope` 解析目标，ID 可代表 Agent 全局目录或项目目录。目标重名/不明确则澄清，不能用显示名称代替 ID，不能自行新增 Target。
- `enable` 可将可用本地副本加入指定环境；`disable` 将该环境副本移到停用区，不删除中央库。它们不代表执行 Skill。
- dry-run 仅展示计划和当前状态，不保证能通过归档/内容/冲突校验；真实结果看实际命令和回读。
- 已满足目标状态可以跳过；冲突时停止，不自动强制覆盖、删目标或先 disable 再 enable 试图绕过检查。
- 回读定位同一 `targets[].targetId` 并检查 `enabled`。停用后 `skill list --agent` 仍可能返回该 Skill，这是 configured 而非仍在启用。
