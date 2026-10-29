# SEO, AEO and GEO audit and implementation — text-2-speech.com

## Production results after deploy (2026-10-29 23:14, `master@83d7a47`)

- **Crawl of all live URLs:** 133 URLs, **0 issues** (baseline 752). `evidence/seo_crawl_prod_after.json`.
- **Lighthouse, production** (`evidence/after_prod.json`): Accessibility, Best Practices and SEO **100 on all 18 runs** (9 pages × mobile and desktop). Performance **100 on all desktop runs and on all mobile runs except the language home pages**.
  - Repeated mobile runs: `/` 100, 100, 95; `/es/` 100, 96, 98; `/de/` 99, 96, 98. Scores move with the lab "speed index" (1.1–4.1 s for the same URL).
  - Measured under 4× CPU throttling, the language home pages do the same work as `/` (script 78–84 ms vs 63 ms; layout 651–679 ms vs 760 ms), so this is measurement variance, not a regression.
  - One desktop run of `/support.html` scored SEO 92 because `robots.txt` could not be fetched during a deploy restart; three re-runs scored 100.
- **Page weight (gzip, live):** home 51 KB; sub-pages and guides 12–15 KB (sub-pages were 221 KB before).
- **Browser suites, production:** full suite 75/75 (Chromium, no-store mode for the support form), UI 36/36, Day-1 10/10, interruption 4/4.
- **Search Console:** the owner resubmitted `sitemap.xml` (previously read with 6 URLs; now 129) and is requesting indexing for the key pages. Indexing and query data will follow.
- Field Core Web Vitals (real users) will appear in Search Console once there is enough traffic; use them, not single lab runs, to judge mobile performance.

Date: 2026-10-29 · Branch: `seo/aeo-geo` (not deployed) · Baseline: production (`master@4da3cd2` code live as `290162e`).
All numbers below come from runs saved in [`evidence/`](evidence/). Nothing here is a ranking, indexing or traffic claim.

## 1. Scorecard

### Lighthouse (lab, 1 run per page and form factor)
Before = production 2026-10-29. After = this branch on a local server (uvicorn, **no gzip**: production adds gzip and HTTP/2 through nginx).

| Page | Form | Perf | A11y | BP | SEO | LCP | CLS | Weight |
|---|---|---|---|---|---|---|---|---|
| / | mobile | 100 → **99**¹ | 98 → **100** | 100 → **100** | 100 → **100** | 1318 → 1923 ms¹ | 0.043 → 0.039 | 49 → 180 KB¹ |
| /es/ | mobile | 100 → **99**¹ | 98 → **100** | 100 → **100** | 100 → **100** | 1412 → 1856 ms¹ | 0 → 0 | 49 → 181 KB¹ |
| /tutorial.html | mobile | 95 → **100** | 100 → **100** | 100 → **100** | 100 → **100** | 910 → 908 ms | 0.13 → 0 | 221 → 28 KB |
| /support.html | mobile | 95 → **100** | 100 → **100** | 100 → **100** | 100 → **100** | 901 → 908 ms | 0.13 → 0.035 | 221 → 29 KB |
| /privacy.html | mobile | 95 → **100** | 100 → **100** | 100 → **100** | 100 → **100** | 944 → 909 ms | 0.13 → 0.011 | 221 → 27 KB |
| / | desktop | 100 → **100** | 98 → **100** | 100 → **100** | 100 → **100** | 376 → 458 ms | 0.028 → 0.024 | 52 → 186 KB¹ |
| /es/ | desktop | 100 → **100** | 98 → **100** | 100 → **100** | 100 → **100** | 568 → 459 ms | 0.028 → 0.024 | 49 → 181 KB¹ |
| /tutorial.html | desktop | 100 → **100** | 100 → **100** | 100 → **100** | 100 → **100** | 332 → 248 ms | 0.014 → 0.002 | 221 → 28 KB |
| /support.html | desktop | 100 → **100** | 100 → **100** | 100 → **100** | 100 → **100** | 252 → 248 ms | 0.001 → 0 | 221 → 29 KB |
| /privacy.html | desktop | 100 → **100** | 100 → **100** | 100 → **100** | 100 → **100** | 330 → 248 ms | 0.003 → 0 | 221 → 27 KB |
| /voices.html *(new)* | mobile / desktop | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 1059 / 290 ms | 0 / 0 | 34 KB |
| /how-it-works.html *(new)* | mobile / desktop | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 907 / 248 ms | 0 / 0 | 27 KB |
| /guides/subtitles.html *(new)* | mobile / desktop | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 908 / 248 ms | 0 / 0 | 27 KB |
| /guides/mp3-vs-wav.html *(new)* | mobile / desktop | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 907 / 247 ms | 0 / 0 | 26 KB |

