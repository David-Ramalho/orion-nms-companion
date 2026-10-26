import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from companion import config


class ModelConfigTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / ".test-data"
        test_root.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=test_root)
        self.root = Path(self.directory.name)
        self.paths = patch.multiple(config, DATA_DIR=self.root, CONFIG_PATH=self.root / "settings.json")
        self.paths.start()
    def tearDown(self):
        self.paths.stop()
        self.directory.cleanup()
    def test_defaults_preserve_32k(self):
        self.assertEqual(config.load_config()["ollama_num_ctx"], 32768)
    def test_per_model_options_persist_independently(self):
        config.save_config({"ollama_model_settings":{
            "liquid": {"ollama_num_ctx":32768,"provider_timeout":300},
            "echo": {"ollama_num_ctx":8192,"ollama_temperature":0.4}}})
        current = config.load_config()
        self.assertEqual(config.effective_ollama_config(current,"liquid")["ollama_num_ctx"],32768)
        self.assertEqual(config.effective_ollama_config(current,"echo")["ollama_num_ctx"],8192)
        self.assertEqual(config.effective_ollama_config(current,"another")["ollama_num_ctx"],32768)
    def test_invalid_options_do_not_modify_saved_file(self):
        config.save_config({"ollama_model":"liquid"})
        before = config.CONFIG_PATH.read_bytes()
        with self.assertRaises(ValueError):
            config.save_config({"ollama_model_settings":{"liquid":{"provider_timeout":1}}})
        self.assertEqual(config.CONFIG_PATH.read_bytes(), before)
    def test_zero_context_and_threads_allow_automatic(self):
        current = config.save_config({"ollama_num_ctx":0,"ollama_num_thread":0})
        self.assertEqual(current["ollama_num_ctx"],0)
    def test_unknown_model_fields_are_removed(self):
        current = config.save_config({"ollama_model_settings":{"liquid":{"ollama_num_ctx":32768,"api_key":"secret"}}})
        self.assertNotIn("api_key",current["ollama_model_settings"]["liquid"])
    def test_invalid_url_and_keepalive_rejected(self):
        for values in ({"ollama_url":"file:///private"},{"ollama_keep_alive":"surprise"},{"ollama_temperature":float('nan')}):
            with self.assertRaises(ValueError):
                config.save_config(values)


    def test_gpu_offload_is_independent_per_model_and_validated(self):
        current=config.save_config({"ollama_model_settings":{
            "large":{"ollama_num_gpu":0,"ollama_num_ctx":32768},
            "small":{"ollama_num_gpu":12}}})
        self.assertEqual(config.effective_ollama_config(current,"large")["ollama_num_gpu"],0)
        self.assertEqual(config.effective_ollama_config(current,"small")["ollama_num_gpu"],12)
        self.assertEqual(config.effective_ollama_config(current,"other")["ollama_num_gpu"],-1)
        with self.assertRaises(ValueError):
            config.save_config({"ollama_num_gpu":-2})

if __name__ == "__main__":
    unittest.main()
