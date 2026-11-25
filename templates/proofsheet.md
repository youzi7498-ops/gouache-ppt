<!-- 水粉绘本 PPT 对此文件进行了修改。上游署名见 NOTICE。 -->

# 幻灯片缩略校样

将最终 PPTX 渲染成按页序编号的 PNG。已有用户指定的成页图时直接使用。按需要输出缩略总览图、校样 PPTX 或两者。缩略图标明页码，保留页面纵横比。

```sh
node scripts/pack_image_deck.mjs --images "images/slide_*.png" --contact-sheet outputs/contact_sheet.png --proofsheet-pptx outputs/proofsheet.pptx
```

路径按实际项目位置填写。可指定 `--proofsheet-cols` 与 `--proofsheet-rows` 调整校样密度。逐页版式验收以实际渲染和放映尺寸为准。
