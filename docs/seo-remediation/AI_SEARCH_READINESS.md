# AI search (GEO/AEO) readiness: text-2-speech.com

Date: 2026-10-31. Measured on production. **No policy change is made in this PR**: the robots/AI-crawler options in §2 are a decision for the owner.
Nothing here is a claim about AI citations or traffic. We have no data on either. Server logs (owner access) are the only source this site has for AI crawler visits and AI referrals.

## 1. Server-rendered content (what a crawler that runs no JavaScript sees)

Most AI crawlers fetch HTML without running JavaScript. Google renders JS but recommends server-side or pre-rendering where possible ([JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)).

| Check (production, no JS) | Result | Evidence |
|---|---|---|
| Primary content in HTML, all 129 sitemap URLs | **Yes**: ≥ 107 words in `<main>` on every URL; one H1 each | `evidence/route_map_prod.csv` (`rendering`, `main_words`) |
| Home generator, FAQ (6 Q&A), how-it-works step, in en/es/ja/ar | **Yes**, translated server-side; `ar` has `dir="rtl"` | `evidence/ssr_check_prod.log` (11/11 OK) |
| Voices table (live catalog) | **Yes**: "322 voices in 75 languages", 75 language rows | same |
| Guides: real SRT cues, measured MP3/WAV sizes | **Yes** | same |
| Language-version links | **No**: in raw HTML, language pages link to English URLs; JS rewrites them (`web/subi18n.js:48`). Finding **L1**, fixed in this PR by Agent 3 | route map: 96 language sub-pages with 0 inbound links |
| Rendered-only content | The voice list (per-voice Preview buttons) and the results list are JS-rendered. That is UI, not content; the voice facts are on `/voices.html` as HTML | — |

## 2. robots.txt and AI crawlers

### 2.1 Policy today (production = repo)

```
User-agent: *
Allow: /
Disallow: /api/
Sitemap: https://text-2-speech.com/sitemap.xml
```

