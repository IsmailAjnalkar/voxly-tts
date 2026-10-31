// Verifies the user-reported UI fixes: node verify_ui.mjs BASE TMPDIR
import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";
import fs from "fs";
const [BASE, TMP] = process.argv.slice(2);
const b = await chromium.launch();
let fails = 0;
const ck = (k, ok, d) => { if (!ok) fails++; console.log(ok ? "PASS" : "FAIL", k, d === undefined ? "" : JSON.stringify(d)); };
const errs = [];
const watch = p => { p.on("pageerror", e => errs.push(e.message)); p.on("console", m => { if (m.type() === "error" && /Content Security Policy/.test(m.text())) errs.push(m.text()); }); };

// ---- 1. speed/pitch clamp + exact value sent
{
  const p = await (await b.newContext()).newPage(); watch(p);
  await p.goto(BASE + "/", { waitUntil: "networkidle" }); await p.waitForSelector("#voicelist .vrow");
  await p.check("#pitch_on"); await p.fill("#pitch_num", "250"); await p.press("#pitch_num", "Tab");
  ck("pitch 250 clamps to 100 on blur", (await p.inputValue("#pitch_num")) === "100" && (await p.inputValue("#pitch")) === "100");
  await p.fill("#pitch_num", "-180"); await p.press("#pitch_num", "Enter");
  ck("pitch -180 clamps to -100 on Enter", (await p.inputValue("#pitch_num")) === "-100");
  await p.check("#speed_on"); await p.fill("#speed_num", "33"); await p.press("#speed_num", "Tab");
  await p.fill("#pitch_num", "250"); // not blurred: still must not send 250
  await p.fill("#text", "Clamp check.");
  const [req] = await Promise.all([p.waitForRequest(r => r.url().endsWith("/api/tts")), p.click("#genbtn")]);
  const body = JSON.parse(req.postData());
  ck("typed 33 sends 33 (not the slider's 35); unblurred 250 sends 100", body.speed === 33 && body.pitch === 100, { speed: body.speed, pitch: body.pitch });
  await p.waitForSelector("#resultlist .item", { timeout: 60000 });
  await p.context().close();
}

// ---- 3. results survive reload and UI-language switch; delete persists; no autoplay on re-render
{
  const ctx = await b.newContext(); const p = await ctx.newPage(); watch(p);
  await p.goto(BASE + "/", { waitUntil: "networkidle" }); await p.waitForSelector("#voicelist .vrow");
  for (const t of ["First result.", "Second result."]) {
    await p.fill("#text", t); await p.click("#genbtn");
    await p.waitForFunction(n => document.querySelectorAll("#resultlist .item").length === n, t === "First result." ? 1 : 2, { timeout: 60000 });
  }
  await p.reload({ waitUntil: "networkidle" });
  await p.waitForFunction(() => document.querySelectorAll("#resultlist .item").length === 2, null, { timeout: 10000 }).catch(() => {});
  ck("2 results survive a reload", (await p.locator("#resultlist .item").count()) === 2);
  ck("restored results show voice names, not ids", !(await p.textContent("#resultlist .meta b")).includes("Neural"), await p.textContent("#resultlist .meta b"));
  ck("restored results don't autoplay", await p.evaluate(() => [...document.querySelectorAll("#resultlist audio")].every(a => a.paused)));
  await p.selectOption("#uilang", "fr"); await p.waitForURL(/\/fr\/$/); await p.waitForLoadState("networkidle");
  await p.waitForFunction(() => document.querySelectorAll("#resultlist .item").length === 2, null, { timeout: 10000 }).catch(() => {});
  ck("results survive a UI-language switch (/fr/)", (await p.locator("#resultlist .item").count()) === 2);
  await p.click("#resultlist [data-del]");
  await p.reload({ waitUntil: "networkidle" }); await p.waitForTimeout(1500);
  ck("a deleted result stays deleted after reload", (await p.locator("#resultlist .item").count()) === 1);
  const href = await p.getAttribute("#resultlist .dl a", "href");
  const st = await p.evaluate(u => fetch(u).then(r => r.status), href);
  ck("restored download link still works", st === 200 || st === 206, st);
  // server-expired items are dropped on restore
  await p.evaluate(() => { const it = JSON.parse(sessionStorage.getItem("voxly-items")); it.push({ ...it[0], id: "deadbeef0000" }); sessionStorage.setItem("voxly-items", JSON.stringify(it)); });
  await p.reload({ waitUntil: "networkidle" }); await p.waitForTimeout(1500);
  ck("items missing on the server are dropped on restore", (await p.locator("#resultlist .item").count()) === 1);
  await ctx.close();
}

