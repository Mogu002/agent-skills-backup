# Variable Causal Handbook

这份 reference 的用途是：**给使用 `sandbox-script-builder` 的 agent 一份可直接用于构建剧本的字段因果分类手册**，明确回答下面 5 个问题：

- 构建剧本时，哪些字段可以作为自变量去改
- 哪些字段只能作为因变量去观察
- 哪些字段属于状态变量 / 中间变量，不能直接当成剧本旋钮
- 每个字段的业务含义是什么、在系统里如何生成
- 从一个自变量出发，应该顺着哪条链去写底表异常

来源依据：学城文档 `特团四张底表字段自变量 vs 因变量`（contentId: `2757729264`）及当前《特团MVP业务沙盒 v0.1》约束。

## 对齐规则

- 本文件与 `SKILL.md`、`references/examples.md` 使用**完全同一套边界口径**。
- 若本文件与 `SKILL.md` 冲突，一律以 `SKILL.md` 为准。
- 本文件默认只服务于当前《特团MVP业务沙盒 v0.1》，不要把字段解释外推到其他业务底座。
- 本文件的核心价值是**帮 agent 把业务语言收敛成当前白名单内的真实字段**，不是鼓励 agent 发明新概念。

## 使用前先过边界闸门

正式查字段之前，先过一遍下面这些硬边界；只要命中对应板块，就**不能超出这些范围**。

### 1. 仿真时间边界

| 项目 | 当前限定值 | 使用规则 |
| --- | --- | --- |
| 仿真总天数 | `31天` | 含 `Day 0` 保护期，不要外推到更长周期 |
| 可见导出窗口 | `Day 1-30` | 所有阶段、切片、验证都必须落在这个窗口里 |
| 剧本生效天 | `Day 11` 起 | 冲击期默认从 `Day 11` 及之后开始 |

### 2. 城市与市场规模白名单

| 城市 | 初始档口数 | 初始用户池 | 城市系数 |
| --- | --- | --- | --- |
| 北京 | `40` | `80,000` | `1.2` |
| 上海 | `50` | `100,000` | `1.3` |
| 成都 | `45` | `90,000` | `1.1` |
| 武汉 | `35` | `70,000` | `0.95` |
| 郑州 | `30` | `60,000` | `0.85` |

全平台合计：`200` 个档口，`400,000` 用户池。

硬规则：

- 只能使用这 5 个城市，不要发明第六个城市。
- 只能在这 5 城内做城市切片，不要写“全国盘”“全省盘”或新的城市层级。
- 城市系数只能围绕当前白名单解释，不要新造城市档位体系。

### 3. 流量入口白名单

| 展示名称 | 枚举值 | 基线流量占比 |
| --- | --- | --- |
| 猜喜高卡 | `main_feeds_high_card` | `45%` |
| 猜喜低卡 | `main_feeds_low_card` | `20%` |
| 搜索 | `search` | `18%` |
| 大团购 | `group_purchase` | `12%` |
| 社群/BD地推 | `community_bd` | `5%` |

硬规则：

- 入口枚举只使用以上 5 个值。
- 不要创造 `feed_banner`、`short_video`、`coupon_center` 等当前模型里没有的入口。
- 如果用户说的是新流量来源，先尝试映射到这 5 个入口之一；映射不了，就收紧而不是扩写。

### 4. 商品类型白名单

- 每个档口的商品数：**指数分布采样，均值 `3.5`，上限 `8` 个商品/档口**
- 当前只支持 3 个品类：

| 品类名称 | 枚举值 | 档口内占比 | 团购价均值 | 划线价均值 | 拉新能力 | GTV贡献 |
| --- | --- | --- | --- | --- | --- | --- |
| 奶茶咖啡 | `milk_tea_coffee` | `40%` | `12` 元 | `22` 元 | `0.70` | `20%` |
| 西式快餐 | `western_fast` | `35%` | `22` 元 | `38` 元 | `0.50` | `30%` |
| 正餐 | `main_meal` | `25%` | `42` 元 | `68` 元 | `0.20` | `50%` |

硬规则：

- 只允许这 3 个品类，不要新增第四个品类。
- 如果用户说的是水果、生鲜、夜宵等概念，先看能否映射到现有 3 个品类；映射不了，就不要写进剧本正文。
- 所有价格、折扣、货盘结构讨论，都要围绕这 3 个品类展开。

### 5. 用户生命周期与用户属性白名单

当前生命周期只支持以下 3 类：

| 生命周期 | 枚举值 | 初始占比 | 日活跃率 |
| --- | --- | --- | --- |
| 新客 | `new_user` | `15%` | `12%` |
| 低频老客 | `low_freq` | `26.2%` | `8%` |
| 规律买用户 | `regular_buyer` | `58.8%` | `25%` |

当前用户属性只支持以下范围：

