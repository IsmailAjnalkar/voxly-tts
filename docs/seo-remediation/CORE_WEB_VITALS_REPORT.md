# Core Web Vitals report: text-2-speech.com

Baseline taken on **2026-10-31** (14:53 to 15:00 UTC) against **production** (`https://text-2-speech.com`), before any of the SEO-remediation changes were deployed. The **After** columns are left empty. The lead fills them in after integration and deploy, using the same command (see [Rerun](#rerun)).

## Field data (CrUX): not available

| Source | Result |
|---|---|
| PageSpeed Insights API v5, no key (`/runPagespeed?url=https://text-2-speech.com/&strategy=mobile\|desktop`) | **HTTP 429.** The daily quota for anonymous callers was used up (the shared keyless project). Tried twice. Raw responses: `evidence/psi-home-mobile.json`, `evidence/psi-home-desktop.json` |
| CrUX API (`chromeuxreport.googleapis.com/v1/records:queryRecord`, origin) | **HTTP 403.** The API needs an API key ("unregistered callers"). |

**Status:** we don't know whether CrUX has field data for this origin. We could not query it, so we make no claim either way. The site is new and low-traffic, so CrUX may well return "not enough data" once someone queries it with a key. That is a guess, not a measurement. To check, with a free Google Cloud API key:

```bash
curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://text-2-speech.com/&strategy=mobile&category=performance&key=$PSI_KEY" \
  | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('loadingExperience'), d.get('originLoadingExperience'))"
# or: curl -X POST "https://chromeuxreport.googleapis.com/v1/records:queryRecord?key=$PSI_KEY" -d '{"origin":"https://text-2-speech.com"}'
```

If `loadingExperience` has no `metrics`, CrUX does not have enough traffic for this origin. Until field data exists, the lab numbers below are the only CWV evidence. Lab data has no real INP, so **TBT is the INP proxy**.

## Lab data: Lighthouse (median of 3 runs)

Columns: P = Performance, A11y = Accessibility, BP = Best Practices, SEO (category scores 0 to 100). LCP, TBT and SI (Speed Index) are in milliseconds. CLS has no unit.

### Mobile (Moto G Power emulation, simulated 4G throttling: RTT 150 ms, ~1.6 Mbps, 4x CPU)

| Page | P | A11y | BP | SEO | LCP | CLS | TBT | SI | After P / LCP / CLS / TBT / SI |
|---|---|---|---|---|---|---|---|---|---|
| `/` | 98 | 100 | 100 | 100 | 1405 | 0.029 | 0 | 3648 | |
| `/es/` | 99 | 100 | 100 | 100 | 1432 | 0.029 | 0 | 2599 | |
| `/tutorial.html` | 100 | 100 | 100 | 100 | 952 | 0 | 0 | 952 | |
| `/how-it-works.html` | 100 | 100 | 100 | 100 | 992 | 0 | 13 | 956 | |
| `/guides/subtitles.html` | 100 | 100 | 100 | 100 | 984 | 0 | 17 | 949 | |
| `/support.html` | 100 | 100 | 100 | 100 | 997 | 0 | 0 | 997 | |

### Desktop (Lighthouse desktop preset)

| Page | P | A11y | BP | SEO | LCP | CLS | TBT | SI | After P / LCP / CLS / TBT / SI |
|---|---|---|---|---|---|---|---|---|---|
| `/` | 100 | 100 | 100 | 100 | 406 | 0.028 | 0 | 454 | |
| `/es/` | 100 | 100 | 100 | 100 | 403 | 0.028 | 0 | 395 | |
| `/tutorial.html` | 100 | 100 | 100 | 100 | 294 | 0 | 0 | 294 | |
| `/how-it-works.html` | 100 | 100 | 100 | 100 | 289 | 0 | 0 | 281 | |
| `/guides/subtitles.html` | 100 | 100 | 100 | 100 | 319 | 0 | 0 | 314 | |
| `/support.html` | 100 | 100 | 100 | 100 | 275 | 0 | 0 | 305 | |

Supporting medians (in `evidence/lighthouse-prod-baseline.json`):

- **FCP:** mobile home 1389 ms, sub-pages about 950 to 1000 ms.
- **Server response time:** 25 to 100 ms.
- **Transfer weight:** home about 54 KB, sub-pages 9 to 10 KB.

Every page/device pair passes the "good" thresholds: LCP ≤ 2.5 s, CLS ≤ 0.1, TBT well under 200 ms.

### What the baseline shows (what to watch after integration)

- **The home page is the only page below 100 on mobile.** Its weak metric is **Speed Index** (median 3.6 s; the audit scores 0.82 to 0.84). The tool UI renders after `/api/voices` returns: the voice list, then the panels below it. The LCP element is the hero sub-heading (`div.hero > p[data-i18n=hero_sub]`). In Lighthouse's breakdown, almost all of LCP is "element render delay", not server time (TTFB about 80 ms).
- **Home CLS 0.029 (mobile) / 0.028 (desktop)** comes from a single shift: `#pitchrow` moves down when the voice list fills in. That is still "good". However, any added content above the tool can make this shift bigger. A fixed `min-height` on `#voicelist` would remove it.
- Sub-pages pull in one small render-blocking script (`/subi18n.js`, about 3 KB). Lighthouse flags it as `render-blocking-insight` (score 0.5), but it costs nothing measurable at this weight.
- Lighthouse rates A11y, Best Practices and SEO at 100 on all 12 page/device pairs. Treat any drop after integration as a regression.

## Methodology

- **Tool:** Lighthouse **12.8.2** (Node API), headless Chrome **156**, default simulated throttling ("lantern"). Mobile uses Lighthouse's default mobile config. Desktop uses `lighthouse/core/config/desktop-config.js`. Runs went from this Windows 11 workstation over its normal internet connection to the production server.
- **Runs:** 3 per page per device, run one after another (36 page loads in total; no load on the server). Each metric is reported as the **median of the 3 runs**, taken per metric. The run whose Performance score equals the median is kept as the representative full report.
- **Clean profile per page:** a fresh Chrome profile is launched for each page. Lighthouse clears caches between runs but **not localStorage**. In a first attempt with one shared profile, the `/es/` visit saved `voxly-ui=es`, and the later English pages then rendered in Spanish through client-side translation: the tutorial's LCP element came out as Spanish text. That first attempt was thrown away. Note for the lead: visitors who once picked Spanish see English URLs translated on the client. Googlebot keeps no localStorage, so crawling is not affected.
- **No INP:** Lighthouse navigation runs cannot measure INP. TBT is used as the lab proxy. Real INP needs field data (CrUX/RUM).
- **Variance:** between runs, mobile Speed Index on the home page ranged from 2.3 to 3.9 s and LCP moved by ±150 ms. Treat differences smaller than that as noise, and compare medians only.

## Rerun

Lighthouse is in the scratchpad `node_modules` (or run `npm i lighthouse chrome-launcher` anywhere). Copy the script next to it, then run it from Git Bash. `MSYS_NO_PATHCONV=1` stops Git Bash from rewriting `/es/` into a Windows path.

```bash
cp audit/scripts/lighthouse_run.mjs <dir-with-lighthouse-node_modules>/ && cd <that dir>
MSYS_NO_PATHCONV=1 RUNS=3 PATHS=/,/es/,/tutorial.html,/how-it-works.html,/guides/subtitles.html,/support.html \
  node lighthouse_run.mjs https://text-2-speech.com C:/Users/ajnal/text2speech/docs/seo-remediation/evidence lighthouse-prod-after
```

The script prints each run and then a `MEDIANS` block that maps one-to-one onto the tables above. Use `BASE=http://localhost:8804` to measure a local build. Local numbers are **not** comparable with production numbers: there is no nginx gzip and no network latency.

## Evidence files (`docs/seo-remediation/evidence/`)

- `lighthouse-prod-baseline.json`: all 36 runs and the medians, with each run's failing audits and LCP element.
- `lighthouse-prod-baseline-lhr/<form>_<page>.json`: the full Lighthouse report of each median run, with screenshots stripped. You can open one in the Lighthouse viewer (googlechrome.github.io/lighthouse/viewer).
- `psi-home-mobile.json`, `psi-home-desktop.json`: the PSI 429 responses.
