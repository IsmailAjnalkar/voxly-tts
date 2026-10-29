#!/usr/bin/env python3
"""Validate web/i18n-sub-parts/<code>.json (25 languages), which the server and
subi18n.js read directly: every language present, exactly the English key set, no empty
values, and HTML markup preserved in the three HTML strings."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PARTS = ROOT / "web" / "i18n-sub-parts"
CODES = ["en", "zh", "zh-TW", "ar", "cs", "da", "de", "es", "fa", "fr",
         "hi", "hu", "id", "it", "ja", "ko", "nl", "no", "pl", "pt",
         "ru", "sv", "th", "tr", "vi"]
HTML_KEYS = {"tut_g2p": ["<b>", "[break:200ms]", "[break:1s]", "[break:2s]",
                         "[break:500ms]", "Ctrl+B"],
             "sup_quick_p": ["<br>"],
             "priv_s4p": ['<a href="/support.html">', "</a>"]}

en = json.loads((PARTS / "en.json").read_text(encoding="utf-8"))
en_keys = set(en)
errors, merged = [], {}

for code in CODES:
    f = PARTS / f"{code}.json"
    if not f.exists():
        errors.append(f"{code}: file missing")
        continue
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        errors.append(f"{code}: JSON parse failed: {e}")
        continue
    if set(d) != en_keys:
        missing = sorted(en_keys - set(d))
        extra = sorted(set(d) - en_keys)
        errors.append(f"{code}: key mismatch missing={missing} extra={extra}")
        continue
    for k, v in d.items():
        if not isinstance(v, str) or not v.strip():
            errors.append(f"{code}:{k}: empty/non-string value")
        for token in HTML_KEYS.get(k, []):
            if token not in v:
                errors.append(f"{code}:{k}: lost required markup/token {token!r}")
    if code != "en":
        for k in ("tut_g1p", "priv_s1p", "terms_s2p"):
            if d[k] == en[k]:
                errors.append(f"{code}:{k}: identical to English (untranslated?)")
    merged[code] = d

if errors:
    print("VALIDATION FAILED:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print(f"valid: {len(merged)} languages x {len(en_keys)} keys (pages are translated server-side from these files)")
