# Shared Checklist

在完成 unified skill 的任一路径后，统一检查以下内容：

- `name` 合法，并且与 skill 目录名一致
- `description` 具体、简洁、以触发和用户意图为中心
- `SKILL.md` 主文件保持聚焦，不承载过多细节
- 重要 gotchas 在主文件中可见，而不是全部藏进可选引用
- references 最好一层直达，避免深层导航
- support files 只在有明确作用时存在，不为“显得完整”而创建
- scripts 如果存在，应优先采用非交互接口
- 最终 skill 必须提供一个清晰默认路径，而不是平铺很多等权选项
- 没有明显的泛化填充语句或模板废话

## Minimal Validation Loop

交付前至少完成一轮最小验证闭环：

- 用 3 条代表性说法检查 `description` 是否会正确命中
- 假设另一个 agent 只读 `SKILL.md`，确认它知道第一步、默认路径和停止扩写的边界
- 用 1 个代表性请求做 dry-run；若环境允许，再做前向测试
- 若出现误触发、默认路径不清、support files 冗余或内容过泛，先收紧再交付
