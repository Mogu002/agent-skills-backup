---
name: skill-creator-zh
description: 创建和更新高质量 skill 的中文指南。当用户想新建一个 skill，或更新已有 skill，以扩展 agent 在特定知识、工作流或工具集成上的能力时，使用这个技能。
metadata:
  short-description: 创建或更新一个 skill
---

# Skill Creator 中文版

这个技能提供一套用于创建高质量 skill 的指导方法。

## 关于 Skill

Skill 是模块化、自包含的文件夹，用来通过专门知识、工作流和工具说明扩展 agent 的能力。你可以把它理解为某个具体领域或任务的“上手指南”——它把通用 agent 变成在特定场景中具备程序性知识的专用 agent。

### Skill 能提供什么

1. 专门工作流 - 面向特定领域的多步骤流程
2. 工具集成 - 针对特定文件格式或 API 的使用说明
3. 领域知识 - 公司内部知识、schema、业务逻辑
4. 配套资源 - 用于复杂和重复任务的脚本、参考资料和静态资源

## 核心原则

### 简洁最重要

上下文窗口是公共资源。Skill 要和系统提示、对话历史、其他 Skill 的元数据以及当前用户请求共享上下文窗口。

**默认假设：agent 本身已经很聪明。** 只补充它本来不太可能稳定掌握的内容。对每一段信息都要追问："这段解释真的有必要吗？"、"它值不值得消耗这些 token？"

优先使用简洁示例，而不是冗长解释。

### 设置合适的自由度

让指令的具体程度与任务的脆弱性和变化程度相匹配：

**高自由度（文字型说明）**：适合多种做法都合理、决策依赖上下文、主要靠启发式判断的任务。

**中等自由度（伪代码或带参数脚本）**：适合存在推荐模式、允许一定变化、行为会受配置影响的任务。

**低自由度（特定脚本、极少参数）**：适合流程脆弱、容易出错、一致性要求很高、必须严格按顺序执行的任务。

可以把 agent 想象成在探索一条路径：如果是两边都是悬崖的窄桥，就需要更强约束；如果是开阔地，就允许更多路线。

### 保护验证的客观性

在迭代过程中，你可以使用子 agent 来验证 skill 在真实任务中的表现，或验证某个怀疑的问题是否真的存在。只有在当前环境允许启动新子 agent 时，才这样做。

使用子 agent 验证时，要把它当成评估手段。目标是判断 skill 是否具有泛化能力，而不是让另一个 agent 因为看到了泄漏上下文而“猜出正确答案”。

优先提供原始材料，比如示例提示词、输出、diff、日志或 trace。只给完成验证所需的最少任务上下文。除非验证本身必须依赖这些内容，否则不要提前暴露预期答案、怀疑的 bug、打算的修复方案或你自己的结论。

### Skill 的组成

每个 skill 都至少包含一个必需的 `SKILL.md` 文件，以及可选的配套资源：

```text
skill-name/
├── SKILL.md (必需)
│   ├── YAML frontmatter 元数据 (必需)
│   │   ├── name: (必需)
│   │   └── description: (必需)
│   └── Markdown 指令正文 (必需)
├── agents/ (推荐)
│   └── openai.yaml - skill 列表和 UI 展示所需元数据
└── 配套资源 (可选)
    ├── scripts/          - 可执行代码（Python/Bash 等）
    ├── references/       - 按需载入上下文的参考资料
    └── assets/           - 输出时会使用到的文件（模板、图标、字体等）
```

#### `SKILL.md`（必需）

每个 `SKILL.md` 都由两部分组成：

- **Frontmatter**（YAML）：包含 `name` 和 `description`。这是 agent 判断何时触发该 skill 的唯一元数据，因此必须清晰、全面地说明 skill 是做什么的，以及什么时候该用。
- **正文**（Markdown）：skill 的使用说明和指导内容。只有在 skill 触发后，正文才会被载入。

#### Agents 元数据（推荐）

- 用于 skill 列表和 UI 芯片的展示元数据
- 生成前先阅读 `references/openai_yaml.md`，并遵守其中的字段说明和约束
- 需要创建面向人的 `display_name`、`short_description` 和 `default_prompt`
- 应通过 `scripts/generate_openai_yaml.py` 或 `scripts/init_skill.py`，使用 `--interface key=value` 以确定性方式生成
- 更新 skill 时，要检查 `agents/openai.yaml` 是否仍与 `SKILL.md` 一致；不一致就重新生成
- 只有用户明确提供时，才加入其他可选界面字段（如图标、品牌色）
- 字段定义和示例见 `references/openai_yaml.md`

#### 配套资源（可选）

##### 脚本（`scripts/`）

用于需要更高确定性或会反复重写的任务的可执行代码（Python/Bash 等）。

