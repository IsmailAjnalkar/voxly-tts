"""Per-language voice pages (/voices/<slug>.html), built from the live voice catalog.

Pure rendering: render() takes one language, that language's live voices (dead ones
already removed, as on /voices.html) and the rendered /voices.html page as the HTML
shell (header, footer, styles, skip link, <main id="main">). register() wires the
routes into server.py. Facts in the static text are checked against the code
(server.py: sentence ends, 5,000-character limit, pause markers, subtitle cues) or are
general, verifiable facts about the language; voice counts, regions and names come
from the catalog at request time. Last checked: UPDATED."""
import html
import json
import re
from collections import Counter

SITE = "https://text-2-speech.com"
UPDATED = "2026-10-31"
E = lambda t: html.escape(t, quote=False)
A = lambda t: html.escape(t, quote=True)

# The catalog uses names like "Swara - IN"; examples below use names that exist in it.
LANGS = [
    {"slug": "english", "code": "en", "name": "English", "related": ("chinese", "german"),
     "title": "English Text to Speech Voices: US, UK, Indian & More | Text 2 Speech",
     "desc": "Free English text to speech with American, British, Indian, Australian and other accents. "
             "See every English voice, pick an accent and make MP3 audio.",
     "about": "All English voices read the same English text: the region changes the accent, the intonation and "
              "how some words sound, so one script can come out American, British, Irish or Indian depending on "
              "the voice you choose. The accent comes from the voice, not from the spelling: a British voice "
              "reading American spelling such as <q>color</q> still sounds British.",
     "variants": "In the converter the region is the code after each voice name (US, GB, AU, IN…). If your "
                 "listeners are in one country, choose a voice from that country. For a mixed international "
                 "audience, compare a US and a UK voice on a paragraph of your own script and keep the one that "
                 "suits it.",
     "tips": [
         ("Search by country.", "Type <q>United Kingdom</q>, <q>India</q> or <q>Australia</q> into <em>Voice "
          "Search</em> to see only that region's English voices."),
         ("Spell out ambiguous abbreviations.", "<q>St.</q> can mean Street or Saint and <q>Dr.</q> Doctor or "
          "Drive. Writing the word you mean removes the guess."),
         ("Reword words with two pronunciations.", "<q>Read</q>, <q>lead</q>, <q>live</q> and <q>record</q> "
          "are spelled the same for two meanings. If a voice picks the wrong one, a small rewording fixes it."),
         ("Steer acronyms.", "Whether an acronym is spelled out or read as a word is the voice's guess. Write it "
          "with spaces between the letters, or as the word you want, to choose."),
     ]},
    {"slug": "spanish", "code": "es", "name": "Spanish", "related": ("french", "portuguese"),
     "title": "Spanish Text to Speech: Spain, Mexico & More Voices | Text 2 Speech",
     "desc": "Free Spanish text to speech with voices from Spain, Mexico, Argentina, the US and other countries. "
             "Compare regional accents and download Spanish MP3 audio.",
     "about": "Spanish is the first language of about twenty countries, and written Spanish is largely the same "
              "in all of them. Any Spanish voice can read your text; the regional variant changes the accent, "
              "the rhythm and a few sounds.",
     "variants": "The clearest difference is between Spain and Latin America. Voices from Spain use the "
                 "pronunciation in which <q>z</q>, and <q>c</q> before e or i, sound like the English <q>th</q> "
                 "(distinción); Latin American voices say them like <q>s</q> (seseo). Mexican, Argentine, "
                 "Caribbean and Andean accents also sound distinct from one another, so choose the country of "
                 "your listeners. For an audience spread across Latin America, compare a Mexican and a US "
                 "Spanish voice.",
     "tips": [
         ("Keep the written accents.", "<q>Papá</q> and <q>papa</q>, <q>está</q> and <q>esta</q>, <q>sí</q> and "
          "<q>si</q> are different words. The voice reads what is written, accents included."),
         ("Match the vocabulary to the variant.", "Spain says <q>ordenador</q> and <q>coche</q>, most of Latin "
          "America <q>computadora</q> and <q>carro</q>. The voice reads the word you write, so pick the words "
          "your audience uses along with the accent."),
         ("Write numbers the local way.", "Spain writes decimals with a comma (3,5), Mexico with a point (3.5). "
          "Use the convention of the voice's country and preview a sentence with figures before a long script."),
         ("Keep ¿ and ¡.", "Opening question and exclamation marks are normal Spanish punctuation and can stay; "
          "the closing ? or ! is where Text 2 Speech ends the sentence."),
     ]},
    {"slug": "hindi", "code": "hi", "name": "Hindi", "related": ("arabic", "indonesian"),
     "title": "Hindi Text to Speech: Free Hindi Voices Online | Text 2 Speech",
     "desc": "Free Hindi text to speech with natural Hindi (India) voices. Tips for Devanagari text, English "
             "words and numbers, and how to download Hindi MP3 audio.",
     "about": "Hindi voices in Text 2 Speech read Hindi written in Devanagari script (हिन्दी). Devanagari gives "
              "the voice the spelling it is designed for. Hindi typed in Latin letters, such as <q>aap kaise "
              "hain</q>, has no fixed spelling, so preview it before you rely on it.",
     "variants": "For English with an Indian accent, use the English (India) voices on the <a "
                 "href=\"/voices/english.html\">English voices page</a>. Bengali, Gujarati, Kannada, Malayalam, "
                 "Marathi, Tamil, Telugu and Urdu have voices of their own on the <a href=\"/voices.html\">voices "
                 "and languages page</a>.",
     "tips": [
         ("The danda ends a sentence.", "Text 2 Speech treats the Hindi full stop । like a full stop: long text "
          "is split there and subtitle lines end there."),
         ("English words in Hindi text.", "Everyday Hindi mixes in English words such as मोबाइल or कंप्यूटर. "
          "Writing them in Devanagari keeps the sentence in one script; if you keep a word in Latin letters, "
          "preview the sentence to hear how the Hindi voice says it."),
         ("Numbers.", "Hindi text uses both international digits (2026) and Devanagari digits (२०२६). Preview a "
          "sentence with your numbers, and write amounts in words where the exact wording matters."),
         ("Use a Hindi voice for Hindi text.", "In a test on this site an English voice returned no audio for "
          "Hindi text, so set <em>Voice Language</em> to Hindi first."),
     ]},
    {"slug": "arabic", "code": "ar", "name": "Arabic", "related": ("portuguese", "hindi"),
     "title": "Arabic Text to Speech: Egyptian, Saudi & Gulf Voices | Text 2 Speech",
     "desc": "Free Arabic text to speech with voices from Egypt, Saudi Arabia, the Gulf, the Levant and North "
             "Africa. Tips for diacritics, numbers and mixed text.",
     "about": "Arabic voices in Text 2 Speech read text written in Arabic script. Most written Arabic, such as "
              "news, documents and lessons, is Modern Standard Arabic, shared by readers across the Arab world; "
              "the country on each voice tells you which region the voice comes from.",
     "variants": "The countries span the Gulf, Egypt, the Levant, Iraq, Yemen and North Africa. Pick the country "
                 "of your listeners when you know it, and compare two or three voices: the same written text can "
                 "sound noticeably different from one country's voice to the next.",
     "tips": [
         ("Add short vowels where a word is ambiguous.", "Without tashkeel some Arabic words have more than one "
          "reading. Adding the vowel marks to that one word can steer the voice to the reading you mean."),
         ("The Arabic question mark works.", "Text 2 Speech treats ؟ like ?: long text is split there and "
          "subtitle lines end there."),
         ("Mixed Arabic and Latin text.", "English words inside an Arabic line can look out of order in the text "
          "box, because right-to-left and left-to-right text are laid out together. The text is still sent in "
          "the order you typed it; preview the sentence to check the result."),
         ("Numbers.", "Arabic text can use Western digits (2026) or Arabic-Indic digits (٢٠٢٦). Preview a "
          "sentence with your numbers to hear how the voice reads them."),
     ]},
    {"slug": "french", "code": "fr", "name": "French", "related": ("german", "spanish"),
     "title": "French Text to Speech: France, Canada & More Voices | Text 2 Speech",
     "desc": "Free French text to speech with voices from France, Canada (Québec), Belgium and Switzerland. See "
             "every French voice, with tips for accents and numbers.",
     "about": "French voices in Text 2 Speech read standard written French. The regional variant changes the "
              "accent: voices from Canada have a Canadian (Québec) accent, while voices from France, Belgium and "
              "Switzerland sound European, each with its own regional colour.",
     "variants": "Pick France for a general European French audience, Canada for listeners in Québec and the "
                 "rest of Canada, and Belgium or Switzerland for that country's accent. Vocabulary differs too: "
                 "Québec French uses <q>courriel</q> (e-mail) and <q>fin de semaine</q> (weekend) where France "
                 "often says <q>e-mail</q> and <q>week-end</q>, so match the words to the accent.",
     "tips": [
         ("Keep accents and the cedilla.", "<q>Rose</q> and <q>rosé</q> sound different, and <q>garçon</q> "
          "without its cedilla would be read with a hard c. The voice reads what is written."),
         ("70 and 90.", "Belgium and Switzerland say <q>septante</q> and <q>nonante</q>, France <q>soixante-dix</q> "
          "and <q>quatre-vingt-dix</q>. If a figure must be said one way, write it in words."),
         ("Write out abbreviations.", "If <q>M.</q> or <q>Mme</q> should be read as Monsieur or Madame, write the "
          "full word; that also keeps the abbreviation's full stop from ending a subtitle line early."),
         ("French spacing is fine.", "French typography puts a space before ? ! : and ;. You can keep it: Text 2 "
          "Speech still finds the end of each sentence."),
     ]},
    {"slug": "german", "code": "de", "name": "German", "related": ("english", "french"),
     "title": "German Text to Speech: German, Austrian & Swiss Voices | Text 2 Speech",
     "desc": "Free German text to speech with voices from Germany, Austria and Switzerland. Tips for umlauts, "
             "compound words and dates, and how to make German MP3 audio.",
     "about": "German voices in Text 2 Speech read Standard German as it is written. The voices from Austria and "
              "Switzerland speak Standard German with their country's accent; they read written German, not a "
              "dialect such as Swiss German (Schweizerdeutsch), which has no standard spelling.",
     "variants": "Choose Germany for a general audience, and Austria or Switzerland when listeners there should "
                 "hear a familiar accent. Swiss Standard German is written without ß (<q>Strasse</q>, not "
                 "<q>Straße</q>); use the spelling your readers expect.",
     "tips": [
         ("Write umlauts and ß.", "The substitutes ae, oe, ue and ss also occur in names such as Goethe, so a "
          "voice cannot always tell that they stand for ä, ö, ü or ß."),
         ("Long compounds.", "Compound words are normal German. If a rare one sounds wrong, a hyphen between its "
          "parts (Donau-Dampfschifffahrt) is valid spelling and can help the voice split it."),
         ("Dates and ordinals.", "<q>3. Oktober</q> can be read with different endings depending on the sentence. "
          "Preview it, and write the words (<q>am dritten Oktober</q>) when the ending matters."),
         ("Write out z. B. and usw.", "Text 2 Speech ends a subtitle line at a full stop, so abbreviations such "
          "as <q>z. B.</q> break lines early; <q>zum Beispiel</q> keeps them whole."),
     ]},
    {"slug": "portuguese", "code": "pt", "name": "Portuguese", "related": ("spanish", "arabic"),
     "title": "Portuguese Text to Speech: Brazilian & European Voices | Text 2 Speech",
     "desc": "Free Portuguese text to speech with Brazilian and European Portuguese voices. Compare the two "
             "accents, see every voice and download Portuguese MP3 audio.",
     "about": "Brazilian and European Portuguese sound clearly different: the vowels, the rhythm of speech and "
              "many everyday words are not the same. Text 2 Speech lists both, each labelled with its country.",
     "variants": "Choose a voice from Brazil for listeners in Brazil and a voice from Portugal for listeners in "
                 "Portugal. Because the accents are so distinct, it is worth matching the voice to the spelling "
                 "and vocabulary of your script as well.",
     "tips": [
         ("Match the vocabulary.", "<q>Ônibus</q> or <q>autocarro</q> (bus), <q>trem</q> or <q>comboio</q> "
          "(train), <q>celular</q> or <q>telemóvel</q> (mobile phone): Brazil uses the first, Portugal the "
          "second, and the voice reads the word you write."),
         ("Match the spelling.", "Brazil writes <q>fato</q> and <q>econômico</q>, Portugal <q>facto</q> and "
          "<q>económico</q>. Use the spelling of the variant you chose."),
         ("Keep accents and tildes.", "<q>Avó</q> (grandmother) and <q>avô</q> (grandfather) differ only in "
          "the accent and are pronounced differently; ã, õ and ç matter in the same way."),
         ("Break up long sentences.", "Portuguese sentences with many clauses are easier to follow with a "
          "pause: add <code>[break:500ms]</code> after a clause, or end the sentence and start a new one."),
     ]},
    {"slug": "chinese", "code": "zh", "vl": "zh-CN", "name": "Chinese", "related": ("japanese", "english"),
     "title": "Chinese Text to Speech: Mandarin & Cantonese Voices | Text 2 Speech",
     "desc": "Free Chinese text to speech in Mandarin and Cantonese: voices for mainland China, Taiwan and Hong "
             "Kong. Tips for characters and punctuation, with MP3 download.",
     "about": "Chinese voices in Text 2 Speech read text written in Chinese characters. The Chinese voice language "
              "covers more than one spoken variety: the mainland and Taiwan voices speak Mandarin, the Hong Kong "
              "voices speak Cantonese, and some voices are labelled with a regional Mandarin dialect.",
     "variants": "Choose by audience: a mainland voice for mainland China, a Taiwan voice for Taiwan, and a Hong "
                 "Kong voice when the audio should be Cantonese. Mandarin and Cantonese read the same characters "
                 "with very different pronunciation, so one cannot stand in for the other.",
     "tips": [
         ("Use your readers' script.", "Mainland China writes Simplified characters; Taiwan and Hong Kong use "
          "Traditional characters. Keep the text in the script that matches the voice's region."),
         ("Chinese punctuation ends sentences.", "Text 2 Speech treats 。！？ like . ! ?: long text is split "
          "there and subtitle lines end there, and words are timed without needing spaces."),
         ("Characters with several readings.", "Characters such as 行 (háng or xíng) and 长 (cháng or zhǎng) "
          "change their reading with the word. If a voice reads a name or rare phrase wrongly, rewrite it with "
          "an unambiguous word."),
         ("Count characters, not words.", "One generation holds 5,000 characters, and every Chinese character "
          "and punctuation mark counts as one; split longer scripts into parts."),
     ]},
    {"slug": "japanese", "code": "ja", "name": "Japanese", "related": ("indonesian", "chinese"),
     "title": "Japanese Text to Speech: Free Japanese Voices Online | Text 2 Speech",
     "desc": "Free Japanese text to speech with natural Japanese voices. Tips for kanji readings, names and "
             "punctuation, and how to make Japanese MP3 audio and subtitles.",
     "about": "Japanese voices in Text 2 Speech read ordinary Japanese text that mixes kanji, hiragana and "
              "katakana, with no spaces between words. The voice works out each kanji's reading from context, "
              "which suits everyday text; names and rare words are where it can guess wrong.",
     "variants": "Standard Japanese is used across the country in writing and broadcasting, so a voice for "
                 "Japan serves most audiences.",
     "tips": [
         ("Names in kana.", "Personal and place names often have several possible readings; 東海林, for "
          "example, is usually Shōji. If the voice picks the wrong one, write the name in hiragana or katakana."),
         ("Japanese punctuation ends sentences.", "Text 2 Speech treats 。！？ like . ! ?: long text is split "
          "there and subtitle lines end there, with words timed even though there are no spaces."),
         ("Loanwords in katakana.", "English words are normally written in katakana (コンピューター) and read "
          "with Japanese pronunciation. An English word left in Latin letters is the voice's guess; preview it."),
         ("Every character counts.", "One generation holds 5,000 characters; each kana, kanji and punctuation "
          "mark counts as one."),
     ]},
    {"slug": "indonesian", "code": "id", "name": "Indonesian", "related": ("hindi", "japanese"),
     "title": "Indonesian Text to Speech: Bahasa Indonesia Voices | Text 2 Speech",
     "desc": "Free Indonesian text to speech with natural Bahasa Indonesia voices. Tips for abbreviations, "
             "loanwords and numbers, and how to make Indonesian MP3 audio.",
     "about": "Indonesian voices in Text 2 Speech read Bahasa Indonesia written in the Latin alphabet. Indonesian "
              "spelling is close to how words are pronounced, so most problems come from informal "
              "abbreviations and from foreign words rather than from standard text.",
     "variants": "Bahasa Indonesia has one standard form, used in schools, media and government across the "
                 "country. Javanese and Sundanese, which many Indonesians speak as a first language, are "
                 "separate languages with voices of their own, as is Malay; they are on the <a "
                 "href=\"/voices.html\">voices and languages page</a>.",
     "tips": [
         ("Write out chat abbreviations.", "<q>yg</q> (yang), <q>dgn</q> (dengan), <q>tdk</q> (tidak) and "
          "<q>dll</q> (dan lain-lain) are fine in messages, but a voice may spell them letter by letter."),
         ("Write plurals in full.", "Use the standard <q>anak-anak</q>, not the informal <q>anak2</q>."),
         ("Foreign words.", "Indonesian spellings of loanwords such as <q>komputer</q> and <q>televisi</q> are "
          "read the Indonesian way; brand names in English spelling are the voice's guess, so preview them."),
         ("Numbers.", "Indonesian uses a dot for thousands and a comma for decimals (Rp1.500.000; 2,5). Write "
          "numbers that way and preview a sentence with figures."),
     ]},
]
BY_SLUG = {l["slug"]: l for l in LANGS}
PATHS = [f"voices/{l['slug']}.html" for l in LANGS]
HREF = {l["code"]: f"/voices/{l['slug']}.html" for l in LANGS}

