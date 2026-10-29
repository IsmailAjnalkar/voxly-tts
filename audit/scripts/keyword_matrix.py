"""Cluster the Google Autocomplete keywords into a matrix with intent, product fit and target page.
Usage: python keyword_matrix.py KEYWORDS.json OUT.csv
Rules are deliberately simple and visible; the first matching rule wins."""
import csv, json, re, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
src, out = sys.argv[1], sys.argv[2]
kws = sorted(json.load(open(src, encoding="utf-8"))["suggestions"])

LANG_WORDS = r"spanish|french|german|hindi|indian|british|australian|arabic|japanese|chinese|korean|russian|portuguese|italian|tamil|telugu|urdu|bahasa|indonesia|creole|jamaican|accent|filipino|tagalog|vietnamese|thai|turkish|dutch|polish|bengali|nepali|swahili|african|irish|scottish|welsh|language"
RULES = [  # (cluster, regex, intent, fit, target)
 ("Competitors & other brands", r"elevenlabs|quillbot|speechify|naturalreader|ttsmaker|luvvoice|\bgoogle\b|siri|alexa|adobe|microsoft|canva|capcut|tiktok|twitch|goanimate|xbox|discord|roblox|reddit|chatgpt|openai|\bllm\b|murf|play\.?ht|kinitopet|ultrakill",
  "Navigational", "Not targetable (other brands); comparison content only", "Future: honest comparison page"),
 ("Character & novelty voices", r"yoda|robot|character|funny|meme|eric|zesty|cartoon|celebrity|trump|anime|sound effect|producer tag|singing|rap|scary|spongebob|darth",
  "Informational", "Not supported (no character/celebrity voices)", "—"),
 ("Devices, apps & extensions", r"iphone|ipad|\bios\b|android|chrome|extension|linux|windows|\bmac\b|laptop|keyboard|shortcut|google docs|\bword\b|kindle|\bapp\b|software|pdf|website|qr code|on screen|accessibility setting",
  "Informational", "Partial: works in any modern browser; no app, extension or PDF reader", "/how-it-works.html"),
 ("Subtitles & captions", r"\bsrt\b|\bvtt\b|subtitle|caption",
  "Transactional", "Supported: SRT + VTT with word timing on every generation", "/guides/subtitles.html"),
 ("Formats & downloads", r"mp3|\bwav\b|download|\bfile\b|audio file|text to audio|to mp3",
  "Transactional", "Supported: MP3 or WAV download", "/ and /guides/mp3-vs-wav.html"),
 ("Languages & accents", LANG_WORDS,
  "Transactional", "Supported where the language exists (75 languages)", "/voices.html"),
 ("Free, no sign-up, limits", r"free|no sign ?up|without (?:login|sign)|no login|unlimited|no limit|no word limit",
  "Transactional", "Supported: free, no sign-up; 5,000 characters per generation (not unlimited)", "/"),
 ("Narration & voiceover", r"narrat|voice ?over|voiceover|dubbing|audiobook|podcast|video",
  "Commercial", "Supported: voiceovers with pauses and subtitles", "/tutorial.html"),
 ("AI voice generator", r"ai voice|voice generator|ai text to speech|neural|realistic|natural|human",
  "Commercial", "Supported: 300+ neural voices", "/"),
 ("Reader / read aloud", r"reader|read aloud|read text|reading",
  "Transactional", "Partial: reads pasted or imported .txt/.md text; no web-page or PDF reader", "/"),
 ("Questions & how-to", r"^(?:how|what|is|can|does|why|which)\b| vs |versus",
  "Informational", "Answerable in documentation/FAQ", "/how-it-works.html"),
 ("Best / comparisons", r"\bbest\b|\btop\b|alternative|compare",
  "Commercial", "Comparison content (honest, tested)", "Future: comparison page"),
]
rows, counts = [], collections.Counter()
for k in kws:
    for cluster, rx, intent, fit, target in RULES:
        if re.search(rx, k, re.I):
            break
    else:
        cluster, intent, fit, target = "General text to speech", "Transactional", "Supported", "/"
    counts[cluster] += 1
    rows.append({"keyword": k, "cluster": cluster, "intent": intent, "product_fit": fit, "target_page": target,
                 "evidence": "Google Autocomplete (en, US), 2026-10-29",
                 "monthly_volume": "n/a (no keyword-data API access)", "difficulty": "n/a"})
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print(len(rows), "keywords")
for c, n in counts.most_common():
    print(f"  {n:4d}  {c}")
