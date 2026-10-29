// Browser audit: node audit.mjs BASE OUTDIR
import { chromium, devices } from "playwright";
import AxeBuilder from "@axe-core/playwright";
import fs from "fs";
import path from "path";

const BASE = process.argv[2].replace(/\/$/, "");
const OUT = process.argv[3];
fs.mkdirSync(path.join(OUT, "shots"), { recursive: true });
const R = { viewports: [], axe: {}, perf: {}, e2e: [], console: [], pages: {} };
const log = (k, ok, detail) => { R.e2e.push({ check: k, result: ok, detail }); console.log((ok === true ? "PASS" : ok === false ? "FAIL" : "INFO"), k, detail ?? ""); };

const browser = await chromium.launch();
const PAGES = ["/", "/tutorial.html", "/donate.html", "/support.html", "/auth.html", "/privacy.html", "/terms.html"];

// ---------- 1. responsive sweep ----------
for (const w of [320, 375, 390, 430, 768, 1024, 1280, 1440, 1920]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, hasTouch: w < 768 });
  const page = await ctx.newPage();
  await page.goto(BASE + "/", { waitUntil: "networkidle" });
  await page.waitForSelector("#voicelist .vrow", { timeout: 20000 }).catch(() => {});
  const m = await page.evaluate(() => {
    const de = document.documentElement;
    const vw = de.clientWidth;
    const over = [...document.querySelectorAll("body *")].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.right > vw + 1 && getComputedStyle(e).position !== "fixed"; })
      .slice(0, 8).map(e => `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}${e.className && typeof e.className === "string" ? "." + e.className.split(" ")[0] : ""} right=${Math.round(e.getBoundingClientRect().right)}`);
    const small = [...document.querySelectorAll("a,button,input,select,textarea,[role=button]")].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.width < 24 || r.height < 24); })
      .slice(0, 10).map(e => `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""} "${(e.textContent || e.value || "").trim().slice(0, 15)}" ${Math.round(e.getBoundingClientRect().width)}x${Math.round(e.getBoundingClientRect().height)}`);
    const nav = document.querySelector(".mainnav"); const burger = document.querySelector("#burger");
    return { scrollW: de.scrollWidth, clientW: vw, hOverflow: de.scrollWidth > vw, over, smallTargets: small,
      navVisible: nav && getComputedStyle(nav).display !== "none", burgerVisible: burger && getComputedStyle(burger).display !== "none",
      genBtnVisible: !!document.querySelector("#genbtn")?.getBoundingClientRect().width };
  });
  await page.screenshot({ path: path.join(OUT, "shots", `home_${w}.png`), fullPage: false });
  R.viewports.push({ width: w, ...m });
  console.log("viewport", w, "overflow", m.hOverflow, m.scrollW, "small", m.smallTargets.length, "nav", m.navVisible, "burger", m.burgerVisible);
  await ctx.close();
}

// ---------- 2. axe on every page (dark default) + home light ----------
for (const p of PAGES) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  page.on("console", m => { if (m.type() === "error") R.console.push({ page: p, text: m.text() }); });
  page.on("pageerror", e => R.console.push({ page: p, text: "pageerror: " + e.message }));
  const resp = await page.goto(BASE + p, { waitUntil: "networkidle" });
  if (p === "/") await page.waitForSelector("#voicelist .vrow", { timeout: 20000 }).catch(() => {});
  const res = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  R.axe[p] = res.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length, sample: v.nodes.slice(0, 3).map(n => n.target.join(" ")) }));
  R.pages[p] = await page.evaluate(() => ({ title: document.title, brand: document.querySelector(".brand")?.textContent.trim().slice(0, 40), h1: document.querySelector("h1")?.textContent.trim(), lang: document.documentElement.lang }));
  R.pages[p].status = resp.status();
  await page.screenshot({ path: path.join(OUT, "shots", `page_${p === "/" ? "home" : p.slice(1, -5)}.png`), fullPage: true });
  console.log("axe", p, R.axe[p].map(v => `${v.id}(${v.impact},${v.nodes})`).join(" "));
  await ctx.close();
}
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await ctx.addInitScript(() => localStorage.setItem("voxly-theme", "light"));
  const page = await ctx.newPage();
  await page.goto(BASE + "/", { waitUntil: "networkidle" });
  await page.waitForSelector("#voicelist .vrow", { timeout: 20000 }).catch(() => {});
  const res = await new AxeBuilder({ page }).withTags(["wcag2aa"]).analyze();
  R.axe["/ (light theme)"] = res.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length, sample: v.nodes.slice(0, 3).map(n => n.target.join(" ")) }));
  await page.screenshot({ path: path.join(OUT, "shots", "home_light.png") });
  await ctx.close();
}

