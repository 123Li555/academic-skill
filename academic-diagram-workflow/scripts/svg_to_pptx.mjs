import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const [preparedJson, outputPptx, runtimeModules] = process.argv.slice(2);
if (!preparedJson || !outputPptx || !runtimeModules) {
  throw new Error("Usage: node svg_to_pptx.mjs INPUT.json OUTPUT.pptx NODE_MODULES_DIR");
}
const requireRuntime = createRequire(path.join(path.dirname(path.resolve(runtimeModules)), "diagram.cjs"));
const { Presentation, PresentationFile } = await import(
  pathToFileURL(requireRuntime.resolve("@oai/artifact-tool")).href
);
const { width, height, items } = JSON.parse(await fs.readFile(preparedJson, "utf8"));
const pres = Presentation.create({ slideSize: { width, height } });

function pos(left, top, width, height) {
  return { left, top, width, height };
}

function custom(slide, vertices, close, options) {
  const minX = Math.min(...vertices.map(([x]) => x));
  const minY = Math.min(...vertices.map(([, y]) => y));
  const width = Math.max(.05, Math.max(...vertices.map(([x]) => x)) - minX);
  const height = Math.max(.05, Math.max(...vertices.map(([, y]) => y)) - minY);
  const commands = vertices.map(([x, y], index) => ({
    [index === 0 ? "moveTo" : "lineTo"]: { x: x - minX, y: y - minY },
  }));
  if (close) commands.push({ close: {} });
  return slide.shapes.add({
    ...options,
    geometry: "custom",
    position: pos(minX, minY, width, height),
    customPaths: [{ width, height, commands }],
  });
}

function add(slide, e, index) {
  const number = key => Number(e[key] ?? 0);
  const fill = e.fill ?? (e.kind === "text" ? "#000000" : "none");
  const line = {
    style: "solid",
    fill: e.stroke ?? "none",
    width: e.stroke && e.stroke !== "none" ? Number(e["stroke-width"] ?? 1) : 0,
  };
  const name = e.id ?? `Figure element ${index}`;
  const options = { name, fill, line };
  if (e.kind === "text") {
    const size = number("font-size") || 16;
    const width = Math.max(size * 2, size * e.text.length * 1.07);
    const anchor = e["text-anchor"] ?? "start";
    const offset = { start: 0, middle: width / 2, end: width }[anchor] ?? 0;
    const shape = slide.shapes.add({
      ...options, geometry: "textbox", fill: "none",
      position: pos(number("x") - offset, number("y") - size * 1.045, width, size * 1.45),
    });
    shape.text = e.text;
    shape.text.style = {
      fontSize: size, typeface: (e["font-family"] ?? "Times New Roman").split(",")[0].replaceAll("'", "").trim(),
      color: fill, bold: e["font-weight"] === "bold" || Number(e["font-weight"]) >= 600,
      italic: e["font-style"] === "italic",
      alignment: { start: "left", middle: "center", end: "right" }[anchor] ?? "left",
      verticalAlignment: "top", insets: 0, wrap: "none", autoFit: "none",
    };
    return;
  }
  if (e.kind === "rect") {
    const width = number("width");
    const height = number("height");
    const round = number("rx");
    const shape = slide.shapes.add({
      ...options, geometry: round ? "roundRect" : "rect",
      position: pos(number("x"), number("y"), width, height),
    });
    if (round) {
      shape.adjustmentList = [{ name: "adj", formula: `val ${Math.round(100000 * round / Math.min(width, height))}` }];
    }
    return;
  }
  if (e.kind === "circle" || e.kind === "ellipse") {
    const rx = number(e.kind === "circle" ? "r" : "rx");
    const ry = number(e.kind === "circle" ? "r" : "ry");
    slide.shapes.add({
      ...options, geometry: "ellipse",
      position: pos(number("cx") - rx, number("cy") - ry, 2 * rx, 2 * ry),
    });
    return;
  }
  if (e.kind === "line") {
    custom(slide, [[number("x1"), number("y1")], [number("x2"), number("y2")]], false, options);
    return;
  }
  const value = e.kind === "path" ? e.d : e.points;
  if (e.kind === "path" && (!/^\s*M/.test(value) || (value.match(/M/g) ?? []).length !== 1 ||
      [...value.matchAll(/[a-zA-Z]/g)].some(([command]) => !"MLZ".includes(command)))) {
    throw new Error(`Unsupported path commands in ${name}: ${value}`);
  }
  const numbers = value.match(/[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?/g).map(Number);
  if (numbers.length < 4 || numbers.length % 2) throw new Error(`Malformed path in ${name}`);
  const vertices = [];
  for (let pair = 0; pair < numbers.length; pair += 2) vertices.push(numbers.slice(pair, pair + 2));
  custom(slide, vertices, e.kind === "polygon" || /Z\s*$/.test(value), options);
}

const slide = pres.slides.add();
items.forEach((e, i) => add(slide, e, i + 1));
const file = await PresentationFile.exportPptx(pres);
await file.save(path.resolve(outputPptx));
