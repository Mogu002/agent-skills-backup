---
name: bilibili-favorites-triage
description: 筛选 B 站收藏夹中适合知识库的来源，按证据查重、分类打标，生成可逐条播放、人评和导出摄入候选的本地 HTML；也用于续审、迁移人工决定与重新分析。
---

## 接收候选文件并按类型摄入

当用户让 LLM-wiki Agent 处理导出的候选 JSON，先读 [接收与分流规则](references/intake.md)。使用候选中的人工类型、备注、AI 主题与形式定位应补充的知识页或工具卡，回读实际证据，并按目标库 ingest 流程执行。旧版文件缺少 AI 字段时按人评和证据判断。

## 从链接到候选文件

脚本位于本 Skill 的 `scripts/triage.py`，下文以 `T` 表示其绝对路径。需要 macOS/Linux、Python 3.9+、可用的 IANA 时区数据库。脚本使用标准库。静态报告可直接打开；内嵌 B 站播放器需要联网。模型判断由当前 Agent 完成；批量任务按用户指定模型与实际可用路由执行。

1. 先读当前工作区采集规则。选择原始缓存目录 `CACHE` 和独立报告目录 `RUN`；personal-wiki 的采集缓存放在 raw/inbox，运行状态和报告放在 outputs。确定知识库目标、收藏夹 URL、稳定 dataset ID（建议 bilibili:加 fid，抽样另设后缀）和时区。
2. 优先复用已保存目录和证据。首次可以执行下方 inventory；它按原序保存只读分页，获取发布日与收藏日，核对总数与 BV 唯一性。相同缓存可接续同一轮盘点；刷新目录时使用新的缓存，避免把不同日期的分页拼接。登录、访问受限、限流或失败时保留已完成页并报告。可改用已安装的 bilibili-subtitle-to-markdown 的 list-only 和浏览器回退；先读实际安装位置的 SKILL.md、references/batch.md 和脚本 --help。缺该技能时仍可用已有材料。该采集器目录如缺收藏日期，传 null。
3. 首批取前 1–5 条并保留原顺序；全夹复用独立 run。用 init 读目录、可选 manifest 和 taxonomy。精确 BV 命中作为查重依据；认定同一工具已收录还须回读工具卡。未检查的库不要写成“无重复”。读 references/analysis.md，用 batch 取待分析输入，当前 Agent 写 JSON，再 merge。先处理廉价元数据；少数能改变判断的条目补读字幕、作者正文或评论，再执行 attach、batch、merge。每批可重复导入，旧分析与证据不一致时禁止出报告。
4. validate 后 render。运行中保持报告路径和 dataset ID 稳定。先在浏览器抽查计数、时间筛选和复核队列，确认人评与分享链接。人评存在浏览器本地；改路径、换浏览器或清理缓存前先点「导出完整决定」。旧报告需在原浏览器和原路径打开。带这项按钮的旧报告能备份历史选择；只有摄入 URL 的老清单不能恢复跳过和撤销历史。
5. 用 import-decisions 导入完整决定，再 export。为新路径 render 时会内嵌已导入的决定；已有浏览器缓存优先，可显式上传决定文件恢复。关闭断舍离可重新看到原来被排除的决定。文件冲突先比对，明确需要以新快照替换时加 --replace，旧快照保存在 decisions.previous.json。备份含全部事件，导出摄入清单只含最后人工决定为 include 且满足断舍离的条目。
6. 候选文件交给既有 ingest 流程。ready_for_ingest 表示有可回查的本地正文材料，登记前仍要核查来源元数据、完整性和去重。missing_evidence 先补采；内容不足时遵守仓库停止条件。报告操作只更新本地决定。

### 命令

以下变量由调用者设置。EVIDENCE 为已取得的材料文件；ANALYSIS 是 Agent 返回的结果文件。

```sh
python3 "$T" inventory --source "$URL" --cache "$CACHE/pages" --out "$CACHE/items.json"
python3 "$T" init --run "$RUN" --input "$CACHE/items.json" --dataset "$DATASET" --name "$NAME" --url "$URL" --goal "$GOAL"
python3 "$T" batch --run "$RUN" --out "$RUN/batch.json" --limit 20
python3 "$T" merge --run "$RUN" --input "$ANALYSIS" --batch "$RUN/batch.json"
python3 "$T" subtitle --bvid "$BV" --cache "$CACHE"
python3 "$T" attach --run "$RUN" --bvid "$BV" --ref subtitle --kind subtitle --file "$EVIDENCE" --label 'B站首P字幕'
python3 "$T" validate --run "$RUN"
python3 "$T" render --run "$RUN" --out "$RUN/review.html"
python3 "$T" import-decisions --run "$RUN" --input "$DECISIONS"
python3 "$T" export --run "$RUN" --out "$RUN/intake-candidates.json" --urls "$RUN/urls.txt"
```

attach 只在有新材料时执行，之后重新 batch 与 merge。init 可加 --manifest、--timezone 和 --taxonomy。export 可用 --as-of YYYY-MM-DD 重现某日的 365 天判断。状态含本机证据路径，搬机器需同时迁移证据并重新绑定；跨浏览器只迁移决定文件即可。