There are no user-agent-specific groups, and the nginx config has no user-agent blocking (`deploy/nginx-voxy-tls.conf`). So **every crawler below is allowed everywhere except `/api/`**, and that includes training crawlers. There are no `noai`-style meta tags and no `nocache`/`noarchive`. Under RFC 9309 a crawler that matches no specific group uses the `*` group ([RFC 9309](https://www.rfc-editor.org/rfc/rfc9309)).

### 2.2 Crawler reference (from each operator's own documentation, fetched 2026-10-31)

| Token / UA | Operator | What it controls | Respects robots.txt (per operator) | Status on this site | Source |
|---|---|---|---|---|---|
| `GPTBot` | OpenAI | **Training** of foundation models | Yes | Allowed | [OpenAI bots](https://developers.openai.com/api/docs/bots) |
| `OAI-SearchBot` | OpenAI | **Search**: appearing in ChatGPT search answers | Yes (changes take ~24 h) | Allowed | same |
| `ChatGPT-User` | OpenAI | **User-triggered** fetches in ChatGPT and GPT Actions; not used for search eligibility | "robots.txt rules may not apply" | Allowed | same |
| `ClaudeBot` | Anthropic | **Training** ("could potentially contribute to their training") | Yes; also supports `Crawl-delay` | Allowed | [Anthropic crawler FAQ](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler) |
| `Claude-SearchBot` | Anthropic | **Search** result quality | Covered by the general "Anthropic's Bots respect robots.txt" statement | Allowed | same |
| `Claude-User` | Anthropic | **User-triggered** fetches when a person asks Claude | Covered by the same general statement | Allowed | same |
| `PerplexityBot` | Perplexity | **Search**: surfacing and linking sites; "not used to crawl content for AI foundation models" | Yes | Allowed | [Perplexity bots](https://docs.perplexity.ai/guides/bots) |
| `Perplexity-User` | Perplexity | **User-triggered** fetches; not training | "Generally ignores robots.txt" | Allowed | same |
| `Google-Extended` | Google | Robots **token only**, not a separate crawler: Gemini **training and grounding**. "Does not impact a site's inclusion in Google Search" and is not a ranking signal | n/a (token) | Allowed (not listed) | [Google common crawlers](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers) |
| `Googlebot` | Google | **Search, including AI Overviews and AI Mode.** Limit these with `nosnippet`, `data-nosnippet`, `max-snippet` or `noindex`, not with Google-Extended | Yes | Allowed | [AI features and your website](https://developers.google.com/search/docs/appearance/ai-features) |
| `Applebot-Extended` | Apple | Token only ("does not crawl webpages"): use of Applebot data for **training** Apple's models. Blocking it keeps Siri/Spotlight/Safari search | n/a (token) | Allowed | [Apple: About Applebot](https://support.apple.com/en-us/119829) |
| `CCBot` | Common Crawl | Open web archive, widely reused, including for model training | Blocking instructions given; full UA `CCBot/2.0` | Allowed | [Common Crawl CCBot](https://commoncrawl.org/ccbot) |
| `meta-externalagent` | Meta | **Training** of foundation models / product indexing | Yes | Allowed | [Meta web crawlers](https://developers.facebook.com/docs/sharing/webmasters/web-crawlers/) |
| `meta-webindexer` | Meta | **Search** quality for Meta AI | Yes | Allowed | same |
| `meta-externalfetcher` | Meta | **User-triggered** fetches | "May bypass robots.txt" | Allowed | same |
| `facebookexternalhit` | Meta | Link previews (title, description, image) | May bypass for security checks | Allowed | same |
| `Bytespider` | ByteDance | **Not verified**: we found no official documentation we could open. Secondary sources disagree on its purpose and on whether it honours robots.txt | Unknown | Allowed | (no primary source) |
| `Bingbot` | Microsoft | Bing search and Copilot answers. `<meta name="robots" content="nocache">` keeps only URL, title and snippet in Bing Chat/Copilot; `noarchive` excludes the content from it; both keep normal Bing results | Yes | Allowed | [Bing blog, 2023-09-22](https://blogs.bing.com/webmaster/september-2023/Announcing-new-options-for-webmasters-to-control-usage-of-their-content-in-Bing-Chat) |

Notes:
- **Search crawlers ≠ training crawlers.** Blocking a search crawler (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, `Googlebot`, `Bingbot`) removes the site from that product's answers. Blocking a training token (`GPTBot`, `ClaudeBot`, `Google-Extended`, `Applebot-Extended`, `meta-externalagent`, `CCBot`) does not affect search per those vendors' docs.
- **User-triggered agents** (`ChatGPT-User`, `Perplexity-User`, `meta-externalfetcher`) may not apply robots.txt at all. Blocking them would need server-side measures, which would also break a user asking an assistant "read this page".
- Training opt-outs are not retroactive.

### 2.3 Owner options (no change made)

| Option | robots.txt change | Effect | Trade-off |
|---|---|---|---|
| **A. Keep as is** (current) | none | Eligible for AI search and AI training everywhere | Content may be used for training. For a free tool whose goal is discovery, this maximises reach |
| **B. Search yes, training no** | Add groups `User-agent: GPTBot` / `ClaudeBot` / `Google-Extended` / `Applebot-Extended` / `meta-externalagent` / `CCBot` with `Disallow: /` | Stays in ChatGPT search, Claude search, Perplexity, Google AI Overviews/AI Mode, Bing Copilot; opts out of the documented training uses | Google-Extended also covers Gemini **grounding**, so Gemini app answers may stop using the site. Bytespider remains undocumented |
| **C. Block all AI** | Option B + `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, `meta-webindexer` | Out of most AI answer engines | Loses AI-search discovery. Google AI Overviews cannot be blocked without affecting Search snippets (`nosnippet`) |

Recommendation for the owner to consider: **A or B**. Both keep the search-facing crawlers. Choosing is a business decision (see `OWNER_ACTION_LIST.md`). If B: keep the `*` group unchanged and add the named groups. A crawler obeys only the most specific group that matches it (RFC 9309 §2.2.1), so rules in `*` do not carry over into a named group. Each named group must be complete on its own.

## 3. llms.txt

- Status: `/llms.txt` returns 200 `text/plain`, identical to the repo. It holds a summary, key facts (price, voices, limits, formats, privacy) and links to how-it-works, voices, both guides and the main pages.
- It is a **community proposal** ([llmstxt.org](https://llmstxt.org/)), not a standard. Google says no special AI text files are needed for AI Overviews/AI Mode ([AI features](https://developers.google.com/search/docs/appearance/ai-features)). Treat it as a **non-ranking convenience** for tools that read it, not a ranking lever.
- To do in this PR (Agent 2): add About, Help and the new guides, and keep the facts in sync with the code constants (`MAX_CHARS = 5000`, pause limits, retention). The facts list on how-it-works and in llms.txt should come from one source (`tools/make_content_pages.py`).

## 4. Entity consistency (production, 2026-10-31)

| Surface | Name | Description / claim | Operator | Notes |
|---|---|---|---|---|
| `<title>` (home) | Text 2 Speech | "Free Text to Speech Online \| Natural AI Voices" | — | |
| `og:site_name`, `og:title` | Text 2 Speech | same as the title | — | |
| `Organization` `#org` | Text 2 Speech | "runs text-2-speech.com, a free online text-to-speech tool" | **not stated** | no `legalName`, `sameAs`, `contactPoint` (E2) |
| `WebApplication`, `WebSite` | Text 2 Speech | "300+ AI voices in 75 languages … Free, no sign-up" | publisher → `#org` | |
| Guides `TechArticle` | author/publisher: Organization "Text 2 Speech" | — | — | |
| Footer (all pages) | Text 2 Speech | "Free text to speech with 300+ natural voices in 75 languages. No sign-up." | **"© 2026 QINTAR LLC"** | the only place QINTAR LLC appears |
| llms.txt | Text 2 Speech (text-2-speech.com) | "300+ neural voices in 75 languages" | not stated | |
| Live catalog (`/voices.html`) | — | **322 voices in 75 languages** | — | "300+" and "75" are consistent with the live data |
| Terms / Privacy | — | names Microsoft as the speech processor | not stated in the body | contact = Support page |
| Legacy brand | "voxly" appears only in localStorage keys and server paths, not in visible text | | | OK |

**Inconsistency:** the operator. QINTAR LLC appears only in the copyright line; the schema, llms.txt, Terms and Privacy never state who operates the service. Fix (E1/E2), **after the owner confirms**: one sentence, "Text 2 Speech is operated by QINTAR LLC", on About, Terms and llms.txt, plus `legalName` on the `Organization`. Until the owner confirms it, add nothing.

## 5. What we will not do (guardrails)

- No invented ratings, reviews, `sameAs` profiles, people, addresses or founding dates.
- No `speakable`, `SearchAction` or `HowTo` markup: there is no backing feature or eligible rich result.
- No AI-only text served to bots (cloaking). Bots get the same HTML as people.

## 6. WebMCP / agent interactivity evaluation

**Decision: do not ship WebMCP in this release (N/A for SAGE "Agent Interactivity 18").** Re-evaluate when it leaves origin trial.

### 6.1 Current status (sources, dates)

| Fact | Source (date) |
|---|---|
| Spec: "WebMCP", **Draft Community Group Report, 27 October 2026**, W3C Web Machine Learning CG; "not a W3C Standard nor is it on the W3C Standards Track". Editors from Microsoft and Google | [webmachinelearning.github.io/webmcp](https://webmachinelearning.github.io/webmcp/) (fetched 2026-10-31) |
| API entry point in the current draft: **`document.modelContext`** with `registerTool()`, `getTools()`, `executeTool()`; events `toolchange`/`toolactivated`/`toolcancel`; gated by the `tools` Permissions Policy (default `'self'`) | same |
| Earlier drafts and the Feb 2026 preview used `navigator.modelContext` with `provideContext()`/`clearContext()`; secondary sources report these were removed or deprecated during the origin trial. **The API surface changed within 2026** | [Chrome early preview blog (2026-02-10)](https://developer.chrome.com/blog/webmcp-epp); [dev.to report](https://dev.to/jangwook_kim_e31e7291ad98/webmcps-origin-trial-providecontext-is-already-gone-54j8) (secondary) |
| Chrome: "a proposed web standard", **origin trial starting Chrome 149**, or local flag `chrome://flags/#enable-webmcp-testing`; Imperative (JS) and Declarative (annotated HTML forms) APIs; "primarily designed for local browser workflows with a human in the loop"; sensitive actions can request a confirmation dialog. Testing is via two Chrome extensions; the page does **not** say that Gemini in Chrome or any shipping agent consumes WebMCP tools | [developer.chrome.com/docs/ai/webmcp](https://developer.chrome.com/docs/ai/webmcp) (published 2026-05-18, updated 2026-10-07) |
| Security section of the spec lists prompt injection, misrepresentation of intent, privacy leakage through over-parameterization, and mitigations still being worked out ("shared attack evaluation datasets", "untrusted annotation") | spec §6 |

### 6.2 Assessment against the criteria

| Criterion | Assessment |
|---|---|
| **Stable enough?** | **No.** Draft CG report revised four days ago; origin trial (needs a per-origin token, expires); the entry point moved from `navigator` to `document` and methods were removed this year. Shipping now means maintaining code against a moving API |
| **Real user benefit?** | **Low today.** The one useful tool would be "generate speech (text, voice, rate, pitch) → audio + subtitle URLs". The page already exposes the same action as a labelled HTML form that DOM-driving agents can use (W2). No shipping, documented agent consumes WebMCP yet, so the benefit reaches only people running trial builds with test extensions |
| **Consent?** | Technically possible: a tool runs in the user's tab, and Chrome describes human-in-the-loop and an optional confirmation dialog. But consent UX is browser/agent-defined and not settled in the spec |
| **Validation, rate limits?** | **Would be identical**: a tool would call the same `POST /api/tts`, so server-side validation (`MAX_CHARS = 5000`, pydantic) and nginx limits (20 r/min, burst 10) apply unchanged. This is the one criterion clearly met |
| **Privacy identical to the UI?** | Partly. The UI shows that text goes to Microsoft's speech service (privacy policy). A tool description would have to say the same, and an agent may pass text the user never saw, which is the "over-parameterization" risk the spec itself lists |

**Result:** stability fails, and user benefit is speculative. Validation and rate limits would be equal; consent and privacy depend on unsettled agent behaviour. → **N/A for now.** No code, no polyfill, no origin-trial token.

**Re-evaluate when** Chrome ships WebMCP outside origin trial (a chromestatus "Shipped" milestone) **and** at least one mainstream agent documents consuming site tools. At that point, the minimum is the **Declarative API on the existing form**: annotate the generator form so it becomes one tool. It reuses the same endpoint and limits, adds no new server surface, and keeps the visible UI as the source of truth.

The SAGE score for Agent Interactivity is expected to stay low after this PR. That is a deliberate, documented decision, not a defect.
