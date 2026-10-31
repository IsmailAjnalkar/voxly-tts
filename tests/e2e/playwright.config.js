// Functional-preservation suite. Env: BASE (default http://localhost:8804),
// BROWSER=chromium|firefox|webkit, NO_GENERATE=1 (skip speech-service calls),
// E2E_JSON (JSON report path, default results/results.json).
const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: __dirname,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  // One worker: no parallel load on the speech service, stable ordering.
  workers: 1,
  fullyParallel: false,
  retries: 0, // the external-service step retries itself once (see generate() in the spec)
  outputDir: "results/artifacts",
  reporter: [["list"], ["json", { outputFile: process.env.E2E_JSON || "results/results.json" }]],
  use: {
    baseURL: process.env.BASE || "http://localhost:8804",
    browserName: process.env.BROWSER || "chromium",
    viewport: { width: 1280, height: 900 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
});
