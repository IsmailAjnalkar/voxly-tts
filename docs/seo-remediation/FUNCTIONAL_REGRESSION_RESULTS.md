# Functional regression results: Playwright E2E suite

This suite checks that the SEO/AEO/GEO remediation did not break the tool itself. It lives in `tests/e2e/`:

- `functional.spec.js`: 31 tests
- `playwright.config.js`
- `package.json`: `@playwright/test` 1.64.1

It runs against any running instance of the app (`BASE`).

## How to run

Start the app (port 8804 is reserved for this suite during the remediation):

```bash
VOXLY_VOICE_SWEEP=0 .venv/Scripts/python.exe -m uvicorn server:app --port 8804
```

**Standard (with its own install):**

```bash
cd tests/e2e && npm install && npx playwright install chromium   # once
npm test                                                         # BASE defaults to http://localhost:8804
```

**Without installing (reuses the scratchpad `node_modules` that already holds `playwright` and `@playwright/test` 1.64.1).** This is the command used for the baseline:

```bash
cd tests/e2e
NM=C:/Users/ajnal/AppData/Local/Temp/claude/c--Users-ajnal-text2speech/b75bffd5-0b5f-41dd-867f-6d0c0a7e7992/scratchpad/pw/node_modules
MSYS_NO_PATHCONV=1 NODE_PATH=$NM node $NM/@playwright/test/cli.js test -c .
```

**Environment variables:**

| Variable | Meaning |
|---|---|
| `BASE=https://…` | Target instance. |
| `BROWSER=firefox` / `BROWSER=webkit` | Other engines. Chromium is the default. |
| `NO_GENERATE=1` | Skips the 6 tests that call Microsoft's speech service. Use it for a production smoke test, so no synthesis traffic is sent through the nginx rate limit. |
| `E2E_JSON=path.json` | Where the JSON report goes. Default: `tests/e2e/results/results.json`. |
| `-g "keyboard"` | Runs a subset of tests. |

Failures keep a trace, a screenshot and an error context under `tests/e2e/results/artifacts/` (that directory is gitignored). Open a trace with `npx playwright show-trace <trace.zip>`.

### Determinism and flaky-service handling

- One worker, run in order. Nothing runs in parallel against the speech service.
- No sleeps. Every wait is on a network response (`/api/tts`, `/api/file/…`), a DOM state, or a media `readyState`.
- `generate()` retries the external-service step **once** when it gets HTTP 5xx or 422 (`NoAudioReceived`). A retry is recorded as a `tts-retry` annotation in the JSON report and printed as `[tts-retry]` in the output. A second failure fails the test.
- Every page in every test is watched for `pageerror`, console errors and **CSP violations**. A `securitypolicyviolation` listener is injected, so this works in every engine. The suite proved it works on its first run: a test of my own used a string predicate that needed `unsafe-eval`, the production CSP blocked it, and the watcher flagged it. That was a test bug and it is fixed.
- Synthesis calls per run: 6 short ones (one or two sentences each).

## Test list

