# Automation Coverage Report — text-2-speech.com

Date: 2026-10-28 · Branch: `audit/2026-10-28` (local, not pushed)

## Existing automation (before audit)

| Asset | What it covers | Runnable from a clean checkout? | Result when run |
|---|---|---|---|
| `tests/lang_test.js` | 26 jsdom checks: language-prefix boot, default voice per UI language, sub-page i18n runtime | **No.** `jsdom` is not declared in `tests/package.json`, `BASE` is hardcoded to `http://localhost:8077`, and `npm test` exits 1 ("no test specified") | **26 passed, 0 failed** (with jsdom supplied via `NODE_PATH` and the app on :8077) |
| CI | — | No CI configuration in the repo | — |
| Backend unit/API tests | — | None | — |
| Browser E2E / a11y / perf | — | None | — |
| Monitoring / error reporting | — | None | — |

Estimated pre-audit coverage: the UI-language boot path only. **0 % of the API and 0 % of generation, download, subtitles, validation or security behaviour.**

## Added by this audit

| File | Type | Runs against | Deterministic? | Cases |
|---|---|---|---|---|
| `tests/test_api.py` | API regression (unittest + FastAPI TestClient; provider **mocked**, real ffmpeg) | in-process | Yes, safe for CI | 14 (6 pass, 8 pinned defects as `expectedFailure`) |
| `.github/workflows/ci.yml` | CI: unit tests + `pip-audit` | GitHub Actions | Yes | — |
| `audit/scripts/api_probe.py` | Bounded API probe (~43 requests): validation, generation, 12 languages, isolation, downloads, ffprobe | any URL | No (real provider) | 43 |
| `audit/scripts/local_stress.py` | Amplification, event-loop health, oversized input, concurrency, directory creation. **Refuses non-localhost URLs.** | localhost only | No | 6 |
| `audit/scripts/browser_audit.mjs` | Playwright: 9-viewport sweep, axe on 7 pages + light theme, web vitals, 35-step E2E (generate, play, download, delete, refresh, keyboard, errors, mobile nav, i18n, mock forms) | any URL | No | ~60 |
| `audit/scripts/browser_extra.mjs` | Import, theme persistence, FAQ, tabs, cookies, Preview Audio (stubbed), row preview | any URL | No | 10 |
| `audit/scripts/browser_subpages.mjs` | Sub-page overflow at 320 px, RTL, localized canonical | any URL | No | 5 |
| `audit/scripts/wer.py`, `acr.py`, `long_check.py` | STT-based WER/CER (faster-whisper + jiwer) | audio files | Model-dependent | 22 files |
| `audit/scripts/score.py` | Recomputes the readiness score from `TEST_CASE_MATRIX.csv` | — | Yes | — |

### Pinned defects in `tests/test_api.py`
`expectedFailure` tests flip to "unexpected success" when fixed, which tells you to delete the marker:

| Test | Bug |
|---|---|
| `test_rejects_oversized_text` | BUG-001 |
| `test_rejects_excessive_total_silence` | BUG-002 |
| `test_requests_word_boundaries` | BUG-005 |
| `test_break_only_text_is_rejected` | BUG-009 |
| `test_voice_display_names_unique` | BUG-012 |
| `test_malformed_json_is_4xx`, `test_non_numeric_speed_is_4xx` | BUG-014 |
| `test_file_get_does_not_create_session_dir` | BUG-019 |

Each expected failure was verified to fail on its assertion, not on a test error.

## Execution evidence (exact commands)

```text
# environment: Windows 11, Python 3.12.10 (.venv), Node 24.16.0, ffmpeg 8.1.2
$ .venv/Scripts/python -m unittest tests/test_api.py
Ran 14 tests in 15.635s
OK (expected failures=8)

$ NODE_PATH=<jsdom>/node_modules node tests/lang_test.js        # app on :8077
LANG TESTS: 26 passed, 0 failed

$ python -I audit/scripts/api_probe.py https://text-2-speech.com OUT/
TOTAL 43 PASS 37 FAIL 6          # see evidence/prod_api_run.log

$ python -I audit/scripts/local_stress.py http://127.0.0.1:8137 data/
amplification {'input_chars': 663, 'status': 200, 'seconds': 8.91, 'audio_duration_s': 1801.61} {'n': 3, 'max_s': 5.904, 'median_s': 2.492}
large 20000 {'status': 502, 'seconds': 45.07, 'result': '{"detail":"Synthesis failed: TimeoutError: "}'}
large 60000 {'status': 502, 'seconds': 45.0, 'result': '{"detail":"Synthesis failed: TimeoutError: "}'}
concurrent {'wall_s': 2.07, 'statuses': [200, 200, 200, 200, 200, 200], ...}
dirs {'before': 10, 'after': 35, 'created': 25}

# long-input threshold probe (local, same session)
3000 chars -> 200 25.0 s, audio 231.12 s
6000 chars -> 200 39.7 s, audio 463.34 s
10000 chars -> 200 23.0 s, audio 772.61 s

$ node audit/scripts/browser_audit.mjs https://text-2-speech.com OUT/   # see evidence/browser_run.log
$ .venv/Scripts/python -m pip_audit -r requirements.txt
certifi 2026.7.22 PYSEC-2026-4320 2026.10.18
$ python -I audit/scripts/score.py
TOTAL tested-score 67.9/100 | readiness-score 63.8/100 | coverage 176/187 = 94.1%
```

## Missing automation (recommended next)

| Gap | Recommendation | Priority |
|---|---|---|
| `lang_test.js` not runnable | Add `"devDependencies": {"jsdom": "^24"}`, read `BASE` from `process.env.BASE`, set `"test": "node lang_test.js"`, start uvicorn in CI | High |
| No browser tests in CI | Port the E2E steps of `browser_audit.mjs` to `@playwright/test` against a local server with the provider mocked (route `/api/tts` to a fixture) | High |
| No a11y gate | axe scan of 7 pages in CI; fail on critical/serious | Medium |
| Provider-failure paths | Unit tests that mock `synth_segment` raising `TimeoutError`, `NoAudioReceived` and an empty response, and assert mapped status and message | High |
| Real-provider smoke | Nightly staging job: 1 generation per 12 languages + WER threshold (≤ 0.1 on en/es/fr/de) | Medium |
| Monitoring | Uptime check on `/api/health` and on a 1-sentence `/api/tts`; error-rate alert from nginx logs | High |
| Security | `pip-audit` (added), header check, `/docs` 404 check in a post-deploy smoke test | Medium |

CI policy: regular CI uses the **mocked** provider only. Real-provider tests run in staging on a schedule so CI never depends on, or loads, Microsoft's endpoint.
