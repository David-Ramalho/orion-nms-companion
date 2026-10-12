# Orion (Ori) — No Man's Sky AI Companion

Orion is a local-first desktop companion prototype inspired by the idea of a voiced, persistent sci-fi companion. It speaks as an **external exosuit persona** while you play No Man's Sky (NMS). The current prototype is a browser-based window on your PC, not a mod that adds a body to the game.

It is designed to show every answer as text as soon as AI output arrives, while speech begins sentence by sentence. You can use push-to-talk or type, select Ollama or Gemini, stop speech, change the voice speed, and keep conversation history and mission notes between launches.

> **Prototype status:** Eight automated tests pass. I could not verify your live microphone, your Ollama service, or a live Gemini request from this environment. See [Testing and verification](docs/TESTING.md) for what has and has not been exercised.

## Find and launch the project

Clone or download this repository, then double-click **`start.bat`** on Windows. A console window runs the app and your default browser should open Orion at `http://127.0.0.1:8765`. Keep the console window open while using Orion. When you are done, close the browser and press **Ctrl+C** in the console. The app's runtime and private data are kept outside the repository by default.

If Windows asks for permission to use the microphone, allow it. Orion’s first launch creates a private Python environment and installs the packages listed in `requirements.txt`. This needs internet access. The first push-to-talk transcription downloads the selected speech model; that download also needs internet, but audio transcription then runs locally on your PC.

### Keep runtime and data on D: (optional)

To put the Python environment, settings, speech model, and SQLite data on another drive, set the runtime location before starting. Open PowerShell in the project folder and run:

```powershell
$env:NMS_COMPANION_RUNTIME = 'D:\NMS-Exosuit-Companion-runtime'
.\start.bat
```

That puts the Python environment, settings, speech model, and SQLite data under the selected folder. The project source remains in its checkout. The first launch downloads Python packages. Orion only needs Ollama's API to be available at the configured local address.

## First conversation: step by step

1. **Start Orion** with `start.bat` and wait for the browser page to load.
2. **Choose an AI provider** in the right-hand **AI systems** panel:
   - **Automatic · local first** checks Ollama first. It only falls back to Gemini if you enable the fallback and accept the cloud notice.
   - **Ollama only** keeps prompts on your PC, provided your Ollama service is available.
   - **Gemini only** sends the conversation to Google's API. You must configure your key and accept the cloud notice first.
3. **For Gemini**, tick **I accept Gemini cloud processing**, press **Save connection settings**, and confirm the notice. Paste your Gemini key into the key field and press **Save**. The key is stored using Windows Credential Manager when available; don't paste it into chat or put it into a project file. Select **Gemini only** and save settings. The app does not verify that your Google project is free of billing; review its billing and limits before using it. Google's free-tier data handling may include product improvement and human review. See [Privacy and data flows](docs/PRIVACY.md).
4. **For Ollama**, start Docker Desktop/Ollama, then check that the connection panel says Ollama is online. Select an installed model from the model list. The prototype defaults to `http://127.0.0.1:11434`, which you can change in the settings panel. It does not assume that a model is installed.
5. **Test typed chat first.** Type a short message in the bottom text box and press Enter or **Send**. You should see subtitle text arrive before the complete response has been generated.
6. **Test voice input.** Hold the round microphone button, speak in English, then release it. Orion transcribes after release and sends the recognized text to the selected provider. First use downloads the local Whisper model: `base.en` is the balanced option (about 150 MB); `tiny.en` is smaller and faster (about 75 MB). Actual download size can vary.
7. **Test spoken output.** Orion starts speaking when it receives a full sentence or finishes a short reply. Choose an installed voice and adjust **Speaking speed** in the **Voice & Text** panel. Text stays visible even if speech is slow or unavailable.
8. **Try cancellation and memory.** Press **Stop voice** during a reply. Add a mission note under **Mission notes**, then restart Orion and confirm that the note and conversation history remain.

## Playing No Man's Sky while using Orion

1. Start Orion first, then launch NMS.
2. Use NMS **borderless/windowed mode**, or put the Orion browser on a second monitor. Orion is not currently an always-on-top overlay.
3. With one monitor, use **Alt+Tab** between NMS and Orion. Click and hold the mic button while speaking; releasing the button submits the transcript. You can also type a question while Orion is visible.
4. For this prototype, tell Orion what you see or discovered. It does not yet capture screenshots, read the NMS save, detect game events, or control the game. It currently knows only what you say/type and the mission notes you save; in-character comments are roleplay, not live game telemetry.

There is no global push-to-talk key yet, and the current browser window may not stay visible over exclusive fullscreen NMS. A native in-game companion body has not been demonstrated; the exosuit persona is the working fallback.

## What is included

- **Interface:** local browser-based subtitle/chat panel and connection controls.
- **Speech input:** push-to-talk recording in the browser; English transcription with `faster-whisper` on CPU/int8.
- **Speech output:** installed browser/Windows voices with adjustable speed.
- **AI:** streaming Ollama and Gemini adapters; easy Automatic, Ollama-only, and Gemini-only modes.
- **Memory:** SQLite conversation history and user-authored mission notes. Recent messages and notes are provided as context to the AI.
- **Personality:** editable system prompt for Orion's voice and behavior.
- **Local files:** settings and memory live under `%LOCALAPPDATA%\NMS-Exosuit-Companion`, unless you set `NMS_COMPANION_RUNTIME` to place them on another drive.

## Technical overview: what happens during a conversation

