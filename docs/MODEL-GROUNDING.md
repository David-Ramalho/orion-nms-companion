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

Explicit save overviews, balances and counts now use a deterministic report assembled from the selected profile's snapshot. The response is labeled **Save reader**, with no claimed Ollama/Gemini generation.

It works when the provider is offline. Missing fields are marked unknown. Readable inventory counts remain explicitly partial. Optional activities in this route are conservative app suggestions and do not assert facilities, production or missions.

General strategy and conversation stay with the user's chosen model. This includes questions about spending resources. They remain subject to model errors; the deterministic route is intentionally limited to recognizable reporting requests.

The general prompt clarifies that local Ori has no inherited ChatGPT memory and should ask about unknown identities. This is a behavioral instruction, not an identity-validation guarantee. The user should record personal information intentionally in the local profile.

## Useful comparison

For factual tests, use the same linked save and a new conversation. Ask for balances/counts, then compare with the snapshot. Check the source badge: a direct report tests the reader, while normal model conversation tests generation. Keep suggestions separate from saved facts.

A larger context window increases input capacity. It does not guarantee correct extraction or reasoning.