// ---- 4. import confirmation
{
  const p = await (await b.newContext()).newPage(); watch(p);
  fs.writeFileSync(TMP + "/imp.txt", "From the file.");
  await p.goto(BASE + "/", { waitUntil: "networkidle" });
  await p.fill("#text", "");
  await p.setInputFiles("#fileinput", TMP + "/imp.txt");
  await p.waitForTimeout(300);
  ck("import into an empty box needs no confirmation", (await p.inputValue("#text")) === "From the file.");
  await p.fill("#text", "My existing draft.");
  let msg = null; p.once("dialog", d => { msg = d.message(); d.dismiss(); });
  await p.setInputFiles("#fileinput", TMP + "/imp.txt"); await p.waitForTimeout(400);
  ck("import over existing text asks first; Cancel keeps the draft", msg && (await p.inputValue("#text")) === "My existing draft.", msg);
  p.once("dialog", d => d.accept());
  await p.setInputFiles("#fileinput", TMP + "/imp.txt"); await p.waitForTimeout(400);
  ck("OK replaces the text (same file picked twice still fires)", (await p.inputValue("#text")) === "From the file.");
  await p.goto(BASE + "/fr/", { waitUntil: "networkidle" }); await p.fill("#text", "Brouillon.");
  let fr = null; p.once("dialog", d => { fr = d.message(); d.dismiss(); });
  await p.setInputFiles("#fileinput", TMP + "/imp.txt"); await p.waitForTimeout(400);
  ck("confirmation is localized (fr)", fr && fr.startsWith("Remplacer"), fr);
  await p.context().close();
}

// ---- 5 + 6. sub-pages: brand, theme, account icon, layout, stubs
{
  const pages = ["tutorial", "donate", "support", "auth", "privacy", "terms"];
  for (const w of [320, 1280]) {
    const p = await (await b.newContext({ viewport: { width: w, height: 800 } })).newPage(); watch(p);
    for (const name of pages) {
      await p.goto(`${BASE}/fr/${name}.html`, { waitUntil: "networkidle" });
      const m = await p.evaluate(() => ({
        brand: document.querySelector(".brand").textContent.trim(),
        overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        wrapped: [...document.querySelectorAll("nav a")].filter(a => a.getClientRects().length > 1 || a.getBoundingClientRect().height > 40).map(a => a.textContent),
        theme: !!document.getElementById("themebtn"), account: !!document.querySelector('.hbtns a[href$="auth.html"]'),
        on: document.querySelector("nav a.on")?.getAttribute("href") || null,
      }));
      ck(`${w}px /fr/${name}.html: brand, theme+account icons, no overflow, no wrapped links`,
         m.brand === "Text 2 Speech" && m.theme && m.account && !m.overflow && !m.wrapped.length, m);
    }
    await p.context().close();
  }
  const ctx = await b.newContext(); const p = await ctx.newPage(); watch(p);
  await p.goto(BASE + "/tutorial.html", { waitUntil: "networkidle" });
  await p.click("#themebtn");
  const light = await p.evaluate(() => [document.documentElement.classList.contains("light"), getComputedStyle(document.body).backgroundColor]);
  ck("sub-page theme toggle switches to light", light[0] && light[1] === "rgb(246, 244, 239)", light);
  await p.goto(BASE + "/", { waitUntil: "networkidle" });
  ck("theme carries to the home page", !(await p.evaluate(() => document.documentElement.classList.contains("dark"))));
  await p.click("#themebtn"); await p.goto(BASE + "/privacy.html", { waitUntil: "networkidle" });
  ck("and back: dark on sub-page after home toggle", !(await p.evaluate(() => document.documentElement.classList.contains("light"))));
  await p.screenshot({ path: TMP + "/sub_privacy_dark.png" });

  await p.goto(BASE + "/auth.html", { waitUntil: "networkidle" });
  ck("auth: notice shown, form disabled, no '#' links",
     await p.isVisible(".notice") && await p.isDisabled("button[data-i18n=auth_signin]") && (await p.locator('a[href="#"]').count()) === 0);
  await p.goto(BASE + "/donate.html", { waitUntil: "networkidle" });
  const pay = await p.$$eval("a.paybtn", as => as.map(a => [a.getAttribute("href"), a.target, a.rel]));
  ck("donate: Stripe + Buy Me a Coffee links open in a new tab", pay.length === 2 &&
     /^https:\/\/(buy|donate)\.stripe\.com\//.test(pay[0][0]) && /^https:\/\/buymeacoffee\.com\//.test(pay[1][0]) &&
     pay.every(([, t, r]) => t === "_blank" && r.includes("noopener")), JSON.stringify(pay));
  await p.goto(BASE + "/support.html", { waitUntil: "networkidle" });
  // the support form went live in the full remediation (sending is covered by verify_full.mjs)
  ck("support: live form, Send enabled, email + message required",
     !(await p.isDisabled("button[type=submit]")) &&
     (await p.getAttribute("#sup_email", "required")) !== null && (await p.getAttribute("#sup_msg", "required")) !== null);
  await p.setViewportSize({ width: 1280, height: 900 });
  await p.goto(BASE + "/fr/auth.html", { waitUntil: "networkidle" });
  await p.screenshot({ path: TMP + "/auth_fr_1280.png" });
  await p.setViewportSize({ width: 320, height: 700 });
  await p.screenshot({ path: TMP + "/auth_fr_320.png" });
  for (const name of ["donate", "support", "auth"]) {
    await p.setViewportSize({ width: 1280, height: 900 });
    await p.goto(`${BASE}/${name}.html`, { waitUntil: "networkidle" });
    const v = (await new AxeBuilder({ page: p }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations.filter(x => x.id !== "color-contrast");
    ck(`axe (excluding contrast) clean on ${name}`, v.length === 0, v.map(x => x.id));
  }
  await ctx.close();
}
ck("no page errors or CSP violations", errs.length === 0, errs);
await b.close();
console.log(fails ? `${fails} FAILED` : "ALL PASSED");
