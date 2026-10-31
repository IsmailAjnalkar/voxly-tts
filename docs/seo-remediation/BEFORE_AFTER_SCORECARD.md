# Before / after scorecard — text-2-speech.com SAGE remediation

Branch `seo/sage-remediation`, 2026-10-31. Every value below was measured; nothing is estimated. Where a value can only be measured after deploy or by the owner, the cell says so.

## SAGE (owner tool — not rerunnable by us)

| Category | Before | After | What changed (evidence) |
|---|---:|---|---|
| Overall | 63 | **owner rerun after deploy** | — |
| Entity & Authority | 10 | owner rerun | `/about.html`, `/help.html`; Organization `contactPoint`, WebSite `copyrightHolder`; consistent "Text 2 Speech" naming. Not shipped until the owner confirms: `legalName`, `sameAs`, people, address (O2, O9, O10) |
| Answer Targeting | 13 | owner rerun | 3 answer-first guides + help centre; first paragraphs 40–60 words; stable ids |
| Citability | 36 | owner rerun | definitions first, tables for limits/formats, Limitations + Troubleshooting sections, TOCs, 0 duplicate paragraphs (17 HTML files) |
| Semantic HTML | 63 | owner rerun | `<main id="main">` on home, labelled navs, one H1, no skipped levels |
| Structured Data | 67 | owner rerun | WebPage/ContactPage on sub-pages, AboutPage, TechArticle on guides, FAQ text = visible FAQ in 25 languages; validator.schema.org 0 errors on 10 URLs |
| Agent Accessibility | 73 | owner rerun | skip link, labelled file input, `tabindex="-1"` 47 → 1, live region, names on every control |
| Internal Linking | 65 | owner rerun | language pages link in their own language (96 sub-pages had 0 inbound HTML links → 0 orphans); footer +5 links; "Learn more" rows |
| Keyword Density | 75 | owner rerun | "preview" 7.54% → 0.47% of visible home text |
| Agent Interactivity / WebMCP | 18 | expected unchanged | Not shipped: origin trial, draft spec (`AI_SEARCH_READINESS.md` §6) |

## Measured by us

| Metric | Before | After | Evidence |
|---|---|---|---|
| axe WCAG 2.2 AA violations | 0 on tested pages; best-practice `landmark-one-main` + 118 × `region` on home | **0** on 18 pages × 1280/390 px (36 runs), incl. RTL and the 5 new pages | `ACCESSIBILITY_REPORT.md`; lead's `axe_all` run |
| Skip link | none | every page, target exists | same run |
| `tabindex="-1"` on home | 47 | 1 (Results heading, focus target after Delete) | `ACCESSIBILITY_REPORT.md` |
| Unlabelled controls on home | 1 | 0 | same |
| Highest non-brand term, home | preview 7.54% | 1.90% | same |
| Indexable URLs / in sitemap | 129 / 129 | 134 / 134 | `tests/seo_checks.py` |
| Sitemap `lastmod` | none | all URLs | `test_sitemap_xml_and_lastmod` |
| SEO issues (`seo_checks.py`, 184 URLs crawled) | n/a (new check) | **0**, max click depth 2, 0 orphans, 0 broken links | CI step "SEO checks" |
| Duplicate URLs | `/index.html`, `/es` (no slash), raw `*.html/`, `/not-found.html` 200 | 301 or 404 | `test_one_url_per_page` |
| Lighthouse production, median of 3 (A / BP / SEO) | 100 / 100 / 100 on 12 page-device pairs | **after deploy** | `evidence/lighthouse-prod-baseline.json` |
| Lighthouse production Performance, mobile `/` | 98 (LCP 1.41 s, CLS 0.029, TBT 0) | **after deploy** | same |
| Lighthouse local (uncompressed), after, 1 run | — | A11y/BP/SEO 100 on `/`, `/es/`, `/help.html`, `/about.html`, a guide (mobile + desktop); Performance 97–100; home CLS **0** (voice list height reserved) | lead's local run |
| Core Web Vitals (field, CrUX) | not available (PSI quota 429; CrUX needs a key) | after deploy, O25 | `CORE_WEB_VITALS_REPORT.md` |

## Regression gates on the integrated branch

| Suite | Before | After |
|---|---|---|
| API tests (`pytest tests/test_api.py`) | 47 | **55 passed** |
| SEO checks (`tests/seo_checks.py`) | — | **0 issues** |
| Language test (`tests/lang_test.js`, 25 languages) | 25 | **27 passed** |
| E2E functional (`tests/e2e`, Chromium) | — | **31 / 31** (incl. 6 real speech generations, keyboard-only flow) |
| Browser suite `verify_full.mjs` | 75 | **all passed** (privacy check updated to the new wording) |
| Browser suite `verify_ui.mjs` | 36 (donate check stale) | **all passed** (donate check now verifies the live Stripe/BMC links) |
| i18n validation (`merge_sub_i18n.py`) | 25 × 80 keys | 25 × 92 keys valid |
| Generator checks (`make_content_pages.py`) | — | 9 / 9 pages, 0 duplicate paragraphs |

E2E on Firefox (31/31) and WebKit (30/31: WebKit's native `<audio>` ignores Space when focused — engine behaviour, clicking plays) were run by Agent 4 before integration; see `FUNCTIONAL_REGRESSION_RESULTS.md`.

## Remaining valid issues

- SAGE after-scores: owner rerun after deploy (O15).
- Entity facts only the owner can give: legal operator (O2), official profiles (O9), public email (O10), support languages (O23).
- Production Lighthouse "after", Rich Results Test and validator on the new pages: after deploy (D2, `DEPLOYMENT_CHECKLIST.md`).
- Toast error messages are English in every UI language (pre-existing).
- Agent interactivity stays low by design until WebMCP is stable (W1).
