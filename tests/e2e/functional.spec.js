// Functional-preservation E2E suite for text-2-speech.com. See README section in
// docs/seo-remediation/FUNCTIONAL_REGRESSION_RESULTS.md for how to run it.
// Tests marked [tts] call Microsoft's speech service through the app: they are
// few, short, and skipped with NO_GENERATE=1.
const { test: base, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

// Every page in every test is watched for page errors, console errors and CSP
// violations ("Failed to load resource" is ignored: HTTP status is asserted directly).
async function watch(page, errs) {
  await page.addInitScript(() => document.addEventListener("securitypolicyviolation",
    e => console.error(`CSP violation: ${e.violatedDirective} blocked ${e.blockedURI}`)));
  page.on("pageerror", e => errs.push("pageerror: " + e.message));
  page.on("console", m => { if (m.type() === "error" && !/Failed to load resource/.test(m.text())) errs.push(m.text()); });
}
const test = base.extend({
  errors: [async ({ page }, use) => {
    const errs = [];
    await watch(page, errs);
    await use(errs);
    expect(errs, "page errors / console errors / CSP violations").toEqual([]);
  }, { auto: true }],
});

const NO_TTS = !!process.env.NO_GENERATE;
const tts = () => test.skip(NO_TTS, "NO_GENERATE=1: speech-service tests skipped");
const isTts = r => r.url().endsWith("/api/tts") && r.request().method() === "POST";

async function openHome(page, url = "/") {
  const r = await page.goto(url);
  expect(r.status()).toBe(200);
  await page.waitForSelector("#voicelist .vrow", { timeout: 30_000 });
}

// Trigger a generation and wait for the /api/tts response. A 5xx/422 from the
// external speech service is retried once (recorded as a test annotation).
async function generate(page, trigger = () => page.click("#genbtn")) {
  let first = null;
  for (let attempt = 1; attempt <= 2; attempt++) {
    const respP = page.waitForResponse(isTts, { timeout: 90_000 });
    await trigger();
    const resp = await respP;
    const flaky = resp.status() >= 500 || resp.status() === 422;
    if (!flaky || attempt === 2) {
      if (first) test.info().annotations.push({ type: "tts-retry",
        description: `first attempt HTTP ${first.status} ${first.body}; retry HTTP ${resp.status()}` });
      return resp;
    }
    first = { status: resp.status(), body: (await resp.text().catch(() => "")).slice(0, 200) };
    console.log(`[tts-retry] ${test.info().title}: HTTP ${first.status} ${first.body}`);
    await expect(page.locator("#genbtn")).toBeEnabled();
    trigger = () => page.click("#genbtn");
  }
}

async function tabTo(page, sel, { back = false, max = 80 } = {}) {
  for (let i = 1; i <= max; i++) {
    await page.keyboard.press(back ? "Shift+Tab" : "Tab");
    if (await page.evaluate(s => !!document.activeElement && document.activeElement.matches(s), sel)) {
      test.info().annotations.push({ type: "tab-presses", description: `${sel}: ${i}` });
      return i;
    }
  }
  const at = await page.evaluate(() => { const a = document.activeElement; return a ? `${a.tagName}#${a.id}.${a.className}` : "none"; });
  throw new Error(`keyboard: ${sel} not reached after ${max} ${back ? "Shift+Tab" : "Tab"} presses (focus at ${at})`);
}

const voicesById = async request => {
  const d = await (await request.get("/api/voices")).json();
  return Object.fromEntries(d.voices.map(v => [v.id, v]));
};
const rowIds = page => page.$$eval("#voicelist .vrow", rs => rs.map(r => r.dataset.id));

// ------------------------------------------------------------------ pages
const PAGES = ["/", "/es/", "/tutorial.html", "/how-it-works.html", "/voices.html", "/guides/subtitles.html",
  "/guides/mp3-vs-wav.html", "/support.html", "/donate.html", "/privacy.html", "/terms.html", "/auth.html"];
for (const p of PAGES) {
  test(`page ${p} loads (200, no console errors or CSP violations)`, async ({ page }) => {
    const r = await page.goto(p, { waitUntil: "load" });
    expect(r.status()).toBe(200);
    await expect(page.locator("h1").first()).toBeVisible();
    if (p === "/" || p === "/es/") await page.waitForSelector("#voicelist .vrow", { timeout: 30_000 });
    else await page.waitForLoadState("networkidle");
  });
}

// ------------------------------------------------------------------ text input
test("text input: counter counts code points and lines; 5,000 limit gates Generate", async ({ page, request }) => {
  await openHome(page);
  await expect(page.locator("#genbtn")).toBeDisabled();
  await page.fill("#text", "Hi 😀\nline2");
  await expect(page.locator("#counter")).toHaveText(/^10 \/ 5000 characters \(2 lines\)/);
  await page.fill("#text", "a".repeat(5000));
  await expect(page.locator("#counter")).toHaveText(/^5000 \/ 5000/);
  await expect(page.locator("#genbtn")).toBeEnabled();
  await page.fill("#text", "a".repeat(5001));
  await expect(page.locator("#genbtn")).toBeDisabled();
  await expect(page.locator("#counter")).toHaveCSS("color", "rgb(255, 107, 74)");
  // the server enforces the same limit (validation runs before any synthesis)
  const r = await request.post("/api/tts", { headers: { "X-Session-Id": "e2elimit" },
    data: { text: "a".repeat(5001), voice: "en-US-JennyNeural" } });
  expect(r.status()).toBe(422);
});

test("Ctrl+B inserts a [break:500ms] marker", async ({ page }) => {
  await openHome(page);
  await page.fill("#text", "Hello world");
  await page.locator("#text").press("End");
  await page.locator("#text").press("Control+b");
  await expect(page.locator("#text")).toHaveValue("Hello world[break:500ms]");
});

test(".txt import: empty box fills directly; over a draft asks, Cancel keeps, OK replaces", async ({ page }) => {
  await openHome(page);
  const file = { name: "imp.txt", mimeType: "text/plain", buffer: Buffer.from("From the file.") };
  await page.setInputFiles("#fileinput", file);
  await expect(page.locator("#text")).toHaveValue("From the file.");
  await expect(page.locator("#counter")).toHaveText(/^14 \//);
  await page.fill("#text", "My existing draft.");
  let msg = null;
  page.once("dialog", d => { msg = d.message(); d.dismiss(); });
  await page.setInputFiles("#fileinput", file);
  await expect.poll(() => msg).toMatch(/Replace the text/);
  await expect(page.locator("#text")).toHaveValue("My existing draft.");
  page.once("dialog", d => d.accept());
  await page.setInputFiles("#fileinput", file);
  await expect(page.locator("#text")).toHaveValue("From the file.");
  // Import File button opens the picker
  const [chooser] = await Promise.all([page.waitForEvent("filechooser"), page.click("#importbtn")]);
  expect(chooser.isMultiple()).toBe(false);
});

// ------------------------------------------------------------------ voices
test("voice language select: switching to Spanish lists only Spanish voices and picks the curated default", async ({ page }) => {
  await openHome(page);
  await expect(page.locator("#langsel")).toHaveValue("en");
  expect((await rowIds(page)).every(id => id.startsWith("en-"))).toBe(true);
  await page.selectOption("#langsel", "es");
  await expect.poll(async () => (await rowIds(page)).every(id => id.startsWith("es-"))).toBe(true);
  await expect(page.locator("#voicelist .vrow.sel")).toHaveAttribute("data-id", "es-AR-ElenaNeural");
});

test("gender filter shows only matching voices and exposes aria-pressed", async ({ page, request }) => {
  const V = await voicesById(request);
  await openHome(page);
  const all = (await rowIds(page)).length;
  for (const g of ["Female", "Male"]) {
    await page.click(`#genderseg button[data-g="${g}"]`);
    await expect(page.locator(`#genderseg button[data-g="${g}"]`)).toHaveAttribute("aria-pressed", "true");
    const ids = await rowIds(page);
    expect(ids.length).toBeGreaterThan(0);
    expect(ids.filter(id => V[id].gender !== g)).toEqual([]);
  }
  await page.click('#genderseg button[data-g="All"]');
  await expect(page.locator("#voicelist .vrow")).toHaveCount(all);
});

test("voice search filters by name and shows an empty state", async ({ page }) => {
  await openHome(page);
  await page.fill("#vsearch", "jenny");
  const ids = await rowIds(page);
  expect(ids.length).toBeGreaterThan(0);
  expect(ids.every(id => /jenny/i.test(id))).toBe(true);
  await page.fill("#vsearch", "zzzz");
  await expect(page.locator("#voicelist")).toContainText("No voices match");
  await page.fill("#vsearch", "");
  await expect(page.locator("#voicelist .vrow").first()).toBeVisible();
});

test("voice selection: clicking a row selects it (radio checked, Selected badge)", async ({ page }) => {
  await openHome(page);
  const row = page.locator('#voicelist .vrow:not(.sel)').first();
  const id = await row.getAttribute("data-id");
  await row.locator(".vpick").click();
  await expect(page.locator("#voicelist .vrow.sel")).toHaveAttribute("data-id", id);
  await expect(page.locator(`#voicelist input[value="${id}"]`)).toBeChecked();
  await expect(page.locator("#voicelist .vrow.sel .badge")).toBeVisible();
});

test("[tts] voice preview renders the real voice and plays it", async ({ page }) => {
  tts();
  await openHome(page);
  const btn = page.locator("#voicelist .vrow.sel .pvbtn");
  let r = await generate(page, () => btn.click());
  expect(r.status(), await r.text()).toBe(200);
  const audio = await page.waitForResponse(x => /\/api\/file\/[0-9a-f]+\.mp3/.test(x.url()), { timeout: 30_000 }).catch(() => null);
  // the media request may already have completed before we listened: check the element instead
  // function form (a string predicate would need 'unsafe-eval', which the CSP rightly forbids);
  // sampleAudio is the page's top-level preview player
  /* global sampleAudio */
  await page.waitForFunction(() => typeof sampleAudio !== "undefined" && !!sampleAudio && (sampleAudio.readyState >= 2 || sampleAudio.currentTime > 0), null, { timeout: 30_000 });
  if (audio) expect([200, 206]).toContain(audio.status());
  await expect(page.locator("#toast")).not.toContainText("could not be played");
});

test("speed/pitch: gated by checkboxes, clamp to ±100, exact values sent [tts]", async ({ page }) => {
  await openHome(page);
  await expect(page.locator("#speed")).toBeDisabled();
  await expect(page.locator("#pitch_num")).toBeDisabled();
  await page.check("#speed_on"); await page.check("#pitch_on");
  await page.locator("#speed").fill("40");
  await expect(page.locator("#speed_num")).toHaveValue("40");
  await page.fill("#pitch_num", "250"); await page.press("#pitch_num", "Tab");
  await expect(page.locator("#pitch_num")).toHaveValue("100");
  await expect(page.locator("#pitch")).toHaveValue("100");
  await page.fill("#speed_num", "33"); await page.press("#speed_num", "Tab");
  await page.fill("#pitch_num", "-20"); await page.press("#pitch_num", "Tab");
  if (NO_TTS) return;
  await page.fill("#text", "Speed and pitch check.");
  const r = await generate(page);
  const body = r.request().postDataJSON();
  expect({ speed: body.speed, pitch: body.pitch }).toEqual({ speed: 33, pitch: -20 });
  expect(r.status(), await r.text()).toBe(200);
  await expect(page.locator("#resultlist .item")).toHaveCount(1);
});

// ------------------------------------------------------------------ generation
test("[tts] generate MP3: result item, audio loads, MP3/SRT/VTT downloads", async ({ page }) => {
  tts();
  await openHome(page);
  await page.locator('#voicelist .vrow[data-id="en-US-JennyNeural"] .vpick').click();
  await page.fill("#text", "Hello, world! It is a fine day.");
  const r = await generate(page);
  expect(r.status(), await r.text()).toBe(200);
  expect(r.request().postDataJSON()).toMatchObject({ voice: "en-US-JennyNeural", format: "mp3" });
  const item = page.locator("#resultlist .item");
  await expect(item).toHaveCount(1);
  await expect(item.locator(".meta")).toContainText("Jenny");
  await expect(item.locator(".meta")).toContainText("MP3");
  await page.waitForFunction(() => { const a = document.querySelector("#resultlist audio"); return a && a.readyState >= 1 && a.duration > 0; }, null, { timeout: 30_000 });
  const links = await item.locator(".dl a").evaluateAll(as => as.map(a => ({ href: a.getAttribute("href"), dl: a.getAttribute("download"), label: a.textContent })));
  expect(links.map(l => l.label.replace(/\W/g, ""))).toEqual(["MP3", "SRT", "VTT"]);
  const want = [/^audio\/(mpeg|mp3)/, /^(text\/plain|application\/x-subrip|text\/srt)/, /^text\/vtt/];
  for (const [i, l] of links.entries()) {
    const f = await page.request.get(l.href);
    expect(f.status(), l.href).toBe(200);
    expect(f.headers()["content-type"], l.href).toMatch(want[i]);
    const b = await f.body();
    expect(b.length, l.href).toBeGreaterThan(i === 0 ? 1000 : 10);
    if (i > 0) expect(b.toString()).toContain("-->");
    if (i === 2) expect(b.toString()).toMatch(/^WEBVTT/);
  }
  // clicking the MP3 link downloads a file named by the server
  const [dl] = await Promise.all([page.waitForEvent("download"), item.locator(".dl a").first().click()]);
  expect(dl.suggestedFilename()).toMatch(/\.mp3$/);
});

test("[tts] WAV generation with a [break:500ms] marker", async ({ page }) => {
  tts();
  await openHome(page);
  await page.click('#fmtrow button[data-f="wav"]');
  await expect(page.locator('#fmtrow button[data-f="wav"]')).toHaveAttribute("aria-pressed", "true");
  await page.fill("#text", "First part. [break:500ms] Second part.");
  const r = await generate(page);
  expect(r.status(), await r.text()).toBe(200);
  const d = await r.json();
  expect(r.request().postDataJSON().format).toBe("wav");
  expect(d.format).toBe("wav");
  expect(d.audioName).toMatch(/\.wav$/);
  expect(d.duration).toBeGreaterThan(1.5);
  expect(d.snippet).not.toContain("[break");
  const item = page.locator("#resultlist .item");
  await expect(item.locator(".meta")).toContainText("WAV");
  const f = await page.request.get(await item.locator(".dl a").first().getAttribute("href"));
  expect(f.status()).toBe(200);
  expect(f.headers()["content-type"]).toMatch(/^audio\/(x-)?wav/);
  expect((await f.body()).subarray(0, 4).toString()).toBe("RIFF");
});

test("more than 25 [break] markers is rejected with a readable message", async ({ page }) => {
  await openHome(page);
  await page.fill("#text", "[break:100ms]".repeat(26) + " hi");
  const r = await generate(page);
  expect(r.status()).toBe(400);
  await expect(page.locator("#toast")).toBeVisible();
  await expect(page.locator("#toast")).toContainText("Too many [break] markers (max 25)");
  await expect(page.locator("#genbtn")).toBeEnabled();
  await expect(page.locator("#resultlist .item")).toHaveCount(0);
});

test("error states: empty text blocked; server 5xx and 429 show a message and keep the text", async ({ page, request }) => {
  await openHome(page);
  await page.fill("#text", "   \n  ");
  await expect(page.locator("#genbtn")).toBeDisabled();
  await expect(page.locator("#previewbtn")).toBeDisabled();
  const empty = await request.post("/api/tts", { headers: { "X-Session-Id": "e2eempty" }, data: { text: "  ", voice: "en-US-JennyNeural" } });
  expect(empty.status()).toBe(400);
  expect((await empty.json()).detail).toBe("Text is empty");

  await page.route("**/api/tts", rt => rt.fulfill({ status: 502, contentType: "application/json", body: '{"detail":"Synthesis failed, please retry"}' }));
  await page.fill("#text", "Keep me.");
  await page.click("#genbtn");
  await expect(page.locator("#toast")).toContainText("Generation failed");
  await expect(page.locator("#text")).toHaveValue("Keep me.");
  await expect(page.locator("#genbtn")).toBeEnabled();
  await page.unroute("**/api/tts");
  // production rate limit (nginx) answers 429: the UI explains it
  await page.route("**/api/tts", rt => rt.fulfill({ status: 429, contentType: "text/html", body: "<html>429</html>" }));
  await page.click("#genbtn");
  await expect(page.locator("#toast")).toContainText("Too many requests");
  await expect(page.locator("#resultlist .item")).toHaveCount(0);
});

test("rate limiting is configured in nginx: 20/min per IP on /api/tts, 429 status (config check, no traffic)", async () => {
  const conf = fs.readFileSync(path.join(__dirname, "..", "..", "deploy", "nginx-voxy-tls.conf"), "utf8");
  expect(conf).toMatch(/limit_req_zone \$binary_remote_addr zone=tts:\S+ rate=20r\/m;/);
  const loc = conf.match(/location = \/api\/tts \{([^}]*)\}/);
  expect(loc, "location = /api/tts block").not.toBeNull();
  expect(loc[1]).toMatch(/limit_req zone=tts burst=\d+/);
  expect(loc[1]).toMatch(/limit_req_status 429;/);
});

// ------------------------------------------------------------------ layout / a11y flows
test.describe("mobile 390 px", () => {
  test.use({ viewport: { width: 390, height: 844 } });
  test("no horizontal overflow; main controls visible, sized and usable", async ({ page }) => {
    for (const p of ["/tutorial.html", "/how-it-works.html", "/guides/subtitles.html", "/support.html", "/es/"]) {
      await page.goto(p);
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), `overflow on ${p}`).toBeLessThanOrEqual(0);
    }
    await openHome(page);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), "overflow on /").toBeLessThanOrEqual(0);
    for (const sel of ["#langsel", "#vsearch", "#voicelist .vrow.sel .vpick", "#text", "#genbtn", "#importbtn", "#uilang", "#themebtn", "#burger"]) {
      const el = page.locator(sel).first();
      await el.scrollIntoViewIfNeeded();
      const bb = await el.boundingBox();
      expect(bb, sel).not.toBeNull();
      expect(bb.x, `${sel} left edge`).toBeGreaterThanOrEqual(0);
      expect(bb.x + bb.width, `${sel} right edge`).toBeLessThanOrEqual(390 + 0.5);
      expect(bb.height, `${sel} target height (WCAG 2.5.8: 24px)`).toBeGreaterThanOrEqual(24);
    }
    await page.click("#burger");
    await expect(page.locator("#burger")).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#mobilenav")).toBeVisible();
    await page.fill("#text", "Mobile check.");
    await expect(page.locator("#genbtn")).toBeEnabled();
    const other = page.locator("#voicelist .vrow:not(.sel)").first();
    const id = await other.getAttribute("data-id");
    await other.locator(".vpick").click();
    await expect(page.locator("#voicelist .vrow.sel")).toHaveAttribute("data-id", id);
  });
});

