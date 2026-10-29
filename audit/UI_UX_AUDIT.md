# UI/UX & Accessibility Audit — text-2-speech.com

Date: 2026-10-28 · Chromium (Playwright) headless · axe-core 4.x with tags wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa.
Screenshots: [evidence/screenshots/](evidence/screenshots/). Automated findings and manual checks are reported separately below.

## Responsive sweep — home page

| Width | Horizontal overflow | Nav mode | Notes | Screenshot |
|---:|---|---|---|---|
| 320 | none | burger | Header language select clipped to "Er" (BUG-017) | home_320.png |
| 375 | none | burger | | home_375.png |
| 390 | none | burger | | home_390.png |
| 430 | none | burger | | home_430.png |
| 768 | none | burger | | home_768.png |
| 1024 | none | full nav | | home_1024.png |
| 1280 | none | full nav | Duplicate "Andrew - US" visible in the list | home_1280.png |
| 1440 | none | full nav | | home_1440.png |
| 1920 | none | full nav | | home_1920.png |

On every width, the fixed cookie banner covers the Output Format (MP3/WAV) buttons until it is dismissed. This is expected banner behaviour, but it hides a control on first visit.

## Page-by-page defects

| Page | Viewport | Element | Expected | Actual | Bug |
|---|---|---|---|---|---|
| All 6 sub-pages | all | header `.brand` | "Text 2 Speech" | "Voxly" | BUG-013 |
| /tutorial.html, /support.html (all sub-pages) | 320 px | header nav + `#sublang` | Wraps or collapses | Page scrollWidth 397 px; "Support" and the language switcher are off-screen | BUG-017 |
| / | 320 px | `#uilang` | Readable | Shows "Er" | BUG-017 |
| / | all | `#voicelist` | Unique labels | Andrew/Ava/Brian/Emma - US duplicated | BUG-012 |
| / | all | `#voicelist` (search "zzzz") | "No voices match" | Blank box | BUG-025 |
| / | all | `#counter` | 10 chars for "Hi 😀⏎line2" | 11 | BUG-024 |
| / | all | `#speed_num` / `#pitch_num` | Value shown = value sent | 33 → 35 sent; 150 shown, 100 sent | BUG-018 |
| / | all | `#genbtn` | Disabled while generating | Re-enabled by typing → duplicate job | BUG-006 |
| / | all | `#toast` (error) | Actionable message | Always appends "service may be unreachable…", even for validation errors | BUG-007 |
| / | all | `#resultlist` after reload | Session items still listed | Empty | BUG-022 |
| /es/, /de/ … | all | FAQ, steps, use cases | Localised | English | BUG-023 |
| /ar/, /fa/ | all | `<html dir>` | rtl | empty (sub-pages are correct) | BUG-023 |
| /auth, /support, /donate | all | primary buttons | Real action or hidden | `alert()` "opens with the public launch" | BUG-016 |
| / | all | Footer "Friend Links" | Real links or none | Single "Google" placeholder | BUG-029 |

Positive: clear two-column layout, strong visual hierarchy, loading state on Generate, disabled states on empty input, sensible default voice, and working mobile burger, theme persistence, FAQ and tabs.

## Accessibility — automated (axe-core)

| Page | Violations (impact, node count) |
|---|---|
| / (dark, default) | `nested-interactive` serious ×47 · `label` critical ×4 (`#speed`, `#speed_num`, `#pitch`, `#pitch_num`) · `color-contrast` serious ×6 (gender "All", `.badge`, format "MP3" …) · `target-size` serious ×6 (footer links) |
| / (light theme) | `color-contrast` serious ×**57** (nav, hero subtitle, buttons, hints) |
| /donate.html | `color-contrast` ×4 (Donate buttons) · `label` critical ×1 (amount input) |
| /support.html | `color-contrast` ×1 · `select-name` critical ×1 (topic select) |
| /auth.html | `color-contrast` ×1 |
| /tutorial.html, /privacy.html, /terms.html | 0 |

## Accessibility — manual / scripted checks

| Check (WCAG) | Result |
|---|---|
| 2.1.1 Keyboard (Level A): select a voice with Enter/Space | **FAIL.** Rows are `div role=button tabindex=0` with a click listener only (BUG-008) |
| 4.1.3 Status messages: generation errors and toasts announced | **FAIL.** `#toast` has no `role`/`aria-live` (BUG-011) |
| 1.3.1 / 4.1.2: the Gender label is not associated with its button group, and segmented buttons have no `aria-pressed` | FAIL (part of BUG-011) |
| Icon buttons (☾ ☰ 👤) accessible names | Weak. The names come from glyph content/`title`. Recommend `aria-label`. |
| 1.4.10 Reflow at 320 CSS px (≈400 % zoom of 1280) — home | PASS |
| 1.4.10 Reflow — sub-pages | FAIL (BUG-017) |
| 3.1.1 Language of page | PASS on all pages |
| Audio player | Native `<audio controls>`, keyboard-operable by the browser — PASS |
| 2.3.3 / prefers-reduced-motion | NOT TESTED |
| Screen-reader walkthrough (NVDA/VoiceOver) | NOT TESTED (no assistive technology available in this environment) |
| 200 % zoom on desktop | Not separately captured; covered indirectly by the 640–768 px sweep (no overflow) |

## Recommendations (UI)
1. Rebuild the voice list as an accessible radio group (fixes BUG-008 and the 47 nested-interactive nodes).
2. Darken accent tokens for the light theme; re-run axe until 0 contrast issues remain.
3. Make the sub-page header responsive (reuse the home burger) and fix the 320 px language select.
4. Fix the busy state, error copy, counter, empty state and duplicate labels (all small, local changes in `web/index.html`).
5. Hide the mock Account, Donate and Support actions until they work.
