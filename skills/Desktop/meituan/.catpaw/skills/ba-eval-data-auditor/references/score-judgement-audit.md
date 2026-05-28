# Score Judgement Audit

当任务不是检查 `instruction.md` / `rubrics.md` 格式，而是复核某次 `score.md` 判分是否正确时，读取本文件。

## 适用场景

用于以下任务：
- 用户要求根据 `message.json` 或 `openai_messages.json`、`score.md`、`solution/rubrics.md` 判断某次 score 是否打对
- 用户怀疑 `score.md` 中 `pass` / `all_pass` / `score` 和模型真实输出不一致
- 用户希望定位是模型答案有问题，还是评分理由写错、判错

## 默认工作流

1. 先确认三类输入是否齐全：模型消息文件、`score.md`、`solution/rubrics.md`
2. 从 `message.json` 或 `openai_messages.json` 中定位最后一个 assistant 最终答复；默认以最后一个 `role=assistant` 的文本内容作为被评分答案
3. 读取 `solution/rubrics.md` 中的 rubrics JSON，按 `id` 和 `content` 建立核对表
4. 读取 `score.md` 中的评分 JSON，核对：
   - `score`
   - `result_json.results[*].rubric_id`
   - `result_json.results[*].rubric_content`
   - `result_json.results[*].reason`
   - `result_json.all_pass`
5. 逐条 rubric 对照最终答复，独立判断该条应当 `pass` 还是 `fail`
6. 再把独立判断与 `score.md` 中记录的 `pass` / `all_pass` / `score` 对比，指出是否判对
7. 若结论不一致，优先说明是以下哪一类问题：
   - rubric 理解错
   - 证据引用错
   - reason 说对了但 `pass` 标错
   - 单条结果对，但 `all_pass` 或 `score` 聚合错

## 具体判断规则

### 先看什么算“被评分答案”

- 默认取消息文件中最后一个 `role=assistant` 的文本内容
- 不要把 tool output、推理草稿或中间轮 assistant 文本当作最终答案，除非用户明确说明评分对象不是最后一次答复
- 若消息文件是对象结构，优先读取 `messages`
- 若消息文件缺少清晰的最终 assistant 文本，要先向用户说明无法可靠复核

### 先做结构一致性检查

至少确认以下几点：
- `score.md` 中每条 `rubric_id` 都能在 `solution/rubrics.md` 中找到
- `score.md` 中的 `rubric_content` 与对应 rubric 原文一致或至少语义一致
- `results` 条数与实际被评分的 rubric 范围一致
- `all_pass=true` 时，所有单条 `pass` 都应为 `true`
- `all_pass=false` 时，至少有一条单条 `pass` 为 `false`
- 若任务采用二值总分，通常 `all_pass=true` 对应 `score=1`，`all_pass=false` 对应 `score=0`；若实际项目另有约定，按题目约定说明

### 单条 rubric 怎么判

逐条看 rubric 时，只依据：
- rubric 原文
- 模型最终答复文本
- score 中给出的 reason

不要用以下内容替代证据：
- 你自己推测模型“本来想表达什么”
- 中间工具输出但最终答复没有写出的信息
- 题目背景中看似合理、但答案文本没出现的事实

判定时优先分三步：
1. rubric 要求答案必须包含什么
2. 最终答复里是否真的出现了这些信息
3. `score.md` 的 `reason` 是否引用了正确证据，并推出了正确的 `pass/fail`

### 何时算 score 判错

满足任一情况即可视为判错：
- `pass=true`，但答案没有满足 rubric
- `pass=false`，但答案其实满足 rubric
- `reason` 引用的证据并不存在于最终答复中
- `reason` 只证明了部分要素，却把整条 rubric 判成通过
- 单条 `pass/fail` 基本正确，但 `all_pass` 聚合结论错误
- `score` 与 `all_pass` 不一致

## 常见 gotchas

- 不要只看 `score.md` 的 `reason` 写得像不像，要回到最终 assistant 答复逐字核对
- 不要把 `rubric_content` 的转述当成 rubric 原文，优先以 `solution/rubrics.md` 为准
- 若 rubric 含“或”条件，只要答案满足任一分支即可，不要误判为必须全满足
- 若 rubric 是“答案需提及/说明/指出”，通常只要求答案明确出现对应要点，不一定要求完全同词复现
- 若 rubric 是高概括表述，要避免过度宽松；不能因为答案主题接近就直接判通过
- 若最终答复很长，优先提取与该 rubric 最相关的原句，再判断 `reason` 是否引用准确
- 若 `score.md` 只错在聚合结果，单条判分也要照实说明，不要把所有条目都算错

## 建议输出方式

向用户汇报时，优先给：
- 本次复核的文件路径
- 最终 assistant 答复是否定位成功
- 每条 rubric 的独立判断结果
- `score.md` 原判是否正确
- 若判错，错在单条 `pass/fail`、`reason`、还是 `all_pass/score` 聚合
- 若没有发现问题，也要明确说明“本次仅基于最终答复文本和现有 rubrics 复核，不能替代 rubric 本身合理性审计”
