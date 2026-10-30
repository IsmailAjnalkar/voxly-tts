"""
Text 2 Speech — free text-to-speech web app (server).
Engine: Microsoft Edge neural voices via edge-tts (300+ voices, 75 languages).
Features: voice catalog API, synthesis with [break:Xms]/[break:Xs] markers,
speed/pitch prosody, MP3/WAV output, SRT/VTT subtitles,
session-scoped result storage (files live only for the browser session).
"""
import asyncio
import hashlib
import hmac
import html as html_lib
import json
import logging
import os
import re
import shutil
import sqlite3
import ssl
import subprocess
import time
import urllib.parse
import uuid
from contextlib import asynccontextmanager, closing
from datetime import datetime, timedelta, timezone
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
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
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
MAX_BREAKS = 25           # [break:...] markers per generation (each one is an ffmpeg job)
# Long text is synthesized as sentence-aligned chunks, each its own provider
# call with its own timeout: one call for 6,000 chars took ~40 s of a 45 s budget.
CHUNK_CHARS = 1500
SYNTH_CONCURRENCY = 4     # provider calls in flight per request
SYNTH_TIMEOUT = 45        # seconds per provider call (one retry on failure)

log = logging.getLogger("text2speech")


@asynccontextmanager
async def _lifespan(app):
    tasks = [asyncio.create_task(_cleanup_loop())]
    if os.environ.get("VOXLY_VOICE_SWEEP", "1") != "0":  # off in CI: no provider calls
        tasks.append(asyncio.create_task(_voice_sweep_loop()))  # hides voices the service won't speak
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(title="Text 2 Speech", docs_url=None, redoc_url=None, openapi_url=None,
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
    path = request.url.path
    if "text/html" in resp.headers.get("content-type", ""):
        resp.headers["Cache-Control"] = "no-cache"
    elif resp.status_code == 200 and not path.startswith("/api/") and "cache-control" not in resp.headers:
        # Static files. Pages reference subi18n.js?v=<version>, so that one is immutable.
        if "v" in request.query_params:
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path.endswith((".png", ".svg", ".ico")):
            resp.headers["Cache-Control"] = "public, max-age=604800"
        else:
            resp.headers["Cache-Control"] = "public, max-age=3600"
    if (request.method == "GET" and resp.status_code == 200 and "text/html" in resp.headers.get("content-type", "")
            and not path.startswith("/admin") and "sec-purpose" not in request.headers  # skip prefetches
            and not _BOT_UA.search(request.headers.get("user-agent") or "bot")
            and not (ADMIN_COOKIE in request.cookies and _is_admin(request))):
        await asyncio.to_thread(_count_view, path)
    return resp


@app.exception_handler(RequestValidationError)
async def _invalid_request(request, exc):
    # One readable string, so the UI can show it as-is (FastAPI's default is a list).
    msg = "; ".join(f"{e['loc'][-1]}: {e['msg']}" for e in exc.errors())
    return JSONResponse({"detail": msg}, status_code=422)
_voices_cache: dict = {"data": None, "ts": 0}


def _session_dir(session_id: str, create: bool = False) -> Path:
    # Only generation creates a session dir; reads and deletes never do
    # (any ?s=<random> used to leave an empty directory behind).
    sid = re.sub(r"[^a-zA-Z0-9_-]", "", session_id or "")[:64]
    if not sid:
        raise HTTPException(400, "Missing session id")
    d = DATA / sid
    if create:
        d.mkdir(exist_ok=True)
    return d


def _cleanup_old_sessions() -> None:
    now = time.time()
    for d in DATA.iterdir():
        if d.is_dir() and now - d.stat().st_mtime > SESSION_TTL:
            shutil.rmtree(d, ignore_errors=True)


async def _cleanup_loop() -> None:
    # On a timer, so files expire even when nobody is generating.
    while True:
        try:
            await asyncio.to_thread(_cleanup_old_sessions)
        except Exception:
            log.exception("session cleanup failed")
        await asyncio.sleep(600)


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
        # Display name like the catalog convention: "Aria - US". Multilingual
        # voices keep a tag: "Andrew - US" existed twice without it.
        short = v["ShortName"].replace(locale + "-", "").replace("Neural", "")
        if short.endswith("Multilingual"):
            short = short[:-len("Multilingual")] + " (Multilingual)"
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
    return JSONResponse({"voices": voices, "languages": sorted(langs.keys()), "count": len(voices)},
                        headers={"Cache-Control": "public, max-age=3600"})


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


_TAIL_PUNCT = re.compile(r"[^\w\s]*")
_SENTENCE_END = (".", "!", "?", "…", "。", "！", "？", "؟", "।")
_ABBREV = {"mr.", "mrs.", "ms.", "dr.", "prof.", "st.", "vs.", "e.g.", "i.e."}  # "." not a sentence end


def align_words(text: str, words: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    """Map engine word timings back onto the source text. The engine drops
    punctuation ("Hello, world!" -> Hello / world) and CJK words carry no
    spaces, so each token becomes the source slice up to and including its
    trailing punctuation, with a leading space only where the source had one."""
    out, pos = [], 0
    for s, e, w in words:
        w = w.strip()
        i = text.find(w, pos) if w else -1
        if i < 0:  # engine rewrote the token: keep its own text
            out.append((s, e, " " + w))
            continue
        j = i + len(w)
        j += len(_TAIL_PUNCT.match(text, j).group())
        piece = text[pos:j]
        out.append((s, e, (" " if piece[:1].isspace() else "") + piece.strip()))
        pos = j
    return out


def build_subtitles(words: list[tuple[float, float, str]], srt: bool) -> str:
    """words: (start_s, end_s, token) from align_words. Cues of <= 10 tokens,
    also split at sentence ends."""
    cues, cur = [], []
    for w in words:
        cur.append(w)
        tok = w[2].strip()
        if len(cur) >= 10 or (tok.endswith(_SENTENCE_END) and tok.lower() not in _ABBREV):
            cues.append(cur); cur = []
    if cur:
        cues.append(cur)
    lines = []
    for i, cue in enumerate(cues, 1):
        start, end = cue[0][0], cue[-1][1]
        text = "".join(w[2] for w in cue).strip()
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
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, proxy=PROXY,
                                boundary="WordBoundary")  # default is SentenceBoundary
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
    if sum(s["type"] == "silence" for s in segments) > MAX_BREAKS:
        raise HTTPException(400, f"Too many [break] markers (max {MAX_BREAKS})")
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

    sdir = _session_dir(x_session_id, create=True)
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
        if words:
            words = align_words(seg["text"], words)
        else:
            # Speech service sent no word boundaries: estimate timings
            # proportionally from the real segment duration so the
            # SRT/VTT subtitles are never empty.
            toks = seg["text"].split()
            weights = [max(1, len(t)) for t in toks]
            total = sum(weights) or 1
            t = 0.0
            for tok, wgt in zip(toks, weights):
                span = dur * wgt / total
                words.append((t, t + span, " " + tok))
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
        # doesn't fit it (e.g. Hindi text on an English voice), or the voice is
        # flaky (sk-SK-Lukas: fails the request, answers the probe). The probe
        # rules out the first; the other two look the same, so name both.
        # Not hidden here: one failure can be a flaky voice; the sweep decides.
        if not await _voice_alive(engine):
            raise HTTPException(422, VOICE_UNAVAILABLE)
        raise HTTPException(422, "The speech service returned no audio for this text. Check that the "
                                 "Voice Language matches the language of your text, or try again.")
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
    if not sdir.is_dir() or sdir.resolve() not in p.parents or not p.is_file():
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
    return {"ok": True, "app": "text-2-speech"}


# --- Support inbox ----------------------------------------------------------
# Messages from /support.html are appended to support/inbox.jsonl (outside
# web/ and data/, so never served and never swept). Read it on the server.
SUPPORT_DIR = BASE / "support"
SUPPORT_MAX_BYTES = 5_000_000  # refuse new mail rather than fill the disk


class SupportRequest(BaseModel):
    email: str = Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    topic: Literal["generation", "voice", "bug", "business", "other"] = "other"
    message: str = Field(min_length=10, max_length=5000)
    website: str = ""  # honeypot: hidden from people, filled in by bots


@app.post("/api/support")
async def api_support(body: SupportRequest):
    if body.website:
        return {"ok": True}  # bot: pretend success, store nothing
    SUPPORT_DIR.mkdir(exist_ok=True)
    inbox = SUPPORT_DIR / "inbox.jsonl"
    if inbox.exists() and inbox.stat().st_size > SUPPORT_MAX_BYTES:
        log.error("support inbox full (%d bytes)", inbox.stat().st_size)
        raise HTTPException(503, "The support inbox is full, please try again later")
    line = json.dumps({"ts": int(time.time()), "email": body.email.strip(), "topic": body.topic,
                       "message": body.message.strip()}, ensure_ascii=False)
    with inbox.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    log.warning("support message received (topic=%s)", body.topic)  # shows up in the journal
    return {"ok": True}


# --- Page views and admin ---------------------------------------------------
# The server counts the HTML pages it serves: UTC date + path and nothing about the
# visitor (no IP, cookie or user agent is stored). Bots and the signed-in admin are
# not counted. /admin shows the counts; it exists only once admin.json has been
# written with tools/set_admin_password.py.
STATS_DB = BASE / "stats" / "views.sqlite3"
ADMIN_FILE = BASE / "admin.json"
ADMIN_COOKIE = "t2s_admin"
ADMIN_SESSION = 7 * 86400
_BOT_UA = re.compile(r"bot|crawl|spider|slurp|preview|headless|lighthouse|facebookexternalhit|curl|wget|"
                     r"python|httpx|node|go-http|java|monitor|uptime", re.I)


def _db() -> sqlite3.Connection:
    STATS_DB.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(STATS_DB, timeout=5)
    con.execute("CREATE TABLE IF NOT EXISTS views(day TEXT, path TEXT, n INTEGER NOT NULL, PRIMARY KEY(day, path))")
    return con


def _count_view(path: str) -> None:
    try:
        with closing(_db()) as con, con:
            con.execute("INSERT INTO views VALUES(date('now'), ?, 1) "
                        "ON CONFLICT(day, path) DO UPDATE SET n = n + 1", (path[:200],))
    except sqlite3.Error as e:  # counting must never break a page
        log.warning("page view not counted: %s", e)


def _admin_conf() -> dict | None:
    try:
        return json.loads(ADMIN_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def hash_password(pw: str, salt: str | None = None, iters: int = 300_000) -> str:
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), iters).hex()
    return f"pbkdf2_sha256${iters}${salt}${digest}"


