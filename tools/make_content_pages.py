"""Build the English content pages from the sub-page template (run from the repo root).
Facts come from the code and from measured runs (2026-10-29); keep them in sync."""
import html, json, pathlib, re

SITE = "https://text-2-speech.com"
UPDATED = "2026-10-29"
tpl = pathlib.Path("web/terms.html").read_text(encoding="utf-8")
style = re.search(r"<style>.*?</style>", tpl, re.S).group(0).replace(
    "</style>",
    "main h2{font-size:22px;margin:30px 0 8px}main h3{font-size:17px;margin:20px 0 6px}"
    ".lead{font-size:17px}.updated{color:var(--muted);font-size:13px}"
    "table{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px}th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}"
    "thead th{background:var(--panel2)}pre{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:12px;overflow:auto;font-size:13px;line-height:1.5}"
    "code{background:var(--panel2);border-radius:5px;padding:1px 5px}.tablewrap{overflow-x:auto}"
    "</style>")
boot = re.search(r"<script>if\(localStorage.*?</script>", tpl).group(0)
icons = re.search(r'<link rel="icon" href="/favicon.svg".*?<link rel="apple-touch-icon"[^>]*>', tpl).group(0)
header = re.search(r"<header>.*?</header>", tpl, re.S).group(0)
footer = re.search(r"<footer>.*?</footer>", tpl, re.S).group(0)
A = lambda t: html.escape(t, quote=True)


def page(path, title, desc, crumbs, body, article=True):
    url = f"{SITE}/{path}"
    ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(crumbs, 1)]}]
    if article:
        ld.append({"@context": "https://schema.org", "@type": "TechArticle", "headline": title.split(" | ")[0],
                   "description": desc, "url": url, "inLanguage": "en", "datePublished": UPDATED, "dateModified": UPDATED,
                   "author": {"@type": "Organization", "name": "Text 2 Speech", "url": SITE + "/"},
                   "publisher": {"@type": "Organization", "name": "Text 2 Speech", "url": SITE + "/",
                                 "logo": {"@type": "ImageObject", "url": SITE + "/logo.png"}},
                   "image": SITE + "/og-image.png", "mainEntityOfPage": url})
    lds = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    nav = ' <span aria-hidden="true">›</span> '.join(f'<a href="{u.replace(SITE, "") or "/"}">{html.escape(n)}</a>' for n, u in crumbs[:-1])
    nav += f' <span aria-hidden="true">›</span> <span aria-current="page">{html.escape(crumbs[-1][0])}</span>'
    out = ('<!DOCTYPE html><html lang="en" data-en-only><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f"<title>{html.escape(title)}</title>{boot}"
           f'<meta name="description" content="{A(desc)}"><link rel="canonical" href="{url}"><meta name="robots" content="index, follow">'
           f'<meta property="og:type" content="{"article" if article else "website"}"><meta property="og:site_name" content="Text 2 Speech"><meta property="og:locale" content="en_US">'
           f'<meta property="og:title" content="{A(title)}"><meta property="og:description" content="{A(desc)}"><meta property="og:url" content="{url}">'
           f'<meta property="og:image" content="{SITE}/og-image.png"><meta name="twitter:card" content="summary_large_image">'
           f"{icons}{style}{lds}</head><body>{header}<main>"
           f'<nav class="crumbs" aria-label="Breadcrumb">{nav}</nav>{body}'
           f'<p class="updated">Last updated: <time datetime="{UPDATED}">29 October 2026</time></p></main>'
           f'{footer}<script src="/subi18n.js"></script></body></html>\n')
    # wide tables and code blocks scroll sideways on phones: keyboard-focusable, labelled regions
    out = out.replace('<div class="tablewrap">', '<div class="tablewrap" tabindex="0" role="region" aria-label="Table (scrolls sideways)">')
    out = out.replace("<pre>", '<pre tabindex="0" role="region" aria-label="Example file">')
    f = pathlib.Path("web") / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(out, encoding="utf-8")
    print("wrote", f, len(out), "bytes")


HOME = ("Home", SITE + "/")

