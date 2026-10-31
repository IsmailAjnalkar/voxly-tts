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
    "figure{margin:18px 0}figure img{display:block;max-width:100%;height:auto;border:1px solid var(--line);border-radius:10px}"
    "figcaption{color:var(--muted);font-size:14px;line-height:1.5;margin-top:6px}"
    ".cta a{display:inline-block;background:var(--accent);color:var(--on-accent);border-radius:10px;padding:10px 18px;font-weight:700;text-decoration:none}"
    "</style>")
boot = re.search(r"<script>if\(localStorage.*?</script>", tpl).group(0)
icons = re.search(r'<link rel="icon" href="/favicon.svg".*?<link rel="apple-touch-icon"[^>]*>', tpl).group(0)
header = re.search(r"<header>.*?</header>", tpl, re.S).group(0)
footer = re.search(r"<footer>.*?</footer>", tpl, re.S).group(0)
main_tag = re.search(r"<main[^>]*>", tpl).group(0)  # keeps id="main" for the skip link
A = lambda t: html.escape(t, quote=True)
ORG = {"@type": "Organization", "@id": SITE + "/#org", "name": "Text 2 Speech", "legalName": "QINTAR LLC", "url": SITE + "/",
       "logo": {"@type": "ImageObject", "url": SITE + "/logo.png"}}
pages = {}  # path -> html, for the checks


def human(d):
    return f"{date.fromisoformat(d).day} {date.fromisoformat(d):%B %Y}"


def page(path, title, desc, crumbs, body, kind="TechArticle", published=UPDATED, image=None):
    """image: a screenshot in web/img/ that illustrates the article (its TechArticle image)."""
    url = f"{SITE}/{path}"
    headline = title.split(" | ")[0]
    ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(crumbs, 1)]}]
    if kind == "TechArticle":
        ld.append({"@context": "https://schema.org", "@type": "TechArticle", "headline": headline,
                   "description": desc, "url": url, "inLanguage": "en", "datePublished": published, "dateModified": UPDATED,
                   "author": ORG, "publisher": ORG, "image": f"{SITE}/img/{image}" if image else SITE + "/og-image.png?v=2",
                   "mainEntityOfPage": url})
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


def fig(name, w, h, alt, caption):
    """A real screenshot from web/img/ (captured from the app with Playwright, see CONTENT_CHANGES_NOV.md)."""
    return (f'<figure><img src="/img/{name}" width="{w}" height="{h}" alt="{A(alt)}" loading="lazy" decoding="async">'
            f"<figcaption>{caption}</figcaption></figure>")