| 属性 | 当前限定值 | 使用规则 |
| --- | --- | --- |
| `_price_sensitivity` | `new_user=0.85`、`low_freq=0.60`、`regular_buyer=0.35`，并叠加高斯噪声 `σ=0.08` 后截断到 `[0,1]` | 用于解释价格敏感差异，不要衍生出新的原生用户标签 |
| `_preferred_category` | 从 `milk_tea_coffee / western_fast / main_meal` 中均匀随机选一个 | 不要新增第四种偏好品类 |
| `join_day` 历史偏移 | `0` 到 `-20` 天 | 用于分散新客 21 天存活期到期点，不要外推更长历史窗 |
| 新客存活期 | `21天` | 不要改写成 45 天、60 天等新机制 |
| 新客晋升条件 | `7天内有成单 -> 晋升 low_freq` | 生命周期改善要围绕已有规则展开 |
| 生命周期迁移概率 | `low_freq -> regular_buyer = 1.8%/天`；`regular_buyer -> low_freq = 0.8%/天` | 不要新增新状态或新跳转规则 |

硬规则：

- 只允许 `new_user / low_freq / regular_buyer` 这 3 类生命周期。
- 不要扩成学生、白领、宝妈、游客等新用户标签体系。
- 如果用户说“价格敏感人群”“奶茶偏好人群”，优先映射到 `_price_sensitivity` 或 `_preferred_category`，不要新增字段。

### 6. Agent 可见数据层白名单

当前 agent 可见层只使用这 4 张表：

- `dwd_transaction`
- `dws_user_daily`
- `dws_stall_daily`
- `dws_platform_daily`

GT / 内部机制字段只用于解释和验证，不默认写成题面主观察字段。

## Agent 怎么使用这份手册

写剧本时，默认按这个顺序使用：

1. 先过上面的边界闸门，确认时间、城市、入口、品类、生命周期、用户属性都没越界。
2. 再判断你要模拟的是哪一层冲击：需求、流量入口、价格折扣、补贴、供给、飞轮。
3. 到“自变量手册”里找**真实可控字段**，不要先发明业务词。
4. 到“因变量手册”里找同一条链上的**可观测字段**。
5. 如果需要解释机制，再补“状态 / GT 字段”，但不要默认把它们写进题面。
6. 最后把链路落成：`事件 -> 自变量 -> 状态变化 -> 因变量异常`。

默认禁忌：

- 不要把 `order_cnt`、`gmv`、`ctr_eff`、`cvr_eff`、`subsidy_roi`、`active_stall_cnt` 直接当自变量。
- 不要把 `_satisfaction`、`_momentum`、`_daily_revenue` 这种 GT 字段直接当 Agent 可见观察字段。
- 不要写“活跃衰减因子”“供给健康度指数”这种抽象词替代真实字段。
- 如果一句业务话无法映射到当前白名单字段，就先收紧，不要继续往后编。

## 字段角色的四层分类

### 1. 剧本自变量

指来自 `config`、`Scenario overrides`、初始分布或机制参数的**外生输入**。只有这一层字段，才是剧本里可以主动调整的量。

### 2. 观测因变量

指四张底表 Agent 可见层里能看到的事件结果、日汇总结果、效率指标。它们是剧本结果，不是剧本旋钮。

### 3. 状态变量 / 混合变量

指“初值由参数决定，但运行中又被系统规则持续更新”的字段，典型是用户 / 档口 `lifecycle`。这类字段适合写成**预期演化结果**，不适合直接当 override 去改。

### 4. GT / 内部机制字段

指为了理解因果机制和验证剧本而存在的内部变量，如 `_discount_rate`、`_total_subsidy`、`_daily_revenue`、`_satisfaction`、`_momentum`。默认只用于解释和验证，不作为题面的主观察字段。

额外说明：

- `day`、`city` 更接近时间轴 / 作用范围 / 分片维度，不是业务冲击主旋钮。
- `day` 的可见切片默认只在 `Day 1-30` 内讨论；正式剧本冲击默认从 `Day 11` 及之后开始。
- `city` 默认只使用北京 / 上海 / 成都 / 武汉 / 郑州。
- `user_id`、`stall_id`、`product_id` 这类字段是标识符，不参与业务因果分类。

## 剧本自变量手册

下面只列**有证据、可用于剧本设计**的真实参数名或机制参数。

### 一、需求活跃与用户生命周期

- `USER_DAILY_ACTIVE_RATE[lifecycle]`
  - 业务含义：控制不同生命周期用户的日活概率，是需求进入漏斗的第一道闸门。
  - 当前白名单：`lifecycle` 只能取 `new_user / low_freq / regular_buyer`，基线分别为 `0.12 / 0.08 / 0.25`。
  - 生效机制：在 Step 1 `activate_users_for_day()` 中，以 `USER_DAILY_ACTIVE_RATE[lifecycle] × 周末系数` 为概率抽样用户是否活跃。
  - 主要下游：`dws_user_daily.is_active`、`expose_cnt`、`click_cnt`、`order_cnt`、`gmv`；`dws_platform_daily.total_active_user_cnt`、`total_expose_cnt`、`total_order_cnt`、`total_gtv`。
  - 剧本用法：节假日出游、竞对分流、需求疲软、新客冷启动等场景都优先从这里落真实参数。

