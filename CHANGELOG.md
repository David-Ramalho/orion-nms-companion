# Mudanças

## Local NMS profile, curated memories and timed journal — local build

- Keep the Liquid 1.2B model and its normal 32k per-model settings.
- Add an optional NMS mode with a separately saved profile: 4k context, 192 output tokens, CPU-only by default and unload-after-reply. All Ollama controls remain editable; GPU placement can be automatic, CPU-only or a positive layer count.
- Cap F8 and browser-microphone recordings at 20 seconds and use one CPU thread for local tiny Whisper while the mode is active.
- Release any currently loaded Ollama model when the mode is first enabled; report memory-allocation failures in plain language.
- Add editable chat excerpts and reviewed session summaries with existing/new categories, including Projects, Stories and Frigate expeditions; add manual due dates that remain available to Ori in later conversations for the same character.
- Document save-reader gaps: fauna, the in-game mission log and active frigate timers are not imported.
- No additional model or speech-model download is required.

## AI conversation and connection recovery

- All normal chat, including save questions, uses the chosen AI again.
- Exact save facts appear as a separate collapsed reference, including on provider failures.
- Fixed reader reports require explicit facts mode.
- The prompt and reference share one snapshot; ordinary chat omits irrelevant numerical details.
- Connection errors distinguish a stopped service, a network block, a disconnected runner and GPU/RAM exhaustion.
- Per-model GPU layers allow automatic placement, CPU-only and requested partial offload without changing context.
- EN/PT reference labels and error translations preserve the existing language toggle.


## Grounded reports and EN/PT interface — 25 October 2026

- Direct save reports preserve exact numbers even without Ollama/Gemini.
- Save reader source labels distinguish app reports from model-generated conversation.
- Explicit reporting stays separate from resource-spending advice.
- English/Portuguese UI toggle persists without changing speech-recognition language or drafts.
- Identity grounding explains that local Ori has no inherited ChatGPT memory.
- README rewritten in first person, with English and Portuguese setup/technical guides.
- Model-grounding diagnosis distinguishes parsed data from inaccurate generation.


## Save-context correction — 25 October 2026

- Preserve currency balances, base counts and readable inventory totals in model context.
- Select relevant base and item records without cutting JSON in the middle.
- Distinguish missing mission import, empty journal and proposed activities.
- Add four regressions for large summaries, targeted item lookup and explicit missing data.


## Atualização local — 25 de outubro de 2026

### Interface e provedores

- Controles avançados discretos para ajustar contexto e geração por modelo.
- Preservação da opção de contexto de 32k; nenhuma redução automática para 2k.
- Consulta de metadados do Ollama para auxiliar a configuração.
- Espera padrão de 180 s configurável; timeout distingue espera de carregamento de servidor inacessível.
- Cancelamento interrompe espera do Ollama antes dos headers HTTP.
- Raciocínio interno do Liquid filtrado também quando chega como tags inline.
- Identificação do provedor/modelo efetivamente usado em respostas novas.
- Limpeza da conversa com cancelamento e preservação do diário.
- Explicação da diferença entre dados do save e objetivos/lore escritos no diário.

### Estabilidade

- Trabalho de áudio separado da thread de atalhos e da interface nativa.
- Limites de áudio e filas; apenas uma transcrição/captura nativa por vez.
- Descarte de resultados antigos após cancelamento ou troca de personagem.
- Timer de gravação vinculado à sessão correta.
- Fechamento e limpeza de streams do provedor.
- Proteção do launcher contra instâncias duplicadas e porta ocupada.
- Registros locais de diagnóstico para ajudar em ocorrências futuras.

### Documentação

- README em português com instalação, uso no NMS, provedores, controles, memória e desenvolvimento.
- Investigação do travamento com limites explícitos da evidência disponível.
- Atualização dos procedimentos de validação.
- Regras de exclusão para dumps, arquivos de ambiente e mídias privadas.

Nenhum push ou deploy faz parte desta atualização.

## Protótipo anterior

- Conversa em streaming e voz do navegador.
- Ollama e Gemini com consentimento explícito de nuvem.
- Diário, objetivos e lore por personagem.
- Leitura de saves PC LZ4 e JSON; watcher e snapshots.
- Captura de tela e OCR com revisão.
- HUD de legendas e atalhos F8/F9/F10 no Windows.