page("how-it-works.html", "How Text 2 Speech Works — Voices, Limits, Privacy | Text 2 Speech",
     "How the free Text 2 Speech converter turns text into audio: Microsoft neural voices, 5,000-character limit, MP3/WAV output, word-timed subtitles and data retention.",
     [HOME, ("How it works", SITE + "/how-it-works.html")], """
<h1>How Text 2 Speech works</h1>
<p class="lead">Text 2 Speech (text-2-speech.com) is a free online text-to-speech tool. You paste or type text, pick one of 300+ neural voices in 75 languages, and download the result as an MP3 or WAV file together with SRT and VTT subtitles. No account is needed.</p>

<h2>Is Text 2 Speech free? Do I need an account?</h2>
<p>Yes, it is free, and no. Generating, listening and downloading need no sign-up and no payment details. There is no paid tier.</p>

<h2>Which voices does it use?</h2>
<p>The voices are Microsoft's online neural text-to-speech voices. The live list currently has 300+ voices across 75 languages and regional variants, female and male, plus a few <em>multilingual</em> voices that handle mixed-language text. The <a href="/voices.html">voices and languages page</a> lists them all. The service checks every voice every six hours and temporarily hides any voice that stops producing audio, so the list only shows voices that work.</p>

<h2>What happens when I press Generate Audio?</h2>
<ol>
<li>Your text is split at any <code>[break:…]</code> pause markers, and long passages are split at sentence ends into chunks of at most 1,500 characters.</li>
<li>Each chunk is sent to the speech service with the voice, speed and pitch you chose; up to four chunks are synthesized at the same time, and a chunk that fails is retried once.</li>
<li>The audio pieces and any pauses are joined in order into one MP3 file (48 kbps, 24 kHz, mono). If you chose WAV, that file is converted to 16-bit PCM WAV (24 kHz, mono).</li>
<li>The speech engine reports when each word starts and ends. Those timings become the SRT and VTT subtitle files, with your original punctuation kept.</li>
</ol>

<h2>Limits</h2>
<div class="tablewrap"><table>
<thead><tr><th scope="col">What</th><th scope="col">Limit</th></tr></thead>
<tbody>
<tr><th scope="row">Text per generation</th><td>5,000 characters (an emoji counts as one character)</td></tr>
<tr><th scope="row">Pause markers</th><td>Up to 25 per generation, at most 30 seconds each and 60 seconds in total</td></tr>
<tr><th scope="row">Speed</th><td>−100% to +100%</td></tr>
<tr><th scope="row">Pitch</th><td>−100 Hz to +100 Hz</td></tr>
<tr><th scope="row">Requests</th><td>About 20 generations per minute from one IP address; voice previews count too</td></tr>
<tr><th scope="row">Formats</th><td>MP3 or WAV audio; SRT and VTT subtitles with every generation</td></tr>
</tbody></table></div>
<p>For longer material, such as book chapters, generate it in parts and join the files in an audio editor.</p>

<h2>What happens to my text and audio?</h2>
<p>Your text is sent to Microsoft's online speech service to be turned into audio. The finished audio and subtitle files are stored on our server under a random session identifier and are deleted automatically about two hours after your last generation. The site sets no cookies and runs no analytics or advertising trackers. Details are in the <a href="/privacy.html">privacy policy</a>.</p>

<h2>What Text 2 Speech does not do</h2>
<ul>
<li>No voice cloning or custom voices: only the listed neural voices are available.</li>
<li>No accounts, saved history or favourites yet. Results stay in your browser tab for the current session.</li>
<li>No guarantee on commercial use: check the <a href="/terms.html">terms</a> and the rights in your source text.</li>
</ul>

<h2>More guides</h2>
<ul>
<li><a href="/tutorial.html">Tutorial: your first voiceover, pauses and the voice collection</a></li>
<li><a href="/guides/subtitles.html">How to create SRT and VTT subtitles from text</a></li>
<li><a href="/guides/mp3-vs-wav.html">MP3 vs WAV for text to speech</a></li>
</ul>
<p>Questions or a problem? Use the <a href="/support.html">support form</a>.</p>
""")

