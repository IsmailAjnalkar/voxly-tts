"""Deterministic API regression tests (no network): the speech provider is mocked.
Run: .venv/Scripts/python -m unittest tests/test_api.py -v   (needs ffmpeg + httpx)

Tests marked @expectedFailure pin a known defect from audit/DEFECT_REGISTER.csv.
When the defect is fixed the test reports "unexpected success": remove the marker."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

VOICES = [
    {"ShortName": "en-US-AriaNeural", "Locale": "en-US", "Gender": "Female", "FriendlyName": "Aria"},
    {"ShortName": "en-US-AndrewNeural", "Locale": "en-US", "Gender": "Male", "FriendlyName": "Andrew"},
    {"ShortName": "en-US-AndrewMultilingualNeural", "Locale": "en-US", "Gender": "Male", "FriendlyName": "Andrew ML"},
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

    def tts(self, **body):
        return self.c.post("/api/tts", json={"voice": "en-US-AriaNeural", **body}, headers=H)

    # ---------- current, correct behaviour ----------
    def test_validation(self):
        self.assertEqual(self.tts(text="").status_code, 400)
        self.assertEqual(self.tts(text="   ").status_code, 400)
        self.assertEqual(self.tts(text="hi", voice="xx-XX-Nope").status_code, 400)
        self.assertEqual(self.tts(text="hi", format="ogg").status_code, 400)
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

    def test_path_traversal(self):
        self.assertEqual(self.c.get("/api/file/..%2f..%2fserver.py", headers=H).status_code, 404)

    def test_parse_segments_caps_single_break(self):
        self.assertEqual(server.parse_segments("[break:99s]"), [{"type": "silence", "ms": 30000}])

    # ---------- known defects (see audit/DEFECT_REGISTER.csv) ----------
    @unittest.expectedFailure  # TTS-BUG-001: no server-side text length limit
    def test_rejects_oversized_text(self):
        self.assertIn(self.tts(text="a" * 200_000).status_code, (400, 413))

    @unittest.expectedFailure  # TTS-BUG-002: break markers amplify into unbounded silence
    def test_rejects_excessive_total_silence(self):
        self.assertIn(self.tts(text="[break:30s]" * 100 + " hi").status_code, (400, 413))

    @unittest.expectedFailure  # TTS-BUG-009: break-only input yields a silent file
    def test_break_only_text_is_rejected(self):
        self.assertEqual(self.tts(text="[break:1s][break:2s]").status_code, 400)

    @unittest.expectedFailure  # TTS-BUG-005: subtitles never use engine word timings
    def test_requests_word_boundaries(self):
        async def no_chunks():
            return
            yield
        with mock.patch.object(server.edge_tts, "Communicate") as comm:
            comm.return_value.stream = no_chunks
            server.asyncio.run(ORIGINAL_SYNTH("hi", "en-US-AriaNeural", "+0%", "+0Hz"))
        self.assertEqual(comm.call_args.kwargs.get("boundary"), "WordBoundary")

    @unittest.expectedFailure  # TTS-BUG-014: malformed JSON returns 500
    def test_malformed_json_is_4xx(self):
        r = self.c.post("/api/tts", content=b"{not json", headers={**H, "Content-Type": "application/json"})
        self.assertLess(r.status_code, 500)

    @unittest.expectedFailure  # TTS-BUG-014: non-numeric speed returns 500
    def test_non_numeric_speed_is_4xx(self):
        self.assertLess(self.tts(text="hi", speed="fast").status_code, 500)

    @unittest.expectedFailure  # TTS-BUG-019: GET /api/file creates a directory per arbitrary session id
    def test_file_get_does_not_create_session_dir(self):
        self.c.get("/api/file/x.mp3?s=brandnewsession42")
        self.assertFalse((server.DATA / "brandnewsession42").exists())

    @unittest.expectedFailure  # TTS-BUG-012: duplicate voice display names
    def test_voice_display_names_unique(self):
        names = [v["name"] for v in self.c.get("/api/voices").json()["voices"]]
        self.assertEqual(len(names), len(set(names)), names)


if __name__ == "__main__":
    unittest.main()
