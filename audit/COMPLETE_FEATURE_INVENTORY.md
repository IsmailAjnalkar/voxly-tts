# Complete Feature Inventory — text-2-speech.com

Audit date: 2026-10-28 · Build audited: `master@7f86514` (production files verified identical to repo, ignoring CRLF)
Status legend: PASS / FAIL / PARTIAL / BLOCKED / NOT IMPLEMENTED / NOT TESTED / NOT APPLICABLE. Test IDs refer to [TEST_CASE_MATRIX.csv](TEST_CASE_MATRIX.csv); bug IDs to [DEFECT_REGISTER.csv](DEFECT_REGISTER.csv).

## Architecture (discovered)

| Layer | Implementation |
|---|---|
| Hosting | Ubuntu VPS: nginx 1.28.3 (TLS, HTTP→HTTPS 301) → uvicorn (1 worker, `127.0.0.1:8000`, systemd `voxly.service`). Render/Docker config also present but production is the VPS. |
| Backend | `server.py` — FastAPI 0.143.3, single file, 5 API routes + static mount + 25 language-prefixed page routes |
| Speech provider | `edge-tts` 7.3.1 → Microsoft Edge "Read Aloud" online neural voices (unofficial client; no API key; 322 voices / 75 languages at audit time) |
| Audio processing | `ffmpeg`/`ffprobe` CLI (silence generation, concat, MP3 48 kbps re-encode, WAV conversion, duration probe) |
| Storage | Local disk `data/<session-id>/` — `<id>.mp3/.wav/.srt/.vtt/.json`; 2 h TTL by directory mtime; no database |
| Frontend | `web/index.html` (90 KB, inline CSS+JS, no build, no framework), 6 standalone sub-pages, `i18n-sub.js` (220 KB) + `subi18n.js` |
| Identity | None. Anonymous; per-tab session id from `crypto.randomUUID()` in `sessionStorage`, sent as `X-Session-Id` or `?s=` |
| Analytics / monitoring / error reporting | None found (banner and privacy policy claim analytics cookies) |
| Feature flags / env config | Only `https_proxy`/`HTTPS_PROXY` (provider proxy) and `PORT` (Docker) |
| Third parties | Microsoft speech service (receives all submitted text); Google Search Console verification meta tag |

## API endpoints

| Method | Path | Auth | Purpose | Result |
|---|---|---|---|---|
| GET | `/api/health` | none | liveness | PASS |
| GET | `/api/voices` | none | voice catalog (cached 24 h) | PASS (uncompressed — BUG-027) |
| POST | `/api/tts` | session id only | synthesize text | PARTIAL — BUG-001/002/003/004/005/007/009/014 |
| GET | `/api/file/{name}?s=` | session id | serve audio/subtitles/metadata | PASS (creates dirs on read — BUG-019) |
| DELETE | `/api/items/{id}` | session id | delete an item | PASS |
| GET | `/docs`, `/redoc`, `/openapi.json` | none | FastAPI defaults, publicly exposed | BUG-020 |

No background jobs, queues, webhooks or database. Cleanup runs inline at the start of each `/api/tts` call.

## Routes and pages

`/`, `/tutorial.html`, `/donate.html`, `/support.html`, `/auth.html`, `/privacy.html`, `/terms.html`, `/robots.txt`, `/sitemap.xml`, `/llms.txt`, `/og-image.png`, `/i18n-sub-parts/*.json` (build artefacts, reachable but harmless), plus every page under 25 language prefixes (`/es/`, `/zh-CN/`, `/de/tutorial.html`, …). All returned 200; unknown paths 404 (as JSON — BUG-026). No orphaned or hidden admin routes found.

## Feature table

