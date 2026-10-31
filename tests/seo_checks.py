"""Repeatable SEO checks, no network: renders every page through the app (speech provider
mocked, as in tests/test_api.py), crawls internal links from / and the sitemap, and fails
on what search engines would trip over.

Run:  python tests/seo_checks.py [--json OUT.json]      (exit 1 when there are issues)
Also run by tests/test_api.py (test_seo_checks_pass).

Checks, per indexable page (the sitemap): status 200, title and description present,
unique and within snippet width, one H1, viewport, self canonical (= og:url), no
noindex, Open Graph / Twitter tags, JSON-LD that parses and has Google's required
properties (no ratings, reviews, speakable, sameAs or SearchAction we can't back),
FAQPage text identical to the visible FAQ, BreadcrumbList ending at the page,
reciprocal hreflang sets (absolute, self-referencing, 200, indexable, right language).
Site-wide: sitemap XML with lastmod, no noindex/alias/admin URL in it, every crawled
indexable page in it, broken internal links and links to redirects, missing #fragments,
img without alt, unlabeled form controls, generic anchor text, orphans, click depth > 3,
404 status for unknown URLs, security and cache headers."""
import collections
import datetime
import html
import json
import re
import sys
import tempfile
import xml.etree.ElementTree as ET  # parses our own sitemap only
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock
from urllib.parse import urldefrag

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server  # noqa: E402

SITE = server.SITE
OG_IMAGE = f"{SITE}/og-image.png?v=2"
TITLE_W, DESC_W = (15, 70), (70, 165)   # display width (CJK counts double), as in snippets
GENERIC_ANCHORS = {"click here", "here", "read more", "more", "learn more", "this", "link", "this page"}
FORBIDDEN_LD = ("aggregateRating", "review", "speakable", "sameAs", "SearchAction")  # nothing verified backs these
SECURITY = ("strict-transport-security", "content-security-policy", "x-content-type-options",
            "referrer-policy", "permissions-policy", "x-frame-options")