# For /voices.html: a link to every language page (independent of the live catalog).
INDEX_HTML = ('<h2 id="by-language">Voice guides by language</h2><p>Every voice, its regional variants and '
              'practical tips for the most used languages: '
              + ", ".join(f'<a href="{HREF[l["code"]]}">{l["name"]} voices</a>' for l in LANGS) + ".</p>")


def label(code: str, name_html: str) -> str:
    """Language name for a /voices.html row: linked when that language has a page."""
    return f'<a href="{HREF[code]}">{name_html}</a>' if code in HREF else name_html


def _region(v: dict) -> str:
    """'Microsoft Swara Online (Natural) - Hindi (India)' -> 'India'; else the locale's country part."""
    m = re.search(r" - [^(]*\(([^)]*)\)", v.get("friendly", ""))
    return m.group(1) if m else v["country"]


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _n(k: int, word: str) -> str:
    return f"{k} {word}{'' if k == 1 else 's'}"


def _variants(vs: list[dict]) -> list[tuple[str, str, list[dict]]]:
    """(locale, region label, voices) per regional variant, most voices first."""
    by = {}
    for v in vs:
        by.setdefault(v["locale"], []).append(v)
    out = []
    for loc, g in by.items():
        c = Counter(_region(v) for v in g)
        out.append((loc, max(c, key=lambda r: (c[r], len(r))), g))
    return sorted(out, key=lambda t: (-len(t[2]), t[1]))


