# SQL 查询模板清单（specialteam）

本文件用于补充 `specialteam/SKILL.md` 中的 Datasette 超时处理路径。

适用场景：
- 通过 `data_url` 查询特团四张表时出现 `SQL Interrupted`
- 需要先探索剧本，再把候选结论补齐为可落题的验证证据
- 需要决定什么时候继续下钻、什么时候停止使用 `dwd_transaction`

## 先区分两类查询

### 1. 探索查询

目的：识别剧本主线、阶段窗口、候选对象、候选结论。

特点：
- 允许只查部分窗口或部分对象
- 允许用较小查询快速探路
- 结果只能用于形成候选 `reference_answer` / 候选 `question`
- 不能直接作为最终题面与 rubrics 的唯一证据

### 2. 验证查询

目的：验证候选题面是否真的存在唯一标准答案。

特点：
- 必须覆盖候选题面所依赖的完整比较范围
- 允许把全集拆成多条小 SQL 再在 agent 内部汇总
- 只要窗口、对象集合、比较粒度完整，拆查结果仍可作为正式出题依据

## 默认查询路径

1. 先查 `dws_platform_daily`，识别异动开始日和阶段窗口
2. 再查 `dws_user_daily` 或 `dws_stall_daily`，固定一个主粒度做候选扫描
3. 基于候选结论反推候选题面
4. 再按候选题面的比较范围补齐验证查询
5. 只有 DWS 无法支撑唯一答案时，才进入 `dwd_transaction`

## 安全改写规则

- 先过滤再聚合：优先把 `day`、`city`、`lifecycle` 写进 `WHERE`
- 一次只保留一种主要粒度：`day`、`city`、`lifecycle`、`stall`、`entrance` 只选一种为主
- 先按时间拆，再按对象拆：优先拆 `1-10 / 11-20 / 21-30`，必要时再拆 `11-15 / 16-20`
- 只取当前判断需要的字段：不要顺手把所有指标一起查出
- 不追求一条 SQL 出答案：允许多条小查询拼成完整比较集
- 如果 `dwd_transaction` 在单天 + 单城市 + 单生命周期 + 单分组维度下仍超时，默认放弃入口/品类题，回退到 DWS 能支撑的题型

## 模板 A：平台日表全量读取（探索阶段第一跳）

用途：识别异动开始日、阶段窗口、平台整体方向。

```sql
SELECT
  day,
  total_active_user_cnt,
  new_user_cnt,
  total_subsidy,
  subsidy_roi,
  ctr_eff,
  cvr_eff,
  new_user_order_ratio,
  avg_order_value
FROM dws_platform_daily
ORDER BY day
```

适合用于：
- 判断“从第几天开始”
- 判断“更像新客问题 / 补贴问题 / 供给问题”
- 给后续下钻确定阶段窗口

## 模板 B：按城市做候选扫描（DWS，探索阶段）

用途：在固定窗口和固定人群下，快速找候选城市。

```sql
SELECT
  city,
  COUNT(*) AS user_cnt,
  SUM(order_cnt) AS total_orders,
  SUM(gmv) AS total_gmv,
  SUM(total_subsidy) AS total_subsidy
FROM dws_user_daily
WHERE day BETWEEN <start_day> AND <end_day>
  AND lifecycle = '<target_lifecycle>'
GROUP BY city
ORDER BY city
```

默认替换建议：
- 新客问题：`<target_lifecycle>` 用 `new_user`
- 复购问题：`<target_lifecycle>` 用 `low_freq` 或 `regular_buyer`

这条查的是候选对象，不直接用于“最优/最差城市”正式落题，除非后续已经补齐完整比较窗口。

## 模板 C：按生命周期做候选扫描（DWS，探索阶段）

用途：判断主要矛盾落在哪类人群。