def _check_password(pw: str, stored: str) -> bool:
    _, iters, salt, _digest = stored.split("$")
    return hmac.compare_digest(hash_password(pw, salt, int(iters)), stored)


def _admin_token(secret: str, exp: int) -> str:
    return f"{exp}.{hmac.new(secret.encode(), str(exp).encode(), hashlib.sha256).hexdigest()}"


def _is_admin(request: Request) -> bool:
    conf, tok = _admin_conf(), request.cookies.get(ADMIN_COOKIE, "")
    exp = tok.split(".", 1)[0]
    return bool(conf and exp.isdigit() and int(exp) > time.time()
                and hmac.compare_digest(tok, _admin_token(conf["secret"], int(exp))))


_ADMIN_CSS = ("body{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#eef1f6}"
              "main{max-width:1000px;margin:0 auto;padding:28px 20px 60px}h1{margin:0 0 4px;font-size:26px}"
              "h2{font-size:15px;text-transform:uppercase;letter-spacing:.07em;color:#94a3b8;margin:30px 0 10px}"
              ".sub{color:#94a3b8;margin:0 0 18px;font-size:14px}.top{display:flex;justify-content:space-between;align-items:start;gap:12px}"
              ".cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}"
              ".card{background:#161c26;border:1px solid #263042;border-radius:12px;padding:14px 16px}"
              ".card b{display:block;font-size:28px}.card span{color:#94a3b8;font-size:13px}"
              ".tw{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px;background:#161c26;border:1px solid #263042}"
              "th,td{padding:7px 12px;border-bottom:1px solid #263042;text-align:left}.n{text-align:right;font-variant-numeric:tabular-nums}"
              "th{color:#94a3b8;font-weight:600}.bar{height:10px;background:#ff6b4a;border-radius:5px;min-width:2px}"
              "a{color:#ff6b4a}input{width:100%;padding:11px;border-radius:10px;border:1px solid #263042;background:#1e2635;color:#eef1f6;"
              "font-size:15px;margin:6px 0 14px;box-sizing:border-box}"
              "button{background:#ff6b4a;color:#1a0e08;border:0;border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-size:15px}"
              "button.ghost{background:#1e2635;color:#eef1f6;border:1px solid #263042}.err{color:#fb7185}"
              ".login{max-width:360px;margin:12vh auto 0;background:#161c26;border:1px solid #263042;border-radius:14px;padding:24px}")
