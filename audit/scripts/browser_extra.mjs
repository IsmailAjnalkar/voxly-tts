import { chromium } from "playwright";
const S = process.argv[2]; const b = await chromium.launch(); const c = await b.newContext(); const p = await c.newPage();
const ck = (k, ok, d) => console.log(ok ? "PASS" : "FAIL", k, d ?? "");
await p.goto("https://text-2-speech.com/", { waitUntil: "networkidle" }); await p.waitForSelector("#voicelist .vrow");
await p.setInputFiles("#fileinput", S + "/import.txt");
await p.waitForTimeout(300);
ck("Import File loads .txt into textarea", (await p.inputValue("#text")) === "Imported line one.\nSecond line é.", JSON.stringify(await p.inputValue("#text")));
ck("counter updates after import", (await p.textContent("#counter")).startsWith("34 "), await p.textContent("#counter"));
const dark0 = await p.evaluate(() => document.documentElement.classList.contains("dark"));
await p.click("#themebtn"); await p.reload({ waitUntil: "networkidle" });
const dark1 = await p.evaluate(() => document.documentElement.classList.contains("dark"));
ck("theme toggle persists across reload", dark0 !== dark1, { before: dark0, after: dark1 });
await p.click("#faqexpand"); ck("FAQ expand all", (await p.locator(".faqitem.open").count()) === 6);
await p.click("#faqcollapse"); ck("FAQ collapse all", (await p.locator(".faqitem.open").count()) === 0);
await p.click('#steptabs button[data-t="2"]'); ck("How-it-works tabs switch", (await p.textContent("#tabpane h3")) === "Preview or generate");
await p.click("#cookiedec"); await p.reload({ waitUntil: "networkidle" }); ck("cookie decline remembered", !(await p.isVisible("#cookie")));
const ck2 = await p.evaluate(() => document.cookie); ck("no cookies set (banner claims analytics cookies)", ck2 === "", JSON.stringify(ck2));
// main preview: stub speechSynthesis and check it is invoked with cleaned text
await p.waitForSelector("#voicelist .vrow");
await p.evaluate(() => { window.__spoken = null; speechSynthesis.speak = u => { window.__spoken = { text: u.text, lang: u.lang, rate: u.rate }; }; });
await p.fill("#text", "Hello [break:2s] world"); await p.click("#previewbtn");
const sp = await p.evaluate(() => window.__spoken);
ck("Preview Audio speaks cleaned text in voice locale (device TTS stubbed)", sp && !sp.text.includes("[break") && sp.lang === "en-AU", sp);
// row preview (real server voice): one request
const [resp] = await Promise.all([p.waitForResponse(r => r.url().includes("/api/tts")), p.click("#voicelist .vrow:nth-child(2) [data-pv]")]);
ck("row Preview renders server sample", resp.status() === 200, resp.status());
await b.close();
