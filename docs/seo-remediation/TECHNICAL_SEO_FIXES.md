# Technical SEO fixes (Agent 3)

Scope: structured data, sitemap, canonicals, hreflang, robots, headers, internal linking, repeatable CI checks.
Findings referenced by ID from [`SEO_AEO_GEO_AUDIT.md`](SEO_AEO_GEO_AUDIT.md) §3 and [`SAGE_FINDING_REMEDIATION.md`](SAGE_FINDING_REMEDIATION.md).
Schema details: [`SCHEMA_VALIDATION_REPORT.md`](SCHEMA_VALIDATION_REPORT.md).

## What changed (server.py)

| ID | Change | Before | After |
|---|---|---|---|
| L1 | Translated pages (home, tutorial, support, privacy, terms, donate, auth) rewrite their internal `href`s to the page's language prefix while rendering. English-only pages (how-it-works, voices, guides, new about/help) stay unprefixed. `subi18n.js` is unchanged and now a no-op on those links | Raw HTML of `/es/…` linked `/tutorial.html`; 96 language sub-pages had **0** inbound `<a>` links, the 24 language homes 4 | `/es/support.html` ← 6 language pages each; 0 orphans |
| — | Support page: the full copy of the home FAQ (6 questions and answers) is replaced by a short "FAQ" card that lists the questions, each linking to `<home of that language>#faqlist` (the existing id of the home FAQ list). Quick fixes and the contact form stay | Same Q&A text on 25 home pages and 25 support pages | Answers only on the home page; 6 contextual links support → home per language |
| R1 | `/index.html` → 301 `/` | 200, raw template (unfilled FAQ, 0 hreflang) | 301 |
| — | `/es`, `/zh-CN`, … (no slash) → 301 `/es/` (query string kept) | 200 duplicate of `/es/` | 301 |
| — | Raw `.html` files are no longer served by the static mount (`_Static`): every page goes through its rendered route | `/tutorial.html/` 200 (raw English template), `/not-found.html` 200 (soft 404) | 404 with the HTML 404 page |
| R2 | Page routes, `/sitemap.xml` and the redirects answer `HEAD` (`_route` helper = `api_route(GET, HEAD)`) | `HEAD /` gave the raw static file's headers | `HEAD /` 200 with the rendered page's Content-Length (123,783 = GET) |
| R3 | `/favicon.ico` → 301 `/favicon-48.png` | 404 | 301 → 200 |
| — | Sitemap `<lastmod>` per URL: the page's own `dateModified` (content pages), else the newest mtime of its sources (template + that language's strings JSON). Never "now" | no lastmod | 129 URLs with lastmod (all 2026-10-31 today, because every template was edited in this branch) |
| E2 / D1 | JSON-LD: see the schema report (contactPoint, copyrightHolder, localized WebApplication description, WebPage/ContactPage on sub-pages) | | |

Unchanged on purpose: the admin/page-view section, `robots.txt` (policy kept; syntax valid), security headers (already complete), hreflang generation (already correct), canonical generation.

Sitemap `xhtml:link` alternates: **not added**. Every translated page already carries the full 26-tag hreflang set in `<head>`; a second copy in the sitemap adds nothing for Google and is one more place to drift.

## Verification

### Status codes and URL consistency

| URL | GET | HEAD |
|---|---|---|
| `/`, `/es/`, `/tutorial.html`, `/how-it-works.html`, `/voices.html`, `/sitemap.xml` | 200 | 200 |
| `/es`, `/zh-CN` | 301 → `/es/`, `/zh-CN/` | 301 |
| `/index.html` | 301 → `/` | 301 |
| `/favicon.ico` | 301 → `/favicon-48.png` | 301 |
| `/en/` | 200, canonical `/` (alias kept: the language switcher uses it) | 200 |
| `/tutorial.html/`, `/not-found.html`, `/es/index.html`, `/es/nope.html`, `/guides/`, `/nope` | 404 (HTML page, not a soft 404) | 404 |
| `/admin` | 404 until a password is set, then `X-Robots-Tag: noindex, nofollow`; never in the sitemap | |

### Headers (HTML, static, 404, redirects, sitemap, robots)

`Strict-Transport-Security`, `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` are present on every response (middleware; the checker asserts it on every crawled page plus `/logo.png`, `/no-such-page`, `/es`, `/sitemap.xml`, `/robots.txt`).
Cache: HTML `no-cache`; versioned assets `immutable`; images 7 days; other static 1 h.

### hreflang

