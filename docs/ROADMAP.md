# Roadmap

## Milestone 0 — Research and proposal: complete

- Compared an independent exosuit companion to WingmanAI's NMS profile and NMS Companion.
- Recommendation: independent small app for the fast-subtitle UX, local-first provider policy, transparent memory and a replaceable game-awareness layer; reuse public projects as references until their exact integration surface and reuse terms are audited.
- An actual body/follower remains an experiment. The first prototype speaks as the player's exosuit and runs alongside the game in a normal desktop window.

## Milestone 1 — Runnable voice vertical slice: implemented, awaiting machine validation

- [x] Push-to-talk browser audio capture and typed input
- [x] Local Whisper transcription endpoint, lazy-loaded on first use
- [x] Ollama and Gemini adapters with Automatic / pinned modes
- [x] Immediate streamed subtitles, speech synthesis by sentence, stop control
- [x] User-selectable speech rate and voice
- [x] Settings and SQLite memory scaffolding
- [x] Automated tests
- [ ] First-run installation from a clean checkout
- [ ] Confirm microphone, local model, speech output, and Gemini with user's setup

## Milestone 2 — Persistent companion quality

- Improve message reconstruction, mission-note editing/deletion, and memory retrieval.
- Add response latency telemetry and a configurable short/long response style.
- Add global hotkey only after checking compatibility with NMS key bindings and focus behavior.

## Milestone 3 — No Man's Sky awareness

- Add explicit screenshot capture + OCR with an on-screen preview and user consent.
- Investigate read-only save parsing and safe backup/path detection. Never write save files.
- Track discoveries and annotate each context item as directly observed, parsed, or inferred.
- Evaluate NMS Assistant's public data/API and current access/licensing terms before depending on it.

## Milestone 4 — Companion behavior

- Prototype an optional transparent/always-on-top desktop HUD or second-monitor companion; validate focus and fullscreen behavior with the user.
- Prototype actions as suggestions first. Any execution must be allowlisted, shown, confirmed, and cancellable.
- Assess native mod feasibility against current NMS modding tools and update cadence before attempting an in-game body. The safe interim fiction is an AI exosuit persona while an ordinary tame creature accompanies the player.

## Milestone 5 — Real setup validation and handoff

- Validate the microphone, Ollama, Gemini opt-in, persistence across restarts, and NMS running concurrently on a representative target PC.
- Record first-token and first-audio latency, CPU/GPU/RAM use, cancellation behavior, failures, and exact model versions.
- Update this roadmap and [testing log](TESTING.md). No publish/upload without explicit approval.
