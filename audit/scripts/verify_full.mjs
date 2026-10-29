// Full-remediation browser checks: [BROWSER=firefox|webkit] node verify_full.mjs BASE OUTDIR [--no-generate]
// Accessibility (axe WCAG 2.2 AA, zero tolerance), keyboard voice selection,
// empty state, RTL, support form, 404, subtitles, CSP/console errors.
import * as pw from "playwright";
import AxeBuilder from "@axe-core/playwright";
import fs from "fs";
const [BASE, OUT] = process.argv.slice(2);
const GENERATE = !process.argv.includes("--no-generate");
fs.mkdirSync(OUT, { recursive: true });
const ENGINE = process.env.BROWSER || "chromium";  // chromium | firefox | webkit
const b = await pw[ENGINE].launch();
console.log("engine:", ENGINE);
let fails = 0;
const ck = (k, ok, d) => { if (!ok) fails++; console.log(ok ? "PASS" : "FAIL", k, d === undefined ? "" : JSON.stringify(d)); };
const errs = [];
const watch = p => {
  p.on("pageerror", e => errs.push(e.message));
  p.on("console", m => { if (m.type() === "error" && !/Failed to load resource/.test(m.text())) errs.push(m.text()); });
};
const ready = async p => { if (await p.locator("#voicelist").count()) await p.waitForSelector("#voicelist .vrow", { timeout: 20000 }); };

// ---- axe on every page, both themes, desktop + mobile
const PAGES = ["/", "/tutorial.html", "/donate.html", "/support.html", "/auth.html", "/privacy.html", "/terms.html", "/nope-404"];
for (const theme of ["dark", "light"]) {
  for (const vp of [{ width: 1280, height: 900 }, { width: 375, height: 800 }]) {
    const ctx = await b.newContext({ viewport: vp });
    await ctx.addInitScript(t => localStorage.setItem("voxly-theme", t), theme);
    const p = await ctx.newPage(); watch(p);
    for (const path of PAGES) {
      await p.goto(BASE + path, { waitUntil: "networkidle" }); await ready(p);
      const v = (await new AxeBuilder({ page: p }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze()).violations;
      ck(`axe ${theme} ${vp.width}px ${path}: 0 violations`, v.length === 0, v.map(x => `${x.id}(${x.nodes.length}): ${x.nodes[0].target.join(" ")}`));
    }
    await ctx.close();
  }
}

// ---- home page behaviour
{
  const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } }); const p = await ctx.newPage(); watch(p);
  await p.goto(BASE + "/", { waitUntil: "networkidle" }); await ready(p);
  ck("no cookie banner (there are no cookies)", (await p.locator("#cookie").count()) === 0);
  ck("no placeholder friend links", !(await p.content()).includes("google.com"));
  ck("pitch unit shows Hz", (await p.textContent("#pitchrow")).includes("Hz"));
  // keyboard: Tab into the radio group, arrow keys move selection, focus stays in the list
  const first = await p.getAttribute("#voicelist .vrow.sel", "data-id");
  await p.focus("#vsearch"); await p.keyboard.press("Tab");
  ck("Tab from search lands on the selected voice radio", await p.evaluate(() => document.activeElement.name === "voice" && document.activeElement.checked));
  await p.keyboard.press("ArrowDown");
  const after = await p.getAttribute("#voicelist .vrow.sel", "data-id");
  const focusOk = await p.evaluate(() => document.activeElement.name === "voice" && document.activeElement.value === document.querySelector("#voicelist .vrow.sel").dataset.id);
  ck("ArrowDown selects the next voice and keeps focus on it", after && after !== first && focusOk, { first, after });
  await p.keyboard.press("ArrowUp");
  ck("ArrowUp moves back", (await p.getAttribute("#voicelist .vrow.sel", "data-id")) === first);
  await p.keyboard.press("Tab");
  ck("Tab from the selected voice reaches its Preview button", await p.evaluate(() => document.activeElement.matches(".pvbtn")));
  await p.fill("#vsearch", "zzzz");
  ck("no-match search shows an empty-state message", /No voices match/.test(await p.textContent("#voicelist")));
  await p.fill("#vsearch", "");
  ck("voice labels unique within English", await p.evaluate(() => { const n = [...document.querySelectorAll("#voicelist .nm")].map(e => e.textContent); return new Set(n).size === n.length; }));
  ck("Multilingual tag shown", /\(Multilingual\)/.test(await p.textContent("#voicelist")));
  await p.click('#genderseg button[data-g="Female"]');
  ck("gender buttons expose aria-pressed", (await p.getAttribute('#genderseg button[data-g="Female"]', "aria-pressed")) === "true"
     && (await p.getAttribute('#genderseg button[data-g="All"]', "aria-pressed")) === "false");
  await p.click('#genderseg button[data-g="All"]');
  if (GENERATE) {
    await p.fill("#text", "Hello, world! It is a fine day. Bye.");
    await p.click("#genbtn");
    await p.waitForSelector("#resultlist .item", { timeout: 60000 });
    const srt = await p.evaluate(u => fetch(u).then(r => r.text()), await p.getAttribute("#resultlist .dl a:nth-child(2)", "href"));
    ck("subtitles keep punctuation and split at sentences (real engine word timings)",
       /Hello, world!/.test(srt) && /It is a fine day\./.test(srt) && /Bye\./.test(srt) && (srt.match(/-->/g) || []).length === 3, srt.slice(0, 200));
  }
  await ctx.close();
}

