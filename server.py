"""
Voxly — free text-to-speech web app (server).
Engine: Microsoft Edge neural voices via edge-tts (300+ voices, 75 languages).
Features: voice catalog API, synthesis with [break:Xms]/[break:Xs] markers,
speed/pitch prosody, MP3/WAV output, SRT/VTT subtitles,
session-scoped result storage (files live only for the browser session).
"""
import asyncio
import json
import logging
import os
import re
import shutil
import ssl
import subprocess
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

# --- Network compatibility -------------------------------------------------
# Some environments (corporate/sandbox egress proxies) MITM TLS with a CA that
# lives in the system trust store rather than certifi's bundle. Prefer the
# system store when present so verification stays ON with the right chain.
_SYSTEM_CA = "/etc/ssl/certs/ca-certificates.crt"
if Path(_SYSTEM_CA).exists():
    try:
        import edge_tts.communicate as _comm
        import edge_tts.voices as _voices_mod
        _ctx = ssl.create_default_context(cafile=_SYSTEM_CA)
        _comm._SSL_CTX = _ctx
        _voices_mod._SSL_CTX = _ctx
    except Exception:
        pass
PROXY = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or None

import edge_tts
from fastapi import FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
SESSION_TTL = 2 * 3600  # generated files are session-only
# Abuse limits for the anonymous /api/tts endpoint. MAX_CHARS is mirrored in
# web/index.html (MAX_CHARS) and stated in the FAQ and llms.txt.
MAX_CHARS = 5000
MAX_SILENCE_MS = 60_000   # total of all [break:...] markers in one request
MAX_SEGMENTS = 50         # speak + silence pieces after splitting on markers
# Long text is synthesized as sentence-aligned chunks, each its own provider
# call with its own timeout: one call for 6,000 chars took ~40 s of a 45 s budget.
CHUNK_CHARS = 1500
SYNTH_CONCURRENCY = 4     # provider calls in flight per request
SYNTH_TIMEOUT = 45        # seconds per provider call (one retry on failure)

log = logging.getLogger("voxly")


@asynccontextmanager
async def _lifespan(app):
    sweep = asyncio.create_task(_voice_sweep_loop())  # hides voices the service won't speak
    yield
    sweep.cancel()


app = FastAPI(title="Voxly TTS", docs_url=None, redoc_url=None, openapi_url=None,
              lifespan=_lifespan)

_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    # Pages use inline <script>/<style>; everything else is same-origin.
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; "
        "connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"),
}


@app.middleware("http")
async def _headers(request, call_next):
    resp = await call_next(request)
    resp.headers.update(_SECURITY_HEADERS)
    # HTML pages must revalidate on every load so a deploy reaches visitors
    # immediately (a stale cached page kept an old, broken script alive).
    if "text/html" in resp.headers.get("content-type", ""):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.exception_handler(RequestValidationError)
async def _invalid_request(request, exc):
    # One readable string, so the UI can show it as-is (FastAPI's default is a list).
    msg = "; ".join(f"{e['loc'][-1]}: {e['msg']}" for e in exc.errors())
    return JSONResponse({"detail": msg}, status_code=422)
_voices_cache: dict = {"data": None, "ts": 0}


def _session_dir(session_id: str) -> Path:
    sid = re.sub(r"[^a-zA-Z0-9_-]", "", session_id or "")[:64]
    if not sid:
        raise HTTPException(400, "Missing session id")
    d = DATA / sid
    d.mkdir(exist_ok=True)
    return d


def _cleanup_old_sessions() -> None:
    now = time.time()
    for d in DATA.iterdir():
        if d.is_dir() and now - d.stat().st_mtime > SESSION_TTL:
            shutil.rmtree(d, ignore_errors=True)


