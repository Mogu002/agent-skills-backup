# Base SQL 不支持能力

仅在判断支持集之外的 SQL 语法、评审或排查 SQL，或者处理 SQL 编译与运行兼容失败时读取。以下能力不写入 `main.sql`：

- 查询结构：无 `FROM` 查询、CTE、`UNION`、`INTERSECT`、`EXCEPT`、`INSERT`、`UPDATE`、`DELETE`、`MERGE`，以及右侧会展开为多个 FROM item 的右深嵌套 JOIN。
- 子查询：`ARRAY` 子查询、`EXISTS` 子查询和标量子查询。
- 类型与表达式：`DURATION`、SQL `TIMESTAMP` 字面量、`INTERVAL`、`CURRENT_DATE`、Simple CASE、显式 `CAST` / Coerce、`EXTRACT`，以及固定支持集之外的函数调用。
- 时间运算：TIMESTAMP 与 DURATION 的加减、TIMESTAMP 相减、DURATION 加减与缩放。
- `rec_id`、`TEXT`、Phone：顺序比较、`BETWEEN`、`NOT BETWEEN`。
- Checkbox：`IN`、顺序比较、`BETWEEN`、`NOT BETWEEN`。
- DateTime：`IN`、`NOT IN`、`LIKE`、`ILIKE`。
- SingleSelect：顺序比较、`BETWEEN`、`NOT BETWEEN`、`LIKE`、`ILIKE`。
- MultiSelect：`LIKE`。
- `USER`、`GROUP`、`FILE`：直接比较完整对象。
- 关联记录集合：集合与标量直接比较，以及直接对集合使用 `LIKE`。
- 聚合与窗口函数：`ARRAY_AGG`、`STDDEV`、`VARIANCE`、`PERCENTILE`、`MEDIAN`、`ROW_NUMBER`。
- 字符串函数：`SUBSTRING`、`REPLACE`、`POSITION`、`REGEXP` / `RLIKE`、`SPLIT`。
- 数字函数：`CEIL`、`FLOOR`、`POWER`、`SQRT`、`LOG`、`EXP`。
- 日期函数：`DATEDIFF` 及其他 DURATION 函数。
