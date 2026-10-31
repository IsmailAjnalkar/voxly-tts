# Keyword strategy: intent → canonical page

Source: [`audit/seo/KEYWORD_MATRIX.csv`](../../audit/seo/KEYWORD_MATRIX.csv). It holds 513 real Google Autocomplete queries (en, US, 2026-10-29) in 13 clusters. **Search volumes and difficulty are `n/a`**: Ahrefs and Semrush had no API access on this account. Query counts below are numbers of distinct autocomplete phrasings, **not demand**. Re-prioritise with Search Console query data once it exists (`OWNER_ACTION_LIST.md`).

New pages are as planned in this PR (Agent 2): `/about.html`, `/help.html`, `/guides/text-to-mp3.html`, `/guides/ai-voiceover.html`, `/guides/choose-voice.html`. The lead must update this file if the final slugs differ.

## 1. Cluster → intent → canonical page

| Cluster (phrasings) | Intent | Product fit | Canonical page | Example queries | Notes |
|---|---|---|---|---|---|
| General text to speech (131) | Transactional | Supported | `/` (+ 24 language homes) | "text to speech converter", "online speech generator" | The tool is the answer. Some phrasings in this cluster are off-topic ("online sound generator hz", "text to speech calculator"): not targeted |
| Free, no sign-up, limits (75) | Transactional | Supported (5,000 chars per generation; free; no account) | `/` | "free text to speech", "free ai voice generator without login" | Answer "unlimited" honestly on `/help.html` (see §3) |
| AI voice generator (21) | Commercial | Supported (Microsoft neural voices) | `/` | "natural text to speech", "online voice generator ai" | Home title already carries "Natural AI Voices" |
| Formats & downloads: "text to mp3" subset (24) | Transactional → how-to | Supported | **Tool intent**: `/`. **How-to intent**: `/guides/text-to-mp3.html` | "text to mp3 converter free" → `/`; "how to convert text to mp3", "text to mp3 download" → guide | See cannibalization C-1 |
| Formats & downloads: rest (27) | Transactional / informational | Supported | `/`; `/guides/mp3-vs-wav.html` for format choice | "convert text to audio file", "mp3 or wav" | "convert text to audiobook" → only "chapter by chapter, 5,000 chars each" (help); no audiobook landing page |
| Subtitles & captions (19) | Transactional | Supported (SRT + VTT, word timings) | `/guides/subtitles.html` | "create srt from text", "text to speech with subtitles" | The strongest differentiator (`audit/seo/COMPETITOR_GAP_ANALYSIS.md`). Off-topic: "srt textile", "srt text editor" |
| Narration & voiceover (15) + voiceover phrasings in "Free…" | Commercial / how-to | Supported | **Workflow**: `/guides/ai-voiceover.html`. **Product walkthrough**: `/tutorial.html` | "create voiceover from text", "video narration generator", "text to speech used in youtube videos" | See cannibalization C-2 |
| Languages & accents (24) | Transactional | Supported where the language exists (75 languages) | `/voices.html` (inventory) + `/guides/choose-voice.html` (how to pick) | "text to speech hindi", "british accent", "indian voice" | See C-3. The live catalog on 2026-10-31 (142 locales) has en-GB, en-IN, hi-IN, ja-JP, ko-KR and 22 Spanish locales. It has **no** Jamaican English (en-JM) and **no** Haitian Creole (ht): those are not targeted. Re-check the catalog before claiming any accent |
| Questions & how-to (18) | Informational | Answerable | `/how-it-works.html` (how the product works); `/help.html` (product Q&A) | "how to text to speech", "is text to speech ai" | General questions about other apps (Clipchamp, Filmora, Python) are not targeted |
| Devices, apps & extensions (71) | Informational | **Partial**: any modern browser, including mobile; no app, extension or PDF reader | `/help.html` ("Does it work on iPhone/Android?") | "how to text to speech iphone", "free text to speech website" | Answer truthfully. Do not target "app", "extension", "pdf reader" as landing intents |
| Reader / read aloud (7) | Transactional | Partial: paste text, or import .txt/.md; no web-page or PDF reading | `/` (paste-and-listen) + `/help.html` answer | "read text aloud online" | "text to speech vs screen reader" → one help answer |
| Best / comparisons (2) | Commercial | Comparison content only | none in this PR; possible honest comparison page later (content plan) | "best text to speech" | Needs dated, sourced competitor facts |
| Competitors & other brands (58) | Navigational | Not targetable | none | "capcut text to speech", "text to speech discord" | Other brands' how-tos; not our product |
| Character & novelty voices (21) | Informational | **Not supported** | none | "text to speech characters", "robot voice", celebrity names | See §3 |
| Brand / entity | Navigational | — | `/about.html` | "text 2 speech", "text-2-speech.com" | Not in the autocomplete set; the About page exists for entity clarity (E1), not keyword reach |

