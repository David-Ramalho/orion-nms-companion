# Orion (Ori) — No Man's Sky Companion

[Português](README.pt-BR.md)

I wanted an AI companion I could actually talk to while exploring No Man's Sky. Someone to keep track of my places, plans and discoveries, and help me pick up where I left off. That's what I'm building with Ori.

Ori runs on my PC with a browser interface, optional Windows subtitle HUD, local voice transcription, and Ollama or Gemini. It can read selected information from an NMS save and keep a separate exploration journal for each character. It is an external companion; it doesn't add a character inside the game.

This is still a prototype. I keep the working features and the limits documented here because a convincing answer isn't proof that the AI understood the save.

## Getting started on Windows

You need **Python 3.12**, Chrome or Edge, and an AI provider. For local AI, install Ollama separately and download a conversation model.

1. Clone or download this repository.
2. Open **start.bat**, or **start-desktop.bat** for the subtitle HUD.
3. Wait for the first setup, then open **http://127.0.0.1:8765** if the browser doesn't open.
4. Under **AI systems**, choose the provider and an installed model. Save settings.
5. Try a typed message first. Then hold the microphone button, speak, and release.
6. Choose a character/profile, open **Expedition & journal**, and link its save.

The first setup downloads Python packages and the versioned save-key map. The first transcription downloads the chosen Whisper model. Later use can stay local with Ollama.

Keep the terminal and **one Ori browser tab** open while using the app. Closing the tab doesn't stop the server. Close the HUD or press **Ctrl+C** in the launcher terminal to finish.

If the launcher says another instance is running, use the existing tab at the local address. The launcher prevents duplicate instances and reports an occupied port; it doesn't kill other programs.

## English or Portuguese

Use the **EN / PT interface selector** to switch the web interface. The browser remembers the choice.

This is separate from the speech-recognition language setting. You can have an English interface and transcribe Portuguese, or the other way around. The model is asked to answer in the language of your message.

## Choosing the model

The list comes from your Ollama server. There is no fixed list of allowed model names: installed conversation models and custom names/tags are supported. Refresh the list after installing one. Embedding/ranking-only models cannot answer chat.

| Mode | What it does |
| --- | --- |
| Ollama only | Sends prompts to the configured Ollama server. |
| Gemini only | Uses the Google API after cloud consent. |
| Automatic | Checks Ollama first; Gemini fallback requires consent, the fallback option, and a configured key. |

Each new answer identifies its source/provider and model. Save connection changes before sending another message.

The default Ollama address is `http://127.0.0.1:11434`. If you use Docker, publish that port to Windows. Useful checks:

```powershell
ollama list
ollama ps
```

The app doesn't start Docker or install Ollama models for you.

### Parameters, without turning this into a full model dashboard

Open **Parameters for this model**. Settings are kept separately for each exact model name.

| Parameter | Initial value | Meaning |
| --- | --- | --- |
| Context | 32768 | Requested context window; 0 lets Ollama choose. |
| Maximum output | 512 | Generation budget, including reasoning for models that produce it. |
| Temperature | 0.7 | General default; use the model's own recommendation when available. |
| CPU threads | 0 | Automatic; a positive value requests that thread count. |
| GPU layers | -1 | Automatic placement; 0 requests CPU only; a positive value requests that many GPU layers. |
| Keep loaded | 5m | 0s unloads after the answer; -1 keeps the model loaded. |
| Timeout | 180 seconds | Connection/read wait; adjustable from 15 to 900 seconds. |
| Thinking | Off | Sends the provider's thinking option when supported. |

**Use model defaults** reads local model metadata. It uses the configured context default when reported, rather than allocating the advertised maximum. Unreported parameters keep their current values.

For Liquid 1.2B Instruct, I use the non-thinking model and can set **32768 context / temperature 0.1 / thinking off**. A 32k window provides room for context; accurate use of that context still depends on the model.

A CUDA out-of-memory error means the selected model failed to load on the GPU. GPU layers can be adjusted per model while keeping the requested context unchanged. CPU-only inference uses system RAM and may be slow or still fail if resources are insufficient.

**Release model memory** asks Ollama to unload the selected model. The next answer has to load it again. This action is blocked during an active response.

### Gemini

