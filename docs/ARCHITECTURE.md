# Architecture

## Data flow

```text
Chrome / Edge UI
  ├─ push-to-talk audio (MediaRecorder) ──HTTP──> Flask /api/transcribe
  │                                               └─ faster-whisper CPU/int8 (local)
  ├─ typed or transcribed text ────────HTTP stream──> provider adapter
  │                                               ├─ Ollama /api/chat (local first)
  │                                               └─ Gemini streamGenerateContent (opt-in cloud)
  ├─ provider chunks ──> immediate subtitle updates
  │                  └─ sentence queue ──> browser speechSynthesis
  └─ local settings + SQLite history/mission notes (%LOCALAPPDATA%)
```

The Flask server binds to `127.0.0.1:8765` only. It is a local prototype rather than a hardened multi-user web service. Keep it bound to loopback; do not expose it to a LAN or public network.

## Integration options considered

| Path | Strength | Cost / risk | Current choice |
|---|---|---|---|
| Independent exosuit window (this app) | Full control over immediate subtitles, voice interruption, provider privacy, and memory. | More work to add game data and overlay behavior; doesn't inject a body into NMS. | Prototype foundation. |
| WingmanAI + its NMS profile | Existing push-to-talk, game profile, and NMS Assistant API integration; quickest way to test a game-aware suit persona. | External app setup/account path, current profile compatibility unverified, and subtitle-first UX needs validation. | Re-evaluate for an optional adapter or comparison after user's live setup test. |
| NMS Companion bridge | Existing offline save catalogue and OCR provide a useful local-awareness reference. | Separate app; exact license was not verified, so no code reuse. Bridge format and version compatibility would need review. | Future read-only data source candidate. |
| Native in-game companion mod | Most immersive if a stable model/entity route exists. | No supported stable API for adding/following a custom companion was verified here; game updates and process hooks create high maintenance and safety risk. | Research experiment only; not a blocker for the exosuit persona. |

Sonorus is treated as a design inspiration for an expressive companion, not a reusable NMS integration. The project was built for a different game and its game-specific assets/dependencies cannot be assumed portable.

## Components

- `companion/app.py`: local HTTP routes, transcription lifecycle, provider selection, cancellation, memory API.
- `companion/providers.py`: streamed Ollama NDJSON and Gemini SSE adapters. The Gemini key is sent in an HTTP header, not a URL.
- `companion/memory.py`: SQLite conversation history and user-curated mission notes. Notes are included as context in subsequent prompts.
- `companion/config.py`: defaults and JSON settings in the Windows local application-data directory.
- `static/app.js`: streamed subtitle rendering, phrase/sentence speech queue, stop, microphone capture, settings.
- `templates/index.html` + `static/*.css`: responsive companion interface.

## Provider behavior

| Mode | Behavior | Data sent to cloud |
|---|---|---|
| Automatic | Probe Ollama; use it if reachable. Otherwise Gemini is eligible only if fallback and consent are both saved. | Only after the user explicitly enables cloud fallback and only when local Ollama is unreachable. |
| Ollama only | Use configured Ollama model and endpoint. Errors stay visible. | None from this app. |
| Gemini only | Use configured Gemini API key and model. | The conversation context and selected saved notes go to Google. |

There is no paid-provider fallback. A provider can still impose charges depending on the user's Google API project/account configuration; the app cannot verify account billing status. Check Google AI Studio / Cloud billing before use.

## Latency design

Provider chunks update text immediately. The UI queues completed sentences for browser speech synthesis while later chunks continue arriving. Browser speech starts after a sentence boundary, or after final output for a short reply with no sentence delimiter. The speech rate setting changes synthesis rate. Stop cancels both speech and the active UI request.

Speech recognition is deliberately local and on CPU so it does not compete with the game for GPU resources. It is not streaming recognition yet: the push-to-talk recording is transcribed after release, then the transcript is sent to the AI. This is the principal first-turn latency limitation.

## Game awareness path

No game data is read in this milestone. The next safe integration path is an explicit user-triggered screenshot/OCR and read-only save parsing, behind visible controls and a provenance distinction between verified data and AI inference. NMS Companion demonstrates offline save cataloguing/OCR as a separate application, but its code reuse/license status has not been cleared. WingmanAI plus its NMS profile is the strongest existing voice assistant reference; it has setup/account and configuration-version trade-offs. Native in-game character injection is not assumed feasible or safe for the prototype.
