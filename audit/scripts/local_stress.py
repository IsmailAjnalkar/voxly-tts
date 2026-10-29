"""LOCAL-ONLY robustness checks (never point at production). Usage: python local_stress.py http://127.0.0.1:8137 DATA_DIR"""
import concurrent.futures as cf, json, os, sys, threading, time, uuid, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE, DATA = sys.argv[1], sys.argv[2]
assert "127.0.0.1" in BASE or "localhost" in BASE, "local only"


def post(text, sid=None, voice="en-US-AriaNeural", timeout=600):
    body = json.dumps({"text": text, "voice": voice, "format": "mp3"}).encode()
    r = urllib.request.Request(BASE + "/api/tts", data=body, method="POST",
                               headers={"Content-Type": "application/json", "X-Session-Id": sid or "local" + uuid.uuid4().hex})
    t = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read()), round(time.time() - t, 2)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200].decode(), round(time.time() - t, 2)


def get(path, timeout=60):
    t = time.time()
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as resp:
            return resp.status, round(time.time() - t, 3)
    except urllib.error.HTTPError as e:
        return e.code, round(time.time() - t, 3)


out = {}
# 1. warm voice cache
print("warm", post("warm up"))

# 2. Break-marker amplification + event-loop blocking probe
health = []
stop = threading.Event()
def pinger():
    while not stop.is_set():
        health.append(get("/api/health")[1]); time.sleep(0.25)
th = threading.Thread(target=pinger); th.start()
amp = "[break:30s]" * 60 + " ok"
code, body, dt = post(amp)
stop.set(); th.join()
out["break_amplification"] = {"input_chars": len(amp), "status": code, "seconds": dt,
                              "audio_duration_s": body.get("duration") if isinstance(body, dict) else body}
out["health_latency_during_amp"] = {"n": len(health), "max_s": max(health), "median_s": sorted(health)[len(health)//2]}
print("amplification", out["break_amplification"], out["health_latency_during_amp"])

# 3. Oversized single input (no server-side limit)
for n in (20000, 60000):
    txt = ("This sentence is part of an oversized input test. " * (n // 50 + 1))[:n]
    code, body, dt = post(txt)
    out[f"large_{n}"] = {"status": code, "seconds": dt,
                         "result": body.get("duration") if isinstance(body, dict) else body}
    print(f"large {n}", out[f"large_{n}"])

# 4. Concurrency: 6 parallel short requests
para = "Concurrency check. The quick brown fox jumps over the lazy dog, twice over."
t0 = time.time()
with cf.ThreadPoolExecutor(6) as ex:
    res = list(ex.map(lambda _: post(para), range(6)))
out["concurrent_6"] = {"wall_s": round(time.time() - t0, 2), "statuses": [r[0] for r in res], "each_s": [r[2] for r in res]}
print("concurrent", out["concurrent_6"])

# 5. Unauthenticated directory creation via GET /api/file
before = len(os.listdir(DATA))
for _ in range(25):
    get(f"/api/file/x.mp3?s=junk{uuid.uuid4().hex}")
after = len(os.listdir(DATA))
out["dir_creation_by_get"] = {"before": before, "after": after, "created": after - before}
print("dirs", out["dir_creation_by_get"])

json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_stress.json"), "w"), indent=1)
