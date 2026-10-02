// Run after generating a dump: pnpm exec node tests/scalars-browser/run.mjs /tmp/scalars-performance.json
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";
import { chromium } from "playwright";

const root = fileURLToPath(new URL("../..", import.meta.url));
const fixture = JSON.parse(await fs.readFile(process.argv[2], "utf8"));
const names = Object.keys(fixture.data[0].scalars).sort();
const experiments = fixture.data.map((entry, index) => ({ id: entry.experiment_id, name: `Experiment ${index}`, createdAt: "2026-01-01T00:00:00Z" }));
const timestamp = (step) => new Date(Date.UTC(2026, 0, 1, 0, 0, step)).toISOString();
const initialStep = Math.max(...fixture.data[0].scalars[names[1]].x);
let step = initialStep;
const server = await createServer({
  root, configFile: false, server: { host: "127.0.0.1", port: 0 },
  resolve: { alias: { "@": path.join(root, "src") } }, esbuild: { jsx: "automatic" },
  define: { "process.env": "{}" },
});
await server.listen();
const origin = `http://127.0.0.1:${server.httpServer.address().port}`;
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome", headless: true, args: ["--no-sandbox"] });
const results = {};
try {
  for (const mode of ["baseline", "improved"]) {
    const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    let requests = 0, bytes = 0;
    const requestedNames = new Set();
    await page.route("**/catalog.json", (route) => route.fulfill({ json: { names, experiments } }));
    await page.route("**/api/scalars/**", async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname.includes("last_logged")) {
        return route.fulfill({ json: { data: experiments.map((experiment) => ({ experiment_id: experiment.id, last_modified: timestamp(step) })), hasNext: false, size: experiments.length, total: experiments.length } });
      }
      const selected = url.searchParams.getAll("scalar_name");
      for (const name of selected) requestedNames.add(name);
      const start = url.searchParams.get("start_time");
      const lower = start ? (Date.parse(start) - Date.parse(timestamp(0))) / 1000 : 0;
      const data = fixture.data.map((entry) => ({ ...entry, scalars: Object.fromEntries(Object.entries(entry.scalars).filter(([name]) => !selected.length || selected.includes(name)).map(([name, series]) => {
        const x = series.x.filter((value) => value >= lower);
        const y = series.y.filter((_, index) => series.x[index] >= lower);
        for (let value = initialStep + 1; value <= step; value++) { x.push(value); y.push(Math.sin(value / 30)); }
        return [name, { x, y }];
      })) }));
      const body = JSON.stringify({ ...fixture, data }); requests++; bytes += Buffer.byteLength(body);
      return route.fulfill({ contentType: "application/json", body });
    });
    const started = performance.now();
    await page.goto(`${origin}/tests/scalars-browser/index.html${mode === "baseline" ? "?baseline" : ""}`);
    await page.waitForFunction(() => document.querySelectorAll(".js-plotly-plot").length > 0, { timeout: 60000 });
    await page.waitForTimeout(1500);
    results[mode] = { scalarRequests: requests, scalarBytes: bytes, mountedCharts: await page.locator(".js-plotly-plot").count(), preparationMs: await page.evaluate(() => window.scalarBench.preparationMs), loadMs: Math.round(performance.now() - started) };
    if (mode === "improved") {
      assert(results.improved.mountedCharts < 12);
      assert(requestedNames.size < 12);
      const scroll = page.locator("[data-scalar-scroll-root]");
      const firstPlot = page.locator(`[data-scalar-placeholder="${names[1]}"] .js-plotly-plot`);
      await firstPlot.evaluate((element) => element.emit("plotly_relayout", { "xaxis.range[0]": 100, "xaxis.range[1]": 200 }));
      await page.waitForFunction((name) => document.querySelector(`[data-scalar-placeholder="${name}"] .js-plotly-plot`)._fullLayout.xaxis.range[1] === 200, names[1]);
      const maxMounted = await page.evaluate(async () => {
        const scroll = document.querySelector("[data-scalar-scroll-root]");
        let maximum = 0;
        for (let top = 0; top < scroll.scrollHeight; top += 350) {
          scroll.scrollTop = top;
          await new Promise((resolve) => setTimeout(resolve, 100));
          maximum = Math.max(maximum, document.querySelectorAll(".js-plotly-plot").length);
        }
        return maximum;
      });
      results.improved.maxMountedWhileScrolling = maxMounted;
      assert(maxMounted < 12);
      await scroll.evaluate((element) => { element.scrollTop = 0; });
      await page.getByRole("button", { name: "Next", exact: true }).click();
      await page.waitForSelector(`[data-scalar-placeholder="${names[12]}"] .js-plotly-plot`);
      step += 20;
      await page.getByRole("button", { name: "Previous", exact: true }).click();
      await page.waitForFunction(({ name, step }) => window.scalarBench.steps[name]?.at(-1) === step, { name: names[1], step });
      const steps = await page.evaluate((name) => window.scalarBench.steps[name], names[1]);
      assert.equal(steps[0], 0); assert.equal(steps.at(-1), step);
      assert(Math.max(...steps.slice(1).map((value, index) => value - steps[index])) <= 3);
      await page.waitForFunction((name) => document.querySelector(`[data-scalar-placeholder="${name}"] .js-plotly-plot`)._fullLayout.xaxis.range[1] === 200, names[1]);
      await page.getByTestId(`button-expand-${names[1]}`).click();
      await page.waitForSelector('[role="dialog"] .js-plotly-plot');
      await page.getByRole("button", { name: "Close fullscreen" }).click();
      results.improved.restoredLastStep = steps.at(-1);
    }
    assert.deepEqual(errors, []);
    await page.close();
  }
  assert(results.improved.scalarBytes < results.baseline.scalarBytes / 2);
  console.log(JSON.stringify(results, null, 2));
} finally { await browser.close(); await server.close(); }