- `WEEKEND_TRAFFIC_BOOST`
  - 业务含义：周末 / 节假日自然流量抬升系数。
  - 生效机制：与 `USER_DAILY_ACTIVE_RATE` 相乘，同时提高部分用户触发第 2 次曝光的概率。
  - 主要下游：`is_active`、`expose_cnt`、`total_active_user_cnt`、`total_expose_cnt`。
  - 剧本用法：节假日天然高活跃背景建议优先用它塑造基线，不要用虚构“节日流量因子”。

- `NEW_USER_DAILY_INFLOW_RATE`
  - 业务含义：每日新客流入速度，是拉新主旋钮。
  - 基线锚点：当前基线为 `0.0093`。
  - 生效机制：每日新增量按 `NEW_USER_DAILY_INFLOW_RATE × (1 + momentum × 0.3)` 生成，再叠加新客自己的活跃率进入当日漏斗。
  - 主要下游：`dws_platform_daily.new_user_cnt`、`new_user_order_ratio`、`total_active_user_cnt`、`total_expose_cnt`。
  - 剧本用法：节日拉新、活动引流、外部曝光增长、自然新客下滑等场景优先使用。

- `INITIAL_USER_LIFECYCLE_DIST`
  - 业务含义：用户生命周期的初始结构分布。
  - 当前白名单：只允许 `new_user / low_freq / regular_buyer`，当前基线占比为 `15% / 26.2% / 58.8%`。
  - 生效机制：初始化时决定这 3 类用户的占比，之后运行期再由系统演化。
  - 主要下游：`dwd_transaction.user_lifecycle`、`dws_user_daily.lifecycle`、`dws_platform_daily.new_user_cnt`、`regular_buyer_cnt`。
  - 剧本用法：适合做“初始盘子不同”的基线构造，不适合拿来表达短周期冲击。

- `LOW_FREQ_TO_REGULAR_DAILY_PROB`
  - 业务含义：低频老客晋升为规律买的日概率。
  - 当前锚点：`1.8%/天`。
  - 生效机制：Step 5c 用户生命周期演化时执行。
  - 主要下游：`dws_user_daily.lifecycle`、`dws_platform_daily.regular_buyer_cnt`、长期 `total_order_cnt`、`total_gtv`。
  - 剧本用法：用于表达留存改善、习惯养成增强、节后沉淀变好。

- `REGULAR_TO_LOW_FREQ_DAILY_PROB`
  - 业务含义：规律买降级为低频老客的日概率。
  - 当前锚点：`0.8%/天`。
  - 生效机制：Step 5c 用户生命周期演化时执行。
  - 主要下游：`regular_buyer_cnt`、长期 `total_order_cnt`、`total_gtv`、`avg_order_value`。
  - 剧本用法：用于表达老客粘性下降、节后回落、竞对挖走高价值用户。

- `REGULAR_CHURN_DAILY_PROB`
  - 业务含义：规律买用户流失概率。
  - 生效机制：Step 5c 生命周期流失逻辑的一部分。
  - 主要下游：`regular_buyer_cnt`、`total_active_user_cnt`、`total_order_cnt`、`total_gtv`。
  - 剧本用法：适合做慢性老客流失型剧本，不适合用来表达瞬时流量冲击。

- `LOW_FREQ_CHURN_DAILY_PROB`
  - 业务含义：低频用户流失概率。
  - 生效机制：Step 5c 生命周期流失逻辑的一部分。
  - 主要下游：`dws_user_daily.lifecycle`、`dws_platform_daily.total_active_user_cnt`、`new_user_cnt` 后续承压。
  - 剧本用法：适合表达低频池萎缩、节日后自然流失加速。

### 二、流量入口与点击阶段

- `ENTRANCE_TRAFFIC_WEIGHT[entrance]`
  - 业务含义：不同入口的曝光权重分配。
  - 当前白名单：`entrance` 只能取 `main_feeds_high_card / main_feeds_low_card / search / group_purchase / community_bd`，基线占比分别为 `45% / 20% / 18% / 12% / 5%`。
  - 生效机制：Stage 1 用 `ENTRANCE_TRAFFIC_WEIGHT × city_coeff` 做加权抽样，决定每次曝光落在哪个入口。
  - 主要下游：`dwd_transaction.entrance` 分布、`dws_platform_daily.total_expose_cnt`、`total_click_cnt`、`ctr_eff`。
  - 剧本用法：用于表达搜索弱化、社群放量、主 feed 调权、节日期间入口结构变化。

- `ENTRANCE_BASE_CTR[entrance]`
  - 业务含义：入口级基准点击率。
  - 当前白名单：`entrance` 仍然只能是上述 5 个入口枚举。
  - 生效机制：进入 `CTR_eff = base_ctr[entrance] × discount_factor × subsidy_factor × noise`。
  - 主要下游：`dwd_transaction.is_clicked`、`dws_user_daily.click_cnt`、`dws_platform_daily.total_click_cnt`、`ctr_eff`。
  - 剧本用法：用于表达入口素材质量变化、节日主题入口更吸睛 / 更失效。

