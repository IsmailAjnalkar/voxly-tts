# Voxly — Free Text to Speech Online

A full-featured text-to-speech web app: 322 neural voices in 75 languages,
voice/gender/search picker, speed & pitch control, MP3/WAV generation with
word-timed SRT/VTT subtitles, [break:...] pause markers, session-only results,
25-language interface, dark/light themes. Built as a clean-room reimplementation
of the classic free-TTS tool layout — original code, copy and branding.

## Run locally
```bash
cd ~/workspace/projects/voxly-tts
.venv/bin/uvicorn server:app --port 8137
# open http://localhost:8137/
```

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
