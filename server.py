"""
Voxly — free text-to-speech web app (server).
Engine: Microsoft Edge neural voices via edge-tts (322 voices, 75+ languages).
Features: voice catalog API, synthesis with [break:Xms]/[break:Xs] markers,
speed/pitch prosody, MP3/WAV output, word-timing SRT/VTT subtitles,
session-scoped result storage (files live only for the browser session).
"""
import asyncio
import json
import os
import re
import shutil
import ssl
import subprocess
import time
import uuid
from pathlib import Path

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
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
SESSION_TTL = 2 * 3600  # generated files are session-only

app = FastAPI(title="Voxly TTS")


@app.middleware("http")
async def _no_cache_html(request, call_next):
    # HTML pages must revalidate on every load so a deploy reaches visitors
    # immediately (a stale cached page kept an old, broken script alive).
    resp = await call_next(request)
    if "text/html" in resp.headers.get("content-type", ""):
        resp.headers["Cache-Control"] = "no-cache"
    return resp
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
        })
    # Alphabetical by display name within each language, matching the
    # reference catalog's ordering (not grouped by region).
    out.sort(key=lambda x: (x["language"], x["name"]))
    _voices_cache.update(data=out, ts=time.time())
    return out


@app.get("/api/voices")
async def api_voices():
    try:
        voices = await get_voices()
    except Exception as e:  # network blocked etc.
        raise HTTPException(502, f"Voice catalog unavailable: {type(e).__name__}")
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


def _silence_mp3(path: Path, ms: int) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
         "-t", str(ms / 1000), "-codec:a", "libmp3lame", "-b:a", "48k", str(path)],
        check=True, capture_output=True)


def _probe_duration(path: Path) -> float:
    r = subprocess.run(
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


@app.post("/api/tts")
async def api_tts(req: Request, x_session_id: str = Header(default="")):
    body = await req.json()
    text = (body.get("text") or "").strip()
    voice = body.get("voice") or ""
    fmt = (body.get("format") or "mp3").lower()
    if fmt not in ("mp3", "wav"):
        raise HTTPException(400, "Format must be mp3 or wav")
    if not text:
        raise HTTPException(400, "Text is empty")
    voices = await get_voices()
    if voice not in {v["id"] for v in voices}:
        raise HTTPException(400, "Unknown voice")
    # Prosody mapping: UI % -> edge-tts rate %; pitch % -> Hz (1% = 1Hz, +/-100)
    speed = int(body.get("speed") or 0)
    pitch_pct = int(body.get("pitch") or 0)
    rate = f"{speed:+d}%"
    pitch = f"{max(-100, min(100, pitch_pct)):+d}Hz"

    _cleanup_old_sessions()
    sdir = _session_dir(x_session_id)
    item_id = uuid.uuid4().hex[:12]
    work = sdir / f"tmp-{item_id}"
    work.mkdir(exist_ok=True)
    segments = parse_segments(text)
    if not segments:
        raise HTTPException(400, "Nothing to synthesize")

    part_files, all_words, offset = [], [], 0.0
    try:
        for i, seg in enumerate(segments):
            part = work / f"part{i}.mp3"
            if seg["type"] == "silence":
                _silence_mp3(part, seg["ms"])
                offset += seg["ms"] / 1000
            else:
                audio, words = await asyncio.wait_for(
                    synth_segment(seg["text"], voice, rate, pitch), timeout=45)
                if not audio:
                    raise HTTPException(502, "Synthesis returned no audio")
                part.write_bytes(audio)
                dur = _probe_duration(part)
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
                for (s, e, w) in words:
                    all_words.append((offset + s, offset + e, w))
                offset += dur
            part_files.append(part)
    except HTTPException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        raise HTTPException(502, f"Synthesis failed: {type(e).__name__}: {e}")

    # Concat -> final mp3
    listfile = work / "list.txt"
    listfile.write_text("".join(f"file '{p.name}'\n" for p in part_files))
    final_mp3 = sdir / f"{item_id}.mp3"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
                    "-codec:a", "libmp3lame", "-b:a", "48k", str(final_mp3)],
                   check=True, capture_output=True)
    audio_name = f"{item_id}.mp3"
    if fmt == "wav":
        wav = sdir / f"{item_id}.wav"
        subprocess.run(["ffmpeg", "-y", "-i", str(final_mp3), str(wav)],
                       check=True, capture_output=True)
        audio_name = f"{item_id}.wav"
    (sdir / f"{item_id}.srt").write_text(build_subtitles(all_words, srt=True), encoding="utf-8")
    (sdir / f"{item_id}.vtt").write_text(build_subtitles(all_words, srt=False), encoding="utf-8")
    duration = _probe_duration(sdir / audio_name)
    snippet = re.sub(r"\s+", " ", BREAK_RE.sub(" ", text))[:120]
    meta = {"id": item_id, "voice": voice, "format": fmt, "duration": round(duration, 2),
            "snippet": snippet, "created": int(time.time()),
            "audio": f"/api/file/{audio_name}?item={item_id}",
            "audioName": audio_name,
            "srt": f"/api/file/{item_id}.srt", "vtt": f"/api/file/{item_id}.vtt"}
    (sdir / f"{item_id}.json").write_text(json.dumps(meta), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
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
