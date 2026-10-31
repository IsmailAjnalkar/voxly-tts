"""Route map of a deployment: every sitemap URL plus key unlisted routes.

Usage: python route_map.py BASE OUT_PREFIX
  e.g. python route_map.py https://text-2-speech.com evidence/route_map_prod
Writes OUT_PREFIX.csv (one row per URL) and OUT_PREFIX.json (rows + anomalies).
Sequential requests, no JS executed (what a non-rendering crawler sees).
The User-Agent contains "bot", so the site's page-view counter does not count it.
"""
import collections, csv, html, json, re, sys, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
BASE, OUT = sys.argv[1].rstrip("/"), sys.argv[2]
SITE = "https://text-2-speech.com"
UA = "Mozilla/5.0 (compatible; t2s-route-map-bot/1.0; seo audit)"

# Unlisted routes worth knowing about: aliases, noindex pages, machine files, API, errors.
EXTRA = ["/en/", "/en/tutorial.html", "/index.html", "/es", "/auth.html", "/donate.html", "/es/donate.html",
         "/admin", "/robots.txt", "/llms.txt", "/sitemap.xml", "/api/health", "/api/voices",
         "/docs", "/openapi.json", "/this-page-does-not-exist", "/favicon.ico", "/about.html", "/help.html"]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with opener.open(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace"), {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace") if e.fp else ""
        return e.code, body, {k.lower(): v for k, v in e.headers.items()}


def one(pattern, text):
    m = re.search(pattern, text, re.S | re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def text_of(fragment):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", fragment, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def words(t):
    return len(re.findall(r"[A-Za-zÀ-ɏЀ-ӿ؀-ۿऀ-ॿ]+", t)) + len(re.findall(r"[฀-๿぀-ヿ一-鿿가-힯]", t)) // 2


def norm(href, page_url):
    """Internal link -> site path (no query/fragment), else None."""
    u = urllib.parse.urljoin(page_url, html.unescape(href))
    p = urllib.parse.urlparse(u)
    if p.scheme not in ("http", "https") or p.netloc not in (urllib.parse.urlparse(BASE).netloc, "text-2-speech.com"):
        return None
    return p.path or "/"


_, sm, _ = get(BASE + "/sitemap.xml")
sitemap = [u.replace(SITE, "") or "/" for u in re.findall(r"<loc>([^<]+)</loc>", sm)]
paths = sitemap + [p for p in EXTRA if p not in sitemap]
rows, links_to = [], collections.defaultdict(set)
for p in paths:
    st, body, hdr = get(BASE + p)
    ctype = hdr.get("content-type", "")
    is_html = "text/html" in ctype
    row = {"path": p, "in_sitemap": p in sitemap, "status": st, "location": hdr.get("location", ""),
           "content_type": ctype.split(";")[0], "x_robots_tag": hdr.get("x-robots-tag", "")}
    if is_html and body:
        main = one(r"<main[^>]*>(.*?)</main>", body) or body
        types = []
        for ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, re.S):
            try:
                d = json.loads(ld)
                types += [str(n.get("@type")) for n in d.get("@graph", [d])]
            except ValueError:
                types.append("INVALID")
        h1s = [text_of(h) for h in re.findall(r"<h1[^>]*>(.*?)</h1>", body, re.S | re.I)]
        canon = one(r'<link rel="canonical" href="([^"]*)"', body)
        desc = one(r'<meta name="description" content="([^"]*)"', body)
        markup = re.sub(r"<script.*?</script>", " ", body, flags=re.S | re.I)  # JS template strings are not links
        hrefs = re.findall(r'<a\b[^>]*\bhref="([^"]+)"', markup, re.I)
        for h in hrefs:
            t = norm(h, BASE + p)
            if t is not None and t != p:
                links_to[t].add(p)
        row.update({
            "rendering": "server (HTML)" if words(text_of(main)) >= 50 else "thin without JS",
            "html_lang": one(r'<html[^>]*\blang="([^"]+)"', body),
            "title": one(r"<title>(.*?)</title>", body), "description_len": len(desc),
            "canonical": canon.replace(SITE, "") if canon else "",
            "self_canonical": (canon.replace(SITE, "") or "/") == p if canon else False,
            "meta_robots": one(r'<meta name="robots" content="([^"]*)"', body),
            "hreflang_count": len(re.findall(r'hreflang="', body)), "h1_count": len(h1s), "h1": " | ".join(h1s)[:120],
            "jsonld_types": " ".join(types), "main_words": words(text_of(main)),
            "internal_links_out": len({norm(h, BASE + p) for h in hrefs} - {None}),
            "tabindex_minus1": body.count('tabindex="-1"'),
            "preview_count": len(re.findall(r"preview", text_of(body), re.I)),
            "page_words": words(text_of(body)),
        })
    rows.append(row)
for r in rows:
    r["inbound_internal_pages"] = len(links_to.get(r["path"], ()))

# Anomalies worth a human look
anom = []
for r in rows:
    if r["in_sitemap"]:
        if r["status"] != 200: anom.append((r["path"], f"sitemap URL status {r['status']}"))
        if not r.get("self_canonical"): anom.append((r["path"], f"sitemap URL not self-canonical ({r.get('canonical')})"))
        if "noindex" in (r.get("meta_robots", "") + r["x_robots_tag"]): anom.append((r["path"], "sitemap URL is noindex"))
        if r.get("h1_count") != 1: anom.append((r["path"], f"{r.get('h1_count')} h1"))
        if r["inbound_internal_pages"] == 0: anom.append((r["path"], "no inbound internal links (orphan)"))
        if r.get("rendering") != "server (HTML)": anom.append((r["path"], "primary content thin without JS"))
linked_not_listed = sorted(t for t in links_to if t not in sitemap)
fields = ["path", "in_sitemap", "status", "location", "content_type", "rendering", "html_lang", "title",
          "description_len", "canonical", "self_canonical", "meta_robots", "x_robots_tag", "hreflang_count",
          "h1_count", "h1", "jsonld_types", "main_words", "page_words", "internal_links_out",
          "inbound_internal_pages", "tabindex_minus1", "preview_count"]
with open(OUT + ".csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fields, extrasaction="ignore")
    w.writeheader(); w.writerows(rows)
json.dump({"base": BASE, "sitemap_count": len(sitemap), "rows": rows, "anomalies": anom,
           "linked_but_not_in_sitemap": {t: len(links_to[t]) for t in linked_not_listed}},
          open(OUT + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"sitemap URLs: {len(sitemap)}; rows: {len(rows)}; anomalies: {len(anom)}")
for a in anom: print("  ANOMALY", *a)
print("linked but not in sitemap:", {t: len(links_to[t]) for t in linked_not_listed})
