# Arquitetura local

O servidor Flask escuta somente em 127.0.0.1:8765. A página usa streaming NDJSON para texto e síntese de voz do navegador. A camada de provedores mantém Ollama e Gemini separados.

O perfil local para NMS guarda opções separadas por modelo, com contexto 4k, saída 192, CPU como padrão para evitar disputa de VRAM e descarregamento após a resposta. A interface deixa os parâmetros editáveis; camadas GPU 0 = CPU, -1 = automático e positivos = número solicitado de camadas. F8 e o microfone limitam gravações a 20 segundos; Whisper tiny usa uma thread CPU.

## Contexto e memória

SQLite contém profiles, messages, facts, journal, snapshots e metrics. Histórico e todas as consultas de exploração são filtrados por perfil. Registros antigos migram para default; journal migra category e due_at sem apagar entradas. Notas de conversa são revisadas antes de gravar e podem receber categoria livre e prazo UTC. Prazos aparecem no diário e entram no contexto da próxima conversa; não são alarmes em tempo real. Nova conversa apaga messages do perfil, não fatos, diário ou save; contexto recupera notas relevantes e lembretes abertos com prazo.

Antes de cada resposta, o servidor monta persona, notas, objetivos abertos, lembretes vencidos/futuros e registros recentes/relevantes do diário do perfil. O snapshot entra como resumo estruturado: horário/origem, moedas, tempo jogado (segundos do save), contagens preservadas, nomes de bases, até oito bases relacionadas à pergunta e até 30 correspondências de inventário. O limite de texto remove registros opcionais inteiros, sem cortar JSON ou esconder totais. Termos comuns da pergunta não contam como correspondências de inventário. A ausência de objetivos e a falta de importação do livro de missões são explícitas. O prompt trata registros como dados, nunca instruções. A memória não é ilimitada: há limites de contexto e correspondência textual simples.

## Saves

O watcher verifica somente arquivos vinculados explicitamente. Faz duas amostras para debounce e valida tamanho/mtime antes/depois da leitura. PC LZ4 é descompactado em memória com limite de 64 MB. Um mapa externo versionado traduz as chaves necessárias. JSON e identificadores são validados; IDs binários ilegíveis são descartados com aviso.

O estado normalizado contém endereço, moedas disponíveis, tempo jogado, bases e inventários selecionados. SHA-256 evita snapshots/eventos duplicados. Mudanças geram observações de último save, não eventos em tempo real. libNOM CLI opcional só recebe uma cópia temporária e a operação Read.

## Captura e desktop

A captura identifica uma janela pelo título, lê sua região visível e normaliza a imagem. OCR tenta Windows WinRT e usa RapidOCR CPU como fallback. Nenhuma observação é incorporada ao contexto até confirmação. Imagens pertencem ao perfil e são servidas por IDs validados.

O módulo desktop registra F8/F9/F10 com RegisterHotKey; falhas ficam no diagnóstico. Sounddevice grava áudio mono a 16 kHz, limitado a 60 s. Um HUD Tkinter exibe legendas em janela sempre no topo. Eventos desktop têm sequência e perfil; a interface mantém um cursor para evitar reenviar transcrições.

## Rede, cancelamento e medições

Requests vindos de outra origem e hosts fora de localhost são rejeitados. Mutações usam JSON ou upload multipart. Chaves ficam no Credential Manager ou em variável de ambiente.

Uma resposta por vez é permitida. O botão/F9 cancela o cliente e sinaliza o gerador. Ollama possui um watcher de cancelamento que fecha o socket inclusive enquanto aguarda os headers de carregamento. No Gemini, a interrupção do socket começa após os headers; a espera inicial continua limitada pelo timeout. Fechar a conexão não garante interrupção imediata do processamento no servidor ou de um driver. Gemini 429 não dispara repetição automática.

Métricas registram transcrição, primeiro texto, resposta completa e memória do processo. O desempenho junto do jogo não é inferido dessas métricas.


## Atualização de estabilidade

O launcher mantém um lock de instância durante preparação e execução e recusa porta local ocupada. O áudio nativo usa um worker com fila limitada; abrir, abortar e fechar o dispositivo não ocorre na thread do HUD/atalhos. Transcrição e OCR nativos são single-flight. Épocas de sessão e IDs de gravação descartam resultados/timers antigos após cancelamento ou troca de personagem.

Logs locais com rotação e registro de falhas ficam em logs dentro da pasta de dados. O monitor de recursos registra pressão de RAM; isso não identifica automaticamente a causa de um crash do NMS.

Configuração avançada e metadados do modelo permitem controlar contexto/geração/espera. A janela de 32k é preservada como opção; não há redução obrigatória baseada só no tamanho anunciado pelo modelo.

## Exact reports and interface language

Normal chat, including save questions, uses the selected provider. The start/error event can include verified_save metadata for a separate reference card. One captured snapshot supplies both the card and model context, avoiding watcher-update races. Only explicit response_mode: facts uses an app-formatted Save reader report without provider calls. Cancellation, profile isolation and history persistence apply to both paths.

The browser i18n module translates registered UI labels and common statuses. The EN/PT preference stays in localStorage, separate from the STT setting. Chat requests carry ui_locale for app-response fallback; the message language takes priority when detected. User/model text is not translated.
