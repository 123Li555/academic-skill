"""Collect editable primitives from a zero-origin SVG for the native PPTX exporter."""

import argparse
import json
import math
import re
from pathlib import Path
from xml.etree import ElementTree as ET


PRIMITIVES = {"rect", "path", "circle", "ellipse", "text", "line", "polygon", "polyline"}
METADATA = {"svg", "g", "title", "desc", "metadata"}
UNSUPPORTED = {"style", "transform", "clip-path", "mask", "filter", "opacity",
               "fill-opacity", "stroke-opacity", "stroke-dasharray", "marker-start", "marker-end"}


def collect(svg_path, allow_outer_frame):
    svg = ET.parse(svg_path).getroot()
    if not svg.tag.endswith("}svg"):
        raise ValueError("Input must be an SVG document.")
    raw_view = re.split(r"[ ,]+", svg.get("viewBox", "").strip())
    if len(raw_view) != 4:
        raise ValueError("Use viewBox='0 0 WIDTH HEIGHT'.")
    x, y, width, height = [float(n) for n in raw_view]
    if x or y or not all(math.isfinite(v) and v > 0 for v in (width, height)):
        raise ValueError("Use a positive, zero-origin SVG viewBox.")

    items = []
    for element in svg.iter():
        kind = element.tag.rsplit("}", 1)[-1]
        attrs = dict(element.attrib)
        if UNSUPPORTED.intersection(attrs) or any(v.startswith("url(") for v in attrs.values()):
            raise ValueError(f"Flatten SVG styles, transforms and effects on {kind} {attrs.get('id', '')}.")
        if kind in METADATA:
            if kind in {"svg", "g"} and set(attrs).intersection({"fill", "stroke", "font-family", "font-size"}):
                raise ValueError("Set editable paint and fonts on the visible primitives.")
            continue
        if kind not in PRIMITIVES:
            raise ValueError(f"Native export does not support <{kind}>.")
        if kind == "rect" and attrs.get("stroke", "none") not in ("none", "transparent"):
            rx, ry, rw, rh = (float(attrs.get(field, 0)) for field in ("x", "y", "width", "height"))
            canvas_frame = rx <= .04*width and ry <= .04*height and (
                rw >= .92*width and rh >= .92*height)
            marked_frame = attrs.get("data-role") in {"outer-frame", "section-frame"}
            if (canvas_frame or marked_frame) and not allow_outer_frame:
                raise ValueError("Remove the enclosing border or explicitly allow outer frames.")
        if kind == "text":
            if len(element):
                raise ValueError("Use separate editable <text> elements for lines and subscripts.")
            attrs["text"] = element.text or ""
            if not attrs["text"].strip():
                continue
        items.append({"kind": kind, **attrs})
    if not items:
        raise ValueError("The SVG contains no supported visible objects.")
    return {"width": width, "height": height, "items": items}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--allow-outer-frame", action="store_true")
    args = parser.parse_args()
    try:
        figure = collect(args.input, args.allow_outer_frame)
        args.output.write_text(json.dumps(figure, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError, ET.ParseError) as error:
        parser.error(str(error))
    print(f"{len(figure['items'])} editable primitives")
