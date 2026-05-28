# 将 AI 生成的图片插入学城文档

学城文档图片有权限校验，**图片权限与所在文档绑定**。非学城链接的图片属于非法数据，**严禁直接插入学城文档**。

当用户要求将 AI 生成的图片插入学城文档时，严格遵循以下工作流：

## 第一步：上传图片到目标文档

```bash
uploadImageToDocument --contentId <目标文档ID> --imageUrl <AI图片URL> [--alt <图片描述>]
```

该命令会：
- 下载 AI 图片二进制数据
- 将图片上传到目标文档的学城图片空间（图片权限与该文档绑定）
- 返回学城 CDN URL 和拼装好的 **CitadelMD 图片语法片段**（`imageMd`）

输出示例：

```
✅ 图片上传成功！
```

## 第二步：获取目标文档内容

```bash
getDocumentCitadelMd --contentId <目标文档ID>
```

获取文档当前完整的 CitadelMD 内容。

## 第三步：由 AI 在指定位置插入图片语法

将第一步返回的 `imageMd`（CitadelMD 图片语法片段）插入到文档 CitadelMD 内容的用户指定位置。

CitadelMD 图片语法格式：

```
![图片描述](https://km.sankuai.com/api/file/box/...)
![图片描述](https://km.sankuai.com/api/file/box/...){width=300 height=200 align=center}
```

支持的图片属性：
- `width`：图片宽度（px）
- `height`：图片高度（px）
- `align`：对齐方式（`left` / `center` / `right`）

## 第四步：回传更新文档

```bash
updateDocumentByMd --contentId <目标文档ID> --content <修改后的CitadelMD>
```

**输出**：返回文档链接，提醒用户刷新页面查看插入的图片。

## 示例 (Example)

用户：帮我把这张图 https://example.com/ai-chart.png 插入到文档 https://km.sankuai.com/collabpage/1234567890 的"总结"章节下面

思考：我需要先上传图片到目标文档，再获取文档内容，由 AI 找到插入位置后更新文档。

```bash
# 第一步：上传图片
uploadImageToDocument --contentId 1234567890 --imageUrl "https://example.com/ai-chart.png" --alt "总结图表"

# 第二步：获取文档内容
getDocumentCitadelMd --contentId 1234567890
```

... 获取到 imageMd 和文档内容后，AI 在"总结"章节下方插入图片语法，然后：

```bash
# 第四步：更新文档
updateDocumentByMd --contentId 1234567890 --content <修改后的CitadelMD>
```

## 禁止事项

- **严禁将非学城图片 URL（包括 AI 生成的图片原始 URL）直接写入 CitadelMD**
- 必须先通过 `uploadImageToDocument` 上传图片，取得学城 CDN URL 后再插入
- 图片上传必须指定目标文档 `contentId`，图片权限与该文档绑定，不可跨文档复用

---

# 将本地文件作为附件插入学城文档

## 第一步：上传附件到目标文档

```bash
uploadAttachmentToDocument --contentId <目标文档ID> --file <本地文件路径>
```

该命令会：
- 以 `multipart/form-data` 方式将本地文件上传到 `POST /api/file/upload/<contentId>`
- 返回学城附件 URL（`url`）及拼装好的 **CitadelMD 附件语法片段**（`attachmentMd`）

上传接口说明：
- **URL**：`POST https://km.sankuai.com/api/file/upload/<contentId>`
- **请求**：`multipart/form-data`，字段名 `file`，值为文件二进制内容
- **响应**（示例）：
  ```json
  {
    "status": 0,
    "data": {
      "url": "https://km.sankuai.com/api/file/attachment/2752685363/228651870995",
      "attachmentId": 228651870995,
      "downloadUrl": "https://file.sankuai.com/file/dl/..."
    }
  }
  ```

## 第二步：获取目标文档内容

```bash
getDocumentCitadelMd --contentId <目标文档ID>
```

获取文档当前完整的 CitadelMD 内容。

## 第三步：由 AI 在指定位置插入附件语法

将第一步返回的 `attachmentMd`（CitadelMD 附件语法片段）插入到文档 CitadelMD 内容的用户指定位置。

CitadelMD 附件语法格式（参考 `doc-update.md` 附件节点说明）：

```
:::attachment{src="https://km.sankuai.com/api/file/attachment/<contentId>/<attachmentId>" name="文件名.pdf" size="1.2MB"}:::
```

支持的附件属性：
- `src`：学城附件 URL（上传响应的 `data.url`），**必填**
- `name`：文件名，用于展示（可从本地文件路径中提取），**必填**
- `size`：文件大小（人类可读格式，如 `1.2MB`），可选

## 第四步：回传更新文档

```bash
updateDocumentByMd --contentId <目标文档ID> --content <修改后的CitadelMD>
```

**输出**：返回文档链接，提醒用户刷新页面查看插入的附件。

## 示例 (Example)

用户：帮我把 /tmp/report.pdf 插入到文档 https://km.sankuai.com/collabpage/1234567890 的"附录"章节下面

思考：我需要先上传附件到目标文档，再获取文档内容，由 AI 找到插入位置后更新文档。

```bash
# 第一步：上传附件
uploadAttachmentToDocument --contentId 1234567890 --file "/tmp/report.pdf"

# 第二步：获取文档内容
getDocumentCitadelMd --contentId 1234567890
```

... 获取到 `attachmentMd` 和文档内容后，AI 在"附录"章节下方插入附件语法，然后：

```bash
# 第四步：更新文档
updateDocumentByMd --contentId 1234567890 --content <修改后的CitadelMD>
```

## 禁止事项

- **严禁将非学城附件 URL 直接写入 CitadelMD**，必须先上传取得学城 URL
- 附件上传必须指定目标文档 `contentId`，附件权限与该文档绑定，不可跨文档复用
