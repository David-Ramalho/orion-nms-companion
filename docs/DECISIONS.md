# Decision log

## ADR-001 — Independent local companion window

**Decision:** Build a small local app for the prototype rather than forking WingmanAI or injecting into NMS.

**Reason:** The required differentiator is immediate subtitles with overlapping speech, provider privacy controls, easy manual/automatic selection, and persistent notes. These can be validated with a small UI before taking on a third-party app's release compatibility or the risk of game process modification. WingmanAI's NMS profile remains the fallback reference if its current version can satisfy the target UX.

**Trade-off:** The first version does not inherit WingmanAI's game commands, NMS Assistant integration, or mature game-specific profile. It also is not a native in-game mod.

## ADR-002 — Local-first with explicit Gemini fallback

**Decision:** Automatic tries Ollama first. Cloud fallback is disabled unless the user enables it and confirms the data-flow notice. Manual Gemini is also available.

**Reason:** Local inference is preferred when available. Cloud use must not happen silently. No paid API fallback is configured; provider costs and quotas are controlled by the provider account.

## ADR-003 — Local speech input, OS speech output

**Decision:** Use `faster-whisper` CPU/int8 for English transcription and browser/Windows speech synthesis for output.

**Reason:** This avoids sending microphone recordings to a cloud transcription service and avoids a second voice model competing with NMS for 4 GB VRAM. It keeps spoken output immediate and configurable. Voice quality/availability depends on installed Windows voices.

**Trade-off:** Push-to-talk transcribes after release rather than showing live partial transcription. Speech synthesis behavior varies by browser and installed voice.

## ADR-004 — SQLite, local settings, no embeddings in MVP

**Decision:** Store the conversation and curated notes in SQLite, settings in `%LOCALAPPDATA%`, and retrieve recent history plus all capped notes without vector embeddings.

**Reason:** Fewer dependencies and no added model/GPU load on the target PC. It is adequate for a short prototype conversation and small note set.

**Trade-off:** Recall quality may decline as conversation history grows; later milestone should add bounded search and explicit fact management.

## ADR-005 — No game process hooks or autonomous input

**Decision:** No injection, memory reading, save-file writing, or unconfirmed keystrokes in this prototype.

**Reason:** Current feasibility, compatibility, safety, and game update impact are unverified. Start with screenshot/OCR and read-only save parsing after explicit implementation approval of their boundaries.