# --- Voices ---------------------------------------------------------------
async def get_voices() -> list[dict]:
    if _voices_cache["data"] and time.time() - _voices_cache["ts"] < 86400:
        return _voices_cache["data"]
    raw = await edge_tts.list_voices(proxy=PROXY)
    out = []
    for v in raw:
        locale = v["Locale"]                       # e.g. en-US
        lang_code, _, country = locale.partition("-")
        friendly = v.get("FriendlyName", v["ShortName"])
        # Display name like the catalog convention: "Aria - US"
        short = (v["ShortName"].replace(locale + "-", "")
                 .replace("Neural", "").replace("Multilingual", ""))
        display = f"{short} - {country}"
        out.append({
            "id": v["ShortName"],
            "name": display,
            "locale": locale,
            "language": lang_code,
            "country": country,
            "gender": v.get("Gender", ""),
            "friendly": friendly,
            # Full name sent to the engine (what Edge itself sends): edge-tts
            # can't expand ids with a script part such as iu-Cans-CA-TaqqiqNeural.
            "engine": v["Name"],
        })
    # Alphabetical by display name within each language, matching the
    # reference catalog's ordering (not grouped by region).
    out.sort(key=lambda x: (x["language"], x["name"]))
    _voices_cache.update(data=out, ts=time.time())
    return out


# Voices the catalog lists but the service won't speak (11 of 322 on
# 2026-10-29: no audio for any text). Found by a sweep every VOICE_SWEEP_EVERY.
_dead_voices: set[str] = set()
VOICE_SWEEP_EVERY = 6 * 3600
VOICE_UNAVAILABLE = ("This voice is currently unavailable from the speech service. "
                     "Please choose another voice.")


SWEEP_ATTEMPTS = 8       # a voice is hidden only after this many failures in a row
PROBE_SPACING = 2         # seconds between attempts: flaky voices fail in runs


async def _voice_alive(engine: str, attempts: int = 1) -> bool:
    """One-word probe. Every working voice accepts English text, whatever its
    language, so 'no audio for Hello.' means the voice itself is unavailable.
    Some voices are flaky (cs-CZ-AntoninNeural answered 2 of 6 rounds), hence
    several spaced attempts before the sweep calls a voice dead."""
    for i in range(attempts):
        if i:
            await asyncio.sleep(PROBE_SPACING)
        try:
            audio, _ = await asyncio.wait_for(synth_segment("Hello.", engine, "+0%", "+0Hz"), 20)
            if audio:
                return True
        except edge_tts.exceptions.NoAudioReceived:
            pass
        except Exception:
            return True  # network trouble is no evidence against the voice
    return False


async def sweep_dead_voices() -> None:
    voices = await get_voices()
    slots = asyncio.Semaphore(8)

    async def check(v):
        async with slots:
            return v["id"], await _voice_alive(v["engine"], SWEEP_ATTEMPTS)

    dead = {vid for vid, ok in await asyncio.gather(*(check(v) for v in voices)) if not ok}
    _dead_voices.clear()
    _dead_voices.update(dead)
    log.warning("voice sweep: %d of %d voices unavailable: %s", len(dead), len(voices), sorted(dead))


async def _voice_sweep_loop() -> None:
    while True:
        try:
            await sweep_dead_voices()
        except Exception:
            log.exception("voice sweep failed")
        await asyncio.sleep(VOICE_SWEEP_EVERY)


@app.get("/api/voices")
async def api_voices():
    try:
        voices = await get_voices()
    except Exception as e:  # network blocked etc.
        raise HTTPException(502, f"Voice catalog unavailable: {type(e).__name__}")
    voices = [v for v in voices if v["id"] not in _dead_voices]
    langs = {}
    for v in voices:
        langs.setdefault(v["language"], 0)
        langs[v["language"]] += 1
    return {"voices": voices, "languages": sorted(langs.keys()), "count": len(voices)}


# --- Synthesis --------------------------------------------------------------
BREAK_RE = re.compile(r"\[break:\s*(\d+(?:\.\d+)?)\s*(ms|s)\]", re.IGNORECASE)


