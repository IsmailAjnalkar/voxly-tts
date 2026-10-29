# Executive Audit Report — text-2-speech.com

| | |
|---|---|
| **APPLICATION** | text-2-speech.com ("Text 2 Speech", repo `IsmailAjnalkar/voxly-tts`) |
| **AUDIT DATE** | 2026-10-28 |
| **ENVIRONMENT** | Production (https://text-2-speech.com, nginx 1.28.3 + uvicorn, build `7f86514`, verified identical to repo) for functional, UI, API and security checks; Local (Windows 11, Python 3.12.10, same code, real provider) for abuse, stress and long-input tests. No staging exists. |
| **OVERALL SCORE** | **64 / 100** readiness (untested = 0) · 68 / 100 on tested checks only |
| **TEST COVERAGE** | **94.1 %** — 176 of 187 applicable test cases executed (10 NOT TESTED, 1 BLOCKED) |
| **CONFIRMED WORKING FEATURES** | 25 of 50 |
| **CONFIRMED FAILED FEATURES** | 7 |
| **PARTIALLY WORKING FEATURES** | 11 |
| **NOT IMPLEMENTED / N/A** | 6 / 1 |
| **BLOCKED / UNTESTED** | 0 features; 11 test cases |
| **TOTAL VERIFIED DEFECTS** | **29** |
| **P0** | 0 |
| **P1** | 3 |
| **P2** | 9 |
| **P3** | 17 |
| **SECURITY STATUS** | AT RISK. No data exposure found; unbounded anonymous usage and request amplification (P1). |
| **PERFORMANCE STATUS** | Front-end excellent (LCP 0.57 s, CLS 0.02). Short generation fast (median 0.91 s). Back-end stalls under heavy requests; long text times out. |
| **UI/UX STATUS** | Good desktop and home-page mobile layout. Keyboard voice selection broken (WCAG A); light-theme contrast failures; sub-pages overflow at 320 px and carry the old brand. |
| **AUDIO QUALITY STATUS** | GOOD. 23/23 files valid, no clipping, WER 0 on en/es/fr/de/he/ru (STT proxy, no human listening). Subtitles are estimated, not word-timed as advertised. |
| **PRODUCTION DECISION** | **NO-GO** for a production-grade release or promotion, until P1 BUG-001 to 003 and P2 BUG-004 are fixed. Then **CONDITIONAL GO**. |

## Decision rationale
- No P0. The essential workflow works end to end in production: pick a voice, generate short or medium text, play, download MP3/WAV/SRT/VTT, and delete. That was verified in a real browser, decoded with ffprobe and checked with STT.
- The hard rule (P0, or a P1 that blocks an essential workflow) is therefore **not** triggered. The NO-GO is a judgment call based on three things:
  1. **Two open P1 security exposures.** The `/api/tts` endpoint is anonymous and unbounded (no size limit, no rate limit), and 663 bytes of break markers produce 30 minutes of audio. Together with BUG-004 (blocking ffmpeg on a single worker, health latency up to 5.9 s), a few anonymous requests can degrade the service for everyone.
  2. **An advertised capability fails.** "No fixed limit" and the audiobook use case: 20k-character input returns 502 after 45 s.
  3. **The readiness score of 64 sits in the "significant gaps" band.**
- These are small, local fixes (about 1–2 days, see [FIX_PRIORITY_ROADMAP.md](FIX_PRIORITY_ROADMAP.md)). After them, a CONDITIONAL GO is justified, with the remaining P2s (accessibility, privacy copy, mock pages) scheduled.

## Score calculation
Credit: PASS = 1, PARTIAL = 0.5, FAIL = 0. "Tested" divides by executed cases; "Readiness" also counts NOT TESTED and BLOCKED as 0. Reproduce with `python audit/scripts/score.py`.

| Dimension | Weight | Applicable | Tested | Pass | Partial | Fail | Blocked / NT | Tested score | Readiness score | Confidence |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Core TTS functionality | 25 | 52 | 47 | 37 | 2 | 8 | 5 | 20.21 | 18.27 | High |
| Audio quality & languages | 10 | 19 | 17 | 15 | 1 | 1 | 2 | 9.12 | 8.16 | Medium (STT proxy; 14 of 322 voices; no listening) |
| UI/UX & responsiveness | 10 | 28 | 28 | 16 | 0 | 12 | 0 | 5.71 | 5.71 | High (Chromium only) |
| API & backend reliability | 10 | 15 | 15 | 10 | 0 | 5 | 0 | 6.67 | 6.67 | High |
| Security & privacy | 15 | 20 | 20 | 9 | 1 | 10 | 0 | 7.12 | 7.12 | Medium-high (no host/infra access) |
| Performance & scalability | 10 | 14 | 12 | 8 | 0 | 4 | 2 | 6.67 | 5.71 | Medium (no load/soak) |
| Authentication & data integrity | 5 | 3 | 3 | 2 | 1 | 0 | 0 | 4.17 | 4.17 | High (no accounts exist) |
| Accessibility | 5 | 14 | 12 | 5 | 0 | 7 | 2 | 2.08 | 1.79 | Medium (no screen reader) |
| SEO & public website | 5 | 15 | 15 | 10 | 0 | 5 | 0 | 3.33 | 3.33 | High |
| Testing, monitoring, deployment | 5 | 7 | 7 | 4 | 0 | 3 | 0 | 2.86 | 2.86 | High |
| **Total** | **100** | **187** | **176** | **116** | **5** | **55** | **11** | **67.9** | **63.8** | |

Coverage effects: the untested items (provider outage simulation, network loss mid-job, real mobile devices, Firefox/Safari, all 322 voices, human listening, soak/load, screen reader) are concentrated in Core, Audio, Performance and Accessibility. Those dimensions carry medium confidence. The overall score could move about ±4 points once they are covered.

## Top 20 verified defects

| # | ID | Sev | Title |
|---|---|---|---|
| 1 | TTS-BUG-001 | P1 | No server-side input size limit and no rate limiting on anonymous POST /api/tts |
| 2 | TTS-BUG-002 | P1 | Break markers amplify a 663-byte request into 30 min of audio |
| 3 | TTS-BUG-003 | P1 | Long text (≥ ~10–20k chars) fails with 502 after 45 s despite "no fixed limit" |
| 4 | TTS-BUG-004 | P2 | Blocking ffmpeg in async handler stalls all users (health up to 5.9 s) |
| 5 | TTS-BUG-005 | P2 | SRT/VTT are estimated, not word-timed as advertised |
| 6 | TTS-BUG-006 | P2 | Typing during generation re-enables Generate, causing duplicate jobs |
| 7 | TTS-BUG-007 | P2 | Language/voice mismatch → 502 and an error that blames the network |
| 8 | TTS-BUG-008 | P2 | Voice rows not keyboard-operable (WCAG 2.1.1 A) |
| 9 | TTS-BUG-010 | P2 | Colour contrast failures (57 nodes in light theme) |
| 10 | TTS-BUG-011 | P2 | Unlabelled controls; status messages not announced |
| 11 | TTS-BUG-015 | P2 | Privacy/cookie/llms.txt statements don't match behaviour |
| 12 | TTS-BUG-016 | P2 | Account/Support/Donate are mocks; no working contact channel |
| 13 | TTS-BUG-020 | P3 | No security headers; /docs exposed; verbose errors; cross-site POST accepted |
| 14 | TTS-BUG-021 | P3 | certifi 2026.7.22 advisory PYSEC-2026-4320 |
| 15 | TTS-BUG-019 | P3 | GET creates session dirs; lazy retention cleanup |
| 16 | TTS-BUG-014 | P3 | Malformed requests → 500 |
| 17 | TTS-BUG-013 | P3 | Sub-pages still branded "Voxly" |
| 18 | TTS-BUG-017 | P3 | Sub-pages overflow at 320 px; language select clipped |
| 19 | TTS-BUG-022 | P3 | Results lost on refresh |
| 20 | TTS-BUG-023 | P3 | Localized home partly English; /ar/ not RTL; no hreflang |

The full register (29 defects, with reproduction steps) is in [DEFECT_REGISTER.csv](DEFECT_REGISTER.csv).

## Major risks
1. **Abuse and availability** (BUG-001/002/004): anonymous, unbounded, single worker.
2. **Provider dependency.** The product relies on Microsoft's consumer Edge "Read Aloud" endpoint through an unofficial client. There is no SLA or contract, and the endpoint can be blocked. Product and legal should decide; plan an Azure AI Speech fallback.
3. **Trust and compliance.** Privacy copy describes analytics that don't exist, omits the third-party processor, and points to a contact form that sends nothing.
4. **No safety net.** There was no CI, no monitoring and no runnable tests. This audit adds a CI workflow and a mocked API suite on a local branch.

## Missing and incomplete features
NOT IMPLEMENTED: accounts (mock page), support inbox (mock), donations (mock), rate limiting/quotas, analytics (claimed), monitoring/error reporting.
INCOMPLETE: word-timed subtitles (estimated), localisation of home content, RTL on the Arabic/Persian home, session persistence of results, keyboard voice selection.
NOT APPLICABLE: history/dashboard/billing/admin/credits (free, anonymous product).

## Production release checklist

- [ ] BUG-001 input limit (API + UI) and nginx rate limit deployed
- [ ] BUG-002 total-silence and segment caps
- [ ] BUG-003 chunked synthesis; 5k-char input passes 10/10 in staging
- [ ] BUG-004 non-blocking ffmpeg; 2+ workers; health p99 < 200 ms under load
- [ ] Security headers, `/docs` disabled, `server_tokens off` (BUG-020)
- [ ] certifi bumped; `pip-audit` clean (BUG-021)
- [ ] Privacy policy and cookie banner corrected; contact channel works (BUG-015/016)
- [ ] Mock Account/Donate entry points hidden (BUG-016)
- [ ] `tests/test_api.py` green in CI with fixed defects' `expectedFailure` markers removed
- [ ] Uptime monitor on `/api/health` and a synthetic 1-sentence `/api/tts`
- [ ] Staging environment created; approved load test run (TC-F14)
- [ ] Rollback plan: previous `server.py` + `web/` kept on the VPS; `systemctl restart voxly`

## Deliverables
| # | File |
|---|---|
| 1 | [EXECUTIVE_AUDIT_REPORT.md](EXECUTIVE_AUDIT_REPORT.md) (this file) |
| 2 | [COMPLETE_FEATURE_INVENTORY.md](COMPLETE_FEATURE_INVENTORY.md) |
| 3 | [DEFECT_REGISTER.csv](DEFECT_REGISTER.csv) |
| 4 | [TEST_CASE_MATRIX.csv](TEST_CASE_MATRIX.csv) |
| 5 | [SECURITY_AUDIT.md](SECURITY_AUDIT.md) |
| 6 | [PERFORMANCE_REPORT.md](PERFORMANCE_REPORT.md) |
| 7 | [UI_UX_AUDIT.md](UI_UX_AUDIT.md) |
| 8 | [AI_AUDIO_QUALITY_REPORT.md](AI_AUDIO_QUALITY_REPORT.md) |
| 9 | [AUTOMATION_COVERAGE_REPORT.md](AUTOMATION_COVERAGE_REPORT.md) |
| 10 | [FIX_PRIORITY_ROADMAP.md](FIX_PRIORITY_ROADMAP.md) |
| — | Evidence: [evidence/](evidence/) (raw JSON results, run logs, 23 screenshots, SRT samples) · scripts: [scripts/](scripts/) · tests: `tests/test_api.py`, `.github/workflows/ci.yml` |

## Remediation log (branch `fix/day1-abuse-availability`, not deployed)

| Bug | Change | Verified by |
|---|---|---|
| 001 | `MAX_CHARS = 5000` in a Pydantic model + UI counter "n / 5000" that disables Generate; nginx `limit_req` 20 r/min/IP, burst 10, 429; `client_max_body_size 64k` | `test_text_length_limit`; local real-provider 5,001 chars → 422 in 0.2 s (was 45 s then 502) |
| 002, 009 | Total pause ≤ 60 s, ≤ 50 segments, at least one spoken segment | `test_break_marker_limits`, `test_break_only_text_is_rejected`; 663-char bomb → 400 in 0.01 s (was 30 min of audio) |
| 004 | ffmpeg/ffprobe moved off the event loop (`asyncio.to_thread`); 2 uvicorn workers | `test_ffmpeg_does_not_block_event_loop`: 5.77 s on old code, < 0.8 s on new |
| 006 | Busy flag on Generate | Browser: typing mid-job keeps it disabled; exactly 1 request |
| 007 | `NoAudioReceived` → 422 "Choose a Voice Language that matches…"; UI shows 4xx detail without blaming the network | `test_language_mismatch_is_actionable_422`; real provider: Hindi on Aria → 422 |
| 014 | Request schema; one readable 422 message | `test_malformed_json_is_4xx`, `test_non_numeric_speed_is_4xx`, `test_prosody_out_of_range_is_422` |
| 020 | HSTS, CSP, nosniff, DENY, Referrer-Policy, Permissions-Policy; `/docs`, `/redoc`, `/openapi.json` off; generic 5xx detail (logged server-side); JSON-only body; nginx `server_tokens off` | `test_security_headers_and_no_docs`, `test_provider_error_detail_not_leaked`, `test_cross_site_text_plain_post_rejected`; browser: no CSP violations, playback and downloads work |
| 021 | certifi 2026.10.19 | pip-audit: no known vulnerabilities |
| 024 | Counter counts code points, matching the server | Browser: "Hi 😀⏎line2" = 10 |
| 003 (partial) | Limit enforced and documented in FAQ, JSON-LD, How-it-works and llms.txt | Still open: chunked synthesis. 5,000 chars can still approach the 45 s timeout on a slow provider day |

Suite after fixes: `python -m unittest tests/test_api.py` → 20 tests, OK (3 expected failures: BUG-005, 012, 019). `tests/lang_test.js` → 26/26. `audit/scripts/verify_day1.mjs` → 10/10.

**Deploy notes:** the live nginx config differs from `deploy/nginx-voxy.conf` (it terminates TLS). Merge the `limit_req_zone`, `limit_req`, `server_tokens` and `client_max_body_size` lines into the live server block by hand, then run `nginx -t`. Update `voxly.service` (`--workers 2`) and `pip install -r requirements.txt` before restarting.

## Audit conduct
- Production received about 45 bounded API calls per probe run (the probe ran 3 times because of a script encoding bug: about 100 calls total) plus about 6 browser generations. There was no load testing, no exploit payloads and no data modification beyond the auditor's own session files.
- No application code was changed. Additions are tests, CI, scripts and reports on local branch `audit/2026-10-28`. Nothing was pushed or deployed.
- Facts in this report come from executed tests or cited code lines. Assumptions and recommendations are labelled as such. The platform/legal risk is an assessment, not a defect.