```sql
SELECT
  lifecycle,
  COUNT(*) AS user_cnt,
  SUM(order_cnt) AS total_orders,
  SUM(gmv) AS total_gmv,
  SUM(total_subsidy) AS total_subsidy
FROM dws_user_daily
WHERE day BETWEEN <start_day> AND <end_day>
GROUP BY lifecycle
ORDER BY lifecycle
```

适合用于：
- 判断“问题主要集中在新客还是老客”
- 给城市题或策略题选定观察对象

## 模板 D：按阶段拆查同一比较集（DWS，验证阶段常用）

用途：一条窗口聚合仍超时时，把同一比较集拆成两段或三段，再在 agent 内部求和。

```sql
SELECT
  city,
  COUNT(*) AS user_cnt,
  SUM(order_cnt) AS total_orders,
  SUM(gmv) AS total_gmv,
  SUM(total_subsidy) AS total_subsidy
FROM dws_user_daily
WHERE day BETWEEN 11 AND 15
  AND lifecycle = 'new_user'
GROUP BY city
ORDER BY city
```

```sql
SELECT
  city,
  COUNT(*) AS user_cnt,
  SUM(order_cnt) AS total_orders,
  SUM(gmv) AS total_gmv,
  SUM(total_subsidy) AS total_subsidy
FROM dws_user_daily
WHERE day BETWEEN 16 AND 20
  AND lifecycle = 'new_user'
GROUP BY city
ORDER BY city
```

只要两条查询：
- 覆盖同一个目标窗口
- 覆盖同一批对象
- 指标口径完全一致

则内部汇总后仍然是正式验证证据。

## 模板 E：按对象逐个验证（DWS，验证阶段兜底）

用途：按城市聚合仍超时时，把对象拆成多条小查询。

```sql
SELECT
  COUNT(*) AS user_cnt,
  SUM(order_cnt) AS total_orders,
  SUM(gmv) AS total_gmv,
  SUM(total_subsidy) AS total_subsidy
FROM dws_user_daily
WHERE day BETWEEN <start_day> AND <end_day>
  AND lifecycle = '<target_lifecycle>'
  AND city = '<target_city>'
```

默认用法：
- 把五个城市分别查完，再比较
- 这类“对象拆分后再汇总”依然可以作为正式出题依据，因为对象全集完整

## 模板 F：起始日 / 首次突破阈值查询（验证阶段）

用途：出“从第几天开始”“首次超过/低于阈值发生在哪天”的题。

### 平台级

```sql
SELECT
  day,
  new_user_order_ratio,
  subsidy_roi,
  ctr_eff,
  cvr_eff,
  avg_order_value
FROM dws_platform_daily
ORDER BY day
```

### 城市级 / 生命周期级

```sql
SELECT
  day,
  COUNT(*) AS user_cnt,
  SUM(order_cnt) AS total_orders,
  SUM(gmv) AS total_gmv,
  SUM(total_subsidy) AS total_subsidy
FROM dws_user_daily
WHERE city = '<target_city>'
  AND lifecycle = '<target_lifecycle>'
GROUP BY day
ORDER BY day
```

注意：
- 这类题必须覆盖完整日序列
- 不能用 `day IN (...)` 的抽样结果来判断“首次发生日”

## 模板 G：档口健康度 / 供给侧验证（DWS）

用途：验证供给侧恶化、档口活跃度、风险档口变化。

```sql
SELECT
  day,
  lifecycle,
  COUNT(*) AS stall_cnt,
  SUM(order_cnt) AS total_orders,
  SUM(gmv) AS total_gmv
FROM dws_stall_daily
GROUP BY day, lifecycle
ORDER BY day, lifecycle
```

或固定窗口按城市比较：

```sql
SELECT
  city,
  lifecycle,
  COUNT(*) AS stall_cnt,
  SUM(order_cnt) AS total_orders,
  SUM(gmv) AS total_gmv
FROM dws_stall_daily
WHERE day BETWEEN <start_day> AND <end_day>
GROUP BY city, lifecycle
ORDER BY city, lifecycle
```