- **什么时候加**：当相同代码会被重复编写，或需要确定性和稳定性时
- **示例**：`scripts/rotate_pdf.py`，用于旋转 PDF
- **好处**：更省 token、更稳定，而且很多情况下无需完整载入上下文即可执行
- **注意**：如果脚本需要 patch 或做环境适配，agent 仍可能需要阅读它

##### 参考资料（`references/`）

用于按需载入上下文、辅助 agent 理解和推理的文档与资料。

- **什么时候加**：当有文档资料需要在工作过程中被参考时
- **示例**：`references/finance.md`、`references/mnda.md`、`references/policies.md`、`references/api_docs.md`
- **用途**：数据库 schema、API 文档、领域知识、公司政策、详细工作流说明
- **好处**：保持 `SKILL.md` 精简，只在需要时加载
- **最佳实践**：如果文件很大（>10k 词），在 `SKILL.md` 中写明 grep 搜索模式
- **避免重复**：信息应只存在于 `SKILL.md` 或 references 文件中的一个位置，不要重复。详细资料更适合放在 references 中；`SKILL.md` 只保留必要流程和核心指导

##### 静态资源（`assets/`）

这些文件通常不应被载入上下文，而是用于最终输出产物中。

- **什么时候加**：当 skill 需要在最终产物中使用某些文件时
- **示例**：`assets/logo.png`、`assets/slides.pptx`、`assets/frontend-template/`、`assets/font.ttf`
- **用途**：模板、图片、图标、脚手架代码、字体、样例文档等
- **好处**：把输出资源和说明文档分开，不必把这些资源塞进上下文

#### 不要在 Skill 里放什么

Skill 只应该包含直接支持其功能的必要文件。不要创建多余文档或辅助文件，包括但不限于：

- `README.md`
- `INSTALLATION_GUIDE.md`
- `QUICK_REFERENCE.md`
- `CHANGELOG.md`
- 等等

Skill 应只保留 AI agent 完成任务真正需要的内容，不要存放关于创建过程、安装和测试流程、面向人的说明文档等额外信息。这些文件只会制造噪音和负担。

### 渐进式披露设计原则

Skill 使用三层加载机制来提高上下文效率：

1. **元数据（name + description）** - 始终在上下文中（约 100 词）
2. **`SKILL.md` 正文** - 当 skill 触发时加载（建议少于 5k 词）
3. **配套资源** - 按需加载（理论上无上限，因为脚本可以不读全文直接执行）

#### 渐进式披露模式

尽量让 `SKILL.md` 正文只保留核心内容，并控制在 500 行以内，以减少上下文膨胀。接近这个规模时，应考虑拆分内容。拆分后，必须在 `SKILL.md` 中明确引用这些文件，并说明何时阅读它们。

**关键原则：** 当一个 skill 支持多种变体、框架或选项时，`SKILL.md` 只保留核心工作流和选择逻辑；把各个变体特有的细节、模式、示例和配置移到单独的参考文件中。

**模式 1：高层指南 + 参考文件**

```markdown
# PDF 处理

## 快速开始

使用 pdfplumber 提取文本：
[代码示例]

## 高级能力

- **表单填写**：完整说明见 [FORMS.md](FORMS.md)
- **API 参考**：全部方法见 [REFERENCE.md](REFERENCE.md)
- **示例**：常见模式见 [EXAMPLES.md](EXAMPLES.md)
```

在这种设计里，agent 只会在需要时再去加载 `FORMS.md`、`REFERENCE.md` 或 `EXAMPLES.md`。

**模式 2：按领域组织**

对于覆盖多个业务域的 skill，按领域拆分内容，避免载入无关信息：

```text
bigquery-skill/
├── SKILL.md （概览与导航）
└── references/
    ├── finance.md （营收、计费指标）
    ├── sales.md （商机、pipeline）
    ├── product.md （API 使用、功能定义）
    └── marketing.md （活动、归因）
```

如果用户问销售指标，只读 `sales.md` 即可。

同理，如果 skill 支持多个框架或供应商，也可以按变体拆分：

```text
cloud-deploy/
├── SKILL.md （工作流 + 供应商选择）
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

当用户选择 AWS 时，只需要读取 `aws.md`。

**模式 3：条件式细节**

基础内容直接写，进阶内容通过引用引导：

```markdown
# DOCX 处理

## 创建文档

新建文档使用 docx-js。详见 [DOCX-JS.md](DOCX-JS.md)。

## 编辑文档

简单编辑可直接修改 XML。