// ---- RTL and English-only sections
{
  const p = await (await b.newContext()).newPage(); watch(p);
  await p.goto(BASE + "/ar/", { waitUntil: "networkidle" }); await ready(p);
  ck("/ar/ home is right-to-left", (await p.evaluate(() => document.documentElement.dir)) === "rtl");
  const arab = /[؀-ۿ]/;
  ck("/ar/ how-it-works, use cases and FAQ are in Arabic",
     arab.test(await p.textContent("#tabpane")) && arab.test(await p.textContent("#usecases")) && arab.test(await p.textContent("#faqlist .q")));
  await p.click('#steptabs button[data-t="3"]');
  ck("/ar/ step tabs switch within Arabic content", arab.test(await p.textContent("#tabpane h3")));
  await p.screenshot({ path: OUT + "/home_ar.png" });
  // "/" serves English HTML but the saved choice is Arabic: the client fetches the Arabic content
  await p.goto(BASE + "/", { waitUntil: "networkidle" }); await ready(p);
  await p.waitForFunction(() => /[؀-ۿ]/.test(document.querySelector("#faqlist .q").textContent), null, { timeout: 5000 }).catch(() => {});
  ck("'/' with a saved Arabic choice shows Arabic content", arab.test(await p.textContent("#faqlist .q")));
  await p.goto(BASE + "/ja/", { waitUntil: "networkidle" });
  ck("/ja/ FAQ in Japanese", /[぀-ヿ一-鿿]/.test(await p.textContent("#faqlist .q")));
  await p.context().close();
}

// ---- 320 px header
{
  const p = await (await b.newContext({ viewport: { width: 320, height: 700 } })).newPage(); watch(p);
  await p.goto(BASE + "/", { waitUntil: "networkidle" }); await ready(p);
  const m = await p.evaluate(() => ({ overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, w: document.querySelector("#uilang").getBoundingClientRect().width }));
  ck("320 px: no overflow, language select readable (>= 90 px)", !m.overflow && m.w >= 90, m);
  await p.screenshot({ path: OUT + "/home_320.png" });
  await p.context().close();
}

// ---- support form
{
  const p = await (await b.newContext()).newPage(); watch(p);
  const posts = []; p.on("request", r => { if (r.url().endsWith("/api/support")) posts.push(r.postData()); });
  await p.goto(BASE + "/support.html", { waitUntil: "networkidle" });
  await p.fill("#sup_msg", "The preview button does nothing on my phone.");
  await p.click('button[type="submit"]'); await p.waitForTimeout(400);
  ck("empty email is blocked by the browser (no request sent)", posts.length === 0 && !(await p.evaluate(() => document.getElementById("sup_email").validity.valid)));
  await p.fill("#sup_email", "not-an-email"); await p.click('button[type="submit"]'); await p.waitForTimeout(300);
  ck("malformed email is blocked", posts.length === 0);
  await p.fill("#sup_email", "qa@example.com"); await p.selectOption("#sup_topic", "bug");
  await p.click('button[type="submit"]');
  await p.waitForFunction(() => document.getElementById("supstatus").textContent.length > 0, null, { timeout: 10000 });
  ck("valid message is sent and confirmed", posts.length === 1 && /sent/.test(await p.textContent("#supstatus")), await p.textContent("#supstatus"));
  ck("form cleared after sending", (await p.inputValue("#sup_msg")) === "");
  await p.goto(BASE + "/fr/support.html", { waitUntil: "networkidle" });
  await p.fill("#sup_email", "qa@example.com"); await p.fill("#sup_msg", "Message de test en français.");
  await p.click('button[type="submit"]');
  await p.waitForFunction(() => document.getElementById("supstatus").textContent.length > 0, null, { timeout: 10000 });
  ck("confirmation is localized (fr)", /envoyé/.test(await p.textContent("#supstatus")), await p.textContent("#supstatus"));
  await p.context().close();
}

// ---- 404 and privacy copy
{
  const p = await (await b.newContext()).newPage(); watch(p);
  const r = await p.goto(BASE + "/no-such-page.html");
  ck("unknown page: HTML 404 with a way home", r.status() === 404 && (await p.isVisible('main a[href="/"]')));
  const api = await p.evaluate(u => fetch(u).then(async r => [r.status, r.headers.get("content-type")]), BASE + "/api/nope");
  ck("unknown API path stays JSON 404", api[0] === 404 && api[1].includes("json"), api);
  await p.goto(BASE + "/privacy.html", { waitUntil: "networkidle" });
  const t = await p.textContent("main");
  ck("privacy names Microsoft, states no cookies/analytics, no consent banner claims", /Microsoft/.test(t) && /do not use cookies/.test(t) && !/accept the cookie banner/.test(t));
  await p.context().close();
}

ck("no page errors, console errors or CSP violations", errs.length === 0, errs.slice(0, 5));
await b.close();
console.log(fails ? `${fails} FAILED` : "ALL PASSED");
