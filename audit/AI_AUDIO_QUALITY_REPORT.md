# AI Audio Quality Report — text-2-speech.com

Date: 2026-10-28 · Engine: Microsoft Edge neural voices via `edge-tts` 7.3.1 · Audio fetched from **production**.

## Method — what was and wasn't done
- **Automated proxy metrics only.** Every file was decoded with `ffprobe`, level-checked with `ffmpeg volumedetect`/`silencedetect`, and transcribed with an independent STT model (faster-whisper `small`, int8, CPU). WER and CER come from `jiwer` after Unicode NFKC normalisation, lower-casing and punctuation stripping.
- **No human listening was performed.** Naturalness, prosody and accent quality were **NOT TESTED** subjectively. Whisper WER is a proxy for intelligibility and carries its own errors, especially for Telugu, Arabic and number formats.
- Corpus: 12 language samples (one sentence pair each), plus English edge cases (numbers, unicode/emoji, HTML-like text, break markers, prosody, 1,001 characters).

## Integrity (all 23 production files)

| Check | Result |
|---|---|
| Decodes | 23/23. MP3: mp3, 24 kHz, mono, ~48 kbps. WAV: pcm_s16le, 24 kHz, mono |
| Metadata duration = decoded duration | 23/23 identical to 2 decimals |
| Clipping | None. Peaks −1.6 to −5.2 dBFS; mean −21.7 to −25.0 dB |
| Empty/silent output | None for text input. Break-only input deliberately yields 3.0 s of silence (BUG-009) |
| Long-text continuity (1,001 chars = 37 repeated sentences) | 38 pause gaps detected, consistent with 37 sentences. Whisper collapsed the repeated sentences (6 of 37 transcribed), a known STT repetition artefact, so this proxy is **inconclusive**. Duration (91.3 s) is consistent with complete speech. |

## Language matrix (production)

| Lang | Voice | Gen latency | Duration | WER | CER | Verdict | Notes |
|---|---|---:|---:|---:|---:|---|---|
| en | en-US-AriaNeural | 0.68 s | 4.08 s | 0.00 | 0.00 | PASS | |
| hi | hi-IN-SwaraNeural | 0.58 s | 5.02 s | 0.08 | 0.06 | PASS | STT spelling variants (सुप्रभाद / मोसम) |
| te | te-IN-ShrutiNeural | 1.83 s | 4.32 s | (1.07) | (1.18) | PASS* | Whisper wrote Devanagari, but the transcription is phonetically the source ("subhodayam … roju vatavaranam chala bagundi"). The high score is an STT script artefact. |
| ar | ar-SA-ZariyahNeural | 1.57 s | 4.56 s | 0.20 | 0.13 | PASS | One word (الطقس) misheard by STT |
| es | es-ES-ElviraNeural | 0.82 s | 4.34 s | 0.00 | 0.00 | PASS | |
| fr | fr-FR-DeniseNeural | 0.82 s | 3.98 s | 0.00 | 0.00 | PASS | |
| de | de-DE-KatjaNeural | 1.19 s | 4.39 s | 0.00 | 0.00 | PASS | |
| zh | zh-CN-XiaoxiaoNeural | 0.74 s | 3.29 s | n/a | 0.11 | PASS | STT output in Traditional script |
| ja | ja-JP-NanamiNeural | 1.43 s | 4.49 s | n/a | 0.06 | PASS | いい→良い (orthographic) |
| ko | ko-KR-SunHiNeural | 1.04 s | 4.58 s | n/a | 0.00 | PASS | |
| he | he-IL-HilaNeural | 2.06 s | 4.42 s | 0.00 | 0.00 | PASS | RTL |
| ru | ru-RU-SvetlanaNeural | 5.66 s | 4.85 s | 0.00 | 0.00 | PASS | slowest request in the run |

*Telugu verdict rests on phonetic reading of the STT output, not on the numeric WER.

Not exercised: 308 of the 322 voices, including the multilingual and dialect voices. Language matrix coverage is 12 of 75 languages.

## English edge cases

| Case | STT transcript (production audio) | Verdict |
|---|---|---|
| Numbers/dates/currency/acronyms: `On 03/14/2026 I paid $1,234.56 and €99 at 7:45 PM, about 12% more. Dr. Smith, NASA and the FBI agreed.` | "On March 14, 2026 I paid $1,234.56 and 99 euros at 7.45 p.m., about 12% more. Dr. Smith, NASA and the FBI agreed." | PASS. Normalised correctly. The WER of 0.16 comes only from written-form differences. |
| Unicode/emoji: `Café déjà vu 😀 naïve — “quotes” ½` | "Café Déjà vu grinning face naive, quotes one-half." | PASS for pronunciation. The emoji is spoken as "grinning face", which contradicts the FAQ's "special symbols are cleaned up automatically" (BUG-015). |
| HTML-looking: `<script>alert(1)</script> <b>bold</b> & done` | "script alert 1 slash script be bold slash be and done" | Safe (no injection). Tags are read aloud, which is literal but unhelpful. |
| Break markers `[break:2s]`, `[break:500ms]` | Text correct; SRT gaps exactly 2.000 s and 0.500 s | PASS |
| Speed +50 %, pitch −20 | 11.06 s → 7.39 s (0.67×), WER 0 | PASS |
| Hindi text on an English voice | **No audio**: HTTP 502 `NoAudioReceived` | FAIL. There is no fallback and the error is misleading (BUG-007). |

## Subtitles (SRT/VTT)
- Advertised as "built from the engine's word-level timings" (FAQ, README, llms.txt).
- **Actual:** edge-tts 7.3.1 defaults to `boundary="SentenceBoundary"`. A direct stream inspection returned `{'audio': 49, 'SentenceBoundary': 2}` with no `WordBoundary` events. `server.py:192` only consumes `WordBoundary`, so every cue time is a **character-proportional estimate** (server.py:239-249).
- Evidence (`evidence/subtitles/para_en.srt`): the last cue ends at exactly 11.064 s, the full file duration including trailing silence, and boundaries track character counts. On real narration the estimate drifts most around commas and numbers.
- BUG-005 (P2). The fix is one keyword argument, plus consuming the events.

## Generation latency / real-time factor
Median latency 0.91 s; median RTF 0.206 (≈5× faster than real time); worst RTF 1.17 (the Russian outlier). Provider failure rate on valid input: 0 of 23.

## Provider fallback
None. A single provider is used, with no retry, no alternative voice and no secondary engine. Provider outage behaviour was not testable in production (NOT TESTED).

## Reproduce
```
python -I audit/scripts/api_probe.py https://text-2-speech.com OUT/
<venv-with-faster-whisper>/python -I audit/scripts/wer.py OUT/      # writes OUT/wer.json
<venv>/python -I audit/scripts/acr.py OUT/numbers.mp3 OUT/unicode.mp3 OUT/htmljs.mp3
ffmpeg -i OUT/len1001.mp3 -af silencedetect=n=-40dB:d=0.25 -f null -
```
(On this host PyAV is blocked by Windows Application Control, so `wer.py` stubs `av` and decodes with the ffmpeg CLI.)