¹ The home page is measured **uncompressed** locally: 180 KB raw. Production serves it gzipped (the same page measured 49 KB and Performance 100 before), so the local 99 is a test-environment artefact, not a regression. It must be re-measured on production after deploy; that is a release gate (section 9).

### Site crawl (all sitemap URLs + aliases; `audit/scripts/seo_crawl.py`)
| | Before (production) | After (branch) |
|---|---:|---:|
| URLs crawled | 158 | 133 |
| Issues | **752** | **0** |
| Duplicate titles / descriptions | 157 / 157 | 0 / 0 |
| `og:url` ≠ canonical | 150 | 0 |
| Favicon not a crawlable file | 157 | 0 |
| Pages without structured data | 151 | 0 |

### Automated tests
API + SEO: **41/41** (`pytest tests/test_api.py`), including 7 SEO tests: every sitemap URL renders, is self-canonical with `og:url` = canonical, has one `h1`, a title and description within width limits, `index` robots and structured data, and no duplicate title or description across the sitemap. Also: language pages rendered server-side, breadcrumbs, noindex, structured-data types, robots/icons/caching, the live voices page. UI-language tests 25/25. Browser suite **75/75 on Chromium, Firefox and WebKit** (axe WCAG 2.2 AA zero violations on 12 pages × 2 themes × 2 widths, keyboard, RTL, support form, subtitles), plus UI 36/36, Day-1 10/10, interruption 4/4, re-checks 6/6.

## 2. Technical SEO issues and fixes

