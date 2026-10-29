"""End-to-end check of the reported voices through the app (LOCAL server)."""
import json, sys, time, urllib.error, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
BASE = sys.argv[1]
assert "127.0.0.1" in BASE


def post(voice, text):
    r = urllib.request.Request(BASE + "/api/tts", method="POST", data=json.dumps({"text": text, "voice": voice}).encode(),
                               headers={"Content-Type": "application/json", "X-Session-Id": "voicecheck"})
    try:
        return 200, json.loads(urllib.request.urlopen(r, timeout=120).read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# wait for the startup sweep to hide dead voices
for _ in range(60):
    cat = json.loads(urllib.request.urlopen(BASE + "/api/voices").read())
    if cat["count"] < 322:
        break
    time.sleep(2)
ids = {v["id"] for v in cat["voices"]}
print(f"catalog after sweep: {cat['count']} voices, {len(cat['languages'])} languages")

REPORTED = {
    "ar-SY-AmanyNeural": "صباح الخير.", "cs-CZ-VlastaNeural": "Dobré ráno.", "en-ZA-LeahNeural": "Good morning.",
    "en-SG-WayneNeural": "Good morning.", "fr-FR-EloiseNeural": "Bonjour.", "iu-Cans-CA-SiqiniqNeural": "ᐅᓪᓛᒃᑯᑦ ᐊᐃᖓᐃ.",
    "iu-Latn-CA-SiqiniqNeural": "Ullaakkut ainngai.", "iu-Cans-CA-TaqqiqNeural": "ᐅᓪᓛᒃᑯᑦ ᐊᐃᖓᐃ.",
    "iu-Latn-CA-TaqqiqNeural": "Ullaakkut ainngai.", "mn-MN-YesuiNeural": "Өглөөний мэнд.",
    "ta-SG-AnbuNeural": "காலை வணக்கம்.", "ta-LK-KumarNeural": "காலை வணக்கம்.", "ta-MY-SuryaNeural": "காலை வணக்கம்.",
    "ta-IN-ValluvarNeural": "காலை வணக்கம்.", "te-IN-MohanNeural": "శుభోదయం.", "sk-SK-LukasNeural": "Dobré ráno.",
}
for voice, text in REPORTED.items():
    code, body = post(voice, text)
    shown = "listed " if voice in ids else "HIDDEN "
    print(f"{voice:28s} {shown} -> {code} {body.get('duration', body.get('detail', ''))}")
print("control: Hindi text on Aria ->", *post("en-US-AriaNeural", "सुप्रभात। आज मौसम बहुत सुहावना है।"))
print("control: Tamil on Pallavi    ->", post("ta-IN-PallaviNeural", "காலை வணக்கம்.")[0])
