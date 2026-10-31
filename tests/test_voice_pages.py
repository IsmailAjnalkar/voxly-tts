"""Per-language voice pages (/voices/<slug>.html, voice_pages.py). No network: the voice
catalog is mocked as in tests/test_api.py.
Run: .venv/Scripts/python -m pytest -q tests/test_voice_pages.py"""
import collections
import html
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server  # noqa: E402
import voice_pages  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

_STATE = Path(tempfile.mkdtemp())  # page-view counts of the test run stay out of the real ones
server.STATS_DB, server.ADMIN_FILE = _STATE / "views.sqlite3", _STATE / "admin.json"


def V(short, gender, region):
    locale = re.match(r"[a-z]+-(?:[A-Za-z]+-)?[A-Z]{2}(?:-[a-z]+)?", short).group(0)
    lang = {"hi": "Hindi", "es": "Spanish", "fr": "French", "en": "English"}[short[:2]]
    return {"ShortName": short, "Locale": locale, "Gender": gender,
            "FriendlyName": f"Microsoft {short.split('-')[-1][:-6]} Online (Natural) - {lang} ({region})",
            "Name": f"Microsoft Server Speech Text to Speech Voice ({locale}, {short.split('-')[-1]})"}


VOICES = [V("hi-IN-MadhurNeural", "Male", "India"), V("hi-IN-SwaraNeural", "Female", "India"),
          V("es-ES-AlvaroNeural", "Male", "Spain"), V("es-MX-DaliaNeural", "Female", "Mexico"),
          V("fr-FR-VivienneMultilingualNeural", "Female", "France"), V("fr-CA-AntoineNeural", "Male", "Canada"),
          V("en-US-AriaNeural", "Female", "United States"), V("en-GB-RyanNeural", "Male", "United Kingdom")]


def main_of(page):
    return re.search(r"<main[^>]*>(.*?)</main>", page, re.S).group(1)


