# Schema validation report (Agent 3)

Date: 2026-10-31. Branch `seo/sage-remediation`, rendered locally (`uvicorn server:app --port 8803`).
Rule: every property must be backed by visible content or a verified fact. Verified facts: brand "Text 2 Speech"; footer "© 2026 QINTAR LLC" (owner-provided); contact = the form at `/support.html`; free (price 0). Not verified, so **not** marked up: social profiles (`sameAs`), address, phone, email, founding date, ratings/reviews, site search (`SearchAction`), named authors, `speakable`.

## Before / after by page type

| Page type (URLs) | Before | After |
|---|---|---|
| Language homes (25) | `Organization` {@id `#org`, name, url, logo 512×512, description} · `WebApplication` {@id `#app`, name, url, publisher→#org, isAccessibleForFree, browserRequirements, applicationCategory, operatingSystem, offers {price "0", USD}, description (English on every language), featureList, inLanguage} · `WebSite` {@id `#website`, name, url, publisher→#org, inLanguage} · `FAQPage` {mainEntity from `i18n-home/<lang>.json`, inLanguage} | Same, plus: `Organization.contactPoint` {ContactPoint, contactType "customer support", url `/support.html`} · `WebSite.copyrightHolder` {Organization "QINTAR LLC"} + `copyrightYear` 2026 (the footer line) · `WebApplication.description` = the page's visible hero tagline in that language |
| Translated sub-pages: tutorial, support, privacy, terms (100) | `BreadcrumbList` | `BreadcrumbList` + `WebPage` (support: `ContactPage`) {@id = url = canonical, name = `<title>`, description = meta description, inLanguage, isPartOf→#website, publisher→#org} |
| Support page FAQ | Visible copy of the home FAQ, no markup | Removed: a card of question links to `/<lang>/#faqlist`. No FAQPage there (the answers are not on the page) |
| donate, auth (noindex) | none | none |
| voices | `BreadcrumbList` | unchanged |
| how-it-works, guides (A2 generator) | `BreadcrumbList` + `TechArticle` {headline, description, url, inLanguage, datePublished, dateModified, author/publisher Organization (no @id), image, mainEntityOfPage} | Generator now (A2) adds `@id #org` to author/publisher; new `about.html` has `AboutPage`, `help.html` and new guides `TechArticle`. dateModified is shown on the page as `<time datetime>` (checked) |

## Checks (local, every page, every language)

`tests/seo_checks.py` (CI) and `tests/test_api.py` assert:

* every `<script type="application/ld+json">` parses, `@context` is `https://schema.org`;
* required properties per Google's docs: Organization (name, url; logo on the site; contactPoint has contactType + url), WebSite (name, url), WebApplication (name, offers.price, offers.priceCurrency; description visible on the page), FAQPage (Question.name + acceptedAnswer.text), BreadcrumbList (positions 1..n, n ≥ 2, absolute item URLs, last item = canonical), Article/TechArticle (headline ≤ 110, image, datePublished, dateModified ≥ datePublished, ISO dates, author.name; dateModified shown on the page), WebPage/ContactPage/AboutPage (url = canonical, name = title);
* **FAQPage = visible FAQ, verbatim**, on all 25 homes (`test_home_schema_backed_by_page` compares every question and answer with the text inside `#faqlist`; seo_checks compares with all visible text);
* the featureList claims are on the page (300+ voices, 75 languages, 5,000 characters, MP3/WAV, SRT and VTT, word-level timing, speed and pitch, `[break:]` markers, Import File, no sign-up);
* forbidden everywhere: `aggregateRating`, `review`, `speakable`, `sameAs`, `SearchAction` (and `availableLanguage` on the home graph, see owner questions).

Result: 0 issues on 129 sitemap URLs (134 with the A2 pages registered).

## validator.schema.org

POSTed the locally rendered HTML (public pages only) to `https://validator.schema.org/validate`:

| Page | Objects | Errors | Warnings | Types detected |
|---|---:|---:|---:|---|
| `/` | 3 | 0 | 0 | Organization, ContactPoint, ImageObject, WebApplication, Offer, WebSite, FAQPage, Question, Answer |
| `/es/`, `/zh-CN/`, `/ar/` | 3 each | 0 | 0 | same |
| `/tutorial.html`, `/de/support.html`, `/privacy.html` | 1 | 0 | 0 | BreadcrumbList, ListItem (run before the WebPage/ContactPage nodes were added) |
| `/how-it-works.html`, `/guides/subtitles.html`, `/guides/mp3-vs-wav.html` | 2 | 0 | 0 | BreadcrumbList, TechArticle, Organization, ImageObject |

After 14 requests the validator answered with Google's rate-limit page (302/405), so the `WebPage`/`ContactPage` nodes and the new A2 pages (about, help, 3 guides) were validated locally only. **Post-deploy gate (D2, lead/owner):** Rich Results Test and validator.schema.org on `/`, `/es/`, `/support.html`, `/how-it-works.html`, `/about.html`, `/help.html`, one guide; save links/screenshots in `evidence/`.

## Rich-result eligibility (what to expect)

* **FAQPage**: since August 2023 Google shows FAQ rich results only for well-known, authoritative government and health sites. This site will not get them. The markup stays because it is accurate, matches the visible FAQ and other consumers read it; it is not a ranking factor.
* **SoftwareApplication / WebApplication**: Google's software-app rich result requires `aggregateRating` or `review`. We have neither and do not invent them, so no rich result; the node still describes the app (price 0, category, OS).
* **BreadcrumbList**: eligible (all nested pages).
* **Article/TechArticle**: no required properties; eligible for article enhancements.
* **Organization**: logo, url, contactPoint feed the knowledge panel; `legalName`/`sameAs` would help once verified.
* **WebPage/ContactPage/AboutPage**: no rich result; they connect each page to `#website` and `#org` for entity understanding.

## Owner questions

1. Is "Text 2 Speech" operated by QINTAR LLC? If yes: add `"legalName": "QINTAR LLC"` to the Organization (or `parentOrganization` if Text 2 Speech is a separate entity of the LLC). Until then only the footer's copyright statement is marked up (`WebSite.copyrightHolder`).
2. In which languages are support messages answered? If the answer is "any of the 25 UI languages", add `availableLanguage` to the ContactPoint; if English only, `"availableLanguage": "English"`.
3. Should a support email be published (E5)? If yes, add `email` to the ContactPoint and the About/Support pages.
4. Official profiles (E3) → `sameAs` once they exist and link back.
