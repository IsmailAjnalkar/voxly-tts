# Competitor gap analysis — text-2-speech.com

Date: 2026-10-29. Source: each competitor's public text-to-speech landing page, fetched once (title, meta description, `h1`/`h2`, structured-data types); raw data in [`evidence/keywords.json`](evidence/keywords.json). No traffic, ranking or backlink data was available (see the report's blockers), so this compares **positioning and on-page structure only**. Competitor claims are quoted from their own pages and were not independently tested.

## What each page leads with

| Competitor | Title / positioning (their words) | Page structure seen | Structured data |
|---|---|---|---|
| ElevenLabs (elevenlabs.io/text-to-speech) | "Text to Speech with Ultra-Realistic AI Voices Online"; "90+ languages" | 12 `h2`: model versions, emotion, use cases (agents, audiobooks), languages | Organization, SoftwareApplication, FAQPage, BreadcrumbList, AggregateRating, Offer |
| NaturalReader (naturalreaders.com/online) | "Free Text to Speech with Gemini and ChatGPT AI Voices"; reads PDFs, books, documents, webpages | App page, no `h2` | WebApplication, AggregateRating, Offer |
| TTSMaker (ttsmaker.com) | "Free Text to Speech Online" | Quick tutorial, usage scenarios, features, FAQs | none detected |
| Speechify (speechify.com/text-to-speech-online) | "Free Text to Speech with Lifelike AI Voices"; "free, no sign-up"; PDF upload | Use cases, FAQ | SoftwareApplication, FAQPage, Review, AggregateRating, Organization |
| Luvvoice (luvvoice.com) | "Free Convert Text to Speech Online, No Word Limit"; 70+ languages, 200 voices, MP3 | Features, languages and voices, testimonials | FAQPage, Organization, WebSite |
| TTSFree (ttsfree.com) | "Free Text to Speech Online"; "140+ languages"; MP3 | Converter, language/voice lists, pricing, how it works | FAQPage, Organization |

## Where Text 2 Speech is ahead (verifiable)
- **Subtitles:** SRT and VTT with word-level timing on every generation. None of the six pages above leads with subtitle files. The 19 subtitle-related autocomplete queries ("ai text to speech with subtitles", "srt text file download") map to `/guides/subtitles.html`.
- **No account and no paid tier:** the converter, downloads and subtitles are free without sign-up, and the privacy policy names the speech provider and retention.
- **25 fully server-rendered interface languages**, each with its own canonical URL and hreflang. Most competitor converter pages are English-first.
- **Documented limits** (5,000 characters, pause limits, rate limit) and measured format data, which answer engines can quote.

## Gaps (and what to do about each, honestly)

| Gap | Evidence | Action | Status |
|---|---|---|---|
| No per-language voice pages ("text to speech in spanish", "indian voice", "british") | 24 language/accent queries; TTSFree and Luvvoice list voices by language | `/voices.html` lists every voice by language. Next: per-language landing pages **only** for languages with real depth (e.g. English, Spanish, Arabic, Hindi), each with voice samples and region notes | Data page done; landing pages in roadmap |
| No comparison content | "text to speech vs", "best text to speech", brand queries (58) | One honest comparison page, built from features tested on a dated day and sourced to each competitor's own pricing page; no unverifiable claims | Roadmap weeks 5–6 |
| No document/PDF or web-page reading | NaturalReader and Speechify lead with PDFs | Not a product capability; do not target "pdf reader" keywords. Consider the feature separately | Product decision |
| "No word limit" positioning (Luvvoice) | 75 "free/unlimited" queries | Do not claim "unlimited": the limit is 5,000 per generation. Answer it plainly (FAQ) and explain chapter-by-chapter generation | Done (FAQ, how-it-works) |
| Ratings and reviews in structured data | ElevenLabs, NaturalReader, Speechify | Only with genuine, verifiable reviews collected from users. Never invent them | Not applicable now |
| Model/voice-quality storytelling | ElevenLabs "emotionally aware", model versions | Explain the actual engine plainly (Microsoft neural voices) and let samples speak; avoid superlatives | Done (how-it-works) |
| Character / novelty voices | 21 queries (yoda, robot, character voices) | Not supported; do not target | — |
| Devices, apps, extensions | 71 queries (iPhone, Chrome extension, Google Docs) | The site works in any modern browser; answer "does it work on iPhone/Android" in the FAQ, but do not claim an app or extension | Roadmap (FAQ additions) |
