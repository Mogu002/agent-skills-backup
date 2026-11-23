# SQL Function 专项

Base SQL 是 PostgreSQL 风格的只读查询子集。只使用本文明确列出的支持集，不从 PostgreSQL 的通用语法或函数推断 Base SQL 能力。

## 阅读路径

1. [Catalog](#catalog)
2. [SQL-类型与结果值](#sql-类型与结果值)
3. [Function-文件与参数](#function-文件与参数)
4. [查询约束](#查询约束)
5. [调用与结果](#调用与结果)
6. [校验](#校验)

## Catalog

`catalog.json` 是已绑定 Base 的 SQL schema。SQL 中的表名、字段名、OPTION 值和关联关系只从这里读取：

```json
{
  "tables": [
    {
      "baseToken": "basxxx",
      "id": "tblTasks",
      "name": "任务",
      "fields": {
        "状态": {
          "id": "fldStatus",
          "name": "状态",
          "baseType": "SingleSelect",
          "sqlType": {
            "kind": "OPTION",
            "options": [{ "id": "optTodo", "name": "待处理" }]
          },
          "nullable": true
        },
        "关联客户": {
          "id": "fldCustomer",
          "name": "关联客户",
          "sqlType": {
            "kind": "COLLECTION",
            "element": { "kind": "RECORD_ID" }
          },
          "nullable": true,
          "reference": {
            "baseToken": "basxxx",
            "tableId": "tblCustomers"
          }
        }
      }
    }
  ]
}
```

- SQL 使用 `tables[].name` 和 `fields[key].name`；中文、空格或标点名称用双引号。
- `fields[key].sqlType` 决定可查询类型；`UNSUPPORTED` 字段不查询。
- OPTION 使用 `options[].name` 比较，不使用 option ID。
- `COLLECTION` / `ARRAY` 的元素类型在 `sqlType.element`。
- 关联目标由 `reference` 定位，JOIN 使用目标表名和其 `rec_id`。
- 每张表自动提供 `rec_id`，类型为 `RECORD_ID`。Base、table、field ID 不写进 SQL。

## SQL 类型与结果值

`sqlType` 是递归结构：标量为 `{"kind":"TEXT"}`，集合为 `{"kind":"COLLECTION","element":{...}}`，OPTION 额外带 `options`。SQL 返回的行会序列化成普通 JSON：

| SQL type | ResultJSON 中的值 |
|---|---|
| `TEXT`、`OPTION` | string |
| `INT` | JavaScript safe integer number |
| `DOUBLE` | number |
| `BOOL` | boolean |
| `TIMESTAMP` | Unix epoch 毫秒 number |
| `USER_ID`、`GROUP_ID`、`RECORD_ID` | ID string |
| `USER` | object；SQL 可读取 `.userId`、`.name` |
| `GROUP` | object；SQL 可读取 `.id`、`.name` |
| `FILE` | object；SQL 可读取 `.id`、`.name`、`.url`、`.size` |
| `COLLECTION<T>`、`ARRAY<T>` | `T[]` |
| nullable field | 原类型或 `null` |

前端处理 `TIMESTAMP` 时先把毫秒 number 转为 `Date`，再按产品目标时区格式化。不要把它当秒级时间戳或已格式化字符串。

## Function 文件与参数

```text
sql/<functionId>/
├── main.sql
└── meta.json
```

`main.sql` 只包含一条固定 `SELECT`。`meta.json` 包含非空 `name`、可选 `description` 和参数声明。

SQL 参数使用 PostgreSQL 位置参数 `$1`、`$2`……；`meta.params` 按相同顺序声明：

```sql
SELECT rec_id AS record_id, "任务名称" AS title, "状态" AS status
FROM "任务"
WHERE "任务名称" LIKE $1 AND "状态" = $2
ORDER BY rec_id DESC
LIMIT $3
```

```json
{
  "name": "搜索任务",
  "description": "按关键词和状态搜索任务",
  "meta": {
    "params": [
      { "kind": "TEXT", "description": "$1，已包含 % 的关键词" },
      { "kind": "OPTION", "description": "$2，任务状态" },
      { "kind": "INT", "description": "$3，返回条数" }
    ]
  }
}
```

`$n`、`meta.params[n-1]` 和调用 `params[n-1]` 必须连续、一一对应。每项只写 `kind` 和可选的 `description`。

参数 `kind` 支持 `TEXT`、`INT`、`DOUBLE`、`BOOL`、`TIMESTAMP`、`OPTION`、`USER_ID`、`GROUP_ID`、`RECORD_ID`。参数必须是非 null 标量；`USER`、`GROUP`、`FILE`、数组和集合不能作为参数。

无参数 Function 可以省略 `meta` 或 `meta.params`；归档统一补成 `{"params":[]}`。

## 查询约束

只编写只读 `SELECT`，页面输入只能进入位置参数。查询使用以下支持集：

- 每条查询从 Catalog 中的真实表开始，也可以从带别名的 `FROM (SELECT ...) AS alias` 派生表开始。
- 查询结构使用投影、`WHERE`、`GROUP BY`、`HAVING`、`ORDER BY`、`LIMIT` 和 `OFFSET`。
- 连接使用 `INNER JOIN`、`LEFT JOIN`、`CROSS JOIN` 或逗号连接。每个 JOIN 的右侧保持为一个表、一个带别名的派生表或一个 `UNNEST`；单条查询的 JOIN 总数不超过 16。
- 子查询只作为带别名的 `FROM` 派生表使用；外层通过派生表输出列名引用结果。
- 列表使用 `LIMIT` 和稳定排序；排序值可能重复时最后按 `rec_id` 排序。
- 返回字段逐列列出并使用 `AS snake_case`。
- 搜索写 `field LIKE $1`，由参数携带 `%`。
- OPTION 与 Catalog 中合法的选项名比较。
- 当前访问者使用 `CURRENT_USER_ID()`，不由页面传入用户 ID。
- 列引用最多两段。标量 `USER`、`GROUP`、`FILE` 子字段不带表别名，分别写 `"负责人".userId`、`"群组".id`、`"附件".url`；多值对象先 `UNNEST(t."人员") AS u`，再写 `u.userId`。
- 集合字段使用 `ARRAY_CONTAINS(array, value)`、`ARRAY_OVERLAP(array, array)`、`@>`、`<@`、`&&` 判断成员或集合关系，或者通过 `UNNEST` 展开；展开时先写真实表，再写 `UNNEST`。
- 条件分支使用搜索式 `CASE WHEN bool_expr THEN value ... ELSE value END`。
- 时间条件使用 `TIMESTAMP` 字段或 `TIMESTAMP` 位置参数；当前时间使用 `CURRENT_TIMESTAMP`。
- 聚合函数使用 `COUNT(*)`、`COUNT(expr)`、`SUM(NUMBER)`、`AVG(NUMBER)`、`MIN(scalar)`、`MAX(scalar)`。
- 字符串函数使用 `LOWER(TEXT)`、`UPPER(TEXT)`、`TRIM(TEXT)`、`CONCAT(TEXT, ...)`。
- 数字计算使用 `+`、`-`、`*`、`/`、`MOD`、`ABS(NUMBER)`、`ROUND(NUMBER[, precision])`。

字段筛选使用以下支持形态：

| 字段类型 | 支持的筛选形态 |
|---|---|
| `rec_id`、`TEXT`、Phone | `=`、`IN`、`NOT IN`、`LIKE`、`NOT LIKE`、`ILIKE`、`NOT ILIKE` |
| `INT`、`DOUBLE` | `=`、`IN`、`NOT IN`、`<`、`<=`、`>`、`>=`、`BETWEEN` |
| `BOOL` | `= TRUE`、`= FALSE` |
| `TIMESTAMP` | 与 `TIMESTAMP` 参数使用 `=`、`!=`、`<`、`<=`、`>`、`>=`、`BETWEEN` |
| `OPTION` | 与 Catalog 中的选项名使用 `=`、`IN`、`NOT IN` |
| 多选、关联记录等集合 | `ARRAY_CONTAINS`、`ARRAY_OVERLAP`、`@>`、`<@`、`&&`，或先 `UNNEST` 再比较元素 |
| `USER`、`GROUP`、`FILE` | 比较 `.userId`、`.id`、`.name`、`.url` 等标量子字段；多值对象先 `UNNEST` |

集合筛选：

```sql
SELECT f.rec_id AS followup_id, f."跟进时间" AS followed_at
FROM "跟进记录" AS f, UNNEST(f."关联线索") AS lead_id
WHERE lead_id = $1
ORDER BY f."跟进时间" DESC, f.rec_id DESC
LIMIT 30
```

读取关联表字段时，先展开 record ID 再 JOIN：

```sql
SELECT x.order_no, c."客户名称" AS customer_name
FROM (
  SELECT o."订单号" AS order_no, customer_id
  FROM "订单" AS o, UNNEST(o."客户") AS customer_id
  WHERE customer_id = $1
) AS x
JOIN "客户" AS c ON x.customer_id = c.rec_id
ORDER BY x.order_no DESC
LIMIT 20
```

搜索、筛选、关联和聚合尽量在 SQL 中完成。没有关系、不同步消费或需要隔离失败语义的结果集可以拆分；拆分后的输入若在开始时已经确定，应并发调用。

## 调用与结果

页面和 FaaS 调用都传数组：

```ts
await invokeFunction({
  projectId: PROJECT_ID,
  functionId: 'searchTasks',
  params: ['%评审%', '待处理', 20],
})
```

公开 HTTP body：

```json
{ "params": ["%评审%", "待处理", 20] }
```

返回是 ResultJSON，不是 rows 数组：

```json
{
  "data": {
    "rows": [
      {
        "record_id": "recxxx",
        "title": "准备评审",
        "status": "待处理",
        "due_at": 1784311200000
      }
    ],
    "columns": [],
    "row_count": 1,
    "fxdb_version": "...",
    "log_id": "..."
  },
  "code": 0,
  "msg": "success"
}
```

先检查 `code===0` 和 `data`，再验证 `data.rows` 以及每一行的数据结构。

## 校验

`base-site deploy` 会统一归档并调用服务端 SQL 校验，以该命令的最终结果为准。Preview 发布后停止，由用户从页面体验真实查询。失败时一次性保留编译错误和 LogID，不更换参数类型或响应 envelope 猜测绕过。
