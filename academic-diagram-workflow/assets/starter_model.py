"""Starter layout for one editable academic model diagram."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from diagram import Diagram


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
args = parser.parse_args()

fig = Diagram(1000, 320, "时空预测流程起稿")
fig.heading(58, 57, "从历史窗口到多步预测")
fig.stack(105, 121, 132, 59, count=2)
fig.stack(438, 121, 132, 59, tint="green")
fig.sequence(734, 136, 160, 31, 12)
fig.arrow((252, 149), (427, 149))
fig.arrow((597, 149), (724, 149))
fig.label(172, 225, "历史输入", size=23, bold=True)
fig.label(505, 225, "时空特征", size=23, bold=True)
fig.label(813, 225, "未来 12 步预测", size=23, bold=True)
fig.label(172, 257, "B × C × N × T", latin=True)
fig.label(505, 257, "B × C′ × N × T", latin=True)
fig.label(813, 257, "B × 12 × N × 1", latin=True)
fig.save(args.output)
