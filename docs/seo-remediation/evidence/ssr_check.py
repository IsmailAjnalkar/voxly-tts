"""No-JS content check: fetch pages as a non-rendering crawler would and confirm the
primary content is in the HTML. Usage: python ssr_check.py BASE OUT.json"""
import html, json, re, sys, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
BASE, OUT = sys.argv[1].rstrip("/"), sys.argv[2]
# path -> list of (label, regex that must match the raw HTML outside <script>)
CHECKS = {
    "/": [("h1", r"<h1"), ("text input", r"<textarea"), ("generate button", r'id="gen'),
          ("FAQ answers", r'class="faqitem"'), ("how-it-works step", r"<h3>"), ("footer links", r'href="/how-it-works.html"')],
    "/es/": [("h1 translated", r'<h1[^>]*>[^<]*(texto|voz)'), ("FAQ answers", r'class="faqitem"'), ("lang=es", r'<html lang="es"')],
    "/ja/": [("lang=ja", r'<html lang="ja"'), ("FAQ answers", r'class="faqitem"')],
    "/ar/": [("rtl", r'dir="rtl"'), ("FAQ answers", r'class="faqitem"')],
    "/tutorial.html": [("h1", r"<h1"), ("steps", r"<h2")],
    "/support.html": [("FAQ on page", r"<h2[^>]*>FAQ</h2>"), ("contact form", r"<form")],
    "/how-it-works.html": [("limits table", r"<table"), ("5,000", r"5,000")],
    "/voices.html": [("voice table rows", r'<tr><th scope="row">'), ("live summary", r"voices in \d+ languages")],
    "/guides/subtitles.html": [("SRT example", r"\d\d:\d\d:\d\d,\d{3} --&gt;"), ("h1", r"<h1")],
    "/guides/mp3-vs-wav.html": [("table", r"<table"), ("measured bytes", r"57,693")],
    "/privacy.html": [("Microsoft named", r"Microsoft")],
}
res = {}
for path, checks in CHECKS.items():
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "t2s-ssr-check-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8", "replace")
    markup = re.sub(r"<script.*?</script>", " ", body, flags=re.S | re.I)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", " ", markup, flags=re.S))))
    res[path] = {"checks": {lbl: bool(re.search(rx, markup, re.I)) for lbl, rx in checks},
                 "faq_items": markup.count('class="faqitem"'), "voice_rows": markup.count('<th scope="row">'),
                 "visible_text_sample": text[:240]}
    ok = all(res[path]["checks"].values())
    print(f"{'OK  ' if ok else 'MISS'} {path:26s} {res[path]['checks']}")
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
