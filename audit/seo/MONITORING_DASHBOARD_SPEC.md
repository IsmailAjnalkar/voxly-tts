# Search and product monitoring — dashboard specification

Constraint: the privacy policy promises **no cookies, analytics or advertising trackers**. Everything below respects that: search data comes from the search engines' own consoles, and product events are counted on the server without identifying anyone. If you later want page-view analytics, use a cookieless, self-hosted tool and update the privacy policy first.

## Data sources
| Source | Access needed | What it gives |
|---|---|---|
| Google Search Console (domain property; the verification tag is already on the site) | Owner login | Queries, pages, impressions, clicks, CTR, average position; page-indexing status; Core Web Vitals field data once traffic is sufficient |
| Bing Webmaster Tools (import from Search Console) | Owner login | Same for Bing, the main source for Copilot |
| Server logs (nginx access log) | Server | Referrers, including AI search products that send a referrer (chatgpt.com, perplexity.ai, copilot.microsoft.com, gemini.google.com). Many AI answers send no referrer, so this is a lower bound |
| App counters (to build; see below) | Server | Successful generations, downloads, errors by type, by interface language |
| GitHub uptime workflow (live) | Repository | Availability every 15 minutes, real generation check |

## Product events (server-side, no personal data)
Count per day, per interface language (from the URL prefix of the page that made the request) and per output format:
- `generation_ok`, `generation_error` (by error class: limit, language mismatch, voice unavailable, provider failure)
- `download_audio`, `download_srt`, `download_vtt` (a `GET /api/file/...` with status 200)
- `support_message` (count only)
Store as daily totals (for example one JSON line per day). No IPs, session IDs or text are stored.

## Dashboard views (weekly)
1. **Search overview:** clicks, impressions, CTR and position, Google and Bing, week over week.
2. **Pages:** top 20 pages by clicks; the 25 language homes side by side; the four new guides.
3. **Queries by cluster:** Search Console queries mapped to the clusters in `KEYWORD_MATRIX.csv` (regex rules from `audit/scripts/keyword_matrix.py`).
4. **Indexing:** indexed vs submitted for the 129 sitemap URLs; pages with issues.
5. **Conversion:** organic landing sessions are not measurable without analytics; use search clicks → `generation_ok` per day as the proxy, and downloads per generation.
6. **AI referrals:** daily visits whose referrer is an AI search product (from nginx logs).
7. **Health:** uptime check results, generation error rate, Lighthouse scores from a monthly run.

## Baseline (2026-10-29)
Lighthouse and crawl baselines are in `SEO_AEO_GEO_REPORT.md`. Search Console, Bing and traffic baselines **do not exist yet**: record them in the first week after deploy and Search Console access.
