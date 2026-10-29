"""LOCAL-ONLY load test: N concurrent users each generating M short texts, while
polling /api/health and the server's memory. Usage:
  python load_test.py http://127.0.0.1:8137 SERVER_PID [users=10] [per_user=6]"""
import concurrent.futures as cf, json, statistics, subprocess, sys, threading, time, urllib.error, urllib.request, uuid
BASE, PID = sys.argv[1], sys.argv[2]
USERS = int(sys.argv[3]) if len(sys.argv) > 3 else 10
PER = int(sys.argv[4]) if len(sys.argv) > 4 else 6
assert "127.0.0.1" in BASE or "localhost" in BASE, "local only"
TEXT = "This is a load test sentence. It checks latency, errors and memory while several people generate at once."


def rss_mb():  # Windows tasklist: memory of the server process tree root
    out = subprocess.run(["tasklist", "/FI", f"PID eq {PID}", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    return round(int(out.split('","')[-1].strip().strip('"').replace(",", "").replace(" K", "").replace("\xa0", "")) / 1024, 1)


def user(_):
    sid, lat, errs = "load" + uuid.uuid4().hex, [], 0
    for _ in range(PER):
        r = urllib.request.Request(BASE + "/api/tts", method="POST", data=json.dumps({"text": TEXT, "voice": "en-US-AriaNeural"}).encode(),
                                   headers={"Content-Type": "application/json", "X-Session-Id": sid})
        t = time.time()
        try:
            urllib.request.urlopen(r, timeout=120).read()
            lat.append(time.time() - t)
        except urllib.error.HTTPError:
            errs += 1
    return lat, errs


health, stop = [], threading.Event()
def poll():
    while not stop.is_set():
        t = time.time(); urllib.request.urlopen(BASE + "/api/health").read(); health.append(time.time() - t); time.sleep(0.2)


m0 = rss_mb(); th = threading.Thread(target=poll); th.start(); t0 = time.time()
with cf.ThreadPoolExecutor(USERS) as ex:
    res = list(ex.map(user, range(USERS)))
wall = time.time() - t0; stop.set(); th.join(); m1 = rss_mb()
lat = sorted(x for l, _ in res for x in l); errs = sum(e for _, e in res)
p = lambda q: round(lat[min(len(lat) - 1, int(q * len(lat)))], 2)
print(json.dumps({"users": USERS, "requests": USERS * PER, "errors": errs, "wall_s": round(wall, 1),
                  "throughput_rps": round(len(lat) / wall, 2), "p50_s": p(.5), "p95_s": p(.95), "max_s": round(lat[-1], 2),
                  "health_p95_ms": round(sorted(health)[int(.95 * len(health))] * 1000), "health_max_ms": round(max(health) * 1000),
                  "rss_mb_before": m0, "rss_mb_after": m1}))
