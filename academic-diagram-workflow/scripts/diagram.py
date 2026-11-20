"""Minimal editable SVG primitives for low-saturation academic schematics."""

import math
from pathlib import Path
from xml.etree import ElementTree as E


NS = "http://www.w3.org/2000/svg"
E.register_namespace("", NS)
PALETTES = {
    "blue": ("#506B82", "#E7EEF4", "#CFDCE7", "#AFC3D4"),
    "green": ("#426A65", "#E5EFED", "#CADCD8", "#ACC8C3"),
    "sand": ("#7B624C", "#F2EBE4", "#E7D8C9", "#CDB49D"),
    "plum": ("#74566E", "#F0E8EE", "#E0D1DD", "#C7B0C4"),
}


class Diagram:
    """Three layers keep connections behind objects and labels on top."""

    def __init__(self, width, height, title):
        self.svg = E.Element(f"{{{NS}}}svg", {"viewBox": f"0 0 {width} {height}",
                                               "width": str(width), "height": str(height)})
        self._add(self.svg, "title").text = title
        self.connections = self._add(self.svg, "g", id="connections")
        self.models = self._add(self.svg, "g", id="models")
        self.labels = self._add(self.svg, "g", id="labels")

    @staticmethod
    def _add(layer, name, **attrs):
        return E.SubElement(layer, f"{{{NS}}}{name}",
                            {key.replace("_", "-"): str(value) for key, value in attrs.items()})

    def _path(self, layer, points, ink, *, fill="none", close=False, weight=1.15):
        geometry = "M " + " L ".join(f"{x:.3f} {y:.3f}" for x, y in points)
        self._add(layer, "path", d=geometry + (" Z" if close else ""), fill=fill,
                  stroke=ink, stroke_width=weight)

    def arrow(self, *points, ink="#495963"):
        x, y = points[-1]
        px, py = points[-2]
        length = math.hypot(x-px, y-py)
        dx, dy = (x-px)/length, (y-py)/length
        back_x, back_y = x-8*dx, y-8*dy
        self._path(self.connections, points, ink, weight=1.65)
        self._path(self.connections, [(x, y), (back_x+3.5*dy, back_y-3.5*dx),
                                       (back_x-3.5*dy, back_y+3.5*dx)],
                   "none", fill=ink, close=True)

    def label(self, x, y, value, *, size=18, ink="#23303A", bold=False,
              anchor="middle", latin=False):
        self._add(self.labels, "text", x=x, y=y, fill=ink, font_size=size,
                  text_anchor=anchor, font_weight="bold" if bold else "normal",
                  font_family="Times New Roman" if latin else "Microsoft YaHei").text = value

    def heading(self, x, y, value, *, tint="blue", size=23):
        ink = PALETTES[tint][0]
        self._add(self.models, "rect", x=x, y=y-size*.83, width=4, height=size*.9, fill=ink)
        self.label(x+14, y, value, size=size, ink=ink, anchor="start", bold=True)

    def slab(self, x, y, w, h, *, tint="blue", depth=6, grid=None):
        ink, face, top, side = PALETTES[tint]
        self._path(self.models, [(x,y), (x+depth,y-depth), (x+w+depth,y-depth), (x+w,y)],
                   ink, fill=top, close=True)
        self._path(self.models, [(x+w,y), (x+w+depth,y-depth),
                                 (x+w+depth,y+h-depth), (x+w,y+h)],
                   ink, fill=side, close=True)
        self._add(self.models, "rect", x=x, y=y, width=w, height=h, fill=face,
                  stroke=ink, stroke_width=1.15)
        if grid is not None:
            columns, rows = grid
            for i in range(1, columns):
                mark = x+w*i/columns
                self._path(self.models, [(mark,y), (mark,y+h)], side, weight=.8)
            for i in range(1, rows):
                mark = y+h*i/rows
                self._path(self.models, [(x,mark), (x+w,mark)], side, weight=.8)

    def stack(self, x, y, w, h, *, tint="blue", count=3, step=7, grid=(5,3)):
        for i in reversed(range(count)):
            self.slab(x+i*step, y-i*step, w, h, tint=tint, grid=grid if i == 0 else None)

    def sequence(self, x, y, width, height, count, *, tint="plum"):
        step = width/count
        for i in reversed(range(count)):
            self.slab(x+i*step, y, step-2, height, tint=tint, depth=3.5)

    def save(self, path):
        E.indent(self.svg)
        E.ElementTree(self.svg).write(Path(path), encoding="utf-8", xml_declaration=True)
