"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright-core");

const ROOT = path.resolve(__dirname, "../website");
const SCREENSHOTS = path.resolve(__dirname, "../qa-screenshots");
const MIME = {
  "index.html": "text/html; charset=utf-8",
  "styles.css": "text/css; charset=utf-8",
  "app.js": "text/javascript; charset=utf-8",
  "dashboard_metrics.js": "text/javascript; charset=utf-8",
  "price_playground.js": "text/javascript; charset=utf-8",
  "data/dashboard.json": "application/json; charset=utf-8",
};

function createLocalServer() {
  return http.createServer((request, response) => {
    const uri = new URL(request.url, "http://127.0.0.1");
    const name = uri.pathname === "/" ? "index.html" : uri.pathname.slice(1);
    if (!Object.hasOwn(MIME, name)) {
      response.writeHead(404).end("Not found");
      return;
    }
    response.setHeader("Content-Type", MIME[name]);
    fs.createReadStream(path.join(ROOT, name)).pipe(response);
  });
}

test("PanganLens browser UX works at mobile, tablet and desktop widths", { timeout: 120000 }, async () => {
  const server = createLocalServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  let browser;
  try {
    browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--no-sandbox"] });
    fs.mkdirSync(SCREENSHOTS, { recursive: true });
    const address = "http://127.0.0.1:" + server.address().port;
    for (const width of [360, 768, 1440]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
      const page = await context.newPage();
      const pageErrors = [];
      page.on("pageerror", (error) => pageErrors.push(error.message));
      await page.goto(address, { waitUntil: "networkidle" });
      await page.locator("#data-notice:not(.hidden)").waitFor();
      assert.equal(await page.locator("#freshness-label").textContent(), "Belum dipublikasikan");
      assert.equal(await page.locator(".freshness-card").isVisible(), true);
      assert.equal(await page.locator("#price-calculator").isVisible(), true);
      assert.equal(await page.locator("#studi-kasus").isVisible(), true);
      assert.equal(await page.locator(".kpi-grid").isVisible(), false);
      const dims = await page.evaluate(() => ({
        pageWidth: document.documentElement.scrollWidth,
        viewportWidth: document.documentElement.clientWidth,
      }));
      assert.ok(dims.pageWidth <= dims.viewportWidth + 1,
        width + "px viewport overflows horizontally: " + JSON.stringify(dims));

      await page.locator(".skip-link").focus();
      const skip = await page.locator(".skip-link").boundingBox();
      assert.ok(skip && skip.y >= 0, "Keyboard skip link remains visible on focus");

      await page.screenshot({ path: path.join(SCREENSHOTS, "panganlens-" + width + ".png"), fullPage: true });
      await page.locator("#price-previous").fill("20000");
      await page.locator("#price-current").fill("22000");
      await page.locator("#price-average").fill("18000");
      await page.locator("#price-region").fill("21600");
      await page.getByRole("button", { name: "Hitung perbandingan" }).click();
      assert.match(await page.locator("#calc-movement").textContent(), /10,0\s*%/);
      assert.match(await page.locator("#calc-region").textContent(), /20,0\s*%/);
      assert.match(await page.locator("#calc-message").textContent(), /bukan data PIHPS/);
      await page.getByRole("button", { name: "Kosongkan" }).click();
      assert.equal(await page.locator("#calc-movement").textContent(), "Belum dihitung");
      assert.equal(await page.locator("#price-previous").inputValue(), "");
      assert.deepEqual(pageErrors, [], "Uncaught browser JS errors at " + width + "px");
      console.log("BROWSER_QA_PASS width=" + width + " status=preview calculator=ok overflow=none");
      await context.close();
    }
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
});
