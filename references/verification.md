# 验收与复现

## 记录每次构建

在项目的 `slides/项目名_时间/` 中保存逐页规划、原始图与来源、生成提示和接受的素材、组版 JSON、输出 PPTX。先在纸面条件差异明显的封皮、图文内容页和章节页各验证一种布局，再铺开。JSON 与资产一并保存时可重复构建相同布局。

## 可选组版助手

`scripts/deck.py` 读取 1600 × 900 坐标的 JSON，用 python-pptx 和 Pillow 构建每页。清单中的元素按从底到顶排列。在计划顶层用 `fonts` 记录已选的标题和正文字族。文本元素可用 `role: "title"` 采用标题字体，省略 `role` 则采用正文。用 `font` 可以指定单个元素的字体。正文配置省略时采用微软雅黑。相关文件路径相对 JSON 文件。用可用的工作区 Python 运行。

```sh
python scripts/deck.py build plan.json output.pptx
python scripts/deck.py stickers assets/stickers
python scripts/deck.py preserve approved.pptx revised.pptx
python scripts/deck.py preserve approved.pptx revised.pptx --exclude 1,3
```

`stickers` 检查独立 PNG 的数量、透明与主体、像素级重复。可以用 `--minimum` 测试子集，正式验收用默认的 20 张。 `preserve` 按幻灯片位置比较已有图片的源文件字节、显示位置、裁切与旋转，允许增加对象或末尾增页。只有用户授权更换或重排图片的页才列入 `--exclude`。插页后按明确的旧页到新页对应关系验收。

以下清单示意章节页和内容页的底图、色晕、纸层、证据与贴纸的顺序。封皮可用相同的 `image` 元素放入生成的艺术字，设置准确的替代文本。封底按同样方式将插画与原生收尾文字叠放。

```json
{
  "fonts": {"title":"幼圆","body":"微软雅黑"},
  "slides": [
    {
      "notes": "从当前章节的问题过渡到下一页。",
      "elements": [
        {"type":"image","file":"chapter.png","box":[0,0,1600,900],"fit":"cover"},
        {"type":"shape","box":[0,0,1600,900],"fill":"183153","opacity":42},
        {"type":"text","role":"title","text":"第一章","box":[440,170,720,60],"size":24,"color":"FFF3D7","align":"center"},
        {"type":"text","role":"title","text":"我们怎样找出目标？","box":[220,295,1160,130],"size":51,"color":"FFF9ED","align":"center","bold":true}
      ]
    },
    {
      "notes":"解释为什么这张图能支持标题。",
      "elements":[
        {"type":"image","file":"section-paper.png","box":[0,0,1600,900],"fit":"cover"},
        {"type":"shape","kind":"wash","box":[970,22,530,140],"fill":"709AAF","opacity":36},
        {"type":"text","role":"title","text":"这张影像能帮我们核对位置","box":[66,54,1460,80],"size":32,"color":"203D53","bold":true},
        {"type":"shape","kind":"round","box":[58,177,872,574],"fill":"ACD0C9","opacity":82,"rotation":-1.5},
        {"type":"shape","kind":"round","box":[76,170,850,566],"fill":"FFF6E7"},
        {"type":"image","file":"paper-figure.png","box":[95,204,812,475],"fit":"contain","alt":"论文图 2，参照原图的图注"},
        {"type":"text","text":"图 2 研究区影像","box":[100,683,800,38],"size":13,"color":"274458"},
        {"type":"shape","kind":"round","box":[973,220,548,285],"fill":"D6E7DF"},
        {"type":"text","text":"把两张图对齐，再核对目标出现的位置。","box":[1000,277,490,150],"size":21,"color":"203D53"},
        {"type":"image","file":"stickers/map.png","box":[1430,190,96,82],"rotation":-8,"fit":"contain"}
      ]
    }
  ]
}
```

元素可用 `name` 命名，图片的 `alt` 用于准确替代文本。 `image` 支持 `contain` 和居中 `cover`， `clip` 可指定原图分数范围 `[左,上,右,下]` 后再等比适配。 `shape` 支持 `rect`、`round`、`oval`、`wash`。 `text` 支持 `left`、`center`、`right` 对齐和显式换行。

## 交付前检查

1. 核对标题、章号、页码及各页主要信息和图文对应关系。图表原图、数据、轴名、单位、引文和注释能在交付成品中找到。
2. 渲染 PPTX 全部页面，用缩略总览检查节奏，再用正常放映大小逐页检查文本框、边缘、图例、贴纸和形状。检查封面图中文字，检查至少 20 张透明贴纸成品。不能渲染的文件继续处理，最终明确哪些检查已完成。
3. 对长文调整断句和空间。留出框内边距，仔细看中英混排、负号和单位、旋转后的边界、字形替代和多行行距。装饰、胶带和形状与图文发生遮挡时，先换装饰位置。关键图文优先于装饰。
4. 对编辑任务用批准稿与新稿做比较，按授权范围检查图片的位置、裁切、旋转和媒体，核对需要保留的正文、备注及用户手工改动。确认从导出包重新打开时页数和页序正确。
