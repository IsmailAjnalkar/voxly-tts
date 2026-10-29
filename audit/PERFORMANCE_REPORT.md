# Performance Report — text-2-speech.com

Date: 2026-10-28 · Client: Windows 11, Chromium (Playwright 1.x headless), residential network.
Production was measured with single-user requests only. Concurrency and stress tests ran **locally** (same code, uvicorn single worker, real Microsoft provider).

## Front-end (production, cold load)

| Metric | Desktop 1440×900 | Mobile (Moto G4 emulation, no CPU throttle) | Threshold | Result |
|---|---:|---:|---:|---|
| TTFB | 134 ms | 91 ms | < 800 ms | PASS |
| First Contentful Paint | 572 ms | 576 ms | < 1.8 s | PASS |
| Largest Contentful Paint | 572 ms | 576 ms | < 2.5 s | PASS |
| Cumulative Layout Shift | 0.0245 | 0 | < 0.1 | PASS |
| Interaction → next paint (voice row click; INP proxy) | 8 ms | 9 ms | < 200 ms | PASS |
| `load` event | 494 ms | 546 ms | — | — |
| Voice list rendered (voices API done) | 624 ms | 613 ms | < 2 s | PASS |
| HTML transfer | 36 KB (gzip, 90 KB raw) | same | — | OK |
| `/api/voices` transfer | 58 KB **uncompressed** | same | gzip | FAIL (BUG-027) |
| Requests on load | 2 (HTML + voices) | 2 | — | Excellent |
| HTTP version | HTTP/1.1 | | h2 | FAIL (BUG-027) |

Note: field INP was not measured (no RUM). The INP figure is a scripted lab proxy.

## Speech generation (production, n = 23 successful requests)

| Metric | Value |
|---|---|
| Latency median / p90 / max | **0.91 s / 1.69 s / 5.66 s** |
| Download latency median / max | 0.32 s / 0.63 s |
| Real-time factor (latency ÷ audio duration) median / max | 0.206 / 1.166 |
| 1,001 chars → 91.3 s audio | 1.49 s |
| Failed requests (unexpected) | 0 of 23 valid requests; 4 × 500/502 on invalid or mismatched input (BUG-007, BUG-014) |

## Long input (local)

| Input | Result | Time |
|---:|---|---:|
| 3,000 chars | 200 (231 s audio) | 25.0 s |
| 6,000 chars | 200 (463 s audio) | **39.7 s** (5.3 s below the 45 s timeout) |
| 10,000 chars | 200 (773 s audio) | 23.0 s |
| 20,000 chars | **502 TimeoutError** | 45.07 s |
| 60,000 chars | **502 TimeoutError** | 45.0 s |

Latency for one input size varies by roughly 2× between runs (provider side). The whole text is one provider call with a fixed 45 s timeout, so anything above about 5k characters is at risk (BUG-003).

## Concurrency and event-loop health (local)

| Scenario | Result |
|---|---|
| 6 parallel short generations | 6 × 200, wall time 2.07 s (0.88–2.06 s each) — PASS |
| `/api/health` polled every 250 ms during one 60-break request | max **5.9 s**, median 2.5 s, only 3 of about 36 polls completed — FAIL (BUG-004) |
| 663-character break-only input | 1,801 s of audio produced in 8.9 s — amplification (BUG-002) |

## Bottlenecks (ranked)
1. **Synchronous ffmpeg/ffprobe in the async handler** (server.py:169-183, 266-287) with one uvicorn worker. Any multi-segment or WAV request stalls every user.
2. **Single provider call per request with a fixed 45 s timeout.** There is no chunking or streaming, so long inputs fail and the work is wasted.
3. **Re-encode of every MP3** (concat with `libmp3lame`) even for single-segment input. `-c copy` would avoid it when no silence is involved.
4. `/api/voices` uncompressed and not cacheable by the browser. It is fetched on every page load.

## Recommended thresholds / SLOs
- Short text (≤ 500 chars): p95 generation < 3 s; error rate < 1 %.
- Max-length text (after BUG-001 sets the limit, e.g. 5,000 chars): p95 < 30 s with chunked synthesis.
- `/api/health` p99 < 200 ms under 10 concurrent generations.
- LCP < 2.5 s, CLS < 0.1, INP < 200 ms (currently met with a wide margin).

## Not measured
Memory and leak behaviour over time (soak), load in staging (BLOCKED: there is no staging environment and no approved concurrency limits), real-device mobile performance, CDN/edge caching.

## Reproduce
```
python -I audit/scripts/api_probe.py https://text-2-speech.com OUT/        # ~43 bounded requests
python -I audit/scripts/local_stress.py http://127.0.0.1:8137 data/        # LOCAL ONLY (asserts localhost)
node audit/scripts/browser_audit.mjs https://text-2-speech.com OUT/        # vitals + E2E
```