- `CITY_TIER_COEFFICIENT`
  - 业务含义：城市层流量系数，决定各城市入口权重放大或缩小。
  - 当前白名单：只能围绕北京 `1.2`、上海 `1.3`、成都 `1.1`、武汉 `0.95`、郑州 `0.85` 解释。
  - 生效机制：参与 `ENTRANCE_TRAFFIC_WEIGHT × city_coeff`。
  - 主要下游：城市切片下的 `entrance` 结构和曝光量。
  - 剧本用法：更适合作为作用范围 / 城市差异背景，不建议作为默认主冲击参数。

### 三、价格、折扣与成交阶段

- `CATEGORY_PROFILE[category]["avg_price"]`
  - 业务含义：品类平均成交价基线。
  - 当前白名单：`category` 只能取 `milk_tea_coffee / western_fast / main_meal`，对应基线分别约为 `12 / 22 / 42` 元。
  - 生效机制：商品初始化时按 `avg_price × rng.uniform(0.85, 1.15)` 生成 `sale_price`。
  - 主要下游：`dwd_transaction.sale_price`、`dws_user_daily.gmv`、`dws_stall_daily.gmv`、`dws_platform_daily.total_gtv`、`avg_order_value`。
  - 剧本用法：需要表达节日货盘提价、主餐占比提升、低价奶茶放量时优先使用项目内已有价格参数。

- `CATEGORY_PROFILE[category]["avg_market_price"]`
  - 业务含义：品类市场价基线。
  - 当前白名单：3 个品类对应基线分别约为 `22 / 38 / 68` 元。
  - 生效机制：与 `sale_price` 一起决定 `_discount_rate = sale_price / market_price`。
  - 主要下游：`_discount_rate`、`discount_factor`、`CTR_eff`、`CVR_eff`。
  - 剧本用法：用于解释折扣力度变化来源；默认不是 Agent 题面的直接观测字段。

- `BASELINE_DISCOUNT_RATE`
  - 业务含义：系统对“够不够便宜”的基准折扣线。
  - 当前锚点：`0.60`。
  - 生效机制：当 `discount_rate < BASELINE_DISCOUNT_RATE` 时，`discount_factor` 对 CTR 有加成；高于基准线时，价格惩罚在 CVR 阶段更容易触发。
  - 主要下游：`is_clicked`、`is_ordered`、`ctr_eff`、`cvr_eff`。
  - 剧本用法：用于表达系统整体价格吸引力阈值变化，慎用；更常见的是改品类价格参数。

- `DISCOUNT_CVR_ELASTICITY`
  - 业务含义：价格惩罚对成交转化的敏感度。
  - 生效机制：进入 `price_penalty = price_sensitivity × max(0, discount_rate - 0.60) × DISCOUNT_CVR_ELASTICITY`。
  - 主要下游：`dwd_transaction.is_ordered`、`dws_user_daily.order_cnt`、`dws_platform_daily.cvr_eff`、`total_order_cnt`。
  - 剧本用法：用于表达用户对贵价商品更敏感、节日期间比价增强等场景。

- `USER_PRICE_SENSITIVITY[lifecycle]`
  - 业务含义：不同生命周期用户的价格敏感底座。
  - 当前白名单：`lifecycle` 只能取 `new_user / low_freq / regular_buyer`，对应基线分别为 `0.85 / 0.60 / 0.35`。
  - 生效机制：初始化时按 `USER_PRICE_SENSITIVITY[lifecycle] + rng.gauss(0, 0.08)` 生成 `_price_sensitivity`，终身固定。
  - 主要下游：CVR 阶段的价格惩罚强度，最终影响 `order_cnt`、`cvr_eff`、`subsidy_roi`。
  - 剧本用法：更像人群画像参数，默认不直接写进业务剧本；只有用户明确要做机制实验时才调整。

### 四、补贴策略

- `B_SUBSIDY_BASE_RATE`
  - 业务含义：商家立减补贴基准率。
  - 基线锚点：当前基线约为 `0.18`。
  - 生效机制：商品初始化时参与 `_b_subsidy = sale_price × B_SUBSIDY_BASE_RATE × noise`，并通过 `subsidy_scale` 间接影响 CTR / CVR。
  - 主要下游：`_b_subsidy`、`_total_subsidy`、`dws_user_daily.total_subsidy`、`dws_platform_daily.total_subsidy`、`subsidy_roi`、`_daily_revenue`。
  - 剧本用法：用于表达 B 补增强 / 收缩，以及商家收益结构变化。

- `C_SUBSIDY_BASE_RATE`
  - 业务含义：用户券补贴基准率。
  - 基线锚点：当前基线约为 `0.08`。
  - 生效机制：参与 `_c_subsidy` 计算，并通过 `subsidy_scale` 直接影响 CTR / CVR。
  - 主要下游：`_c_subsidy`、`total_subsidy`、`ctr_eff`、`cvr_eff`、`subsidy_roi`、`new_user_order_ratio`。
  - 剧本用法：适合表达新客刺激强弱、节日拉新补贴、竞对补贴战应对。

