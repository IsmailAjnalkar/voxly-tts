import { chromium, devices } from "playwright";
const b = await chromium.launch(); const out = process.argv[2];
const c = await b.newContext({ ...devices["iPhone SE"] }); const p = await c.newPage();
for (const u of ["/tutorial.html", "/support.html"]) {
  await p.goto("https://text-2-speech.com" + u, { waitUntil: "networkidle" });
  const m = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  console.log(u, "375px overflow:", m.sw > m.cw, m);
  await p.screenshot({ path: `${out}/sub_${u.slice(1, -5)}_375.png` });
}
await p.goto("https://text-2-speech.com/ar/", { waitUntil: "networkidle" });
console.log("/ar/ home: dir=", await p.evaluate(() => document.documentElement.dir), "h1=", await p.textContent("h1"));
await p.goto("https://text-2-speech.com/ar/tutorial.html", { waitUntil: "networkidle" });
console.log("/ar/tutorial: dir=", await p.evaluate(() => document.documentElement.dir));
await p.goto("https://text-2-speech.com/es/", { waitUntil: "networkidle" });
console.log("/es/ canonical:", await p.getAttribute('link[rel=canonical]', "href"), "| howto:", (await p.textContent("#tabpane h3")));
await b.close();