// ---------- 3. performance (cold, mobile-ish & desktop) ----------
for (const [label, opts] of [["desktop", { viewport: { width: 1440, height: 900 } }], ["mobile", { ...devices["Moto G4"] }]]) {
  const ctx = await browser.newContext(opts);
  const page = await ctx.newPage();
  await page.addInitScript(() => {
    window.__lcp = 0; window.__cls = 0;
    new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lcp = e.startTime; }).observe({ type: "largest-contentful-paint", buffered: true });
    new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({ type: "layout-shift", buffered: true });
  });
  const t0 = Date.now();
  await page.goto(BASE + "/", { waitUntil: "load" });
  await page.waitForSelector("#voicelist .vrow", { timeout: 20000 }).catch(() => {});
  const voicesReady = Date.now() - t0;
  await page.waitForTimeout(1500);
  const p = await page.evaluate(() => {
    const n = performance.getEntriesByType("navigation")[0];
    const res = performance.getEntriesByType("resource").map(r => ({ name: r.name.replace(location.origin, ""), kb: Math.round(r.transferSize / 1024), ms: Math.round(r.duration) }));
    const fcp = performance.getEntriesByName("first-contentful-paint")[0]?.startTime;
    return { ttfb: Math.round(n.responseStart), domContentLoaded: Math.round(n.domContentLoadedEventEnd), load: Math.round(n.loadEventEnd),
      htmlTransferKB: Math.round(n.transferSize / 1024), fcp: Math.round(fcp), lcp: Math.round(window.__lcp), cls: +window.__cls.toFixed(4), resources: res };
  });
  // INP proxy: time from click on a voice row to next paint
  const inp = await page.evaluate(async () => {
    const row = document.querySelectorAll("#voicelist .vrow")[3]; if (!row) return null;
    const t = performance.now(); row.click(); await new Promise(r => requestAnimationFrame(() => setTimeout(r, 0))); return Math.round(performance.now() - t);
  });
  R.perf[label] = { ...p, voicesReadyMs: voicesReady, interactionToPaintMs: inp };
  console.log("perf", label, JSON.stringify({ ...p, resources: p.resources.length, voicesReady, inp }));
  await ctx.close();
}