- `MT_SUBSIDY_BASE_RATE`
  - 业务含义：平台侧补贴基准率。
  - 生效机制：参与 `_mt_subsidy` 计算，并进入 `_total_subsidy`。
  - 主要下游：`dws_platform_daily.total_subsidy`、`subsidy_roi`、`_daily_revenue`。
  - 剧本用法：适合表达平台兜底、节日保供补贴、ROI 再平衡。

### 五、供给与飞轮

- `STALL_EXTERNAL_PRESSURE`
  - 业务含义：供给侧外部压力，如节日返乡、竞对挖档口、经营受阻。
  - 生效机制：在 `_satisfaction` 计算的最后一步直接扣减，形成供给负反馈。
  - 主要下游：`dws_stall_daily.lifecycle`、`dws_platform_daily.active_stall_cnt`、`total_online_prod_cnt`、`cvr_eff`、`total_gtv`、`new_user_cnt`。
  - 剧本用法：供给侧冲击首选真实参数，不要发明“供给崩盘系数”。

- `STALL_CHURN_CONSECUTIVE_DAYS`
  - 业务含义：档口从低满意度进入 `churned` 的连续风险阈值天数。
  - 基线锚点：当前默认门槛为 `8` 天；供给冲击剧本可收紧到更短窗口，但仍要围绕现有机制解释。
  - 生效机制：当 `_satisfaction < 0.25` 时累计风险天数；达到阈值后 `lifecycle -> churned`。
  - 主要下游：`dws_stall_daily.lifecycle`、`active_stall_cnt`、`total_online_prod_cnt`。
  - 剧本用法：适合表达“节日期间更脆弱，几天扛不住就流失”的场景。

- `MOMENTUM_ALPHA`
  - 业务含义：平台动量对当日档口满意度的吸收速度。
  - 生效机制：`_momentum = MOMENTUM_ALPHA × _avg_stall_satisfaction + (1 - MOMENTUM_ALPHA) × 昨日momentum`。
  - 主要下游：`NEW_USER_DAILY_INFLOW_RATE × (1 + momentum × 0.3)` 的放大或抑制。
  - 剧本用法：这是系统机制参数，不建议作为默认业务剧本旋钮；更适合机制实验。

## 因变量手册：Agent 可见字段该怎么理解和使用

### 一、`dwd_transaction`：事件层 / 漏斗层

- `entrance`
  - 业务含义：本次触达来自哪个流量入口。
  - 当前白名单：只会出现 `main_feeds_high_card / main_feeds_low_card / search / group_purchase / community_bd`。
  - 生成机制：Stage 1 按 `ENTRANCE_TRAFFIC_WEIGHT × city_coeff` 加权抽样。
  - 剧本用法：观察入口结构是否按预期迁移，是“入口冲击是否真正落地”的第一观察位。

- `user_lifecycle`
  - 业务含义：本次曝光发生时用户所处生命周期。
  - 当前白名单：只会出现 `new_user / low_freq / regular_buyer`。
  - 生成机制：初始由 `INITIAL_USER_LIFECYCLE_DIST` 决定，之后由 Step 5c 每日演化；事件层记录的是当时快照。
  - 剧本用法：它是状态变量，不是直接旋钮；适合解释“哪个人群被触达 / 成交”。

- `is_clicked`
  - 业务含义：该次曝光是否发生点击。
  - 生成机制：Stage 2 用 `CTR_eff` 抽样；`CTR_eff = base_ctr[entrance] × discount_factor × subsidy_factor × noise`。
  - 剧本用法：入口流量、折扣吸引力、补贴刺激是否影响点击，最终都先看这里。

- `is_ordered`
  - 业务含义：该次点击后是否最终成单。
  - 生成机制：仅当 `is_clicked=True` 时进入 Stage 3；用 `CVR_eff` 抽样，受生命周期加成、价格惩罚、补贴因子等共同影响。
  - 剧本用法：这是漏斗终态事件字段，是 `order_cnt` / `total_order_cnt` 的最底层来源。

- `sale_price`
  - 业务含义：商品实际成交价 / 标价。
  - 生成机制：商品初始化时按白名单品类平均价加噪声生成，当前版本固定不变；未成单记录也保留该价格。
  - 剧本用法：观察价格结构、解释折扣率分布、支撑 `avg_order_value` 变化。

提示：

- `record_id`、`user_id`、`stall_id`、`product_id`、`day`、`city` 只用于切片，不用写成异常主语。
- `city` 的切片范围仍然只限北京 / 上海 / 成都 / 武汉 / 郑州。

### 二、`dws_user_daily`：用户日汇总层

- `lifecycle`
  - 业务含义：用户当天的生命周期状态。
  - 生成机制：初始由 `INITIAL_USER_LIFECYCLE_DIST` 决定，之后由晋升 / 降级 / 流失规则更新。
  - 剧本用法：适合写成结构性结果，如“规律买占比回落”“新客池扩张”，不直接当旋钮。

