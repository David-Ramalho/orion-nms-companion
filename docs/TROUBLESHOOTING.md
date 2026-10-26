# Diagnóstico de estabilidade e conexão

## Travamento relatado em 24 de outubro de 2026

Foi encontrado um arquivo de crash do NMS com **zero bytes**, modificado às **20h55 no horário de São Paulo**. O nome menciona a camada Steam Vulkan Fossilize, mas um nome de arquivo não identifica a causa. Sem conteúdo, o dump não fornece stack, código de falha ou uso de memória.

O acesso ao log de eventos do Windows e aos logs do Docker foi negado neste ambiente de diagnóstico. O aplicativo não tinha um log persistente próprio que permitisse reconstruir o instante do travamento. A partir desta atualização, os registros ficam em logs/orion.log e logs/fault.log, dentro da pasta de dados do aplicativo. Eles não contêm deliberadamente prompts, chaves ou notas; reveja-os antes de compartilhar.

**Conclusão:** a causa permanece indeterminada. Não foi demonstrado que Ori causou o crash, nem que reduzir contexto resolveria o problema. Não foram alterados drivers, configurações gráficas, arquivos do Steam ou saves.

A correção desta atualização cobre riscos encontrados no aplicativo: operações de áudio que podiam bloquear callbacks, concorrência de captura/transcrição, resultados antigos após cancelamento, instâncias duplicadas e falta de diagnóstico persistente. Isso não substitui uma reprodução com o jogo aberto.

## Ollama: servidor disponível e modelo pronto são estados diferentes

A lista de modelos usa a API de catálogo do servidor. Uma resposta de catálogo confirma conectividade naquele instante, mas o modelo ainda pode precisar carregar pesos, alocar contexto ou esperar outra inferência.

1. Confirme o endereço na interface e salve.
2. Confira `ollama list` e `ollama ps` no terminal da sua instalação.
3. Se usa Docker, confirme que o contêiner está ativo e a porta 11434 está publicada para o Windows.
4. Escolha um modelo instalado e espere um único pedido completar.
5. Confira os controles de tempo de espera, contexto e geração. Um timeout curto pode interromper carregamentos válidos.
6. Teste uma pergunta curta antes de enviar um resumo extenso do save.
7. Registre horário, modelo, valores configurados e mensagem de erro, sem incluir chave ou prompt privado.

Um teste controlado desta atualização confirmou o Ollama online e resposta final do Liquid com contexto 32768. O primeiro carregamento levou cerca de 17 segundos até a saída inicial; uma pergunta genérica posterior retornou OK em cerca de 4,8 segundos. Isso demonstra que uma espera curta pode falhar mesmo com o servidor disponível, mas não determina a duração nem a causa exata das tentativas anteriores do usuário.

O contexto de 32k continua disponível. Memória e velocidade variam com o modelo e a configuração; metadados não garantem a quantidade de RAM/VRAM usada durante uma conversa. Não reduza parâmetros automaticamente só porque o modelo tem uma janela grande.

A indicação de erro do app é limitada à solicitação observada. Se o tempo de espera terminar, não conclua que o serviço está desligado permanentemente.

## Teste controlado junto ao jogo

1. Reinicie a sessão após um travamento e abra uma única instância do Orion.
2. Confirme uma conversa com o provedor escolhido antes de abrir o jogo.
3. Abra NMS em janela sem bordas e carregue o save normalmente.
4. Teste primeiro texto/voz; depois F8/F9 e, por último, uma captura F10.
5. Observe RAM/VRAM e FPS com suas ferramentas habituais. Registre o horário se ocorrer uma falha.
6. Reúna o novo registro local do Orion e, na sessão normal do Windows, os eventos de aplicação próximos do horário.
7. Revise qualquer log antes de compartilhar. Dumps e exports pessoais não devem entrar no repositório.

Se houver travamento mesmo com Ori fechado, essa observação é útil para a investigação. Se acontecer somente com determinada combinação de modelo, contexto e jogo, registre a combinação em vez de trocar várias opções ao mesmo tempo.

