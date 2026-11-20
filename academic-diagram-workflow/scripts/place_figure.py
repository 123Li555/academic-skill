"""Place a single native figure in a new, structurally verified PPTX."""

import argparse
import math
import posixpath
import shutil
import tempfile
from copy import copy, deepcopy
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from lxml import etree as E


NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
EMU_PER_PT = 12700


def q(local):
    prefix, tag = local.split(":")
    return f"{{{NS[prefix]}}}{tag}"


def child(parent, tag, **attrs):
    return E.SubElement(parent, q(tag), {k: str(v) for k, v in attrs.items()})


def parse_part(z, part):
    return E.fromstring(z.read(part), E.XMLParser(resolve_entities=False, no_network=True))


def read_presentation(z):
    p = parse_part(z, "ppt/presentation.xml")
    relationships = parse_part(z, "ppt/_rels/presentation.xml.rels")
    links = {r.get("Id"): r.get("Target") for r in relationships}
    slides = []
    for ref in p.findall("p:sldIdLst/p:sldId", NS):
        target = links[ref.get(q("r:id"))]
        slides.append(target.lstrip("/") if target.startswith("/") else
                      posixpath.normpath(posixpath.join("ppt", target)))
    size = p.find("p:sldSz", NS)
    return slides, (int(size.get("cx")), int(size.get("cy")))


def sp_tree(slide):
    return slide.find("p:cSld/p:spTree", NS)


def choose_picture(tree, target_id):
    if target_id is None:
        pics = tree.findall("p:pic", NS)
        if len(pics) == 1:
            return pics[0]
        ids = [s.find("p:nvPicPr/p:cNvPr", NS).get("id") for s in pics]
        raise ValueError(f"Expected one top-level picture, found IDs {ids}. Use --shape-id.")
    for shape in tree:
        properties = shape.find("./*/p:cNvPr", NS)
        if properties is None or properties.get("id") != str(target_id):
            continue
        if shape.tag == q("p:pic"):
            return shape
        if shape.tag == q("p:grpSp"):
            items = [item for item in shape if item.tag not in {
                q("p:nvGrpSpPr"), q("p:grpSpPr")}]
            if items and all(item.tag == q("p:pic") for item in items):
                return shape
        raise ValueError("The selected ID must be a top-level picture or a picture-only group.")
    raise ValueError(f"No top-level shape with ID {target_id}.")


def placement(shape, box, slide_size):
    if box is not None:
        if not all(math.isfinite(v) for v in box):
            raise ValueError("--box values must be finite.")
        x, y, w, h = (round(v * EMU_PER_PT) for v in box)
    else:
        tag = "grpSpPr" if shape.tag == q("p:grpSp") else "spPr"
        xf = shape.find(f"p:{tag}/a:xfrm", NS)
        if xf is None or int(xf.get("rot", "0")) or any(
            xf.get(key) in {"1", "true"} for key in ("flipH", "flipV")
        ):
            raise ValueError("Specify --box for a picture with a missing, rotated, or flipped transform.")
        off, ext = xf.find("a:off", NS), xf.find("a:ext", NS)
        if off is None or ext is None:
            raise ValueError("Specify --box for a picture without a complete transform.")
        x, y = (int(off.get(k)) for k in ("x", "y"))
        w, h = (int(ext.get(k)) for k in ("cx", "cy"))
    if min(x, y) < 0 or min(w, h) <= 0 or x + w > slide_size[0] or y + h > slide_size[1]:
        raise ValueError("The image box must be positive and inside the target slide.")
    return x, y, w, h


def scale_fonts(shape, factor):
    font_specs = [
        ("latin", "Times New Roman", {"ea", "cs"}),
        ("ea", "Microsoft YaHei", {"cs"}),
        ("cs", "Times New Roman", set()),
    ]
    for pr in shape.xpath(".//a:rPr|.//a:defRPr|.//a:endParaRPr", namespaces=NS):
        if "sz" in pr.attrib:
            pr.set("sz", str(max(100, round(int(pr.get("sz")) * factor))))
        for field, font, following in font_specs:
            member = pr.find(q(f"a:{field}"))
            if member is None:
                member = E.Element(q(f"a:{field}"))
                after = following | {"sym", "hlinkClick", "hlinkMouseOver", "extLst"}
                index = next((i for i, node in enumerate(pr) if E.QName(node).localname in after), len(pr))
                pr.insert(index, member)
            member.set("typeface", font)


