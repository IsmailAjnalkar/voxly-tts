"""WER of audio files against one reference text. Usage: python wer_file.py TEXT_FILE AUDIO...
PyAV is blocked by Application Control on the audit host, so `av` is stubbed and ffmpeg decodes."""
import re, subprocess, sys, types, unicodedata
sys.modules["av"] = types.ModuleType("av")
sys.stdout.reconfigure(encoding="utf-8")
import jiwer
import numpy as np
from faster_whisper import WhisperModel


def norm(s):
    s = re.sub(r"[^\w\s]", " ", unicodedata.normalize("NFKC", s).lower())
    return re.sub(r"\s+", " ", s).strip()


ref = norm(open(sys.argv[1], encoding="utf-8").read())
model = WhisperModel("small", device="cpu", compute_type="int8")
for f in sys.argv[2:]:
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = model.transcribe(np.frombuffer(pcm, np.int16).astype(np.float32) / 32768, language="en",
                               condition_on_previous_text=False)
    hyp = norm(" ".join(s.text for s in segs))
    o = jiwer.process_words(ref, hyp)
    print(f"{f.split('/')[-1].split(chr(92))[-1]}: WER {o.wer:.3f}  ref {len(ref.split())} words, "
          f"hyp {len(hyp.split())}, deletions {o.deletions}, insertions {o.insertions}, substitutions {o.substitutions}")