// ---------- 4. functional E2E on production (bounded: 3 generations) ----------
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage();
  const ttsCalls = [];
  page.on("request", r => { if (r.url().includes("/api/tts")) ttsCalls.push(Date.now()); });
  page.on("pageerror", e => R.console.push({ page: "e2e", text: "pageerror: " + e.message }));
  await page.goto(BASE + "/", { waitUntil: "networkidle" });
  await page.waitForSelector("#voicelist .vrow", { timeout: 20000 });

  log("cookie banner shown on first visit", await page.isVisible("#cookie"));
  const langCount = await page.locator("#langsel option").count();
  log("language dropdown lists 75 languages", langCount === 75, langCount);
  log("default language English", (await page.inputValue("#langsel")) === "en");
  const sel = await page.locator("#voicelist .vrow.sel .nm").textContent();
  log("a default voice is preselected", !!sel, sel);
  log("generate disabled on empty text", await page.isDisabled("#genbtn"));
  log("preview disabled on empty text", await page.isDisabled("#previewbtn"));

  // counter accuracy
  await page.fill("#text", "Hi 😀\nline2");
  const counter = await page.textContent("#counter");
  log("counter counts characters (emoji = 1 char, 'Hi 😀\\nline2' = 10)", /^10 /.test(counter), counter);
  await page.fill("#text", "");

  // gender filter + search
  const all = await page.locator("#voicelist .vrow").count();
  await page.click('#genderseg button[data-g="Female"]');
  const fem = await page.locator("#voicelist .vrow").count();
  await page.click('#genderseg button[data-g="Male"]');
  const male = await page.locator("#voicelist .vrow").count();
  await page.click('#genderseg button[data-g="All"]');
  log("gender filter partitions English voices", fem + male === all && fem > 0 && male > 0, { all, fem, male });
  await page.fill("#vsearch", "aria");
  const aria = await page.locator("#voicelist .vrow .nm").allTextContents();
  log("search 'aria' finds Aria", aria.some(t => t.includes("Aria")), aria);
  await page.fill("#vsearch", "united states");
  log("search 'united states' finds voices", (await page.locator("#voicelist .vrow").count()) > 0);
  await page.fill("#vsearch", "zzzz");
  const none = await page.locator("#voicelist .vrow").count();
  const emptyMsg = await page.locator("#voicelist").textContent();
  log("no-match search shows an empty-state message", none === 0 && emptyMsg.trim().length > 0, JSON.stringify(emptyMsg.trim()));
  await page.fill("#vsearch", "");
  const dupNames = await page.evaluate(() => { const n = [...document.querySelectorAll("#voicelist .nm")].map(e => e.textContent); return n.filter((x, i) => n.indexOf(x) !== i); });
  log("voice labels are unique within English", dupNames.length === 0, dupNames);

  // language switch
  await page.selectOption("#langsel", "hi");
  const hiVoices = await page.locator("#voicelist .vrow .nm").allTextContents();
  log("switching to Hindi lists Hindi voices", hiVoices.length > 0 && hiVoices.every(t => t.endsWith("IN")), hiVoices);
  await page.selectOption("#langsel", "en");

  // keyboard selection of a voice row
  const rows = page.locator("#voicelist .vrow");
  const target = await rows.nth(2).getAttribute("data-id");
  await rows.nth(2).focus();
  await page.keyboard.press("Enter");
  const afterEnter = await page.locator("#voicelist .vrow.sel").getAttribute("data-id");
  log("keyboard Enter selects a focused voice row", afterEnter === target, { target, afterEnter });
  await page.keyboard.press("Space");
  log("keyboard Space selects a focused voice row", (await page.locator("#voicelist .vrow.sel").getAttribute("data-id")) === target);
  await rows.nth(2).click();

  // speed number box vs slider
  await page.check("#speed_on");
  await page.fill("#speed_num", "33");
  const sv = await page.inputValue("#speed");
  log("speed number box 33 -> value sent is 33", sv === "33", { slider: sv, numberBox: "33" });
  await page.fill("#speed_num", "150");
  log("speed number box rejects 150", (await page.inputValue("#speed_num")) !== "150", { numberBox: await page.inputValue("#speed_num"), slider: await page.inputValue("#speed") });
  await page.fill("#speed_num", "0"); await page.uncheck("#speed_on");

  // Ctrl+B
  await page.fill("#text", "Hello");
  await page.focus("#text"); await page.keyboard.press("End"); await page.keyboard.press("Control+b");
  log("Ctrl+B inserts [break:500ms]", (await page.inputValue("#text")) === "Hello[break:500ms]");

  // generation #1 + double-trigger check: type during generation
  await page.fill("#text", "Audit run one. The quick brown fox jumps over the lazy dog.");
  const n0 = ttsCalls.length;
  await page.click("#genbtn");
  log("generate button shows busy state", (await page.textContent("#genbtn")).includes("…"));
  await page.type("#text", " x");
  const reenabled = !(await page.isDisabled("#genbtn"));
  log("generate stays disabled while a job runs (after typing)", !reenabled, { enabledMidJob: reenabled });
  if (reenabled) await page.click("#genbtn").catch(() => {});
  await page.waitForSelector("#resultlist .item", { timeout: 60000 });
  await page.waitForTimeout(3000);
  log("only one /api/tts request per intended generation", ttsCalls.length - n0 === 1, { requests: ttsCalls.length - n0 });

  const items = await page.locator("#resultlist .item").count();
  log("result item rendered", items >= 1, items);
  const a = await page.evaluate(async () => {
    const el = document.querySelector("#resultlist audio");
    if (el.readyState < 1) await new Promise(r => { el.onloadedmetadata = r; setTimeout(r, 8000); });
    return { duration: el.duration, src: el.getAttribute("src"), paused: el.paused };
  });
  log("audio element loads with duration > 0", a.duration > 0, a);
  log("autoplay starts playback (headless, no gesture policy)", a.paused === false, { paused: a.paused });

  // player controls via media API
  const ctrl = await page.evaluate(async () => {
    const el = document.querySelector("#resultlist audio"); el.muted = true;
    await el.play().catch(() => {}); await new Promise(r => setTimeout(r, 600));
    const playing = !el.paused; el.pause(); const pausedAt = el.currentTime;
    await new Promise(r => setTimeout(r, 300)); const stillPaused = el.currentTime === pausedAt;
    el.currentTime = 0; const restarted = el.currentTime === 0; el.volume = 0; const v0 = el.volume; el.volume = 1;
    el.currentTime = Math.max(0, el.duration - 0.3); await el.play().catch(() => {});
    const ended = await new Promise(r => { el.onended = () => r(true); setTimeout(() => r(false), 3000); });
    return { playing, stillPaused, restarted, v0, ended };
  });
  log("player play/pause/seek/volume/ended work", ctrl.playing && ctrl.stillPaused && ctrl.restarted && ctrl.v0 === 0 && ctrl.ended, ctrl);

  // downloads
  for (const sel of ["#resultlist .dl a:nth-child(1)", "#resultlist .dl a:nth-child(2)", "#resultlist .dl a:nth-child(3)"]) {
    const [dl] = await Promise.all([page.waitForEvent("download", { timeout: 15000 }).catch(() => null), page.click(sel)]);
    if (!dl) { log("download " + sel, false, "no download event"); continue; }
    const p = path.join(OUT, "dl_" + dl.suggestedFilename());
    await dl.saveAs(p);
    const size = fs.statSync(p).size;
    log("download produces non-empty file: " + dl.suggestedFilename(), size > 0, size);
  }

  // delete
  await page.click("#resultlist [data-del]");
  log("delete removes the item from the list", (await page.locator("#resultlist .item").count()) === items - 1);

  // results after refresh
  await page.fill("#text", "Audit run two, persistence check.");
  await page.click("#genbtn");
  await page.waitForSelector("#resultlist .item", { timeout: 60000 });
  await page.reload({ waitUntil: "networkidle" });
  const afterReload = await page.locator("#resultlist .item").count();
  log("results survive a page refresh within the session (as 'kept for this browser session' implies)", afterReload > 0, { afterReload });

  // error path: mismatched language text on English voice
  await page.waitForSelector("#voicelist .vrow", { timeout: 20000 });
  await page.fill("#text", "सुप्रभात। आज मौसम बहुत सुहावना है।");
  await page.click("#genbtn");
  await page.waitForSelector("#toast", { state: "visible", timeout: 30000 }).catch(() => {});
  const toast = await page.textContent("#toast");
  log("Hindi text on English voice gives an actionable error", /language|voice/i.test(toast) && !/unreachable/i.test(toast), toast);
  const ariaLive = await page.getAttribute("#toast", "aria-live") || await page.getAttribute("#toast", "role");
  log("toast is announced to screen readers (aria-live/role)", !!ariaLive, ariaLive);

  // mobile nav
  const m = await browser.newContext({ ...devices["iPhone 13"] });
  const mp = await m.newPage();
  await mp.goto(BASE + "/", { waitUntil: "networkidle" });
  const navBefore = await mp.isVisible("#mobilenav");
  await mp.click("#burger");
  const navAfter = await mp.isVisible("#mobilenav");
  log("mobile burger toggles navigation", !navBefore && navAfter);
  await mp.screenshot({ path: path.join(OUT, "shots", "mobile_nav_open.png") });
  await m.close();

  // sub-page language prefix
  const l = await browser.newContext(); const lp = await l.newPage();
  await lp.goto(BASE + "/es/tutorial.html", { waitUntil: "networkidle" });
  log("/es/tutorial.html renders Spanish", (await lp.evaluate(() => document.documentElement.lang)) === "es", await lp.textContent("h1"));
  await lp.goto(BASE + "/es/", { waitUntil: "networkidle" });
  const esFaq = await lp.textContent("#faqlist .q");
  log("/es/ home translates FAQ/steps content", !/Is Text 2 Speech free/.test(esFaq), esFaq);
  await lp.goto(BASE + "/ar/", { waitUntil: "networkidle" });
  log("/ar/ home sets dir=rtl", (await lp.evaluate(() => document.documentElement.dir)) === "rtl", await lp.evaluate(() => document.documentElement.dir));
  await l.close();

  // mock forms
  const f = await browser.newContext(); const fp = await f.newPage();
  for (const [p, btn] of [["/auth.html", "button"], ["/support.html", "button"], ["/donate.html", ".grid button"]]) {
    await fp.goto(BASE + p, { waitUntil: "networkidle" });
    const reqs = [];
    fp.on("request", r => { if (!r.url().match(/\.(js|css|png)$/) && r.url() !== BASE + p) reqs.push(r.url()); });
    let msg = null; fp.once("dialog", d => { msg = d.message(); d.dismiss(); });
    await fp.locator(btn).first().click(); await fp.waitForTimeout(800);
    log(`${p} primary action performs a real request`, reqs.length > 0, { alert: msg, requests: reqs.length });
  }
  await f.close();
  await ctx.close();
}

fs.writeFileSync(path.join(OUT, "browser_results.json"), JSON.stringify(R, null, 1));
await browser.close();
console.log("DONE");