| # | Test | What it asserts |
|---|---|---|
| 1-12 | `page <path> loads` for `/`, `/es/`, `/tutorial.html`, `/how-it-works.html`, `/voices.html`, `/guides/subtitles.html`, `/guides/mp3-vs-wav.html`, `/support.html`, `/donate.html`, `/privacy.html`, `/terms.html`, `/auth.html` | HTTP 200, `h1` visible, voice list rendered (home pages), no page errors, console errors or CSP violations |
| 13 | text input | The counter counts code points ("Hi 😀\nline2" gives `10 / 5000 characters (2 lines)`). Generate is enabled at 5,000 characters and disabled at 5,001, with the counter shown in red. The server returns 422 for 5,001 characters. |
| 14 | Ctrl+B | Inserts `[break:500ms]` at the caret. |
| 15 | .txt import | Importing into an empty box fills it with no prompt. Importing over a draft asks first: Cancel keeps the draft and OK replaces it. The Import File button opens a single-file chooser. |
| 16 | voice language select | `es` lists only `es-*` voices and selects the curated default `es-AR-ElenaNeural`. |
| 17 | gender filter | Female and Male show only matching voices (checked against `/api/voices`). `aria-pressed` is set. All restores the full list. |
| 18 | voice search | "jenny" matches only Jenny voices. "zzzz" shows the "No voices match" empty state. |
| 19 | voice selection | Clicking a row moves `.sel`, checks the radio and shows the badge. |
| 20 | [tts] voice preview | Row Preview gets `POST /api/tts` 200 back, the preview `Audio` loads or plays, and no "could not be played" toast appears. |
| 21 | speed/pitch [tts] | The controls are gated by their checkboxes. Moving the slider updates the number box. 250 clamps to 100 on blur. The exact typed values (33, −20) are sent, and the 200 response produces a result. |
| 22 | [tts] generate MP3 | The chosen voice and `mp3` are sent. A result item appears with the voice name and "MP3". The `<audio>` element loads (`duration > 0`). The MP3, SRT and VTT links return **200** with `audio/mpeg`, `text/plain`/`application/x-subrip` and `text/vtt`. Bodies are not empty, SRT/VTT contain cues, and VTT starts with `WEBVTT`. Clicking the MP3 link downloads a `.mp3` file. |
| 23 | [tts] WAV + `[break:500ms]` | `format: wav` is sent and returned, the file is `.wav`, the duration is over 1.5 s, and the break marker is stripped from the snippet. The download is `audio/wav` with a `RIFF` header. |
| 24 | >25 breaks | 26 markers get HTTP 400, and the toast reads "Generation failed: Too many [break] markers (max 25)". No result is added and Generate is enabled again. |
| 25 | error states | Whitespace-only text disables Generate and Preview. The API returns 400 "Text is empty". A mocked 502 shows "Generation failed…" and keeps the text. A mocked 429 shows "Too many requests…". |
| 26 | rate-limit config | Reads `deploy/nginx-voxy-tls.conf` and checks for `limit_req_zone … zone=tts … rate=20r/m`, and that `location = /api/tts` has `limit_req zone=tts burst=…` and `limit_req_status 429`. No traffic is sent. |
| 27 | mobile 390 px | No horizontal overflow on `/`, `/es/`, `/tutorial.html`, `/how-it-works.html`, `/guides/subtitles.html` and `/support.html`. Key controls sit inside the viewport with a height of at least 24 px. The burger opens the nav with `aria-expanded=true`. Typing and selecting a voice work. |
| 28 | [tts] keyboard only | From the top of the page, using only Tab, Shift+Tab, Arrow keys, Space and Enter: Tab to the selected voice radio and ArrowDown to choose another; Space turns Autoplay off; type the text; Enter on Generate (checks that the keyboard-chosen voice is sent); Space on the audio player plays it; Enter on the MP3 link downloads it. The Tab presses for each step are recorded. |
| 29 | language switcher | `#uilang` set to `es` navigates to `/es/`. `html[lang=es]`, the Spanish H1 "Texto a voz gratuito en línea", "Generar audio" and the Spanish empty state are present. Header links point to `/es/…`. |
| 30 | theme toggle | Dark is the default. The toggle switches to light and sets `localStorage voxly-theme=light`. Light survives a reload and carries to `/tutorial.html`. Toggling back there makes home dark again. |
| 31 | [tts] session privacy | A result survives a reload in the same tab. A **new tab** in the same browser gets a different session id and an empty list. A **new browser context** sees no results. Fetching the file with another session id, or with none, returns 404. Another session's `DELETE /api/items/<id>` does not remove the file. |

### Rate limiting (production only, checked by reading the config)

This is enforced by nginx (`deploy/nginx-voxy-tls.conf`), not by the app, so a local run never hits it:

| Endpoint | Rule | Burst | Over the limit |
|---|---|---|---|
| `/api/tts` | 20 requests/min per IP (`zone=tts:10m rate=20r/m`) | `burst=10 nodelay` | `limit_req_status 429` |
| `/api/support` | 3 requests/min | `burst=3` | 429 |
| `/admin/login` | 3 requests/min | `burst=3` | 429 |

