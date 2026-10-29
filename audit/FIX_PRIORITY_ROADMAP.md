# Fix Priority Roadmap — text-2-speech.com

Ordered by risk ÷ effort. Effort: S < 2 h, M ≈ half a day, L > 1 day. Every fix needs its regression test green, and its `expectedFailure` marker removed where one exists.

## 1. Immediate P0 remediation
None. No P0 defects were confirmed.

## 2. Critical P1 fixes (release gate)

| # | Bug | Fix | Files | Depends on | Acceptance criteria | Regression test | Effort |
|---|---|---|---|---|---|---|---|
| 1 | BUG-001 | Pydantic request model: `text: str = Field(max_length=MAX_CHARS)` (e.g. 5,000), `speed`/`pitch: int = Field(0, ge=-100, le=100)`, `format: Literal["mp3","wav"]`. Mirror the limit in the UI counter (show "n / 5000", disable Generate above it). nginx `limit_req` 10 r/min/IP burst 5 on `/api/tts`; `client_max_body_size 256k`. | server.py, web/index.html, deploy/nginx-voxy.conf | — | Text over the limit → 422/413; the 11th request in a minute from one IP → 429; FAQ and llms.txt state the limit | `test_rejects_oversized_text`; nginx smoke test | M |
| 2 | BUG-002 | After `parse_segments`: reject if total silence > 60 s or segments > 50; reject if no speak segment (also fixes BUG-009) | server.py | #1 | 663-char break bomb → 400 | `test_rejects_excessive_total_silence`, `test_break_only_text_is_rejected` | S |
| 3 | BUG-003 | Chunk speak segments into sentence-aligned pieces of about 2,000 chars, each with its own 45 s timeout and one retry, then concat. Map timeout to 504 "The speech service is slow, please retry". | server.py | #1 | 5,000-char input succeeds 10/10 in staging; p95 < 30 s | Unit test of the chunker; staging integration test at the maximum length | M |

## 3. High-value P2 fixes

| # | Bug | Fix | Files | Acceptance criteria | Regression test | Effort |
|---|---|---|---|---|---|---|
| 4 | BUG-004 | Replace `subprocess.run` with `asyncio.create_subprocess_exec` (or `run_in_threadpool`); run `--workers 2` | server.py, deploy/voxly.service | `/api/health` p99 < 200 ms during 5 concurrent max-length jobs | Async health-latency test | S |
| 5 | BUG-005 | `edge_tts.Communicate(..., boundary="WordBoundary")`; keep the estimate as a fallback only | server.py:187 | SRT cue ends ≠ file duration; word cue start times within 100 ms of STT word timestamps on a sample | `test_requests_word_boundaries` | S |
| 6 | BUG-006 | `busy` flag; `updateCounter()` keeps Generate disabled while busy | web/index.html | Typing mid-job keeps the button disabled; exactly 1 request | Playwright | S |
| 7 | BUG-007 | Catch `NoAudioReceived` → 422 with a language-mismatch message; client shows `detail` without the network suffix for 4xx | server.py, web/index.html | Hindi text + English voice → actionable message | API + Playwright | S |
| 8 | BUG-008 | Voice list → `role=radiogroup` / `<input type=radio>` rows; Preview button outside the label | web/index.html | Enter/Space selects; axe nested-interactive = 0 | Playwright keyboard + axe | M |
| 9 | BUG-010, BUG-011 | Contrast tokens (light theme first); labels for sliders, number boxes, donate amount and support select; `#toast role=status aria-live=polite` | web/*.html | axe: 0 serious/critical on all 7 pages, both themes | axe in CI | M |
| 10 | BUG-015 | Remove the cookie banner (or add real analytics); name Microsoft as processor; fix llms.txt "runs entirely in the browser", "word-level timings" and "symbols cleaned up" | web/privacy.html, web/index.html, web/llms.txt, web/i18n-sub-parts | Disclosures match observed behaviour | Manual review checklist | S |
| 11 | BUG-016 | Hide the Account icon and Donate page until they work; replace the Support form with `mailto:` or a working endpoint; add a contact email to the privacy policy | web/*.html | No mock action reachable; a contact path delivers | Playwright | S |

## 4. P3 improvements

| # | Bug | Fix | Effort |
|---|---|---|---|
| 12 | BUG-020 | nginx security headers + `server_tokens off`; `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`; generic error details; require JSON content type | S |
| 13 | BUG-021 | `certifi>=2026.10.18`; keep `pip-audit` in CI (the added workflow fails until this is bumped) | S |
| 14 | BUG-019 | Read-only session lookup for GET; periodic cleanup task (e.g. every 10 min) | S |
| 15 | BUG-014 | Covered by the request model in #1; also wrap `get_voices()` in `api_tts` | S |
| 16 | BUG-013 | Replace the "Voxly" header brand on 6 pages; CI grep for user-visible "Voxly" | S |
| 17 | BUG-017 | Responsive sub-page header; min-width or icon for `#uilang` at 320 px | S |
| 18 | BUG-018 | Bind to the number box, `step=1`, clamp both; pitch label/units | S |
| 19 | BUG-022 | Persist results metadata in `sessionStorage` | S |
| 20 | BUG-023 | Translate or hide localized home content; `dir=rtl` for ar/fa; server-rendered canonical + hreflang; language URLs in sitemap | M |
| 21 | BUG-024, BUG-025, BUG-012 | Grapheme-correct counter; empty-state row; "(Multilingual)" label suffix | S |
| 22 | BUG-026, BUG-027 | www → apex 301; HTML 404 page; gzip JSON; HTTP/2; cache `/api/voices` | S |
| 23 | BUG-028 | Make `lang_test.js` runnable (devDependency, env BASE, npm script); uptime monitor + error logging | S |
| 24 | BUG-029 | Remove the placeholder "Friend Links" | S |

## 5. Future enhancements (not defects)
- Contracted provider (Azure AI Speech) or a fallback engine, to remove dependency on the unofficial Edge endpoint (see SECURITY_AUDIT.md, platform risk).
- Cancel button for long jobs; progress indication for chunked synthesis.
- A staging environment with an approved load-test budget (unblocks TC-F14) and a soak test (TC-F13).
- Human listening panel (MOS) for the top 20 voices; extend the STT matrix to all 75 languages.
- Real-device mobile checks (iOS Safari, Android Chrome) and Firefox/Safari desktop runs.

## Suggested sequence
Day 1: #1, #2, #4, #6, #12, #13 (abuse surface closed, availability protected).
Day 2: #3, #5, #7, #10, #11, #16.
Week 2: accessibility (#8, #9), then the remaining P3s.
Once #1–#4 are verified in staging, the release decision can move to **CONDITIONAL GO** (see EXECUTIVE_AUDIT_REPORT.md).
