# Accessibility, semantic HTML and "preview" density — remediation report

Scope: SAGE findings Semantic HTML 63/100, Agent Accessibility 73/100, Keyword Density 75/100.
Measured on a local server (`uvicorn server:app --port 8801`, headless Chromium via Playwright,
axe-core tags wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa, plus best-practice run separately).
Pages: `/`, `/ar/`, `/es/` (1280 px; `/` and `/ar/` also 390 px and 320 px), `/tutorial.html`,
`/support.html`, `/terms.html`, `/donate.html`, `/auth.html`, `/privacy.html`, 404, `/ar/tutorial.html`,
`/ar/support.html` (320 px), `/tutorial.html` (320 px).

## Before / after

| Metric (rendered DOM, after the voice list loads) | Before | After |
|---|---|---|
| axe WCAG 2.0/2.1/2.2 A+AA violations, all 16 runs | 0 | 0 |
| axe best-practice, home | `landmark-one-main`, `region` ×118 | 0 |
| axe best-practice, sub-pages | 0 | 0 |
| axe with skip link focused, light and dark theme (`/`, `/ar/`, `/terms.html`) | — | 0 |
| `tabindex="-1"` on the home page | 47 (1 list container + 46 voice buttons) | 1 (Results heading, a real focus target) |
| `tabindex="-1"` on support page | 1 (honeypot) | 1 (kept, see below) |
| Controls with no accessible name (home) | 1 (`#fileinput`) | 0 |
| `<main>` on the home page | 0 | 1 (`<main id="main">`) |
| `<nav>` with a name | 0 of 2 | 2 of 2 (translated "Main menu"); breadcrumb nav already named |
| Skip link, first focusable element | none | every page (home + 7 sub-pages; generated pages once regenerated) |
| Live region for generation | `#toast` (role=alert) only | `#genstatus` (role=status, polite) + `#toast` alert for errors |
| Heading order (home) | one H1, no skipped levels | unchanged (one H1, no skips) |
| "preview" in visible body text (innerText), `/` | 50 / 663 words = **7.54 %** | 3 / 632 = **0.47 %** |
| "preview" in textContent (CSS ignored), `/` | 50 | 3 |
| Highest non-brand term on `/` (innerText) | preview 7.54 % | text / voice 1.90 % |
| Highest term on `/es/` | escuchar 7.00 % | voz 2.44 % |
| Highest term on `/ar/` | معاينة 7.14 % | الصوت 1.87 % |
| Horizontal overflow at 390 / 320 px (en, ar, sub-pages) | none | none |

The three remaining "preview" words are the main **Preview Audio** button and the "Preview or generate"
step tab (plus the step text), all describing the device-voice preview feature.

## What changed

### Skip link and landmarks (home + `tutorial`, `donate`, `support`, `auth`, `privacy`, `terms`, `not-found`)
- `<a class="skip-link" href="#main">` is the first child of `<header>` (so `tools/make_content_pages.py`,
  which copies `<header>…</header>` from `terms.html`, carries it to the generated pages). Off-screen until
  focused, then shown at the top start corner (`inset-inline-start`, so it sits on the right in Arabic/Persian).
- Home: `.wrap` and the How-it-works / Use-cases / FAQ sections are wrapped in `<main id="main">`; footer
  stays outside. Sub-pages: their existing `<main>` got `id="main"`. Exactly one `<main>` per page.
- Both header navs (desktop and mobile) are labelled by a hidden translated span (`#nav_lbl`, "Main menu").
  The mobile nav links were English on every language; they now carry `data-i18n`. Home link has
  `aria-current="page"`.
- Text: `skip` "Skip to main content" in all 25 languages (I18N object and `i18n-sub-parts/*.json`).

### Accessible names
Names come from visible or hidden **text with `data-i18n`**, so the server translates them in the HTML
(`_translate()` handles text, not attributes) and the client keeps them in sync.

| Control | Before | After |
|---|---|---|
| Interface language select | English `aria-label` on every language | `<label for>` (sr-only), translated |
| Theme button | "Toggle dark / light theme", English, no state | "Dark theme" + `aria-pressed`, translated; icon `aria-hidden` |
| Account link | English `aria-label` | sr-only translated text; icon `aria-hidden` |
| Burger | English `aria-label`; had `aria-expanded`/`aria-controls` | translated sr-only text; `aria-expanded` toggles, `aria-controls="mobilenav"` |
| Voice list | unlabeled `div tabindex=-1` | `role="radiogroup"` labelled "Choose a voice" (translated) |
| Per-voice sample button | text "Preview", name "Preview: Aria - US" | icon ▶, name "Play sample: Aria - US" (unique per voice), tooltip "Play sample" |
| Speed / pitch number boxes | "Speed" / "Pitch" (same as the slider) | "Speed %" / "Pitch Hz" (label + unit) |
| Import button / file input | input had no name | input labelled by the Import button, both described by "Plain text files: .txt, .md or .text" |
| Preview / Generate | name included "▶" / "⚡" | glyphs `aria-hidden`; `type="button"` |
| Step tabs | no state | `aria-pressed` |
| FAQ questions | no state; "▾" read out | `aria-expanded`; "▾" and use-case emoji `aria-hidden` (set by JS, see request below) |
| Audio player | unnamed | "Generated audio: Aria - US, 10:42:07" |
| Downloads | "⬇ MP3", "⬇ SRT", "⬇ VTT" (same for every item) | "Download audio (MP3) — Aria - US, 10:42:07", "Download subtitles (SRT) — …", "(VTT) — …" |
| Delete | "Delete" (same for every item) | "Delete: Aria - US, 10:42:07"; focus moves to the Results heading afterwards |
| Gender filter, format buttons | already `role=group` + `aria-pressed` | unchanged |