Test 26 guards the config. Test 25 checks that the UI handles a 429 ("Too many requests — please wait a minute and try again."). Production was **not** hammered to prove the limit.

## Baseline results (before integration)

Run on branch `seo/sage-remediation` at `88cdfd4`, with other agents' uncommitted edits in the working tree (53 changed files at the time). The app ran locally on :8804 and spoke to the real Microsoft speech service. Date: 2026-10-31.

| Engine | Passed | Failed | Flaky / retried | Duration | Report |
|---|---|---|---|---|---|
| Chromium (run 1) | **31** | 0 | 0 / 0 | 28 s | `evidence/e2e-baseline-chromium.json` |
| Chromium (run 2, determinism check) | **31** | 0 | 0 / 0 | 27 s | (same result) |
| Firefox | **31** | 0 | 0 / 0 | 69 s | `evidence/e2e-baseline-firefox.json` |
| WebKit (Playwright build for Windows) | 30 | **1** | 0 / 0 | 109 s | `evidence/e2e-baseline-webkit.json` |

No `tts-retry` was needed in any run.

### Keyboard-only flow: where it works and where it fails

Tab presses per step (Chromium / Firefox / WebKit):

| Step | Chromium | Firefox | WebKit | Result |
|---|---|---|---|---|
| Page top → selected voice radio | 17 | 18 | 8 (WebKit skips links when tabbing) | pass in all three |
| → Autoplay checkbox | 6 | 6 | 6 | pass |
| → text box | 1 | 1 | 1 | pass |
| → Generate (Enter) | 3 | 3 | 3 | pass |
| → audio player (Space) | 1 | 1 | 1 | **WebKit fails here** |
| → MP3 link (Enter) | 6 | 5 | not reached | pass in Chromium and Firefox |

- **WebKit failure, step "Tab to the audio player and press Space to play":** focus does land on the `<audio controls>` element, but Space does not start playback (the 10 s wait for `!audio.paused` times out). Pointer playback works, and the same audio loads in WebKit (test 22 passes). This is how WebKit's native media controls handle keys in Playwright's Windows build, not an app regression. The page cannot change it without custom player controls.
- **Observation, not a regression:** it takes 17 Tab presses to reach the voice list, because the header nav, language select, theme and account buttons, the Donate links, Voice Language, the three Gender buttons and the search box all come first. There is no "skip to the tool" link. Adding one would make keyboard access faster.

### Product bugs found

**None in the tested flows** on Chromium or Firefox. Notes:

- **Drag-and-drop import is not a product feature.** `web/index.html` has no `dragover`/`drop` handler; import is the button and `<input type=file>` only. Because of that it is not tested. Dropping a file on the textarea gets the browser's default behaviour.
- **SRT content type:** locally (Windows, Python `mimetypes`), SRT is served as `text/plain; charset=utf-8`. On Linux production it may be `application/x-subrip`, depending on `/etc/mime.types`. The test accepts either. It was not verified on production, because that would need a synthesis there.
- Out of scope for this suite but seen during measurement: an English sub-page shows **Spanish** content on the client if the visitor once chose Spanish (localStorage `voxly-ui`). This is intentional UX. Crawlers are unaffected. See `CORE_WEB_VITALS_REPORT.md`.

## After integration (lead fills in)

| Engine | Passed | Failed | Notes |
|---|---|---|---|
| Chromium | | | |
| Firefox | | | |
| WebKit | | | |

Run the same command with `E2E_JSON=…/evidence/e2e-after-chromium.json`. Any test that went from passing to failing is a regression. The WebKit keyboard Space-on-audio step is the known baseline failure.

## Related older suites (still usable)

Copy any of these into the scratchpad `pw/` directory and run it from there:

- `audit/scripts/verify_full.mjs BASE OUTDIR`: axe WCAG 2.2 AA on 12 pages in both themes, RTL, support form (`NO_STORE=1` for the production honeypot), 404s.
- `verify_ui.mjs BASE TMPDIR`
- `verify_day1.mjs BASE`
- `verify_interrupt.mjs BASE`
