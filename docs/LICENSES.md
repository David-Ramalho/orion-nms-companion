# Dependencies and license notes

## Direct Python dependencies

| Package | Version pinned | License / note |
|---|---:|---|
| Flask | 3.1.3 | BSD-3-Clause; local HTTP UI |
| faster-whisper | 1.2.1 | MIT; downloads model weights on first transcription |
| keyring | 25.7.0 | MIT; credential storage interface, backend behavior depends on Windows environment |

Dependencies also install transitive packages; review their licenses before redistribution. No dependency is bundled into a release artifact yet. Model weights have their own upstream terms and are downloaded at runtime; check the chosen model's license before redistribution.

## Existing NMS projects reviewed

- [WingmanAI NMS profile](https://github.com/teddybear082/wingmanai-nomanssky): the public profile repository reports MIT; its README currently describes WingmanAI installation, a free account/trial, local model/STT alternatives, and an NMS Assistant API integration. Treat profile/config compatibility as unverified until tested with the current Wingman release. Referenced xVASynth voice files have their own provenance/license concerns and are not included here.
- [WingmanAI](https://github.com/ShipBit/wingman-ai): candidate for reuse or later migration; this prototype does not copy its code. Audit current license and architecture before adapting any code.
- [NMS Companion](https://github.com/Delwing/nms-companion): public README describes offline save cataloguing and screenshot OCR. Its current repository licensing was not verified in this research snapshot, so use as a capability reference only and do not copy implementation.
- No Man's Sky, its assets, names, and trademarks belong to their respective owners. This is an unofficial fan-made prototype and is not affiliated with Hello Games.

## References

- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Gemini API reference](https://ai.google.dev/api)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini API additional terms](https://ai.google.dev/gemini-api/terms)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [Flask documentation](https://flask.palletsprojects.com/)
