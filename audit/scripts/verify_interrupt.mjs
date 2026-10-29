// Reload / go offline in the middle of a generation: node verify_interrupt.mjs BASE
import { chromium } from "playwright";
const BASE = process.argv[2];
const b = await chromium.launch();
let fails = 0;
const ck = (k, ok, d) => { if (!ok) fails++; console.log(ok ? "PASS" : "FAIL", k, d === undefined ? "" : JSON.stringify(d)); };
const ctx = await b.newContext(); const p = await ctx.newPage();
await p.goto(BASE + "/", { waitUntil: "networkidle" }); await p.waitForSelector("#voicelist .vrow");

// 1. reload while the request is in flight
await p.fill("#text", "Reload during generation. ".repeat(40));
await p.click("#genbtn");
await p.waitForTimeout(150);
await p.reload({ waitUntil: "networkidle" }); await p.waitForSelector("#voicelist .vrow");
await p.fill("#text", "After the reload.");
ck("after a mid-generation reload the page is usable (Generate enabled, no stuck busy state)",
   !(await p.isDisabled("#genbtn")) && !(await p.textContent("#genbtn")).includes("…"));
await p.click("#genbtn"); await p.waitForSelector("#resultlist .item", { timeout: 60000 });
ck("and a new generation works", (await p.locator("#resultlist .item").count()) >= 1);

// 2. network drops while generating
const before = await p.locator("#resultlist .item").count();
await p.fill("#text", "Offline during generation.");
await ctx.setOffline(true);
await p.click("#genbtn");
await p.waitForSelector("#toast", { state: "visible", timeout: 15000 });
const toast = await p.textContent("#toast");
ck("offline: clear error, text kept, button usable again",
   /unreachable|failed/i.test(toast) && (await p.inputValue("#text")) === "Offline during generation." && !(await p.isDisabled("#genbtn")), toast.slice(0, 90));
await ctx.setOffline(false);
await p.click("#genbtn");
await p.waitForFunction(n => document.querySelectorAll("#resultlist .item").length > n, before, { timeout: 60000 });
ck("back online: retry succeeds", true);
await b.close();
console.log(fails ? `${fails} FAILED` : "ALL PASSED");
