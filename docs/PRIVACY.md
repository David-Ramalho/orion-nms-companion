# Privacy and data flows

## Local by default

- Flask listens on loopback (`127.0.0.1`) only.
- Audio captured in the browser is posted to the local Flask server and transcribed by local `faster-whisper` after its model is downloaded.
- Browser speech synthesis runs through installed browser/Windows voices.
- Settings, history, and notes stay under `%LOCALAPPDATA%\NMS-Exosuit-Companion`.
- The Gemini key is stored via Windows Credential Manager if available. It is not included in SQLite or the project files.

## Cloud behavior

- Pinned Gemini mode sends conversation messages and the configured persona/system prompt to Google's Gemini API. The app adds saved mission notes and up to 16 recent messages as context.
- Automatic mode sends those same text fields only after the explicit cloud fallback toggle is saved and Ollama is unreachable.
- The prototype does not send microphone audio to Gemini.
- The API key is sent in the `x-goog-api-key` HTTP header.
- Google's terms, account tier, region, quotas, retention, and billing are controlled by Google and the user's account and can change. The app cannot enforce project billing, free-tier availability, or spending limits. Review Google's current terms and pricing before enabling cloud use.
- The app does not use Google Fonts or other remote assets in its UI.

See [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) and [Gemini API additional terms](https://ai.google.dev/gemini-api/terms) for current conditions; these can change.

## Controls and limitations

- Leave Gemini unconfigured and use Ollama-only to keep prompt text local.
- Clear conversation history from the UI; this does not clear mission notes. Notes are not currently removable individually from the UI.
- This is a prototype local server without authentication or hardened CSRF defense. Keep it on loopback and do not port-forward it or expose it on a network.
- Diagnostic errors may include provider error text. Do not share logs/screenshots containing API keys or sensitive mission notes.