Save your Google AI Studio key and allow cloud processing. The key uses **Windows Credential Manager**, with `GEMINI_API_KEY` as an environment-variable alternative.

Use **Check models for my key** to find a model your project can access. Listing a model doesn't guarantee free use. Review the Google project's quota and billing.

- **429:** quota/rate limit.
- **503:** temporary service unavailability; saving the same key again doesn't fix it.
- **401/403:** check the key and permissions.

ChatGPT subscriptions and OpenAI API billing are separate. Ori currently uses Ollama or Gemini, not your ChatGPT subscription.

## Using it while playing

Start Ori first and use NMS in **borderless windowed mode**. Keep an Ori browser tab open: it receives native events, submits transcribed text, and speaks replies. The HUD alone isn't a complete chat client.

| Action | Control |
| --- | --- |
| Start recording, then finish/send | Press F8 once for each action |
| Cancel recording, answer and speech | F9 |
| Capture the visible NMS window for OCR | F10 |
| Talk from the browser | Hold the microphone button, release to send |
| Clear the current profile's chat | New conversation |

Recordings have a 60-second limit. Native audio work runs outside the HUD/hotkey thread. If Windows can't register a shortcut, diagnostics reports it.

Speech input uses multilingual Whisper tiny/base on CPU/int8. Output uses available browser/Windows voices. A provider's marked internal reasoning is filtered from displayed/spoken text; this doesn't turn a thinking model into a different model.

## What Ori can read from a save

**NMS doesn't need to be running to read an existing save.** While playing, changes appear after the game writes its next save. Ori isn't reading game-process memory or looking at the screen continuously.

| Data | Current support |
| --- | --- |
| Units, Nanites, Quicksilver | Recognized save fields, when present |
| Bases | Names and available position/address data |
| Location | Last saved address, not a live position |
| Inventory | Readable entries from supported player, storage, freighter, ship and vehicle inventories |
| Personal goals, lore and plans | Entries you add to Ori's journal |
| Complete in-game mission book | Not imported |
| What is on screen | A user-triggered capture, followed by OCR review |

Item IDs may be untranslated. Some binary/unreadable IDs are omitted with a warning. An empty section can mean unsupported fields or no linked save; it isn't proof that the player owns nothing.

The original save is read-only. The PC reader supports bounded LZ4 save blocks and a pinned key map. Human-readable JSON imports are also supported. An optional external libNOM CLI receives a temporary copy.

Link a save to the right profile. The watcher checks linked files every four seconds and waits for writes to stabilize. Source and timestamp stay visible.

## Exact save facts and AI answers

I found a practical problem during testing: a small model could receive the correct data and still confuse currency balances with inventory counts or invent a base's purpose from its name.

**Conversation always goes to the selected AI**, including questions about my save. The app supplies verified save context and shows a separate, collapsed **Verified save facts** reference beneath the reply. I can open it to compare the model's interpretation with the exact snapshot values. The card isn't an AI answer and doesn't replace conversation.

The reference and the AI context use the same captured snapshot. Currency balances and totals are presented clearly to the model; container counts and coordinates are included when relevant to the question. A standalone, non-AI report remains available only for clients that explicitly send `response_mode: "facts"`.

General conversation still uses the selected LLM. It can misunderstand, hallucinate, or invent details. Prompt instructions reduce that risk but don't guarantee correctness. A base name alone doesn't prove there is a factory, research facility, resource deposit or mission there.

The context supplied to AI includes selected journal entries, open goals, recent conversation and a structured save summary. It doesn't include every inventory slot or every past conversation in each request. Exact item lookup currently uses text/ID matching, not a game-wide item-name or recipe database.

## Memory, identity and the journal

Profiles keep separate conversations, fixed memories, journal entries and snapshots.

The local Ori **doesn't inherit my ChatGPT memory**, emails, browser history or personal background. To make it remember something, add a memory or record it explicitly:

> Ori, remember my name is David.

> Ori, record goal: build an observatory near my main base.

> Ori, record lore: this settlement is the capital of my exploration network.

> Based on my recorded goals, what could I work on next? Separate facts from ideas.

The journal also supports reviewed observations and generated session summaries. Lore is fiction supplied by the user; generated summaries are labeled.

**New conversation** clears messages for the current profile and cancels the active response. Saved memories, journal entries and linked-save data remain. You can delete journal entries separately or export them as JSON.

