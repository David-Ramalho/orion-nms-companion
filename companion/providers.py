from __future__ import annotations

import json
import http.client
import io
import socket
import _socket
import threading
from urllib.parse import urlsplit

from .config import effective_ollama_config, OLLAMA_FIELDS
import urllib.error
import urllib.request


class ProviderError(RuntimeError):
    pass


def _limit(config, key, default, minimum, maximum):
    try:
        return max(minimum, min(maximum, int(config.get(key, default))))
    except (TypeError, ValueError):
        return default


def _response_socket(response):
    try:
        return response.fp.raw._sock
    except AttributeError:
        return None


def _watch_cancel(stop_event, finished, socket_getter):
    if stop_event is None:
        return
    def cancel():
        while not finished.wait(0.1):
            if stop_event.is_set():
                active_socket = socket_getter()
                if active_socket is not None:
                    try:
                        active_socket.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    # On Windows, BufferedReader's makefile reference can keep
                    # close() deferred and recv blocked after shutdown(). Close
                    # the underlying socket handle; later wrapper cleanup is
                    # safe because its descriptor is already invalidated.
                    try:
                        _socket.socket.close(active_socket)
                    except OSError:
                        pass
                    return
    threading.Thread(target=cancel, name="ori-provider-cancel", daemon=True).start()


class _ConnectionResponse:
    """Own both the HTTP response and cancellation watcher lifetime."""
    def __init__(self, response, connection, finished):
        self.response, self.connection, self.finished = response, connection, finished
    def __iter__(self):
        return iter(self.response)
    def read(self, *args):
        return self.response.read(*args)
    def close(self):
        self.finished.set()
        self.response.close()
        self.connection.close()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


def _request(url, payload, headers=None, timeout=180, stop_event=None):
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", **(headers or {})}
    if stop_event is None:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        return urllib.request.urlopen(req, timeout=timeout)
    # A socket remains reachable while Ollama is loading the model, before HTTP
    # headers arrive. Shutting it down lets Stop/Clear interrupt that wait too.
    parsed = urlsplit(url)
    connection_type = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    connection = connection_type(parsed.hostname, parsed.port, timeout=timeout)
    finished = threading.Event()
    response_holder = [None]
    def active_socket():
        return connection.sock or _response_socket(response_holder[0])
    _watch_cancel(stop_event, finished, active_socket)
    try:
        connection.request("POST", parsed.path or "/", body=body, headers=headers)
        response = connection.getresponse()
        response_holder[0] = response
        if response.status >= 400:
            detail = response.read(1000)
            raise urllib.error.HTTPError(url, response.status, response.reason, response.headers, io.BytesIO(detail))
        return _ConnectionResponse(response, connection, finished)
    except BaseException:
        finished.set()
        connection.close()
        raise


def _ollama_error(exc, timeout):
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 404:
            return "Modelo Ollama nao encontrado. Atualize a lista e escolha um modelo instalado."
        if exc.code == 503:
            return "Ollama respondeu 503: servidor ocupado ou sem recursos para carregar o modelo. Confira os logs do Ollama."
        try:
            detail = json.loads(exc.read(1000)).get("error", "")
        except (ValueError, OSError):
            detail = ""
        lower_detail = str(detail).lower()
        if any(message in lower_detail for message in ("does not support chat", "does not support generate", "does not support completion")):
            return "Este modelo Ollama nao oferece geracao de conversa. Modelos apenas de embeddings ou ranking nao podem responder ao chat; escolha um modelo de texto."
        if "does not support thinking" in lower_detail:
            return "Este modelo Ollama nao aceita raciocinio. Desative Pensar nos parametros deste modelo e envie novamente."
        return f"Ollama respondeu HTTP {exc.code}. {str(detail)[:240]}".strip()
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
        return (f"Ollama nao enviou dados por {timeout}s. O servidor pode estar carregando o modelo "
                "ou processando o contexto; isso nao confirma que esta offline. "
                "Aumente o tempo de espera nos parametros, confira o modelo carregado e os logs do Ollama.")
    return "Nao foi possivel conectar ao Ollama. Confira se o servidor esta iniciado e a URL em Configuracoes."


