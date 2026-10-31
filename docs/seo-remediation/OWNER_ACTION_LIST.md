# Owner action list

These are things only the site owner can do or decide. Each item says why, where the evidence is, and what we need back. The lead adds anything the other agents flag.

## Before the deploy (blocking)

| # | Action | Why / evidence | What we need from you |
|---|---|---|---|
| O1 | ~~Confirm the live donation links are yours~~ **Resolved**: both links are in `master` (7565220, f8d43ee, committed by the owner) and merged into this branch; both return 200 | Production has these links, but **git does not**: every branch, including this one, still has `donate.stripe.com/EXAMPLE-replace-me` and `buymeacoffee.com/yourname`. `release.sh` replaces `web/` entirely, so deploying would bring the placeholders back (finding X1, `SEO_AEO_GEO_AUDIT.md` §2.4). Also: the brief said the live buttons point to example links. On production they don't; the repo does | "Yes, both are mine", so the lead commits them. Or give the correct URLs |
| O2 | **Done 2026-10-31: owner confirmed QINTAR LLC runs the site** (legalName + About page). ~~Confirm QINTAR LLC is the legal operator~~ of text-2-speech.com, and the jurisdiction if you want it shown | The footer says "© 2026 QINTAR LLC"; nothing else does (E1, E2). We add `legalName` and "operated by QINTAR LLC" only after your confirmation | Yes/no, and the exact legal name |
| O3 | **Approve the About page text** (`/about.html`): every sentence about who runs the site | No invented people, dates or addresses | Approval or edits |
| O4 | **Done 2026-10-31: owner approved all new pages.** **Review the new content pages** (`/help.html`, the text-to-mp3, ai-voiceover and choose-voice guides) | Rule: no unreviewed generated content is published | Approval or edits |
| O5 | **Approve the PR and the deploy** | `DEPLOYMENT_CHECKLIST.md` | Merge + run `release.sh` (or tell the lead to) |

## Entity facts (provide only what is true; leave blank otherwise)

| # | Fact | Used in | Note |
|---|---|---|---|
| O6 | People behind the site (name and role), if you want them public | About page; `Organization.founder` or article authors | Optional. The organization as author is valid |
| O7 | Founding or launch date of the service | About; `Organization.foundingDate` | Optional |
| O8 | Public address | About; `PostalAddress` | Optional and not needed for an online tool. Never use a registered-agent address as if it were an office |
| O9 | Official social and directory profiles (only accounts you control) | `Organization.sameAs`, About page | None exist in the markup today (E3). Don't create profiles just for `sameAs`; create them only if you will maintain them |
| O10 | A public contact email, yes or no | About, Support, `contactPoint` | Today the only route is the support form (E5) |

## Policy decisions

| # | Decision | Options and evidence |
|---|---|---|
| O11 | **Decided 2026-10-31: option A, allow all (robots.txt unchanged).** **robots.txt AI-crawler policy** | Today all crawlers are allowed except on `/api/`, including training crawlers. Options: A keep; B search yes, training no; C block AI. Details in `AI_SEARCH_READINESS.md` §2.3, with each vendor's own documentation. We changed nothing |
| O12 | **Privacy-policy wording** on (a) the anonymous page-view counter (stores UTC date + path, no IP, cookie or user agent; bots and the admin are not counted) and (b) web-server access logs | The policy says "no cookies, analytics or advertising trackers", which is true. It doesn't mention the counter or server logs (X2). nginx logs are on by default: check what is logged and how long `/etc/logrotate.d/nginx` keeps it on the VPS, then approve a one-paragraph text (translated into 25 languages) |
| O13 | WebMCP | We recommend **not now** (origin trial, draft spec changed 2026-10-27). `AI_SEARCH_READINESS.md` §6. Just confirm |
| O14 | Comparison page (later) | Only with dated, sourced competitor facts (`CONTENT_PLAN_90_DAYS.md` week 10) |

## After the deploy

| # | Action | Where | Done when |
|---|---|---|---|
| O15 | **Rerun SAGE** on https://text-2-speech.com and fill the "After" column | `SAGE_FINDING_REMEDIATION.md` (last table) | Scores recorded with date. We cannot run SAGE |
| O16 | **Google Search Console**: resubmit `sitemap.xml` (expect 129 + the new English pages); URL Inspection → Request indexing for `/about.html`, `/help.html`, the 3 new guides, `/es/tutorial.html` | GSC (the verification meta tag is already on the site) | Sitemap "Success"; inspected URLs indexed or a reason shown |
| O17 | **Bing Webmaster Tools**: same sitemap; URL Inspection for the same pages; optionally IndexNow | BWT (the `msvalidate.01` tag is on the site) | Same |
| O18 | **Rich Results Test** and validator.schema.org on `/`, `/es/`, `/about.html`, `/how-it-works.html`, one guide | search.google.com/test/rich-results | Results saved to `docs/seo-remediation/evidence/` (D2) |
| O19 | Ignore the page-view spikes on audit days | Audit crawls with the old crawler UA were counted as views (X3). Our crawls on 2026-10-31 used a bot UA and were not counted | — |
| O20 | Optional: grep nginx access logs weekly for AI crawler UAs (`GPTBot`, `OAI-SearchBot`, `ClaudeBot`, `Claude-SearchBot`, `PerplexityBot`, …) and AI referrers (`chatgpt.com`, `perplexity.ai`, `copilot.microsoft.com`, `gemini.google.com`) | VPS | This is the only real evidence of AI visibility the site has. A lower bound, since many AI answers send no referrer |
| O21 | Keyword volumes: if you enable Ahrefs or Semrush API units, we can add volumes to `KEYWORD_MATRIX.csv` | — | Optional |

## Flagged by other agents (lead to merge here)

| # | Item | From | Status |
|---|---|---|---|
| | | | |

## Added by the lead after integration (2026-10-31)

| # | Action | Why |
|---|---|---|
| O22 | Decide how long support messages are kept and whether to delete them automatically | The privacy page says messages are kept "only as long as needed", but `support/inbox.jsonl` is never pruned automatically |
| O23 | Confirm the languages you answer support messages in | Decides `contactPoint.availableLanguage` (left out until then) |
| O24 | **Approved 2026-10-31.** Approve the new privacy wording (page counter + 14-day server logs) in English; the 24 translations follow it | X2; the wording is factual (checked in code and `/etc/logrotate.d/nginx`) but it is your policy |
| O25 | After deploy: real-user Core Web Vitals | PageSpeed API quota was exhausted (429) and CrUX needs an API key; run `CORE_WEB_VITALS_REPORT.md` command with `&key=` |
