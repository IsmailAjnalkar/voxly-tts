"""Non-destructive API probe. Usage: python api_probe.py BASE_URL OUTDIR
Sends a bounded set of requests (~35) and writes results.json + audio files."""
import json, os, subprocess, sys, time, uuid, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE, OUT = sys.argv[1].rstrip("/"), sys.argv[2]
os.makedirs(OUT, exist_ok=True)
SID = "audit" + uuid.uuid4().hex
results = []


def req(method, path, body=None, headers=None, raw=None, sid=SID):
    h = {"Content-Type": "application/json"}
    if sid is not None:
        h["X-Session-Id"] = sid
    h.update(headers or {})
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    t = time.time()
    try:
        with urllib.request.urlopen(r, timeout=300) as resp:
            content, code, ctype = resp.read(), resp.status, resp.headers.get("content-type", "")
    except urllib.error.HTTPError as e:
        content, code, ctype = e.read(), e.code, e.headers.get("content-type", "")
    return code, ctype, content, round(time.time() - t, 3)


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration,format_name,bit_rate:stream=codec_name,sample_rate,channels",
                        "-of", "json", path], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"error": r.stderr[:200]}


def record(case, code, ctype, content, dt, expect=None, extra=None):
    try:
        body = json.loads(content)
    except Exception:
        body = content[:200].decode("utf-8", "replace")
    row = {"case": case, "status": code, "ctype": ctype, "latency_s": dt, "body": body}
    if expect is not None:
        row["expected"] = expect
        row["verdict"] = "PASS" if code == expect else "FAIL"
    row.update(extra or {})
    results.append(row)
    print(f"{case:45s} {code} {dt:6.2f}s {row.get('verdict','')} {str(body)[:110]}")
    return body


def tts(case, text, voice="en-US-AriaNeural", fmt="mp3", expect=200, save=None, **kw):
    body = {"text": text, "voice": voice, "format": fmt, **kw}
    code, ctype, content, dt = req("POST", "/api/tts", body)
    meta = record(case, code, ctype, content, dt, expect, {"chars": len(text)})
    if code == 200 and save:
        c2, ct2, audio, dt2 = req("GET", meta["audio"] + "&s=" + SID, sid=None)
        p = os.path.join(OUT, save + "." + meta["format"])
        open(p, "wb").write(audio)
        srt = req("GET", meta["srt"] + "?s=" + SID, sid=None)[2].decode("utf-8", "replace")
        open(os.path.join(OUT, save + ".srt"), "w", encoding="utf-8").write(srt)
        results[-1].update(download_status=c2, download_ctype=ct2, bytes=len(audio),
                           download_s=dt2, probe=probe(p), file=p, text=text, voice=voice)
    return meta


# --- validation / negative cases ---
tts("empty text", "", expect=400)
tts("whitespace-only text", "   \n\t ", expect=400)
tts("unknown voice", "hello", voice="xx-XX-FakeNeural", expect=400)
tts("missing voice", "hello", voice="", expect=400)
tts("bad format ogg", "hello", fmt="ogg", expect=400)
tts("only break markers", "[break:1s][break:2s]", expect=400)
code, ct, c, dt = req("POST", "/api/tts", {"text": "hi", "voice": "en-US-AriaNeural"}, sid="")
record("missing session id", code, ct, c, dt, 400)
code, ct, c, dt = req("POST", "/api/tts", raw=b"{not json")
record("malformed JSON (expect 4xx)", code, ct, c, dt, 422)
code, ct, c, dt = req("POST", "/api/tts", raw=b"[1,2,3]")
record("JSON array body (expect 4xx)", code, ct, c, dt, 422)
tts("speed non-numeric (expect 4xx)", "hello", speed="fast", expect=422)
tts("speed out of range 1000 (expect 4xx/clamp)", "hello", speed=1000, expect=400)
tts("speed float 10.5", "hello", speed=10.5, expect=200)

# --- positive cases ---
tts("one char", "a", save="one_char")
tts("one word", "Hello", save="one_word")
para = ("The quick brown fox jumps over the lazy dog. Speech synthesis converts written "
        "text into spoken audio, and this paragraph checks a normal length request.")