CTA = '<p class="cta"><a href="/">Open the free text to speech tool</a></p>'
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
<p>Text 2 Speech is operated by QINTAR LLC, the company that owns the site and its content (© 2026 QINTAR LLC). Questions for the team go through the <a href="/support.html">support form</a>.</p>

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
<li><a href="/text-to-speech-download.html">Text to speech download: save speech as MP3 or WAV</a></li>
<li><a href="/text-to-voice.html">Text to voice: language, accent, speed, pitch and pauses</a></li>
<li><a href="/ai-voice-generator.html">Free AI voice generator from text: what it can and cannot do</a></li>
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
""" + toc(("steps", "Steps"), ("mp3-file", "What the MP3 file contains"), ("worked-example", "Worked example: a 930-character passage"),
          ("estimate", "Estimate length and size before you convert"), ("prepare", "Prepare the text for a clean MP3"),
          ("long-text", "Text longer than 5,000 characters"), ("troubleshooting", "Troubleshooting"),
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
""" + fig("text-to-mp3-result.webp", 818, 286,
          "Results panel of Text 2 Speech with a finished 8-second MP3 by the voice Ryan (GB): an audio player, the buttons ⬇ MP3, ⬇ SRT and ⬇ VTT, and a Delete button",
          "A finished result. Play it in the page first, then save it with <strong>⬇ MP3</strong>; the SRT and VTT buttons save its subtitles.") + """

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
<p>WAV is also available, but it is about eight times larger and sounds the same; <a href="/guides/mp3-vs-wav.html">MP3 vs WAV</a> explains when it is worth it. Everything about saving the files, from subtitle downloads to file names and the download folder, is collected on the <a href="/text-to-speech-download.html">text to speech download</a> page.</p>

<h2 id="worked-example">Worked example: a 930-character passage</h2>
<p>To show what a typical conversion produces, an English passage of 930 characters (eight sentences, a notice about a library reading programme) was converted with the voice Aria (US) on 31 October 2026, in three versions:</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Version</th><th scope="col">Audio length</th><th scope="col">File size</th></tr></thead>
<tbody>
<tr><th scope="row">MP3, normal speed</th><td>56.6 s</td><td>340,365 bytes (≈ 332 KB)</td></tr>
<tr><th scope="row">WAV, normal speed</th><td>56.6 s</td><td>2,718,798 bytes (≈ 2.6 MB)</td></tr>
<tr><th scope="row">MP3, speed −20%</th><td>70.8 s</td><td>425,181 bytes (≈ 415 KB)</td></tr>
</tbody></table></div>
<p>Three things follow from it. The size of an MP3 depends on how long the audio is, not on how many characters went in, so slowing the voice down makes the file bigger. The WAV holds exactly the same 56.6 seconds in eight times the space. And the subtitle files of that generation split the eight sentences into 20 captions, because a caption also closes after ten words.</p>

<h2 id="estimate">Estimate length and size before you convert</h2>
<p>At normal speed, English came out at roughly 15 to 16 characters per second of speech in these tests (930 characters in 56.6 seconds, 5,000 in 5 minutes 28 seconds), and the 48 kbps MP3 takes 6 KB for every second of audio. Multiplying the two gives a quick estimate for any text:</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Text</th><th scope="col">Speech at normal speed</th><th scope="col">MP3 size</th></tr></thead>
<tbody>
<tr><th scope="row">1,000 characters</th><td>About 1 minute</td><td>About 0.4 MB</td></tr>
<tr><th scope="row">5,000 characters (one generation)</th><td>About 5½ minutes</td><td>About 2 MB</td></tr>
<tr><th scope="row">20,000 characters (four parts)</th><td>About 22 minutes</td><td>About 8 MB</td></tr>
<tr><th scope="row">50,000 characters (ten parts)</th><td>About 55 minutes</td><td>About 20 MB</td></tr>
</tbody></table></div>
<p>These are English figures for one voice. Other voices speak faster or slower (six English voices are compared in the <a href="/guides/choose-voice.html#pace">voice guide</a>), and other languages differ again, so treat the table as a starting point: each result shows the real length of its file.</p>

<h2 id="prepare">Prepare the text for a clean MP3</h2>
<ul>
<li><strong>Check pasted text for stray lines.</strong> Text copied from a web page or a document often brings menu items, captions or page numbers with it, and the voice reads whatever is in the box.</li>
<li><strong>Clean up imported Markdown.</strong> <em>Import File</em> loads a <code>.md</code> file as-is, so symbols such as <code>#</code>, <code>*</code> and link brackets stay in the text. Remove them before generating so the voice only gets the words.</li>
<li><strong>End headings with a full stop.</strong> A line break alone does not end a caption: a heading without punctuation is joined to the next sentence in the subtitle files.</li>
<li><strong>Spell out what must be heard exactly.</strong> If a voice reads a date, a time or an abbreviation differently from what you intended, write it the way it should sound, for example <q>half past ten</q> instead of <q>10:30</q>.</li>
<li><strong>Watch the counter.</strong> It shows how many of the 5,000 characters you have used; pause markers and spaces count too.</li>
</ul>

<h2 id="long-text">Text longer than 5,000 characters</h2>
<p>To turn a longer document, such as a book chapter, into MP3, convert it in parts and join them afterwards:</p>
<ol>
<li>Split the text at paragraph or section breaks into parts of up to 5,000 characters.</li>
<li>Convert each part with the same voice, speed and pitch, so the parts sound alike.</li>
<li>Download and rename each file in order (<code>part-01.mp3</code>, <code>part-02.mp3</code>…) before the two-hour expiry.</li>
<li>Join the files in an audio editor, or simply play them as a playlist.</li>
</ol>

<h2 id="troubleshooting">Troubleshooting</h2>
<h3 id="generate-disabled">Generate Audio stays greyed out</h3>
<p>The button is disabled while the text box is empty, while another generation is still running, and whenever the text is over 5,000 characters (the counter turns red then). Shorten the text or split it as described above.</p>
<h3 id="wav-button">The result has a ⬇ WAV button, not ⬇ MP3</h3>
<p>The format is fixed when you press <em>Generate Audio</em>, and that result was made while <em>WAV</em> was selected. Click <em>MP3</em> under <em>Output Format</em> and generate again; the WAV result stays in the list until you delete it.</p>
<h3 id="link-gone">The result or its download buttons have disappeared</h3>
<p>Results are tied to the browser tab, and the server deletes the files about two hours after your last generation. Generate the text again and save the MP3 right away; the <a href="/help.html#files-expired">help centre</a> explains the rules.</p>
<h3 id="no-result">An error appears instead of a result</h3>
<p>The two most common messages are a rate-limit warning (wait a minute, your text stays in the box) and <q>The speech service returned no audio for this text</q>, which usually means the voice does not match the language of the text. Both are covered in the <a href="/help.html#troubleshooting">help centre</a>.</p>
<h3 id="tempo-off">The MP3 sounds faster or slower than the sample</h3>
<p>Look at the <em>Speed</em> checkbox: a value set for an earlier conversion still applies while the box is ticked. Untick it, or set it back to 0, and generate again. Pitch works the same way.</p>
<h3 id="name-wrong">A name or a foreign word is mispronounced</h3>
<p>Write the word the way it sounds in the language of the voice, for example with an added hyphen or a phonetic spelling, and test just that sentence before converting the whole text. A short test generation takes a few seconds and saves regenerating thousands of characters.</p>

<h2 id="limitations">Limitations</h2>
<ul>
<li>One voice per file: for a dialogue, convert each speaker's lines separately.</li>
<li>The input is plain text; the tool cannot open PDF, Word or web pages.</li>
<li>Files are not stored long-term and there is no account history.</li>
</ul>
<p>The complete list is in the <a href="/help.html#limitations">help centre</a>.</p>

<h2 id="related">Related guides</h2>
<ul>
<li><a href="/text-to-speech-download.html">Text to speech download: MP3, WAV and subtitle files</a></li>
<li><a href="/guides/choose-voice.html">How to choose a text to speech voice and accent</a></li>
<li><a href="/guides/ai-voiceover.html">How to make a free AI voiceover from text</a></li>
<li><a href="/guides/subtitles.html">How to create SRT and VTT subtitles from text</a></li>
</ul>
""", image="text-to-mp3-result.webp")