_ADMIN_HEADERS = {"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"}


def _admin_page(title: str, body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="robots" content="noindex, nofollow"><title>{title} | Text 2 Speech</title>'
        f'<link rel="icon" href="/favicon.svg" type="image/svg+xml"><style>{_ADMIN_CSS}</style></head><body><main>{body}</main></body></html>',
        status_code=status, headers=_ADMIN_HEADERS)


def _admin_login(error: str = "", status: int = 200) -> HTMLResponse:
    err = f'<p class="err" role="alert">{error}</p>' if error else ""
    return _admin_page("Admin sign in", '<form class="login" method="post" action="/admin/login"><h1>Admin</h1>'
                       f'<p class="sub">Text 2 Speech page views</p>{err}<label for="pw">Password</label>'
                       '<input id="pw" type="password" name="password" autocomplete="current-password" required autofocus>'
                       '<button type="submit">Sign in</button></form>', status)


def _admin_stats() -> dict:
    with closing(_db()) as con:
        rows = con.execute("SELECT day, path, n FROM views").fetchall()  # ponytail: full scan; aggregate in SQL past ~1M rows
    today = datetime.now(timezone.utc).date()
    start = {"today": today, "7 days": today - timedelta(days=6), "30 days": today - timedelta(days=29)}
    daily = {(today - timedelta(days=i)).isoformat(): 0 for i in range(30)}
    totals = {"Today": 0, "Yesterday": 0, "Last 7 days": 0, "Last 30 days": 0, "All time": 0}
    pages, langs = {}, {}
    lang_segs = {_PATH_OF_UI.get(c, c) for c in _UI_CODES}
    for day, path, n in rows:
        d = datetime.fromisoformat(day).date()
        row = pages.setdefault(path, {"today": 0, "7 days": 0, "30 days": 0, "all": 0})
        row["all"] += n
        for k, since in start.items():
            row[k] += n if d >= since else 0
        totals["All time"] += n
        totals["Today"] += n if d == today else 0
        totals["Yesterday"] += n if d == today - timedelta(days=1) else 0
        totals["Last 7 days"] += n if d >= start["7 days"] else 0
        totals["Last 30 days"] += n if d >= start["30 days"] else 0
        if day in daily:
            daily[day] += n
        if d >= start["30 days"]:
            seg = path.split("/")[1] if path.count("/") > 1 else ""
            lang = seg if seg in lang_segs else "en"
            langs[lang] = langs.get(lang, 0) + n
    return {"totals": totals, "daily": daily, "langs": langs,
            "pages": sorted(pages.items(), key=lambda kv: (-kv[1]["30 days"], -kv[1]["all"], kv[0]))}