test("[tts] keyboard only: choose voice -> type -> generate -> play -> download", async ({ page }) => {
  tts();
  await openHome(page);
  await page.locator("body").focus();
  let first;
  await test.step("Tab to the selected voice radio and ArrowDown to choose another", async () => {
    first = await page.getAttribute("#voicelist .vrow.sel", "data-id");
    await tabTo(page, 'input[name="voice"]:checked');
    await page.keyboard.press("ArrowDown");
    const now = await page.getAttribute("#voicelist .vrow.sel", "data-id");
    expect(now).not.toBe(first);
    first = now;
  });
  await test.step("Tab to Autoplay and turn it off with Space", async () => {
    await tabTo(page, "#autoplay");
    await page.keyboard.press("Space");
    await expect(page.locator("#autoplay")).not.toBeChecked();
  });
  await test.step("Tab to the text box and type", async () => {
    await tabTo(page, "#text");
    await page.keyboard.type("Keyboard only.");
    await expect(page.locator("#text")).toHaveValue("Keyboard only.");
  });
  await test.step("Tab to Generate and press Enter", async () => {
    await tabTo(page, "#genbtn");
    const r = await generate(page, () => page.keyboard.press("Enter"));
    expect(r.status(), await r.text()).toBe(200);
    expect(r.request().postDataJSON().voice).toBe(first);
    await expect(page.locator("#resultlist .item")).toHaveCount(1);
  });
  await test.step("Tab to the audio player and press Space to play", async () => {
    await page.focus("#genbtn");
    await tabTo(page, "#resultlist audio", { max: 10 });
    await page.keyboard.press("Space");
    await page.waitForFunction(() => { const a = document.querySelector("#resultlist audio"); return a && !a.paused; }, null, { timeout: 10_000 });
  });
  await test.step("Tab to the MP3 download link and press Enter", async () => {
    await tabTo(page, "#resultlist .dl a", { max: 15 });
    const [dl] = await Promise.all([page.waitForEvent("download"), page.keyboard.press("Enter")]);
    expect(dl.suggestedFilename()).toMatch(/\.mp3$/);
  });
});

