# Text 2 Speech — Free Text to Speech Online

A full-featured text-to-speech web app: 300+ neural voices in 75 languages,
voice/gender/search picker, speed & pitch control, MP3/WAV generation with
word-timed SRT/VTT subtitles, [break:...] pause markers, session-only results,
25-language interface, dark/light themes. Built as a clean-room reimplementation
of the classic free-TTS tool layout — original code, copy and branding.

## Run locally
Needs Python 3.12 and ffmpeg on PATH.
```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn server:app --port 8137        # open http://localhost:8137/
```
Set `VOXLY_VOICE_SWEEP=0` to skip the startup voice-health sweep (one short
synthesis per voice) when you don't need it.

## Tests
```bash
.venv/bin/pip install httpx pytest
.venv/bin/python -m pytest tests/test_api.py          # API, speech provider mocked
VOXLY_VOICE_SWEEP=0 .venv/bin/uvicorn server:app --port 8077 &
cd tests && npm ci && npm test                        # UI-language tests (BASE=http://localhost:8077)
```
CI (`.github/workflows/ci.yml`) runs both plus `pip-audit`. Browser, audio and
load checks against the real service live in `audit/scripts/` (see
`audit/AUTOMATION_COVERAGE_REPORT.md`).

## Support inbox
Messages from the Support page are appended to `support/inbox.jsonl` on the
server (one JSON object per line: time, email, topic, message). It is never
served over HTTP; read it on the host, e.g.
`tail -n 20 /opt/voxly/support/inbox.jsonl`.

## Architecture
- `server.py` — FastAPI backend.
  - `GET /api/voices` — live voice catalog from the Edge speech service
    (cached 24h), shaped as Name/CC + locale + gender.
  - `POST /api/tts` — {text, voice, speed%, pitch%, format} → parses
    [break:Xms]/[break:Xs] markers into speak/silence segments, synthesizes
    each with edge-tts (rate/pitch prosody), inserts real silence, concatenates
    with ffmpeg, converts to WAV on request, and builds SRT+VTT from the
    engine's word-boundary timings. Files are stored per browser session
    (X-Session-Id header or ?s= param) and expire after 2h.
  - `GET /api/file/{name}`, `DELETE /api/items/{id}`, `GET /api/health`.
  - Network hardening: prefers the system CA store (some egress proxies MITM
    TLS with a system-installed CA) and honors https_proxy env vars.
- `web/` — dependency-free frontend (no build step): index.html is the tool;
  tutorial/donate/support/auth/privacy/terms are standalone pages in the
  same theme (coral/amber on slate; the reference site used indigo/emerald).

## Notes / known limits
- Preview uses the visitor's own device speech voices for zero-latency
  sampling; Generate always renders with the selected server voice.
- Donate checkout and the support inbox are front-end complete and open
  with a public launch (no payment details are collected yet).
- In heavily proxied sandboxes the speech service's WebSocket handshake may
  be blocked by the egress proxy (catalog over HTTPS still works). On a
  normal host (e.g. Render) generation works end to end.