page("guides/subtitles.html", "Create SRT and VTT Subtitles from Text (Free) | Text 2 Speech",
     "Turn text into speech and get matching SRT and VTT subtitle files with word-level timing. Step-by-step guide with real example files and SRT vs VTT differences.",
     [HOME, ("How it works", SITE + "/how-it-works.html"), ("Subtitles guide", SITE + "/guides/subtitles.html")], """
<h1>How to create SRT and VTT subtitles from text</h1>
<p class="lead"><strong>Short answer:</strong> paste your script into <a href="/">Text 2 Speech</a>, pick a voice and press <em>Generate Audio</em>. Every generation comes with two subtitle files, SRT and VTT, timed to the generated speech word by word. Download them next to the audio.</p>

<h2>Step by step</h2>
<ol>
<li>Choose the <em>Voice Language</em> that matches your script, then a voice.</li>
<li>Paste or import your text (up to 5,000 characters). End sentences with punctuation: each sentence becomes its own caption.</li>
<li>Optionally add pauses with <code>[break:500ms]</code> or <code>[break:2s]</code>. Pauses show up as gaps between captions.</li>
<li>Press <em>Generate Audio</em>.</li>
<li>In the result, download the audio and the <strong>⬇ SRT</strong> or <strong>⬇ VTT</strong> file.</li>
</ol>

<h2>What the files look like</h2>
<p>This is the real output for the script <q>Welcome to the course. In this lesson, you will learn how subtitles are timed. Each cue follows the speech, word by word.</q> with the voice Aria (US):</p>
<h3>SRT</h3>
<pre>1
00:00:00,100 --&gt; 00:00:01,300
Welcome to the course.

2
00:00:02,162 --&gt; 00:00:05,125
In this lesson, you will learn how subtitles are timed.

3
00:00:05,988 --&gt; 00:00:08,662
Each cue follows the speech, word by word.</pre>
<h3>VTT</h3>
<pre>WEBVTT

00:00:00.100 --&gt; 00:00:01.300
Welcome to the course.

00:00:02.162 --&gt; 00:00:05.125
In this lesson, you will learn how subtitles are timed.

00:00:05.988 --&gt; 00:00:08.662
Each cue follows the speech, word by word.</pre>

<h2>How the captions are built</h2>
<ul>
<li><strong>Timing:</strong> the speech engine reports when every word starts and ends; captions start at their first word and end at their last.</li>
<li><strong>Splitting:</strong> a new caption starts after a sentence ends (<code>.</code> <code>!</code> <code>?</code> and their CJK forms) or after ten words, whichever comes first. Common abbreviations such as "Dr." do not end a caption.</li>
<li><strong>Text:</strong> captions keep your original punctuation, and Chinese or Japanese text is joined without extra spaces.</li>
</ul>

<h2>SRT or VTT?</h2>
<div class="tablewrap"><table>
<thead><tr><th scope="col"></th><th scope="col">SRT (.srt)</th><th scope="col">VTT (.vtt)</th></tr></thead>
<tbody>
<tr><th scope="row">First line</th><td>Caption number</td><td><code>WEBVTT</code> header</td></tr>
<tr><th scope="row">Time format</th><td><code>00:00:01,300</code> (comma)</td><td><code>00:00:01.300</code> (full stop)</td></tr>
<tr><th scope="row">Typical use</th><td>Video editors, media players, video platforms</td><td>HTML5 video on web pages (<code>&lt;track&gt;</code>)</td></tr>
</tbody></table></div>

<h2>Using the files</h2>
<ul>
<li><strong>Web page:</strong> <code>&lt;video src="voiceover.mp4" controls&gt;&lt;track kind="captions" src="subtitles.vtt" srclang="en" label="English" default&gt;&lt;/video&gt;</code></li>
<li><strong>Video platforms and editors:</strong> most accept an SRT upload as a caption track; use the file from the same generation as the audio you place on the timeline.</li>
<li><strong>Media players:</strong> load the SRT next to the video file; many players pick it up automatically when it has the same file name.</li>
</ul>

<h2>Troubleshooting</h2>
<ul>
<li><strong>Captions drift:</strong> use the subtitle file from the same generation as the audio. A new generation, even of the same text, can be timed slightly differently.</li>
<li><strong>A caption is too long:</strong> add sentence punctuation; captions break at sentence ends and after ten words.</li>
<li><strong>Nothing was generated:</strong> check that the Voice Language matches the language of your text.</li>
</ul>
""")

