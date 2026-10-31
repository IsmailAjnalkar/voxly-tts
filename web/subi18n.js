/* Text 2 Speech sub-page runtime. The server renders each page in the language
   of its URL (/es/, /de/ ...), so normally nothing needs translating here. When a
   visitor's saved language differs from the one the server rendered (e.g. "/"
   after choosing Español), the strings for that one language are fetched from
   /i18n-sub-parts/<lang>.json and applied. Also: language switcher, theme
   toggle, current-page highlight and the support form. */
(function () {
  var NAMES = [["en", "English"], ["zh", "简体中文"], ["zh-TW", "繁體中文"], ["ar", "العربية"], ["cs", "Cestina"], ["da", "Dansk"], ["de", "Deutsch"], ["es", "Espanol"], ["fa", "فارسی"], ["fr", "Francais"], ["hi", "हिन्दी"], ["hu", "Magyar"], ["id", "Bahasa Indonesia"], ["it", "Italiano"], ["ja", "日本語"], ["ko", "한국어"], ["nl", "Nederlands"], ["no", "Norsk"], ["pl", "Polski"], ["pt", "Portugues (Brasil)"], ["ru", "Русский"], ["sv", "Svenska"], ["th", "ไทย"], ["tr", "Turkce"], ["vi", "Tieng Viet"]];
  var CODES = NAMES.map(function (n) { return n[0]; });
  var PATH2UI = { "zh-CN": "zh" }, UI2PATH = { "zh": "zh-CN" };
  function pathOf(c) { return UI2PATH[c] || c; }
  var root = document.documentElement;
  var served = root.getAttribute("data-ui") || "en";        // language the server rendered
  var enOnly = root.hasAttribute("data-en-only");           // English-only content page (guides)

  var seg = location.pathname.split("/")[1] || "";
  var urlLang = PATH2UI[seg] || (CODES.indexOf(seg) >= 0 ? seg : null);
  var lang = urlLang || localStorage.getItem("voxly-ui") || "en";
  if (CODES.indexOf(lang) < 0) lang = "en";
  if (urlLang) localStorage.setItem("voxly-ui", lang);

  var parts = location.pathname.split("/").filter(Boolean);
  if (urlLang) parts.shift();
  var fname = parts.length ? parts[parts.length - 1] : "";
  var embedded = document.getElementById("substrings");
  var D = embedded ? JSON.parse(embedded.textContent) : {};
  function str(k) { return D[k]; }

  var TITLES = { "tutorial.html": "doc_tutorial", "donate.html": "doc_donate", "support.html": "doc_support", "auth.html": "doc_auth", "privacy.html": "doc_privacy", "terms.html": "doc_terms" };
  function apply() {
    if (TITLES[fname] && str(TITLES[fname])) document.title = str(TITLES[fname]);
    root.lang = lang;
    root.dir = (lang === "ar" || lang === "fa") && !enOnly ? "rtl" : "ltr";
    document.querySelectorAll("[data-i18n]").forEach(function (el) { var v = str(el.getAttribute("data-i18n")); if (v != null) el.textContent = v; });
    if (enOnly) return;  // guide bodies are English; only the header/footer were translated above
    document.querySelectorAll("[data-i18n-html]").forEach(function (el) { var v = str(el.getAttribute("data-i18n-html")); if (v != null) el.innerHTML = v; });
    document.querySelectorAll("[data-i18n-ph]").forEach(function (el) { var v = str(el.getAttribute("data-i18n-ph")); if (v != null) el.setAttribute("placeholder", v); });
  }
  if (lang !== served) {
    fetch("/i18n-sub-parts/" + lang + ".json").then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) { D = d; apply(); } }).catch(function () {});
  }

  if (lang !== "en") {
    var p = "/" + pathOf(lang);
    document.querySelectorAll('a[href^="/"]').forEach(function (a) {
      var h = a.getAttribute("href");
      if (h === "/" || /^\/(tutorial|donate|support|auth|privacy|terms)\.html$/.test(h)) a.setAttribute("href", p + (h === "/" ? "/" : h));
    });
  }

  var sel = document.getElementById("sublang");
  if (sel) {
    if (!sel.options.length) sel.innerHTML = NAMES.map(function (n) { return '<option value="' + n[0] + '">' + n[1] + "</option>"; }).join("");
    sel.value = lang;
    sel.addEventListener("change", function () {
      localStorage.setItem("voxly-ui", sel.value);
      // English-only pages have no translated copy: go to the language's home page instead
      location.href = "/" + pathOf(sel.value) + "/" + (enOnly ? "" : fname);
    });
  }

  document.querySelectorAll("nav a").forEach(function (a) {
    if (fname && a.getAttribute("href").slice(-fname.length - 1) === "/" + fname) a.classList.add("on");
  });

  // Theme: same storage key and default (dark) as the home page; the <head>
  // boot script applies "light" before first paint.
  var tb = document.getElementById("themebtn");
  if (tb) {
    // Icon in an aria-hidden span; the button's name ("Dark theme") is a translated
    // span and its state is aria-pressed. Older markup (icon as the only text) still works.
    var icon = tb.querySelector("[aria-hidden]");
    var paint = function () {
      var light = root.classList.contains("light");
      (icon || tb).textContent = light ? "☾" : "☀";
      if (icon) tb.setAttribute("aria-pressed", String(!light));
    };
    paint();
    tb.addEventListener("click", function () {
      root.classList.toggle("light");
      localStorage.setItem("voxly-theme", root.classList.contains("light") ? "light" : "dark");
      paint();
    });
  }

  // Support form: the browser validates (required, email, length) before this runs.
  var form = document.getElementById("supform");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = form.querySelector('button[type="submit"]'), out = document.getElementById("supstatus");
      btn.disabled = true;
      out.textContent = "";
      fetch("/api/support", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.email.value, topic: form.topic.value,
                               message: form.message.value, website: form.website.value })
      }).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        out.textContent = str("sup_ok") || "Thanks — your message has been sent.";
        form.reset();
      }).catch(function () {
        out.textContent = str("sup_err") || "Sorry, your message could not be sent. Please try again later.";
      }).then(function () { btn.disabled = false; });
    });
  }
})();
