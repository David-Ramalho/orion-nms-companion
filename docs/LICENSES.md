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

## Added local integrations

- sounddevice 0.5.6: MIT. Native audio capture and PortAudio wheels carry their own notices.
- Pillow 13.0.0: HPND/PIL licensing; image processing.
- psutil 7.2.2: BSD-3-Clause; process measurements.
- rapidocr-onnxruntime 1.4.4: Apache-2.0; CPU OCR. Package models and transitive ONNX Runtime, OpenCV, NumPy, Shapely and Pyclipper retain upstream notices. Default OCR recognition primarily targets English/Chinese.
- lz4 4.4.5: BSD; bounded PC save block decompression.
- socksio 1.0.0: MIT; compatibility with SOCKS proxy environments during model downloads.
- A runtime-only keymap subset is obtained from zencq/libNOM.map (GPL-3.0), pinned Git blob 8199b7833bbdf81981159e88efe7d52ce03165ea (libMBIN version 6.11.0.1). setup-reader.py verifies the blob and records provenance. The map is external data, not part of the source checkout. Distribution of the map still needs to respect its GPL terms.
- Optional libNOM.io CLI 0.14.2: GPL-3.0. Not bundled into source. The PC reader does not require this executable.

No Wingman, Delwing or Sonorus code was copied. No general project license has been selected. Dependency/model/map licenses remain separate; process separation alone is not a license exemption.