如果 `city + lifecycle` 过重，先固定 `lifecycle` 再按 `city` 查，或先按 `city` 找候选，再做二次验证。

## 模板 H：DWD 单窗口单粒度查询（只在必须时使用）

用途：必须比较 `entrance` / `category` / 细粒度 CTR / CVR 时，先缩到最小范围。

```sql
SELECT
  entrance,
  COUNT(*) AS record_cnt,
  SUM(CASE WHEN is_clicked THEN 1 ELSE 0 END) AS click_cnt,
  SUM(CASE WHEN is_ordered THEN 1 ELSE 0 END) AS order_cnt,
  SUM(CASE WHEN is_ordered THEN sale_price ELSE 0 END) AS gtv
FROM dwd_transaction
WHERE day = <target_day>
  AND city = '<target_city>'
  AND user_lifecycle = '<target_lifecycle>'
GROUP BY entrance
ORDER BY entrance
```

只建议在以下条件同时满足时使用：
- 题目本质必须依赖入口/品类
- DWS 不能支撑唯一答案
- 已经先通过 DWS 确认了窗口、对象和候选方向

## 模板 I：DWD 单对象逐个查询（DWD 最后兜底）

用途：连 `GROUP BY entrance` 都超时时，把入口逐个拆开查。

```sql
SELECT
  COUNT(*) AS record_cnt,
  SUM(CASE WHEN is_clicked THEN 1 ELSE 0 END) AS click_cnt,
  SUM(CASE WHEN is_ordered THEN 1 ELSE 0 END) AS order_cnt,
  SUM(CASE WHEN is_ordered THEN sale_price ELSE 0 END) AS gtv
FROM dwd_transaction
WHERE day = <target_day>
  AND city = '<target_city>'
  AND user_lifecycle = '<target_lifecycle>'
  AND entrance = '<target_entrance>'
```

默认入口枚举：
- `main_feeds_high_card`
- `main_feeds_low_card`
- `search`
- `group_purchase`
- `community_bd`

如果五个入口都能完整查完，再在 agent 内部比较，仍可作为正式出题依据。

## 什么时候可以把查询结果拿来正式出题

只有当下面三件事同时满足时，查询结果才可直接支撑正式题面与 rubrics：

1. **窗口完整**：例如题目比较 `21-30`，则查询结果必须覆盖完整 `21-30`
2. **对象集合完整**：例如题目问“哪个城市最好”，则必须覆盖全部城市
3. **比较粒度一致**：例如题目在城市粒度回答，就不能只拿平台级或入口级结果替代

注意：
- 可以拆成多条小 SQL 再汇总
- 不可以用抽样点、部分对象、错粒度结果直接定题

## 什么情况下应停止下钻并换题型

满足任一条件时，应优先换到 DWS 可支撑的题型，而不是继续硬查 DWD：

- `dwd_transaction` 在“单天 + 单城市 + 单生命周期 + 单分组维度”下仍持续超时
- 要形成唯一结论必须同时比较 `city + lifecycle + entrance` 等多维宽口径
- DWS 已足以支撑平台级 / 城市级 / 生命周期级的唯一结论
- 继续追 DWD 只会增加细节，不会改变最终业务结论

## 推荐题型与默认表

- 起始日 / 阈值突破题：优先 `dws_platform_daily`
- 城市最优 / 最差题：优先 `dws_user_daily`
- 生命周期对比题：优先 `dws_user_daily`
- 档口健康度 / 供给侧题：优先 `dws_stall_daily`
- 入口 / 品类 / 细漏斗题：最后才考虑 `dwd_transaction`

## 最后判断标准

不是“有没有一条 SQL 直接出答案”，而是：

> 是否已经通过一组口径一致的小查询，恢复出了候选题面所依赖的完整比较集。

如果可以，就能定题；如果还不行，该结果只能用来形成候选结论，不能直接写进最终 `instruction.md` 与 `solution/rubrics.md`。
