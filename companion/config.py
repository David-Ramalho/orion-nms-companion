from __future__ import annotations

import json
import os
import re
from urllib.parse import urlsplit
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
    "ollama_num_ctx": 32768,
    "ollama_num_predict": 512,
    "ollama_temperature": 0.7,
    "ollama_num_thread": 0,
    "ollama_num_gpu": -1,
    "ollama_keep_alive": "5m",
    "ollama_think": False,
    "provider_timeout": 180,
    "ollama_model_settings": {},
    "gemini_model": "gemini-3.8-flash",
    "cloud_fallback": False,
    "cloud_consent": False,
    "system_prompt": "You are Orion (Ori), a calm, curious exosuit AI companion exploring No Man's Sky with the player. Be warm, concise, observant, and honest. Never claim to see the game unless the user provides game context. Keep spoken replies natural and brief; use readable paragraphs.",
    "stt_model": "tiny",
    "stt_language": "auto",
    "quiet_mode": False,
    "reply_style": "explorer",
    "proactive_interval": 180,
    "save_bindings": {},
    "active_profile": "default",
    "keymap_path": "",
    "libnom_cli": "",
    "tts_enabled": True,
    "voice_rate": 1.2,
    "voice_name": "",
}


def load_config() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        saved = {}
    if not isinstance(saved, dict):
        saved = {}
    current = {**DEFAULTS, **saved}
    # Rename the original prototype persona without discarding a user's other settings.
    current["system_prompt"] = (current.get("system_prompt") or DEFAULTS["system_prompt"]).replace("You are Aster", "You are Orion (Ori)")
    return current


# Zero context/threads means Ollama chooses; model-specific values override the
# shared defaults only for that model. A model's advertised maximum is not a
# recommendation to allocate that whole context window.
OLLAMA_FIELDS = (
    "ollama_num_ctx", "ollama_num_predict", "ollama_temperature",
    "ollama_num_thread", "ollama_num_gpu", "ollama_keep_alive", "ollama_think", "provider_timeout",
)


def _number(value, key, minimum, maximum, integer=True):
    try:
        result = int(value) if integer else float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid numeric setting: {key}") from exc
    if not minimum <= result <= maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}.")
    return result


def validate_ollama_settings(values):
    result = {}
    limits = {
        "ollama_num_ctx": (0, 1048576, True),
        "ollama_num_predict": (1, 65536, True),
        "ollama_temperature": (0, 2, False),
        "ollama_num_thread": (0, 128, True),
        "ollama_num_gpu": (-1, 256, True),
        "provider_timeout": (15, 900, True),
    }
    for key, limit in limits.items():
        if key in values:
            result[key] = _number(values[key], key, *limit)
    if "ollama_keep_alive" in values:
        value = str(values["ollama_keep_alive"]).strip()
        if not re.fullmatch(r"-?\d+(?:\.\d+)?(?:ms|s|m|h)?", value):
            raise ValueError("Keep alive must be a duration such as 5m, 0 or -1.")
        result["ollama_keep_alive"] = value
    if "ollama_think" in values:
        if not isinstance(values["ollama_think"], bool):
            raise ValueError("Thinking must be true or false.")
        result["ollama_think"] = values["ollama_think"]
    return result


def effective_ollama_config(config, model=None):
    current = {**DEFAULTS, **config}
    selected = str(model if model is not None else current.get("ollama_model", "")).strip()
    mapping = current.get("ollama_model_settings")
    specific = mapping.get(selected, {}) if isinstance(mapping, dict) else {}
    if isinstance(specific, dict):
        current.update(validate_ollama_settings(specific))
    current["ollama_model"] = selected
    return current


def save_config(values: dict) -> dict:
    with _lock:
        current = load_config()
        for key in DEFAULTS:
            if key in values:
                current[key] = values[key]
        current["provider_mode"] = current["provider_mode"] if current["provider_mode"] in ("auto", "ollama", "gemini") else "auto"
        if current["stt_language"] not in ("auto", "pt", "en"):
            raise ValueError("Idioma inválido.")
        if current["stt_model"] not in ("tiny", "base", "tiny.en", "base.en"):
            raise ValueError("Modelo de voz inválido.")
        if current["stt_language"] != "en" and current["stt_model"].endswith(".en"):
            current["stt_model"] = current["stt_model"].replace(".en", "")
        if current["reply_style"] not in ("explorer", "technical", "narrative"):
            raise ValueError("Estilo inválido.")
        current["voice_rate"] = min(2.0, max(0.6, float(current["voice_rate"])))
        current["ollama_url"] = str(current["ollama_url"]).rstrip("/")
        parsed = urlsplit(current["ollama_url"])
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Ollama URL must be an HTTP(S) server address without credentials or query.")
        current.update(validate_ollama_settings(current))
        mapping = current.get("ollama_model_settings", {})
        if not isinstance(mapping, dict) or len(mapping) > 200:
            raise ValueError("Invalid per-model settings.")
        clean_mapping = {}
        for model, options in mapping.items():
            if not isinstance(model, str) or not model.strip() or len(model) > 300 or not isinstance(options, dict):
                raise ValueError("Invalid per-model settings.")
            clean_mapping[model] = validate_ollama_settings(options)
        current["ollama_model_settings"] = clean_mapping
        temporary = CONFIG_PATH.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(current, indent=2), encoding="utf-8")
        temporary.replace(CONFIG_PATH)
        return current