def ollama_models(config):
    try:
        with urllib.request.urlopen(config.get("ollama_url", "http://127.0.0.1:11434").rstrip("/") + "/api/tags", timeout=5) as response:
            packet = json.load(response)
        return packet.get("models", [])
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise ProviderError(_ollama_error(exc, 5)) from exc


def model_details(config, model=None):
    selected = str(model if model is not None else config.get("ollama_model", "")).strip()
    if not selected:
        raise ProviderError("Choose an installed Ollama model in Settings first.")
    try:
        with _request(config.get("ollama_url", "http://127.0.0.1:11434").rstrip("/") + "/api/show", {"model": selected}, timeout=10) as response:
            packet = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise ProviderError(_ollama_error(exc, 10)) from exc
    info = packet.get("model_info", {})
    contexts = [int(value) for key, value in info.items()
                if key.endswith(".context_length") and isinstance(value, (int, float)) and value > 0]
    defaults = {}
    for line in packet.get("parameters", "").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            try:
                defaults[parts[0]] = json.loads(parts[1])
            except ValueError:
                defaults[parts[0]] = parts[1]
    details = packet.get("details", {})
    effective = effective_ollama_config(config, selected)
    return {"model": selected, "context_length": max(contexts, default=None),
            "default_context_length": defaults.get("num_ctx"),
            "family": details.get("family", ""), "parameter_size": details.get("parameter_size", ""),
            "quantization_level": details.get("quantization_level", ""),
            "capabilities": packet.get("capabilities", []), "model_defaults": defaults,
            "effective_settings": {key: effective[key] for key in OLLAMA_FIELDS}}


class _VisibleOllamaText:
    """Suppress inline reasoning used by some Liquid model templates.

    Delimiters may be split across packets. Retain only a delimiter prefix,
    discarding hidden content as it arrives instead of accumulating it.
    """
    def __init__(self):
        self.hidden = False
        self.pending = ""

    def feed(self, text):
        self.pending += text
        visible = []
        while self.pending:
            delimiter = "</think>" if self.hidden else "<think>"
            index = self.pending.lower().find(delimiter)
            if index >= 0:
                if not self.hidden:
                    visible.append(self.pending[:index])
                self.pending = self.pending[index + len(delimiter):]
                self.hidden = not self.hidden
                continue
            keep = 0
            for length in range(1, min(len(delimiter), len(self.pending) + 1)):
                if self.pending[-length:].lower() == delimiter[:length]:
                    keep = length
            ready = self.pending[:-keep] if keep else self.pending
            if not self.hidden:
                visible.append(ready)
            self.pending = self.pending[-keep:] if keep else ""
            break
        return "".join(visible)

    def finish(self):
        return "" if self.hidden else self.pending


def ollama_stream(config, messages, stop_event=None):
    if stop_event is not None and stop_event.is_set():
        return
    config = effective_ollama_config(config)
    response = None
    emitted = False
    visible_text = _VisibleOllamaText()
    model = config.get("ollama_model", "").strip()
    if not model:
        raise ProviderError("Choose an installed Ollama model in Settings first.")
    timeout = _limit(config, "provider_timeout", 180, 15, 900)
    options = {"num_predict": _limit(config, "ollama_num_predict", 512, 1, 65536),
               "temperature": float(config.get("ollama_temperature", 0.7))}
    context = _limit(config, "ollama_num_ctx", 32768, 0, 1048576)
    threads = _limit(config, "ollama_num_thread", 0, 0, 128)
    if context:
        options["num_ctx"] = context
    if threads:
        options["num_thread"] = threads
    try:
        response = _request(config.get("ollama_url", "http://127.0.0.1:11434").rstrip("/") + "/api/chat",
                            {"model": model, "messages": messages, "stream": True,
                             "think": bool(config.get("ollama_think", False)),
                             "keep_alive": config.get("ollama_keep_alive", "5m"), "options": options},
                            timeout=timeout, stop_event=stop_event)
        for line in response:
            if stop_event is not None and stop_event.is_set():
                return
            if not line.strip():
                continue
            packet = json.loads(line)
            if packet.get("error"):
                raise ProviderError(str(packet["error"])[:240])
            text = visible_text.feed(packet.get("message", {}).get("content", ""))
            if text and (emitted or text.strip()):
                emitted = True
                yield text
            if packet.get("done"):
                break
        tail = visible_text.finish()
        if tail and (emitted or tail.strip()) and (stop_event is None or not stop_event.is_set()):
            emitted = True
            yield tail
        if not emitted and (stop_event is None or not stop_event.is_set()):
            raise ProviderError("Ollama terminou sem texto. Confira o modelo e aumente o limite de resposta se o raciocinio consumiu a geracao.")
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
        if stop_event is None or not stop_event.is_set():
            raise ProviderError(_ollama_error(exc, timeout)) from exc
    except (json.JSONDecodeError, ValueError) as exc:
        if stop_event is None or not stop_event.is_set():
            raise ProviderError("Ollama enviou uma resposta invalida. Confira a URL e os logs do servidor.") from exc
    finally:
        if response is not None:
            response.close()


