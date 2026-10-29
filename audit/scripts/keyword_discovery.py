"""Keyword discovery from Google Autocomplete (real queries, no volumes) + competitor page metadata.
Usage: python keyword_discovery.py OUT.json"""
import html, json, re, string, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
OUT = sys.argv[1]
UA = {"User-Agent": "Mozilla/5.0 (keyword research)"}


def suggest(q):
    url = "https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q=" + urllib.parse.quote(q)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
            return json.loads(r.read().decode("utf-8", "replace"))[1]
    except Exception:
        return []


SEEDS = ["free text to speech", "text to speech online", "ai text to speech", "text to voice converter",
         "free ai voice generator", "natural text to speech", "text to speech mp3", "text to speech wav",
         "text to speech without signup", "text to speech with subtitles", "online voice generator",
         "convert text to audio", "narration generator"]
EXPAND = ["text to speech " + c for c in string.ascii_lowercase] + [
    "text to speech for", "text to speech in", "how to text to speech", "how to convert text to speech",
    "best text to speech", "is text to speech", "can text to speech", "text to speech vs", "text to speech that sounds",
    "srt from text", "text to mp3", "tts online", "tts free", "read text aloud", "voiceover from text"]
found = {}
for q in SEEDS + EXPAND:
    for s in suggest(q):
        found.setdefault(s.lower(), q)
    time.sleep(0.3)

COMP = {"ElevenLabs": "https://elevenlabs.io/text-to-speech", "NaturalReader": "https://www.naturalreaders.com/online/",
        "TTSMaker": "https://ttsmaker.com/", "Speechify": "https://speechify.com/text-to-speech-online/",
        "Luvvoice": "https://luvvoice.com/", "TTSFree": "https://ttsfree.com/"}
comp = {}
for name, url in COMP.items():
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            body = r.read().decode("utf-8", "replace")
        g = lambda p: (lambda m: html.unescape(m.group(1)).strip() if m else None)(re.search(p, body, re.S | re.I))
        comp[name] = {"url": url, "title": g(r"<title[^>]*>(.*?)</title>"), "description": g(r'<meta name="description" content="([^"]*)"'),
                      "h1": [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<h1[^>]*>(.*?)</h1>", body, re.S)][:2],
                      "h2": [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.S)][:12],
                      "jsonld": sorted({t for t in re.findall(r'"@type"\s*:\s*"([^"]+)"', body)}),
                      "faq_like": len(re.findall(r"\?</(?:h2|h3|summary|button)", body)), "bytes": len(body)}
    except Exception as e:
        comp[name] = {"url": url, "error": type(e).__name__}
json.dump({"suggestions": found, "competitors": comp}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(found), "unique suggestions")
for n, c in comp.items():
    print(n, "|", c.get("title") or c.get("error"), "| h2:", len(c.get("h2", [])), "| ld:", c.get("jsonld"))