On every one of the 125 translated URLs: 26 `<link rel="alternate">` (25 languages + `x-default`), absolute, self-referencing, identical set on all 25 versions of a page (reciprocal), every target 200, indexable, self-canonical and with a matching `<html lang>` primary subtag; canonical = the page itself. English-only pages carry none (no translations). Test: `test_hreflang_reciprocal` + `seo_checks.py`.

### Page-level checks on all 129 sitemap URLs (seo_checks.py)

One H1; title 15–70 and description 70–165 display columns, all unique; viewport; self canonical = `og:url`; no `noindex`;
`og:title/description/url/image/type/site_name/locale` + `twitter:card`; `og:image` = `https://text-2-speech.com/og-image.png?v=2`; `<html lang>`; valid JSON-LD with required properties; BreadcrumbList on every nested page (not on homes); no `img` without `alt`; no unlabeled visible form control. **0 issues** (with the new A2 pages registered; see below).

Note: sub-pages have no `twitter:title/description/image`; X/Twitter falls back to the `og:` tags, so this is fine.

### Internal linking (crawl from `/` and the sitemap, `<a href>` + hreflang edges)

| Metric | Before (production audit, 2026-10-31) | After (local, current tree + A2 pages registered) |
|---|---|---|
| Sitemap URLs | 129 | 134 (129 + about, help, 3 guides, automatically from `_EN_PAGES`) |
| Orphans (no inbound `<a>`) | 96 language sub-pages | 0 |
| Broken internal links | 0 | 0 |
| Links to redirects | 0 | 0 |
| Missing `#fragment` targets | n/a | 0 |
| Generic anchors ("click here", "read more", …) | n/a | 0 |
| Max click depth from `/` | 2 (via hreflang) | 2 |

Contextual inbound links (inside `<main>`, breadcrumbs excluded, unique source pages), English pages:

| Page | Contextual inbound | Total inbound |
|---|---:|---:|
| `/help.html` | 8 | 8 |
| `/guides/subtitles.html` | 5 | 183 |
| `/guides/ai-voiceover.html` | 5 | 5 |
| `/guides/choose-voice.html` | 4 | 4 |
| `/guides/text-to-mp3.html` | 4 | 4 |
| `/guides/mp3-vs-wav.html` | 3 | 183 |
| `/voices.html` | 3 | 183 |
| `/privacy.html`, `/support.html` | 3 | 15 |
| `/how-it-works.html` | 2 | 183 |
| `/terms.html` | 2 | 15 |
| `/tutorial.html` | **1** | 15 |
| `/about.html` | **1** | **1** (needs the planned footer link) |

Links still wanted (L2): see "Requests for other agents" in the lead report and below.

### Crawler (`audit/scripts/seo_crawl.py http://localhost:8803`)

133 URLs, **0 issues** (2.8 s). Changes: user agent now contains "bot" (X3: the server no longer counts audit crawls as page views), `localhost` is fetched as `127.0.0.1` (Windows tried `::1` first, ~1 s per request), reports URLs that redirect and sitemap URLs without `lastmod`, and treats `support.html` as short-by-design like privacy/terms (the support page lost the duplicated FAQ, so 19 language versions are under 250 words).

## Repeatable checks

* `tests/seo_checks.py` — runs the app in-process (FastAPI TestClient, voice catalog mocked, page views to a temp DB), crawls `/` + the sitemap, exits 1 on any issue. `--json OUT` writes issues plus the link report (inbound counts, contextual sources, depth). ~6 s.
* CI (`.github/workflows/ci.yml`): new step "SEO checks" after the API tests, report uploaded as the `seo-report` artifact.
* New tests in `tests/test_api.py`: `test_sitemap_xml_and_lastmod`, `test_hreflang_reciprocal`, `test_seo_checks_pass`, `test_seo_checks_catch_defects` (proves the checker flags a broken page), `test_one_url_per_page`, `test_localized_internal_links`, `test_support_links_to_home_faq_instead_of_copying_it`, `test_home_schema_backed_by_page`; `test_sitemap_lists_every_language` now counts `len(_INDEXED) * 25 + len(_EN_PAGES)` so new English pages need no test edit.

## Deployment note (lastmod accuracy)

`deploy/release.sh` copies `web/` with `cp -r`, which sets every file's mtime to the deploy time. Translated pages and the home take their `lastmod` from mtimes, so after such a deploy they would all show the deploy date. Change that line to `cp -rp web /opt/voxly/web.new` (keeps the mtimes `git pull` left: only files changed by the pull get a new date). Docker `COPY` keeps mtimes already.
