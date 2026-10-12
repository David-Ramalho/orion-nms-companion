# Testing and verification log

## Environment research

- Development and automated checks were run on Windows with Python 3.12.
- The Ollama endpoint was unavailable during the test session; no live local-model request was made.
- No live Gemini request was made. Provider behavior is covered with mocked response streams only.
- Live browser, microphone, speech output, and in-game behavior remain user-side validation items.

## Milestone verification

| Check | Result | Evidence / next step |
|---|---|---|
| Python syntax | Passed | `python -m compileall -q companion tests`. |
| Flask route and memory tests | Passed | `.venv\Scripts\python.exe -m unittest discover -s tests -v`: 8 tests pass, including local page, persisted memory, Gemini consent gate, and uploaded WAV decoding. |
| Streaming provider adapters | Passed with mocks | Ollama NDJSON and Gemini SSE parsing/key header tested using fixture streams; no live service request made. |
| Runtime imports | Passed | Installed `Flask 3.1.3`, `faster-whisper 1.2.1`, `av 18.1.0`, and `keyring 25.7.0`; imports succeeded. The required Whisper model weights are not downloaded yet. |
| Speech decoder compatibility | Passed | Reproduced the reported `metadata_errors` failure with PyAV 19.0.1, pinned `av<19`, installed PyAV 18.1.0, and confirmed the faster-whisper WAV decoder test passes. |
| Mic / local Whisper | Pending | Requires browser permission and model download on the user's PC. |
| Subtitle and spoken overlap | Pending | Requires opening UI in Chrome/Edge with an available system voice. |
| Ollama | Not available at research time | Start existing local Ollama service/container on D: and select an installed model. |
| Gemini | Not tested | User adds own key in app. No key should be pasted into chat or committed. |
| Live loopback HTTP probe | Blocked in sandbox | Server started and printed its loopback URL, but a separate sandbox HTTP client could not reach the server. Flask test-client route tests pass; user launch remains needed for browser/mic validation. |
| NMS in-game behavior | Not implemented | External exosuit UI only; no screenshot/OCR, save parsing, event detection, overlay, native body, or following. Native body/following remains unverified. |

Update this table with actual outcomes; never mark machine-dependent behavior as passing from mocks alone.
