# 水粉绘本 PPT

`$gouache-ppt` 是一个 Codex 技能，用来根据大纲、文档、图片或已有 PPTX 制作可编辑的水粉绘本式演示文稿。

- **内容页**按图数、主次、阅读顺序和文字容量选版，用水粉背景、纸层和装饰组织图文。
- **字体与主题**按题材选配色和本机可用的标题字族，搭配易读的正文字族。
- **完整演示**含图片艺术字封皮、统一章节页和独立封底，制作至少 20 枚独立透明的主题贴纸。
- **可编辑组版**保留独立的文字、形状和图片对象。按项目需要保存素材、组版清单和逐页预览。

## 安装与使用

将本仓库下载后，把包含 `SKILL.md` 的目录命名为 `gouache-ppt`，放进 Codex 扫描的技能目录。例如放在项目的 `.agents/skills/gouache-ppt/`。全局目录按当前 Codex 环境配置。

在 Codex 中调用：

> 用 $gouache-ppt，按我提供的大纲和版式参考制作一套可编辑的水粉绘本 PPT，重点设计内容页的图文配合。

生成背景、艺术字和贴纸需要可用的图像生成工具。运行组版脚本需要 Python、`python-pptx` 和 `Pillow`。缩略校样脚本所需的 Node.js 依赖见脚本中的说明。

- [技能入口](SKILL.md)
- [版式、字体与水粉风格](references/layout.md)
- [生图与贴纸规范](references/assets.md)
- [验收与复现](references/verification.md)

## 来源与许可

本技能借鉴了 [FA-T-T 的 ppt-image（Codex Skill: Academic Slides）](https://github.com/FA-T-T/codex-skill-academic-slides)。

按 Apache License 2.0 发布。授权文本和原项目署名见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。
