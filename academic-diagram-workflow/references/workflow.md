# 从原图到可编辑交付

## 1. 核对内容与版面

从最新附件读出输入、处理顺序、支路接入点和输出。对照作者正文或实际实现确认参数、步长、张量轴和归一化位置。框架图的叠层用省略号配合实际层数符号，避免图上恰好画出的块数被读成固定层数。技术路线图中的评估范围和已完成结果各用准确措辞。

先在目标页找出图、图注、公式和标题的位置，再决定画布比例。总框架图读取方向通常从左到右，模块图可以按机制分成上下两行。大分区靠留白与短标题区分。把残差、跳跃连接和门控单独画清楚，箭头落在真正的输入或汇合节点。

## 2. 起稿与预览

[起稿脚本](../assets/starter_model.py) 展示如何用 [轴测原语](../scripts/diagram.py) 生成带可编辑文字的 SVG。直接按实际输入和结构改坐标、标签及列数。[无外框起稿示例](../assets/starter-open.svg) 展示张量、时间条带和箭头之间的排版。修改现有矢量时先识别外围容器的对象 ID，再定点处理；张量正面也可能是矩形，需按语义保留。

统一轴测面方向和深度，用拼接、矩阵、层板或序列表示实际结构。文字采用独立 SVG 文本，公式可用若干独立基线文字拼接。放映预览使用白底，SVG 可保留透明画布。逐项检查拼写、语义、线条和下标，并以目标尺寸评估可读性。

## 3. 脚本命令

使用 Codex 的工作区依赖工具取得 Python、Node.js 及 Node 模块目录。以下命令中的变量指向本地实际路径，输出落在本次任务的工作目录。已有 SVG 可以从第二行起执行。若只需 SVG，完成起稿与预览即可。PowerPoint 导出使用 `@oai/artifact-tool`；浏览器预览使用同一运行时中的 Playwright 与本机 Chromium 系浏览器。

~~~powershell
& $python -B "$skill\assets\starter_model.py" "$work\figure.svg"
& $python -B "$skill\scripts\prepare_svg.py" "$work\figure.svg" "$work\figure.json"
& $node "$skill\scripts\preview_svg.cjs" "$work\figure.svg" "$work\figure.png" $nodeModules $browserExe
& $node "$skill\scripts\svg_to_pptx.mjs" "$work\figure.json" "$work\figure.pptx" $nodeModules
~~~

转换器使用原点为 `0 0` 的 SVG viewBox。本地编辑格式支持独立的 `text`、矩形、椭圆、圆、直线和由 `M/L/Z` 构成的单段路径。复杂效果、透明度与继承样式先改成直接的矢量构件。默认检查整幅矩形边框与显式标注的分区外框；分区布局仍需在预览中目检。用户明确要求外围边框时可传入 `--allow-outer-frame`。

## 4. 回填已有 PowerPoint

先核对当前文件、页码和目标图片。脚本按实际放映顺序定位页，目标页只有一张顶层图片时可直接定位。多张图片或图片组时，从页面对象检查结果确定顶层对象 ID，再用 `--shape-id` 指定。原图比例适用时沿用其可用框，必要时用 `--box X Y W H` 指定图注上方的新框，单位是 PowerPoint 点。输出采用一个新路径。

~~~powershell
& $python -B "$skill\scripts\place_figure.py" "$work\original.pptx" "$work\figure.pptx" "$work\updated.pptx" --page 12 --shape-id 17
& "$skill\scripts\render_slide.ps1" -Pptx "$work\updated.pptx" -Page 12 -Png "$work\page12.png"
~~~

插入时按比例适配、保留原图图层位置和对象 ID，把矢量对象组保存在目标页。处理中文与拉丁字体，并按落位比例修正显式文字字号。替换脚本核验原有对象、其余页面和包内组件；PowerPoint 预览补充检查实际文字大小、箭头、层次与图注间距。渲染前后分别保留目标页预览便于对照。PowerPoint 预览脚本适用于 Windows 桌面版。

用户需要覆盖原件时，确认磁盘原件与起始快照哈希一致，在同目录保留独立备份，使用已核验稿覆盖，并复核新旧文件。遇到原件刚被改动或锁定时，保留可交付的新稿，避免覆盖用户的新编辑。