## Captures and OCR

F10 captures the desktop region occupied by a visible NMS window. Keep the game unobscured. You can also upload an image.

OCR tries Windows OCR, then RapidOCR on CPU. Review names and numbers before confirming. A capture only becomes journal context after confirmation. Discarded captures remain local until manually removed.

## How it works technically

1. The browser sends typed text or a short microphone recording to Flask on `127.0.0.1:8765`.
2. Whisper transcribes audio locally. Typed messages skip this step.
3. SQLite supplies data for the selected profile. The read-only save adapter maintains historical snapshots.
4. Normal chat goes to Ollama or consented Gemini with verified context; a separate reference card shows exact save facts. Only an explicit facts-mode request skips AI.
5. Responses use NDJSON streaming. The browser displays text and queues completed sentences for speech.
6. A native Windows service handles global shortcuts, bounded recording and the optional Tk subtitle HUD.

There is no autonomous web search, game control or continuous vision in this version.

| Code | Responsibility |
| --- | --- |
| `companion/app.py` | Local API and response lifecycle |
| `companion/grounding.py` | Direct save reports and request classification |
| `companion/providers.py` | Provider adapters and cancellable streaming |
| `companion/memory.py` | SQLite, profiles and context retrieval |
| `companion/game.py`, `save_reader.py` | Read-only saves, normalization and watching |
| `companion/desktop.py`, `capture.py` | HUD, shortcuts, microphone and reviewed OCR |
| `static/`, `templates/` | Browser UI and EN/PT localization |
| `launch.py` | Dependency setup and single-instance launch |

## Data and troubleshooting

The launcher normally keeps private data in **.runtime/userdata**. `NMS_COMPANION_RUNTIME` changes the runtime folder; `NMS_COMPANION_DATA` changes the app's data folder.

SQLite, settings, models, captures, audio, logs, dumps and credentials are excluded from source commits. Logs under **logs/orion.log** rotate; **fault.log** records low-level failures when available. App logs deliberately omit prompts and keys.

Ollama/Gemini receive the selected text context. Whisper and OCR run locally; raw audio and screenshots aren't sent to Gemini. Cloud processing still sends the selected text to Google.

Start Ollama before chatting. With Docker, start Docker Desktop and the existing Ollama container; an online Docker engine alone doesn't mean Ollama is listening. A refused connection means no service accepted that address/port. A connection closed during model loading is reported separately.

A connection timeout doesn't prove Ollama is offline. Cold loading and long prompts can take time. Check the server, model and timeout before retrying.

An NMS crash was reported during testing. The dump found was empty, so its cause remains unconfirmed. The app now has better cancellation, bounded work, duplicate-instance protection and resource logs. These changes don't establish stable FPS or prove a driver/game crash is fixed.

## Development and verification

After the launcher has installed dependencies:

```powershell
New-Item -ItemType Directory -Force .tmp, .test-data | Out-Null
$env:PYTHONPATH = (Join-Path (Get-Location) '.packages') + ';' + (Join-Path (Get-Location) 'tests')
$env:NMS_COMPANION_DATA = Join-Path (Get-Location) '.test-data'
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
python -m unittest discover -s tests -v
```

Use `.runtime/packages` instead of `.packages` if that's where your launcher installed them. Always use test data, not the real journal.

The checks cover parsing, profile isolation, model settings, streaming/cancellation, direct save facts, memory, journal and launcher behavior. Browser tests use a fake provider. Real Ollama tests confirmed connectivity and also reproduced incorrect factual answers from Liquid.

A full session alongside NMS, physical microphone quality, native shortcut behavior and FPS still need normal desktop/game testing. See [test details](docs/TESTING.md), [troubleshooting](docs/TROUBLESHOOTING.md), [architecture](docs/ARCHITECTURE.md), [privacy](docs/PRIVACY.md) and [changes](CHANGELOG.md).

## Project status

I want Ori to become a useful exploration companion step by step. Better item names/recipes, stronger retrieval and more reliable voice/game testing are next possibilities. A native follower inside NMS is still research, not an implemented feature.

No general project license has been chosen yet. Dependency/model licenses remain separate. This is an unofficial fan project, with no affiliation to Hello Games.
