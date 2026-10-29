// Verifies the Day-1 fixes in a real browser: node verify_day1.mjs http://127.0.0.1:8137
import { chromium } from "playwright";
const BASE = process.argv[2];
const b = await chromium.launch();
const p = await (await b.newContext()).newPage();
const errors = [], tts = [];
p.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
p.on("pageerror", e => errors.push(e.message));
p.on("request", r => { if (r.url().endsWith("/api/tts")) tts.push(r.url()); });
const ck = (k, ok, d) => console.log(ok ? "PASS" : "FAIL", k, d ?? "");

await p.goto(BASE + "/", { waitUntil: "networkidle" });
await p.waitForSelector("#voicelist .vrow", { timeout: 20000 });

await p.fill("#text", "Hi 😀\nline2");
ck("counter counts code points and shows the limit", (await p.textContent("#counter")).startsWith("10 / 5000"), await p.textContent("#counter"));

await p.fill("#text", "a".repeat(5001));
ck("Generate disabled above 5000 chars", await p.isDisabled("#genbtn"));
await p.fill("#text", "a".repeat(5000));
ck("Generate enabled at exactly 5000 chars", !(await p.isDisabled("#genbtn")));

await p.fill("#text", "Day one fix check. The quick brown fox jumps over the lazy dog.");
await p.click("#genbtn");
await p.type("#text", " x");
ck("Generate stays disabled when typing mid-job", await p.isDisabled("#genbtn"));
await p.waitForSelector("#resultlist .item", { timeout: 60000 });
await p.waitForTimeout(1500);
ck("exactly one /api/tts request", tts.length === 1, tts.length);
const dur = await p.evaluate(async () => { const a = document.querySelector("#resultlist audio"); if (a.readyState < 1) await new Promise(r => { a.onloadedmetadata = r; setTimeout(r, 8000); }); return a.duration; });
ck("generated audio plays under the new CSP", dur > 0, dur);
ck("Generate re-enabled after the job", !(await p.isDisabled("#genbtn")));

await p.fill("#text", "[break:30s][break:30s][break:1s] hi");
await p.click("#genbtn");
await p.waitForSelector("#toast", { state: "visible", timeout: 15000 });
const t = await p.textContent("#toast");
ck("400 shows server reason without the network blame", /pause length/i.test(t) && !/unreachable/i.test(t), t);

const [dl] = await Promise.all([p.waitForEvent("download"), p.click("#resultlist .dl a:nth-child(1)")]);
ck("download still works", !!(await dl.path()));
// The deliberate 400 above logs "Failed to load resource"; anything else is real.
const real = errors.filter(e => !/Failed to load resource: .* 400/.test(e));
ck("no CSP violations or page errors", real.length === 0, real);
await b.close();
