# Verification — 25 October 2026

Environment: Windows, Python 3.12, Chrome/Playwright. **103 automated tests pass** in the final integrated suite.

## What the tests cover

- Read-only save decoding, size bounds, unmapped fields, stable file reads and snapshot deduplication.
- Profile isolation across chat, fixed memories, journal, exports and save data.
- Config validation, atomic saves and independent model settings, including 32768 context.
- Ollama/Gemini stream parsing, consent boundaries, provider errors and resource cleanup.
- Cancellation while a local HTTP server is waiting to send headers.
- Clearing a conversation while streaming, without restoring an old reply.
- Default save questions invoke the selected AI with exact context and a separately attributed reference card.
- Explicit facts mode, missing-data handling and source attribution without a provider or credentials.
- Same-snapshot consistency between the model prompt and reference, including during watcher updates.
- GPU offload settings, explicit CPU mode, context preservation and distinct refused/reset/GPU-memory errors.
- EN/PT report detection and advice questions remaining on the normal model path.
- Bounded desktop audio/capture work, stale-result rejection and launcher protection.
- Audio decoding with synthetic silence; this does not test real speech comprehension.

New grounding tests use fictional currencies, counts and base names. Private saves, transcripts and diagnostic captures are excluded from Git.

## Browser verification

The integrated smoke test passes with no JavaScript page errors and no horizontal overflow at 390 px.

It covers journal creation/search, fake-provider streaming, reload persistence, profile isolation, reviewed OCR, model-specific parameters, clearing during a stream, a save import and AI-routed response with a verified reference, provider-error reference retention, GPU-layer persistence, and EN/PT switching.

The locale test checks that drafts, the chosen model and speech-recognition language survive a UI-language change; the language preference survives reload. User-authored journal text stays unchanged.

## Native and real-data checks

- A real PC save was read and its source hash stayed unchanged. Supported currency, base, address and readable inventory data were extracted. The original and its identifiers are not committed.
- RapidOCR recognized a synthetic English test image. Windows OCR was unavailable in the restricted environment.
- Multilingual Whisper tiny loaded on CPU/int8; synthetic silence produced no transcript.
- The launcher and local endpoints started with existing user data. Log files were created.

## Real model observations

Ollama responded to catalog/metadata requests. Liquid32k produced a generic visible answer with a 32768 context request. A cold load took about 17 seconds to first output; a warm generic response took about 4.8 seconds. These are observations, not performance guarantees.

A later grounding check sent correct save facts to Liquid 1.2B Instruct at temperature 0.1. It miscopied a balance in a short prompt and mixed balances with container counts in a larger prompt without conversation history. This demonstrates a generation/grounding failure in that tested setup; a unit-test pass does not establish LLM answer accuracy.

A raw-template comparison could not complete because the local Ollama service subsequently refused connections. The tests do not isolate model weights, quantization, runtime and template behavior from each other. See [the diagnosis](MODEL-GROUNDING.md).

Default save conversation now uses AI, with exact parsed values in a separate reference card. Explicit facts mode alone bypasses model generation. General chat can still hallucinate. No live Gemini success is claimed.

A later real AI request selected lfm2.5:8b at 32768 context. Ollama returned HTTP 500 with cudaMalloc failed: out of memory. A CPU-only attempt at the same context disconnected during loading; it did not establish a working CPU configuration. The selected model and saved user parameters were not silently changed. Docker engine/container availability was also a separate cause of refused connections.

## Still needs normal desktop testing

- Physical microphone quality in English/Portuguese and browser voice output.
- F8/F9/F10 registration and capture/HUD behavior in a normal Windows session.
- A sustained NMS session with FPS, frametime and RAM/VRAM observations.
- Real-provider behavior with long conversations, different models and game load.

The empty NMS crash dump did not identify the crash cause.

## Run locally

```powershell
New-Item -ItemType Directory -Force .tmp, .test-data | Out-Null
$env:PYTHONPATH = (Join-Path (Get-Location) '.packages') + ';' + (Join-Path (Get-Location) 'tests')
$env:NMS_COMPANION_DATA = Join-Path (Get-Location) '.test-data'
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
python -m unittest discover -s tests -v
```

Replace `.packages` with `.runtime/packages` when appropriate. Keep real user data out of test runs.

For browser QA, start `python tests/qa_server.py`, then run `node tests/browser_smoke.cjs` with Playwright installed. `ORION_PLAYWRIGHT` can point at an existing installation; Chrome's path can be set through `CHROME_PATH`.

The browser fixture uses a fake provider and synthetic save data. Its OCR upload is generated by `tests/native_smoke.py` in the local test folder; it is not a committed game screenshot.

A later Granite 3B request timed out while the backend was unresponsive after the failed large-model attempts. It is not recorded as a successful live-model benchmark. The latest full browser check passed with mocked provider output, separate verified facts, retained references on errors, EN/PT changes, GPU-layer persistence and no horizontal overflow at 390 px.