def parse_segments(text: str) -> list[dict]:
    """Split text into speak/silence segments using [break:Xms] / [break:Xs]."""
    segments, pos = [], 0
    for m in BREAK_RE.finditer(text):
        chunk = text[pos:m.start()].strip()
        if chunk:
            segments.append({"type": "speak", "text": chunk})
        val = float(m.group(1))
        ms = int(val if m.group(2).lower() == "ms" else val * 1000)
        if ms > 0:
            segments.append({"type": "silence", "ms": min(ms, 30000)})
        pos = m.end()
    tail = text[pos:].strip()
    if tail:
        segments.append({"type": "speak", "text": tail})
    return segments


# A sentence: anything up to and including end punctuation or a newline, plus
# trailing whitespace. Pieces concatenate back to the original text exactly.
_SENTENCE = re.compile(r"[^.!?…。！？؟।\n]*(?:[.!?…。！？؟।]+|\n|$)\s*")


def split_text(text: str, limit: int) -> list[str]:
    """Split text into chunks of <= limit chars at sentence ends, else at the
    last space, else hard, keeping the original separators inside chunks.
    ponytail: '.' after abbreviations ("Dr.") counts as a sentence end; it only
    matters if a chunk boundary lands exactly there."""
    chunks, cur = [], ""
    for piece in _SENTENCE.findall(text):
        while len(cur) + len(piece) > limit:
            if cur:
                chunks.append(cur)
                cur = ""
            else:  # one sentence longer than the limit
                cut = piece.rfind(" ", 0, limit) + 1 or limit
                chunks.append(piece[:cut])
                piece = piece[cut:]
        cur += piece
    if cur:
        chunks.append(cur)
    return [c.strip() for c in chunks if c.strip()]


