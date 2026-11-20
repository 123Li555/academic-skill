---
name: academic-diagram-workflow
description: "Create or redraw academic model architecture, mechanism, and technical roadmap diagrams as editable SVG or native PowerPoint shapes. Use for 科研架构图、模型模块图、技术路线图、低饱和轴测图、去外框配图。Use a plotting skill for quantitative charts."
---

# 科研架构绘图流程

把用户提供的模型、机制或技术路线绘制成低饱和、可编辑的矢量图。以最新附件、演示稿和用户指定的实现为事实依据。

## 默认样式

- **整图和大分区默认无外围边框。** 用留白、标题和对齐区分层次。模块需要强调时，用短色条、标题色或局部浅底。张量的轴测轮廓、掩码单元和运算节点的必要边线照常绘制。
- 轴测形状应说明结构。张量用网格薄片、历史窗口用有意义的步数条带、代理记忆用代理槽、主干重复用层板和省略号。图卷积和超图卷积可分别画节点连线和超边区域。算子、公式和维度保留简短可编辑标注。
- 采用低饱和灰蓝、灰绿、砂棕和灰紫，箭头方向清楚，用标题和标注提供颜色以外的辨识线索。默认中文用微软雅黑，英文、数字与公式符号用 Times New Roman。用户指定的字体和配色优先。

## 交付步骤

1. 核对输入、输出、箭头方向、张量轴和分支接入点。用原稿或代码区分示意步数、真实参数和实验数值。技术路线图按读者需要保留数据准备、方法与验证的关系。
2. 按目标页可用空间设计。已有 PPT 先定位当前文件与指定页的图、图注、公式和正文。纯绘图按适合阅读的宽高比起稿。用 [轴测原语](scripts/diagram.py)、[可运行起稿](assets/starter_model.py) 或 [无外框示例](assets/starter-open.svg) 组织矢量元素。
3. 在最终尺寸预览 SVG。逐项检查外围留白、重叠、箭头连接、数学下标和字体。PNG 用于预览，SVG 是矢量母版。
4. 若交付可编辑 PPT，按 [完整操作和命令](references/workflow.md) 转为原生形状并渲染。现有 PPT 先完成局部替换和核验，再按用户授权备份与发布。

用户只要图时交付图稿。需要回填时交付验证后的 PPT，并按任务提供独立 SVG 或预览。