def _admin_dashboard(st: dict) -> str:
    e = html_lib.escape
    cards = "".join(f'<div class="card"><b>{v:,}</b><span>{k}</span></div>' for k, v in st["totals"].items())
    peak = max(st["daily"].values()) or 1
    daily = "".join(f'<tr><td>{d}</td><td style="width:60%">{f'<div class="bar" style="width:{n * 100 / peak:.1f}%"></div>' if n else ''}</td>'
                    f'<td class="n">{n:,}</td></tr>' for d, n in st["daily"].items())
    pages = "".join(f'<tr><td><a href="{e(p)}" target="_blank" rel="noopener">{e(p)}</a></td><td class="n">{r["today"]:,}</td>'
                    f'<td class="n">{r["7 days"]:,}</td><td class="n">{r["30 days"]:,}</td><td class="n">{r["all"]:,}</td></tr>'
                    for p, r in st["pages"]) or '<tr><td colspan="5">No page views yet.</td></tr>'
    langs = "".join(f'<tr><td>{e(c)}</td><td class="n">{n:,}</td></tr>'
                    for c, n in sorted(st["langs"].items(), key=lambda kv: -kv[1])) or '<tr><td colspan="2">No page views yet.</td></tr>'
    return ('<div class="top"><div><h1>Page views</h1><p class="sub">Pages served to visitors, counted on the server (UTC days). '
            'Bots and your own visits are not counted; nothing about visitors is stored.</p></div>'
            '<form method="post" action="/admin/logout"><button class="ghost" type="submit">Sign out</button></form></div>'
            f'<div class="cards">{cards}</div>'
            '<h2>Pages</h2><div class="tw"><table><thead><tr><th>Page</th><th class="n">Today</th><th class="n">7 days</th>'
            f'<th class="n">30 days</th><th class="n">All time</th></tr></thead><tbody>{pages}</tbody></table></div>'
            f'<h2>Last 30 days</h2><div class="tw"><table><tbody>{daily}</tbody></table></div>'
            f'<h2>Languages (last 30 days)</h2><div class="tw"><table><tbody>{langs}</tbody></table></div>')


@app.get("/admin", include_in_schema=False)
async def admin(request: Request):
    if not _admin_conf():
        raise HTTPException(404)
    if not _is_admin(request):
        return _admin_login()
    return _admin_page("Page views", _admin_dashboard(await asyncio.to_thread(_admin_stats)))


@app.post("/admin/login", include_in_schema=False)
async def admin_login(request: Request):
    conf = _admin_conf()
    if not conf:
        raise HTTPException(404)
    form = urllib.parse.parse_qs((await request.body())[:4000].decode("utf-8", "replace"))
    pw = form.get("password", [""])[0]
    if not pw or not await asyncio.to_thread(_check_password, pw, conf["password_hash"]):
        log.warning("admin sign-in failed")
        return _admin_login("Wrong password.", 401)
    exp = int(time.time()) + ADMIN_SESSION
    resp = RedirectResponse("/admin", status_code=303, headers=_ADMIN_HEADERS)
    resp.set_cookie(ADMIN_COOKIE, _admin_token(conf["secret"], exp), max_age=ADMIN_SESSION,
                    httponly=True, secure=True, samesite="strict", path="/")
    return resp


