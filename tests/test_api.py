"""Deterministic API regression tests (no network): the speech provider is mocked.
Run: .venv/Scripts/python -m unittest tests/test_api.py -v   (needs ffmpeg + httpx)

Tests marked @expectedFailure pin a known, still-open defect.
When the defect is fixed the test reports "unexpected success": remove the marker."""
import asyncio
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

    @unittest.expectedFailure  # TTS-BUG-005: subtitles never use engine word timings
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
