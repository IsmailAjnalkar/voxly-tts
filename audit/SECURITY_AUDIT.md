# Security & Privacy Audit — text-2-speech.com

Date: 2026-10-28 · Scope: production (non-destructive checks only), source at `7f86514`, local instance for abuse tests.
No exploit payloads were run against production. No load or DoS testing was run against production. Credentials: none exist in the system.

## Summary

| Risk | Count | IDs |
|---|---:|---|
| P0 | 0 | — |
| P1 | 2 | BUG-001 (no input/rate limits), BUG-002 (break-marker amplification) |
| P2 | 2 | BUG-004 (event-loop blocking → availability), BUG-015 (privacy disclosures) |
| P3 | 4 | BUG-019, BUG-020, BUG-021, plus BUG-016 (no privacy contact channel, tracked as functional P2) |

**Status: AT RISK.** Data exposure risk is low: there are no accounts or secrets, files are isolated per session, and path traversal is blocked. The open risk is **availability and abuse**. Any anonymous client can make the server do unbounded work and use the site as a free proxy to Microsoft's speech service.

## Verified controls (PASS)

| Control | Evidence |
|---|---|
| No API keys / tokens in frontend | grep over `web/` found none; production files identical to repo |
| Provider access server-side only | `edge_tts` used only in `server.py` |
| Cross-session file access blocked | Other session id → 404 (`prod_api_results.json`) |
| Path traversal blocked | `/api/file/..%2f..%2fserver.py` → 404; code strips to `[a-zA-Z0-9_.-]` and checks `parents` (server.py:290-297) |
| User text never rendered as HTML | Snippet escapes `<` (index.html:570); text sent as JSON |
| Session id entropy | `crypto.randomUUID()` (122 bits) — index.html:431 |
| HTTPS | HTTP → 301 HTTPS; TLS 1.0 and 1.1 refused |
| CORS | Preflight from foreign origin → 405, no `Access-Control-Allow-Origin` |
| Static files | `/.git/config`, `/server.py` → 404 (only `web/` is mounted) |

## Findings

### S-1 · Unbounded anonymous usage — BUG-001 (P1)
- `POST /api/tts` has no auth, no size limit and no rate limit. nginx allows a 10 MB body (`deploy/nginx-voxy.conf:4`).
- Evidence: a 60,000-character request was accepted and held the provider for 45 s before failing (local). 43 production requests in about one minute were all served.
- Impact: cost and abuse. A third party can script the site as a free TTS API. Microsoft may throttle or block the server's IP, which takes the product down for everyone.
- Mitigation: hard `MAX_CHARS`; nginx `limit_req_zone $binary_remote_addr zone=tts:10m rate=10r/m;` with `limit_req zone=tts burst=5 nodelay;` on `/api/tts`; `client_max_body_size 256k`.

### S-2 · Break-marker amplification — BUG-002 (P1)
- 663 bytes of `[break:30s]` produced a **1,801.6 s (30 min)** MP3 and 60 ffmpeg processes in 8.9 s (local).
- Combined with S-3, a handful of such requests degrade the service for every user.
- Mitigation: cap total silence (e.g. 60 s) and segment count (e.g. 50).

### S-3 · Event-loop blocking — BUG-004 (P2, availability)
- `subprocess.run` (ffmpeg/ffprobe) runs inside `async def api_tts` on a single uvicorn worker.
- During S-2, `/api/health` took up to 5.9 s and only 3 of about 36 probes completed.
- Mitigation: `asyncio.create_subprocess_exec` or a threadpool; 2–4 workers.

### S-4 · Misconfiguration and information disclosure — BUG-020 (P3)
```
$ curl -sD - -o /dev/null https://text-2-speech.com/
HTTP/1.1 200 OK
Server: nginx/1.28.3 (Ubuntu)
Content-Type: text/html; charset=utf-8
cache-control: no-cache
```
- Missing: `Strict-Transport-Security`, `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options` / `frame-ancestors`, `Referrer-Policy`, `Permissions-Policy`.
- `/docs`, `/redoc`, `/openapi.json` are public (200).
- Raw exception text is returned to clients, e.g. `Synthesis failed: NoAudioReceived: No audio was received. Please verify that your parameters are correct.` (server.py:260).
- A cross-origin `Content-Type: text/plain` POST is accepted (200), because `req.json()` ignores content type. Impact is limited because no ambient credentials exist.
- Mitigation: nginx `server_tokens off;` plus the headers above (CSP: `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; frame-ancestors 'none'`); `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`; generic error details; require `application/json`.

### S-5 · Server state created by reads; lazy retention — BUG-019 (P3)
- `GET /api/file/x?s=<anything>` creates `data/<anything>/` (25 requests → 25 directories, local).
- The 2 h deletion runs only when someone generates, so files outlive the TTL on an idle server.

### S-6 · Vulnerable dependency — BUG-021 (P3)
```
$ pip-audit -r requirements.txt
Name    Version   ID              Fix Versions
certifi 2026.7.22 PYSEC-2026-4320 2026.10.18
```
Exploitability for this app was not assessed. Upgrade and add `pip-audit` to CI.

### S-7 · Malformed input → 500 — BUG-014 (P3)
Not a security hole by itself, but the absence of a request schema is also why S-1 and S-2 exist. A Pydantic model with `max_length` and range constraints fixes S-7 and enforces S-1 and S-2 in one place.

## Privacy review

| Question | Finding |
|---|---|
| Is user text sent to a third party? | **Yes.** Every generation sends the full text to Microsoft's online speech service through the unofficial `edge-tts` client. The privacy policy says only "the speech engine" and does not name Microsoft (BUG-015). |
| Retention of text/audio | Audio, subtitles and a JSON with a 120-character snippet are stored on disk for about 2 h after the session's last write. Deletion is lazy (S-5). Server logs were not inspected (no server access). |
| Cookies/analytics | Banner and policy describe analytics cookies, but none exist: `document.cookie` is empty after Accept and no analytics requests are made (BUG-015). |
| "Never used to train models" | Cannot be guaranteed for the third-party provider. Reword. |
| Contact for privacy requests | Policy points to the Support form, which is a non-functional mock (BUG-016). |

## Platform / legal risk (not a defect, flagged for decision)
The product depends on Microsoft's consumer "Read Aloud" endpoint through a reverse-engineered client, not on a contracted Azure Speech subscription. There is no SLA, the terms of use for commercial redistribution are unclear, and Microsoft can change or block the endpoint at any time. **Recommendation:** a product owner and legal should review this, and the team should plan a fallback to the paid Azure AI Speech API, which uses the same voice names and supports word boundaries.

## Not tested
Authenticated flows, RBAC and multi-tenant data (none exist); server-side log contents; infrastructure hardening of the VPS (SSH, firewall, OS patching); DoS resilience in production (prohibited without authorization).
