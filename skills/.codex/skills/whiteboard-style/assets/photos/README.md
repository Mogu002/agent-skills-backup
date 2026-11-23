# 图片展示用的三张素材

`p1.jpg` 机房、`p2.jpg` 协作评审、`p3.jpg` 城市夜景。

`assets/dsl/whiteboard_dsl_photo.json` 里的 `image.src` 是**目标画板上的 media token**，
换画板后必须重新上传并替换：

```bash
lark-cli docs +media-upload --as user --parent-type whiteboard \
  --parent-node <board_token> --file assets/photos/p1.jpg --format json
```

三张图必须互不相同（上传后比较文件大小 / 目检），尺寸统一 240×160。