- `is_active`
  - 业务含义：用户当天是否进入漏斗。
  - 生成机制：由 `USER_DAILY_ACTIVE_RATE[lifecycle] × 周末系数` 抽样决定。
  - 剧本用法：需求侧冲击最直接的用户层观察字段。

- `expose_cnt`
  - 业务含义：用户当天被推入漏斗的次数。
  - 生成机制：统计当天 `TransactionRecord` 条数；通常 1 次，周末部分用户会触发第 2 次曝光。
  - 剧本用法：区分“活跃下降”与“活跃不变但人均曝光下降”。

- `click_cnt`
  - 业务含义：用户当天点击次数。
  - 生成机制：统计 `is_clicked=True` 的记录数。
  - 剧本用法：观察点击兴趣变化，常与 `expose_cnt` 联动判断 CTR 变动原因。

- `order_cnt`
  - 业务含义：用户当天成单次数。
  - 生成机制：统计 `is_ordered=True` 的记录数。
  - 剧本用法：用户行为结果核心指标，适合承接需求 / 价格 / 补贴 / 供给冲击。

- `gmv`
  - 业务含义：用户当天贡献的 GMV。
  - 生成机制：累加该用户所有成单记录的 `sale_price`。
  - 剧本用法：适合写用户价值变化，不要把它当成参数去改。

- `total_subsidy`
  - 业务含义：该用户当天消耗的平台补贴总额。
  - 生成机制：累加所有成单记录的 `_total_subsidy`。
  - 剧本用法：这是 Agent 可见层里观察补贴规模的关键字段；如果要看用户侧补贴是否真被打出去，优先看它。

### 三、`dws_stall_daily`：供给日汇总层

- `lifecycle`
  - 业务含义：档口当前状态，`active / at_risk / churned`。
  - 生成机制：`_satisfaction < 0.25` 时累计风险天数；达到 2 天进入 `at_risk`，达到 `STALL_CHURN_CONSECUTIVE_DAYS` 后进入 `churned`；新档口有 3 天保护期。
  - 剧本用法：这是供给侧最核心的可见状态字段，适合写“档口风险上升 / 流失加快”。

- `online_prod_cnt`
  - 业务含义：档口当天在线商品数。
  - 生成机制：统计 `is_online=True` 的商品数。
  - 剧本用法：观察供给商品池是否缩小，它是 `cvr_eff` 变化的重要上游。

- `order_cnt`
  - 业务含义：档口当天接单量。
  - 生成机制：统计 `stall_id` 对应的成单记录数。
  - 剧本用法：适合看供给损失是“无曝光”“有曝光无成交”还是“整体订单缩水”。

- `gmv`
  - 业务含义：档口当天产生的 GMV。
  - 生成机制：累加该档口成单记录的 `sale_price`。
  - 剧本用法：供给侧收入规模的可见近似指标。

关键边界：

- **Agent 可见层没有可直接使用的 `dws_stall_daily.revenue` 字段。**
- 如果你想表达“档口真实到账收入”，默认用 `gmv` 做可见观察，用 GT `_daily_revenue` 做机制解释或验证。

### 四、`dws_platform_daily`：平台日汇总层

- `total_stall_cnt`
  - 业务含义：当天仍产生 `StallDailyRow` 的档口数。
  - 生成机制：统计当日 `stall_rows` 行数；`churned` 档口当天起不再生成记录。
  - 剧本用法：适合观察供给池总体规模。

- `active_stall_cnt`
  - 业务含义：状态仍为 `active` 的档口数，是供给活力核心指标。
  - 生成机制：在平台聚合时统计 `lifecycle == "active"` 的档口数。
  - 剧本用法：供给侧冲击的主观察字段，不要把它当自变量。

- `total_online_prod_cnt`
  - 业务含义：全平台在线商品池大小。
  - 生成机制：汇总所有 `StallDailyRow.online_prod_cnt`。
  - 剧本用法：用来判断供给冲击是否进一步传导到匹配效率和 CVR。

- `total_active_user_cnt`
  - 业务含义：全平台当日活跃用户数。
  - 生成机制：统计所有 `is_active_today=True` 的用户数。
  - 剧本用法：需求侧总盘子主观察字段。

- `new_user_cnt`
  - 业务含义：当日活跃用户中属于 `new_user` 的人数。
  - 生成机制：由 `NEW_USER_DAILY_INFLOW_RATE × (1 + momentum × 0.3)` 生成新增，再叠加新客活跃概率。
  - 剧本用法：拉新类剧本优先看这个，不要只看 `total_active_user_cnt`。

- `regular_buyer_cnt`
  - 业务含义：当日活跃用户中属于 `regular_buyer` 的人数。
  - 生成机制：来自用户生命周期长期晋升 / 降级 / 流失后的结果。
  - 剧本用法：判断高价值用户是否被留住，是留存健康度关键字段。

- `total_expose_cnt`
  - 业务含义：全平台总曝光次数。
  - 生成机制：`len(records)`。
  - 剧本用法：入口调权、活跃变化、周末加曝光都会先反映到这里。

