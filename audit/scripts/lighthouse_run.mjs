// Lighthouse scorecard: node lighthouse_run.mjs BASE OUTDIR [label]
// Runs mobile (default emulation) and desktop for the main URLs, 1 run each,
// and writes scores + Core Web Vitals lab metrics to OUTDIR/<label>.json.
import lighthouse from "lighthouse";
import * as chromeLauncher from "chrome-launcher";
import fs from "fs";
const [BASE, OUT, LABEL = "lighthouse"] = process.argv.slice(2);
const PATHS = ["/", "/es/", "/tutorial.html", "/support.html", "/privacy.html", ...(process.env.EXTRA_PATHS || "").split(",").filter(Boolean)];
const chrome = await chromeLauncher.launch({ chromePath: process.env.CHROME_PATH, chromeFlags: ["--headless=new", "--no-sandbox"] });
const rows = [];
for (const form of ["mobile", "desktop"]) {
  for (const path of PATHS) {
    const config = form === "desktop" ? (await import("lighthouse/core/config/desktop-config.js")).default : undefined;
    const r = await lighthouse(BASE + path, { port: chrome.port, output: "json", logLevel: "error" }, config);
    const L = r.lhr, a = L.audits;
    const fails = Object.values(a).filter(x => x.score !== null && x.score < 1 && x.scoreDisplayMode !== "informative" && x.scoreDisplayMode !== "manual" && x.scoreDisplayMode !== "notApplicable")
      .map(x => `${x.id}(${x.score})`);
    const row = { form, path,
      performance: Math.round(L.categories.performance.score * 100), accessibility: Math.round(L.categories.accessibility.score * 100),
      bestPractices: Math.round(L.categories["best-practices"].score * 100), seo: Math.round(L.categories.seo.score * 100),
      lcp_ms: Math.round(a["largest-contentful-paint"].numericValue), cls: +a["cumulative-layout-shift"].numericValue.toFixed(3),
      tbt_ms: Math.round(a["total-blocking-time"].numericValue), fcp_ms: Math.round(a["first-contentful-paint"].numericValue),
      bytes_kb: Math.round(a["total-byte-weight"].numericValue / 1024), failing: fails };
    rows.push(row);
    console.log(`${form.padEnd(7)} ${path.padEnd(16)} P${row.performance} A${row.accessibility} BP${row.bestPractices} SEO${row.seo} LCP ${row.lcp_ms}ms CLS ${row.cls} TBT ${row.tbt_ms}ms ${row.bytes_kb}KB | ${fails.join(" ")}`);
  }
}
await chrome.kill();
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(`${OUT}/${LABEL}.json`, JSON.stringify(rows, null, 1));
