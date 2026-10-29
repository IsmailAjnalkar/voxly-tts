import sys, types, subprocess
sys.modules["av"] = types.ModuleType("av")
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from faster_whisper import WhisperModel

f = sys.argv[1]
m = WhisperModel("small", device="cpu", compute_type="int8")
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"], capture_output=True).stdout
a = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
segs, _ = m.transcribe(a, language="en", condition_on_previous_text=False)
t = " ".join(s.text for s in segs).lower()
print("occurrences:", t.count("boundar"), "expected:", ("Testing length boundaries. " * 40)[:1001].lower().count("boundar"))
