---
name: pi-project-resource-installer
description: 当用户要为某一个具体项目安装、创建、迁移、启用、禁用或更新 Pi Extension、Skill、Prompt、Theme、Pi package、项目级配置或相关运行时依赖，并要求与全局 Pi 及其他项目隔离时，使用这个技能。NOT for 安装或升级 Pi CLI 本体、配置模型账号，或用户明确要求全局安装资源。
---

# Pi 项目级资源安装

将 Pi 本体视为全局运行时，将所有业务能力限制在目标项目自己的 `.pi/`。默认不得改变其他项目和用户级 Pi 资源。

## 开始前

1. 解析目标项目根目录。优先使用用户明确给出的目录，其次使用当前 Git 仓库根目录，再次使用当前工作目录。若存在多个合理目标且无法安全判断，先询问用户。
2. 完整读取目标项目的 `AGENTS.md`、现有 `.pi/settings.json`、相关 `package.json` 和待安装资源说明。保留无关的已有修改。
3. 检查资源来源、版本、运行时代码和依赖。Extension 拥有当前用户权限；安装第三方资源前必须审查来源，不能把未审查代码当作普通配置。
4. 明确本次范围：Extension、Skill、Prompt、Theme、package、配置和依赖分别需要哪些。不要顺带安装未要求的全局资源。

## 默认安装路径

资源是规范 Pi package 时，优先在目标项目根目录执行：

```bash
pi install -l <固定版本或固定 ref 的来源>
```

`-l` 是强制要求。npm 包优先固定精确版本；Git 来源优先固定 tag 或 commit。确认结果写入项目 `.pi/settings.json`，并安装在项目 `.pi/npm/` 或 `.pi/git/`。

只有资源不是 Pi package，或用户正在项目内开发该资源时，才使用松散项目结构：

```text
<project>/
└── .pi/
    ├── extensions/
    ├── skills/
    ├── prompts/
    ├── themes/
    ├── settings.json
    ├── package.json
    └── node_modules/
```

只创建实际需要的目录。Skill 使用 `<project>/.pi/skills/<skill-name>/SKILL.md`；Extension、Prompt 和 Theme 分别放入对应目录。

## 依赖与配置

- Pi package 的第三方运行时依赖必须声明在该 package 的 `dependencies`；Pi 核心包和 `typebox` 按 Pi package 规范声明为 `"*"` 的 `peerDependencies`，不要重复打包。
- 松散 `.pi/extensions/` 直接导入的第三方包，应声明在项目 `.pi/package.json` 的 `dependencies`，固定精确版本，并安装到 `.pi/node_modules/`，确保 Node 从 Extension 的父目录解析到依赖。
- npm 安装默认使用 `npm install --ignore-scripts`。如依赖确实需要生命周期脚本，先审查脚本，再取得用户明确许可。
- `.pi/settings.json` 中的本地路径相对于该配置文件解析。优先使用项目内相对路径；禁止引用 Pi 源码仓库、临时目录、相邻业务项目或它们的 `node_modules`。
- 合并现有 JSON 配置，不覆盖无关键。项目级资源需要筛选时，使用 `packages` 对象形式限制 `extensions`、`skills`、`prompts` 或 `themes`。
- 默认不修改 `~/.pi/agent`、`~/.agents/skills`、全局 npm 安装或 shell 启动文件。只有用户明确要求全局作用域时才能改动，并应退出本 Skill 的默认项目级路径重新确认范围。

## 隔离检查

安装完成后必须验证：

1. 目标项目内所需资源和依赖完整，配置不存在指向项目外部实现目录的绝对路径或 `../` 跨项目引用。
2. `command -v pi` 指向全局 Pi CLI，而不是目标项目或某个 Pi 源码仓库；不要为了加载插件修改 Pi 本体。
3. 从目标项目启动一次 Pi，只检查启动页和已加载资源，不发送模型请求。确认目标 Extension、Skill 和 Prompt 只出现一次且无加载错误，然后立即退出。
4. 从一个不包含对应 `.pi` 的独立目录检查该业务 Extension、Skill 和 Prompt 未被加载。用户级 `~/.agents/skills` 可能仍由 Pi 自动发现；这不代表项目资源泄漏，应按资源名称核验。
5. 若有测试或确定性诊断，运行最小相关测试。安装失败时修复项目本地结构，不通过全局安装或引用其他项目依赖来绕过。

## 完成标准

最终报告必须说明：

- 目标项目路径；
- 安装或修改了哪些项目级资源；
- 依赖安装位置；
- 是否修改任何全局配置；
- 目标项目启动验证结果；
- 独立目录隔离验证结果；
- 尚未迁移或需要用户决定的旧副本。

未经用户明确要求，不删除旧资源、不移动历史 Session、不提交代码。
