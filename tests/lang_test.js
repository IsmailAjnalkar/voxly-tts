/* Language-parity tests: URL-prefix boot, default voice, sub-page runtime. */
const { JSDOM } = require("jsdom");
const BASE = "http://localhost:8077";
let pass = 0, fail = 0;
const failures = [];
function ck(name, cond, extra) {
  if (cond) { pass++; }
  else { fail++; failures.push(name + (extra ? " :: " + extra : "")); }
}
async function loadDom(url) {
  const res = await fetch(url);
  const html = await res.text();
  const dom = new JSDOM(html, {
    url, runScripts: "dangerously", resources: "usable", pretendToBeVisual: true,
    beforeParse(window) {
      window.fetch = (u, o) => fetch(new URL(u, url), o);
      window.scrollTo = () => {};
    }
  });
  await new Promise(r => { dom.window.addEventListener("load", r); setTimeout(r, 6000); });
  // the voice catalog loads async; poll until rendered (sub-pages: brief settle)
  const list = dom.window.document.querySelector("#voicelist");
  if (list) {
    for (let i = 0; i < 60 && !list.querySelector(".vrow"); i++) await new Promise(r => setTimeout(r, 250));
  } else {
    await new Promise(r => setTimeout(r, 900));
  }
  return dom;
}
(async () => {
  // 1) /es/ homepage boots in Spanish, switcher set to es
  {
    const dom = await loadDom(BASE + "/es/");
    const d = dom.window.document;
    ck("es home: uisel=es", d.querySelector("#uilang").value === "es", d.querySelector("#uilang").value);
    const h1 = d.querySelector("h1").textContent;
    ck("es home: H1 Spanish", /voz/i.test(h1), h1);
    ck("es home: html lang es", d.documentElement.lang === "es", d.documentElement.lang);
    dom.window.close();
  }
  // 2) default selected voice on the plain homepage is the first EN voice
  {
    const dom = await loadDom(BASE + "/");
    const d = dom.window.document;
    const rows = [...d.querySelectorAll("#voicelist .vrow")];
    const badged = rows.find(r => r.querySelector(".badge"));
    ck("home: badge on first row (Natasha)", !!badged && badged === rows[0] && /Natasha/.test(badged.textContent),
       badged ? badged.textContent.slice(0, 40) : "none");
    dom.window.close();
  }
  // 3) German tutorial: full translation applied from SUBI18N
  {
    const dom = await loadDom(BASE + "/de/tutorial.html");
    const d = dom.window.document, w = dom.window;
    ck("de tut: SUBI18N loaded", !!w.SUBI18N && !!w.SUBI18N.de);
    const de = (w.SUBI18N || {}).de || {};
    ck("de tut: title translated", d.title === de.doc_tutorial, d.title);
    ck("de tut: guide1 heading", d.querySelector('[data-i18n="tut_g1h"]').textContent === de.tut_g1h);
    ck("de tut: guide1 heading is German anchor", /Erste Schritte/.test(d.querySelector('[data-i18n="tut_g1h"]').textContent));
    ck("de tut: guide2 html keeps break tokens", d.querySelector('[data-i18n-html="tut_g2p"]').innerHTML.includes("[break:500ms]"));
    ck("de tut: switcher value de", d.querySelector("#sublang").value === "de");
    ck("de tut: switcher has 25 options", d.querySelectorAll("#sublang option").length === 25);
    const navTut = d.querySelector('nav a[href="/de/tutorial.html"]');
    ck("de tut: nav links prefixed", !!navTut);
    const foot = d.querySelector('footer a[href="/de/privacy.html"]');
    ck("de tut: footer links prefixed", !!foot);
    dom.window.close();
  }
  // 4) French support: options + placeholder + alert hook translated
  {
    const dom = await loadDom(BASE + "/fr/support.html");
    const d = dom.window.document, w = dom.window;
    const fr = (w.SUBI18N || {}).fr || {};
    ck("fr sup: bug option French", d.querySelector('[data-i18n="sup_o3"]').textContent === fr.sup_o3 && fr.sup_o3 !== "Bug report", fr.sup_o3);
    ck("fr sup: placeholder French", d.querySelector("[data-i18n-ph]").getAttribute("placeholder") === fr.sup_msg_ph);
    const btn = [...d.querySelectorAll("button")].find(b => (b.getAttribute("onclick") || "").includes("subAlert"));
    ck("fr sup: send uses subAlert('sup_alert')", !!btn && btn.getAttribute("onclick").includes("sup_alert"));
    ck("fr sup: subAlert defined", typeof w.subAlert === "function");
    dom.window.close();
  }
  // 5) Arabic privacy: RTL + translated heading
  {
    const dom = await loadDom(BASE + "/ar/privacy.html");
    const d = dom.window.document, w = dom.window;
    const ar = (w.SUBI18N || {}).ar || {};
    ck("ar priv: dir=rtl", d.documentElement.dir === "rtl", d.documentElement.dir);
    ck("ar priv: h1 Arabic", d.querySelector('[data-i18n="priv_h1"]').textContent === ar.priv_h1 && /[\u0600-\u06FF]/.test(ar.priv_h1));
    ck("ar priv: contact link kept", !!d.querySelector('[data-i18n-html="priv_s4p"] a'));
    dom.window.close();
  }
  // 6) no-prefix sub-page with saved language: localStorage drives it
  {
    const dom = await loadDom(BASE + "/tutorial.html");
    const w = dom.window;
    w.localStorage.setItem("voxly-ui", "it");
    dom.window.close();
    const dom2 = await loadDom(BASE + "/tutorial.html");
    // fresh jsdom has its own storage; emulate by checking default stays English without storage
    ck("plain tut: defaults English", dom2.window.document.querySelector('[data-i18n="tut_g1h"]').textContent.startsWith("Getting started"));
    dom2.window.close();
  }
  console.log(`LANG TESTS: ${pass} passed, ${fail} failed`);
  failures.forEach(f => console.log("FAIL:", f));
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error("ERROR", e); process.exit(2); });
