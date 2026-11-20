const path = require("node:path");
const { pathToFileURL } = require("node:url");

async function main() {
  const [input, output, runtimeModules, browserExecutable] = process.argv.slice(2);
  if (!input || !output || !runtimeModules) {
    throw new Error("Usage: node preview_svg.cjs INPUT.svg OUTPUT.png NODE_MODULES_DIR [BROWSER_EXE]");
  }
  const { chromium } = require(path.resolve(runtimeModules, "playwright"));
  const browser = await chromium.launch({ executablePath: browserExecutable, headless: true });
  try {
    const page = await browser.newPage({ deviceScaleFactor: 2 });
    await page.goto(pathToFileURL(path.resolve(input)).href);
    const svg = page.locator("svg");
    const bounds = await svg.evaluate(node => {
      const { width, height } = node.viewBox.baseVal;
      const outside = [...node.querySelectorAll("text")].flatMap(text => {
        const { x, y, width: w, height: h } = text.getBBox();
        return x < 0 || y < 0 || x + w > width || y + h > height
          ? [text.textContent] : [];
      });
      return { width, height, outside };
    });
    await page.setViewportSize({ width: Math.ceil(bounds.width) + 32, height: Math.ceil(bounds.height) + 32 });
    await svg.screenshot({ path: path.resolve(output) });
    console.log(JSON.stringify({ textOutsideCanvas: bounds.outside }));
    if (bounds.outside.length) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
