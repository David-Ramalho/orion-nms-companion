# Model or application? What was established

The user observed wrong currency values and invented details about bases and personal identity. The investigation separated stored data, outgoing context and generated answers.

## Evidence

1. The selected profile's parsed snapshot contained consistent balances, base counts and readable inventory counts.
2. The outgoing context summary contained those values correctly as valid JSON.
3. Liquid 1.2B Instruct at temperature 0.1 miscopied a numeric balance even with a short, clean fact list.
4. With the larger app context and no conversation history, it substituted container/slot counts for balances and invented base functions.
5. No personal identity had been recorded locally. Claiming an unfamiliar person was a known NMS character was unsupported.

For these requests, the wrong numbers were produced during generation, rather than being the numbers read from the snapshot. An earlier app issue could truncate context; that was fixed separately and did not eliminate the reproduced generation errors.

These checks establish a failure in the tested model/setup. They do not prove all small models behave alike or isolate weights, quantization and rendering. A planned raw-template comparison could not run after Ollama became unreachable. They also do not validate every possible save schema.

## Application change

Normal save questions go to the selected AI. The app supplies a compact, authoritative fact list and shows a separate Verified save facts reference card. Model output is not replaced by a fixed report. The card remains available if a provider request fails, so local data availability and AI connectivity can be distinguished.

Container counts, item examples and coordinates are retrieved when relevant rather than competing with currency values in every greeting or overview. The card and prompt share one captured snapshot.

A deterministic report is available only through explicit response_mode: facts. It is labeled Save reader and can work offline. It does not claim to be an AI response.

The general prompt clarifies that local Ori has no inherited ChatGPT memory and should ask about unknown identities. This is a behavioral instruction, not an identity-validation guarantee. The user should record personal information intentionally in the local profile.

## Useful comparison

For factual tests, use the same linked save and a new conversation. Ask for balances/counts, then compare with the snapshot. Check the source badge: the reference card tests stored data, while normal model conversation tests generation. Keep suggestions separate from saved facts.

A larger context window increases input capacity. It does not guarantee correct extraction or reasoning.

## Separate resource failure

The later lfm2.5:8b request reached Ollama but failed loading GPU buffers with a CUDA out-of-memory error. That is not a save-parser error or evidence that the model misunderstood a prompt: generation had not begun. The CPU-only retry disconnected, so it did not validate that fallback. Application flow tests and real model/runtime capacity tests are reported separately.
