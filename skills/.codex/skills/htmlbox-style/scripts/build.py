# -*- coding: utf-8 -*-
import os, sys, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
mods = ["g1", "g2", "g3", "g4"]
charts = {}
for m in mods:
    mod = importlib.import_module(m)
    charts.update(mod.CHARTS)
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "html")
os.makedirs(out, exist_ok=True)
for name, html in charts.items():
    with open(os.path.join(out, name + ".html"), "w", encoding="utf-8") as f:
        f.write(html)
print(len(charts), "files written")
for n in charts: print(n)