# ---------------------------------------------------------------- guide: AI voiceover
page("guides/ai-voiceover.html", "How to Make a Free AI Voiceover from Text | Text 2 Speech",
     "Make a voiceover from a script for free: pick a neural voice, pace it with pause markers, generate it scene by scene and add matching SRT subtitles to video.",
     [HOME, HELP, ("AI voiceover", SITE + "/guides/ai-voiceover.html")], """
<h1>How to make a free AI voiceover from text</h1>
<p class="lead"><strong>Short answer:</strong> write the script, paste it into <a href="/">Text 2 Speech</a>, choose a neural voice, add <code>[break:…]</code> markers where the narration should pause, and press <em>Generate Audio</em>. You get the voiceover as an MP3 or WAV file plus SRT and VTT subtitles timed to it, ready to place on a video timeline.</p>
""" + toc(("script", "Prepare the script"), ("pauses", "Pace it with pauses"), ("steps", "Generate the voiceover"),
          ("worked-example", "Worked example: a three-scene explainer"), ("speed", "Adjust speed and pitch"),
          ("fit", "Fit a voiceover to a fixed length"), ("video", "Add it to a video"), ("troubleshooting", "Troubleshooting"),
          ("limitations", "Limitations"), ("related", "Related guides")) + """
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
""" + fig("voiceover-break-markers.webp", 818, 432,
          "The Input Text box of Text 2 Speech holding a short course script with the pause markers [break:1s], [break:500ms] and [break:2s] between sentences; the counter reads 213 / 5000 characters",
          "Pause markers typed straight into the script. They count toward the 5,000 characters but are never spoken.") + """

<h2 id="steps">Generate the voiceover</h2>
<ol>
<li>Choose the <em>Voice Language</em> of the script and pick a narrator; listen to two or three with their <em>Preview</em> buttons.</li>
<li>Paste the first scene into <em>Input Text</em> and add your pause markers.</li>
<li>Choose MP3, or WAV if your video editor prefers it, and press <em>Generate Audio</em>.</li>
<li>Listen to the result. To change a line, edit the text and generate again; each version stays in the results list.</li>
<li>Download the audio and the <strong>⬇ SRT</strong> file of the version you keep, and rename both with the scene number.</li>
<li>Repeat for each scene with the same voice, speed and pitch.</li>
</ol>

<h2 id="worked-example">Worked example: a three-scene explainer</h2>
<p>This short explainer about watering houseplants was generated scene by scene with the voice Aria (US) at normal speed on 31 October 2026. The script, exactly as typed:</p>
<pre aria-label="Example script">Scene 1: Most houseplants die from too much water, not too little.[break:1s] In the next minute, you will learn a simple test that tells you exactly when to water.

Scene 2: Push one finger into the soil, up to the second knuckle.[break:500ms] If the soil feels dry at your fingertip, water slowly until it runs out of the drainage holes.[break:500ms] If it still feels damp, wait two or three days and test again.

Scene 3: That is the whole method.[break:1s] Test first, water second, and check again next week.</pre>
<p>Each scene was pasted on its own, without the <q>Scene</q> label. To see what the markers add, every scene was also generated once with the markers removed:</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Scene</th><th scope="col">Characters</th><th scope="col">Markers</th><th scope="col">Audio length</th><th scope="col">Without markers</th><th scope="col">Captions</th></tr></thead>
<tbody>
<tr><th scope="row">1 · Hook</th><td>154</td><td>1 × 1 s</td><td>10.8 s</td><td>9.7 s</td><td>3</td></tr>
<tr><th scope="row">2 · Method</th><td>240</td><td>2 × 500 ms</td><td>15.9 s</td><td>14.6 s</td><td>6</td></tr>
<tr><th scope="row">3 · Close</th><td>88</td><td>1 × 1 s</td><td>7.6 s</td><td>6.5 s</td><td>2</td></tr>
</tbody></table></div>
<p>The three files add up to 34.3 seconds. Each one-second marker lengthened its scene by about 1.1 seconds, and the two half-second markers together by 1.2 seconds, so plan for slightly more silence than you type. Scene 2 produced six captions from three sentences because long sentences are split after ten words. Saved as <code>scene-01.mp3</code>/<code>scene-01.srt</code> and so on, the files drop onto a timeline in order. To write a script for a target length, use the characters-per-second planner on the <a href="/ai-voice-generator.html#planner">AI voice generator</a> page.</p>

<h2 id="speed">Adjust speed and pitch</h2>
<p>Speed changes how fast the voice talks, from −100% to +100%, without changing the words. In a test, +50% made a sentence play in two-thirds of the time (5.1 s to 3.5 s) and −50% made it twice as long (10.2 s). Pitch moves the voice up or down by up to 100 Hz. The slider moves in steps of 5; type any whole value into the number box next to it.</p>

<h2 id="fit">Fit a voiceover to a fixed length</h2>
<p>Speed works in proportion: the new length is roughly the normal length divided by (1 + speed ÷ 100). Measured examples:</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Speed</th><th scope="col">Length compared with normal</th><th scope="col">Measured</th></tr></thead>
<tbody>
<tr><th scope="row">−50%</th><td>× 2.0</td><td>A sentence went from 5.1 s to 10.2 s</td></tr>
<tr><th scope="row">−20%</th><td>× 1.25</td><td>A passage went from 56.6 s to 70.8 s</td></tr>
<tr><th scope="row">+10%</th><td>× 0.91</td><td>Scene 2 above went from 15.9 s to 14.5 s</td></tr>
<tr><th scope="row">+50%</th><td>× 0.67</td><td>A sentence went from 5.1 s to 3.5 s</td></tr>
</tbody></table></div>
<p>When a scene has to fill an exact slot, such as a 15-second clip, work in this order: generate at normal speed and read the length in the result; close a small gap with speed in steps of 5 or 10; close a large gap by cutting or adding a sentence, which sounds more natural than a big speed change; and fine-tune with pause markers, whose length is exact. Voices also differ in pace, by about a fifth between the fastest and slowest English voices in the <a href="/guides/choose-voice.html#pace">voice guide's measurement</a>, so choose the voice before you time anything.</p>

<h2 id="video">Add it to a video</h2>
<ol>
<li>Import the audio file into your video editor and place it on the timeline.</li>
<li>Import the SRT file from the <em>same</em> generation as a caption track. Its times are measured from the start of that audio file, so align the two clips.</li>
<li>For a video on your own web page, use the VTT file in a <code>&lt;track&gt;</code> element.</li>
</ol>
<p>The <a href="/guides/subtitles.html">subtitles guide</a> shows real SRT and VTT output and how the captions are split.</p>

<h2 id="troubleshooting">Troubleshooting</h2>
<h3 id="marker-spoken">A pause marker was read aloud</h3>
<p>Only markers in the form <code>[break:</code> number <code>ms]</code> or <code>[break:</code> number <code>s]</code> become silence; anything else is ordinary text and is spoken. Upper case and spaces inside the brackets are fine.</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Typed</th><th scope="col">Result</th></tr></thead>
<tbody>
<tr><th scope="row"><code>[break:750ms]</code>, <code>[break:1.5s]</code>, <code>[BREAK: 2 s]</code></th><td>Silence</td></tr>
<tr><th scope="row"><code>[pause:1s]</code>, <code>(break:1s)</code></th><td>Read as text: wrong word or brackets</td></tr>
<tr><th scope="row"><code>[break:1sec]</code>, <code>[break:1m]</code></th><td>Read as text: only <code>ms</code> and <code>s</code> are units</td></tr>
<tr><th scope="row"><code>[break:1,5s]</code></th><td>Read as text: use a full stop for decimals</td></tr>
</tbody></table></div>
<h3 id="scene-sounds-different">One scene sounds different from the others</h3>
<p>Check that every scene used the same voice, speed and pitch: the settings stay as you left them, but a ticked or unticked <em>Speed</em> box is easy to miss. Each result shows its voice name, so compare the labels in the results list.</p>
<h3 id="captions-early">Captions appear before the voice starts</h3>
<p>The subtitle times start at the beginning of the audio file. If you trimmed silence from the start of the clip in your editor, or moved the audio without the captions, shift the caption track by the same amount.</p>
<h3 id="error-too-many">"Too many [break] markers" or "Total pause length exceeds 60 s"</h3>
<p>A generation allows 25 markers and 60 seconds of pauses altogether. Split the scene in two, or leave longer silences to the video editor.</p>

<h2 id="limitations">Limitations</h2>
<ul>
<li>One voice per generation: for several speakers, generate each speaker's lines separately and arrange them in the editor.</li>
<li>No speaking styles, emotions or SSML: pacing comes from punctuation, pause markers and speed.</li>
<li>No voice cloning: only the listed voices are available.</li>
<li>Commercial use is your responsibility; see the <a href="/terms.html">terms of service</a>.</li>
</ul>

<h2 id="related">Related guides</h2>
<ul>
<li><a href="/ai-voice-generator.html">Free AI voice generator from text: what it can and cannot do</a></li>
<li><a href="/guides/choose-voice.html">How to choose a text to speech voice and accent</a></li>
<li><a href="/guides/subtitles.html">How to create SRT and VTT subtitles from text</a></li>
<li><a href="/guides/mp3-vs-wav.html">MP3 vs WAV for text to speech</a></li>
<li><a href="/help.html">Help centre</a></li>
</ul>
""", image="voiceover-break-markers.webp")