def _body(lang: dict, vs: list[dict]) -> str:
    name, code = lang["name"], lang["code"]
    vs = sorted(vs, key=lambda v: (v["locale"], v["name"]))
    variants = _variants(vs)
    multi = [v for v in vs if "Multilingual" in v["id"]]
    f = sum(v["gender"] == "Female" for v in vs)
    m = sum(v["gender"] == "Male" for v in vs)
    tool = f'<a href="/?vl={lang.get("vl", code)}">Try {name} voices in the free tool</a>'
    h = [f"<h1>{name} text to speech voices</h1>"]
    if vs:
        if len(vs) <= 4:
            who = _join([f"{E(v['name'])} ({v['gender'].lower() or 'voice'})" for v in vs])
            where = (f"for {name} as spoken in {E(variants[0][1])}" if len(variants) == 1
                     else f"in {_n(len(variants), 'regional variant')}")
            lead = f"Text 2 Speech has {_n(len(vs), name + ' voice')} right now, {where}: {who}."
        else:
            lead = (f"Text 2 Speech has {len(vs)} {name} voices right now, {f} female and {m} male, in "
                    f"{_n(len(variants), 'regional variant')}.")
        lead += f" {({1: 'It is', 2: 'Both are'}).get(len(vs), 'All of them are')} free to use with no sign-up. {tool}."
    else:
        lead = (f"The live list of {name} voices could not be loaded just now; please reload the page. "
                f"{tool}.")
    h.append(f'<p class="lead">{lead}</p>')
    h.append(f"<p>{lang['about']}</p>")
    if vs:
        rows = "".join(
            f'<tr><th scope="row">{E(v["name"])}</th><td>{E(_region(v))}</td><td>{E(v["locale"])}</td>'
            f'<td>{E(v["gender"])}</td><td>{"Yes" if "Multilingual" in v["id"] else "No"}</td></tr>' for v in vs)
        h.append(f'<h2 id="list">All {name} voices</h2>'
                 f"<p>The table lists every {name} voice the speech service offers today. The list is refreshed "
                 f"daily, and a {name} voice that stops producing audio is hidden until it works again.</p>"
                 f'<div class="tablewrap" tabindex="0" role="region" aria-label="{name} voices (table, scrolls '
                 f'sideways)"><table><thead><tr><th scope="col">Voice</th><th scope="col">Region</th>'
                 f'<th scope="col">Locale</th><th scope="col">Gender</th><th scope="col">Multilingual</th></tr>'
                 f"</thead><tbody>{rows}</tbody></table></div>")
        if multi:
            h.append(f"<p>{_n(len(multi), 'multilingual ' + name + ' voice')} ({_join([E(v['name']) for v in multi])}) "
                     f"{'is' if len(multi) == 1 else 'are'} meant for text that mixes {name} with other languages; "
                     f'see <a href="/guides/choose-voice.html#multilingual">multilingual voices</a>.</p>')
        else:
            h.append(f"<p>None of the {name} voices is a multilingual voice. For text that mixes {name} with "
                     f'other languages, see <a href="/guides/choose-voice.html#multilingual">multilingual '
                     f"voices</a>.</p>")
    h.append(f'<h2 id="variants">Regional variants of {name}</h2>')
    if vs:
        items = "".join(
            f"<li><strong>{E(r)}</strong> ({E(loc)}): {_n(len(g), 'voice')}, "
            f"{sum(v['gender'] == 'Female' for v in g)} female and {sum(v['gender'] == 'Male' for v in g)} male</li>"
            for loc, r, g in variants)
        h.append(f"<ul>{items}</ul>")
    h.append(f"<p>{lang['variants']}</p>")
    h.append(f'<h2 id="tips">Tips for {name} text</h2><ul>'
             + "".join(f"<li><strong>{t}</strong> {d}</li>" for t, d in lang["tips"]) + "</ul>")
    ex = [v["name"] for v in vs[:1]] + [v["name"] for v in vs if v["gender"] != (vs[0]["gender"] if vs else "")][:1]
    pick = (f"Pick a voice, for example {_join([E(x) for x in ex])}, and press <em>Preview</em> next to it "
            f"to hear it." if ex else f"Pick a {name} voice and press <em>Preview</em> next to it to hear it.")
    h.append(f'<h2 id="how">How to make {name} speech</h2><ol>'
             f"<li>{tool}: the link opens the converter with <em>Voice Language</em> set to {name}.</li>"
             f"<li>Paste or type your {name} text, up to 5,000 characters, or import a .txt file.</li>"
             f"<li>{pick}</li>"
             f"<li>Add pauses between {name} sentences or sections where you need them: <code>[break:500ms]</code> "
             f"(<kbd>Ctrl</kbd>+<kbd>B</kbd> inserts it) or <code>[break:2s]</code>. One generation holds 25 "
             f"pause markers and up to 60 seconds of silence.</li>"
             f"<li>Press <em>Generate Audio</em>, then download the {name} audio as MP3 or WAV with its SRT and VTT "
             f"subtitles.</li></ol>")
    rel = [BY_SLUG[s] for s in lang["related"]]
    h.append(f'<h2 id="related">Related pages</h2><ul>'
             + "".join(f'<li><a href="/voices/{r["slug"]}.html">{r["name"]} text to speech voices</a></li>' for r in rel)
             + f'<li><a href="/voices.html">Voices and languages: the full list</a></li>'
             f'<li><a href="/guides/choose-voice.html">How to choose a voice and accent</a></li></ul>')
    return "".join(h)


