"""Deterministic API regression tests (no network): the speech provider is mocked.
Run: .venv/Scripts/python -m unittest tests/test_api.py -v   (needs ffmpeg + httpx)

Tests marked @expectedFailure pin a known, still-open defect (none at the moment).
When the defect is fixed the test reports "unexpected success": remove the marker."""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx  # noqa: E402
import server  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

LONG = "Microsoft Server Speech Text to Speech Voice ({}, {})"
VOICES = [
    {"ShortName": "en-US-AriaNeural", "Locale": "en-US", "Gender": "Female", "FriendlyName": "Aria",
     "Name": LONG.format("en-US", "AriaNeural")},
    {"ShortName": "en-US-AndrewNeural", "Locale": "en-US", "Gender": "Male", "FriendlyName": "Andrew",
     "Name": LONG.format("en-US", "AndrewNeural")},
    {"ShortName": "en-US-AndrewMultilingualNeural", "Locale": "en-US", "Gender": "Male", "FriendlyName": "Andrew ML",
     "Name": LONG.format("en-US", "AndrewMultilingualNeural")},
    # Locale with a script part: edge-tts can't expand this short id itself.
    {"ShortName": "iu-Cans-CA-TaqqiqNeural", "Locale": "iu-Cans-CA", "Gender": "Male", "FriendlyName": "Taqqiq",
     "Name": LONG.format("iu-Cans-CA", "TaqqiqNeural")},
]
H = {"X-Session-Id": "unittestsession"}
ORIGINAL_SYNTH = server.synth_segment  # captured before setUpClass mocks it


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tone = Path(cls.tmp.name) / "tone.mp3"
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=440:d=1:r=24000", "-ac", "1",
                        "-codec:a", "libmp3lame", "-b:a", "48k", str(tone)], check=True, capture_output=True)
        cls.tone = tone.read_bytes()
        server.DATA = Path(cls.tmp.name) / "data"
        server.DATA.mkdir()
        server._voices_cache.update(data=None, ts=0)
        cls.patches = [
            mock.patch.object(server.edge_tts, "list_voices", mock.AsyncMock(return_value=VOICES)),
            mock.patch.object(server, "synth_segment", mock.AsyncMock(return_value=(cls.tone, []))),
        ]
        for p in cls.patches:
            p.start()
        cls.c = TestClient(server.app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls):
        for p in cls.patches:
            p.stop()
        cls.tmp.cleanup()

    def setUp(self):
        server._dead_voices.clear()  # a test that kills a voice must not leak into the next

    def tts(self, **body):
        return self.c.post("/api/tts", json={"voice": "en-US-AriaNeural", **body}, headers=H)

    # ---------- current, correct behaviour ----------
    def test_validation(self):
        self.assertEqual(self.tts(text="").status_code, 400)
        self.assertEqual(self.tts(text="   ").status_code, 400)
        self.assertEqual(self.tts(text="hi", voice="xx-XX-Nope").status_code, 400)
        self.assertEqual(self.tts(text="hi", format="ogg").status_code, 422)
        self.assertEqual(self.c.post("/api/tts", json={"text": "hi", "voice": "en-US-AriaNeural"}).status_code, 400)

    def test_generate_download_isolate_delete(self):
        r = self.tts(text="Hello world.")
        self.assertEqual(r.status_code, 200, r.text)
        m = r.json()
        self.assertAlmostEqual(m["duration"], 1.0, delta=0.15)
        f = self.c.get(m["audio"], headers=H)
        self.assertEqual(f.status_code, 200)
        self.assertEqual(f.headers["content-type"], "audio/mpeg")
        self.assertGreater(len(f.content), 1000)
        self.assertEqual(self.c.get(m["audio"], headers={"X-Session-Id": "someoneelse"}).status_code, 404)
        self.assertEqual(self.c.get(m["srt"], headers=H).text.splitlines()[:2][1][:17], "00:00:00,000 --> ")
        self.assertTrue(self.c.get(m["vtt"], headers=H).text.startswith("WEBVTT"))
        self.assertEqual(self.c.delete(f"/api/items/{m['id']}", headers=H).status_code, 200)
        self.assertEqual(self.c.get(m["audio"], headers=H).status_code, 404)

    def test_wav(self):
        m = self.tts(text="Hi", format="wav").json()
        self.assertIn(self.c.get(m["audio"], headers=H).headers["content-type"], ("audio/x-wav", "audio/wav"))

    def test_break_marker_inserts_silence(self):
        m = self.tts(text="One. [break:2s] Two.").json()
        self.assertAlmostEqual(m["duration"], 4.0, delta=0.3)

    def test_page_routes_ignore_query_params(self):  # TTS-BUG-030: ?page= read any file
        for q in ("page=../server.py", "page=../../etc/passwd", "name=../server.py", "n=../server.py", "c=x"):
            r = self.c.get(f"/es/tutorial.html?{q}")
            self.assertEqual(r.status_code, 200, q)
            self.assertIn("text/html", r.headers["content-type"], q)
            self.assertNotIn("edge_tts", r.text, q)
            self.assertIn('<html lang="es"', r.text, q)

    def test_localized_pages_server_side(self):  # TTS-BUG-023
        r = self.c.get("/es/")
        self.assertIn('<html lang="es"', r.text)
        self.assertIn('<link rel="canonical" href="https://text-2-speech.com/es/">', r.text)
        self.assertEqual(r.text.count('rel="alternate" hreflang='), 26)  # 25 languages + x-default
        self.assertIn('hreflang="pt-BR" href="https://text-2-speech.com/pt/"', r.text)
        self.assertIn('<html lang="ar" dir="rtl"', self.c.get("/ar/").text)
        self.assertIn('<link rel="canonical" href="https://text-2-speech.com/">', self.c.get("/").text)
        self.assertIn('href="https://text-2-speech.com/zh-CN/tutorial.html"', self.c.get("/zh-CN/tutorial.html").text)
        self.assertNotIn("hreflang", self.c.get("/auth.html").text)  # noindex page

    def test_home_content_localized_server_side(self):  # TTS-BUG-023
        import re as _re
        for path, lang, first_q in (("/", "en", "Is Text 2 Speech free to use?"), ("/de/", "de", None), ("/ar/", "ar", None)):
            html = self.c.get(path).text
            self.assertNotIn("<!--home:", html, path)
            self.assertIn(f'id="homecontent" type="application/json" data-lang="{lang}"', html, path)
            data = json.loads(_re.search(r'id="homecontent"[^>]*>(.*?)</script>', html, _re.S).group(1))
            ld = json.loads(_re.search(r'application/ld\+json">(.*?)</script>', html, _re.S).group(1))
            faq = [n for n in ld["@graph"] if n["@type"] == "FAQPage"][0]
            self.assertEqual(faq["inLanguage"], lang, path)
            self.assertEqual(faq["mainEntity"][0]["name"], data["faq"][0]["q"], path)
            self.assertIn(server.html_lib.escape(data["faq"][0]["q"], quote=False), html, path)  # visible FAQ too
            if first_q:
                self.assertEqual(data["faq"][0]["q"], first_q)
            else:
                self.assertNotEqual(data["faq"][0]["q"], "Is Text 2 Speech free to use?", path)

    def test_sitemap_lists_every_language(self):  # TTS-BUG-023
        r = self.c.get("/sitemap.xml")
        self.assertEqual(r.headers["content-type"].split(";")[0], "application/xml")
        # 5 indexed pages x (root + 24 other languages) + 4 English-only pages
        self.assertEqual(r.text.count("<loc>"), 5 * 25 + 4)
        for absent in ("auth.html", "donate.html", "/en/"):
            self.assertNotIn(absent, r.text)
        for present in ("/voices.html", "/how-it-works.html", "/guides/subtitles.html", "/guides/mp3-vs-wav.html"):
            self.assertIn(present, r.text)

    # ---------- SEO: every indexable URL in every language ----------
    def _sitemap_pages(self):
        import re as _re
        return [u.replace("https://text-2-speech.com", "") for u in _re.findall(r"<loc>([^<]+)</loc>", self.c.get("/sitemap.xml").text)]

    def _head(self, html):
        import re as _re
        g = lambda p: (lambda m: m.group(1) if m else None)(_re.search(p, html, _re.S))
        return {"title": g(r"<title>(.*?)</title>"), "desc": g(r'<meta name="description" content="([^"]*)"'),
                "canon": g(r'<link rel="canonical" href="([^"]*)"'), "og_url": g(r'<meta property="og:url" content="([^"]*)"'),
                "robots": g(r'<meta name="robots" content="([^"]*)"'), "h1": len(_re.findall(r"<h1[\s>]", html)),
                "ld": [json.loads(x) for x in _re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, _re.S)]}

    def test_every_sitemap_url_is_unique_and_self_canonical(self):
        titles, descs = {}, {}
        for path in self._sitemap_pages():
            r = self.c.get(path)
            self.assertEqual(r.status_code, 200, path)
            h = self._head(r.text)
            self.assertEqual(h["canon"], "https://text-2-speech.com" + path, path)
            self.assertEqual(h["og_url"], h["canon"], path)
            self.assertEqual(h["h1"], 1, path)
            # display width: CJK characters count double, as in search result snippets
            self.assertTrue(h["title"] and 15 <= server._width(h["title"]) <= 90, (path, h["title"]))
            self.assertTrue(h["desc"] and 70 <= server._width(h["desc"]) <= 170, (path, h["desc"]))
            self.assertIn("index", h["robots"], path)
            self.assertNotIn("noindex", h["robots"], path)
            self.assertTrue(h["ld"], path)  # every page carries structured data
            titles.setdefault(h["title"], []).append(path)
            descs.setdefault(h["desc"], []).append(path)
        self.assertEqual({t: p for t, p in titles.items() if len(p) > 1}, {})
        self.assertEqual({d: p for d, p in descs.items() if len(p) > 1}, {})

    def test_language_pages_rendered_server_side(self):
        es = self.c.get("/es/").text
        self.assertIn("<title>Texto a voz gratuito en línea | Text 2 Speech</title>", es)
        self.assertIn('<meta property="og:locale" content="es_ES">', es)
        self.assertIn('<option value="es" selected>', es)  # language select filled server-side
        self.assertIn(server._HOME_UI["es"]["generate_audio"], es)  # UI strings, not only the FAQ
        tut = self.c.get("/es/tutorial.html").text
        sub = server._sub_strings("es")
        self.assertIn(f"<h1 data-i18n=\"tut_h1\">{sub['tut_h1']}</h1>", tut)
        self.assertIn('data-ui="es"', tut)
        self.assertNotIn("i18n-sub.js", tut)  # the 216 KB all-language bundle is gone
        self.assertIn('id="substrings"', tut)
        self.assertEqual(self._head(self.c.get("/en/").text)["canon"], "https://text-2-speech.com/")
        self.assertIn('<html lang="ar" dir="rtl" data-ui="ar"', self.c.get("/ar/privacy.html").text)

    def test_breadcrumbs_and_noindex(self):
        h = self._head(self.c.get("/fr/tutorial.html").text)
        crumbs = [x for x in h["ld"] if x.get("@type") == "BreadcrumbList"][0]["itemListElement"]
        self.assertEqual([c["item"] for c in crumbs], ["https://text-2-speech.com/fr/", "https://text-2-speech.com/fr/tutorial.html"])
        self.assertIn('class="crumbs"', self.c.get("/fr/tutorial.html").text)
        for path in ("/donate.html", "/de/donate.html", "/auth.html"):
            self.assertIn("noindex", self._head(self.c.get(path).text)["robots"], path)

    def test_structured_data(self):
        home = self._head(self.c.get("/").text)["ld"][0]["@graph"]
        types = {n["@type"]: n for n in home}
        self.assertEqual(set(types), {"Organization", "WebApplication", "WebSite", "FAQPage"})
        self.assertEqual(types["WebApplication"]["publisher"], {"@id": "https://text-2-speech.com/#org"})
        self.assertEqual(types["Organization"]["logo"]["url"], "https://text-2-speech.com/logo.png")
        self.assertNotIn("aggregateRating", json.dumps(home))  # no ratings we do not have
        for path in ("/guides/subtitles.html", "/guides/mp3-vs-wav.html", "/how-it-works.html"):
            art = [x for x in self._head(self.c.get(path).text)["ld"] if x["@type"] == "TechArticle"][0]
            for k in ("headline", "datePublished", "dateModified", "author", "publisher"):
                self.assertIn(k, art, (path, k))

    def test_crawl_basics_icons_and_caching(self):
        robots = self.c.get("/robots.txt").text
        self.assertIn("Disallow: /api/", robots)
        self.assertIn("Sitemap: https://text-2-speech.com/sitemap.xml", robots)
        for f in ("/favicon.svg", "/favicon-48.png", "/apple-touch-icon.png", "/logo.png"):
            r = self.c.get(f)
            self.assertEqual(r.status_code, 200, f)
            self.assertIn("max-age=604800", r.headers["cache-control"], f)
        import re as _re
        src = _re.search(r'src="(/subi18n\.js\?v=[^"]+)"', self.c.get("/tutorial.html").text).group(1)
        self.assertIn("immutable", self.c.get(src).headers["cache-control"])
        self.assertEqual(self.c.get("/tutorial.html").headers["cache-control"], "no-cache")

    def test_voices_page_lists_live_catalog(self):
        try:
            server._dead_voices.add("en-US-AndrewNeural")
            html = self.c.get("/voices.html").text
        finally:
            server._dead_voices.clear()
        self.assertIn("<strong>3 voices in 2 languages</strong>", html)
        self.assertIn("Taqqiq - Cans-CA", html)
        self.assertNotIn("Andrew - US,", html)  # hidden while unavailable
        self.assertNotIn("<!--voices:", html)

    def test_html_404_for_pages_json_for_api(self):  # TTS-BUG-026
        r = self.c.get("/nope.html")
        self.assertEqual(r.status_code, 404)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("Page not found", r.text)
        r = self.c.get("/api/nope")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json(), {"detail": "Not Found"})

    def test_voices_cacheable(self):  # TTS-BUG-027
        self.assertEqual(self.c.get("/api/voices").headers["cache-control"], "public, max-age=3600")

    def test_subtitles_keep_punctuation_and_cjk_spacing(self):  # TTS-BUG-005
        words = [(0.1, 0.5, "Hello"), (0.8, 1.0, "world"), (1.2, 1.5, "Bye")]
        with mock.patch.object(server, "synth_segment", mock.AsyncMock(return_value=(self.tone, words))):
            m = self.tts(text="Hello, world! Bye.").json()
        srt = self.c.get(m["srt"], headers=H).text
        self.assertIn("Hello, world!", srt)
        self.assertIn("Bye.", srt)
        self.assertIn("00:00:00,100 --> 00:00:01,000", srt)
        zh = server.align_words("早上好。今天很好！", [(0, 1, "早上"), (1, 2, "好"), (3, 4, "今天"), (4, 5, "很"), (5, 6, "好")])
        self.assertEqual([c.strip() for c in server.build_subtitles(zh, srt=False).split("\n\n")[1:3]],
                         ["00:00:00.000 --> 00:00:02.000\n早上好。", "00:00:03.000 --> 00:00:06.000\n今天很好！"])

    def test_expired_sessions_are_cleaned(self):  # TTS-BUG-019
        old, fresh = server.DATA / "oldsession", server.DATA / "freshsession"
        old.mkdir(); fresh.mkdir()
        t = time.time() - server.SESSION_TTL - 60
        os.utime(old, (t, t))
        server._cleanup_old_sessions()
        self.assertFalse(old.exists())
        self.assertTrue(fresh.exists())

    def test_support_inbox(self):  # TTS-BUG-016
        tmp = Path(self.tmp.name) / "support"
        good = {"email": "a@example.com", "topic": "bug", "message": "The preview button does nothing."}
        with mock.patch.object(server, "SUPPORT_DIR", tmp):
            self.assertEqual(self.c.post("/api/support", json=good).json(), {"ok": True})
            line = json.loads((tmp / "inbox.jsonl").read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual((line["email"], line["topic"], line["message"]), (good["email"], "bug", good["message"]))
            for bad in ({**good, "email": ""}, {**good, "email": "not-an-email"}, {**good, "message": "short"},
                        {**good, "message": "x" * 5001}, {**good, "topic": "spam"}):
                self.assertEqual(self.c.post("/api/support", json=bad).status_code, 422, bad)
            n = len((tmp / "inbox.jsonl").read_text(encoding="utf-8").splitlines())
            self.assertEqual(self.c.post("/api/support", json={**good, "website": "http://spam"}).status_code, 200)
            self.assertEqual(len((tmp / "inbox.jsonl").read_text(encoding="utf-8").splitlines()), n)  # bot: not stored
            with mock.patch.object(server, "SUPPORT_MAX_BYTES", 10):
                self.assertEqual(self.c.post("/api/support", json=good).status_code, 503)
        self.assertNotIn("support", [p.name for p in Path(server.BASE / "web").iterdir()])  # never served

    def test_path_traversal(self):
        self.assertEqual(self.c.get("/api/file/..%2f..%2fserver.py", headers=H).status_code, 404)

    def test_parse_segments_caps_single_break(self):
        self.assertEqual(server.parse_segments("[break:99s]"), [{"type": "silence", "ms": 30000}])

    # ---------- fixed defects (regression guards) ----------
    def test_text_length_limit(self):  # TTS-BUG-001
        n = server.MAX_CHARS
        self.assertEqual(self.tts(text="a" * n).status_code, 200)
        self.assertEqual(self.tts(text="😀" * n).status_code, 200)  # code points, like the UI counter
        r = self.tts(text="a" * (n + 1))
        self.assertEqual(r.status_code, 422)
        self.assertIn("text:", r.json()["detail"])  # one readable string for the UI toast

    def test_break_marker_limits(self):  # TTS-BUG-002
        self.assertEqual(self.tts(text="[break:30s]" * 2 + " hi").status_code, 200)  # exactly 60 s
        self.assertEqual(self.tts(text="[break:30s]" * 2 + "[break:1ms] hi").status_code, 400)
        self.assertEqual(self.tts(text="a [break:1ms] " * 26).status_code, 400)  # 51 segments

    def test_break_only_text_is_rejected(self):  # TTS-BUG-009
        self.assertEqual(self.tts(text="[break:1s][break:2s]").status_code, 400)

    def test_prosody_out_of_range_is_422(self):  # TTS-BUG-014 / BUG-018 server side
        self.assertEqual(self.tts(text="hi", speed=1000).status_code, 422)
        self.assertEqual(self.tts(text="hi", pitch=-101).status_code, 422)
        self.assertEqual(self.tts(text="hi", speed=-100, pitch=100).status_code, 200)

    def test_cross_site_text_plain_post_rejected(self):  # TTS-BUG-020
        r = self.c.post("/api/tts", content=b'{"text":"hi","voice":"en-US-AriaNeural"}',
                        headers={**H, "Content-Type": "text/plain"})
        self.assertEqual(r.status_code, 422)

    def test_security_headers_and_no_docs(self):  # TTS-BUG-020
        h = self.c.get("/api/health").headers
        for k in ("strict-transport-security", "content-security-policy", "x-content-type-options",
                  "x-frame-options", "referrer-policy"):
            self.assertIn(k, h)
        for p in ("/docs", "/redoc", "/openapi.json"):
            self.assertEqual(self.c.get(p).status_code, 404, p)

    def test_provider_error_detail_not_leaked(self):  # TTS-BUG-020
        with mock.patch.object(server, "synth_segment", mock.AsyncMock(side_effect=RuntimeError("secret-internal"))):
            with self.assertLogs("voxly", "ERROR"):
                r = self.tts(text="hi")
        self.assertEqual(r.status_code, 502)
        self.assertNotIn("secret-internal", r.text)

    def test_language_mismatch_is_actionable_422(self):  # TTS-BUG-007 (server side)
        async def only_english(text, *a):  # a live voice that can't read Devanagari
            if text != "Hello.":
                raise server.edge_tts.exceptions.NoAudioReceived("No audio was received.")
            return self.tone, []
        with mock.patch.object(server, "synth_segment", side_effect=only_english):
            r = self.tts(text="सुप्रभात")
        self.assertEqual(r.status_code, 422)
        self.assertIn("Voice Language", r.json()["detail"])
        self.assertNotIn("en-US-AriaNeural", server._dead_voices)

    # ---------- voices the service lists but won't speak (user report, 2026-10-29) ----------
    def test_engine_gets_full_voice_name(self):
        synth = mock.AsyncMock(return_value=(self.tone, []))
        with mock.patch.object(server, "synth_segment", synth):
            self.assertEqual(self.tts(text="ᐅᓪᓛᒃᑯᑦ", voice="iu-Cans-CA-TaqqiqNeural").status_code, 200)
        self.assertEqual(synth.call_args.args[1], LONG.format("iu-Cans-CA", "TaqqiqNeural"))

    def test_sweep_hides_dead_voices_only(self):
        flaky = {"n": 0}

        async def synth(text, engine, *a):
            if "AndrewNeural" in engine:  # dead: never answers
                raise server.edge_tts.exceptions.NoAudioReceived("No audio was received.")
            if "AriaNeural" in engine:    # flaky: fails a few times, then answers
                flaky["n"] += 1
                if flaky["n"] <= server.SWEEP_ATTEMPTS - 1:
                    raise server.edge_tts.exceptions.NoAudioReceived("No audio was received.")
            if "Taqqiq" in engine:
                raise ConnectionError("network blip")  # not evidence the voice is dead
            return self.tone, []
        try:
            with mock.patch.object(server, "synth_segment", side_effect=synth), \
                 mock.patch.object(server, "PROBE_SPACING", 0):
                server.asyncio.run(server.sweep_dead_voices())
            self.assertEqual(server._dead_voices, {"en-US-AndrewNeural"})
            ids = [v["id"] for v in self.c.get("/api/voices").json()["voices"]]
            self.assertNotIn("en-US-AndrewNeural", ids)
            self.assertIn("iu-Cans-CA-TaqqiqNeural", ids)
            r = self.tts(text="hi", voice="en-US-AndrewNeural")  # a stale page still offering it
            self.assertEqual(r.status_code, 422)
            self.assertIn("currently unavailable", r.json()["detail"])
        finally:
            server._dead_voices.clear()

    def test_failing_voice_is_reported_but_not_hidden(self):
        err = server.edge_tts.exceptions.NoAudioReceived("No audio was received.")
        synth = mock.AsyncMock(side_effect=err)
        with mock.patch.object(server, "synth_segment", synth):
            r = self.tts(text="Hello there.", voice="en-US-AndrewNeural")
        self.assertEqual(r.status_code, 422)
        self.assertIn("currently unavailable", r.json()["detail"])
        # request, its retry, then one probe; hiding is left to the sweep (flaky voices)
        self.assertEqual([c.args[0] for c in synth.call_args_list], ["Hello there.", "Hello there.", "Hello."])
        self.assertNotIn("en-US-AndrewNeural", server._dead_voices)

    def test_split_text(self):  # TTS-BUG-003
        text = "".join(f"Sentence {i} is here, with a clause! " if i % 3 else f"Line {i}\n"
                       for i in range(400)) + "x" * 40
        for limit in (50, 300, 1500):
            chunks = server.split_text(text, limit)
            self.assertTrue(all(0 < len(c) <= limit for c in chunks))
            self.assertEqual("".join(chunks).replace(" ", "").replace("\n", ""),
                             text.replace(" ", "").replace("\n", ""))  # nothing lost or reordered
        self.assertEqual(server.split_text("Short. Text!\nKept as is.", 1500), ["Short. Text!\nKept as is."])
        self.assertEqual(server.split_text("a" * 25, 10), ["a" * 10, "a" * 10, "a" * 5])

    def test_long_text_is_chunked_in_order(self):  # TTS-BUG-003
        text = " ".join(f"This is sentence number {i}." for i in range(170))  # ~4,800 chars
        synth = mock.AsyncMock(return_value=(self.tone, []))
        with mock.patch.object(server, "synth_segment", synth):
            r = self.tts(text=text)
        self.assertEqual(r.status_code, 200, r.text)
        sent = [c.args[0] for c in synth.call_args_list]
        self.assertGreater(len(sent), 1)
        self.assertTrue(all(len(s) <= server.CHUNK_CHARS for s in sent))
        self.assertEqual(" ".join(sent), text)
        self.assertAlmostEqual(r.json()["duration"], len(sent), delta=0.3)  # 1 s tone per chunk

    def test_provider_call_retried_once(self):  # TTS-BUG-003
        synth = mock.AsyncMock(side_effect=[RuntimeError("blip"), (self.tone, [])])
        with mock.patch.object(server, "synth_segment", synth), self.assertLogs("voxly", "WARNING"):
            self.assertEqual(self.tts(text="hi").status_code, 200)
        self.assertEqual(synth.call_count, 2)
        synth = mock.AsyncMock(side_effect=RuntimeError("down"))
        with mock.patch.object(server, "synth_segment", synth), self.assertLogs("voxly", "WARNING"):
            self.assertEqual(self.tts(text="hi").status_code, 502)
        self.assertEqual(synth.call_count, 2)
        err = server.edge_tts.exceptions.NoAudioReceived("no audio")
        synth = mock.AsyncMock(side_effect=err)
        with mock.patch.object(server, "synth_segment", synth):
            self.assertEqual(self.tts(text="hi").status_code, 422)
        # no audio: one retry (flaky voices), then one probe to pick the message
        self.assertEqual([c.args[0] for c in synth.call_args_list], ["hi", "hi", "Hello."])

    def test_ffmpeg_does_not_block_event_loop(self):  # TTS-BUG-004
        real_run = subprocess.run

        def slow_run(*a, **k):
            time.sleep(1.0)
            return real_run(*a, **k)

        async def scenario():
            transport = httpx.ASGITransport(app=server.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
                with mock.patch.object(server.subprocess, "run", slow_run):
                    # Timer starts before the job: a blocking job holds the loop
                    # for its whole duration (~4 s of ffmpeg), so the health
                    # check can't even be sent until the job is done.
                    t = time.perf_counter()
                    job = asyncio.create_task(c.post("/api/tts", headers=H, json={
                        "text": "a [break:100ms] b", "voice": "en-US-AriaNeural"}))
                    await asyncio.sleep(0.3)
                    await c.get("/api/health")
                    waited = time.perf_counter() - t
                    self.assertEqual((await job).status_code, 200)
            return waited

        self.assertLess(asyncio.run(scenario()), 0.8)

    # ---------- known open defects ----------

    # TTS-BUG-005 (fixed): engine word timings requested
    def test_requests_word_boundaries(self):
        async def no_chunks():
            return
            yield
        with mock.patch.object(server.edge_tts, "Communicate") as comm:
            comm.return_value.stream = no_chunks
            server.asyncio.run(ORIGINAL_SYNTH("hi", "en-US-AriaNeural", "+0%", "+0Hz"))
        self.assertEqual(comm.call_args.kwargs.get("boundary"), "WordBoundary")

    def test_malformed_json_is_4xx(self):  # TTS-BUG-014 (fixed)
        r = self.c.post("/api/tts", content=b"{not json", headers={**H, "Content-Type": "application/json"})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(self.c.post("/api/tts", json=[1, 2, 3], headers=H).status_code, 422)

    def test_non_numeric_speed_is_4xx(self):  # TTS-BUG-014 (fixed)
        self.assertEqual(self.tts(text="hi", speed="fast").status_code, 422)

    # TTS-BUG-019 (fixed): reads never create session directories
    def test_file_get_does_not_create_session_dir(self):
        self.c.get("/api/file/x.mp3?s=brandnewsession42")
        self.assertFalse((server.DATA / "brandnewsession42").exists())

    # TTS-BUG-012 (fixed): Multilingual voices keep their tag
    def test_voice_display_names_unique(self):
        names = [v["name"] for v in self.c.get("/api/voices").json()["voices"]]
        self.assertEqual(len(names), len(set(names)), names)


if __name__ == "__main__":
    unittest.main()
