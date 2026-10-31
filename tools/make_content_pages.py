"""Build the English content pages from the sub-page template (run from the repo root).
Facts come from the code (server.py, web/index.html, deploy/nginx-voxy*.conf) and from
measured runs on 2026-10-29 and 2026-10-31; keep them in sync. Each claim's source is
listed in docs/seo-remediation/CONTENT_CHANGES.md. The checks at the bottom fail the
build on broken structure, links or duplicated paragraphs."""
import html, json, pathlib, re
from datetime import date
from html.parser import HTMLParser

SITE = "https://text-2-speech.com"
UPDATED = "2026-10-31"
tpl = pathlib.Path("web/terms.html").read_text(encoding="utf-8")
style = re.search(r"<style>.*?</style>", tpl, re.S).group(0).replace(
    "</style>",
    "main h2{font-size:22px;margin:30px 0 8px}main h3{font-size:17px;margin:20px 0 6px}"
    ".lead{font-size:17px}.updated{color:var(--muted);font-size:13px}"
    "table{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px}th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}"
    "thead th{background:var(--panel2)}.voices td:nth-child(3){white-space:nowrap}pre{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:12px;overflow:auto;font-size:13px;line-height:1.5}"
    "code{background:var(--panel2);border-radius:5px;padding:1px 5px}.tablewrap{overflow-x:auto}"
    "nav.toc{display:block;margin:16px 0 8px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 18px}"
    "nav.toc p{margin:0}nav.toc ol{margin:4px 0;padding-left:22px}nav.toc a{white-space:normal}"
    "</style>")
boot = re.search(r"<script>if\(localStorage.*?</script>", tpl).group(0)
icons = re.search(r'<link rel="icon" href="/favicon.svg".*?<link rel="apple-touch-icon"[^>]*>', tpl).group(0)
header = re.search(r"<header>.*?</header>", tpl, re.S).group(0)
footer = re.search(r"<footer>.*?</footer>", tpl, re.S).group(0)
main_tag = re.search(r"<main[^>]*>", tpl).group(0)  # keeps id="main" for the skip link
A = lambda t: html.escape(t, quote=True)
ORG = {"@type": "Organization", "@id": SITE + "/#org", "name": "Text 2 Speech", "url": SITE + "/",
       "logo": {"@type": "ImageObject", "url": SITE + "/logo.png"}}
pages = {}  # path -> html, for the checks


def human(d):
    return f"{date.fromisoformat(d).day} {date.fromisoformat(d):%B %Y}"