Language homes (`/es/`, `/de/` …) target the same transactional intent as `/` in their own language. hreflang links them, which is localisation, not cannibalization ([Google: localized versions](https://developers.google.com/search/docs/specialty/international/localized-versions)).

## 2. Cannibalization check

| # | Pages that could compete | Shared intent | Resolution |
|---|---|---|---|
| C-1 | `/`, `/guides/text-to-mp3.html`, `/guides/mp3-vs-wav.html` | "text to mp3" | `/` owns **"text to mp3 converter (free/online)"** (tool intent). The guide owns **"how to convert text to MP3 / download MP3"**: its title starts with "How to", its first paragraph links to the converter, and it doesn't repeat "free text to mp3 converter" as its H1. `/guides/mp3-vs-wav.html` owns **format choice** ("mp3 vs wav"). The guide and mp3-vs-wav link to each other |
| C-2 | `/tutorial.html`, `/guides/ai-voiceover.html` | "create voiceover from text" | Tutorial = **product walkthrough** (first generation, pause markers, voice collection), translated in 25 languages. Guide = **end-to-end video workflow** (script → audio → SRT → editor), English. The guide's title and H1 carry "voiceover"; the tutorial's keep "Tutorial". Each links to the other once |
| C-3 | `/voices.html`, `/guides/choose-voice.html` | "text to speech [language/accent]" | `/voices.html` = **inventory** (every voice, live). The guide = **how to choose** (criteria, multilingual voices, testing with Preview) and links to `/voices.html` for the list. The guide gets no per-language headings that duplicate the inventory table |
| C-4 | `/help.html`, `/support.html`, home FAQ, `/how-it-works.html` | product questions | Home FAQ: 6 short answers (25 languages). `/support.html`: the same 6 plus the contact form (translated). `/help.html`: **the extended Q&A** that the FAQ doesn't cover (devices, offline, API, PDF, unlimited, commercial use), English. `/how-it-works.html`: architecture, limits table, data handling. **No question appears with a different answer on two pages**; reuse the same strings. Only one `FAQPage` block per question set (home); help carries no second `FAQPage` with duplicated Q&A |
| C-5 | `/about.html`, `/how-it-works.html` | "what is Text 2 Speech" | About = **who/why** (operator, purpose, contact, editorial policy). How-it-works = **how** (pipeline, limits). About links to how-it-works for the technical detail |
| C-6 | `/` and `/en/`, `/index.html`, `/es` | the same page | Already canonicalised (route map); R1 optional 301 for `/index.html` |

## 3. Queries we deliberately do not target

| Query group | Why not | What we do instead |
|---|---|---|
| Character, celebrity, novelty voices ("donald trump", "robot", "scary", "characters") | No such voices. Celebrity voice imitation also carries rights issues | Nothing. Never imply it |
| "Unlimited", "no word limit", "100 000 words" | False: 5,000 characters per generation | A `/help.html` answer: the limit, and that long texts are generated in parts |
| App, Chrome extension, Android/iPhone app, Google Docs/Word add-in | No app or extension exists | A help answer: works in mobile and desktop browsers; no install |
| PDF reader, web-page reader, "read this website" | No PDF or URL input (only .txt/.md/.text import) | A help answer; consider the feature as a product decision first |
| Other brands' how-tos (CapCut, Canva, Discord, TikTok, Clipchamp, Filmora) | Navigational to other products; we can't answer for them truthfully | None. A dated, sourced comparison page is possible later |
| Voice cloning, custom voices, emotion control, SSML styles, API access | Not offered (`/api/` is the site's own endpoint, not a documented API) | State it in How it works → "What it does not do" |
| "Offline text to speech" | Needs Microsoft's online service | A help answer: no |
| Off-topic phrasings caught by autocomplete ("online sound generator hz", "srt textile", "text to speech calculator") | Different meaning | None |
| Per-keyword doorway pages (e.g. one page per "text to speech in <language>") | Google [doorway abuse](https://developers.google.com/search/docs/essentials/spam-policies#doorways) | Language landing pages only where the catalog gives real, distinct content and a native reviewer exists (content plan) |