tts("paragraph mp3", para, save="para_en")
tts("paragraph wav", para, fmt="wav", save="para_en_wav")
tts("html/js-looking text", "<script>alert(1)</script> <b>bold</b> & done", save="htmljs")
tts("emoji + unicode", "Café déjà vu 😀 naïve — “quotes” ½", save="unicode")
tts("numbers/currency/dates", "On 03/14/2026 I paid $1,234.56 and €99 at 7:45 PM, about 12% more. Dr. Smith, NASA and the FBI agreed.", save="numbers")
tts("break markers", "First sentence. [break:2s] Second sentence. [break:500ms] Third.", save="breaks")
tts("speed+50 pitch-20", para, speed=50, pitch=-20, save="prosody")
tts("1001 chars", ("Testing length boundaries. " * 40)[:1001], save="len1001")

# --- languages ---
LANG = {
    "en": ("en-US-AriaNeural", "Good morning. The weather is pleasant today."),
    "hi": ("hi-IN-SwaraNeural", "सुप्रभात। आज मौसम बहुत सुहावना है।"),
    "te": ("te-IN-ShrutiNeural", "శుభోదయం. ఈ రోజు వాతావరణం చాలా బాగుంది."),
    "ar": ("ar-SA-ZariyahNeural", "صباح الخير. الطقس جميل اليوم."),
    "es": ("es-ES-ElviraNeural", "Buenos días. Hoy hace muy buen tiempo."),
    "fr": ("fr-FR-DeniseNeural", "Bonjour. Il fait très beau aujourd'hui."),
    "de": ("de-DE-KatjaNeural", "Guten Morgen. Das Wetter ist heute schön."),
    "zh": ("zh-CN-XiaoxiaoNeural", "早上好。今天天气很好。"),
    "ja": ("ja-JP-NanamiNeural", "おはようございます。今日はいい天気です。"),
    "ko": ("ko-KR-SunHiNeural", "좋은 아침입니다. 오늘 날씨가 좋네요."),
    "he": ("he-IL-HilaNeural", "בוקר טוב. מזג האוויר נעים היום."),
    "ru": ("ru-RU-SvetlanaNeural", "Доброе утро. Сегодня хорошая погода."),
}
for lang, (voice, text) in LANG.items():
    tts(f"lang {lang} {voice}", text, voice=voice, save=f"lang_{lang}")
tts("mismatch: hindi text on en voice", LANG["hi"][1], voice="en-US-AriaNeural", save="mismatch_hi_en")

# --- files / isolation ---
meta = tts("item for isolation tests", "Isolation check.", save="iso")
if isinstance(meta, dict) and "id" in meta:
    name = meta["audioName"]
    code, ct, c, dt = req("GET", f"/api/file/{name}", sid="someotherSession123")
    record("other session cannot read file", code, ct, c, dt, 404)
    code, ct, c, dt = req("GET", f"/api/file/..%2f..%2fserver.py", sid=SID)
    record("path traversal encoded", code, ct, c, dt, 404)
    code, ct, c, dt = req("GET", f"/api/file/{meta['id']}.json", sid=SID)
    record("own metadata json readable", code, ct, c, dt, 200)
    code, ct, c, dt = req("DELETE", f"/api/items/{meta['id']}")
    record("delete item", code, ct, c, dt, 200)
    code, ct, c, dt = req("GET", f"/api/file/{name}", sid=SID)
    record("file gone after delete", code, ct, c, dt, 404)
code, ct, c, dt = req("DELETE", "/api/items/doesnotexist")
record("delete nonexistent (idempotent)", code, ct, c, dt, 200)
code, ct, c, dt = req("GET", "/api/file/x.mp3", sid=None)
record("file without session", code, ct, c, dt, 400)

json.dump(results, open(os.path.join(OUT, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("TOTAL", len(results), "PASS", sum(r.get("verdict") == "PASS" for r in results),
      "FAIL", sum(r.get("verdict") == "FAIL" for r in results))
