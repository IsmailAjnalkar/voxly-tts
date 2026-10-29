import sys, types, subprocess
sys.modules["av"] = types.ModuleType("av"); sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
for f in sys.argv[1:]:
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"], capture_output=True).stdout
    segs, _ = m.transcribe(np.frombuffer(pcm, np.int16).astype(np.float32) / 32768, language="en")
    print(f.split("/")[-1], "=>", " ".join(s.text for s in segs))
