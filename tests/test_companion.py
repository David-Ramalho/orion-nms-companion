import io
import json
import wave
import unittest
from pathlib import Path
from unittest.mock import patch

from companion import memory, providers
from companion.app import app


class CompanionTests(unittest.TestCase):
    def setUp(self):
        test_data = Path(__file__).parent / ".runtime"
        test_data.mkdir(exist_ok=True)
        memory.DB_PATH = test_data / f"test-{self.id().split('.')[-1]}.sqlite3"
        memory.DB_PATH.unlink(missing_ok=True)
        app.testing = True
        self.client = app.test_client()

    def tearDown(self):
        memory.DB_PATH.unlink(missing_ok=True)
        Path(str(memory.DB_PATH) + "-wal").unlink(missing_ok=True)
        Path(str(memory.DB_PATH) + "-shm").unlink(missing_ok=True)

    def test_memory_persists_notes_and_history(self):
        memory.add_fact("My ship is called Wayfarer")
        memory.add_message("user", "Remember the ship")
        memory.add_message("assistant", "Wayfarer is noted.")
        self.assertEqual(memory.facts(), ["My ship is called Wayfarer"])
        self.assertEqual([m["role"] for m in memory.history()], ["user", "assistant"])

    def test_ollama_stream_decodes_ndjson_deltas(self):
        response = io.BytesIO(b'{"message":{"content":"Hello"},"done":false}\n{"message":{"content":" there."},"done":true}\n')
        with patch("companion.providers._request", return_value=response):
            result = list(providers.ollama_stream({"ollama_model": "fixture", "ollama_url": "http://localhost"}, []))
        self.assertEqual(result, ["Hello", " there."])

    def test_gemini_stream_uses_key_header_and_parses_sse(self):
        response = io.BytesIO(b'data: {"candidates":[{"content":{"parts":[{"text":"Orion"}]}}]}\n\ndata: {"candidates":[{"content":{"parts":[{"text":" online."}]}}]}\n')
        with patch("companion.providers.urllib.request.urlopen", return_value=response) as open_mock:
            result = list(providers.gemini_stream({"gemini_model": "fixture"}, [{"role": "user", "content": "hi"}], "secret-test"))
        req = open_mock.call_args.args[0]
        self.assertEqual(req.get_header("X-goog-api-key"), "secret-test")
        self.assertEqual(result, ["Orion", " online."])

    def test_auto_mode_does_not_fall_back_to_cloud_without_opt_in(self):
        config = {"provider_mode": "auto", "ollama_url": "http://127.0.0.1:1", "cloud_fallback": False, "cloud_consent": False}
        with self.assertRaises(providers.ProviderError):
            list(providers.stream_reply(config, [], api_key="secret-test"))

    def test_streaming_chat_returns_deltas_and_persists_turn(self):
        config = {"provider_mode": "ollama", "ollama_url": "http://localhost", "ollama_model": "fixture", "system_prompt": "Be brief"}
        with patch("companion.app.load_config", return_value=config), patch("companion.app.providers.ollama_stream", return_value=iter(["Hello", " Traveller."])):
            response = self.client.post("/api/chat/stream", json={"text": "Hi"}, buffered=True)
        records = [json.loads(line) for line in response.data.decode().splitlines()]
        self.assertEqual([r["type"] for r in records], ["start", "delta", "delta", "done"])
        self.assertEqual(records[0]["provider"],"Ollama")
        self.assertEqual(records[0]["model"],"fixture")
        self.assertEqual(memory.history()[-1]["content"], "Hello Traveller.")

    def test_manual_gemini_requires_cloud_consent(self):
        config = {"provider_mode": "gemini", "cloud_consent": False, "system_prompt": "Be brief"}
        with patch("companion.app.load_config", return_value=config), patch("companion.app.get_key", return_value="fixture-key"), patch("companion.app.providers.gemini_stream") as call:
            response = self.client.post("/api/chat/stream", json={"text": "Hi"}, buffered=True)
        records = [json.loads(line) for line in response.data.decode().splitlines()]
        self.assertEqual(records[0]["type"], "error")
        call.assert_not_called()

    def test_home_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ORION", response.data)

    def test_audio_decoder_accepts_uploaded_wave(self):
        from faster_whisper.audio import decode_audio
        audio_path = memory.DB_PATH.parent / "silence.wav"
        with wave.open(str(audio_path), "wb") as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000); wav.writeframes(b"\x00\x00" * 16000)
        decoded = decode_audio(str(audio_path))
        self.assertEqual(len(decoded), 16000)
        audio_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