| # | Issue (evidence) | Fix | Verified by |
|---|---|---|---|
| T1 | 25 language versions of every page shared one English `<title>`, description, `og:title`/`og:description` (157 duplicates) | Server renders each language: title from the translated `h1`/`doc_*` strings, description from the translated tagline/intro (width-aware clipping, CJK counted double) | `test_every_sitemap_url_is_unique_and_self_canonical` |
| T2 | Sub-page text was English in HTML and translated only by JavaScript; AI crawlers that do not run JS saw English everywhere | Server-side translation of every `data-i18n` element, placeholder and HTML string, using the existing translations | `test_language_pages_rendered_server_side`, crawl word counts |
| T3 | `og:url` pointed at the English page on language URLs (150) | `og:url` = canonical; `og:locale` per language | crawl, tests |
| T4 | `/en/` was self-canonical, duplicating `/` | `/en/` canonical → `/`; hreflang `en` and `x-default` → `/`; `/en/` not in sitemap | `test_language_pages_rendered_server_side` |
| T5 | Favicon only as a `data:` URI (Google's SERP favicon needs a crawlable file) | `/favicon.svg`, `/favicon-48.png`, `/apple-touch-icon.png`, `/logo.png` (512 px) | `test_crawl_basics_icons_and_caching` |
| T6 | Donate page (non-working placeholder) indexable and in the sitemap | `noindex, follow` on Donate (Account already was); removed from sitemap | `test_breadcrumbs_and_noindex` |
| T7 | No breadcrumbs | Visible breadcrumb + `BreadcrumbList` on every indexable sub-page and guide, in the page language | `test_breadcrumbs_and_noindex` |
| T8 | Home heading order skipped levels (`h1` → `h3`; footer `h4`) — Lighthouse a11y 98 | Card and footer titles are `h2` (same look) | Lighthouse 100 |
| T9 | 216 KB all-language JS bundle on every sub-page; layout shift 0.13 on mobile (language select filled by JS) | Bundle removed (server renders the language; one 7 KB file is fetched only when a saved language differs); select pre-filled server-side with fixed width | Lighthouse: 221 → 28 KB, CLS 0.13 → ≤ 0.035 |
| T10 | Static files had no long cache policy | `subi18n.js?v=<version>` immutable for 1 year; icons 7 days; other static 1 hour; HTML `no-cache` | `test_crawl_basics_icons_and_caching` |
| T11 | `robots.txt` allowed crawling `/api/` (generation API, per-visitor files) | `Disallow: /api/`; everything else open to all crawlers incl. AI search crawlers | test |
| T12 | Support pages thin (≈150 words) while saying "the answers are in the FAQ" | The six FAQ answers are shown on the support page in its language | crawl |
| T13 | Long translated titles (66–79 chars) would be truncated | Over 70 columns: drop the " \| Text 2 Speech" suffix, or keep the part before " — " | crawl (0 issues) |
| T14 | English tutorial description 168 chars | Shortened to 151 | crawl |

Already in place before this work and re-verified: HTTPS everywhere, `http://` and `www.` → 301 to `https://text-2-speech.com`, HTTP/2, HTML 404 with correct status, 6 security headers, server-side `lang`/`dir`, hreflang (26 per page), FAQ structured data.

## 3. Structured data validation

Validation method: every JSON-LD block on every sitemap URL is parsed (crawl + tests), and the tests assert required properties per type. **Not run:** Google Rich Results Test and validator.schema.org (interactive web tools); run them on the deployed URLs before relying on rich results.

| Page type | Types | Notes |
|---|---|---|
| Home (25 languages) | `Organization` (`@id #org`, logo 512 px), `WebApplication` (`isAccessibleForFree`, `offers` price 0, `featureList`, publisher → #org, `inLanguage`), `WebSite` (publisher → #org, `inLanguage`), `FAQPage` (the visible FAQ, in the page language) | No `aggregateRating` or reviews: we have none, and inventing them is against Google's guidelines (tested) |
| Tutorial, Support, Privacy, Terms (25 languages each) | `BreadcrumbList` | Names and URLs in the page language |
| How it works, Subtitles guide, MP3 vs WAV | `BreadcrumbList`, `TechArticle` (headline, description, `datePublished`/`dateModified`, author and publisher = the Text 2 Speech organization, image) | Author is the organization; no invented people |
| Voices & languages | `BreadcrumbList` | Live data table, refreshed with the catalog |

FAQ rich results are limited by Google to well-known government and health sites since 2023, so `FAQPage` here is kept for entity clarity and answer engines, not for a SERP feature. `HowTo` was deliberately not used (Google deprecated HowTo rich results).

## 4. Sitemap and metadata

- `https://text-2-speech.com/sitemap.xml`: **129 URLs** = 5 translated pages (home, tutorial, support, privacy, terms) × 25 language versions (English at the root) + 4 English-only pages. Excludes Account, Donate and `/en/` aliases. Generated by the app, so it cannot drift from the routes.
- Every listed URL: 200, self-canonical, `index, follow`, unique title and description, one `h1`, structured data, `og:locale`, crawlable icons.
- Per-language metadata examples: `/de/` "Kostenloser Text-zu-Sprache-Generator online | Text 2 Speech"; `/ja/` "無料オンライン音声合成 | Text 2 Speech"; `/es/tutorial.html` "Tutorial de texto a voz — Cómo crear locuciones | Text 2 Speech".
- Full crawl output: `evidence/seo_crawl_after.json` (before: `evidence/seo_crawl_baseline.json`).

## 5. Core Web Vitals

Lab data only (Lighthouse table above). Field data (CrUX) was not queried: it needs a CrUX API key and enough real-user traffic.
- LCP: 0.25–1.9 s (local, uncompressed) — target ≤ 2.5 s met everywhere.
- CLS: ≤ 0.039 everywhere (sub-pages were 0.13 on mobile before).
- INP: not measurable in a lab run; Total Blocking Time 0 ms on every page (INP proxy). An earlier scripted interaction-to-paint measurement was 8–9 ms.
- Home page HTML grew because the translated FAQ, steps and use cases are now in the HTML (needed for crawlers); gzipped this is roughly +10 KB in production — confirm with the post-deploy Lighthouse run.

## 6. Content added (English; drafts for review before deploy)

| Page | Purpose | Facts used |
|---|---|---|
| `/how-it-works.html` | Product identity and documentation: what it is, free/no account, voices, the generation pipeline, a limits table, data handling, what it does not do | Code constants (5,000 chars, 1,500-char chunks, 25 pauses / 60 s, ±100), privacy behaviour |
| `/voices.html` | Every voice by language, generated from the live catalog (dead voices left out) | Live catalog |
| `/guides/subtitles.html` | How to create SRT/VTT from text; real example files; how cues are built; SRT vs VTT | Real output generated 2026-10-29 |
| `/guides/mp3-vs-wav.html` | When to use each format, with measured sizes; explains that WAV is decoded from the MP3 (no quality gain) | Measured: 9.53 s → 57,693 B MP3 vs 457,422 B WAV |

All four: one `h1`, question-style headings with the answer directly below, tables, breadcrumbs, `TechArticle` (except the data page), "Last updated" date, internal links (footer "Resources" on every page, links between guides). They are English only and say so: the language switcher sends visitors to their language's home page instead of a missing translation. **Please read them before deploy** — the brief asks that no unreviewed generated content is published.

## 7. AEO / GEO checklist

| # | Item | Status | Where |
|---|---|---|---|
| 1 | Clear product identity in one sentence, consistent across pages, structured data and llms.txt | Done | How it works, home `Organization`/`WebApplication`, llms.txt |
| 2 | Direct answers under question headings | Done | FAQ (home, 25 langs), support page FAQ, how-it-works, guides |
| 3 | Pricing / free usage answered | Done | FAQ, how-it-works |
| 4 | Limits answered precisely (characters, pauses, rate) | Done | How-it-works table, FAQ |
| 5 | Formats, subtitles, downloads answered | Done | Guides, FAQ |
| 6 | Privacy and data retention answered, naming the processor | Done | Privacy policy (25 langs), how-it-works |
| 7 | Languages and voices answerable ("does it support Telugu?") | Done | Voices page (live), voices count in metadata |
| 8 | Original, verifiable data | Done | Measured file sizes, real SRT/VTT output, live voice table |
| 9 | Essential content in server-rendered HTML (no JS needed) | Done | All pages, all languages |
| 10 | Entity-consistent structured data, no fake ratings | Done | Section 3 |
| 11 | Author/editorial/update information | Done (organization as author, update dates) | Guides |
| 12 | Crawler access incl. AI search crawlers | Done | robots.txt allows all except `/api/` |
| 13 | llms.txt kept accurate | Done | `/llms.txt` updated (links to new docs) |
| 14 | Honest comparison content | Planned, not written | Needs dated, sourced competitor facts (roadmap weeks 5–6) |
| 15 | Consistent external profiles (directories, social) | Not done | Needs your accounts |
| 16 | Search Console / Bing Webmaster verification and sitemap submission | Not verifiable here | GSC verification tag present; needs your access |

## 8. Blockers and items needing your access

- **Keyword volumes and difficulty:** the Ahrefs connector returned "Insufficient plan" (no API access on the plan). The Semrush account reported insufficient API units (more at https://www.semrush.com/mcp-access). The keyword matrix therefore uses Google Autocomplete phrasing (513 real queries) without volumes; volumes need one of those to be enabled.
- **Google Search Console / Bing Webmaster Tools:** no access from here. After deploy: submit `sitemap.xml` in both, check Page indexing for the 129 URLs, and use URL Inspection on `/`, `/es/`, `/voices.html`.
- **Analytics:** the site promises no cookies or analytics (privacy policy). Adding GA4 would contradict that. A cookieless option (self-hosted Plausible/Umami, or server-side counters) is a product and privacy decision; see `MONITORING_DASHBOARD_SPEC.md`.
- **External profiles and backlinks:** none created; nothing claimed.

## 9. Release gates and readiness

Ready to deploy after your review of the four new pages. Gates after deploy:
1. Lighthouse on production for `/`, `/es/`, a guide and `/voices.html` (mobile + desktop): expect Performance 100 with gzip; investigate if the home page is below 100.
2. Re-run `seo_crawl.py` against production: expect 0 issues.
3. Rich Results Test on `/`, `/tutorial.html`, `/guides/subtitles.html`.
4. Submit the sitemap in Search Console and Bing Webmaster Tools.

Readiness: technical SEO, accessibility and performance targets are met in the lab on the branch; AEO/GEO checklist 13 of 16 done, the other 3 need your accounts or a sourced comparison page. Search rankings and AI citations cannot be promised and are not claimed.
