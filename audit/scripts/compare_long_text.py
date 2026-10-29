"""LOCAL-ONLY: compare long-text generation between two local servers.
Usage: python compare_long_text.py TEXT_FILE OUTDIR http://127.0.0.1:8078=master http://127.0.0.1:8137=chunked [runs]"""
import json, os, subprocess, sys, time, urllib.error, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
text = open(sys.argv[1], encoding="utf-8").read()
out = sys.argv[2]
targets = [a.split("=") for a in sys.argv[3:5]]
runs = int(sys.argv[5]) if len(sys.argv) > 5 else 3
assert all("127.0.0.1" in u or "localhost" in u for u, _ in targets), "local only"
os.makedirs(out, exist_ok=True)
res = {name: [] for _, name in targets}
for run in range(runs):
    for url, name in targets:  # alternate so provider slow spells hit both
        req = urllib.request.Request(url + "/api/tts", method="POST",
                                     data=json.dumps({"text": text, "voice": "en-US-AriaNeural"}).encode(),
                                     headers={"Content-Type": "application/json", "X-Session-Id": "cmp" + name})
        t = time.time()
        try:
            meta = json.loads(urllib.request.urlopen(req, timeout=300).read())
            dt = round(time.time() - t, 1)
            f = os.path.join(out, f"{name}_{run}.mp3")
            data = urllib.request.urlopen(urllib.request.Request(
                url + meta["audio"] + "&s=cmp" + name)).read()
            open(f, "wb").write(data)
            res[name].append({"status": 200, "s": dt, "audio_s": meta["duration"], "file": f})
        except urllib.error.HTTPError as e:
            res[name].append({"status": e.code, "s": round(time.time() - t, 1), "detail": e.read()[:100].decode()})
        print(run, name, res[name][-1])
json.dump(res, open(os.path.join(out, "compare.json"), "w"), indent=1)
for name, rs in res.items():
    ok = [r["s"] for r in rs if r["status"] == 200]
    print(f"{name}: {len(ok)}/{len(rs)} ok, times {ok}")
