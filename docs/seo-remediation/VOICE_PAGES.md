# Per-language voice pages

`/voices/<slug>.html` for the ten languages below, rendered per request by `voice_pages.py`
from the live voice catalog (voices hidden by the 6-hourly health sweep are left out, as on
`/voices.html`). Tests: `tests/test_voice_pages.py`.

## Languages (live catalog, 31 October 2026: 322 voices)

| Page | Code | Voices | Variants | Multilingual | Why |
|---|---|---|---|---|---|
| /voices/english.html | en | 47 | 14 | 5 | most voices, largest demand |
| /voices/spanish.html | es | 45 | 22 | 0 | 2nd by voices |
| /voices/hindi.html | hi | 2 | 1 | 0 | search demand ("Hindi text to speech"), UI language |
| /voices/arabic.html | ar | 32 | 16 | 0 | 3rd by voices, UI language |
| /voices/french.html | fr | 13 | 4 | 2 | 5th by voices |
| /voices/german.html | de | 10 | 3 | 2 | 6th by voices |
| /voices/portuguese.html | pt | 5 | 2 | 1 | demand (Brazil), UI language |
| /voices/chinese.html | zh | 14 | 5 | 0 | 4th by voices, demand |
| /voices/japanese.html | ja | 2 | 1 | 0 | demand, UI language |
| /voices/indonesian.html | id | 2 | 1 | 0 | demand, UI language |

Tamil (8 voices) has more voices than Portuguese but far less search demand; it is a candidate for the next batch.

## What each page holds

- Title and description written per language, with no counts (counts change with the catalog, and the
  titles must stay valid when a voice is hidden). Title ≤ 70 columns, description 120–160 characters.
- H1 `<Language> text to speech voices`; visible breadcrumb Home › Voices & languages › Language;
  BreadcrumbList + CollectionPage JSON-LD (no ratings).
- Answer-first intro with the live count (female/male, variants), a link `Try <Language> voices in the
  free tool` to `/?vl=<code>`, the voice table (voice, region, locale, gender, multilingual), the
  regional variants from the catalog plus a written explanation, 4 language tips, a 5-step how-to,
  related pages (2 languages, /voices.html, /guides/choose-voice.html).
- If the catalog cannot be loaded the page says so (like /voices.html) and still answers 200.

## Sources for the tips

- Sentence ends (। ؟ 。！？ and . ! ?) used to split long text and end subtitle lines: `_SENTENCE` and
  `_SENTENCE_END` in server.py. A full stop after an abbreviation not in `_ABBREV` ends a subtitle line.
- 5,000-character limit (every character counts): `MAX_CHARS` and the `text` field in server.py.
- Pause markers, Ctrl+B, 25 markers / 60 s: help centre and `MAX_BREAKS` / `MAX_SILENCE_MS`.
- "An English voice returned no audio for Hindi text": the test recorded in /guides/choose-voice.html.
- The language facts (Spanish distinción/seseo, Swiss Standard German without ß, BR/PT vocabulary and
  spelling, Simplified/Traditional script, Cantonese vs Mandarin, Indonesian number format…) are general,
  checkable facts; anything about how a voice reads ambiguous input is phrased as "preview it".

## Content updates

Edit the entry in `LANGS` (voice_pages.py) and set `UPDATED` (also the sitemap lastmod and the page's
"Last updated"). `tests/test_voice_pages.py` fails on duplicated paragraphs across the pages, title/description
length, broken links and table rows that do not match the catalog.