// ------------------------------------------------------------------ site
test("language switcher navigates to /es/ and the UI is Spanish", async ({ page }) => {
  await openHome(page);
  await Promise.all([page.waitForURL(/\/es\/$/), page.selectOption("#uilang", "es")]);
  await page.waitForSelector("#voicelist .vrow", { timeout: 30_000 });
  expect(await page.evaluate(() => document.documentElement.lang)).toBe("es");
  await expect(page.locator("h1")).toHaveText("Texto a voz gratuito en línea");
  await expect(page.locator("#genbtn")).toContainText("Generar audio");
  await expect(page.locator("#resultlist .empty")).toHaveText("Aún no hay elementos generados");
  // internal links keep the language
  await expect(page.locator('header a[href="/es/tutorial.html"]').first()).toBeAttached();
});

test("theme toggle persists across reload and onto sub-pages", async ({ page }) => {
  await openHome(page);
  const dark = () => page.evaluate(() => document.documentElement.classList.contains("dark"));
  expect(await dark()).toBe(true); // default
  await page.click("#themebtn");
  expect(await dark()).toBe(false);
  expect(await page.evaluate(() => localStorage.getItem("voxly-theme"))).toBe("light");
  await page.reload();
  expect(await dark()).toBe(false);
  await page.goto("/tutorial.html");
  expect(await page.evaluate(() => document.documentElement.classList.contains("light"))).toBe(true);
  await page.click("#themebtn");
  await page.goto("/");
  expect(await dark()).toBe(true);
});