Visible text is always contained in the accessible name (WCAG 2.5.3). New strings (13 home, 5 sub-page)
are written for all 25 languages; `tools/merge_sub_i18n.py` validates 25 × 85 keys.

### `tabindex="-1"` audit (every occurrence)

| Pattern | Count before | Decision |
|---|---|---|
| `#voicelist` container `tabindex="-1"` | 1 | **Removed.** Nothing focuses it programmatically (no `.focus()` call in the code); leftover. |
| Per-voice Preview buttons, roving `tabindex="-1"` on every row but the selected one | 46 | **Removed.** Not focus targets; they only kept 46 buttons out of the Tab order. Replaced by CSS: on hover-capable devices the sample button of a non-selected row is `visibility:hidden` until the row is hovered, which also removes it from the Tab order and the accessibility tree. Keyboard / screen-reader users get the same flow as before (Tab → selected voice radio → arrows choose → Tab → its sample button), mouse users still sample any voice in one click without selecting it, touch screens (`hover:none`) show every row's button. |
| Results `<h2 id="results_h" tabindex="-1">` | 0 | **Added, legitimate.** Programmatic focus target after Delete removes the focused button, so keyboard focus is not lost to `<body>`. |
| Support form honeypot `<input name="website" tabindex="-1">` inside `<div hidden>` | 1 | **Kept.** Anti-spam honeypot; already hidden from everyone, the tabindex is a second guard if the container is ever un-hidden by CSS. |

### Live region
- `#genstatus` (`role="status"`, `aria-live="polite"`, visually hidden) inside the Results card says
  "Generating…" when Generate starts and "Audio ready: Aria - US, 0:02" when it finishes (translated).
- Errors keep using `#toast` (`role="alert"`); `toast()` clears the status line so the two never disagree.

### Focus visibility and the sticky header (WCAG 2.4.7, 2.4.11)
- `:focus-visible` ring: 3 px solid accent with 2 px offset everywhere; inputs/selects/textarea had
  `outline:none` (border colour only), they now get the same ring. The voice row keeps its `:focus-within` ring.
- `html{scroll-padding-top:96px}` (140 px under 440 px, where the sticky header wraps to two rows), so a
  focused element scrolled into view is never under the sticky header.

### Keyboard-only flow (Playwright, keyboard events only)
Script: `kbd_flow.mjs` (scratchpad). Run at 1280 px (with generation), 390 px (no generation) and 320 px (with generation): **all passed**.
1. First Tab → skip link, on screen; Enter → `#main`; next Tab lands inside `<main>`.
2. Tab order: donate links → voice language → gender ×3 → search → selected voice radio (ArrowDown picks the next voice) → **its one** sample button → speed checkbox (slider/number disabled until checked) → pitch checkbox → MP3/WAV → autoplay (Space toggles) → text area (typed) → Import → Preview Audio → Generate.
3. Every Tab stop showed a ≥2 px outline (or native media control ring); no stop was under the sticky header.
4. Enter on Generate → result appears; status says "Audio ready: Neerja - IN, 0:02".
5. Tab → audio player ("Generated audio: …"); Space starts playback; the native player has 6 internal stops (play, seek, volume, menu…), then Download MP3 (Enter → `.mp3` downloaded), SRT (Enter → `subtitles.srt`), VTT, Delete (Enter → item removed, focus on the Results heading).
6. 390 / 320 px: burger toggles `aria-expanded` and shows/hides the mobile nav.

Extra checks (`extra_checks.mjs`): one visible sample button at rest on desktop, hover reveals a row's
button, clicking it posts that voice to `/api/tts` without changing the selection, all 47 names unique;
touch context shows all buttons; skip link first, translated and on-screen at 320 px for `/ar/`,
`/ar/tutorial.html` (right edge, RTL), `/de/support.html`, `/terms.html`, 404, `/zh-CN/donate.html`;
header control names translated there; theme toggle flips `aria-pressed`.

## Regression results
- `pytest tests/test_api.py`: 54 passed, 1 failed — `test_seo_checks_pass` reports 14 broken links
  (`/help.html`, `/about.html`, `/guides/text-to-mp3.html`, …) from generated pages other agents are
  adding; none from files in this change. The suite now has 55 tests (other agents added some).
- `tests/lang_test.js`: 27 passed, 0 failed (25 existing + 2 new: translated skip link / `main#main` on `/es/`; German skip link, language label and nav label on `/de/tutorial.html`).
- `audit/scripts/verify_full.mjs`: 75 passed, ALL PASSED (includes "Tab from the selected voice reaches its Preview button").
- `audit/scripts/verify_ui.mjs`: 35 passed, 1 failed — "donate: notice shown, all 4 Donate buttons
  disabled", which tests the donate page from before commit 88cdfd4 (now 2 live buttons, no notice); fails on HEAD too, not from this change.
- `tools/merge_sub_i18n.py`: valid, 25 languages × 85 keys.

## Not done / notes
- Toast error messages (`"Generation failed: …"`, `"Too many requests…"` etc.) are English in every
  language. They were English before this change; translating them is a separate i18n task.
- The I18N key `preview` ("Preview") is no longer used by the page; left in place (harmless).
- Generated pages (`how-it-works`, `voices`, `guides/*`) get the skip link, nav label, `<main id="main">`
  and focus styles when `tools/make_content_pages.py` is re-run: it copies `<header>`, `<style>` and the
  `<main …>` tag from `terms.html`.
- Server-rendered FAQ (`<span>▾</span>`) and use-case emoji (`<div class="emo">`) are made `aria-hidden`
  by client JS; the same could be emitted directly by `server.py` `_home_content()`.