# ---------------------------------------------------------------- guide: choose a voice
page("guides/choose-voice.html", "Choose a Text to Speech Voice and Accent | Text 2 Speech",
     "Pick the right text to speech voice: match the language, find accents such as British or Indian English, use multilingual voices and compare voices quickly.",
     [HOME, HELP, ("Choose a voice", SITE + "/guides/choose-voice.html")], """
<h1>How to choose a text to speech voice and accent</h1>
<p class="lead"><strong>Short answer:</strong> set <em>Voice Language</em> to the language of your text first, then choose among its voices: the country code after each name (US, GB, IN, AU…) is the accent. Compare two or three with their <em>Preview</em> buttons. For text that mixes languages, try a voice marked <em>(Multilingual)</em>.</p>
""" + toc(("language", "Match the language of your text"), ("accents", "Find an accent"), ("per-language", "How many voices each language has"),
          ("multilingual", "Multilingual voices"), ("compare", "Compare voices quickly"), ("pace", "Measured: voices speak at different speeds"),
          ("by-use", "Choose by purpose"), ("troubleshooting", "Troubleshooting"), ("limitations", "Limitations"),
          ("related", "Related pages")) + """
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
""" + fig("choose-voice-british.webp", 1176, 539,
          "Voice settings in Text 2 Speech: Voice Language set to English, the Female filter on and United Kingdom typed into Voice Search, listing Libby, Maisie and Sonia (GB) with Sonia selected",
          "Typing <q>United Kingdom</q> with the <em>Female</em> filter on narrows the 47 English voices to three British ones.") + """

<h2 id="per-language">How many voices each language has</h2>
<p>The choice depends a lot on the language. On 31 October 2026, 60 of the 75 languages had exactly two voices, one female and one male; a few had many more:</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Language</th><th scope="col">Voices</th><th scope="col">Regional variants</th></tr></thead>
<tbody>
<tr><th scope="row">English</th><td>47</td><td>14, listed in the table above</td></tr>
<tr><th scope="row">Spanish</th><td>45</td><td>22, including Spain, Mexico, Argentina, Colombia and the US</td></tr>
<tr><th scope="row">Arabic</th><td>32</td><td>16, from Morocco to Oman</td></tr>
<tr><th scope="row">Chinese</th><td>14</td><td>Mainland China, Hong Kong and Taiwan, plus one Liaoning and one Shaanxi dialect voice</td></tr>
<tr><th scope="row">French</th><td>13</td><td>France, Canada, Belgium, Switzerland</td></tr>
<tr><th scope="row">German</th><td>10</td><td>Germany, Austria, Switzerland</td></tr>
<tr><th scope="row">Tamil</th><td>8</td><td>India, Sri Lanka, Malaysia, Singapore</td></tr>
<tr><th scope="row">Dutch</th><td>5</td><td>Netherlands, Belgium</td></tr>
<tr><th scope="row">Portuguese</th><td>5</td><td>Brazil, Portugal</td></tr>
</tbody></table></div>
<p>Hindi, Japanese and most other languages are in the two-voice group, where choosing takes a minute: listen to both. Hindi, Tamil, Telugu and Urdu each have their own entry in the language list rather than appearing under English.</p>

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

<h2 id="pace">Measured: voices speak at different speeds</h2>
<p>Voices differ in pace as well as in sound. The sentence <q>Thank you for calling. Your appointment is confirmed for Tuesday at ten in the morning.</q> was generated with six English voices at normal speed on 31 October 2026:</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Voice</th><th scope="col">Accent</th><th scope="col">Length</th></tr></thead>
<tbody>
<tr><th scope="row">Sonia</th><td>British (GB)</td><td>5.62 s</td></tr>
<tr><th scope="row">Ryan</th><td>British (GB)</td><td>5.98 s</td></tr>
<tr><th scope="row">Guy</th><td>American (US)</td><td>6.00 s</td></tr>
<tr><th scope="row">Aria</th><td>American (US)</td><td>6.05 s</td></tr>
<tr><th scope="row">Natasha</th><td>Australian (AU)</td><td>6.58 s</td></tr>
<tr><th scope="row">Neerja</th><td>Indian (IN)</td><td>6.79 s</td></tr>
</tbody></table></div>
<p>The slowest voice needed 21% more time than the fastest for the same words. Over a five-minute narration a gap like that would come to about a minute, so when audio has to fit a fixed length, settle on the voice first and adjust the speed afterwards. Pitch, by contrast, does not change the timing: Aria measured 6.05 s at −50 Hz, 0 and +50 Hz. How speed and pitch shape a voice is explained on the <a href="/text-to-voice.html#speed-pitch">text to voice</a> page.</p>

<h2 id="by-use">Choose by purpose</h2>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Purpose</th><th scope="col">What to listen for</th><th scope="col">How to test</th></tr></thead>
<tbody>
<tr><th scope="row">Video voiceover</th><td>Clear words at the speed you plan to use</td><td>Generate the first scene with your two or three favourites</td></tr>
<tr><th scope="row">Lessons and training</th><td>The accent your learners expect; comfort at a slightly slower speed</td><td>Try the same paragraph at −10% and −20%</td></tr>
<tr><th scope="row">Phone or announcement prompts</th><td>Names, numbers and times read the way you intend</td><td>Generate the trickiest line first</td></tr>
<tr><th scope="row">Long reading, such as chapters</th><td>Whether the voice stays pleasant after several minutes</td><td>Listen to a full minute, not just the sample</td></tr>
<tr><th scope="row">Mixed-language text</th><td>Correct pronunciation in both languages</td><td>A multilingual voice with a real paragraph</td></tr>
<tr><th scope="row">Language practice</th><td>The regional variant you are learning</td><td>Compare, for example, GB with US, or Spain with Mexico</td></tr>
</tbody></table></div>

<h2 id="troubleshooting">Troubleshooting</h2>
<h3 id="no-match">"No voices match your search"</h3>
<p>The language, the <em>Gender</em> filter and the search text all apply at once. Clear <em>Voice Search</em> and set <em>Gender</em> to <em>All</em>. Search looks at the voice name, the country code, the full country name and the language, so with English selected <q>Ireland</q> finds Connor and Emily, while a style word such as <q>calm</q> finds nothing.</p>
<h3 id="voice-missing">A voice I used before is missing</h3>
<p>Every voice is tested every six hours, and one that fails eight checks in a row is hidden until it works again. Choose a similar voice for now; keep a note of the voice you used for a project so you can match it later.</p>
<h3 id="sample-silent">The ▶ sample does not play</h3>
<p>Each sample is a request to the speech service and counts toward the limit of about 20 requests per minute. After a burst of samples, wait a minute. Also check that the tab is not muted.</p>
<h3 id="wrong-accent">The voice has an odd accent with my text</h3>
<p>The text is probably in a different language from the voice. Switch <em>Voice Language</em> to the language of the text, or use a multilingual voice for text that mixes languages.</p>

<h2 id="limitations">Limitations</h2>
<ul>
<li>You cannot create, clone or upload a voice; only catalog voices are available.</li>
<li>A voice can be missing from the list for a while if the speech service stops answering for it.</li>
<li>There are no speaking styles or emotion settings; speed and pitch are the only adjustments.</li>
</ul>

<h2 id="related">Related pages</h2>
<ul>
<li><a href="/voices.html">All voices and languages</a></li>
<li><a href="/text-to-voice.html">Text to voice: language, accent, speed, pitch and pauses</a></li>
<li><a href="/guides/ai-voiceover.html">How to make a free AI voiceover from text</a></li>
<li><a href="/guides/text-to-mp3.html">How to convert text to MP3 for free</a></li>
</ul>
""", image="choose-voice-british.webp")

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

