from __future__ import annotations

import json
import urllib.error
import urllib.request


class ProviderError(RuntimeError):
    pass


def _request(url, payload, headers=None, timeout=90):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    return urllib.request.urlopen(req, timeout=timeout)


def ollama_stream(config, messages):
    model = config.get("ollama_model", "").strip()
    if not model:
        raise ProviderError("Choose an installed Ollama model in Settings first.")
    try:
        response = _request(config.get("ollama_url", "http://127.0.0.1:11434") + "/api/chat", {"model": model, "messages": messages, "stream": True, "options": {"num_ctx": 4096}})
        for line in response:
            if not line.strip():
                continue
            packet = json.loads(line)
            text = packet.get("message", {}).get("content", "")
            if text:
                yield text
            if packet.get("done"):
                break
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(f"Ollama unavailable: {exc}") from exc


def gemini_stream(config, messages, api_key):
    if not api_key:
        raise ProviderError("Gemini API key is not configured in this app.")
    model = config["gemini_model"].strip() or "gemini-2.5-flash"
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages if m["role"] != "system"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
    req = urllib.request.Request(url, data=json.dumps({"systemInstruction": {"parts": [{"text": system}]}, "contents": contents, "generationConfig": {"temperature": 0.75, "maxOutputTokens": 700}}).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": api_key}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            for raw in response:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    packet = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                for candidate in packet.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        if part.get("text"):
                            yield part["text"]
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", "replace")[:500]
        raise ProviderError(f"Gemini returned HTTP {exc.code}: {details}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProviderError(f"Gemini connection failed: {exc}") from exc


def stream_reply(config, messages, api_key=None):
    mode = config["provider_mode"]
    if mode == "ollama":
        yield from ollama_stream(config, messages)
        return "Ollama"
    if mode == "gemini":
        yield from gemini_stream(config, messages, api_key)
        return "Gemini"
    try:
        yield from ollama_stream(config, messages)
        return "Ollama"
    except ProviderError as local_error:
        if not (config.get("cloud_fallback") and config.get("cloud_consent")):
            raise ProviderError(f"{local_error} Auto mode is local-only unless Gemini fallback is explicitly enabled.") from local_error
    yield from gemini_stream(config, messages, api_key)
    return "Gemini"