def page(path, title, desc, crumbs, body, kind="TechArticle", published=UPDATED):
    url = f"{SITE}/{path}"
    headline = title.split(" | ")[0]
    ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(crumbs, 1)]}]
    if kind == "TechArticle":
        ld.append({"@context": "https://schema.org", "@type": "TechArticle", "headline": headline,
                   "description": desc, "url": url, "inLanguage": "en", "datePublished": published, "dateModified": UPDATED,
                   "author": ORG, "publisher": ORG, "image": SITE + "/og-image.png?v=2", "mainEntityOfPage": url})
    elif kind == "AboutPage":
        # Only what the site itself states: the brand, the free web app and the footer's copyright line.
        ld.append({"@context": "https://schema.org", "@type": "AboutPage", "name": headline, "description": desc,
                   "url": url, "inLanguage": "en", "dateModified": UPDATED,
                   "isPartOf": {"@type": "WebSite", "@id": SITE + "/#website", "name": "Text 2 Speech", "url": SITE + "/"},
                   "about": {"@type": "WebApplication", "@id": SITE + "/#app", "name": "Text 2 Speech", "url": SITE + "/",
                             "applicationCategory": "MultimediaApplication", "operatingSystem": "Web",
                             "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}},
                   "publisher": ORG, "copyrightHolder": {"@type": "Organization", "name": "QINTAR LLC"}, "copyrightYear": 2026})
    lds = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    nav = ' <span aria-hidden="true">›</span> '.join(f'<a href="{u.replace(SITE, "") or "/"}">{html.escape(n)}</a>' for n, u in crumbs[:-1])
    nav += f' <span aria-hidden="true">›</span> <span aria-current="page">{html.escape(crumbs[-1][0])}</span>'
    out = ('<!DOCTYPE html><html lang="en" data-en-only><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f"<title>{html.escape(title)}</title>{boot}"
           f'<meta name="description" content="{A(desc)}"><link rel="canonical" href="{url}"><meta name="robots" content="index, follow">'
           f'<meta property="og:type" content="{"article" if kind == "TechArticle" else "website"}"><meta property="og:site_name" content="Text 2 Speech"><meta property="og:locale" content="en_US">'
           f'<meta property="og:title" content="{A(title)}"><meta property="og:description" content="{A(desc)}"><meta property="og:url" content="{url}">'
           f'<meta property="og:image" content="{SITE}/og-image.png?v=2"><meta name="twitter:card" content="summary_large_image">'
           f"{icons}{style}{lds}</head><body>{header}{main_tag}"
           f'<nav class="crumbs" aria-label="Breadcrumb">{nav}</nav>{body}'
           f'<p class="updated">Last updated: <time datetime="{UPDATED}">{human(UPDATED)}</time></p></main>'
           f'{footer}<script src="/subi18n.js"></script></body></html>\n')
    # wide tables and code blocks scroll sideways on phones: keyboard-focusable, labelled regions
    out = out.replace('<div class="tablewrap">', '<div class="tablewrap" aria-label="Table (scrolls sideways)">').replace(
        '<div class="tablewrap" aria-label=', '<div class="tablewrap" tabindex="0" role="region" aria-label=')
    out = out.replace("<pre>", '<pre aria-label="Example file">').replace("<pre aria-label=", '<pre tabindex="0" role="region" aria-label=')
    f = pathlib.Path("web") / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(out, encoding="utf-8")
    pages[path] = out
    print("wrote", f, len(out), "bytes")


def toc(*items):
    """'On this page' list; items are (id, label) and must match the H2 ids."""
    lis = "".join(f'<li><a href="#{i}">{html.escape(t)}</a></li>' for i, t in items)
    return f'<nav class="toc" aria-labelledby="toc-h"><p id="toc-h"><strong>On this page</strong></p><ol>{lis}</ol></nav>'


HOME = ("Home", SITE + "/")
HELP = ("Help", SITE + "/help.html")

# ---------------------------------------------------------------- about
page("about.html", "About Text 2 Speech: Free Online Text to Speech",
     "What Text 2 Speech is, what it does, how it is run and funded, how it handles your text, and how to contact the team behind text-2-speech.com.",
     [HOME, ("About", SITE + "/about.html")], """
<h1>About Text 2 Speech</h1>
<p class="lead">Text 2 Speech is a free web app at text-2-speech.com that turns written text into natural-sounding speech. It offers 300+ Microsoft neural voices in 75 languages, needs no account, and delivers every result as an MP3 or WAV file with matching SRT and VTT subtitle files.</p>
""" + toc(("what", "What Text 2 Speech does"), ("how", "How it works, in brief"), ("who", "Who runs Text 2 Speech"),
          ("funding", "How it is funded"), ("privacy", "Your text and privacy"), ("accuracy", "How these pages are checked"),
          ("contact", "Contact")) + """
<h2 id="what">What Text 2 Speech does</h2>
<p>Text 2 Speech converts a script of up to 5,000 characters into a downloadable audio file in the browser, with nothing to install. You choose the language and voice, can change speed and pitch, can insert exact pauses, and get subtitle files timed to the speech. The interface is available in 25 languages.</p>
<p>Typical uses are voiceovers for videos and presentations, narration for lessons, listening to your own drafts, and hearing how a sentence sounds in another language. The full feature list and every limit are in the <a href="/help.html">help centre</a>.</p>

<h2 id="how">How it works, in brief</h2>
<p>Your text goes from the page to the Text 2 Speech server, which sends it to Microsoft's online speech service in pieces, joins the returned audio into one file and builds the subtitles from the word timings the service reports. The <a href="/how-it-works.html">how it works page</a> describes each step.</p>

<h2 id="who">Who runs Text 2 Speech</h2>
<p>The site and its content are © 2026 QINTAR LLC, as stated in the footer of every page. Questions for the team go through the <a href="/support.html">support form</a>.</p>

<h2 id="funding">How it is funded</h2>
<p>Text 2 Speech is free to use: there is no paid plan, no sign-up and no advertising on the site. Running costs are covered by optional donations: anyone who wants to support the site can give any amount by card through <a href="https://buy.stripe.com/aFa6oIcYQ4QE00O22Q1Nu08" rel="noopener">Stripe</a> or through <a href="https://buymeacoffee.com/text2speech" rel="noopener">Buy Me a Coffee</a>, both linked from the <a href="/donate.html">Donate page</a>. Donating changes nothing in the tool: every feature stays free for everyone.</p>

<h2 id="privacy">Your text and privacy</h2>
<ul>
<li>You do not need to give a name or an email address to use the converter.</li>
<li>The text you convert is sent to Microsoft's online speech service, because that is where the audio is made.</li>
<li>Generated files are deleted from the server about two hours after your last generation.</li>
<li>The site sets no cookies and loads no third-party analytics or advertising scripts. The server keeps an anonymous count of page views (date and page address only).</li>
</ul>
<p>The legal details are in the <a href="/privacy.html">privacy policy</a>; what is stored where, and for how long, is listed under <a href="/help.html#data">data retention</a> in the help centre.</p>

<h2 id="accuracy">How these pages are checked</h2>
<p>The facts in the guides and the help centre, such as limits, file formats, file sizes and timings, are taken from the product's own code and from test generations on the tool itself. Each page shows the date it was last checked, and the figures are updated when the product changes.</p>

<h2 id="contact">Contact</h2>
<p>The contact channel is the form on the <a href="/support.html">support page</a>. Choose a topic (generation problem, voice request, bug report, business or licensing, or other), leave an email address for the reply, and describe what happened.</p>
""", kind="AboutPage")

# ---------------------------------------------------------------- help
page("help.html", "Text 2 Speech Help: Limits, Formats, Troubleshooting",
     "Reference for Text 2 Speech: features, exact limits (5,000 characters, 25 pauses), MP3, WAV, SRT and VTT formats, data retention, limitations and fixes.",
     [HOME, HELP], """
<h1>Text 2 Speech help centre</h1>
<p class="lead">This is the reference for Text 2 Speech, the free online text-to-speech converter at text-2-speech.com. It lists every feature, the exact limits, the file formats you can download, how long files are kept, what the tool does not do, and how to fix the problems people run into most often.</p>
""" + toc(("features", "Features"), ("limits", "Limits"), ("formats", "File formats"), ("data", "Data retention"),
          ("limitations", "What Text 2 Speech does not do"), ("troubleshooting", "Troubleshooting"), ("guides", "Guides"),
          ("contact", "Still stuck?")) + """
<h2 id="features">Features</h2>
<p>Text 2 Speech converts typed, pasted or imported text into speech with a chosen neural voice and returns an audio file plus two subtitle files.</p>
<div class="tablewrap" aria-label="Features (table)"><table>
<thead><tr><th scope="col">Feature</th><th scope="col">How it works</th></tr></thead>
<tbody>
<tr><th scope="row">Voices</th><td>300+ Microsoft neural voices in 75 languages, female and male. Filter by gender, or search by voice name, country or language (for example <q>India</q>). See the <a href="/voices.html">full voice list</a>.</td></tr>
<tr><th scope="row">Voice samples</th><td>The <em>Preview</em> button next to a voice plays a short sample sentence in that voice.</td></tr>
<tr><th scope="row">Quick read-back</th><td><em>Preview Audio</em> reads the first 1,200 characters of your text instantly with a voice built into your own browser or device, not with the selected neural voice.</td></tr>
<tr><th scope="row">Speed and pitch</th><td>Tick <em>Speed</em> or <em>Pitch</em> to unlock a slider (steps of 5) and a number box for exact values.</td></tr>
<tr><th scope="row">Pauses</th><td>Type <code>[break:500ms]</code> or <code>[break:1.5s]</code> anywhere in the text. <kbd>Ctrl</kbd>+<kbd>B</kbd> (<kbd>⌘</kbd>+<kbd>B</kbd> on a Mac) inserts <code>[break:500ms]</code> at the cursor.</td></tr>
<tr><th scope="row">File import</th><td><em>Import File</em> loads a <code>.txt</code>, <code>.md</code> or <code>.text</code> file into the text box as-is, after asking before it replaces existing text.</td></tr>
<tr><th scope="row">Output</th><td>MP3 or WAV, chosen before you generate, plus SRT and VTT subtitles with every generation.</td></tr>
<tr><th scope="row">Results list</th><td>Each result has a player, download links and a <em>Delete</em> button. <em>Autoplay after generation</em> plays new results automatically.</td></tr>
<tr><th scope="row">Interface languages</th><td>25, for example <a href="/es/">/es/</a>, <a href="/de/">/de/</a> and <a href="/zh-CN/">/zh-CN/</a>. The guides and this help centre are in English.</td></tr>
<tr><th scope="row">Price</th><td>Free, with no sign-up.</td></tr>
</tbody></table></div>

<h2 id="limits">Limits</h2>
<p>Each generation accepts up to 5,000 characters of text with up to 25 pause markers; the table lists every limit and what happens when you go over it.</p>
<div class="tablewrap" aria-label="Limits (table)"><table>
<thead><tr><th scope="col">Limit</th><th scope="col">Value</th><th scope="col">If you go over it</th></tr></thead>
<tbody>
<tr><th scope="row">Text per generation</th><td>5,000 characters, pause markers included; an emoji counts as one character</td><td>The counter turns red and <em>Generate Audio</em> is disabled</td></tr>
<tr><th scope="row">Pause markers</th><td>25 per generation</td><td>Error: <q>Too many [break] markers (max 25)</q></td></tr>
<tr><th scope="row">One pause</th><td>30 seconds</td><td>A longer marker is shortened to 30 seconds</td></tr>
<tr><th scope="row">All pauses together</th><td>60 seconds</td><td>Error: <q>Total pause length exceeds 60 s</q></td></tr>
<tr><th scope="row">Speed</th><td>−100% to +100%</td><td>A typed value outside the range snaps back to the nearest end</td></tr>
<tr><th scope="row">Pitch</th><td>−100 Hz to +100 Hz</td><td>Same as speed</td></tr>
<tr><th scope="row">Requests</th><td>About 20 per minute from one IP address; the voice <em>Preview</em> buttons count too</td><td>Message: <q>Too many requests — please wait a minute and try again.</q></td></tr>
<tr><th scope="row">Voices per generation</th><td>One</td><td>Generate each speaker separately</td></tr>
</tbody></table></div>
<p>For a sense of scale: in a test on 31 October 2026, 5,000 characters of English produced 5 minutes 28 seconds of speech.</p>

<h2 id="formats">File formats</h2>
<p>Text 2 Speech outputs MP3 or WAV audio and, with every generation, SRT and VTT subtitles; it imports plain-text files.</p>
<div class="tablewrap" aria-label="File formats (table)"><table>
<thead><tr><th scope="col">Format</th><th scope="col">Details</th><th scope="col">Downloaded file name</th></tr></thead>
<tbody>
<tr><th scope="row">MP3 (default)</th><td>48 kbps, 24 kHz, mono; about 0.36 MB per minute</td><td>A random 12-character name, such as <code>ddfd8759b889.mp3</code></td></tr>
<tr><th scope="row">WAV</th><td>16-bit PCM, 24 kHz, mono, decoded from the MP3; about 2.9 MB per minute</td><td>A random 12-character name ending in <code>.wav</code></td></tr>
<tr><th scope="row">SRT subtitles</th><td>Numbered cues, times like <code>00:00:01,300</code></td><td><code>subtitles.srt</code></td></tr>
<tr><th scope="row">VTT subtitles</th><td><code>WEBVTT</code> header, times like <code>00:00:01.300</code></td><td><code>subtitles.vtt</code></td></tr>
<tr><th scope="row">Import</th><td>Plain text from <code>.txt</code>, <code>.md</code> or <code>.text</code> files</td><td>—</td></tr>
</tbody></table></div>
<p>Rename the files right after downloading so each audio file stays next to its subtitles. Which audio format to pick is covered in <a href="/guides/mp3-vs-wav.html">MP3 vs WAV</a>; how the captions are built is in the <a href="/guides/subtitles.html">subtitles guide</a>.</p>

<h2 id="data">Data retention</h2>
<p>Generated files are kept on the Text 2 Speech server for about two hours after the last generation in your browser session and are then deleted automatically.</p>
<div class="tablewrap" aria-label="Data retention (table)"><table>
<thead><tr><th scope="col">What</th><th scope="col">Where</th><th scope="col">How long</th></tr></thead>
<tbody>
<tr><th scope="row">Your text</th><td>Sent to Microsoft's online speech service to create the audio. Our server saves the first 120 characters as the result's label.</td><td>The label is deleted with the files</td></tr>
<tr><th scope="row">Audio and subtitle files</th><td>Our server, in a folder named after a random session identifier</td><td>About 2 hours after your last generation; <em>Delete</em> removes a result at once</td></tr>
<tr><th scope="row">Results list</th><td>Your browser's session storage, for that tab only</td><td>Until the tab is closed; expired results drop off when the page reloads</td></tr>
<tr><th scope="row">Theme and interface language</th><td>Your browser's local storage</td><td>Until you clear it</td></tr>
<tr><th scope="row">Support messages</th><td>Our server's support inbox (email address, topic, message)</td><td>As long as needed to answer you</td></tr>
<tr><th scope="row">Page views</th><td>A counter of date and page address; no IP address, cookie or browser details</td><td>Daily totals</td></tr>
</tbody></table></div>
<p>See the <a href="/privacy.html">privacy policy</a> for the legal terms.</p>

<h2 id="limitations">What Text 2 Speech does not do</h2>
<p>Text 2 Speech is a browser-based converter for plain text; these features are not available:</p>
<ul>
<li><strong>No accounts.</strong> The sign-in page is a placeholder; there is no saved history or favourites, and everything works signed out.</li>
<li><strong>No developer API.</strong> There are no API keys and no API documentation; the converter is used through the web page.</li>
<li><strong>No PDF, Word, e-book or web-page reading.</strong> Only plain-text files can be imported; copy the text out of other documents first.</li>
<li><strong>No offline mode.</strong> The speech is made by an online service, so the converter needs an internet connection, and there is no app to install.</li>
<li><strong>No voice cloning or custom voices.</strong> Only the voices in the list can be used.</li>
<li><strong>No SSML, speaking styles or emotions.</strong> SSML tags are not interpreted; speed and pitch are the only voice controls, and pauses come from punctuation and <code>[break:…]</code> markers.</li>
<li><strong>No long-term storage.</strong> Download anything you want to keep.</li>
<li><strong>No commercial-use guarantee.</strong> Check the <a href="/terms.html">terms of service</a> and the rights in your source text.</li>
</ul>

<h2 id="troubleshooting">Troubleshooting</h2>
<p>Most problems come from a language mismatch between the text and the voice, from the rate limit, or from files that have already expired.</p>
<h3 id="no-sound-preview">No sound when I press Preview Audio</h3>
<p><em>Preview Audio</em> uses the speech voices installed in your browser or operating system, not the selected neural voice. If your device has no voice for that language, the preview can be silent or sound unlike your choice; some browsers have no speech support at all and show <q>Speech preview is not supported in this browser.</q> Check that the tab and device are not muted, then use the <em>Preview</em> button next to a voice, or <em>Generate Audio</em>, to hear the real voice.</p>
<h3 id="wrong-language">The voice sounds wrong, or no audio came back for the text</h3>
<p>Set <em>Voice Language</em> to the language your text is written in. A voice is built for its own language: with text in another language it may still produce audio, or it returns nothing when it cannot read the script: Hindi text sent to a US English voice fails with <q>The speech service returned no audio for this text.</q> For text that mixes languages, try a voice marked <em>(Multilingual)</em>; see <a href="/guides/choose-voice.html">how to choose a voice</a>.</p>
<h3 id="long-text">Long text is slow, or generation fails</h3>
<p>In testing, a full 5,000-character English text finished in about 12 seconds, so a wait of minutes points to a problem. Long text is processed in pieces of up to 1,500 characters; a piece that fails is retried once, and if it fails again you see <q>Synthesis failed, please retry</q>. Try again, or split the text into shorter parts. Over 5,000 characters, <em>Generate Audio</em> stays disabled until you shorten the text.</p>
<h3 id="voice-unavailable">"This voice is currently unavailable from the speech service"</h3>
<p>The speech service occasionally stops answering for a particular voice. Choose another voice for now. The server tests every voice every six hours and hides a voice from the list after eight failed attempts in a row, until it works again.</p>
<h3 id="too-many-requests">"Too many requests — please wait a minute and try again"</h3>
<p>The site allows about 20 requests per minute from one IP address, and each voice <em>Preview</em> click is a request. Wait a minute and generate again; your text and settings stay in the page.</p>
<h3 id="files-expired">A result or a download link disappeared</h3>
<p>Results belong to the browser tab they were made in, and the files are deleted about two hours after your last generation. A new tab starts with an empty list, and a reload removes results whose files have expired. Generate the text again and download it straight away.</p>
<h3 id="pause-errors">A pause marker is ignored or rejected</h3>
<p>Markers must look like <code>[break:500ms]</code> or <code>[break:2s]</code>; decimals such as <code>[break:1.5s]</code> work, and anything else is read as text. The limits are 25 markers, 30 seconds per marker and 60 seconds in total.</p>
<h3 id="voices-not-loading">The voice list does not load</h3>
<p>The page shows <q>Could not load the voice catalog. Check your connection and reload.</q> when the voice list cannot be fetched. Check your connection and reload the page; if it keeps happening, the speech service may be briefly unreachable.</p>
<p>Subtitles that drift from the audio are covered in the <a href="/guides/subtitles.html#troubleshooting">subtitles guide</a>.</p>

<h2 id="guides">Guides</h2>
<ul>
<li><a href="/guides/text-to-mp3.html">How to convert text to MP3 for free</a></li>
<li><a href="/guides/ai-voiceover.html">How to make a free AI voiceover from text</a></li>
<li><a href="/guides/choose-voice.html">How to choose a text to speech voice and accent</a></li>
<li><a href="/guides/subtitles.html">How to create SRT and VTT subtitles from text</a></li>
<li><a href="/guides/mp3-vs-wav.html">MP3 vs WAV for text to speech</a></li>
<li><a href="/how-it-works.html">How Text 2 Speech works</a> and the <a href="/tutorial.html">tutorial</a></li>
</ul>

<h2 id="contact">Still stuck?</h2>
<p>Send the details through the <a href="/support.html">support form</a>: the voice you chose, roughly how long the text was, and the exact error message help the most.</p>
""", kind="TechArticle")

# ---------------------------------------------------------------- how it works
page("how-it-works.html", "How Text 2 Speech Works: Voices, Pipeline, Privacy",
     "How the free Text 2 Speech converter turns text into audio: where the voices come from, each processing step, why the limits exist and where your text goes.",
     [HOME, ("How it works", SITE + "/how-it-works.html")], """
<h1>How Text 2 Speech works</h1>
<p class="lead">Text 2 Speech (text-2-speech.com) is a free online text-to-speech tool: you paste or type text, pick one of 300+ neural voices in 75 languages, and download the speech as an MP3 or WAV file together with SRT and VTT subtitles. This page explains what happens between pressing <em>Generate Audio</em> and getting the files.</p>
""" + toc(("voices", "Where the voices come from"), ("pipeline", "What happens when you press Generate Audio"),
          ("why-limits", "Why each generation has a limit"), ("data-flow", "Where your text goes"), ("related", "Related pages")) + """
<h2 id="voices">Where the voices come from</h2>
<p>The voices are Microsoft's online neural text-to-speech voices. On 31 October 2026 the catalog held 322 voices, 163 female and 159 male, across 75 languages and 142 regional variants, including twelve <em>multilingual</em> voices meant for text in more than one language. The server reloads the catalog once a day and tests every voice every six hours; a voice that fails eight test requests in a row is hidden until it works again. The <a href="/voices.html">voices and languages page</a> shows the current list.</p>

<h2 id="pipeline">What happens when you press Generate Audio</h2>
<ol>
<li>Your text is split at any <code>[break:…]</code> pause markers, and long passages are split at sentence ends into pieces of at most 1,500 characters.</li>
<li>Each piece is sent to the speech service with the voice, speed and pitch you chose. Up to four pieces are synthesized at the same time, each request has 45 seconds to finish, and a piece that fails is retried once.</li>
<li>The audio pieces and the pauses are joined in order into one MP3 file (48 kbps, 24 kHz, mono). If you chose WAV, that file is converted to 16-bit PCM WAV (24 kHz, mono).</li>
<li>The speech engine reports when each word starts and ends. Those timings become the SRT and VTT subtitle files, with your original punctuation kept; if the engine sends no timings, they are estimated from the length of each word and the real duration of the audio.</li>
<li>The result appears in your results list with a player and download links.</li>
</ol>

<h2 id="why-limits">Why each generation has a limit</h2>
<p>The 5,000-character limit, the cap of 25 pause markers and the per-minute request limit protect a free, anonymous service from abuse so that it stays fast for everyone. Within those limits a generation is quick: 5,000 characters of English became 5 minutes 28 seconds of audio in about 12 seconds when tested on 31 October 2026. Every limit and its exact value is listed in the <a href="/help.html#limits">help centre</a>.</p>

<h2 id="data-flow">Where your text goes</h2>
<p>Your text travels from your browser to the Text 2 Speech server and from there to Microsoft's online speech service, which returns the audio and the word timings. The server writes the finished files into a folder named after a random session identifier and deletes that folder about two hours after the last generation in it. The site sets no cookies and loads no third-party analytics or advertising scripts; the server only counts page views by date and page address. What is kept where is listed under <a href="/help.html#data">data retention</a>, and the <a href="/privacy.html">privacy policy</a> has the legal wording.</p>

<h2 id="related">Related pages</h2>
<ul>
<li><a href="/help.html">Help centre: features, limits, formats and troubleshooting</a></li>
<li><a href="/guides/text-to-mp3.html">How to convert text to MP3 for free</a></li>
<li><a href="/guides/ai-voiceover.html">How to make a free AI voiceover from text</a></li>
<li><a href="/guides/subtitles.html">How to create SRT and VTT subtitles from text</a></li>
<li><a href="/about.html">About Text 2 Speech</a></li>
</ul>
""", published="2026-10-29")

# ---------------------------------------------------------------- guide: text to MP3
page("guides/text-to-mp3.html", "How to Convert Text to MP3 for Free | Text 2 Speech",
     "Convert text to an MP3 file for free with no sign-up: paste text, pick one of 300+ voices, generate and download. Steps, file details and tips for long texts.",
     [HOME, HELP, ("Text to MP3", SITE + "/guides/text-to-mp3.html")], """
<h1>How to convert text to MP3 for free</h1>
<p class="lead"><strong>Short answer:</strong> paste your text into <a href="/">Text 2 Speech</a>, choose a voice, leave the output format on MP3 and press <em>Generate Audio</em>, then click <strong>⬇ MP3</strong> in the result. It is free with no sign-up, each conversion takes up to 5,000 characters, and you get a 48 kbps mono MP3 plus subtitles.</p>
""" + toc(("steps", "Steps"), ("mp3-file", "What the MP3 file contains"), ("long-text", "Text longer than 5,000 characters"),
          ("limitations", "Limitations"), ("related", "Related guides")) + """
<h2 id="steps">Steps</h2>
<ol>
<li>Open the <a href="/">converter</a>. The <em>Voice Language</em> list starts on English.</li>
<li>Set <em>Voice Language</em> to the language of your text, then select a voice. Its <em>Preview</em> button plays a sample.</li>
<li>Paste your text into <em>Input Text</em>, or press <em>Import File</em> to load a <code>.txt</code>, <code>.md</code> or <code>.text</code> file. The counter shows how many of the 5,000 characters you have used.</li>
<li>Optional: tick <em>Speed</em> or <em>Pitch</em> to change them, and add pauses with <code>[break:1s]</code> or <kbd>Ctrl</kbd>+<kbd>B</kbd>.</li>
<li>Check that <em>Output Format</em> shows <strong>MP3</strong> selected; it is the default.</li>
<li>Press <em>Generate Audio</em>. The result appears under <em>Results</em> with a player.</li>
<li>Click <strong>⬇ MP3</strong> to save the file. <strong>⬇ SRT</strong> and <strong>⬇ VTT</strong> save the matching subtitles.</li>
</ol>

<h2 id="mp3-file">What the MP3 file contains</h2>
<p>The download is a standard MP3 that plays on practically any phone, computer or browser.</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Property</th><th scope="col">Value</th></tr></thead>
<tbody>
<tr><th scope="row">Encoding</th><td>MP3 at 48 kbps, 24 kHz sample rate, mono</td></tr>
<tr><th scope="row">Size</th><td>About 0.36 MB per minute of speech</td></tr>
<tr><th scope="row">Length</th><td>5,000 characters of English gave 5 min 28 s of speech (voice Aria, US, tested 31 October 2026)</td></tr>
<tr><th scope="row">Time to convert</th><td>About 12 seconds for those 5,000 characters in the same test</td></tr>
<tr><th scope="row">File name</th><td>Random, for example <code>ddfd8759b889.mp3</code>; rename it after downloading</td></tr>
<tr><th scope="row">Kept online</th><td>About two hours after your last generation</td></tr>
</tbody></table></div>
<p>WAV is also available, but it is about eight times larger and sounds the same; <a href="/guides/mp3-vs-wav.html">MP3 vs WAV</a> explains when it is worth it.</p>

<h2 id="long-text">Text longer than 5,000 characters</h2>
<p>To turn a longer document, such as a book chapter, into MP3, convert it in parts and join them afterwards:</p>
<ol>
<li>Split the text at paragraph or section breaks into parts of up to 5,000 characters.</li>
<li>Convert each part with the same voice, speed and pitch, so the parts sound alike.</li>
<li>Download and rename each file in order (<code>part-01.mp3</code>, <code>part-02.mp3</code>…) before the two-hour expiry.</li>
<li>Join the files in an audio editor, or simply play them as a playlist.</li>
</ol>

<h2 id="limitations">Limitations</h2>
<ul>
<li>One voice per file: for a dialogue, convert each speaker's lines separately.</li>
<li>The input is plain text; the tool cannot open PDF, Word or web pages.</li>
<li>Files are not stored long-term and there is no account history.</li>
</ul>
<p>The complete list is in the <a href="/help.html#limitations">help centre</a>.</p>

<h2 id="related">Related guides</h2>
<ul>
<li><a href="/guides/choose-voice.html">How to choose a text to speech voice and accent</a></li>
<li><a href="/guides/ai-voiceover.html">How to make a free AI voiceover from text</a></li>
<li><a href="/guides/subtitles.html">How to create SRT and VTT subtitles from text</a></li>
</ul>
""")

# ---------------------------------------------------------------- guide: AI voiceover
page("guides/ai-voiceover.html", "How to Make a Free AI Voiceover from Text | Text 2 Speech",
     "Make a voiceover from a script for free: pick a neural voice, pace it with pause markers, generate it scene by scene and add matching SRT subtitles to video.",
     [HOME, HELP, ("AI voiceover", SITE + "/guides/ai-voiceover.html")], """
<h1>How to make a free AI voiceover from text</h1>
<p class="lead"><strong>Short answer:</strong> write the script, paste it into <a href="/">Text 2 Speech</a>, choose a neural voice, add <code>[break:…]</code> markers where the narration should pause, and press <em>Generate Audio</em>. You get the voiceover as an MP3 or WAV file plus SRT and VTT subtitles timed to it, ready to place on a video timeline.</p>
""" + toc(("script", "Prepare the script"), ("pauses", "Pace it with pauses"), ("steps", "Generate the voiceover"),
          ("speed", "Adjust speed and pitch"), ("video", "Add it to a video"), ("limitations", "Limitations"),
          ("related", "Related guides")) + """
<h2 id="script">Prepare the script</h2>
<ul>
<li><strong>One part per scene.</strong> Keep each part under 5,000 characters; a separate file per scene is easier to re-do and to place on a timeline.</li>
<li><strong>End every sentence with punctuation.</strong> Full stops, question marks and exclamation marks give natural pauses, and each sentence becomes its own caption in the subtitle files.</li>
<li><strong>Check the wording first.</strong> <em>Preview Audio</em> gives an instant rough read-back with your device's own voice, which is enough to catch awkward phrasing before you generate.</li>
</ul>

<h2 id="pauses">Pace it with pauses</h2>
<p>A pause marker inserts an exact silence into the generated audio; it is never read aloud and never appears in the subtitles.</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Type this</th><th scope="col">Silence added</th></tr></thead>
<tbody>
<tr><th scope="row"><code>[break:300ms]</code></th><td>0.3 seconds</td></tr>
<tr><th scope="row"><code>[break:500ms]</code> or <kbd>Ctrl</kbd>+<kbd>B</kbd></th><td>0.5 seconds</td></tr>
<tr><th scope="row"><code>[break:1.5s]</code></th><td>1.5 seconds</td></tr>
<tr><th scope="row"><code>[break:2s]</code></th><td>2 seconds</td></tr>
</tbody></table></div>
<p>The gap you hear is slightly longer than the marker, because the speech on either side keeps its own short natural edges: in a test, adding <code>[break:2s]</code> between two one-word sentences made the clip 2.9 seconds longer. A generation can hold 25 markers, each up to 30 seconds and 60 seconds in total.</p>

<h2 id="steps">Generate the voiceover</h2>
<ol>
<li>Choose the <em>Voice Language</em> of the script and pick a narrator; listen to two or three with their <em>Preview</em> buttons.</li>
<li>Paste the first scene into <em>Input Text</em> and add your pause markers.</li>
<li>Choose MP3, or WAV if your video editor prefers it, and press <em>Generate Audio</em>.</li>
<li>Listen to the result. To change a line, edit the text and generate again; each version stays in the results list.</li>
<li>Download the audio and the <strong>⬇ SRT</strong> file of the version you keep, and rename both with the scene number.</li>
<li>Repeat for each scene with the same voice, speed and pitch.</li>
</ol>

<h2 id="speed">Adjust speed and pitch</h2>
<p>Speed changes how fast the voice talks, from −100% to +100%, without changing the words. In a test, +50% made a sentence play in two-thirds of the time (5.1 s to 3.5 s) and −50% made it twice as long (10.2 s). Pitch moves the voice up or down by up to 100 Hz. The slider moves in steps of 5; type any whole value into the number box next to it.</p>

<h2 id="video">Add it to a video</h2>
<ol>
<li>Import the audio file into your video editor and place it on the timeline.</li>
<li>Import the SRT file from the <em>same</em> generation as a caption track. Its times are measured from the start of that audio file, so align the two clips.</li>
<li>For a video on your own web page, use the VTT file in a <code>&lt;track&gt;</code> element.</li>
</ol>
<p>The <a href="/guides/subtitles.html">subtitles guide</a> shows real SRT and VTT output and how the captions are split.</p>

<h2 id="limitations">Limitations</h2>
<ul>
<li>One voice per generation: for several speakers, generate each speaker's lines separately and arrange them in the editor.</li>
<li>No speaking styles, emotions or SSML: pacing comes from punctuation, pause markers and speed.</li>
<li>No voice cloning: only the listed voices are available.</li>
<li>Commercial use is your responsibility; see the <a href="/terms.html">terms of service</a>.</li>
</ul>

<h2 id="related">Related guides</h2>
<ul>
<li><a href="/guides/choose-voice.html">How to choose a text to speech voice and accent</a></li>
<li><a href="/guides/subtitles.html">How to create SRT and VTT subtitles from text</a></li>
<li><a href="/guides/mp3-vs-wav.html">MP3 vs WAV for text to speech</a></li>
<li><a href="/help.html">Help centre</a></li>
</ul>
""")

# ---------------------------------------------------------------- guide: choose a voice
page("guides/choose-voice.html", "Choose a Text to Speech Voice and Accent | Text 2 Speech",
     "Pick the right text to speech voice: match the language, find accents such as British or Indian English, use multilingual voices and compare voices quickly.",
     [HOME, HELP, ("Choose a voice", SITE + "/guides/choose-voice.html")], """
<h1>How to choose a text to speech voice and accent</h1>
<p class="lead"><strong>Short answer:</strong> set <em>Voice Language</em> to the language of your text first, then choose among its voices: the country code after each name (US, GB, IN, AU…) is the accent. Compare two or three with their <em>Preview</em> buttons. For text that mixes languages, try a voice marked <em>(Multilingual)</em>.</p>
""" + toc(("language", "Match the language of your text"), ("accents", "Find an accent"), ("multilingual", "Multilingual voices"),
          ("compare", "Compare voices quickly"), ("limitations", "Limitations"), ("related", "Related pages")) + """
<h2 id="language">Match the language of your text</h2>
<p>A voice reads best in its own language, so the <em>Voice Language</em> list decides which voices you see. When text and voice do not match, the voice may still produce audio (a US English voice read a German sentence in a test) but it is not a voice for that language, or it returns no audio at all when it cannot read the script, as happened with Hindi text and an English voice. All 75 languages and their voices are on the <a href="/voices.html">voices and languages page</a>.</p>

<h2 id="accents">Find an accent</h2>
<p>An accent in Text 2 Speech is a regional variant of a language, shown as the country code after the voice name, such as <q>Sonia - GB</q> for British English. All regional variants of a language appear together under that language. To narrow the list, type a country into <em>Voice Search</em>: <q>United Kingdom</q> or <q>India</q> works, as does a voice name. English voices in the catalog on 31 October 2026:</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Accent</th><th scope="col">Code</th><th scope="col">Voices</th></tr></thead>
<tbody>
<tr><th scope="row">American</th><td>US</td><td>Ana, Andrew, Aria, Ava, Brian, Christopher, Emma, Eric, Guy, Jenny, Michelle, Roger, Steffan, plus Andrew, Ava, Brian and Emma (Multilingual)</td></tr>
<tr><th scope="row">British</th><td>GB</td><td>Libby, Maisie, Ryan, Sonia, Thomas</td></tr>
<tr><th scope="row">Indian</th><td>IN</td><td>Neerja, NeerjaExpressive, Prabhat</td></tr>
<tr><th scope="row">Australian</th><td>AU</td><td>Natasha, William (Multilingual)</td></tr>
<tr><th scope="row">Irish</th><td>IE</td><td>Connor, Emily</td></tr>
<tr><th scope="row">Canadian</th><td>CA</td><td>Clara, Liam</td></tr>
<tr><th scope="row">Also available</th><td>NZ, ZA, SG, PH, HK, NG, KE, TZ</td><td>Two voices each, one female and one male</td></tr>
</tbody></table></div>
<p>Other languages have regional variants too: Spanish has 22 (for example Spain, Mexico and the US), Arabic 16, French 4 (France, Canada, Belgium, Switzerland) and Portuguese 2 (Brazil and Portugal). Hindi, Tamil, Telugu and Urdu voices are listed under their own languages.</p>

<h2 id="multilingual">Multilingual voices</h2>
<p>Multilingual voices are voices that Microsoft names <q>Multilingual</q>: they are intended to read more than one language with the same voice, which suits text that mixes languages. Twelve were in the catalog on 31 October 2026, each listed under its home language:</p>
<ul>
<li>English: Andrew, Ava, Brian and Emma (US), William (AU)</li>
<li>German: Florian, Seraphina</li>
<li>French: Remy, Vivienne</li>
<li>Italian: Giuseppe · Korean: Hyunsu · Portuguese: Thalita (Brazil)</li>
</ul>
<p>Type <q>multilingual</q> into <em>Voice Search</em> to list the ones in the selected language. Test one with a paragraph of your real text before relying on it.</p>

<h2 id="compare">Compare voices quickly</h2>
<ol>
<li>Use the <em>Gender</em> filter to show only female or male voices. Most regional variants (126 of 142 on 31 October 2026) have exactly one female and one male voice.</li>
<li>Press <em>Preview</em> next to each candidate to hear a short sample sentence in that voice.</li>
<li>Generate the same first paragraph of your text with your two or three favourites. Each result is labelled with its voice name, so you can play them one after another.</li>
<li>Keep the winner, and use the same voice, speed and pitch for every part of the project.</li>
</ol>
<p>The <em>Preview Audio</em> button under the text box is not a voice sample: it uses your device's own voice. See the <a href="/help.html#no-sound-preview">help centre</a> for details.</p>

<h2 id="limitations">Limitations</h2>
<ul>
<li>You cannot create, clone or upload a voice; only catalog voices are available.</li>
<li>A voice can be missing from the list for a while if the speech service stops answering for it.</li>
<li>There are no speaking styles or emotion settings; speed and pitch are the only adjustments.</li>
</ul>

<h2 id="related">Related pages</h2>
<ul>
<li><a href="/voices.html">All voices and languages</a></li>
<li><a href="/guides/ai-voiceover.html">How to make a free AI voiceover from text</a></li>
<li><a href="/guides/text-to-mp3.html">How to convert text to MP3 for free</a></li>
</ul>
""")

# ---------------------------------------------------------------- guide: subtitles
page("guides/subtitles.html", "Create SRT and VTT Subtitles from Text | Text 2 Speech",
     "Turn text into speech and get matching SRT and VTT subtitle files with word-level timing. Step-by-step guide with real example files and SRT vs VTT differences.",
     [HOME, HELP, ("Subtitles guide", SITE + "/guides/subtitles.html")], """
<h1>How to create SRT and VTT subtitles from text</h1>
<p class="lead"><strong>Short answer:</strong> paste your script into <a href="/">Text 2 Speech</a>, pick a voice and press <em>Generate Audio</em>. Every generation comes with two subtitle files, SRT and VTT, timed to the generated speech word by word. Download them next to the audio.</p>
""" + toc(("steps", "Step by step"), ("example", "What the files look like"), ("cues", "How the captions are built"),
          ("srt-or-vtt", "SRT or VTT?"), ("using", "Using the files"), ("troubleshooting", "Troubleshooting")) + """
<h2 id="steps">Step by step</h2>
<ol>
<li>Choose the <em>Voice Language</em> that matches your script, then a voice.</li>
<li>Paste or import your text (up to 5,000 characters). End sentences with punctuation: each sentence becomes its own caption.</li>
<li>Optionally add pauses with <code>[break:500ms]</code> or <code>[break:2s]</code>. Pauses show up as gaps between captions.</li>
<li>Press <em>Generate Audio</em>.</li>
<li>In the result, download the audio and the <strong>⬇ SRT</strong> or <strong>⬇ VTT</strong> file.</li>
</ol>

<h2 id="example">What the files look like</h2>
<p>This is the real output for the script <q>Welcome to the course. In this lesson, you will learn how subtitles are timed. Each cue follows the speech, word by word.</q> with the voice Aria (US):</p>
<h3>SRT</h3>
<pre aria-label="Example SRT file">1
00:00:00,100 --&gt; 00:00:01,300
Welcome to the course.

2
00:00:02,162 --&gt; 00:00:05,125
In this lesson, you will learn how subtitles are timed.

3
00:00:05,988 --&gt; 00:00:08,662
Each cue follows the speech, word by word.</pre>
<h3>VTT</h3>
<pre aria-label="Example VTT file">WEBVTT

00:00:00.100 --&gt; 00:00:01.300
Welcome to the course.

00:00:02.162 --&gt; 00:00:05.125
In this lesson, you will learn how subtitles are timed.

00:00:05.988 --&gt; 00:00:08.662
Each cue follows the speech, word by word.</pre>

<h2 id="cues">How the captions are built</h2>
<p>Captions are built from the word timings the speech engine reports, so each one starts with its first spoken word and ends with its last.</p>
<ul>
<li><strong>Splitting:</strong> a new caption starts after a sentence ends (<code>.</code> <code>!</code> <code>?</code> and their CJK forms) or after ten words, whichever comes first. Common abbreviations such as "Dr." do not end a caption.</li>
<li><strong>Text:</strong> captions keep your original punctuation, and Chinese or Japanese text is joined without extra spaces.</li>
<li><strong>Pause markers:</strong> never appear in the captions; they only widen the gap between two captions.</li>
</ul>

<h2 id="srt-or-vtt">SRT or VTT?</h2>
<p>SRT and VTT contain the same captions and timings; they differ only in layout and in where they are used.</p>
<div class="tablewrap"><table>
<thead><tr><td></td><th scope="col">SRT (.srt)</th><th scope="col">VTT (.vtt)</th></tr></thead>
<tbody>
<tr><th scope="row">First line</th><td>Caption number</td><td><code>WEBVTT</code> header</td></tr>
<tr><th scope="row">Time format</th><td><code>00:00:01,300</code> (comma)</td><td><code>00:00:01.300</code> (full stop)</td></tr>
<tr><th scope="row">Typical use</th><td>Video editors, media players, video platforms</td><td>HTML5 video on web pages (<code>&lt;track&gt;</code>)</td></tr>
</tbody></table></div>

<h2 id="using">Using the files</h2>
<ul>
<li><strong>Web page:</strong> <code>&lt;video src="voiceover.mp4" controls&gt;&lt;track kind="captions" src="subtitles.vtt" srclang="en" label="English" default&gt;&lt;/video&gt;</code></li>
<li><strong>Video platforms and editors:</strong> most accept an SRT upload as a caption track; use the file from the same generation as the audio you place on the timeline.</li>
<li><strong>Media players:</strong> load the SRT next to the video file; many players pick it up automatically when it has the same file name.</li>
</ul>

<h2 id="troubleshooting">Troubleshooting</h2>
<ul>
<li><strong>Captions drift:</strong> use the subtitle file from the same generation as the audio. A new generation, even of the same text, can be timed slightly differently.</li>
<li><strong>A caption is too long:</strong> add sentence punctuation; captions break at sentence ends and after ten words.</li>
<li><strong>Nothing was generated:</strong> check that the Voice Language matches the language of your text.</li>
</ul>
<p>More fixes are in the <a href="/help.html#troubleshooting">help centre</a>; the <a href="/guides/ai-voiceover.html">voiceover guide</a> covers the whole script-to-video workflow.</p>
""", published="2026-10-29")

# ---------------------------------------------------------------- guide: MP3 vs WAV
page("guides/mp3-vs-wav.html", "MP3 vs WAV for Text to Speech | Text 2 Speech",
     "MP3 or WAV for a voiceover? Measured file sizes from Text 2 Speech (a 9.5-second clip: 56 KB MP3 vs 447 KB WAV) and when each format is the better choice.",
     [HOME, HELP, ("MP3 vs WAV", SITE + "/guides/mp3-vs-wav.html")], """
<h1>MP3 vs WAV for text to speech</h1>
<p class="lead"><strong>Short answer:</strong> choose <strong>MP3</strong> for almost everything: sharing, web pages, e-learning and podcast drafts. It is about eight times smaller and sounds the same for speech. Choose <strong>WAV</strong> when an editing tool or workflow requires uncompressed audio.</p>

<h2 id="measured">Measured on Text 2 Speech</h2>
<p>The same 9.53-second clip (voice Aria, US), generated on 29 October 2026:</p>
<div class="tablewrap"><table>
<thead><tr><td></td><th scope="col">MP3</th><th scope="col">WAV</th></tr></thead>
<tbody>
<tr><th scope="row">File size (9.53 s)</th><td>57,693 bytes (≈ 56 KB)</td><td>457,422 bytes (≈ 447 KB)</td></tr>
<tr><th scope="row">Approx. per minute of speech</th><td>≈ 0.36 MB</td><td>≈ 2.9 MB</td></tr>
<tr><th scope="row">Encoding</th><td>MP3, 48 kbps, 24 kHz, mono</td><td>16-bit PCM, 24 kHz, mono (384 kbps)</td></tr>
<tr><th scope="row">Plays in</th><td>Practically every browser, phone and player</td><td>Practically every browser, editor and player</td></tr>
</tbody></table></div>

<h2 id="quality">Does WAV sound better?</h2>
<p>Not here. Text 2 Speech creates the WAV by decoding the generated MP3, so the WAV contains exactly the same sound in an uncompressed container. It does not add detail. Pick WAV for compatibility, for example tools that only import WAV, or to avoid re-compressing an MP3 when you edit and export again. Do not pick it for quality.</p>

<h2 id="when">When to use which</h2>
<ul>
<li><strong>MP3:</strong> sharing a voiceover, embedding audio in a web page, uploading to e-learning or podcast platforms, sending by message or email.</li>
<li><strong>WAV:</strong> importing into a video or audio editor that you will export from again, or any pipeline that requires PCM audio.</li>
</ul>
<p>Both formats come with the same SRT and VTT subtitle files. See the <a href="/guides/subtitles.html">subtitles guide</a>.</p>

<h2 id="sample-rate">Why 24 kHz?</h2>
<p>A 24 kHz sample rate captures frequencies up to 12 kHz, which covers the range that matters for speech intelligibility. It is the format the speech service delivers, so higher rates would only make files bigger.</p>
<p>Step-by-step conversion is in <a href="/guides/text-to-mp3.html">how to convert text to MP3</a>; all formats and limits are in the <a href="/help.html#formats">help centre</a>.</p>
""", published="2026-10-29")

# ---------------------------------------------------------------- voices (rows filled in by server.py at request time)
page("voices.html", "300+ Text to Speech Voices in 75 Languages | Text 2 Speech",
     "Every voice available in Text 2 Speech, grouped by language: 300+ neural voices in 75 languages and regional variants, with female and male voices for each.",
     [HOME, ("Voices & languages", SITE + "/voices.html")], """
<h1>Text to speech voices and languages</h1>
<p class="lead"><!--voices:summary--> Choose the language of your text in <a href="/">the converter</a>, then try two or three voices: voices in the same language can sound very different.</p>
<p>The list comes straight from the speech service and is refreshed daily. Voices that stop producing audio are hidden until they work again. <em>Multilingual</em> voices can read mixed-language text.</p>
<div class="tablewrap"><table class="voices">
<thead><tr><th scope="col">Language</th><th scope="col">Locales</th><th scope="col">Voices</th><th scope="col">Voice names</th></tr></thead>
<tbody><!--voices:rows--></tbody></table></div>
<p>Not sure which to pick? <a href="/guides/choose-voice.html">How to choose a voice and accent</a> explains accents and multilingual voices, and the <a href="/help.html">help centre</a> covers limits and formats.</p>
""", kind=None)


# ---------------------------------------------------------------- checks
class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heads, self.ids, self.links, self.lds, self.paras = [], [], [], [], []
        self._ld = self._p = None
        self.title = self.desc = ""
        self._t = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if re.fullmatch(r"h[1-6]", tag):
            self.heads.append(int(tag[1]))
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if tag == "script" and a.get("type") == "application/ld+json":
            self._ld = ""
        if tag in ("p", "li", "td") and self._p is None:
            self._p, self._ptag = "", tag
        if tag == "title":
            self._t = True
        if tag == "meta" and a.get("name") == "description":
            self.desc = a["content"]

    def handle_endtag(self, tag):
        if tag == "script" and self._ld is not None:
            self.lds.append(json.loads(self._ld))
            self._ld = None
        if self._p is not None and tag == self._ptag:
            self.paras.append(re.sub(r"\s+", " ", self._p).strip())
            self._p = None
        if tag == "title":
            self._t = False

    def handle_data(self, d):
        if self._ld is not None:
            self._ld += d
        if self._p is not None:
            self._p += d
        if self._t:
            self.title += d


def scan(text):
    s = Scan()
    s.feed(text)
    return s


ROUTES = {"/", "/es/", "/de/", "/zh-CN/"}  # served by server.py, not files in web/
problems, seen = [], {}
others = {str(p.relative_to("web")).replace("\\", "/"): p.read_text(encoding="utf-8")
          for p in pathlib.Path("web").rglob("*.html")}
home = json.loads(pathlib.Path("web/i18n-home/en.json").read_text(encoding="utf-8"))
for t in [f["a"] for f in home["faq"]] + [x["b"] for x in home["steps"]] + [u["p"] for u in home["usecases"]]:
    seen.setdefault(re.sub(r"\s+", " ", t).strip(), []).append("home (i18n-home/en.json)")
for path, text in {**others, **pages}.items():  # other pages count for duplicates only
    s = scan(text)
    for para in s.paras:
        if len(para) >= 80:
            seen.setdefault(para, []).append(path)
    if path not in pages:
        continue
    if s.heads.count(1) != 1:
        problems.append(f"{path}: {s.heads.count(1)} h1")
    if any(b - a > 1 for a, b in zip(s.heads, s.heads[1:])):
        problems.append(f"{path}: skipped heading level {s.heads}")
    if len(s.ids) != len(set(s.ids)):
        problems.append(f"{path}: duplicate ids")
    if not 120 <= len(s.desc) <= 160:
        problems.append(f"{path}: description is {len(s.desc)} chars")
    if len(s.title) > 60:
        problems.append(f"{path}: title is {len(s.title)} chars")
    for href in s.links:
        if href.startswith("#"):
            if href[1:] not in s.ids:
                problems.append(f"{path}: missing anchor {href}")
        elif href.startswith("/"):
            target, _, frag = href.partition("#")
            f = pathlib.Path("web") / target.lstrip("/")
            if target not in ROUTES and not f.is_file():
                problems.append(f"{path}: broken link {href}")
            elif frag and target.lstrip("/") in pages and frag not in scan(pages[target.lstrip("/")]).ids:
                problems.append(f"{path}: missing anchor {href}")
problems += [f"duplicate paragraph on {where}: {para[:70]}…" for para, where in seen.items() if len(where) > 1]
assert not problems, "\n".join(problems)
print("checks passed:", len(pages), "pages; no duplicate paragraphs across", len({**others, **pages}), "HTML files")