# ---------------------------------------------------------------- landing: text to speech download
page("text-to-speech-download.html", "Text to Speech Download: Save Speech as MP3 or WAV",
     "Download text to speech as MP3 or WAV with SRT and VTT subtitles, free: how to save the files, what they are called and how to split text over 5,000 characters.",
     [HOME, ("Text to speech download", SITE + "/text-to-speech-download.html")], """
<h1>Text to speech download: save speech as MP3 or WAV</h1>
<p class="lead"><strong>Short answer:</strong> paste your text into <a href="/">Text 2 Speech</a>, pick a voice and an output format, press <em>Generate Audio</em>, then click <strong>⬇ MP3</strong> (or <strong>⬇ WAV</strong>) in the result to save the speech as a file. <strong>⬇ SRT</strong> and <strong>⬇ VTT</strong> save subtitles that match it. Downloading is free with no sign-up; each generation takes up to 5,000 characters, and the files stay online for about two hours.</p>
""" + CTA + toc(("steps", "How to download speech as an audio file"), ("format", "MP3 or WAV: which download to choose"),
                ("subtitles", "Download the subtitles as well"), ("names", "File names and where the files go"),
                ("long-texts", "Downloading long texts"), ("retention", "How long downloads stay available"),
                ("problems", "Download problems"), ("limitations", "Limitations"), ("related", "Related pages")) + """
<h2 id="steps">How to download speech as an audio file</h2>
<ol>
<li>Open the <a href="/">converter</a>, set <em>Voice Language</em> to the language of your text and click a voice.</li>
<li>Under <em>Output Format</em>, choose <strong>MP3</strong> (the default) or <strong>WAV</strong>. Do this before generating: a finished result keeps the format it was made in.</li>
<li>Paste or type your text, up to 5,000 characters, or import a plain-text file.</li>
<li>Press <em>Generate Audio</em> and wait for the result to appear under <em>Results</em>.</li>
<li>Play it once in the page to check names, numbers and pauses.</li>
<li>Click the audio button to save the speech, and <strong>⬇ SRT</strong> or <strong>⬇ VTT</strong> if you need captions.</li>
<li>Rename the files straight away, so you know later which text each one belongs to.</li>
</ol>
""" + fig("download-wav-and-subtitles.webp", 1176, 404,
          "Text 2 Speech with Output Format set to WAV and two results: an 18-second WAV by Aria (US) and an 8-second MP3 by Ryan (GB), each with buttons to download the audio, SRT and VTT",
          "Every result has its own download buttons, and the audio button is labelled with the format that result was generated in.") + """

<h2 id="format">MP3 or WAV: which download to choose</h2>
<p>Pick MP3 unless a program you use insists on WAV. Both hold the same sound, because the WAV is decoded from the generated MP3; the WAV is simply about eight times larger. Measured on the same 56.6-second clip:</p>
<div class="tablewrap"><table>
<thead><tr><td></td><th scope="col">MP3</th><th scope="col">WAV</th></tr></thead>
<tbody>
<tr><th scope="row">Size of the 56.6 s clip</th><td>≈ 332 KB</td><td>≈ 2.6 MB</td></tr>
<tr><th scope="row">Encoding</th><td>48 kbps, 24 kHz, mono</td><td>16-bit PCM, 24 kHz, mono</td></tr>
<tr><th scope="row">Best for</th><td>Sharing, web pages, e-learning platforms, phones</td><td>Audio and video editors, workflows that require PCM</td></tr>
</tbody></table></div>
<p>The reasoning behind that advice, with byte-exact measurements, is in <a href="/guides/mp3-vs-wav.html">MP3 vs WAV for text to speech</a>.</p>

<h2 id="subtitles">Download the subtitles as well</h2>
<p>Each generation also produces two subtitle files, built from the moment each word is spoken: SRT for video editors and media players, VTT for video on web pages. There is nothing extra to switch on. A subtitle file only fits the audio of its own result, since another generation of the same text can be timed slightly differently, so keep each audio file together with its subtitles. Real examples of both formats are in the <a href="/guides/subtitles.html">subtitles guide</a>.</p>

<h2 id="names">File names and where the files go</h2>
<p>Your browser saves the files wherever it saves other downloads, usually the <em>Downloads</em> folder, unless it is set to ask you each time. The names are not taken from your text:</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">File</th><th scope="col">Name when saved</th><th scope="col">Suggested rename</th></tr></thead>
<tbody>
<tr><th scope="row">Audio</th><td>12 random letters and digits, for example <code>c5983b36f65c.wav</code></td><td><code>lesson-01.wav</code></td></tr>
<tr><th scope="row">SRT subtitles</th><td><code>subtitles.srt</code></td><td><code>lesson-01.srt</code></td></tr>
<tr><th scope="row">VTT subtitles</th><td><code>subtitles.vtt</code></td><td><code>lesson-01.vtt</code></td></tr>
</tbody></table></div>
<p>Because every result's subtitles share the same two names, a second download into the same folder is usually renamed by the browser, for example to <code>subtitles (1).srt</code>. Renaming each set as soon as it lands keeps the audio and its captions paired.</p>

<h2 id="long-texts">Downloading long texts</h2>
<p>There is a limit: one generation takes at most 5,000 characters, counting spaces and pause markers, and <em>Generate Audio</em> stays disabled above it. In English that is about five and a half minutes of speech (5,000 characters became 5 minutes 28 seconds in a test), so longer pieces are downloaded as several files:</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Length of the text</th><th scope="col">Files to generate</th><th scope="col">Approximate audio in English</th></tr></thead>
<tbody>
<tr><th scope="row">Up to 5,000 characters</th><td>1</td><td>Up to about 5½ minutes</td></tr>
<tr><th scope="row">12,000 characters</th><td>3</td><td>About 13 minutes</td></tr>
<tr><th scope="row">30,000 characters</th><td>6</td><td>About 33 minutes</td></tr>
<tr><th scope="row">55,000 characters</th><td>11</td><td>About 1 hour</td></tr>
</tbody></table></div>
<p>Split at paragraph or chapter breaks, keep the voice, speed, pitch and format identical for every part, and number the downloads in order. The step-by-step method for joining the parts is in <a href="/guides/text-to-mp3.html#long-text">how to convert text to MP3</a>.</p>

<h2 id="retention">How long downloads stay available</h2>
<p>The files only live on the Text 2 Speech server for a short time: they are deleted about two hours after the last generation in your browser session. The results list belongs to the tab it was made in, so a different tab or window starts empty, and <em>Delete</em> removes a result and its files at once. There is no account or download history, which makes the copy on your own device the one that lasts.</p>

<h2 id="problems">Download problems</h2>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Problem</th><th scope="col">Cause and fix</th></tr></thead>
<tbody>
<tr><th scope="row">The download buttons are gone</th><td>The files expired or the tab was closed. Generate the text again and download at once.</td></tr>
<tr><th scope="row">Generate Audio cannot be pressed</th><td>The text box is empty or over 5,000 characters. Add text, or shorten and split it.</td></tr>
<tr><th scope="row">The audio button says WAV, not MP3</th><td>WAV was selected when that result was made. Choose MP3 and generate again.</td></tr>
<tr><th scope="row">The WAV file is very large</th><td>That is expected: about 2.9 MB per minute. Download MP3 for sharing.</td></tr>
<tr><th scope="row">Subtitles drift away from the audio</th><td>They come from a different generation. Take both files from the same result.</td></tr>
</tbody></table></div>

<h2 id="limitations">Limitations</h2>
<ul>
<li>5,000 characters per generation, so long documents are saved as several files.</li>
<li>Audio comes as MP3 or WAV only; for another format, convert the download with an audio tool.</li>
<li>Files are not kept long-term and there is no history of past downloads.</li>
<li>The tool cannot open PDFs, Word files or web pages; copy their text into the box instead.</li>
<li>Your text is sent to Microsoft's online speech service to create the audio.</li>
</ul>

<h2 id="related">Related pages</h2>
<ul>
<li><a href="/guides/text-to-mp3.html">How to convert text to MP3 for free</a></li>
<li><a href="/guides/mp3-vs-wav.html">MP3 vs WAV for text to speech</a></li>
<li><a href="/guides/subtitles.html">How to create SRT and VTT subtitles from text</a></li>
<li><a href="/help.html#formats">File formats in the help centre</a></li>
</ul>
""", image="download-wav-and-subtitles.webp")