class VoicePages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not any(getattr(r, "path", "") == "/voices/hindi.html" for r in server.app.routes):
            raise unittest.SkipTest("voice_pages is not wired into server.py yet")
        server._voices_cache.update(data=None, ts=0)
        cls.patch = mock.patch.object(server.edge_tts, "list_voices", mock.AsyncMock(return_value=VOICES))
        cls.patch.start()
        cls.c = TestClient(server.app, raise_server_exceptions=False)
        cls.pages = {p: cls.c.get("/" + p) for p in voice_pages.PATHS}

    @classmethod
    def tearDownClass(cls):
        cls.patch.stop()
        server._voices_cache.update(data=None, ts=0)

    def test_pages_render_with_unique_meta(self):
        titles, descs = set(), set()
        for lang, path in zip(voice_pages.LANGS, voice_pages.PATHS):
            r = self.pages[path]
            self.assertEqual(r.status_code, 200, path)
            self.assertIn("text/html", r.headers["content-type"])
            t = r.text
            self.assertEqual(t.count("<h1"), 1, path)
            self.assertIn(f'<link rel="canonical" href="{server.SITE}/{path}">', t)
            self.assertIn(f'<meta property="og:url" content="{server.SITE}/{path}">', t)
            title = html.unescape(re.search(r"<title>(.*?)</title>", t).group(1))
            desc = re.search(r'<meta name="description" content="([^"]*)"', t).group(1)
            self.assertLessEqual(server._width(title), 70, title)
            self.assertTrue(120 <= len(desc) <= 160, (path, len(desc)))
            titles.add(title)
            descs.add(desc)
            self.assertIn(f'href="/?vl={lang.get("vl", lang["code"])}"', t)
            self.assertNotIn("<!--voices:", t)
        self.assertEqual(len(titles), len(voice_pages.LANGS))
        self.assertEqual(len(descs), len(voice_pages.LANGS))

    def test_structured_data(self):
        for path in voice_pages.PATHS:
            lds = [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                                                      self.pages[path].text, re.S)]
            types = [d["@type"] for d in lds]
            self.assertEqual(types, ["BreadcrumbList", "CollectionPage"], path)
            crumbs = lds[0]["itemListElement"]
            self.assertEqual([c["position"] for c in crumbs], [1, 2, 3])
            self.assertEqual(crumbs[-1]["item"], f"{server.SITE}/{path}")
            self.assertEqual(lds[1]["url"], f"{server.SITE}/{path}")
            self.assertNotIn("aggregateRating", self.pages[path].text)

    def test_table_matches_catalog(self):
        rows = lambda p: re.findall(r'<tr><th scope="row">([^<]*)</th><td>([^<]*)</td><td>([^<]*)</td>'
                                    r"<td>([^<]*)</td><td>([^<]*)</td></tr>", self.pages[p].text)
        self.assertEqual(rows("voices/hindi.html"), [("Madhur - IN", "India", "hi-IN", "Male", "No"),
                                                     ("Swara - IN", "India", "hi-IN", "Female", "No")])
        self.assertEqual(rows("voices/spanish.html"), [("Alvaro - ES", "Spain", "es-ES", "Male", "No"),
                                                       ("Dalia - MX", "Mexico", "es-MX", "Female", "No")])
        self.assertIn(("Vivienne (Multilingual) - FR", "France", "fr-FR", "Female", "Yes"), rows("voices/french.html"))
        self.assertIn("Text 2 Speech has 2 Hindi voices right now, for Hindi as spoken in India: "
                      "Madhur - IN (male) and Swara - IN (female).", self.pages["voices/hindi.html"].text)
        self.assertIn("<li><strong>Mexico</strong> (es-MX): 1 voice, 1 female and 0 male</li>",
                      self.pages["voices/spanish.html"].text)
        jp = self.pages["voices/japanese.html"].text  # no Japanese voice in the mocked catalog
        self.assertEqual(rows("voices/japanese.html"), [])
        self.assertIn("could not be loaded just now", jp)

    def test_dead_voices_excluded(self):
        try:
            server._dead_voices.add("hi-IN-MadhurNeural")
            t = self.c.get("/voices/hindi.html").text
        finally:
            server._dead_voices.clear()
        self.assertNotIn("Madhur", t)
        self.assertIn("Text 2 Speech has 1 Hindi voice right now", t)

    def test_links_resolve(self):
        cache = {}
        for path in voice_pages.PATHS:
            for href in set(re.findall(r'href="(/[^"]*)"', self.pages[path].text)):
                target, _, frag = href.partition("#")
                target = target.split("?")[0] or "/"
                if target not in cache:
                    cache[target] = self.c.get(target)
                self.assertEqual(cache[target].status_code, 200, (path, href))
                if frag:
                    self.assertIn(f'id="{frag}"', cache[target].text, (path, href))

    def test_linked_from_voices_page_and_sitemap(self):
        v = self.c.get("/voices.html").text
        sm = self.c.get("/sitemap.xml").text
        for path in voice_pages.PATHS:
            self.assertIn(f'href="/{path}"', v)
            self.assertIn(f"<loc>{server.SITE}/{path}</loc><lastmod>{voice_pages.UPDATED}</lastmod>", sm)
        self.assertIn('<th scope="row"><a href="/voices/hindi.html">Hindi</a></th>', v)
        self.assertEqual(self.c.get("/voices/klingon.html").status_code, 404)

    def test_no_shared_paragraphs(self):
        seen = collections.defaultdict(set)
        for path in voice_pages.PATHS:
            for block in re.findall(r"<(?:p|li)>(.*?)</(?:p|li)>", main_of(self.pages[path].text), re.S):
                if not re.fullmatch(r"<a [^>]*>[^<]*</a>", block):  # link lists (related pages) are navigation
                    seen[block].add(path)
        shared = {b: p for b, p in seen.items() if len(p) > 1}
        self.assertEqual(shared, {})


if __name__ == "__main__":
    unittest.main()