def render(slug: str, voices: list[dict], shell: str) -> str:
    """One language page. voices: the live catalog without dead voices (any language);
    shell: the rendered /voices.html, whose head metadata, JSON-LD and <main> are replaced."""
    lang = BY_SLUG[slug]
    url = f"{SITE}/voices/{slug}.html"
    title, desc = lang["title"], lang["desc"]
    vs = [v for v in voices if v["language"] == lang["code"]]
    crumbs = [("Home", SITE + "/"), ("Voices & languages", SITE + "/voices.html"), (lang["name"], url)]
    lds = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
               {"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(crumbs, 1)]},
           {"@context": "https://schema.org", "@type": "CollectionPage", "@id": url, "url": url, "name": title,
            "description": desc, "inLanguage": "en", "dateModified": UPDATED,
            "about": {"@type": "Language", "name": lang["name"], "alternateName": lang["code"]},
            "isPartOf": {"@id": f"{SITE}/#website"}, "publisher": {"@id": f"{SITE}/#org"}}]
    nav = (" <span aria-hidden=\"true\">›</span> ".join(f'<a href="{u.replace(SITE, "") or "/"}">{E(n)}</a>'
                                                        for n, u in crumbs[:-1])
           + f' <span aria-hidden="true">›</span> <span aria-current="page">{E(crumbs[-1][0])}</span>')
    main = (f'<nav class="crumbs" aria-label="Breadcrumb">{nav}</nav>{_body(lang, vs)}'
            f'<p class="updated">Last updated: <time datetime="{UPDATED}">31 October 2026</time></p>')
    s = re.sub(r"<title>.*?</title>", lambda _: f"<title>{E(title)}</title>", shell, count=1, flags=re.S)
    for attr, key, val in (("name", "description", desc), ("property", "og:title", title),
                           ("property", "og:description", desc), ("property", "og:url", url),
                           ("name", "twitter:title", title), ("name", "twitter:description", desc)):
        s = re.sub(rf'<meta {attr}="{key}" content="[^"]*">', lambda _: f'<meta {attr}="{key}" content="{A(val)}">', s, count=1)
    s = re.sub(r'<link rel="canonical" href="[^"]*">', lambda _: f'<link rel="canonical" href="{url}">', s, count=1)
    s = re.sub(r'<script type="application/ld\+json">.*?</script>', "", s, flags=re.S)
    s = s.replace("</head>", "".join('<script type="application/ld+json">'
                                     + json.dumps(d, ensure_ascii=False).replace("</", "<\\/") + "</script>"
                                     for d in lds) + "</head>", 1)
    return re.sub(r"(<main[^>]*>).*?(</main>)", lambda m: m.group(1) + main + m.group(2), s, count=1, flags=re.S)


def register(route, shell, get_voices, dead) -> None:
    """route: server._route; shell(): the rendered /voices.html; get_voices: the async catalog;
    dead: the set of voice ids the health sweep hid (read on every request)."""
    from fastapi.responses import HTMLResponse

    def handler_for(slug):  # a closure with no parameters (a default argument would become a query param)
        async def handler():
            try:
                vs = [v for v in await get_voices() if v["id"] not in dead]
            except Exception:  # catalog unreachable: the page says so, like /voices.html
                vs = []
            return HTMLResponse(render(slug, vs, shell()))
        return handler

    for slug in BY_SLUG:
        route(f"/voices/{slug}.html")(handler_for(slug))