def fmt_ts(seconds: float, srt: bool) -> str:
    ms_total = int(round(seconds * 1000))
    h, rem = divmod(ms_total, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    sep = "," if srt else "."
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def build_subtitles(words: list[tuple[float, float, str]], srt: bool) -> str:
    """words: (start_s, end_s, text). Group into cues of <= 10 words."""
    cues, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 10 or w[2].endswith((".", "!", "?", "。")):
            cues.append(cur); cur = []
    if cur:
        cues.append(cur)
    lines = []
    for i, cue in enumerate(cues, 1):
        start, end = cue[0][0], cue[-1][1]
        text = " ".join(w[2] for w in cue)
        if srt:
            lines.append(f"{i}\n{fmt_ts(start, True)} --> {fmt_ts(end, True)}\n{text}\n")
        else:
            lines.append(f"{fmt_ts(start, False)} --> {fmt_ts(end, False)}\n{text}\n")
    return ("WEBVTT\n\n" if not srt else "") + "\n".join(lines)


async def _ffmpeg(*args: str) -> None:
    # In a worker thread: a blocking subprocess.run on the event loop stalled
    # every other request (health checks took ~6 s during one long job).
    await asyncio.to_thread(subprocess.run, ["ffmpeg", "-y", *args],
                            check=True, capture_output=True)


async def _silence_mp3(path: Path, ms: int) -> None:
    await _ffmpeg("-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                  "-t", str(ms / 1000), "-codec:a", "libmp3lame", "-b:a", "48k", str(path))


async def _probe_duration(path: Path) -> float:
    r = await asyncio.to_thread(
        subprocess.run,
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


async def synth_segment(text: str, voice: str, rate: str, pitch: str) -> tuple[bytes, list]:
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, proxy=PROXY)
    audio, words = b"", []
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            words.append((chunk["offset"] / 1e7, (chunk["offset"] + chunk["duration"]) / 1e7, chunk["text"]))
    return audio, words


async def _synth_with_retry(text: str, voice: str, rate: str, pitch: str) -> tuple[bytes, list]:
    try:
        return await asyncio.wait_for(synth_segment(text, voice, rate, pitch), SYNTH_TIMEOUT)
    except Exception as e:  # incl. NoAudioReceived: some voices drop requests at random
        log.warning("provider call failed, retrying once (%s, %d chars)", type(e).__name__, len(text))
        return await asyncio.wait_for(synth_segment(text, voice, rate, pitch), SYNTH_TIMEOUT)


class TTSRequest(BaseModel):
    text: str = Field("", max_length=MAX_CHARS)
    voice: str = ""
    speed: int = Field(0, ge=-100, le=100)   # % -> edge-tts rate
    pitch: int = Field(0, ge=-100, le=100)   # % -> Hz, 1:1
    format: Literal["mp3", "wav"] = "mp3"


@app.post("/api/tts")
async def api_tts(body: TTSRequest, x_session_id: str = Header(default="")):
    text, voice, fmt = body.text.strip(), body.voice, body.format
    if not text:
        raise HTTPException(400, "Text is empty")
    segments = parse_segments(text)
    if not any(s["type"] == "speak" for s in segments):
        raise HTTPException(400, "Nothing to synthesize")
    if len(segments) > MAX_SEGMENTS:
        raise HTTPException(400, f"Too many [break] markers (max {MAX_SEGMENTS // 2})")
    if sum(s.get("ms", 0) for s in segments) > MAX_SILENCE_MS:
        raise HTTPException(400, f"Total pause length exceeds {MAX_SILENCE_MS // 1000} s")
    try:
        voices = await get_voices()
    except Exception:
        log.exception("voice catalog unavailable")
        raise HTTPException(502, "Voice catalog unavailable, please retry")
    engine = next((v["engine"] for v in voices if v["id"] == voice), None)
    if engine is None:
        raise HTTPException(400, "Unknown voice")
    if voice in _dead_voices:
        raise HTTPException(422, VOICE_UNAVAILABLE)
    rate, pitch = f"{body.speed:+d}%", f"{body.pitch:+d}Hz"

    _cleanup_old_sessions()
    sdir = _session_dir(x_session_id)
    item_id = uuid.uuid4().hex[:12]
    work = sdir / f"tmp-{item_id}"
    work.mkdir(exist_ok=True)

    pieces = [p for s in segments for p in (
        [{"type": "speak", "text": t} for t in split_text(s["text"], CHUNK_CHARS)]
        if s["type"] == "speak" else [s])]
    slots = asyncio.Semaphore(SYNTH_CONCURRENCY)

    async def render(i: int, seg: dict) -> tuple[Path, float, list]:
        part = work / f"part{i}.mp3"
        if seg["type"] == "silence":
            await _silence_mp3(part, seg["ms"])
            return part, seg["ms"] / 1000, []
        async with slots:
            audio, words = await _synth_with_retry(seg["text"], engine, rate, pitch)
        if not audio:
            raise HTTPException(502, "Synthesis returned no audio")
        part.write_bytes(audio)
        dur = await _probe_duration(part)
        if not words:
            # Speech service sent no word boundaries: estimate timings
            # proportionally from the real segment duration so the
            # SRT/VTT subtitles are never empty.
            toks = seg["text"].split()
            weights = [max(1, len(t)) for t in toks]
            total = sum(weights) or 1
            t = 0.0
            for tok, wgt in zip(toks, weights):
                span = dur * wgt / total
                words.append((t, t + span, tok))
                t += span
        return part, dur, words

    all_words, offset = [], 0.0
    tasks = [asyncio.create_task(render(i, s)) for i, s in enumerate(pieces)]
    try:
        try:
            rendered = await asyncio.gather(*tasks)
        except BaseException:
            # One piece failed: stop the rest before the work dir is removed.
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        for _, dur, words in rendered:
            all_words += [(offset + s, offset + e, w) for s, e, w in words]
            offset += dur
        part_files = [part for part, _, _ in rendered]

        # Concat -> final mp3
        listfile = work / "list.txt"
        listfile.write_text("".join(f"file '{p.name}'\n" for p in part_files))
        final_mp3 = sdir / f"{item_id}.mp3"
        await _ffmpeg("-f", "concat", "-safe", "0", "-i", str(listfile),
                      "-codec:a", "libmp3lame", "-b:a", "48k", str(final_mp3))
        audio_name = f"{item_id}.mp3"
        if fmt == "wav":
            await _ffmpeg("-i", str(final_mp3), str(sdir / f"{item_id}.wav"))
            audio_name = f"{item_id}.wav"
    except HTTPException:
        raise
    except edge_tts.exceptions.NoAudioReceived:
        # Either the voice itself is gone upstream, or the text's script
        # doesn't fit it (e.g. Hindi text on an English voice). A probe tells.
        # Not hidden here: one failure can be a flaky voice; the sweep decides.
        if not await _voice_alive(engine):
            raise HTTPException(422, VOICE_UNAVAILABLE)
        raise HTTPException(422, "This voice can't read this text. Choose a Voice Language "
                                 "that matches the language of your text.")
    except Exception:
        # Details go to the log, not to anonymous clients.
        log.exception("synthesis failed (voice=%s, chars=%d)", voice, len(text))
        raise HTTPException(502, "Synthesis failed, please retry")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    (sdir / f"{item_id}.srt").write_text(build_subtitles(all_words, srt=True), encoding="utf-8")
    (sdir / f"{item_id}.vtt").write_text(build_subtitles(all_words, srt=False), encoding="utf-8")
    duration = await _probe_duration(sdir / audio_name)
    snippet = re.sub(r"\s+", " ", BREAK_RE.sub(" ", text))[:120]
    meta = {"id": item_id, "voice": voice, "format": fmt, "duration": round(duration, 2),
            "snippet": snippet, "created": int(time.time()),
            "audio": f"/api/file/{audio_name}?item={item_id}",
            "audioName": audio_name,
            "srt": f"/api/file/{item_id}.srt", "vtt": f"/api/file/{item_id}.vtt"}
    (sdir / f"{item_id}.json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


@app.get("/api/file/{name}")
async def api_file(name: str, s: str = "", x_session_id: str = Header(default="")):
    # Media/download requests from the browser cannot send custom headers,
    # so the session id may arrive as the ?s= query parameter instead.
    sdir = _session_dir(x_session_id or s)
    p = (sdir / re.sub(r"[^a-zA-Z0-9_.-]", "", name)).resolve()
    if sdir.resolve() not in p.parents or not p.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(p)


@app.delete("/api/items/{item_id}")
async def api_delete(item_id: str, x_session_id: str = Header(default="")):
    sdir = _session_dir(x_session_id)
    iid = re.sub(r"[^a-zA-Z0-9]", "", item_id)
    for ext in ("mp3", "wav", "srt", "vtt", "json"):
        (sdir / f"{iid}.{ext}").unlink(missing_ok=True)
    return {"ok": True}


@app.get("/api/health")
async def health():
    return {"ok": True, "app": "voxly"}


# Per-language URLs, mirroring the reference site's scheme: /en/, /es/,
# /zh-CN/ ... Every page is reachable under each language prefix; the page
# itself boots in that language (client-side). Only exact known codes and
# page names are registered, so nothing else is swallowed.
_UI_CODES = ["en", "zh", "zh-TW", "ar", "cs", "da", "de", "es", "fa", "fr",
             "hi", "hu", "id", "it", "ja", "ko", "nl", "no", "pl", "pt",
             "ru", "sv", "th", "tr", "vi"]
_PATH_OF_UI = {"zh": "zh-CN"}  # URL segment for a UI code, when different
_PAGES = ["tutorial.html", "donate.html", "support.html", "auth.html",
          "privacy.html", "terms.html"]
_WEBDIR = BASE / "web"


def _serve_page(name: str):
    return FileResponse(_WEBDIR / name)


for _ui in _UI_CODES:
    _seg = _PATH_OF_UI.get(_ui, _ui)
    app.get(f"/{_seg}", include_in_schema=False)(
        lambda: _serve_page("index.html"))
    app.get(f"/{_seg}/", include_in_schema=False)(
        lambda: _serve_page("index.html"))
    for _page in _PAGES:
        app.get(f"/{_seg}/{_page}", include_in_schema=False)(
            lambda page=_page: _serve_page(page))


app.mount("/", StaticFiles(directory=str(BASE / "web"), html=True), name="web")