page("guides/mp3-vs-wav.html", "MP3 vs WAV for Text to Speech: Size and When to Use | Text 2 Speech",
     "MP3 or WAV for a voiceover? Measured file sizes from Text 2 Speech (a 9.5-second clip: 56 KB MP3 vs 447 KB WAV) and when each format is the better choice.",
     [HOME, ("How it works", SITE + "/how-it-works.html"), ("MP3 vs WAV", SITE + "/guides/mp3-vs-wav.html")], """
<h1>MP3 vs WAV for text to speech</h1>
<p class="lead"><strong>Short answer:</strong> choose <strong>MP3</strong> for almost everything: sharing, web pages, e-learning and podcast drafts. It is about eight times smaller and sounds the same for speech. Choose <strong>WAV</strong> when an editing tool or workflow requires uncompressed audio.</p>

<h2>Measured on Text 2 Speech</h2>
<p>The same 9.53-second clip (voice Aria, US), generated on 29 October 2026:</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col"></th><th scope="col">MP3</th><th scope="col">WAV</th></tr></thead>
<tbody>
<tr><th scope="row">File size (9.53 s)</th><td>57,693 bytes (≈ 56 KB)</td><td>457,422 bytes (≈ 447 KB)</td></tr>
<tr><th scope="row">Approx. per minute of speech</th><td>≈ 0.36 MB</td><td>≈ 2.9 MB</td></tr>
<tr><th scope="row">Encoding</th><td>MP3, 48 kbps, 24 kHz, mono</td><td>16-bit PCM, 24 kHz, mono (384 kbps)</td></tr>
<tr><th scope="row">Plays in</th><td>Practically every browser, phone and player</td><td>Practically every browser, editor and player</td></tr>
</tbody></table></div>

<h2>Does WAV sound better?</h2>
<p>Not here. Text 2 Speech creates the WAV by decoding the generated MP3, so the WAV contains exactly the same sound in an uncompressed container. It does not add detail. Pick WAV for compatibility, for example tools that only import WAV, or to avoid re-compressing an MP3 when you edit and export again. Do not pick it for quality.</p>

<h2>When to use which</h2>
<ul>
<li><strong>MP3:</strong> sharing a voiceover, embedding audio in a web page, uploading to e-learning or podcast platforms, sending by message or email.</li>
<li><strong>WAV:</strong> importing into a video or audio editor that you will export from again, or any pipeline that requires PCM audio.</li>
</ul>
<p>Both formats come with the same SRT and VTT subtitle files. See the <a href="/guides/subtitles.html">subtitles guide</a>.</p>

<h2>Why 24 kHz?</h2>
<p>A 24 kHz sample rate captures frequencies up to 12 kHz, which covers the range that matters for speech intelligibility. It is the format the speech service delivers, so higher rates would only make files bigger.</p>
""")

page("voices.html", "Text to Speech Voices and Languages (300+ Voices) | Text 2 Speech",
     "Every voice available in Text 2 Speech, grouped by language: 300+ neural voices in 75 languages and regional variants, with female and male voices for each.",
     [HOME, ("Voices & languages", SITE + "/voices.html")], """
<h1>Text to speech voices and languages</h1>
<p class="lead"><!--voices:summary--> Choose the language of your text in <a href="/">the converter</a>, then try two or three voices: voices in the same language can sound very different.</p>
<p>The list comes straight from the speech service and is refreshed daily. Voices that stop producing audio are hidden until they work again. <em>Multilingual</em> voices can read mixed-language text.</p>
<div class="tablewrap"><table>
<thead><tr><th scope="col">Language</th><th scope="col">Locales</th><th scope="col">Voices</th><th scope="col">Voice names</th></tr></thead>
<tbody><!--voices:rows--></tbody></table></div>
<p>Not sure which to pick? The <a href="/tutorial.html">tutorial</a> explains how to compare voices, and <a href="/how-it-works.html">how it works</a> covers limits and formats.</p>
""", article=False)