- `total_click_cnt`
  - 业务含义：全平台总点击次数。
  - 生成机制：`sum(1 for r in records if r.is_clicked)`。
  - 剧本用法：与 `total_expose_cnt` 结合判断点击阶段是否失效。

- `total_order_cnt`
  - 业务含义：全平台总成单笔数，是业务量最核心指标。
  - 生成机制：`sum(1 for r in records if r.is_ordered)`。
  - 剧本用法：几乎所有剧本最终都要落到这里，但它永远是结果字段。

- `total_gtv`
  - 业务含义：全平台总 GTV。
  - 生成机制：累加所有成单记录的 `sale_price`。
  - 剧本用法：营收规模主观察字段，适合与 `total_order_cnt`、`avg_order_value` 联合看量价结构。

- `total_subsidy`
  - 业务含义：全平台补贴总消耗。
  - 生成机制：汇总 B / C / MT 三类补贴。
  - 剧本用法：补贴剧本和 ROI 剧本必看字段。

- `ctr_eff`
  - 业务含义：全平台有效点击率。
  - 生成机制：`total_click_cnt / total_expose_cnt`。
  - 剧本用法：入口质量、价格吸引力、补贴刺激是否影响点击效率，看这里。

- `cvr_eff`
  - 业务含义：全平台有效成交转化率。
  - 生成机制：`total_order_cnt / total_click_cnt`。
  - 剧本用法：价格、供给匹配、生命周期结构、补贴强弱最终都会汇到这里。

- `overall_convert_rate`
  - 业务含义：端到端整体转化率。
  - 生成机制：`total_order_cnt / total_expose_cnt`，也可理解为 `ctr_eff × cvr_eff`。
  - 剧本用法：用于看全链路效率，但不适合替代分阶段诊断。

- `subsidy_roi`
  - 业务含义：每花 1 元补贴撬动的 GTV。
  - 生成机制：`total_gtv / total_subsidy`。
  - 剧本用法：补贴效率的核心结果字段；只能观察不能直接设值。

- `new_user_order_ratio`
  - 业务含义：新客成单占总成单的比例。
  - 生成机制：`is_ordered=True` 且 `user_lifecycle == "new_user"` 的记录数除以 `total_order_cnt`。
  - 剧本用法：用于判断活动是在拉新，还是只在存量用户里挪单。

- `avg_order_value`
  - 业务含义：平均客单价。
  - 生成机制：`total_gtv / total_order_cnt`。
  - 剧本用法：用于判断 GMV 变化来自“量”还是“价 / 货盘结构”。

## GT / 内部机制字段手册

这类字段默认不写成题面主观察对象，但 agent 需要知道它们，否则容易把链路写断。

- `_discount_rate`
  - 含义：商品折扣率，`sale_price / market_price`。
  - 作用：低于 `BASELINE_DISCOUNT_RATE(0.60)` 时提升 CTR；高于 `0.60` 时触发价格惩罚，压低 CVR。
  - 用法：用于解释“为什么看起来价格只涨了一点，CVR 却掉得更快”。

- `_price_sensitivity`
  - 含义：用户价格敏感度，按生命周期初始化后终身固定。
  - 当前白名单：其底座只能来自 `new_user=0.85 / low_freq=0.60 / regular_buyer=0.35`，再叠加高斯噪声 `σ=0.08` 截断到 `[0,1]`。
  - 作用：决定价格惩罚强度。
  - 用法：用于解释“同样提价，新客比规律买跌得更厉害”。

- `_preferred_category`
  - 含义：用户默认偏好品类。
  - 当前白名单：只会从 `milk_tea_coffee / western_fast / main_meal` 中均匀随机选取。
  - 作用：帮助解释品类偏好与成交结构，不是默认剧本旋钮。
  - 用法：用于解释“为什么某类用户更偏向奶茶咖啡 / 正餐”，不要把它扩成新的偏好标签体系。

- `join_day`
  - 含义：用户进入系统的历史天偏移。
  - 当前白名单：初始新客的 `join_day` 随机偏移 `0` 到 `-20` 天，用于分散 21 天存活期到期点。
  - 作用：影响新客存活期触发时点。
  - 用法：用于解释“为什么新客流失不是同一天一起发生”，不要把它当成新的时间机制去扩写。

- `_b_subsidy` / `_c_subsidy` / `_mt_subsidy` / `_total_subsidy`
  - 含义：单笔订单的补贴构成及总补贴。
  - 作用：共同决定可见层 `total_subsidy`，并通过 `subsidy_scale` 影响点击和成交。
  - 用法：用于解释补贴结构，不直接当题面字段。

- `_daily_revenue`
  - 含义：档口当日实际到账收入，`Σ(sale_price - _total_subsidy)`。
  - 作用：是 `_satisfaction` 的直接输入。
  - 用法：如果要解释供给为何流失，这个字段比单看 `gmv` 更接近真实机制。

- `_satisfaction`
  - 含义：档口满意度，是供给侧飞轮的核心状态。
  - 作用：由 `_daily_revenue` 经分段线性映射后，再减 `STALL_EXTERNAL_PRESSURE`；低于 `0.25` 会推动风险天数累积。
  - 用法：用于验证供给剧本是否真的触发了风险和流失。