# ---------------------------------------------------------------- landing: text to voice
page("text-to-voice.html", "Text to Voice: Turn Writing into a Natural Voice",
     "Turn text into a natural voice for free: pick the language, accent and voice, then shape it with speed, pitch and exact pauses. Measured examples and limits.",
     [HOME, ("Text to voice", SITE + "/text-to-voice.html")], """
<h1>Text to voice: turn writing into a natural voice</h1>
<p class="lead"><strong>Short answer:</strong> text to voice means typing or pasting writing and getting it back as speech. In <a href="/">Text 2 Speech</a> you set the language of your text, choose one of its voices (each tied to a regional accent), optionally adjust speed, pitch and pauses, and press <em>Generate Audio</em>. It is free, needs no account, and takes up to 5,000 characters per generation.</p>
""" + CTA + toc(("decisions", "What decides how the voice sounds"), ("steps", "Turn text into a voice, step by step"),
                ("language", "Language and accent"), ("voice", "Picking one voice out of several"), ("speed-pitch", "Speed and pitch"),
                ("pauses", "Pauses and pacing"), ("listen", "Listen before you generate"), ("limitations", "Limitations"),
                ("related", "Related pages")) + """
<h2 id="decisions">What decides how the voice sounds</h2>
<p>Six settings shape the result. Only the first two need a decision; the rest default to normal speed, normal pitch and no extra pauses.</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Setting</th><th scope="col">Where to find it</th><th scope="col">What it changes</th></tr></thead>
<tbody>
<tr><th scope="row">Language</th><td><em>Voice Language</em> list</td><td>Which voices are offered; it should match the language of the text</td></tr>
<tr><th scope="row">Voice and accent</th><td>The voice list, a name plus a country code such as <q>Ryan - GB</q></td><td>Timbre, gender and regional accent</td></tr>
<tr><th scope="row">Gender filter</th><td><em>All</em>, <em>Male</em>, <em>Female</em></td><td>Only which voices are listed</td></tr>
<tr><th scope="row">Speed</th><td><em>Speed</em> checkbox and slider, −100% to +100%</td><td>How fast the words come, and so the length</td></tr>
<tr><th scope="row">Pitch</th><td><em>Pitch</em> checkbox and slider, −100 to +100 Hz</td><td>How high or low the voice sits; the timing stays the same</td></tr>
<tr><th scope="row">Pauses</th><td><code>[break:…]</code> markers or <kbd>Ctrl</kbd>+<kbd>B</kbd> in the text</td><td>Exact silences between words or sentences</td></tr>
</tbody></table></div>

<h2 id="steps">Turn text into a voice, step by step</h2>
<ol>
<li>Open the <a href="/">converter</a> and set <em>Voice Language</em> to the language your text is written in.</li>
<li>Click a voice. To shorten the list, use <em>Gender</em> or type a country into <em>Voice Search</em>; press ▶ beside a voice to hear its sample.</li>
<li>Type or paste the text, or import a <code>.txt</code>, <code>.md</code> or <code>.text</code> file.</li>
<li>Tick <em>Speed</em> or <em>Pitch</em> to change them, and type an exact value into the number box if the slider's steps of 5 are too coarse.</li>
<li>Add pauses where a reader would stop for breath or effect.</li>
<li>Press <em>Generate Audio</em>, listen to the result, and download it as MP3 or WAV.</li>
</ol>
""" + fig("text-to-voice-speed-pitch.webp", 1176, 603,
          "Text 2 Speech with the voice Ryan (GB) selected, Speed ticked at −10% and Pitch ticked at 5 Hz, and a finished 8-second MP3 in the results that begins: Chapter one. The old lighthouse stood at the edge of the bay",
          "A British English voice slowed by 10% and raised by 5 Hz. Speed and pitch apply to the whole generation.") + """

<h2 id="language">Language and accent</h2>
<p>Text 2 Speech offers 322 voices in 75 languages and 142 regional variants (catalog of 31 October 2026). The variant is the accent: English alone comes in 14, from American and British to Indian, Nigerian and Kenyan English, and Spanish in 22. The country code after each voice name tells you which one you are hearing.</p>
<p>Match the language before anything else. A voice is made for its own language, and text in another language may come out mispronounced or produce no audio at all. Accents, multilingual voices and a quick way to compare candidates are covered in <a href="/guides/choose-voice.html">how to choose a voice and accent</a>, and every voice is listed on the <a href="/voices.html">voices and languages page</a>.</p>

<h2 id="voice">Picking one voice out of several</h2>
<p>Voices in the same language differ more than you might expect, in sound and in pace: six English voices took between 5.6 and 6.8 seconds to say the same sentence in a measured test. Two habits narrow the choice quickly. First, press ▶ beside each candidate: every voice reads the same sample sentence, so the comparison is fair. Then generate the opening paragraph of your own text with the two or three you liked best; each result is labelled with its voice, so they are easy to play back to back.</p>

<h2 id="speed-pitch">Speed and pitch</h2>
<p>Both controls are off until you tick their checkboxes, and both apply to the whole generation.</p>
<ul>
<li><strong>Speed</strong> (−100% to +100%) changes the tempo and therefore the length of the audio. In a test, −20% stretched a 56.6-second passage to 70.8 seconds. To hit an exact length, use the speed table in the <a href="/guides/ai-voiceover.html#fit">AI voiceover guide</a>.</li>
<li><strong>Pitch</strong> (−100 to +100 Hz) moves the voice higher or lower without changing its timing: one sentence measured 6.05 seconds at −50 Hz, at 0 and at +50 Hz.</li>
</ul>
<p>Small changes sound the most natural. A large pitch shift can make a voice sound processed, so for a clearly different character, choose another voice instead of pushing the pitch slider to its end.</p>

<h2 id="pauses">Pauses and pacing</h2>
<p>Commas and full stops already make the voice pause briefly. For an exact silence, type a marker such as <code>[break:800ms]</code> or <code>[break:2s]</code> where it should go, or press <kbd>Ctrl</kbd>+<kbd>B</kbd> (<kbd>⌘</kbd>+<kbd>B</kbd> on a Mac) to insert half a second at the cursor. Markers are not spoken and do not appear in the subtitles. One generation can hold 25 of them, none longer than 30 seconds and no more than 60 seconds in total.</p>

<h2 id="listen">Listen before you generate</h2>
<p>Three buttons play something, and they do different things:</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Button</th><th scope="col">What you hear</th><th scope="col">Use it for</th></tr></thead>
<tbody>
<tr><th scope="row">▶ beside a voice</th><td>A short sample sentence in that neural voice</td><td>Choosing a voice</td></tr>
<tr><th scope="row"><em>Preview Audio</em></th><td>The first 1,200 characters of your text, read by a voice built into your browser or device; pauses are only approximated</td><td>Catching typos and clumsy phrasing</td></tr>
<tr><th scope="row"><em>Generate Audio</em></th><td>Your text in the chosen neural voice, with speed, pitch and exact pauses</td><td>The real result to download</td></tr>
</tbody></table></div>

<h2 id="limitations">Limitations</h2>
<ul>
<li>5,000 characters per generation; longer writing is converted in parts with the same settings.</li>
<li>One voice per generation, so a conversation needs a separate generation for each speaker.</li>
<li>No custom or cloned voices and no emotion or speaking-style settings: speed, pitch and pauses are the only controls.</li>
<li>Your text is sent to Microsoft's online speech service to be voiced, so do not paste anything you may not share.</li>
<li>Results belong to the browser tab and are deleted about two hours after your last generation; download what you want to keep.</li>
</ul>

<h2 id="related">Related pages</h2>
<ul>
<li><a href="/guides/choose-voice.html">How to choose a text to speech voice and accent</a></li>
<li><a href="/ai-voice-generator.html">Free AI voice generator from text</a></li>
<li><a href="/voices.html">All voices and languages</a></li>
<li><a href="/text-to-speech-download.html">Text to speech download: MP3, WAV and subtitles</a></li>
</ul>
""", image="text-to-voice-speed-pitch.webp")

