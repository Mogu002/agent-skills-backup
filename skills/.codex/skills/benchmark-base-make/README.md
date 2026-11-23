# benchmark-base-make

按飞书评测题的【样张设计思路】构建或修整指定 Base 副本，支持字段口径差异、正负样本、PDF/扫描附件、Gold 和写入验收。

## 安装

解压后，将 `benchmark-base-make` 文件夹复制到 `C:\Users\<用户名>\.codex\skills\`；如使用 `CODEX_HOME`，复制到 `%CODEX_HOME%\skills\benchmark-base-make\`。重启或刷新 Codex。

## 使用

任务中明确调用 `$benchmark-base-make`，并提供评测表链接、题号和目标字段。例如：
`使用 [$benchmark-base-make]，按照这张评测表的【样张设计思路】修改【考察数据表的副本】，处理 Q60-Q65。`

技能使用 lark-cli 读写 Base，并在本地生成附件。执行前需完成 Lark/飞书认证并具备目标 Base 权限。

## 文件

`SKILL.md` 是主指令；`references/` 是计划、写入和验收规则；`scripts/` 是快照、请求准备、附件生成和验收脚本；`agents/openai.yaml` 是界面元数据。