LABELLED_BY_TYPE = {"hidden", "submit", "button", "reset", "image"}


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.title, self.meta, self.canon, self.alts, self.h1 = None, {}, [], [], 0
        self.links, self.ids, self.lds, self.imgs_no_alt, self.controls = [], set(), [], 0, []
        self.label_for, self.html_lang, self.text = set(), None, []
        self._tag, self._a, self._label, self._main, self._crumbs, self._skip = None, None, 0, 0, 0, 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "html":
            self.html_lang = a.get("lang")
        elif tag == "title":
            self._tag = "title"
        elif tag == "meta" and (a.get("name") or a.get("property")):
            self.meta[a.get("name") or a.get("property")] = a.get("content")
        elif tag == "link" and a.get("rel") == "canonical":
            self.canon.append(a.get("href"))
        elif tag == "link" and a.get("rel") == "alternate" and a.get("hreflang"):
            self.alts.append((a["hreflang"], a.get("href")))
        elif tag == "h1":
            self.h1 += 1
        elif tag == "main":
            self._main += 1
        elif tag == "nav" and "crumbs" in (a.get("class") or ""):
            self._crumbs += 1
        elif tag == "a" and "href" in a:
            self._a = {"href": a["href"], "text": "", "label": a.get("aria-label"),
                       "contextual": bool(self._main and not self._crumbs)}
        elif tag == "img" and "alt" not in a:
            self.imgs_no_alt += 1
        elif tag == "label":
            self._label += 1
            if a.get("for"):
                self.label_for.add(a["for"])
        elif tag in ("input", "select", "textarea") and a.get("type") not in LABELLED_BY_TYPE and "hidden" not in a:
            ok = self._label or a.get("aria-label") or a.get("aria-labelledby") or a.get("title")
            self.controls.append((a.get("id") or a.get("name") or tag, bool(ok)))
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._tag = "ld"
            self.lds.append("")
        elif tag in ("script", "style", "template"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("title", "script"):
            if self._tag:
                self._tag = None
            elif tag == "script":
                self._skip -= 1
        elif tag in ("style", "template"):
            self._skip -= 1
        elif tag == "a" and self._a:
            self.links.append(self._a)
            self._a = None
        elif tag == "label":
            self._label -= 1
        elif tag == "main":
            self._main -= 1
        elif tag == "nav" and self._crumbs:
            self._crumbs -= 1

    def handle_data(self, data):
        if self._tag == "title":
            self.title = (self.title or "") + data
        elif self._tag == "ld":
            self.lds[-1] += data
        elif not self._skip:
            self.text.append(data)
            if self._a:
                self._a["text"] += data


def _norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def _ld_nodes(p, issues, url):
    nodes = []
    for raw in p.lds:
        try:
            d = json.loads(raw)
        except ValueError as e:
            issues.append((url, f"invalid JSON-LD: {e}"))
            continue
        if d.get("@context") not in ("https://schema.org", "https://schema.org/"):
            issues.append((url, "JSON-LD @context is not https://schema.org"))
        nodes += d.get("@graph", [d])
        for bad in FORBIDDEN_LD:
            if f'"{bad}"' in raw:
                issues.append((url, f"JSON-LD has {bad} (not backed by verified data)"))
    return nodes


def _check_ld(nodes, p, url, canon, issues):
    """Required properties from Google's structured-data docs (plus schema.org basics)."""
    visible = _norm(" ".join(p.text))
    date = re.compile(r"^\d{4}-\d\d-\d\d")
    for n in nodes:
        t, err = n.get("@type"), lambda m: issues.append((url, f"{n.get('@type')}: {m}"))
        if not t:
            err("no @type")
        elif t == "Organization":
            for k in ("name", "url"):
                if not n.get(k):
                    err(f"missing {k}")
            if n.get("logo") and not str((n["logo"] or {}).get("url", n["logo"])).startswith(SITE):
                err("logo not on the site")
            cp = n.get("contactPoint")
            if cp and not (cp.get("contactType") and (cp.get("url") or cp.get("email") or cp.get("telephone"))):
                err("contactPoint needs contactType and url/email/telephone")
        elif t == "WebSite":
            for k in ("name", "url"):
                if not n.get(k):
                    err(f"missing {k}")
        elif t in ("WebPage", "ContactPage", "AboutPage", "CollectionPage"):
            if n.get("url") != canon or _norm(n.get("name")) != _norm(p.title):
                err("url must be the canonical and name the page title")
        elif t in ("WebApplication", "SoftwareApplication"):
            o = n.get("offers") or {}
            if not n.get("name") or "price" not in o or not o.get("priceCurrency"):
                err("needs name, offers.price and offers.priceCurrency")
            if n.get("description") and _norm(n["description"]) not in visible:
                err("description is not visible on the page")
        elif t == "FAQPage":
            qs = n.get("mainEntity") or []
            if not qs:
                err("no mainEntity")
            for q in qs:
                a = (q.get("acceptedAnswer") or {}).get("text")
                if q.get("@type") != "Question" or not q.get("name") or not a:
                    err("Question needs name and acceptedAnswer.text")
                elif _norm(q["name"]) not in visible or _norm(a) not in visible:
                    err(f"FAQ text differs from the visible FAQ: {q['name'][:60]!r}")
        elif t == "BreadcrumbList":
            items = n.get("itemListElement") or []
            if [i.get("position") for i in items] != list(range(1, len(items) + 1)) or len(items) < 2:
                err("positions must run 1..n (n >= 2)")
            if any(not i.get("name") or not str(i.get("item", "")).startswith(SITE) for i in items):
                err("every item needs a name and an absolute item URL")
            if items and items[-1].get("item") != canon:
                err("last item is not the page itself")
        elif t in ("Article", "TechArticle", "BlogPosting", "NewsArticle"):
            for k in ("headline", "image", "datePublished", "dateModified", "author"):
                if not n.get(k):
                    err(f"missing {k}")
            if len(n.get("headline") or "") > 110:
                err("headline over 110 characters")
            if not all(date.match(str(n.get(k, ""))) for k in ("datePublished", "dateModified")) \
                    or str(n.get("dateModified")) < str(n.get("datePublished")):
                err("dates must be ISO 8601 and dateModified >= datePublished")
            if not (n.get("author") or {}).get("name"):
                err("author needs a name")
            if n.get("dateModified") and n["dateModified"][:10] not in re.findall(r'datetime="([^"]+)"', p.src):
                err("dateModified is not shown on the page (<time datetime>)")


def run(client):
    """Crawl the app and return (issues, report)."""
    issues, pages = [], {}
    sm = client.get("/sitemap.xml")
    try:
        root = ET.fromstring(sm.content)
    except ET.ParseError as e:
        return [("/sitemap.xml", f"invalid XML: {e}")], {}
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    entries = [(u.findtext("s:loc", namespaces=ns), u.findtext("s:lastmod", namespaces=ns)) for u in root.findall("s:url", ns)]
    sitemap = [loc for loc, _ in entries]
    today = datetime.date.today().isoformat()
    for loc, lastmod in entries:
        if not loc or not loc.startswith(SITE + "/"):
            issues.append(("/sitemap.xml", f"loc not absolute on {SITE}: {loc}"))
        if not lastmod or not re.fullmatch(r"\d{4}-\d\d-\d\d", lastmod) or lastmod > today:
            issues.append(("/sitemap.xml", f"bad lastmod {lastmod!r} for {loc}"))
        if "/admin" in (loc or ""):
            issues.append(("/sitemap.xml", "lists /admin"))
    for loc, n in collections.Counter(sitemap).items():
        if n > 1:
            issues.append(("/sitemap.xml", f"duplicate loc {loc}"))

    # Crawl: start at / and every sitemap URL; follow <a href> and hreflang links on the site.
    edges, todo, redirects = collections.defaultdict(set), ["/"] + [u.replace(SITE, "") for u in sitemap], {}
    while todo:
        path = todo.pop()
        if path in pages or path in redirects:
            continue
        r = client.get(path, follow_redirects=False)
        if r.status_code in (301, 302, 307, 308):
            redirects[path] = r.headers["location"]
            todo.append(r.headers["location"])
            continue
        pages[path] = {"status": r.status_code, "headers": r.headers, "html": None}
        if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
            continue
        p = pages[path]["html"] = Page(r.text)
        p.src = r.text
        for a in p.links + [{"href": h} for _, h in p.alts]:
            href = a["href"].replace(SITE, "") if a["href"].startswith(SITE) else a["href"]
            if not href.startswith("/") or href.startswith("//"):
                continue
            target = urldefrag(href)[0] or path
            edges[path].add(target)
            todo.append(target)

    def final(path, seen=()):
        while path in redirects and path not in seen:
            seen += (path,)
            path = redirects[path]
        return path

    indexable = []
    for path, pg in pages.items():
        p = pg["html"]
        if p is None:
            continue
        canon = p.canon[0] if p.canon else None
        noindex = "noindex" in (p.meta.get("robots") or "") or "noindex" in pg["headers"].get("x-robots-tag", "")
        if not noindex and canon == SITE + path:
            indexable.append(path)
        if SITE + path in sitemap and (noindex or canon != SITE + path):
            issues.append((path, "in the sitemap but noindex or not self-canonical"))
        if p.imgs_no_alt:
            issues.append((path, f"{p.imgs_no_alt} img without alt"))
        for cid, ok in p.controls:
            if not ok and cid not in p.label_for:
                issues.append((path, f"form control without a label: {cid}"))
        for a in p.links:
            text = _norm(a["text"]) or _norm(a["label"])
            if not text:
                issues.append((path, f"link without text: {a['href']}"))
            elif text.lower() in GENERIC_ANCHORS:
                issues.append((path, f"generic anchor text {text!r} -> {a['href']}"))
        if len(p.canon) > 1:
            issues.append((path, "more than one canonical"))
        for k in SECURITY:
            if k not in pg["headers"]:
                issues.append((path, f"missing header {k}"))
        if pg["headers"].get("cache-control") != "no-cache":
            issues.append((path, f"HTML cache-control {pg['headers'].get('cache-control')!r}, want no-cache"))

    titles, descs = collections.defaultdict(list), collections.defaultdict(list)
    for path in [u.replace(SITE, "") for u in sitemap]:
        pg = pages.get(final(path))
        if path in redirects or not pg or pg["status"] != 200 or pg["html"] is None:
            issues.append((path, f"sitemap URL is not a 200 page ({redirects.get(path) or (pg or {}).get('status')})"))
            continue
        p, canon = pg["html"], SITE + path
        m = p.meta
        title, desc = _norm(p.title), _norm(m.get("description"))
        titles[title].append(path)
        descs[desc].append(path)
        if not TITLE_W[0] <= server._width(title) <= TITLE_W[1]:
            issues.append((path, f"title width {server._width(title)} (want {TITLE_W[0]}-{TITLE_W[1]}): {title!r}"))
        if not DESC_W[0] <= server._width(desc) <= DESC_W[1]:
            issues.append((path, f"description width {server._width(desc)} (want {DESC_W[0]}-{DESC_W[1]})"))
        if p.h1 != 1:
            issues.append((path, f"{p.h1} h1"))
        if not p.canon or p.canon[0] != canon:
            issues.append((path, f"canonical {p.canon} is not the page itself"))
        if "width=device-width" not in (m.get("viewport") or ""):
            issues.append((path, "no responsive viewport"))
        if "index" not in (m.get("robots") or "index"):
            issues.append((path, f"robots {m.get('robots')!r}"))
        for k in ("og:title", "og:description", "og:url", "og:image", "og:type", "og:site_name", "og:locale", "twitter:card"):
            if not m.get(k):
                issues.append((path, f"missing {k}"))
        if m.get("og:url") and m["og:url"] != canon:
            issues.append((path, "og:url != canonical"))
        if m.get("og:image") and m["og:image"] != OG_IMAGE:
            issues.append((path, f"og:image {m['og:image']} (want {OG_IMAGE})"))
        if not p.html_lang:
            issues.append((path, "no <html lang>"))
        nodes = _ld_nodes(p, issues, path)
        if not nodes:
            issues.append((path, "no structured data"))
        if not re.fullmatch(r"/([\w-]+/)?", path) and not any(n.get("@type") == "BreadcrumbList" for n in nodes):  # not on homes
            issues.append((path, "nested page without BreadcrumbList"))
        _check_ld(nodes, p, path, canon, issues)

        # hreflang: absolute, self-referencing, x-default, reciprocal, 200 + indexable + same language
        if p.alts:
            langs = dict(p.alts)
            if len(langs) != len(p.alts):
                issues.append((path, "duplicate hreflang codes"))
            if "x-default" not in langs:
                issues.append((path, "hreflang without x-default"))
            if canon not in langs.values():
                issues.append((path, "hreflang set does not include the page itself"))
            for code, href in p.alts:
                tp = (href or "").replace(SITE, "")
                if not (href or "").startswith(SITE + "/"):
                    issues.append((path, f"hreflang {code} not absolute: {href}"))
                    continue
                tg = pages.get(tp)
                th = tg and tg["html"]
                if not th or tg["status"] != 200:
                    issues.append((path, f"hreflang {code} -> {tp} is not a 200 page"))
                    continue
                if th.canon[:1] != [href] or "noindex" in (th.meta.get("robots") or ""):
                    issues.append((path, f"hreflang {code} -> {tp} is not indexable/self-canonical"))
                if sorted(th.alts) != sorted(p.alts):
                    issues.append((path, f"hreflang not reciprocal with {tp}"))
                if code != "x-default" and (th.html_lang or "").split("-")[0] != code.split("-")[0]:
                    issues.append((path, f"hreflang {code} -> {tp} has <html lang={th.html_lang}>"))
    for kind, seen in (("title", titles), ("description", descs)):
        for v, ps in seen.items():
            if len(ps) > 1:
                issues.append((ps[0], f"duplicate {kind} on {len(ps)} pages: {ps[:4]}"))
    for path in indexable:
        if SITE + path not in sitemap:
            issues.append((path, "indexable page missing from the sitemap"))

    # Links: broken, via redirects, missing fragments.
    inbound, contextual = collections.defaultdict(set), collections.defaultdict(set)
    for path, pg in pages.items():
        for a in (pg["html"].links if pg["html"] else []):
            href = a["href"].replace(SITE, "") if a["href"].startswith(SITE) else a["href"]
            if not href.startswith("/") or href.startswith("//"):
                continue
            target, frag = urldefrag(href)
            target = target or path
            if target in redirects:
                issues.append((path, f"links to a redirect: {href} -> {redirects[target]}"))
            tg = pages.get(final(target))
            if not tg or tg["status"] != 200:
                issues.append((path, f"broken link {href} ({tg and tg['status']})"))
                continue
            if frag and tg["html"] and frag not in tg["html"].ids:
                issues.append((path, f"link to missing #{frag} on {target}"))
            if final(target) != path:
                inbound[final(target)].add(path)
                if a["contextual"]:
                    contextual[final(target)].add(path)

    # Click depth from / (links and hreflang alternates, which crawlers follow) and orphans.
    depth, frontier = {"/": 0}, ["/"]
    while frontier:
        nxt = []
        for u in frontier:
            for v in edges[u]:
                v = final(v)
                if v not in depth and v in pages:
                    depth[v] = depth[u] + 1
                    nxt.append(v)
        frontier = nxt
    for path in indexable:
        if path != "/" and not inbound[path]:
            issues.append((path, "orphan: no internal <a> link points here"))
        if depth.get(path, 99) > 3:
            issues.append((path, f"click depth {depth.get(path, 'unreachable')} from /"))

    # Status codes and headers beyond the crawl.
    for path in ("/no-such-page", "/es/no-such-page.html", "/guides/no-such-guide.html", "/tutorial.html/", "/not-found.html"):
        r = client.get(path, follow_redirects=False)
        if r.status_code != 404:
            issues.append((path, f"unknown URL answers {r.status_code}, want 404 (soft 404)"))
    for path in ("/logo.png", "/no-such-page", "/es", "/sitemap.xml", "/robots.txt"):
        h = client.get(path, follow_redirects=False).headers
        for k in SECURITY:
            if k not in h:
                issues.append((path, f"missing header {k}"))
    r = client.get("/admin")  # 404 until a password is set, then a noindex login page
    if r.status_code != 404 and "noindex" not in r.headers.get("x-robots-tag", ""):
        issues.append(("/admin", "admin is not noindex"))
    robots = client.get("/robots.txt").text
    if f"Sitemap: {SITE}/sitemap.xml" not in robots or re.search(r"(?mi)^Disallow:\s*/\s*$", robots):
        issues.append(("/robots.txt", "robots.txt must allow the site and point to the sitemap"))

    report = {
        "urls_crawled": len(pages) + len(redirects), "pages_200": sum(pg["status"] == 200 for pg in pages.values()),
        "sitemap_urls": len(sitemap), "indexable": len(indexable), "redirects": redirects,
        "max_depth": max(depth.get(p, 99) for p in indexable),
        "inbound_links": {p: len(inbound[p]) for p in sorted(indexable)},
        "contextual_inbound": {p: sorted(contextual[p]) for p in sorted(indexable)},
        "depth": {p: depth.get(p) for p in sorted(indexable)},
    }
    return issues, report


def client():
    from fastapi.testclient import TestClient
    server._voices_cache.update(data=None, ts=0)
    return TestClient(server.app, raise_server_exceptions=False)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    tmp = Path(tempfile.mkdtemp())  # page views of the crawl must not reach the real counts
    server.STATS_DB, server.ADMIN_FILE = tmp / "views.sqlite3", tmp / "admin.json"
    voices = [{"ShortName": "en-US-AriaNeural", "Locale": "en-US", "Gender": "Female", "FriendlyName": "Aria",
               "Name": "Microsoft Server Speech Text to Speech Voice (en-US, AriaNeural)"}]
    with mock.patch.object(server.edge_tts, "list_voices", mock.AsyncMock(return_value=voices)):
        issues, report = run(client())
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(
            json.dumps({"issues": issues, "report": report}, ensure_ascii=False, indent=1), encoding="utf-8")
    few = [p for p, n in report.get("inbound_links", {}).items() if n < 3]
    print(f"{report.get('urls_crawled')} URLs crawled, {report.get('indexable')} indexable, "
          f"{report.get('sitemap_urls')} in sitemap, max click depth {report.get('max_depth')}, "
          f"{len(report.get('redirects', {}))} redirects, {len(issues)} issues")
    if few:
        print(f"note: {len(few)} indexable pages have fewer than 3 inbound links: {few[:10]}")
    for path, msg in issues:
        print(f"  {path}: {msg}")
    sys.exit(1 if issues else 0)