@app.post("/admin/logout", include_in_schema=False)
async def admin_logout():
    resp = RedirectResponse("/admin", status_code=303, headers=_ADMIN_HEADERS)
    resp.delete_cookie(ADMIN_COOKIE, path="/", secure=True, httponly=True, samesite="strict")
    return resp


# --- Pages ------------------------------------------------------------------
# Every page is served at / and under each UI-language prefix (/es/, /zh-CN/
# ...). The server renders each language completely - visible text, title,
# description, social tags, canonical, hreflang, breadcrumbs - so crawlers
# (including AI crawlers that run no JavaScript) see the right language.
SITE = "https://text-2-speech.com"
_UI_CODES = ["en", "zh", "zh-TW", "ar", "cs", "da", "de", "es", "fa", "fr",
             "hi", "hu", "id", "it", "ja", "ko", "nl", "no", "pl", "pt",
             "ru", "sv", "th", "tr", "vi"]
_PATH_OF_UI = {"zh": "zh-CN"}            # URL segment for a UI code, when different
_HREFLANG = {"zh": "zh-CN", "pt": "pt-BR"}  # the pt UI is Brazilian Portuguese
_OG_LOCALE = {"en": "en_US", "zh": "zh_CN", "zh-TW": "zh_TW", "ar": "ar_AR", "cs": "cs_CZ", "da": "da_DK",
              "de": "de_DE", "es": "es_ES", "fa": "fa_IR", "fr": "fr_FR", "hi": "hi_IN", "hu": "hu_HU",
              "id": "id_ID", "it": "it_IT", "ja": "ja_JP", "ko": "ko_KR", "nl": "nl_NL", "no": "nb_NO",
              "pl": "pl_PL", "pt": "pt_BR", "ru": "ru_RU", "sv": "sv_SE", "th": "th_TH", "tr": "tr_TR", "vi": "vi_VN"}
_RTL = {"ar", "fa"}
# Translated pages (all 25 languages) and English-only content pages.
_PAGES = ["tutorial.html", "donate.html", "support.html", "auth.html", "privacy.html", "terms.html"]
_EN_PAGES = ["how-it-works.html", "voices.html", "guides/subtitles.html", "guides/mp3-vs-wav.html"]
_NOINDEX = {"donate.html", "auth.html"}  # placeholders until accounts/donations exist
_INDEXED = ["", "tutorial.html", "support.html", "privacy.html", "terms.html"]
# Description source and breadcrumb label for each translated sub-page.
_SUB_META = {"tutorial.html": ("tut_g1p", "nav_tutorial"), "support.html": (("sup_sub", "sup_quick_p"), "nav_support"),
             "privacy.html": ("priv_intro", "foot_privacy"), "terms.html": ("terms_s1p", "foot_terms"),
             "donate.html": ("don_sub", "nav_donate"), "auth.html": ("auth_sub", None)}
_WEBDIR = BASE / "web"
_HOMEDIR = _WEBDIR / "i18n-home"
_SUBDIR = _WEBDIR / "i18n-sub-parts"
_page_cache: dict = {}
_e = lambda t: html_lib.escape(t, quote=False)   # element text
_a = lambda t: html_lib.escape(t, quote=True)    # attribute value


def _home_ui_strings() -> dict:
    """UI strings per language from the I18N object in index.html (one line per language)."""
    src = (_WEBDIR / "index.html").read_text(encoding="utf-8")
    block = src[src.index("const I18N = {"):src.index("\n};", src.index("const I18N = {"))]
    out = {}
    for line in block.splitlines()[1:]:
        m = re.match(r'\s*"?([\w-]+)"?:\{(.*)\},?\s*$', line)
        if m:
            out[m.group(1)] = {k: json.loads(f'"{v}"') for k, v in
                               re.findall(r'(\w+):"((?:[^"\\]|\\.)*)"', m.group(2))}
    return out


_HOME_UI = _home_ui_strings()
_UI_NAMES = json.loads(re.search(r"const UI_LANGS = (\[.*?\]);", (_WEBDIR / "index.html").read_text(encoding="utf-8")).group(1))


def _sub_strings(code: str) -> dict:
    f = _SUBDIR / f"{code}.json"
    return json.loads((f if f.exists() else _SUBDIR / "en.json").read_text(encoding="utf-8"))


def _asset_version(path: str) -> str:
    st = (_WEBDIR / path.lstrip("/")).stat()
    return f"{int(st.st_mtime)}{st.st_size % 997}"


def _url(code: str | None, page: str) -> str:
    # English lives at the root: /en/ is an alias whose canonical is /.
    return f"{SITE}/{_PATH_OF_UI.get(code, code)}/{page}" if code and code != "en" else f"{SITE}/{page}"