def native_group(tree, picture, donor_tree, donor_size, box):
    native_tags = {q(f"p:{tag}") for tag in ("sp", "cxnSp", "grpSp")}
    canvas_props = {q(f"p:{tag}") for tag in ("nvGrpSpPr", "grpSpPr", "extLst")}
    items = [deepcopy(s) for s in donor_tree if s.tag not in canvas_props]
    if not items or any(s.tag not in native_tags for s in items):
        raise ValueError("The figure slide must contain only native editable shapes.")
    new_id = max(int(s.get("id")) for s in tree.iter(q("p:cNvPr"))) + 1
    ids = {}
    for shape in items:
        for node in shape.iter():
            if node.tag in {q(f"p:{tag}") for tag in ("pic", "graphicFrame", "contentPart", "ph")}:
                raise ValueError("Embedded media, chart objects and placeholders cannot be placed.")
            if any(attr.startswith("{" + NS["r"] + "}") for attr in node.attrib):
                raise ValueError("The figure has an external dependency. Use native shapes and text.")
        for nv in shape.iter(q("p:cNvPr")):
            old_id = nv.get("id")
            if old_id in ids:
                raise ValueError(f"Duplicate figure shape ID {old_id}.")
            ids[old_id] = str(new_id)
            nv.set("id", str(new_id))
            new_id += 1
    x, y, box_w, box_h = box
    source_w, source_h = donor_size
    factor = min(box_w / source_w, box_h / source_h)
    w, h = round(source_w * factor), round(source_h * factor)
    grp = E.Element(q("p:grpSp"))
    nv = child(grp, "p:nvGrpSpPr")
    picture_id = picture.find("./*/p:cNvPr", NS).get("id")
    child(nv, "p:cNvPr", id=picture_id, name="科研架构图（可编辑）")
    child(nv, "p:cNvGrpSpPr")
    child(nv, "p:nvPr")
    xf = child(child(grp, "p:grpSpPr"), "a:xfrm")
    child(xf, "a:off", x=x + (box_w - w) // 2, y=y + (box_h - h) // 2)
    child(xf, "a:ext", cx=w, cy=h)
    child(xf, "a:chOff", x=0, y=0)
    child(xf, "a:chExt", cx=source_w, cy=source_h)
    for shape in items:
        for conn in shape.xpath(".//a:stCxn|.//a:endCxn", namespaces=NS):
            if conn.get("id") not in ids:
                raise ValueError("The figure includes a connector to a shape outside the drawing.")
            conn.set("id", ids[conn.get("id")])
        for effect in shape.xpath(".//a:effectRef", namespaces=NS):
            effect.set("idx", "0")
        # PowerPoint applies group scaling to shape geometry, not explicit run sizes.
        scale_fonts(shape, factor)
        grp.append(shape)
    return grp, picture_id, len(ids)


def place(original, donor, staged, page, target_id, box):
    if staged.exists():
        raise ValueError(f"Choose a new staged file: {staged}")
    staged.parent.mkdir(parents=True, exist_ok=True)
    with (ZipFile(original) as base, ZipFile(donor) as source,
          tempfile.TemporaryDirectory(prefix=".figure-stage-", dir=staged.parent) as tmp):
        slides, slide_size = read_presentation(base)
        donor_slides, donor_size = read_presentation(source)
        if not 1 <= page <= len(slides) or len(donor_slides) != 1:
            raise ValueError("Choose an existing destination page and a one-slide figure PPTX.")
        if min(donor_size) <= 0:
            raise ValueError("The figure slide size must be positive.")
        target = slides[page - 1]
        body = parse_part(base, target)
        tree = sp_tree(body)
        old = choose_picture(tree, target_id)
        box = placement(old, box, slide_size)
        group, shape_id, count = native_group(tree, old, sp_tree(parse_part(source, donor_slides[0])),
                                              donor_size, box)
        unchanged = [E.tostring(e, method="c14n") for e in tree if e is not old]
        tree.replace(old, group)
        if [E.tostring(e, method="c14n") for e in tree if e is not group] != unchanged:
            raise ValueError("An unrelated object on the target slide changed.")
        updated_xml = E.tostring(body, encoding="UTF-8", xml_declaration=True, standalone=True)
        temp_path = Path(tmp) / "checked.pptx"
        with ZipFile(temp_path, "w") as out:
            for entry in base.infolist():
                out.writestr(copy(entry), updated_xml if entry.filename == target else base.read(entry))
        with ZipFile(temp_path) as check:
            changed = [key for key in base.namelist() if base.read(key) != check.read(key)]
            if check.testzip() is not None or changed != [target] or read_presentation(check) != (slides, slide_size):
                raise ValueError("PPTX validation failed. Only the designated page may change.")
        with temp_path.open("rb") as data, staged.open("xb") as result:
            try:
                shutil.copyfileobj(data, result)
            except OSError:
                result.close()
                staged.unlink(missing_ok=True)
                raise
    print(f"{staged} | page {page} | shape {shape_id} | {count} editable objects")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("input", type=Path)
    cli.add_argument("figure", type=Path)
    cli.add_argument("staged", type=Path)
    cli.add_argument("--page", type=int, required=True)
    cli.add_argument("--shape-id", type=int)
    cli.add_argument("--box", type=float, nargs=4, metavar=("X", "Y", "W", "H"),
                     help="Placement in PowerPoint points from the slide's upper left.")
    args = cli.parse_args()
    try:
        place(args.input, args.figure, args.staged, args.page, args.shape_id, args.box)
    except (OSError, ValueError, KeyError, BadZipFile, E.XMLSyntaxError) as issue:
        cli.exit(1, f"Placement failed: {issue}\n")


if __name__ == "__main__":
    main()
