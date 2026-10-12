from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock

APP_NAME = "NMS-Exosuit-Companion"
DATA_DIR = Path(os.environ.get("NMS_COMPANION_DATA", Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME))
CONFIG_PATH = DATA_DIR / "settings.json"
_lock = Lock()
DEFAULTS = {
    "provider_mode": "auto",
    "ollama_url": "http://127.0.0.1:11434",
    "ollama_model": "",
    "gemini_model": "gemini-3.8-flash",
    "cloud_fallback": False,
    "cloud_consent": False,
    "system_prompt": "You are Orion (Ori), a calm, curious exosuit AI companion exploring No Man's Sky with the player. Be warm, concise, observant, and honest. Never claim to see the game unless the user provides game context. Keep spoken replies natural and brief; use readable paragraphs.",
    "stt_model": "base.en",
    "voice_rate": 1.2,
    "voice_name": "",
}


def load_config() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        saved = {}
    current = {**DEFAULTS, **saved}
    # Rename the original prototype persona without discarding a user's other settings.
    current["system_prompt"] = current.get("system_prompt", DEFAULTS["system_prompt"]).replace("You are Aster", "You are Orion (Ori)")
    return current


def save_config(values: dict) -> dict:
    with _lock:
        current = load_config()
        for key in DEFAULTS:
            if key in values:
                current[key] = values[key]
        current["provider_mode"] = current["provider_mode"] if current["provider_mode"] in ("auto", "ollama", "gemini") else "auto"
        current["voice_rate"] = min(2.0, max(0.6, float(current["voice_rate"])))
        current["ollama_url"] = str(current["ollama_url"]).rstrip("/")
        CONFIG_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
        return current
