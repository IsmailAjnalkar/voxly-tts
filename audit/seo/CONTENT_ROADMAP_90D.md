# 90-day organic growth roadmap — text-2-speech.com

Start: the week the `seo/aeo-geo` branch is deployed. Rules for every item: it targets a cluster in [`KEYWORD_MATRIX.csv`](KEYWORD_MATRIX.csv) whose product fit is "Supported" or "Partial"; it contains facts tested on the live product (date-stamped); **a person reviews it before it is published**; no doorway pages, no invented numbers, reviews or citations. Re-check search demand with Search Console data once it exists. Keyword volumes were not available for this plan (see the main report's blockers).

## Days 1–14: foundations (no new articles)
| Task | Output | Done when |
|---|---|---|
| Verify the deploy | Lighthouse and `seo_crawl.py` on production; Rich Results Test on 3 URLs | 0 crawl issues; Performance 100 or explained |
| Search Console + Bing Webmaster Tools | Sitemap submitted in both; URL Inspection of `/`, `/es/`, `/voices.html` | Sitemap processed; no coverage errors |
| Baseline dashboard | The views in `MONITORING_DASHBOARD_SPEC.md` | First weekly snapshot saved |
| FAQ additions (all 25 languages) | Answers for "does it work on iPhone/Android?", "can I use it offline?", "is there an API?" (each answered truthfully) | Reviewed translations live |

## Days 15–45: capability guides (one per week, English first)
| Week | Page | Cluster (matrix) | Source of facts |
|---|---|---|---|
| 3 | How to add pauses and pacing (break markers, punctuation) | Narration & voiceover | Generate examples; measure pause timing in the output |
| 4 | Video narration workflow: script → audio → subtitles → editor | Narration & voiceover, Subtitles | A real end-to-end test with a free editor |
| 5 | Choosing a voice: tips per language, multilingual voices | Languages & accents, AI voice generator | Generated samples, voice catalog |
| 6 | Honest comparison: Text 2 Speech and five alternatives | Best / comparisons | Each competitor's own pricing/limits page, quoted with the date; our tested features |

## Days 46–75: languages and accessibility
| Week | Page | Notes |
|---|---|---|
| 7–8 | Language landing pages for the deepest catalogs (e.g. English, Spanish, Arabic, Hindi): voices, regions, sample audio, tips | Only where the catalog gives real content; translated by a native speaker, not machine-only |
| 9 | Text to speech for learning and accessibility (listening while reading, dyslexia-friendly use) | Practical, no medical claims; cite reputable sources |
| 10 | Troubleshooting: no audio, wrong language, long text, flaky voices | From real support messages (support inbox) and the error messages in the app |

## Days 76–90: review and iterate
- Compare Search Console queries with the matrix; refresh titles and FAQ for queries with impressions but low CTR.
- Translate the best-performing guide into the top 3 interface languages by traffic (native review).
- Update `llms.txt` and the how-it-works page with any changed limits or features.
- Re-run Lighthouse, the crawl and the browser suite; publish a dated changelog of content changes.

## Not planned (and why)
Character/celebrity voice pages, "unlimited" claims, PDF or web-page reader pages, and app/extension pages target features the product does not have. Mass-generated pages per keyword are doorway pages.