| ID | Feature | Route / component | Intended behaviour | Status | Test method | Evidence | Defects |
|---|---|---|---|---|---|---|---|
| F-01 | Voice catalog | `GET /api/voices`, `get_voices()` | Live catalog of all voices | PASS | API + browser | TC-C36: 322 voices / 75 langs, unique ids | BUG-027 |
| F-02 | Voice language selector | `#langsel` | 75 languages, English default | PASS | Browser | TC-C37 | — |
| F-03 | Gender filter | `#genderseg` | All / Male / Female | PASS | Browser | TC-C38: 24 F + 23 M = 47 | — |
| F-04 | Voice search | `#vsearch` | Match name / locale / country / language | PARTIAL | Browser | TC-C39 pass; TC-U17 no empty state | BUG-025 |
| F-05 | Voice selection | `#voicelist .vrow` | Click or keyboard selects | PARTIAL | Browser | Mouse works; Enter/Space do nothing (TC-X08) | BUG-008, BUG-012 |
| F-06 | Curated default voice | `CURATED_DEFAULTS` | Preselect a voice | PASS | Browser | TC-C40 Natasha - AU | — |
| F-07 | Row Preview (server voice sample) | `previewVoice()` | Plays a real server sample | PASS | Browser | TC-C50 200 | — |
| F-08 | Preview Audio (device voice) | `#previewbtn` | Speaks text with a device voice | PASS (invocation) | Browser, speechSynthesis stubbed | TC-C49: cleaned text, locale en-AU; audible output NOT TESTED (headless) | — |
| F-09 | Text input + counter | `#text`, `updateCounter()` | Accurate count, enable buttons | PARTIAL | Browser | Emoji counted as 2 (TC-C33) | BUG-024 |
| F-10 | Ctrl+B break insertion | keydown handler | Insert `[break:500ms]` | PASS | Browser | TC-C34 | — |
| F-11 | Import .txt/.md | `#fileinput` | Load file into textarea | PASS | Browser | TC-C35 | — |
| F-12 | Speed control | `#speed`, `#speed_num` | −100…+100 % applied | PARTIAL | Browser + API | Applied (TC-C21) but box/slider desync (TC-C54), no server clamp (TC-P07) | BUG-018 |
| F-13 | Pitch control | `#pitch`, `#pitch_num` | −100…+100 % | PARTIAL | API + code | Applied as ±Hz, labelled % | BUG-018 |
| F-14 | MP3 output | `format=mp3` | Valid MP3 | PASS | ffprobe | TC-C19 | — |
| F-15 | WAV output | `format=wav` | Valid WAV | PASS | ffprobe | TC-C20 | — |
| F-16 | Break markers | `parse_segments()` | Exact silences | PARTIAL | API + SRT | Gaps correct (TC-C15); silent-only output (TC-C16); unbounded total (TC-S08) | BUG-002, BUG-009 |
| F-17 | Speech generation (short/medium) | `POST /api/tts` | Audio for valid input | PASS | API, browser, ffprobe, STT | 23 prod generations, median 0.91 s | — |
| F-18 | Long-text generation ("no fixed limit") | `POST /api/tts` | Long text succeeds | FAIL | Local API | 20k/60k chars → 502 after 45 s (TC-C10/11) | BUG-003, BUG-001 |
| F-19 | Multilingual generation | voices per language | Correct language speech | PASS | STT on 12 languages | TC-A01…A12 | — |
| F-20 | Duplicate-job prevention | `#genbtn` | One job at a time | FAIL | Browser | 2 requests (TC-C26) | BUG-006 |
| F-21 | Error handling & messaging | toast, `HTTPException` | Actionable messages, 4xx for bad input | FAIL | API + browser | 500s (TC-P04-06); misleading toast (TC-U19) | BUG-007, BUG-014 |
| F-22 | Results list + audio player | `#resultlist` | Play/pause/seek/volume | PASS | Browser media API | TC-C42 | — |
| F-23 | Autoplay after generation | `#autoplay` | Plays when ticked | PASS | Browser | TC-C43 | — |
| F-24 | Audio download | `.dl a[download]` | Correct non-empty file | PASS | Browser + ffprobe | TC-C44, TC-A16 | — |
| F-25 | SRT/VTT subtitles | `build_subtitles()` | Word-timed captions | PARTIAL | Library inspection + SRT | Files download; timings estimated (TC-A15) | BUG-005 |
| F-26 | Delete result | `DELETE /api/items/{id}` | Item and files removed | PASS | Browser + API | TC-C47 | — |
| F-27 | Results kept for the browser session | `ITEMS` | Survive refresh | FAIL | Browser | 0 after reload (TC-C48) | BUG-022 |
| F-28 | Session isolation | `_session_dir`, `api_file` | Only owner reads files | PASS | API | TC-S04, TC-P09 | — |
| F-29 | File retention (2 h) | `_cleanup_old_sessions` | Auto-delete | PARTIAL | Code review | Only runs on new generations | BUG-019 |
| F-30 | Interface language (25 UIs) | `#uilang`, `I18N`, `subi18n.js` | Full localisation | PARTIAL | Browser + repo test | Sub-pages and core strings localised (lang_test 26/26); home FAQ/steps English; /ar/ home not RTL | BUG-023 |
| F-31 | Language URL prefixes | `server.py:315-339` | `/es/…` serve pages | PASS | curl + browser | All 200; /xx/ 404 | — |
| F-32 | Dark/light theme | `#themebtn` | Toggle + persist | PASS | Browser | TC-U13 | BUG-010 (light contrast) |
| F-33 | Mobile navigation (home) | `#burger` | Toggle nav | PASS | Browser | TC-U12 | — |
| F-34 | Responsive sub-pages | sub-page header | No overflow at 320 px | FAIL | Browser | scrollWidth 397 (TC-U10) | BUG-017 |
| F-35 | How-it-works tabs, use cases, FAQ | `#steptabs`, `#usecases`, `#faqlist` | Interactive content | PASS | Browser | TC-U14, TC-U15 | — |
| F-36 | Cookie consent banner | `#cookie` | Consent for analytics | PARTIAL | Browser | Works and remembers; nothing to consent to (no analytics) | BUG-015 |
| F-37 | Tutorial / Privacy / Terms pages | sub-pages | Content pages | PASS | Browser + axe | 0 axe violations; content present | BUG-013 (brand) |
| F-38 | Branding consistency | headers | "Text 2 Speech" | FAIL | Browser | 6 pages show "Voxly" | BUG-013 |
| F-39 | Account sign-in / sign-up / reset | `/auth.html` | — | NOT IMPLEMENTED | Browser | `alert()` mock; 0 requests | BUG-016 |
| F-40 | Support contact form | `/support.html` | Deliver message | NOT IMPLEMENTED | Browser | `alert()` mock | BUG-016 |
| F-41 | Donations | `/donate.html` | Checkout | NOT IMPLEMENTED | Browser | `alert()` mock | BUG-016 |
| F-42 | Health endpoint | `/api/health` | 200 | PASS | curl | TC-P01 | — |
| F-43 | SEO metadata, sitemap, robots, JSON-LD, OG | all pages | Valid | PASS | curl + parse | TC-E01…E08 | BUG-023, BUG-026 |
| F-44 | llms.txt (AI answer engines) | `/llms.txt` | Accurate facts | FAIL | Source review | False claims | BUG-015 |
| F-45 | Rate limiting / quotas / abuse protection | — | Bound anonymous usage | NOT IMPLEMENTED | Code + API | None anywhere | BUG-001, BUG-002 |
| F-46 | Analytics | — | Claimed by banner/policy | NOT IMPLEMENTED | Source + network | No script, no cookies | BUG-015 |
| F-47 | Monitoring / error reporting | — | Alerting on failures | NOT IMPLEMENTED | Source review | None | BUG-028 |
| F-48 | Automated tests / CI | `tests/` | Runnable suite in CI | PARTIAL | Executed | lang_test passes 26/26 once deps supplied; no CI | BUG-028 |
| F-49 | Deployment & TLS | nginx + systemd | HTTPS, redirect | PASS | curl | TC-S10, TC-S11, TC-T07 | BUG-020, BUG-027 |
| F-50 | History, dashboard, profile, billing, admin, credits | — | — | NOT APPLICABLE | Code review | Not part of the product (free, anonymous) | — |

### Feature counts

| Status | Count |
|---|---:|
| PASS | 25 |
| PARTIAL | 11 |
| FAIL | 7 |
| NOT IMPLEMENTED | 6 (3 visible mocks, rate limiting, analytics, monitoring) |
| NOT APPLICABLE | 1 |
| BLOCKED / NOT TESTED | 0 at feature level (gaps are at test-case level: 10 NOT TESTED, 1 BLOCKED) |
| **Total** | **50** |
