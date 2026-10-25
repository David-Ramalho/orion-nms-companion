"""Isolated browser QA server: deterministic replies, no external provider requests."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ["NMS_COMPANION_DATA"] = str(Path(__file__).resolve().parents[1]/".test-data"/"browser")
from companion.app import app
from companion import providers
import companion.app as module
original_config = module.load_config
def config():
    cfg=original_config()
    cfg.update(provider_mode="ollama",ollama_model="fixture",tts_enabled=False)
    return cfg
module.load_config=config
module.get_key=lambda:None
def reply(config,messages,stop_event=None):
    if "[slow]" in messages[-1]["content"]:
        yield "Aguardando teste. "
        if stop_event is not None and stop_event.wait(2):
            return
    yield "Diário consultado. "
    yield "Podemos retomar a exploração do Big Forest Empire."
providers.ollama_stream=reply
providers.ollama_models=lambda config: [{"name":"fixture"},{"name":"fixture-other"}]
providers.model_details=lambda config,model=None: {"model":model or "fixture","context_length":128000,"default_context_length":32768,"model_defaults":{"num_ctx":32768,"temperature":0.05},"effective_settings":config}
app.run(host="127.0.0.1",port=8766,threaded=True,use_reloader=False)
