"""Behavioral regression tests for cancellation, profile isolation and resource actions."""
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from companion import memory
from companion.app import app

module = importlib.import_module("companion.app")
CFG = {"provider_mode":"ollama","ollama_model":"fixture","system_prompt":"Be concise"}

class TurnLifecycleTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).parent / ".runtime"
        parent.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.old = memory.DB_PATH
        memory.DB_PATH = Path(self.temp.name) / "memory.sqlite3"
        self.client = app.test_client()
        app.testing = True

    def tearDown(self):
        memory.DB_PATH = self.old
        self.temp.cleanup()

    def test_clear_while_streaming_cannot_restore_reply(self):
        memory.add_fact("Keep my ship")
        memory.add_entry("default",{"title":"Keep my goal","content":"Build an observatory","kind":"goal"})
        def fragments(*args, **kwargs):
            yield "Hello "
            self.client.post("/api/memory/clear-history", json={})
            yield "again"
        with patch.object(module, "load_config", return_value=CFG), patch.object(module.providers,"ollama_stream", side_effect=fragments):
            response = self.client.post("/api/chat/stream", json={"text":"Hello"}, buffered=True)
        records = [json.loads(line) for line in response.data.splitlines()]
        self.assertEqual(records[-1]["type"],"cancelled")
        self.assertEqual(memory.history(),[])
        self.assertEqual(memory.facts(),["Keep my ship"])
        self.assertEqual(len(memory.entries("default")),1)
        self.assertFalse(module._turn_lock.locked())

    def test_other_profile_clear_does_not_cancel_current_reply(self):
        other = memory.add_profile("Other")
        memory.add_message("user","Other history",other)
        def fragments(*args,**kwargs):
            yield "A"
            self.client.post("/api/memory/clear-history?profile="+other,json={})
            yield "B"
        with patch.object(module,"load_config",return_value=CFG), patch.object(module.providers,"ollama_stream",side_effect=fragments):
            response = self.client.post("/api/chat/stream",json={"text":"Hi"},buffered=True)
        self.assertIn(b'"done"',response.data)
        self.assertEqual(memory.history()[-1]["content"],"AB")
        self.assertEqual(memory.history(profile=other),[])

    def test_context_failure_releases_lock(self):
        with patch.object(module,"load_config",return_value=CFG), patch.object(memory,"context",side_effect=RuntimeError("fixture")):
            with self.assertRaises(RuntimeError):
                self.client.post("/api/chat/stream",json={"text":"Hi"})
        self.assertFalse(module._turn_lock.locked())

    def test_busy_turn_rejects_unload_and_new_turn(self):
        module._turn_lock.acquire()
        try:
            self.assertEqual(self.client.post("/api/models/unload",json={}).status_code,409)
            self.assertEqual(self.client.post("/api/chat/stream",json={"text":"Hi"}).status_code,409)
        finally:
            module._turn_lock.release()

    def test_model_details_passes_selected_model(self):
        with patch.object(module.providers,"model_details",return_value={"context_length":32768}) as call:
            response = self.client.get("/api/models/details?model=Liquid32k")
        self.assertEqual(response.json["context_length"],32768)
        self.assertEqual(call.call_args.args[1],"Liquid32k")

    def test_explicit_unload_uses_selected_model(self):
        with patch.object(module,"load_config",return_value=dict(CFG)), patch.object(module.providers,"unload_ollama") as call:
            response = self.client.post("/api/models/unload",json={"model":"other"})
        self.assertTrue(response.json["ok"])
        self.assertEqual(call.call_args.args[0]["ollama_model"],"other")