def _width(text: str) -> int:
    """Display width: CJK and other wide characters count double (as in search snippets)."""
    return sum(2 if ord(ch) >= 0x2E80 else 1 for ch in text)


def _clip(text: str, n: int = 158) -> str:
    """Shorten to n display columns, at a sentence end, else a space, else hard."""
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()
    if _width(text) <= n:
        return text
    w = i = 0
    while i < len(text) and w + _width(text[i]) <= n - 1:
        w += _width(text[i]); i += 1
    cut = text[:i]
    end = max(cut.rfind(". "), cut.rfind("。"), cut.rfind("? "), cut.rfind("! "), cut.rfind("！"), cut.rfind("？"))
    if end > len(cut) // 2:
        return cut[:end + 1]
    space = cut.rfind(" ")
    return (cut[:space] if space > len(cut) // 2 else cut).rstrip(",;:、，") + "…"


def _translate(html: str, s: dict) -> str:
    """Server-side version of the client i18n: data-i18n (text), data-i18n-ph
    (placeholder) and data-i18n-html (inner HTML) take the language's strings."""
    html = re.sub(r'(<[^>]*\bdata-i18n="([\w-]+)"[^>]*>)([^<]*)(<)',
                  lambda m: m.group(1) + (_e(s[m.group(2)]) if m.group(2) in s else m.group(3)) + m.group(4), html)
    html = re.sub(r'(<[^>]*\bdata-i18n-ph="([\w-]+)"[^>]*\bplaceholder=")([^"]*)(")',
                  lambda m: m.group(1) + (_a(s[m.group(2)]) if m.group(2) in s else m.group(3)) + m.group(4), html)
    html = re.sub(r'(<(\w+)[^>]*\bdata-i18n-html="([\w-]+)"[^>]*>)(.*?)(</\2>)',
                  lambda m: m.group(1) + (s[m.group(3)] if m.group(3) in s else m.group(4)) + m.group(5), html, flags=re.S)
    return html


def _set_meta(html: str, title: str, desc: str | None, url: str | None, locale: str) -> str:
    html = re.sub(r"<title>.*?</title>", lambda m: f"<title>{_e(title)}</title>", html, count=1, flags=re.S)
    for attr, key, val in (("property", "og:title", title), ("name", "twitter:title", title),
                           ("name", "description", desc), ("property", "og:description", desc),
                           ("name", "twitter:description", desc), ("property", "og:url", url)):
        if val is not None:
            html = re.sub(rf'<meta {attr}="{key}" content="[^"]*">', lambda m: f'<meta {attr}="{key}" content="{_a(val)}">', html, count=1)
    if '<meta property="og:site_name"' in html and "og:locale" not in html:
        html = html.replace('<meta property="og:site_name" content="Text 2 Speech">',
                            f'<meta property="og:site_name" content="Text 2 Speech"><meta property="og:locale" content="{locale}">', 1)
    return html


def _lang_options(code: str) -> str:
    return "".join(f'<option value="{c}"{" selected" if c == code else ""}>{_e(n)}</option>' for c, n in _UI_NAMES)


def _breadcrumbs(html: str, items: list[tuple[str, str]]) -> str:
    """Visible breadcrumb at the top of <main> plus BreadcrumbList JSON-LD."""
    links = " <span aria-hidden=\"true\">›</span> ".join(
        f'<a href="{_a(u.replace(SITE, ""))}">{_e(n)}</a>' for n, u in items[:-1]) \
        + f' <span aria-hidden="true">›</span> <span aria-current="page">{_e(items[-1][0])}</span>'
    nav = f'<nav class="crumbs" aria-label="Breadcrumb">{links}</nav>'
    html = re.sub(r"(<main[^>]*>)", lambda m: m.group(1) + nav, html, count=1)
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(items, 1)]}
    return _add_jsonld(html, ld)


def _add_jsonld(html: str, data: dict) -> str:
    body = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return html.replace("</head>", '<script type="application/ld+json">' + body + "</script></head>", 1)


