// Lighthouse scorecard: [RUNS=3] [PATHS=/,/es/] [EXTRA_PATHS=/x.html] node lighthouse_run.mjs BASE OUTDIR [label]
// Runs mobile (default emulation) and desktop for each URL, RUNS times each, and
// writes every run plus the per-page median (by Performance score, then LCP) to
// OUTDIR/<label>.json, and the median run's full Lighthouse report (screenshots
// stripped) to OUTDIR/<label>-lhr/<form>_<page>.json.
// Needs the `lighthouse` and `chrome-launcher` packages next to this script (or on NODE_PATH).
import lighthouse from "lighthouse";
import * as chromeLauncher from "chrome-launcher";
import fs from "fs";
const [BASE, OUT, LABEL = "lighthouse"] = process.argv.slice(2);
const RUNS = +(process.env.RUNS || 1);
const PATHS = (process.env.PATHS ? process.env.PATHS.split(",") : ["/", "/es/", "/tutorial.html", "/support.html", "/privacy.html"])
  .concat((process.env.EXTRA_PATHS || "").split(",").filter(Boolean));
const desktop = (await import("lighthouse/core/config/desktop-config.js")).default;
const median = xs => { const s = [...xs].sort((a, b) => a - b); return s[(s.length - 1) >> 1]; };
const runs = [], medians = [];
fs.mkdirSync(`${OUT}/${LABEL}-lhr`, { recursive: true });
for (const form of ["mobile", "desktop"]) {
  for (const path of PATHS) {
    // Fresh Chrome profile per page: Lighthouse does not clear localStorage, and a
    // saved UI language (voxly-ui) from /es/ would make later pages render Spanish.
    const chrome = await chromeLauncher.launch({ chromePath: process.env.CHROME_PATH, chromeFlags: ["--headless=new", "--no-sandbox"] });
    const mine = [];
    for (let i = 0; i < RUNS; i++) {
      const r = await lighthouse(BASE + path, { port: chrome.port, output: "json", logLevel: "error" }, form === "desktop" ? desktop : undefined);
      const L = r.lhr, a = L.audits, sc = k => Math.round((L.categories[k].score ?? 0) * 100);
      const nv = (id, f = Math.round) => a[id]?.numericValue === undefined ? null : f(a[id].numericValue);
      const fails = Object.values(a).filter(x => x.score !== null && x.score < 1 && !["informative", "manual", "notApplicable"].includes(x.scoreDisplayMode))
        .map(x => `${x.id}(${x.score})`);
      const row = { form, path, run: i + 1, performance: sc("performance"), accessibility: sc("accessibility"),
        bestPractices: sc("best-practices"), seo: sc("seo"),
        lcp_ms: nv("largest-contentful-paint"), cls: nv("cumulative-layout-shift", v => +v.toFixed(3)),
        tbt_ms: nv("total-blocking-time"), fcp_ms: nv("first-contentful-paint"),
        si_ms: nv("speed-index"), ttfb_ms: nv("server-response-time"),
        bytes_kb: nv("total-byte-weight", v => Math.round(v / 1024)), runtimeError: L.runtimeError?.code || null,
        lcpElement: a["largest-contentful-paint-element"]?.details?.items?.[0]?.items?.[0]?.node?.nodeLabel?.slice(0, 70) || null, failing: fails };
      for (const k of ["final-screenshot", "screenshot-thumbnails"]) delete a[k];
      delete L.fullPageScreenshot;
      mine.push({ row, lhr: L }); runs.push(row);
      console.log(`${form.padEnd(7)} ${path.padEnd(22)} #${i + 1} P${row.performance} A${row.accessibility} BP${row.bestPractices} SEO${row.seo} LCP ${row.lcp_ms}ms CLS ${row.cls} TBT ${row.tbt_ms}ms SI ${row.si_ms}ms ${row.bytes_kb}KB${row.runtimeError ? " ERR " + row.runtimeError : ""}`);
    }
    await chrome.kill();
    // Median per metric (the median-Performance run is kept as the representative full report)
    const rows = mine.map(m => m.row), m = { form, path, runs: RUNS };
    for (const k of ["performance", "accessibility", "bestPractices", "seo", "lcp_ms", "cls", "tbt_ms", "fcp_ms", "si_ms", "ttfb_ms", "bytes_kb"]) m[k] = median(rows.map(r => r[k]).filter(v => v !== null)) ?? null;
    const rep = mine.find(x => x.row.performance === m.performance) || mine[0];
    m.failing = rep.row.failing; m.lcpElement = rep.row.lcpElement;
    medians.push(m);
    fs.writeFileSync(`${OUT}/${LABEL}-lhr/${form}_${path.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "") || "home"}.json`, JSON.stringify(rep.lhr));
  }
}
fs.writeFileSync(`${OUT}/${LABEL}.json`, JSON.stringify({ base: BASE, date: new Date().toISOString(), runsPerPage: RUNS, medians, runs }, null, 1));
console.log("\nMEDIANS");
for (const m of medians) console.log(`${m.form.padEnd(7)} ${m.path.padEnd(22)} P${m.performance} A${m.accessibility} BP${m.bestPractices} SEO${m.seo} LCP ${m.lcp_ms}ms CLS ${m.cls} TBT ${m.tbt_ms}ms SI ${m.si_ms}ms`);
