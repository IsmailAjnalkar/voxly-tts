# 90-day content plan (updated for the SAGE remediation)

Supersedes [`audit/seo/CONTENT_ROADMAP_90D.md`](../../audit/seo/CONTENT_ROADMAP_90D.md) (2026-10-29). Day 1 = the day this PR is deployed.

**Rules for every item** (unchanged and binding):
1. It targets a cluster whose product fit is Supported or Partial in `KEYWORD_STRATEGY.md`.
2. Every fact is tested on the live product or read from code, and the page carries a "Last updated" date.
3. **A person reviews it before publishing** (owner or a named reviewer). For translations, a native speaker reviews; machine-only translation is not enough.
4. No doorway pages, invented numbers, reviews, quotes or citations. No features we don't have.
5. One intent per page (cannibalization table in `KEYWORD_STRATEGY.md` §2).

What changed against the old roadmap:
- The capability guides from old weeks 4–5 ("video narration workflow", "choosing a voice") ship in **this PR** as `/guides/ai-voiceover.html` and `/guides/choose-voice.html`, so they leave the plan.
- `/about.html`, `/help.html` and `/guides/text-to-mp3.html` were added (SAGE E1, A1q, A2q).
- The FAQ additions (iPhone/Android, offline, API) are answered on `/help.html`.
- Planned slugs; the lead records the final ones.

## Shipped in this PR (Day 0): review before deploy

| Page | Target cluster / intent | Facts source | Review step |
|---|---|---|---|
| `/about.html` | Brand/entity (E1) | Owner-confirmed facts only: operator (QINTAR LLC?), purpose, contact route. Product facts from how-it-works | **Owner approves every sentence about the operator** |
| `/help.html` | Devices & apps, "unlimited", reader, offline, API, commercial use (Q&A) | `server.py` constants (`MAX_CHARS`), Terms, privacy policy, a real test on a phone browser (dated) | Owner reads; each answer is checked against code and Terms |
| `/guides/text-to-mp3.html` | Formats: how to convert text to MP3 (how-to intent) | A real generation: measured file size and duration, MP3 encoding (48 kbps, 24 kHz mono, from `server.py`/llms.txt) | Reviewer reproduces the steps on production |
| `/guides/ai-voiceover.html` | Narration & voiceover (workflow) | A real script → MP3 + SRT → import into a free editor, with the date and editor version | Reviewer repeats the workflow |
| `/guides/choose-voice.html` | Languages & accents (how to choose) | Live catalog (`/api/voices`: 322 voices, 142 locales, 75 languages on 2026-10-31); Preview behaviour in the UI | Reviewer checks the counts on the day of publishing |
| `llms.txt` | Non-ranking aid | Links to the pages above; facts unchanged | Diff review |

## Days 1–14: verify, measure, no new pages

| Task | Output | Done when |
|---|---|---|
| Post-deploy checks | `DEPLOYMENT_CHECKLIST.md` §3 completed | All gates green, results in `evidence/` |
| Search Console + Bing Webmaster Tools | Sitemap resubmitted; URL Inspection of `/about.html`, `/help.html`, the 3 new guides, `/es/tutorial.html` (L1 fix) | Pages "URL is on Google" or a known reason |
| SAGE rerun | After scores in `SAGE_FINDING_REMEDIATION.md` | Owner records them |
| Search baseline | First weekly snapshot (`audit/seo/MONITORING_DASHBOARD_SPEC.md` views 1–4) | Saved |

## Days 15–45: fill gaps found by real data

| Week | Item | Target cluster | Facts source | Review |
|---|---|---|---|---|
| 3 | **Pauses and pacing guide** (`[break:…]` markers, punctuation, speed/pitch) | Narration & voiceover | Generated examples; measured pause timing in the output (ffprobe) | Reviewer reproduces |
| 4 | Refresh titles and descriptions for pages with impressions but low CTR | per GSC | Search Console | Owner approves changes |
| 5 | **Troubleshooting** section in `/help.html` (no audio, wrong language/voice mismatch, long text, voice temporarily unavailable) | Questions & how-to | Error messages in `server.py`/`index.html`; support inbox (count only, no personal data) | Owner |
| 6 | Translate `/help.html` into the top 3 UI languages **by actual traffic** (`/admin` page views per language prefix) | Devices & apps (localised) | English page | Native reviewer per language |

## Days 46–75: languages and accessibility, only where justified

| Week | Item | Gate before starting |
|---|---|---|
| 7–8 | Language landing pages for at most 2–3 languages with real depth (e.g. Spanish: 22 locales; Arabic; Hindi/Indian English), each with distinct content: regional voices, audio samples, tips | The catalog shows the depth **and** a native reviewer is available. Otherwise skip (doorway risk) |
| 9 | Text to speech for learning and accessibility (listening while reading) | Cite reputable sources; no medical or therapeutic claims |
| 10 | Optional honest comparison page | Each competitor fact quoted from their own pricing/limits page with the access date; our features tested the same day; owner approves |

## Days 76–90: review and iterate

- Map Search Console queries to clusters; retire or merge pages with no impressions after 60 days, rather than adding more.
- Re-run the route map, `tests/seo_checks.py`, the E2E suite and Lighthouse; write a dated changelog of content changes.
- Update llms.txt, how-it-works and help for any changed limits (single source in `tools/make_content_pages.py`).
- Decide WebMCP again (`AI_SEARCH_READINESS.md` §6 criteria).

## Not planned (and why)

Character or celebrity voice pages, "unlimited" claims, PDF or web-page reader pages, app or extension pages, voice cloning: these are features we don't have. Per-keyword or per-language pages without distinct content are doorway pages. The full list is in `KEYWORD_STRATEGY.md` §3.
