"""WER/CER of generated audio via faster-whisper. Usage: python wer.py RESULTS_DIR
PyAV is blocked by Application Control on this host, so audio is decoded with
the ffmpeg CLI and `av` is stubbed before faster_whisper is imported."""
import json, os, re, subprocess, sys, types, unicodedata
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.modules["av"] = types.ModuleType("av")
import numpy as np
from faster_whisper import WhisperModel
import jiwer

D = sys.argv[1]
R = json.load(open(os.path.join(D, "results.json"), encoding="utf-8"))
model = WhisperModel(os.environ.get("WHISPER", "small"), device="cpu", compute_type="int8")


def load(path):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1",
                          "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0


def norm(s):
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"\[break:[^\]]*\]", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


CJK = {"zh", "ja", "ko", "th"}
rows = []
for r in R:
    if "file" not in r or r["case"] in ("one char",):
        continue
    lang = r["voice"].split("-")[0]
    segs, info = model.transcribe(load(r["file"]), language=lang, beam_size=5)
    hyp = " ".join(s.text for s in segs)
    ref_n, hyp_n = norm(r["text"]), norm(hyp)
    cer = jiwer.cer(ref_n.replace(" ", ""), hyp_n.replace(" ", "")) if ref_n else None
    wer = None if lang in CJK else (jiwer.wer(ref_n, hyp_n) if ref_n else None)
    dur = r["probe"]["format"]["duration"]
    rows.append({"case": r["case"], "voice": r["voice"], "wer": wer, "cer": cer,
                 "rtf": round(r["latency_s"] / float(dur), 3), "ref": r["text"][:90], "hyp": hyp.strip()[:90]})
    print(f"{r['case'][:30]:30s} WER={wer if wer is None else round(wer,3)} CER={round(cer,3)} RTF={rows[-1]['rtf']} | {hyp.strip()[:80]}")
json.dump(rows, open(os.path.join(D, "wer.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