- `consecutive_risk_days`
  - 含义：档口连续低满意度天数。
  - 作用：达到阈值后推动 `lifecycle` 进入 `at_risk / churned`。
  - 用法：用于解释“为什么供给不是当天崩，而是几天后才断崖”。

- `_avg_stall_satisfaction`
  - 含义：全平台档口平均满意度。
  - 作用：进入 `_momentum` 更新。
  - 用法：用于解释平台供给健康的全局信号。

- `_momentum`
  - 含义：平台动量，是正 / 负飞轮的核心传导变量。
  - 作用：用 EMA 吸收 `_avg_stall_satisfaction`，再反过来放大或压制新客流入。
  - 用法：用于解释“为什么供给冲击会二次伤害拉新”。

## 自变量和因变量之间的默认对应关系

写剧本时，优先按下面这些因果链配字段，而不是随手拼。

- 需求活跃链
  - `USER_DAILY_ACTIVE_RATE` / `WEEKEND_TRAFFIC_BOOST`
  - `-> dws_user_daily.is_active / expose_cnt`
  - `-> dws_platform_daily.total_active_user_cnt / total_expose_cnt`
  - `-> total_order_cnt / total_gtv`

- 拉新链
  - `NEW_USER_DAILY_INFLOW_RATE`
  - `-> new_user 新增规模`
  - `-> dws_platform_daily.new_user_cnt`
  - `-> new_user_order_ratio / total_expose_cnt / total_order_cnt`

- 入口流量链
  - `ENTRANCE_TRAFFIC_WEIGHT[entrance]`
  - `-> dwd_transaction.entrance 分布`
  - `-> total_expose_cnt / total_click_cnt`
  - `-> ctr_eff / total_order_cnt`

- 点击效率链
  - `ENTRANCE_BASE_CTR[entrance]` + 折扣 / 补贴吸引力
  - `-> dwd_transaction.is_clicked`
  - `-> dws_user_daily.click_cnt`
  - `-> dws_platform_daily.total_click_cnt / ctr_eff`

- 成交转化链
  - `DISCOUNT_CVR_ELASTICITY` / `USER_PRICE_SENSITIVITY` / 生命周期结构 / 补贴因子
  - `-> dwd_transaction.is_ordered`
  - `-> dws_user_daily.order_cnt / gmv`
  - `-> total_order_cnt / cvr_eff / total_gtv`

- 补贴效率链
  - `B_SUBSIDY_BASE_RATE` / `C_SUBSIDY_BASE_RATE` / `MT_SUBSIDY_BASE_RATE`
  - `-> _total_subsidy`
  - `-> dws_user_daily.total_subsidy / dws_platform_daily.total_subsidy`
  - `-> subsidy_roi`

- 供给飞轮链
  - `STALL_EXTERNAL_PRESSURE` / `STALL_CHURN_CONSECUTIVE_DAYS`
  - `-> _daily_revenue / _satisfaction / consecutive_risk_days`
  - `-> dws_stall_daily.lifecycle / online_prod_cnt`
  - `-> active_stall_cnt / total_online_prod_cnt / cvr_eff / total_gtv`
  - `-> _momentum`
  - `-> new_user_cnt`

## 写剧本时的硬规则

- 先定自变量，再定因变量；不要从结果字段反推“我就把它改掉”。
- 默认优先写真实 `config` / `overrides` 字段名，不要自造“业务因子”。
- `lifecycle` 是状态变量：可以写成结构结果，不要直接把可见层 `lifecycle` 当 override。
- 供给侧如果要写“收益受损”，默认题面观察写 `gmv`、`lifecycle`、`active_stall_cnt`、`total_online_prod_cnt`；机制验证再看 `_daily_revenue` / `_satisfaction`。
- 补贴侧如果要写“补贴打得更重 / 更轻”，默认观察写 `total_subsidy`、`subsidy_roi`、`ctr_eff`、`cvr_eff`、`new_user_order_ratio`；不要直接把 ROI 当参数。
- 节假日剧本优先同时考虑：`WEEKEND_TRAFFIC_BOOST`、`NEW_USER_DAILY_INFLOW_RATE`、入口流量结构、供给压力四类字段，而不是只改一个总量参数。
- 不要新增第六个城市、第四个品类、新生命周期枚举、新入口枚举或新的用户标签体系。
- 不要把当前模型里没有的表和指标写进字段手册或剧本，例如司机表、乘客表、等待时长、取消率等未建模概念。
- 如果一句业务话无法映射到本文件中的真实字段名，就先回到白名单边界重新收敛，不要继续扩写。

## 最后只记住这三句话

- **剧本里能主动改的，只有参数层和机制层字段。**
- **底表里的 `order_cnt`、`gmv`、`ctr_eff`、`subsidy_roi`、`active_stall_cnt` 永远先当结果看。**
- **如果一句业务话无法落到真实字段名，就先回到这份手册补字段，不要继续往后写。**