def gemini_stream(config, messages, api_key, stop_event=None):
    if stop_event is not None and stop_event.is_set():
        return
    if not api_key:
        raise ProviderError("Gemini API key is not configured in this app.")
    model = config["gemini_model"].strip() or "gemini-2.5-flash"
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages if m["role"] != "system"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
    req = urllib.request.Request(url, data=json.dumps({"systemInstruction": {"parts": [{"text": system}]}, "contents": contents, "generationConfig": {"temperature": 0.75, "maxOutputTokens": 700}}).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": api_key}, method="POST")
    finished = threading.Event()
    try:
        with urllib.request.urlopen(req, timeout=_limit(config, "provider_timeout", 180, 15, 900)) as response:
            _watch_cancel(stop_event, finished, lambda: _response_socket(response))
            for raw in response:
                if stop_event is not None and stop_event.is_set():
                    return
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    packet = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                for candidate in packet.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        if part.get("text") and not part.get("thought", False):
                            yield part["text"]
    except urllib.error.HTTPError as exc:
        if exc.code==503:
            raise ProviderError("Gemini temporariamente indisponível (503). O serviço pode estar ocupado. Aguarde alguns segundos e envie a mensagem novamente; se persistir, consulte outro modelo disponível. Sua chave não precisa ser salva novamente.") from exc
        if exc.code==429:
            raise ProviderError("Quota do Gemini atingida (429). Aguarde a renovação da quota ou selecione Ollama. Nenhuma repetição automática foi feita.") from exc
        if exc.code in (401,403):
            raise ProviderError("Gemini: chave ou permissão inválida. Confira a chave e o projeto no Google AI Studio.") from exc
        if exc.code==404:
            raise ProviderError("Modelo Gemini indisponível. Consulte os modelos da sua chave nas configurações.") from exc
        raise ProviderError(f"Gemini retornou HTTP {exc.code}. Consulte o Google AI Studio.") from exc
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
        if stop_event is None or not stop_event.is_set():
            raise ProviderError("Gemini: conexao interrompida ou tempo de espera excedido. Tente novamente.") from exc
    finally:
        finished.set()


def unload_ollama(config):
    model = config.get("ollama_model", "").strip()
    if not model:
        raise ProviderError("Choose an installed Ollama model first.")
    try:
        with _request(config.get("ollama_url", "http://127.0.0.1:11434") + "/api/generate",
                      {"model": model, "keep_alive": 0}, timeout=5) as response:
            response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProviderError(f"Could not unload Ollama: {exc}") from exc


def stream_reply(config, messages, api_key=None, stop_event=None):
    mode = config["provider_mode"]
    if mode == "gemini":
        yield from gemini_stream(config, messages, api_key, stop_event)
        return "Gemini"
    if mode not in ("ollama", "auto"):
        raise ProviderError("Unknown provider mode. Select Ollama or Gemini in Settings.")
    emitted = False
    try:
        for text in ollama_stream(config, messages, stop_event):
            emitted = True
            yield text
        return "Ollama"
    except ProviderError:
        if (emitted or mode != "auto" or not config.get("cloud_fallback")
                or not config.get("cloud_consent")
                or (stop_event is not None and stop_event.is_set())):
            raise
    yield from gemini_stream(config, messages, api_key, stop_event)
    return "Gemini"