**处理 tracked changes**：见 [REDLINING.md](REDLINING.md)
**查看 OOXML 细节**：见 [OOXML.md](OOXML.md)
```

只有当用户真的需要这些高级能力时，agent 才去读 `REDLINING.md` 或 `OOXML.md`。

**重要规则：**

- **避免深层嵌套引用** - 所有参考文件都应直接从 `SKILL.md` 链接，最多一层深度
- **长参考文件要有目录** - 超过 100 行的参考文件，顶部应写目录，便于快速预览整体结构

## Skill 创建流程

Skill 创建通常包括以下步骤：

1. 通过具体示例理解 skill 的用途
2. 规划可复用的 skill 内容（scripts、references、assets）
3. 初始化 skill（运行 `init_skill.py`）
4. 编辑 skill（编写资源和 `SKILL.md`）
5. 验证 skill（运行 `quick_validate.py`）
6. 基于真实使用不断迭代；复杂 skill 还要做前向测试

除非有明确理由不适用，否则按顺序执行这些步骤。

### Skill 命名

- 只使用小写字母、数字和连字符；把用户给的标题规范化为连字符形式，例如 `Plan Mode` -> `plan-mode`
- 名称长度控制在 64 个字符以内
- 尽量使用简短、偏动作导向的名称
- 当按工具命名能提高清晰度或触发准确性时，可以加命名空间，例如 `gh-address-comments`、`linear-address-issue`
- skill 文件夹名必须与 skill 名完全一致

### 第 1 步：通过具体示例理解 Skill

只有当 skill 的使用模式已经非常清晰时，才可以跳过这一步。即便是在改已有 skill，这一步通常仍然有价值。

要做出有效的 skill，必须先理解它会如何被实际使用。这种理解可以来自：

- 用户直接提供的真实示例
- 由你生成、再通过用户反馈校准的示例

例如，构建一个 `image-editor` skill 时，值得弄清楚的问题包括：

- “这个 skill 要支持哪些功能？编辑、旋转，还有别的吗？”
- “你能给几个这个 skill 的典型使用示例吗？”
- “我能想到像‘去掉红眼’、‘旋转图片’这样的需求，还有其他常见说法吗？”
- “用户会怎么说，才能触发这个 skill？”
- “这个 skill 应该建在哪里？如果你没要求，我默认放到 `$CODEX_HOME/skills`；如果没设置 `CODEX_HOME`，就放到 `~/.codex/skills`，这样可以被自动发现。”

为了避免一次性问太多，不要在一条消息里塞进大量问题。优先问最关键的，再按需要追问。

当你已经清楚这个 skill 需要支持哪些能力时，这一步就结束。

### 第 2 步：规划可复用的 Skill 内容

要把具体示例转成高质量 skill，需要逐个分析这些示例：

1. 假设从零开始完成这个任务，需要怎么做
2. 判断哪些 `scripts`、`references`、`assets` 能帮助后续重复执行时更高效

例如：

- 为 `pdf-editor` 处理“帮我旋转这个 PDF”这类需求时，会发现旋转 PDF 需要反复写类似代码，因此可以加入 `scripts/rotate_pdf.py`
- 为 `frontend-webapp-builder` 处理“帮我做个待办应用”这类需求时，会发现前端项目需要重复写同样脚手架，因此可以加入 `assets/hello-world/` 之类模板
- 为 `big-query` 处理“今天有多少用户登录”这类需求时，会发现每次都要重新摸清表结构，因此可以加入 `references/schema.md`

通过分析每个具体示例，整理出 skill 里真正值得沉淀的可复用资源列表：脚本、参考资料和静态资源。

### 第 3 步：初始化 Skill

这时就该真正创建 skill 了。

如果要开发的 skill 已经存在，可以跳过这一步，继续后面编辑。

在运行 `init_skill.py` 前，先确认用户想把 skill 建在哪里。如果用户没指定，默认用 `$CODEX_HOME/skills`；若 `CODEX_HOME` 未设置，则回退到 `~/.codex/skills`，这样 skill 能被自动发现。

从零创建 skill 时，始终优先运行 `init_skill.py`。这个脚本会生成一套标准模板，把 skill 所需的基础结构一次性搭好，能显著提升效率和可靠性。

用法：

```bash
scripts/init_skill.py <skill-name> --path <output-directory> [--resources scripts,references,assets] [--examples]
```

示例：

```bash
scripts/init_skill.py my-skill --path "${CODEX_HOME:-$HOME/.codex}/skills"
scripts/init_skill.py my-skill --path "${CODEX_HOME:-$HOME/.codex}/skills" --resources scripts,references
scripts/init_skill.py my-skill --path ~/work/skills --resources scripts --examples
```

这个脚本会：

- 在指定路径创建 skill 目录
- 生成带正确 frontmatter 和 TODO 占位的 `SKILL.md` 模板
- 基于传入的界面字段，通过 agent 生成 `agents/openai.yaml`
- 按 `--resources` 选择性创建资源目录
- 在启用 `--examples` 时，加入示例文件

初始化后，再根据实际需要定制 `SKILL.md` 和相关资源。如果用了 `--examples`，记得替换或删除占位示例。

要生成 `display_name`、`short_description` 和 `default_prompt`，先阅读 skill 本身，再把这些值通过 `--interface key=value` 传给 `init_skill.py`；或者之后再用下面命令重新生成：

```bash
scripts/generate_openai_yaml.py <path/to/skill-folder> --interface key=value
```

除非用户明确提供，否则不要填写其他可选界面字段。完整字段定义见 `references/openai_yaml.md`。

### 第 4 步：编辑 Skill

编辑新建或已有 skill 时，要始终记住：这个 skill 是给另一个 agent 使用的。你要写进去的是对另一个 agent 真正有帮助、而且不是显而易见的内容。重点考虑哪些程序性知识、领域细节或可复用资源，能显著提升另一个 agent 执行任务的效果。

经过较大修改后，或者 skill 本身比较复杂时，应使用子 agent 做前向测试。测试时要把待验证的 skill 和真实任务材料交给子 agent，而不是把你自己的诊断意见一起告诉它；提示词也应足够通用，避免因为泄漏答案导致“假成功”。

#### 先实现可复用资源

开始实现时，先处理前面识别出的 `scripts/`、`references/` 和 `assets/`。这一步有时需要用户提供输入，例如品牌资产、模板或文档。

新增的脚本必须实际运行测试，确认没有 bug，并且输出符合预期。如果有很多相似脚本，可以挑代表性样本测试，以平衡质量和效率。

如果初始化时用了 `--examples`，删除不需要的占位文件。只保留真正用得上的资源目录。

#### 更新 `SKILL.md`

**写作规则：** 正文尽量使用祈使式或动词原形表达。

##### Frontmatter

在 YAML frontmatter 中写入 `name` 和 `description`：

- `name`：skill 名称
- `description`：skill 的主触发机制，用来帮助 agent 判断什么时候该用它
  - 既要写出 skill 做什么，也要写清楚哪些场景会触发它
  - 所有“什么时候使用”的信息都应写在 `description` 中，而不是正文里。因为正文只有触发后才会加载，所以正文中的 “When to Use This Skill” 对触发帮助不大
  - 例如 `docx` skill 的描述可以写成："用于专业文档（.docx）的创建、编辑和分析，支持 tracked changes、评论、格式保留和文本提取。当 agent 需要新建文档、修改内容、处理修订、添加评论或执行其他文档任务时使用。"

不要在 YAML frontmatter 中加入其他字段。

##### 正文

正文用于写 skill 的使用说明，以及如何使用其中的配套资源。

### 第 5 步：验证 Skill

完成开发后，先验证 skill 目录，尽早发现基础问题：

```bash
scripts/quick_validate.py <path/to/skill-folder>
```

这个校验脚本会检查 YAML frontmatter 格式、必需字段和命名规则。如果失败，就根据报错修复后重新运行。

### 第 6 步：迭代

skill 在测试或真实使用后，可能会暴露新的问题；用户也可能继续提出改进需求。

常见迭代流程：

1. 用这个 skill 处理真实任务
2. 观察哪里卡住、低效或误触发
3. 找出应该如何更新 `SKILL.md` 或配套资源
4. 实施修改并重新测试
5. 在合理且合适时做前向测试

## 前向测试

前向测试可以通过启动子 agent 来进行，用极少上下文对 skill 做压力测试。
子 agent **不应该知道自己在“测试 skill”**。它应被当成一个正常收到用户任务的 agent。

给子 agent 的提示词应类似：

```text
Use $skill-x at /path/to/skill-x to solve problem y
```

而不是：

```text
Review the skill at /path/to/skill-x; pretend a user asks you to...
```

前向测试的决策规则：

- 默认倾向于做前向测试
- 但如果你判断前向测试可能：
  - 花很长时间
  - 需要额外用户审批
  - 修改真实生产系统

那么应先向用户展示你计划使用的提示词，并请求：
1. 一个 yes/no 决定
2. 任何他们建议的修改

前向测试时，还要注意：

- 每次独立测试尽量用全新线程
- 传给子 agent 的是 skill 和接近真实用户的话术
- 传原始材料，不传你的结论
- 不要泄露预期答案或计划中的修复
- 每轮迭代后，重新从源材料构建上下文
- 审查子 agent 的输出、推理和产物
- 不要在磁盘上残留会污染后续测试的产物；测试后要及时清理

如果前向测试只有在子 agent 看到了泄漏上下文时才成功，那就说明 skill 本身或测试方法仍需收紧，不能直接信任这个结果。
