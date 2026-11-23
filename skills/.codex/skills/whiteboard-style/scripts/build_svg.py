# -*- coding: utf-8 -*-
"""一键重建 13 张 SVG 画板图源：python3 build_svg.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diagrams1
import diagrams2
import diagrams3

for fn in (diagrams1.architecture, diagrams1.flowchart, diagrams1.organization, diagrams1.swimlane,
           diagrams2.fishbone, diagrams2.funnel, diagrams2.pyramid, diagrams2.milestone, diagrams2.comparison,
           diagrams3.bar_chart, diagrams3.line_chart, diagrams3.treemap, diagrams3.flywheel):
    fn()

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "svg")
print("13 svg written to", out)
