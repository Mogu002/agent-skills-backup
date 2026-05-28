# 设计手册 — 踩坑经验详解

> 本文件是 SKILL.md 中"关键经验速查"的展开版本，在需要排查具体问题时阅读。

---

## 经验 1：base_config 与运行时 config 必须严格分离

**现象**：剧本覆盖参数后，基准计算也被污染，归因结果混乱。

**根因**：竞对价格 = 基准价格 × 比率。若剧本同时覆盖"比率"和"基准价格"，价格比较的参照系已变，无法分辨是"竞对降价"还是"基准涨价"。

**解法**：
```python
self.base_config = copy.deepcopy(original_config)  # 永久基准，绝不随剧本变化
self.config = copy.deepcopy(original_config)        # 运行时配置，随剧本动态覆盖

# 基准参照系永远用 base_config
base_price = calculate_from(self.base_config)
competitor_price = base_price * self.config.COMPETITOR_PRICE_RATIO
```

---

## 经验 2：剧本生效后必须同步所有子模块的 config 引用

**现象**：主模拟器 config 已更新，但 decision_model、ecosystem 等仍指向旧对象，剧本效果部分失效。

**解法**：每次更新 config 后，调用统一同步方法：
```python
def _update_modules_config(self):
    self.decision_model.config = self.config
    self.ecosystem.config = self.config
    self.ecosystem.population_manager.config = self.config
    self.ecosystem.metrics_calculator.config = self.config
    self.ecosystem.supply_demand_model.config = self.config
    self.ecosystem.retention_model.config = self.config
    self.supply_pool.config = self.config
    # EntityGenerator 仅初始化时用，无需更新
```

---

## 经验 3：交易级覆盖必须用深拷贝临时配置

**现象**：北京早高峰新用户补贴的剧本覆盖，把同批次其他订单的参数也改了。

**根因**：直接修改了全局 config，而不是订单副本。

**解法**：
```python
order_config = copy.deepcopy(self.config)
if self.scenario_manager:
    overrides, modes = self.scenario_manager.get_transaction_overrides(context)
    apply_overrides(order_config, overrides, modes)
    original_config = self.config
    self.config = order_config
    self.decision_model.config = order_config

# ... 执行决策漏斗 ...

if self.scenario_manager:
    self.config = original_config
    self.decision_model.config = original_config
```

---

## 经验 4：供需比的单位在设计时就固化，不能混用

**现象**：供需比"平衡点"标定出错，用"人数比"和"时长/单量比"阈值差一个数量级。

**解法**：在 `decision.py` 开头写明公式和单位，所有阈值都在该单位下标定：
```python
# 供需比定义：
# supply = 在线供给主体数 × 平均在线时长（小时）
# demand = 本时段实际提单数（笔）
# supply_demand_ratio = supply / demand  单位：小时/笔
#
# 平衡点 ≈ 0.25（等待时间正常）
# 临界值 < 0.10（严重短缺，等待时间急剧上升）
```

---

## 经验 5：需求侧分层流失率必须相互独立

**现象**：新老用户共用同一套流失参数，补贴剧本无法区分"拉新"和"留老"，归因题无法设计。

**解法**：新老用户（及不同敏感度分层）必须有独立的系数和上限：
```python
# 新用户专属
NEW_DEMAND_PRICE_RATIO_THRESHOLD = 1.01
NEW_DEMAND_PRICE_CHURN_PROB_MAX = 0.6

# 老用户按敏感度三分层
PRICE_CHURN_PROB_MAX_HIGH = 0.45
PRICE_CHURN_PROB_MAX_MEDIUM = 0.25
PRICE_CHURN_PROB_MAX_LOW = 0.10
```

---

## 经验 6：第1天必须设保护期

**现象**：初始化时随机扰动导致满意度偏低，立即触发大量不合理人口流失，污染第2天起的数据。

**解法**：
```python
def update_population(self, region, metrics, day=None, ...):
    if day == 0:
        return  # 第1天保护期：不触发任何人口变化
    # 正常流失/激活逻辑...
```

---

## 经验 7：第1天排除与题目口径偏移必须显式约定

**现象**：系统内部第11天生效的剧本，题目里写"第10天生效"，答案系统性错位。

**约定模板（必须写入项目文档）**：
```
⚠️ 口径换算约定：
- 模拟系统运行 N 天，导出时排除第1天（初始化扰动日）
- 最终数据对应系统内部第 2~N 天，对外呈现为"第 1~(N-1) 天"
- 换算公式：题目天数 = 系统天数 - 1
- 剧本在系统第 11-20 天生效 → 题目描述为"第 10-19 天生效"
```

---

## 经验 8：均衡态参数标定必须先于剧本开发

**现象**：先开发剧本，再标定基准参数，两者反复互相干扰，最终都不准确。

**正确顺序**：
1. 关闭所有剧本，运行纯均衡态模拟
2. 验证成交转化率、留存率、活跃率都在合理区间
3. **固化**基准参数（提交到版本控制）
4. 再开发剧本层

---

## 飞轮效应建模要点

### 满意度均衡区间设计

```
目标：无剧本时满意度稳定在 0.5（中性值）
原因：满意度冲到顶（1.0）后，剧本负面冲击无处体现
```

分段线性映射示例（供给侧收益指标 → 满意度）：
```
IPH < 低临界值  → 满意度 [0, 0.3]  线性映射
IPH ∈ 均衡区间  → 满意度 [0.4, 0.6] 线性映射（基准工作在此区间）
IPH > 高临界值  → 满意度 [0.7, 1.0] 线性映射
```

### 平台动量（指数移动平均）

```python
momentum = alpha * today_avg_satisfaction + (1 - alpha) * yesterday_momentum
# alpha = 0.2~0.3，防止单日异常剧烈影响全局，体现业务惯性
```

---

## 三遍扫描详解（仅即时匹配型业务）

### 为什么需要三遍

循环依赖链：`提单数 → 供需比 → 价格 → 提单数`

### 三遍内容

| 遍 | 操作 | 输出 |
|----|------|------|
| 第一遍 | 生成所有需求意向（仅生成"计划"，不做任何判断） | 意向列表 |
| 第二遍 | 轻量价格判断（仅阶段1），按{地域×时段}统计估算提单数 | 供需比 |
| 第三遍 | 带入真实供需比，执行完整决策漏斗（含交易级剧本覆盖） | 最终订单记录 |

### 关键约束

- 第一遍不消耗随机数（或保存随机种子），否则第三遍结果与第一遍不一致
- 第三遍的交易级剧本覆盖使用深拷贝临时配置（见经验3）
- 供需比计算必须按{地域×时段}分组，不能全局汇总