test("[tts] session privacy: results are per tab; another context can't see or fetch them", async ({ page, browser, context }) => {
  tts();
  await openHome(page);
  await page.fill("#text", "Private result.");
  const r = await generate(page);
  expect(r.status(), await r.text()).toBe(200);
  const d = await r.json();
  await expect(page.locator("#resultlist .item")).toHaveCount(1);
  await page.reload();
  await expect(page.locator("#resultlist .item")).toHaveCount(1); // same tab keeps it

  const errs = [];
  const tab2 = await context.newPage(); await watch(tab2, errs);
  await openHome(tab2);
  await expect(tab2.locator("#resultlist .empty")).toBeVisible();
  const s1 = await page.evaluate(() => sessionStorage.getItem("voxly-session"));
  const s2 = await tab2.evaluate(() => sessionStorage.getItem("voxly-session"));
  expect(s2).not.toBe(s1);

  const other = await browser.newContext(); const p2 = await other.newPage(); await watch(p2, errs);
  await openHome(p2);
  await expect(p2.locator("#resultlist .item")).toHaveCount(0);
  const s3 = await p2.evaluate(() => sessionStorage.getItem("voxly-session"));
  for (const s of [s2, s3, ""]) {
    const st = await p2.evaluate(u => fetch(u).then(x => x.status), `/api/file/${d.audioName}?s=${s}`);
    expect([400, 404], `fetch with session "${s}"`).toContain(st);
  }
  const del = await p2.evaluate(([id, s]) => fetch(`/api/items/${id}`, { method: "DELETE", headers: { "X-Session-Id": s } }).then(x => x.status), [d.id, s3]);
  expect(del).toBe(200);
  const still = await page.evaluate(u => fetch(u).then(x => x.status), `${d.audio}&s=${s1}`);
  expect(still, "another session's DELETE must not remove the file").toBe(200);
  await other.close();
  expect(errs).toEqual([]);
});
