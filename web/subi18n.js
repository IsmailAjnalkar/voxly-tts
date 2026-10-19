/* Text 2 Speech sub-page language runtime. Boots the page in the language named by
   the URL prefix (/es/, /de/ ...), falling back to the visitor's saved
   language; translates every [data-i18n] string from window.SUBI18N;
   keeps navigation inside the active language; drives the header
   language switcher and translated alert messages. */
(function () {
  var NAMES = [["en", "English"], ["zh", "简体中文"], ["zh-TW", "繁體中文"], ["ar", "العربية"], ["cs", "Cestina"], ["da", "Dansk"], ["de", "Deutsch"], ["es", "Espanol"], ["fa", "فارسی"], ["fr", "Francais"], ["hi", "हिन्दी"], ["hu", "Magyar"], ["id", "Bahasa Indonesia"], ["it", "Italiano"], ["ja", "日本語"], ["ko", "한국어"], ["nl", "Nederlands"], ["no", "Norsk"], ["pl", "Polski"], ["pt", "Portugues (Brasil)"], ["ru", "Русский"], ["sv", "Svenska"], ["th", "ไทย"], ["tr", "Turkce"], ["vi", "Tieng Viet"]];
  var CODES = NAMES.map(function (n) { return n[0]; });
  var PATH2UI = { "zh-CN": "zh" }, UI2PATH = { "zh": "zh-CN" };
  function pathOf(c) { return UI2PATH[c] || c; }

  var seg = location.pathname.split("/")[1] || "";
  var urlLang = PATH2UI[seg] || (CODES.indexOf(seg) >= 0 ? seg : null);
  var lang = urlLang || localStorage.getItem("voxly-ui") || "en";
  if (CODES.indexOf(lang) < 0) lang = "en";
  if (urlLang) localStorage.setItem("voxly-ui", lang);

  var ALL = window.SUBI18N || {};
  var D = ALL[lang] || ALL.en || {};
  function str(k) { return D[k] != null ? D[k] : (ALL.en || {})[k]; }

  var parts = location.pathname.split("/").filter(Boolean);
  if (urlLang) parts.shift();
  var fname = parts.length ? parts[parts.length - 1] : "";
  var TITLES = { "tutorial.html": "doc_tutorial", "donate.html": "doc_donate", "support.html": "doc_support", "auth.html": "doc_auth", "privacy.html": "doc_privacy", "terms.html": "doc_terms" };
  if (TITLES[fname] && str(TITLES[fname])) document.title = str(TITLES[fname]);

  document.documentElement.lang = lang;
  if (lang === "ar" || lang === "fa") document.documentElement.dir = "rtl";

  document.querySelectorAll("[data-i18n]").forEach(function (el) { var v = str(el.getAttribute("data-i18n")); if (v != null) el.textContent = v; });
  document.querySelectorAll("[data-i18n-html]").forEach(function (el) { var v = str(el.getAttribute("data-i18n-html")); if (v != null) el.innerHTML = v; });
  document.querySelectorAll("[data-i18n-ph]").forEach(function (el) { var v = str(el.getAttribute("data-i18n-ph")); if (v != null) el.setAttribute("placeholder", v); });

  if (lang !== "en") {
    var p = "/" + pathOf(lang);
    document.querySelectorAll('a[href^="/"]').forEach(function (a) {
      var h = a.getAttribute("href");
      if (h === "/" || /^\/(tutorial|donate|support|auth|privacy|terms)\.html$/.test(h)) a.setAttribute("href", p + (h === "/" ? "/" : h));
    });
  }

  var sel = document.getElementById("sublang");
  if (sel) {
    sel.innerHTML = NAMES.map(function (n) { return '<option value="' + n[0] + '">' + n[1] + "</option>"; }).join("");
    sel.value = lang;
    sel.addEventListener("change", function () {
      localStorage.setItem("voxly-ui", sel.value);
      location.href = "/" + pathOf(sel.value) + "/" + (fname || "");
    });
  }

  window.subAlert = function (key) { var v = str(key); alert(v != null ? v : key); };
})();
