"""SEO crawl: fetch every sitemap URL (plus extras) and report metadata quality.
Usage: python seo_crawl.py BASE OUT.json   (BASE e.g. https://text-2-speech.com)"""
import collections, html, json, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
BASE, OUT = sys.argv[1].rstrip("/"), sys.argv[2]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (seo-audit)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, "", dict(e.headers)


def one(pattern, text, flags=re.S | re.I):
    m = re.search(pattern, text, flags)
    return html.unescape(m.group(1)).strip() if m else None


_, sm, _ = get(BASE + "/sitemap.xml")
urls = re.findall(r"<loc>([^<]+)</loc>", sm)
urls = [u.replace("https://text-2-speech.com", BASE) for u in urls]
for extra in ("/auth.html", "/donate.html", "/en/", "/index.html"):
    if BASE + extra not in urls:
        urls.append(BASE + extra)
rows = []
for u in urls:
    st, body, hdr = get(u)
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    vis = html.unescape(text)
    words = len(re.findall(r"[A-Za-zÀ-ɏЀ-ӿ؀-ۿऀ-ॿ]+", vis)) +         len(re.findall(r"[฀-๿぀-ヿ一-鿿가-힯]", vis)) // 2
    lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)
    types, ld_ok = [], True
    for ld in lds:
        try:
            d = json.loads(ld)
            for n in d.get("@graph", [d]):
                types.append(n.get("@type"))
        except Exception:
            ld_ok = False
    rows.append({
        "url": u.replace(BASE, ""), "status": st,
        "title": one(r"<title>(.*?)</title>", body), "description": one(r'<meta name="description" content="([^"]*)"', body),
        "canonical": one(r'<link rel="canonical" href="([^"]*)"', body), "robots": one(r'<meta name="robots" content="([^"]*)"', body),
        "html_lang": one(r"<html[^>]*\blang=\"([^\"]+)\"", body), "h1": re.findall(r"<h1[^>]*>(.*?)</h1>", body, re.S),
        "og_title": one(r'<meta property="og:title" content="([^"]*)"', body), "og_url": one(r'<meta property="og:url" content="([^"]*)"', body),
        "og_locale": one(r'<meta property="og:locale" content="([^"]*)"', body),
        "hreflang": len(re.findall(r'hreflang="', body)), "jsonld_types": types, "jsonld_valid": ld_ok,
        "words_html": words, "x_robots": hdr.get("X-Robots-Tag"),
        "icon_file": bool(re.search(r'<link rel="(?:icon|shortcut icon)"[^>]+href="/[^"]+"', body)),
    })
canon_rows = [r for r in rows if not r["canonical"] or r["canonical"].replace("https://text-2-speech.com", "") == r["url"]]
dup_title = {t: n for t, n in collections.Counter(r["title"] for r in canon_rows).items() if n > 1}
dup_desc = {t: n for t, n in collections.Counter(r["description"] for r in canon_rows if r["description"]).items() if n > 1}
issues = []
W = lambda t: sum(2 if ord(ch) >= 0x2E80 else 1 for ch in t)  # display width: CJK counts double
for r in rows:
    if r["status"] != 200: issues.append((r["url"], f"status {r['status']}"))
    if not r["title"]: issues.append((r["url"], "no title"))
    elif not 15 <= W(r["title"]) <= 70: issues.append((r["url"], f"title width {W(r['title'])}"))
    if r["robots"] and "noindex" in r["robots"]: continue
    if r["canonical"] and r["canonical"].replace("https://text-2-speech.com", "") != r["url"]: continue  # alias
    if not r["description"]: issues.append((r["url"], "no meta description"))
    elif not 70 <= W(r["description"]) <= 165: issues.append((r["url"], f"description width {W(r['description'])}"))
    if r["title"] in dup_title: issues.append((r["url"], "duplicate title"))
    if r["description"] in dup_desc: issues.append((r["url"], "duplicate description"))
    if len(r["h1"]) != 1: issues.append((r["url"], f"{len(r['h1'])} h1"))
    if not r["canonical"]: issues.append((r["url"], "no canonical"))
    if not r["jsonld_valid"]: issues.append((r["url"], "invalid JSON-LD"))
    if r["og_url"] and r["canonical"] and r["og_url"] != r["canonical"]: issues.append((r["url"], "og:url != canonical"))
    if not r["icon_file"]: issues.append((r["url"], "favicon is not a crawlable file"))
    if r["words_html"] < 250 and not r["url"].endswith(("privacy.html", "terms.html")): issues.append((r["url"], f"thin HTML ({r['words_html']} words without JS)"))
json.dump({"pages": rows, "issues": issues}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(rows)} URLs crawled, {len(issues)} issues")
for kind, n in collections.Counter(i[1].split(" (")[0] if "thin" in i[1] else re.sub(r"\d+", "N", i[1]) for i in issues).most_common():
    print(f"  {n:4d} x {kind}")
for r in rows[:1] + [x for x in rows if x["url"] in ("/es/", "/tutorial.html", "/es/tutorial.html", "/en/", "/donate.html")]:
    print(f"  {r['url']:20s} title={r['title']!r:.70} canon={r['canonical']} lang={r['html_lang']} h1={len(r['h1'])} words={r['words_html']} ld={r['jsonld_types']}")