def _home_content(html: str, code: str | None) -> str:
    """Fill the home page's how-it-works, use cases, FAQ and FAQ JSON-LD from
    web/i18n-home/<lang>.json, and embed the data for client-side tab switching."""
    lang = code if code and (_HOMEDIR / f"{code}.json").exists() else "en"
    c = json.loads((_HOMEDIR / f"{lang}.json").read_text(encoding="utf-8"))
    step = c["steps"][0]
    html = html.replace("<!--home:step-->", f"<h3>{_e(step['h'])}</h3><p>{_e(step['b'])}</p>", 1)
    html = html.replace("<!--home:usecases-->", "".join(
        f'<div class="ucard"><div class="emo">{_e(u["e"])}</div><h3>{_e(u["h"])}</h3><p>{_e(u["p"])}</p></div>'
        for u in c["usecases"]), 1)
    html = html.replace("<!--home:faq-->", "".join(
        f'<div class="faqitem"><button class="q" type="button">{_e(f["q"])}<span>▾</span></button>'
        f'<div class="a">{_e(f["a"])}</div></div>' for f in c["faq"]), 1)
    data = json.dumps(c, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace("<!--home:data-->",
                        f'<script id="homecontent" type="application/json" data-lang="{lang}">{data}</script>', 1)
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    ld = json.loads(m.group(1))
    for node in ld["@graph"]:
        if node.get("@type") == "FAQPage":
            node["inLanguage"] = _HREFLANG.get(lang, lang)
            node["mainEntity"] = [{"@type": "Question", "name": f["q"],
                                   "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in c["faq"]]
        if node.get("@type") in ("WebApplication", "WebSite"):
            node["inLanguage"] = _HREFLANG.get(lang, lang)
    ld_text = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    return html[:m.start(1)] + ld_text + html[m.end(1):]


def _render(name: str, code: str | None) -> str:
    lang = code or "en"
    html = (_WEBDIR / name).read_text(encoding="utf-8")
    page = "" if name == "index.html" else name
    canon = _url(code, page)
    html = html.replace("/subi18n.js\"", f"/subi18n.js?v={_asset_version('subi18n.js')}\"")
    if name == "index.html":
        html = _home_content(html, code)
        ui = {**_HOME_UI["en"], **_HOME_UI.get(lang, {})}
        if lang != "en":
            html = _translate(html, ui)
            faq0 = json.loads((_HOMEDIR / f"{lang}.json").read_text(encoding="utf-8"))["faq"][0]["a"]
            faq0 = re.sub(r"^[^.。!！?？]{1,12}[.。!！?？]\s*", "", faq0)  # drop a leading "Yes."
            # The tagline alone when it fills a snippet; short ones (e.g. Chinese) get the free/no-sign-up
            # answer appended. Thai marks sentences with spaces, so it keeps the tagline only.
            desc = ui["hero_sub"] if _width(ui["hero_sub"]) >= 100 or lang == "th" else _clip(f"{ui['hero_sub']} {faq0}")
            html = _set_meta(html, f"{ui['h1']} | Text 2 Speech", desc, canon, _OG_LOCALE[lang])
        else:
            html = _set_meta(html, re.search(r"<title>(.*?)</title>", html).group(1), None, canon, "en_US")
        html = html.replace('<select class="uilang" id="uilang"', f'<select class="uilang" id="uilang" data-ssr="1"', 1)
        html = re.sub(r'(<select class="uilang" id="uilang"[^>]*>)(</select>)', lambda m: m.group(1) + _lang_options(lang) + m.group(2), html, count=1)
    elif name in _PAGES:
        s = _sub_strings(lang)
        html = _translate(html, s)
        desc_key, crumb_key = _SUB_META[name]
        if lang != "en":
            title = s.get({"tutorial.html": "doc_tutorial", "support.html": "doc_support", "privacy.html": "doc_privacy",
                           "terms.html": "doc_terms", "donate.html": "doc_donate", "auth.html": "doc_auth"}[name])
            if _width(title) > 70:  # search results cut long titles; they show the site name anyway
                title = title.replace(" | Text 2 Speech", "")
            if _width(title) > 70 and " — " in title:
                title = title.split(" — ")[0] + " | Text 2 Speech"
            html = _set_meta(html, title, _clip(" ".join(s[k] for k in (desc_key if isinstance(desc_key, tuple) else (desc_key,)))), canon, _OG_LOCALE[lang])
        else:
            html = _set_meta(html, re.search(r"<title>(.*?)</title>", html).group(1), None, canon, "en_US")
        html = html.replace('<script src="/subi18n.js',
                            '<script id="substrings" type="application/json">'
                            + json.dumps({k: s[k] for k in ("sup_ok", "sup_err")}, ensure_ascii=False)
                            + '</script><script src="/subi18n.js', 1)
        if crumb_key and name not in _NOINDEX:
            html = _breadcrumbs(html, [(s["nav_home"], _url(code, "")), (s[crumb_key], canon)])
        if name == "support.html":  # answer the common questions right on the support page
            c = json.loads((_HOMEDIR / f"{lang if (_HOMEDIR / f'{lang}.json').exists() else 'en'}.json").read_text(encoding="utf-8"))
            faq = "".join(f"<h3>{_e(f['q'])}</h3><p>{_e(f['a'])}</p>" for f in c["faq"])
            html = html.replace('<div class="card"><h2 style="margin-top:0" data-i18n="sup_contact_h">',
                                f'<div class="card"><h2 style="margin-top:0">FAQ</h2>{faq}</div>'
                                '<div class="card"><h2 style="margin-top:0" data-i18n="sup_contact_h">', 1)
    if name in _NOINDEX:
        html = re.sub(r'<meta name="robots" content="[^"]*">', '<meta name="robots" content="noindex, follow">', html, count=1)
    if name in _PAGES or name == "index.html":
        html = re.sub(r'(<select id="sublang"[^>]*>)(</select>)', lambda m: m.group(1) + _lang_options(lang) + m.group(2), html, count=1)
    if page in _INDEXED:
        links = f'<link rel="canonical" href="{canon}">' + "".join(
            f'<link rel="alternate" hreflang="{_HREFLANG.get(c, c)}" href="{_url(c, page)}">'
            for c in _UI_CODES) + f'<link rel="alternate" hreflang="x-default" href="{_url(None, page)}">'
        html = re.sub(r'<link rel="canonical" href="[^"]*">', lambda m: links, html, count=1)
    html = html.replace('<html lang="en"', f'<html lang="{lang}"' + (' dir="rtl"' if lang in _RTL else "")
                        + f' data-ui="{lang}"', 1)
    return html


def _page(name: str, code: str | None = None) -> HTMLResponse:
    key = (name, code)
    if key not in _page_cache:
        _page_cache[key] = _render(name, code)
    return HTMLResponse(_page_cache[key])


async def _voices_page() -> HTMLResponse:
    """voices.html with the live catalog table (voices the service won't speak are left out)."""
    html = _page("voices.html").body.decode("utf-8")
    try:
        voices = [v for v in await get_voices() if v["id"] not in _dead_voices]
    except Exception:
        voices = []
    by_lang: dict = {}
    for v in voices:
        by_lang.setdefault(v["language"], []).append(v)
    def lang_name(vs):
        names = sorted({re.sub(r"\s*\(.*", "", v["friendly"].split(" - ", 1)[-1]) for v in vs if " - " in v["friendly"]})
        return names[0] if names else vs[0]["language"]
    rows = []
    for code, vs in sorted(by_lang.items(), key=lambda kv: lang_name(kv[1]).lower()):
        f = sum(v["gender"] == "Female" for v in vs)
        locales = ", ".join(sorted({v["locale"] for v in vs}))
        names = ", ".join(_e(v["name"]) for v in sorted(vs, key=lambda v: v["name"]))
        rows.append(f"<tr><th scope=\"row\">{_e(lang_name(vs))}</th><td>{_e(locales)}</td>"
                    f"<td>{len(vs)} ({f} female, {len(vs) - f} male)</td><td>{names}</td></tr>")
    summary = (f"<strong>{len(voices)} voices in {len(by_lang)} languages</strong> are available right now."
               if voices else "The live voice list could not be loaded just now; please reload the page.")
    html = html.replace("<!--voices:summary-->", summary, 1).replace("<!--voices:rows-->", "".join(rows), 1)
    return HTMLResponse(html, headers={"Cache-Control": "public, max-age=3600"})


def _page_route(name: str, code: str | None):
    # A closure with NO parameters. A default-argument lambda (lambda page=...)
    # becomes a query parameter in FastAPI: ?page=../server.py read any file.
    async def handler():
        return _page(name, code)
    return handler


for _code in [None] + _UI_CODES:
    _prefix = f"/{_PATH_OF_UI.get(_code, _code)}" if _code else ""
    for _route in ([_prefix, _prefix + "/"] if _code else ["/"]):
        app.get(_route, include_in_schema=False)(_page_route("index.html", _code))
    for _name in _PAGES:
        app.get(f"{_prefix}/{_name}", include_in_schema=False)(_page_route(_name, _code))
app.get("/voices.html", include_in_schema=False)(_voices_page)
for _name in _EN_PAGES:
    if _name != "voices.html":
        app.get(f"/{_name}", include_in_schema=False)(_page_route(_name, None))


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap():
    locs = [_url(c, p) for p in _INDEXED for c in [None] + [c for c in _UI_CODES if c != "en"]]
    locs += [f"{SITE}/{p}" for p in _EN_PAGES]
    urls = "".join(f"<url><loc>{u}</loc></url>" for u in locs)
    return Response('<?xml version="1.0" encoding="UTF-8"?>\n'
                    f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n',
                    media_type="application/xml")


@app.exception_handler(StarletteHTTPException)
async def _not_found_page(request, exc):
    # Browsers get an HTML 404 page; the API keeps JSON errors.
    if exc.status_code == 404 and not request.url.path.startswith("/api/"):
        return HTMLResponse((_WEBDIR / "not-found.html").read_text(encoding="utf-8"), status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)


app.mount("/", StaticFiles(directory=str(BASE / "web"), html=True), name="web")