1. The browser records audio only while push-to-talk is held. After release, it sends the recording to the local Flask app.
2. `faster-whisper` transcribes the recording on the PC. Typed text skips this step. The transcript is never sent to Gemini as audio.
3. The app loads recent conversation turns and saved mission notes from SQLite, then sends that text to the selected AI provider. Automatic mode tries Ollama first; Gemini fallback requires explicit opt-in. Gemini receives the prompt, persona, and selected notes.
4. Provider output streams back in small text fragments. The page adds subtitles as fragments arrive and queues completed sentences for the browser's installed speech voice. Stopping cancels the active response and speech playback.
5. Conversation turns and manually saved notes persist locally. There is no vector database or automatic fact extraction yet.

The Python server is Flask and listens only on `127.0.0.1:8765`. The UI is HTML/CSS/JavaScript. `companion/providers.py` isolates Ollama and Gemini APIs; `companion/memory.py` owns SQLite storage; `companion/config.py` handles defaults and local settings. See [Architecture](docs/ARCHITECTURE.md) for the data-flow diagram and design decisions.

## Future direction

The roadmap is staged so game awareness can be added without pretending the current persona sees the game. The next likely step is a user-triggered screenshot/OCR scan with a preview and clear source labels, then investigation of safe, read-only save parsing. A compact overlay and global push-to-talk can follow if they work reliably in borderless NMS. A native in-game follower is an experiment, not a promised feature. See [Roadmap](docs/ROADMAP.md).

## What is not included yet

- A character, pet, or follower spawned or controlled inside NMS.
- Screenshot capture, OCR, save-file parsing, discovery tracking, or automatic game awareness.
- Global hotkeys, always-on-top game overlay, or game input/control commands.
- Automatic long-term fact extraction or semantic/vector search; add important facts yourself as mission notes.
- Verified live latency, memory use, or performance while NMS is running on your PC.

See [Roadmap](docs/ROADMAP.md) for the planned steps and [Architecture](docs/ARCHITECTURE.md) for integration options and design choices.

## Troubleshooting

### Orion does not answer

- Check the status lights in **AI systems**.
- If using **Ollama only**, start the Ollama service and select an installed model.
- If using **Automatic**, Ollama is tried first. If it is offline, enable the Gemini fallback and accept cloud processing—or choose Gemini manually.
- If using **Gemini**, confirm the key is saved, the model is available to your API project, your quota is available, and the cloud notice is accepted. Read the error text shown in the conversation.

### Microphone button does nothing

- Use current Chrome or Edge and grant microphone access to `http://127.0.0.1:8765`.
- Check the Windows microphone privacy setting and selected input device.
- Hold the button while speaking and release it to submit. The prototype does not continuously listen.
- The first transcription can take longer because it downloads and initializes the speech model. If download fails, check internet access and try again.

### I don't hear speech

- Check Windows volume and the browser's audio output device.
- Choose another installed voice from the **Voice** menu.
- Speech waits for punctuation or the end of a short response; subtitles stream as text arrives.

### Ollama is offline

The app does not control Docker. Start Docker Desktop and the existing Ollama container/service on D:, then confirm its API is reachable at the address configured in Orion. You do not need to move Docker's data back to C: if the service can still expose its local API.

### Dependency installation fails

- Confirm Python 3.12 is installed and available as `python` in PowerShell.
- Confirm internet access and enough space on the drive used by `NMS_COMPANION_RUNTIME`.
- Close the app and run `start.bat` again. Do not delete the project source; the `.venv` directory is only the installed runtime and can be recreated.

## Project layout

```text
companion/       Flask app, settings, providers, and SQLite memory
static/          Browser behavior and styling
templates/       Companion page
tests/           Automated tests
docs/            Architecture, decisions, privacy, roadmap, licenses, tests
requirements.txt Pinned direct Python dependencies
run.ps1          Setup and launch script
start.bat        Double-click Windows launcher
```

## Tests

From this folder, run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The automated suite includes checks for the local page, SQLite persistence, provider-stream parsing, opt-in behavior, streamed chat, and the audio decoder compatibility fix. These use mocked AI streams; they do **not** prove that your live Gemini key, Ollama model, microphone, voice, or NMS session works. The current test record is in [Testing and verification](docs/TESTING.md).

## Preparing for a future GitHub upload

This is an early prototype. Before reusing or redistributing it:

1. Review every file and remove local test data, credentials, logs, and any personal conversation/memory database. `.gitignore` excludes virtual environments, databases, downloaded models, temporary files, and local test data, but inspect the staged changes yourself.
2. Never include your Gemini key. Keep it in Windows Credential Manager or an environment variable.
3. Do not include Whisper model weights or Ollama models; let each user download their own.
4. Choose a project license before publishing. Review the licenses for direct and transitive packages and downloaded models; see [Dependencies and licenses](docs/LICENSES.md). NMS and any third-party game assets remain owned by their respective rights holders.
5. Update the testing record with real hardware/provider results, and explain which features remain experimental.
6. Review the entire public repository and its visibility before sharing forks or releases.

## Documentation index

- [Architecture and integration options](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture decision records](docs/DECISIONS.md)
- [Privacy and data flows](docs/PRIVACY.md)
- [Testing and verification](docs/TESTING.md)
- [Dependencies and licenses](docs/LICENSES.md)

## Safety and scope

Orion is informational only. It does not send commands to NMS, change game files, or write NMS saves. The local web server binds to `127.0.0.1`; do not expose it to your network. This is an unofficial fan-made prototype and is not affiliated with Hello Games.

## License

No project license has been selected yet. Until one is added, the source is publicly viewable but standard copyright rules apply; third-party dependency and model licenses remain separate.

