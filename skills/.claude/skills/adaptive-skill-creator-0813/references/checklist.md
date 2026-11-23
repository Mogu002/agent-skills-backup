# Delivery Checklist

## Fit and Scope

- [ ] Skill 是合适载体；必须执行的控制没有只留在 Skill 中
- [ ] 边界对应一个内聚用户结果，而不是宽泛领域或原子动作集合
- [ ] 已说明主模式 Explore / Codify / Learn，以及是否应用 Harden
- [ ] 知识、行为、验证、风险和路由证据分别评估

## Discovery and Reasoning

- [ ] `name` 合法且与目录一致
- [ ] `description` 描述用户意图和可观察结果，不含实现故事
- [ ] 覆盖正例、负例、hard negative 和相邻 Skill 边界
- [ ] 默认策略包含采用条件、切换信号、信息不足和停止处理
- [ ] 没有把未经验证的偏好写成普遍真理

## Execution and Information

- [ ] 正文只保留会改变决策的信息，长度与任务复杂度匹配
- [ ] support files 都有明确读取或使用条件，没有占位目录
- [ ] 确定性、重复或严格步骤已按需下沉为脚本/工具
- [ ] 脚本说明输入、输出、依赖、错误和副作用；高风险写入支持 preview/dry-run
- [ ] 平台专属能力位于显式适配分支，可移植核心不依赖单次环境

## Verification and Control

- [ ] 已按风险完成路由和行为评测，并与无 Skill 基线比较
- [ ] 客观、主观或混合任务使用了匹配的验证信号；主观不被当作跳过评测的理由
- [ ] 同一 Agent 的 self-check 没有被当作独立评测；评审独立性与任务风险相匹配
- [ ] 完成标准使用测试、schema、回读、渲染、diff 或专家 rubric 等独立信号
- [ ] 高风险操作具备最小权限、确认、恢复和审计
- [ ] 必须发生的步骤由 hook、CI、policy、状态机或程序保证
- [ ] 失败已归因到 routing / reasoning / execution / verification / control 层

## Reuse, Security and Lifecycle

- [ ] 没有样本 ID、测试 URL、本机路径、账号、secret、临时依赖或无法泛化的 workaround
- [ ] 已逐条审查负向迁移历史；不改变当前决策的表述已删除，确有必要的限制已改写为现在时边界而非旧方案叙述
- [ ] 已审计第三方内容、脚本、依赖、网络调用和权限
- [ ] `description`、正文、脚本默认值、输出格式与完成标准一致
- [ ] 团队或生产 Skill 已按需记录来源、兼容性、owner、回归条件和弃用方式
- [ ] 交付说明区分了证据、假设、已验证结论和剩余风险
