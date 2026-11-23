# 分层验收与交付

## 可执行快照比较

`verify_snapshot.py` 对照一张表的前后快照与 expect.json，不修改远端。快照格式由 snapshot.py 产生。expected_records 用 field ID（或快照中唯一名称）；created_record_ids 是实际返回且核对过的ID。

```json
{
  "expected_count": 120,
  "created_record_ids": [],
  "expected_records": {},
  "allowed_existing_changes": {},
  "attachments": []
}
```

`allowed_existing_changes` 是 record ID 到允许变化 field ID 数组；原有行的其他字段必须保持原样，禁止凭“允许”把预期值检查省掉；每个允许变化字段都要有 expected_records 值。附件字段用附件检查条目承载预期，attachment的例子：

```json
{
  "record_id": "actual-record",
  "field_id": "actual-attachment-field",
  "local_path": "attachments/sample.pdf",
  "exact_count": 1,
  "absent_tokens": ["approved-old-token"],
  "downloaded_path": "readback/sample.pdf",
  "download_receipt_path": "readback/sample-download-response.json"
}
```

路径相对于 expect.json。local_path检查名称和大小；downloaded_path配合真实CLI下载回执绑定当前file token后比SHA256，报告这一项才称云端下载完整性通过。没有下载回执不能声称云端hash验证通过。所有声明的新ID都应在expected_records中有内容预期。

默认字段配置按ID比较，忽略字段返回顺序，保留选项顺序的意义。批准字段迁移时提供 `expected_schema` 为预期完整字段对象列表，并验证记录迁移及直接依赖。不要为了测试通过而忽略实际结构变化。

## 建设验收

全量结构/记录：完整分页、预期行数、record ID集合、字段/选项、存储值、附件存在、无非预期变化。日期依据实际表时区比较，不能直接忽略日期或默认中国时区。若含自动更新系统列，只有明确发生业务变更的行可用 allow_system_updates=true 放行 updated_at/updated_by，其他行仍检查；这不允许忽略普通存储字段。文件：名称与大小不是内容证明；对关键替换全部hash，新增大量附件可按风险抽样hash并报告覆盖率。

语义：公司全称/别名/母子法人关系、行业、报告期、文件类别/效力、金标准集合与排除理由。计数/唯一匹配/极值需要检查整个最终数据集，不能只检查新增行。图片型PDF需确认无文字层；混合型单独分类，不能都算纯图片扫描件。既有未知数量不能按零处理。

生成模板先渲染代表性封面、长文本、正文、正例、硬负、扫描样本；没有乱码、裁切、重叠才继续。缩放/渲染影响OCR，适度质量波动来自题目要求，不自行增加难度。合成标识不得替代真实证据；不要用目标文件名或POS/NEG标签泄漏答案。

## 独立语义与检索效果验收

把同源计划一致性校验、独立附件提取、实际运行题目查询分别记录。独立提取不以生成文本或计划值充当观察结果；扫描件需要OCR/视觉证据。盲测只给执行者题目和最终被测资源，不提供Gold或预期答案；运行后才比对目标集合与硬负排除。

工具或权限不足时明确未验证项与影响，不把“Gold内部有30对”升级为“独立查询能正确返回30对”。不存在效果验收工具时可完成建设，但交付分开说明，不能宣称盲测通过。

## 按风险选择范围

生成少量新附件检查对应文件/记录。批量建设核验所有新增记录并审查存量影响。字段分类/公共计算变动扩展到直接依赖；未知边界再扩大。局部修整只补测受影响记录、必要的整表不变性和计数，复用之前有效证据，不默认重跑其他无关表或整个系统。

交付包含：题号与来源记录、准确目标链接、改前/后数量、字段与口径变更、样本与附件数量、Gold与证据、授权的替换范围、风险及未验证项。工作目录保留快照、计划、请求、状态、Gold、备份和验收结果；不污染技能包或同步sources。