## Quando objetivos ou o livro aparecem vazios

O save pode ser lido com o jogo fechado. O conteúdo corresponde ao último salvamento, e não a uma transmissão ao vivo.

O leitor atual reconhece moedas, tempo jogado, endereço salvo, inventários e bases. Ele ainda não importa fauna, o diário de missões do jogo nem temporizadores ativos das expedições de fragatas. Use o diário do Ori para registrar manualmente descobertas, projetos e horários de retorno. Entradas guardadas nesse diário continuam disponíveis em novas conversas do mesmo personagem; Nova conversa limpa o histórico, não o diário.

## Gemini 503 e assinatura ChatGPT

503 indica indisponibilidade temporária do serviço Gemini; não é um diagnóstico de chave inválida. Não há repetição automática ilimitada. Aguarde ou escolha um modelo listado para sua chave.

A assinatura do ChatGPT e a API da OpenAI têm cobrança separada. Orion utiliza Ollama ou Gemini e não usa os créditos de uma assinatura ChatGPT.

## Erro de memória ao enviar uma gravação F8 com NMS aberto

O F8 grava até 60 segundos no modo normal e envia o áudio para o Whisper `tiny` por meio do faster-whisper/CTranslate2, em CPU/int8. O erro `mkl_malloc: failed to allocate memory` logo depois do segundo F8 indica que uma biblioteca nativa não conseguiu reservar memória. O momento sugere a transcrição local; os logs não registram a mensagem nativa e não provam o ponto exato da falha.

Ative **NMS aberto · modo econômico** em Sistemas de IA. Ele limita F8 e o microfone do navegador a 20 segundos, usa uma thread na transcrição, envia contexto 4k e até 192 tokens ao Ollama, começa com GPU em `0` (somente CPU) e descarrega o modelo depois da resposta. Todos os parâmetros continuam editáveis; o perfil normal de 32k fica salvo separadamente. Digitar continua disponível se a memória ficar apertada.

O faster-whisper usa CTranslate2 e oferece modo int8 para CPU; a transcrição ainda precisa de memória temporária. Veja as [orientações de desempenho do CTranslate2](https://opennmt.net/CTranslate2/performance.html) e os [detalhes de memória do faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## MKL allocation during F8 with NMS open

Normal mode records up to 60 seconds and transcribes with local Whisper `tiny` through faster-whisper/CTranslate2 on CPU/int8. `mkl_malloc: failed to allocate memory` means a native library could not reserve memory. Its timing points to local transcription, but Ori's logs do not capture the native message or prove the exact failing call.

Enable **NMS open · low-resource mode** under AI systems. Its separate profile starts with CPU-only Ollama placement, 4k context, up to 192 output tokens, 20-second F8/browser recordings and one CPU thread for Whisper, then unloads Ollama after each answer. All model controls stay editable. GPU layers `0` requests CPU only, `-1` automatic placement, and a positive number requests that many model layers on the GPU, up to the full model. CPU avoids VRAM pressure but may compete for system RAM/CPU; automatic placement can still fail while NMS is using VRAM. Your normal 32k profile remains separate. Typed chat is available if transcription runs out of memory.

faster-whisper uses CTranslate2 and supports CPU int8; transcription still needs temporary working memory. See [CTranslate2 performance tips](https://opennmt.net/CTranslate2/performance.html) and [faster-whisper memory details](https://github.com/SYSTRAN/faster-whisper).

## AI conversation and GPU-memory failures

Normal chat always uses the chosen AI, even for save questions. The Verified save facts card is a separate reference; it does not replace the model response. Start Ollama or the existing Docker container before chatting. Refused connections, interrupted runners and GPU-memory errors are reported separately.

The current 1.2B model failing to load with NMS open does not mean it can never use the GTX 1650. NMS and Ollama share the card's VRAM, and automatic placement may request more than remains free. Try the NMS profile's CPU-only choice first; if it is too slow, try a small positive GPU-layer value and increase gradually. CPU inference uses the same system RAM and CPU as the game, so it is not guaranteed to be smoother. The standard profile is stored separately.