# ---------------------------------------------------------------- landing: AI voice generator
page("ai-voice-generator.html", "Free AI Voice Generator from Text | Text 2 Speech",
     "A free AI voice generator for text: 300+ Microsoft neural voices in 75 languages, MP3 or WAV with subtitles, no sign-up. What it can and cannot do, plainly.",
     [HOME, ("AI voice generator", SITE + "/ai-voice-generator.html")], """
<h1>Free AI voice generator from text</h1>
<p class="lead"><strong>Short answer:</strong> <a href="/">Text 2 Speech</a> is a free AI voice generator that turns typed or pasted text into speech with Microsoft's neural voices: 300+ voices in 75 languages, downloadable as MP3 or WAV with SRT and VTT subtitles, without an account. It reads your text in ready-made voices; it does not clone voices or act out emotions.</p>
""" + CTA + toc(("meaning", "What “AI voice” means here"), ("steps", "Generate an AI voice in four steps"),
                ("can-cannot", "What it can and cannot do"), ("uses", "Where an AI voice fits"),
                ("planner", "How much text for how many seconds"), ("rights", "Your text, your responsibility"),
                ("limitations", "Limitations"), ("related", "Related pages")) + """
<h2 id="meaning">What “AI voice” means here</h2>
<p>The voices are neural text-to-speech voices from Microsoft's online speech service. A neural voice comes from a model trained on recorded human speech: it predicts how a text should sound, including stress and intonation, and synthesizes the audio, rather than stitching together recorded snippets. That is why it sounds much closer to a person reading than older computer voices.</p>
<p>Text 2 Speech is the free web page around that service. It splits your text into pieces, sends them with the voice, speed and pitch you chose, joins the returned audio and your pauses into one file, and builds subtitles from the timing of each spoken word. Each step is described on the <a href="/how-it-works.html">how it works page</a>.</p>
""" + fig("ai-voice-generator-overview.webp", 1176, 921,
          "The Text 2 Speech generator: voice settings on the left with language, gender, voice search, speed, pitch and output format; the input text with pause markers on the right; and two finished results with players and download buttons",
          "The whole generator on one page: voice settings, the text box and the results with their downloads.") + """

<h2 id="steps">Generate an AI voice in four steps</h2>
<ol>
<li>Choose the language of your text in <em>Voice Language</em>, then click a voice; ▶ plays a sample of it.</li>
<li>Type, paste or import up to 5,000 characters.</li>
<li>Pick MP3 or WAV and, if you like, set speed, pitch and <code>[break:…]</code> pauses.</li>
<li>Press <em>Generate Audio</em>. A text of the full 5,000 characters was ready in about 12 seconds in a test. Download the audio and, for captions, the SRT or VTT file.</li>
</ol>

<h2 id="can-cannot">What it can and cannot do</h2>
<div class="tablewrap"><table>
<thead><tr><th scope="col">It can</th><th scope="col">It cannot</th></tr></thead>
<tbody>
<tr><td>Read text aloud with 322 voices across 75 languages and 142 regional accents</td><td>Copy, clone or imitate a particular person's voice, including your own</td></tr>
<tr><td>Change speed (−100% to +100%) and pitch (−100 to +100 Hz)</td><td>Set an emotion or a speaking style such as cheerful, whispering or angry</td></tr>
<tr><td>Insert exact pauses with <code>[break:…]</code> markers</td><td>Interpret SSML tags</td></tr>
<tr><td>Take up to 5,000 characters per generation</td><td>Take unlimited text in one go; longer texts are done in parts</td></tr>
<tr><td>Deliver MP3 or WAV plus SRT and VTT subtitles</td><td>Mix several voices in one file</td></tr>
<tr><td>Work in a modern browser with no account</td><td>Run offline, as an installed app, or through an API</td></tr>
<tr><td>Import <code>.txt</code>, <code>.md</code> and <code>.text</code> files</td><td>Open PDFs, Word files or web pages</td></tr>
</tbody></table></div>

<h2 id="uses">Where an AI voice fits</h2>
<ul>
<li><strong>Video voiceovers.</strong> Narration for explainers, tutorials, product demos and social clips, with captions from the same generation. The <a href="/guides/ai-voiceover.html">AI voiceover guide</a> walks through a measured three-scene example.</li>
<li><strong>E-learning and training.</strong> Lesson narration that is easy to update when the material changes: edit the sentence and generate again instead of booking a new recording.</li>
<li><strong>Accessibility.</strong> An audio version of an article, notice or handout for people who prefer listening, plus subtitle files for viewers who cannot hear the audio. It does not replace a screen reader, which reads whole interfaces as you move through them.</li>
<li><strong>Language practice.</strong> Hearing a sentence in the language and accent you are learning, slowed down if needed.</li>
<li><strong>Drafts and prototypes.</strong> Placeholder narration and phone-menu or announcement prompts, to test the wording before a final recording.</li>
</ul>
<p>To shape how the voice sounds (accent, speed, pitch and pauses), see <a href="/text-to-voice.html">text to voice</a>.</p>

<h2 id="planner">How much text for how many seconds</h2>
<p>In English tests at normal speed, the voice Aria (US) spoke about 15 to 16 characters per second, counting spaces and punctuation. That is enough to size a script before you write it:</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Target length</th><th scope="col">Characters of script</th><th scope="col">Roughly</th></tr></thead>
<tbody>
<tr><th scope="row">15 seconds</th><td>225–240</td><td>Two or three sentences</td></tr>
<tr><th scope="row">30 seconds</th><td>450–480</td><td>A short paragraph</td></tr>
<tr><th scope="row">1 minute</th><td>900–960</td><td>Two paragraphs</td></tr>
<tr><th scope="row">5 minutes</th><td>4,500–4,800</td><td>Almost a full generation</td></tr>
</tbody></table></div>
<p>Treat the table as a first estimate. Voices differ in pace by up to about a fifth, slower speeds stretch the audio, and pause markers add their own time, so generate the first scene and check its length in the results list before writing the rest.</p>

<h2 id="rights">Your text, your responsibility</h2>
<p>Everything you convert is sent to Microsoft's online speech service, and the generated files are deleted from the Text 2 Speech server about two hours after your last generation. You are responsible for having the right to use the text and for how you use the audio: the <a href="/terms.html">terms of service</a> apply, and Text 2 Speech gives no guarantee that a particular commercial use is allowed. Some platforms also ask creators to label synthetic or AI-generated voices, so check the rules of the place where you publish.</p>

<h2 id="limitations">Limitations</h2>
<ul>
<li>One generation is limited to 5,000 characters and 25 pause markers.</li>
<li>About 20 requests per minute are allowed from one IP address, and the ▶ voice samples count toward that.</li>
<li>Voices depend on the speech service: one that stops answering is hidden from the list until it works again.</li>
<li>Results belong to the browser tab and expire; there is no account, history or saved project.</li>
<li>An internet connection is required, because the audio is made by an online service.</li>
</ul>

<h2 id="related">Related pages</h2>
<ul>
<li><a href="/guides/ai-voiceover.html">How to make a free AI voiceover from text</a></li>
<li><a href="/text-to-voice.html">Text to voice: language, accent, speed, pitch and pauses</a></li>
<li><a href="/how-it-works.html">How Text 2 Speech works</a></li>
<li><a href="/voices.html">All voices and languages</a></li>
</ul>
""", image="ai-voice-generator-overview.webp")

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
        self.heads, self.ids, self.links, self.lds, self.paras, self.imgs = [], [], [], [], [], []
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
        if tag == "img":
            self.imgs.append(a)
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


def strings(x):  # every text in the home strings, whatever key it lives under
    if isinstance(x, str):
        yield re.sub(r"\s+", " ", x).strip()
    for v in (x.values() if isinstance(x, dict) else x if isinstance(x, list) else []):
        yield from strings(v)


for t in set(strings(home)):
    if len(t) >= 80:
        seen.setdefault(t, []).append("home (i18n-home/en.json)")
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
    for img in s.imgs:  # screenshots: present, small, sized, described, lazy
        f = pathlib.Path("web") / img.get("src", "").lstrip("/")
        if not f.is_file() or f.stat().st_size > 80_000:
            problems.append(f"{path}: image {img.get('src')} missing or over 80 KB")
        if not (img.get("width") and img.get("height") and len(img.get("alt", "")) > 20 and img.get("loading") == "lazy"):
            problems.append(f"{path}: image {img.get('src')} needs width, height, alt and loading=lazy")
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
