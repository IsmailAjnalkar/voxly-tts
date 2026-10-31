# SAGE finding → remediation map

Finding IDs and evidence: [`SEO_AEO_GEO_AUDIT.md`](SEO_AEO_GEO_AUDIT.md) §3. **Evidence column: the lead fills it after integration** (test name, commit, file in `evidence/`, or URL after deploy). "Accept" means no code change, with the reason recorded.

SAGE cannot be rerun by us. The owner records the after-deploy SAGE scores in the last table.

| ID | Planned fix | Owner | Done when (acceptance) | Evidence (lead fills) |
|---|---|---|---|---|
| X1 | Before merging, put the live donation URLs into `web/index.html` and `web/donate.html` (owner confirms both accounts are his), or keep the placeholders and remove the buttons. Never deploy placeholders over live links | Lead + Owner | `git grep -E "EXAMPLE-replace-me\|buymeacoffee.com/yourname"` is empty, or the owner signs off in writing | Done: merged `origin/master` (7565220, f8d43ee) into the branch; real Stripe + Buy Me a Coffee links in `web/index.html` and `web/donate.html`, both return 200; `git grep EXAMPLE-replace-me` = 0; `verify_ui.mjs` donate check |
| E1 | `/about.html`: what the tool is, who operates it (only facts the owner confirms), how it works, contact route, last updated | A2 | 200, self-canonical, in the sitemap, linked from the footer, `AboutPage` + breadcrumb | `web/about.html` (54a1219): 200, self-canonical, in the sitemap, footer Product → About, AboutPage + BreadcrumbList; `seo_checks.py` 0 issues |
| E2 | `Organization`: add `legalName` (QINTAR LLC, **if the owner confirms**), `url`, `logo`, `contactPoint` (support page URL); `sameAs` only for profiles the owner provides. Same name in title, OG `site_name`, footer, llms.txt | A3 (+ Owner facts) | `tests/seo_checks.py` passes; the entity check in `AI_SEARCH_READINESS.md` §4 is consistent | `contactPoint` (support page) + WebSite `copyrightHolder` QINTAR LLC (ab5dedd); `legalName` **not** added until O2; `test_home_schema_backed_by_page` |
| E3 | Owner creates or lists official profiles; then add them to `sameAs` | Owner → A3 | Profiles exist and link back to the site | Open: owner (O9). No `sameAs` shipped |
| E4 | Accept: the organization stays the author. Named authors only for real people | — | Recorded | n/a |
| E5 | Owner decides whether to publish an email address. If yes, put it in the About and Support pages and in `contactPoint` | Owner | Decision recorded | Open: owner (O10) |
| A1q | `/help.html`: question headings with the answer in the first sentence. Covers devices (works in any modern browser; no app or extension), offline (no), API (no documented public API; `/api/` is the site's own endpoint, rate-limited), PDF/web reader (no; paste text or import .txt/.md), "unlimited" (5,000 characters per generation), commercial use (user responsible; per Terms) | A2 | Every answer matches code or Terms; linked from the footer and support page | `web/help.html` (54a1219); generator checks 9/9; axe 0 violations (1280 + 390 px) |
| A2q | Guides: `/guides/text-to-mp3.html` (how to), `/guides/ai-voiceover.html` (script → audio → subtitles → editor), `/guides/choose-voice.html` (from the live catalog). The slugs are as planned; the lead records the final ones | A2 | Each page has one intent (see `KEYWORD_STRATEGY.md` cannibalization table), tested facts, a date, a review step | `guides/text-to-mp3`, `guides/ai-voiceover`, `guides/choose-voice` (54a1219); linked from footer Guides column and the home + tutorial "Learn more" rows |
| A3q | Accept (heuristic); covered by A1q/A2q | — | — | n/a |
| C1 | Stable `id` anchors on h2/h3 of content pages; the key facts in a plain table or list (no accordion) on how-it-works | A2 / A1 | Anchors present; facts visible without interaction | Stable H2 ids + "On this page" TOCs (54a1219); generator anchor check passes; 0 duplicate paragraphs across 17 HTML files |
| C2 | Deferred: honest comparison page (content plan, weeks 9–10) | A2 later | — | n/a this PR |
| S1 | Wrap the home page's primary content in `<main>` (one per page) | A1 | `tests/seo_checks.py` or E2E asserts one `<main>`; axe passes | `<main id="main">` on home (bde8625); axe `landmark-one-main` resolved |
| S2 | Skip link "Skip to content" → `#main` as the first focusable element on all pages (home, sub-pages, generated pages) | A1 (+ A2 for generated pages) | E2E: the first Tab focuses the skip link; activating it moves focus into main | Skip link on every page: 36/36 axe + skip-target runs clean (18 pages × 1280/390 px); `lang_test.js` checks the translated skip link |
| G1 | `aria-label` on the hidden file input (harmless); keep the button's visible label | A1 | axe clean | File input labelled and described (bde8625); unlabelled controls on home 1 → 0 |
| G2 | Keep roving tabindex; verify Arrow/Home/End move between voice Preview buttons and Tab leaves the list | A1 / A4 | E2E keyboard test passes | Changed approach: roving tabindex replaced by one ▶ sample button per voice reachable after the selected radio; `tabindex="-1"` on home 47 → 1; keyboard-only E2E test passes on Chromium and Firefox |
| L1 | Server-side: rewrite internal hrefs to the page's language prefix when rendering (`/tutorial.html` → `/es/tutorial.html` on `/es/…`), for the translated pages only; English-only pages stay unprefixed. Keep `subi18n.js` as a no-op fallback | A3 | Rerun `evidence/route_map.py`: 0 sitemap URLs with 0 inbound links | Server-side language hrefs (ab5dedd); `test_localized_internal_links`; `seo_checks.py`: 0 orphans |
| L2 | Contextual links: home "how it works", formats and subtitles sections → the guides; tutorial → voices and guides | A3 / A1 | Inbound count for the guides rises beyond footer-only (route map) | Home "Learn more" row (how it works, voices, text to MP3, AI voiceover, subtitles, help), tutorial row, footer +5 links; `seo_checks.py`: max click depth 2 |
| K1 | Reduce the visible repetition of "Preview" in the voice list (for example an icon button with `aria-label="Preview <voice>"`, or the label only on the selected or hovered row) **without** losing an accessible name; keep "preview" only where it is the clearest word | A1 | The rendered-DOM count drops; axe clean; E2E preview still works | "preview" 50/663 = 7.54% → 0.47% of visible home text; top non-brand term 1.90% (`ACCESSIBILITY_REPORT.md`) |
| W1 | Not shipped (see `AI_SEARCH_READINESS.md` §6). Re-evaluate when WebMCP leaves origin trial | Lead | Decision recorded | n/a |
| W2 | Accept | — | — | n/a |
| D1 | Optional: `WebPage` with `isPartOf` `#website` and `publisher` `#org` on sub-pages; `AboutPage` on about, `FAQPage`-free help page unless the visible FAQ matches 1:1 | A3 | seo_checks JSON-LD tests pass | WebPage / ContactPage on translated sub-pages (ab5dedd) |
| D2 | After deploy: Rich Results Test on `/`, `/es/`, `/how-it-works.html`, `/about.html`, `/help.html`, one guide; validator.schema.org on the same | Lead / Owner | Screenshots or links saved in `evidence/` | Pending deploy (lead/owner) |
| D3 | Keep the guard tests (no ratings, reviews or `SearchAction` without backing) | A3 | Test present | `test_home_schema_backed_by_page` + `seo_checks.py` forbidden-property check |
| R1 | Optional: 301 `/index.html` → `/` | A3 | Route map shows 301 | `test_one_url_per_page` |
| R2 | Optional: answer `HEAD` on page routes (`api_route(methods=["GET","HEAD"])`) | A3 | `curl -I /` Content-Length matches GET | `test_one_url_per_page` (HEAD Content-Length = GET) |
| R3 | Optional: serve `/favicon.ico` (copy of the 48 px PNG, or a redirect to it) | A3 | 200 | `/favicon.ico` → 301 `/favicon-48.png` |
| H1x | Keep 26 per translated page; new English-only pages without hreflang | A3 | Route map | `test_hreflang_reciprocal`; `seo_checks.py` hreflang checks |
| X2 | Privacy policy: add one paragraph on the anonymous page-view counter and on server access logs (what is stored, retention). Wording approved by the owner; translate to 25 languages | Owner + A2 | Owner approval recorded | `priv_s2p` rewritten in 25 languages: page counter (date + path) and server access logs kept about 14 days (checked on the server: `/etc/logrotate.d/nginx` daily, rotate 14); `verify_full.mjs` privacy check. Owner approves the wording (O12) |
| X3 | `audit/scripts/seo_crawl.py` UA → include "bot" | A3 | Grep | `seo_crawl.py` user agent contains "bot" (ab5dedd) |

## SAGE scores (owner fills after deploy and a SAGE rerun)

| Category | Before (2026-10-31) | After | Date of rerun |
|---|---:|---:|---|
| Overall | 63 | | |
| Entity & Authority | 10 | | |
| Answer Targeting | 13 | | |
| Citability | 36 | | |
| Semantic HTML | 63 | | |
| Structured Data | 67 | | |
| Agent Accessibility | 73 | | |
| Internal Linking | 65 | | |
| Keyword Density | 75 | | |
| Agent Interactivity / WebMCP | 18 | (WebMCP not shipped; expect no change) | |
| Crawlability | 100 | | |
