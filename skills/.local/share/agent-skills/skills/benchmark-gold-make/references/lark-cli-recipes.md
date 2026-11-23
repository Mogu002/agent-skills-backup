# lark-cli 操作配方（Windows PowerShell）

全程 `--as user`。关键坑：**PowerShell 下 lark-cli 的 `--filter-json` / `--json` / `--output` 都不能直接吃长 JSON 字符串或绝对路径**——字符串会被 shell 拆坏，绝对路径会被拒（"must be a relative path within the current directory"）。统一改用「相对路径的 @file」并用 `cwd` 定位。

## 1. 解析链接 / 读 schema

```
lark-cli base +url-resolve --url '<带 table、view 的链接>' --as user
```
返回 base_token / table_id / view_id，并在 hint.fields 里带全字段 schema（含 select 选项）。副本 Base 链接同样用它解析。

```
lark-cli base +table-list  --base-token <bt> --as user --format json   # data.tables[].{id,name,records_count}
lark-cli base +field-list  --base-token <bt> --table-id <tbl> --as user --format json   # data.fields[].{id,name,type,options}
```

## 2. 按题号取行（filter 用 @file）

filter_qxx.json（内容示例，放工作目录）：
```json
{"logic":"or","conditions":[["题号","==","Q58"],["题号","==","Q59"],["题号","==","Q60"]]}
```
执行（cwd 设为该文件所在目录，用相对 @ 路径）：
```
lark-cli base +record-list --base-token <bt> --table-id <tbl> --filter-json "@filter_qxx.json" --format json --as user
```
注意：`--filter-json` 不支持 `--output`；要落盘用 PowerShell `| Out-File -Encoding utf8`。读回时文件带 BOM，Python 用 `encoding="utf-8-sig"`。

record-list 返回里：`data.data`=二维值数组，`data.fields`=列名顺序，`data.record_id_list`=行 id，按下标 zip 还原每行。select 单元格是字符串数组，附件单元格是 `[{file_token,name,size}]`。

## 3. 写回 目标表 + 参考答案（batch-update 用 @file）

update_text.json：
```json
{"update_records":{
  "<record_id>":{"目标表":["表A","表B","表C"],"参考答案":"……多行文本……"}
}}
```
```
# cwd = update_text.json 所在目录
lark-cli base +record-batch-update --base-token <bt> --table-id <tbl> --json "@update_text.json" --as user
```
单批最多 200 条，同表串行写。select 传选项名数组；清空传 null 或 []。公式/lookup/时间戳等只读字段误写会被静默忽略（返回 ignored_fields）。

## 4. 命中附件：先下载后上传

下载（record-id + file-token，`--output` 用相对路径，cwd 设为目标目录）：
```
# cwd = 下载目录
lark-cli base +record-download-attachment --base-token <srcBt> --table-id <srcTbl> --record-id <rid> --file-token <tok> --output "./<原文件名>.pdf" --overwrite --as user
```
file_token 从来源记录的附件单元格 `[{file_token,name}]` 取。

上传到主控表附件字段（可重复 --file 批量；>20MB 自动分片）：
```
# cwd = 本地文件目录
lark-cli base +record-upload-attachment --base-token <bt> --table-id <tbl> --record-id <rid> --field-id "命中附件" --file "./a.pdf" --file "./b.pdf" --as user
```
上传后附件名=本地文件名，所以下载时就用来源原名。单元格上限 50 文件 / 单文件 2GB。

## 5. 读回验收

```
lark-cli base +record-get --base-token <bt> --table-id <tbl> --record-id <r1> --record-id <r2> --field-id 题号 --field-id 目标表 --field-id 命中附件 --as user --format json
```

## 批量脚本建议

多行下载/上传用 Python `subprocess.run([...], shell=True, cwd=<目录>)` 循环逐条调 lark-cli，用相对 `./文件名` 做 --output/--file，避免 PowerShell 引号与绝对路径两个坑。
