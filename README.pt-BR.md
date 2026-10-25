# Orion (Ori) — Companheiro para No Man's Sky

[English](README.md)

Eu queria uma IA com quem pudesse conversar enquanto exploro No Man's Sky. Alguém para guardar meus lugares, planos e descobertas, e me ajudar a continuar a viagem de onde parei. É essa a ideia do Ori.

O aplicativo roda no PC, com interface no navegador, voz, diário por personagem, leitura do último save e um HUD opcional de legendas no Windows. A IA pode ser local pelo Ollama ou usar Gemini. Ainda é um protótipo, então deixei explicado o que funciona, como funciona e onde estão os limites.

Ori é um companheiro externo. Ele não coloca um personagem dentro do jogo.

## Começar no Windows

É necessário **Python 3.12**, Chrome ou Edge e um provedor de IA. Para usar localmente, instale o Ollama e baixe um modelo de conversa separadamente.

1. Clone ou baixe o projeto.
2. Abra **start.bat** para o navegador ou **start-desktop.bat** para abrir também o HUD.
3. Aguarde a preparação e acesse **http://127.0.0.1:8765** se a página não abrir sozinha.
4. Em **Sistemas de IA**, escolha o provedor e o modelo. Salve as configurações.
5. Teste digitando. Depois segure o botão do microfone, fale e solte para enviar.
6. Escolha o personagem, abra **Expedição & diário** e vincule o save dele.

A primeira preparação baixa pacotes Python e o mapa de chaves do leitor. A primeira transcrição baixa o Whisper escolhido. Depois disso, a conversa pode continuar local com o Ollama.

Mantenha o terminal e **uma aba do Ori** abertos. Fechar apenas a aba não encerra o servidor. Para terminar, feche o HUD ou pressione **Ctrl+C** no terminal.

Se aparecer o aviso de outra instância, use a janela já aberta no endereço local. O launcher evita duplicar processos e informa se a porta está ocupada; ele não encerra outros programas.

## Interface em inglês ou português

O seletor **EN / PT** muda a interface web e guarda a preferência no navegador.

Isso é separado do idioma do reconhecimento de fala. Dá para usar interface em inglês e falar português. O modelo recebe a orientação de responder no idioma da mensagem.

## Escolher a IA e os parâmetros

A lista vem do seu servidor Ollama. Aceita modelos de conversa instalados, inclusive nomes personalizados e tags. Atualize a lista depois de instalar outro. Modelos exclusivos de embeddings ou ranking não respondem ao chat.

| Modo | Comportamento |
| --- | --- |
| Somente Ollama | Usa o endereço e o modelo local selecionados. |
| Somente Gemini | Usa a API do Google após consentimento. |
| Automático | Verifica Ollama primeiro; Gemini exige consentimento, fallback habilitado e chave configurada. |

Cada resposta nova identifica a fonte/provedor e o modelo. Alterar uma seleção exige salvar antes da próxima mensagem.

O endereço padrão é `http://127.0.0.1:11434`. Se usar Docker, publique essa porta para o Windows. Para conferir a instalação:

```powershell
ollama list
ollama ps
```

O aplicativo não inicia o Docker nem baixa modelos Ollama automaticamente.

### Controles por modelo

Abri uma seção recolhida para ajustar o necessário sem transformar a interface em outro painel completo de modelos. Cada nome exato de modelo tem seus parâmetros salvos separadamente.

| Controle | Valor inicial | Como funciona |
| --- | --- | --- |
| Contexto | 32768 tokens | Janela solicitada; 0 deixa o Ollama escolher. |
| Saída máxima | 512 tokens | Limite da geração, incluindo raciocínio quando houver. |
| Temperatura | 0,7 | Padrão geral; confira a recomendação do modelo. |
| Threads CPU | 0 | Automático; um valor positivo solicita esse número. |
| Manter carregado | 5m | 0s libera após responder; -1 mantém na memória. |
| Tempo de espera | 180 segundos | Espera de conexão/leitura, ajustável de 15 a 900. |
| Raciocínio interno | Desligado | Depende do suporte do modelo. |

**Usar padrões do modelo** consulta os metadados locais. Usa o contexto configurado quando informado, sem adotar automaticamente o máximo anunciado. O que não for informado mantém o valor atual.

Para o Liquid 1.2B Instruct, posso usar **32768 de contexto, temperatura 0,1 e raciocínio desligado**. Ter 32k dá espaço para receber informações; a precisão continua dependendo de como o modelo consegue usá-las.

**Liberar modelo da memória** pede ao Ollama para descarregar o selecionado. A próxima resposta precisa carregá-lo novamente. O botão fica bloqueado durante uma resposta ativa.

### Gemini

Salve a chave do Google AI Studio e permita o processamento na nuvem. Ela fica no **Gerenciador de Credenciais do Windows**; `GEMINI_API_KEY` é uma alternativa por variável de ambiente.

Consulte os modelos disponíveis para sua chave. Estar na lista não garante gratuidade: confira quota e faturamento no projeto do Google.

- **429:** limite de uso/quota.
- **503:** indisponibilidade temporária do serviço. Salvar a mesma chave novamente não resolve.
- **401/403:** conferir chave e permissões.

A assinatura do ChatGPT não inclui créditos da API da OpenAI. Ori usa Ollama ou Gemini, sem aproveitar a assinatura do ChatGPT.

## Conversar durante o jogo

Abra o Ori primeiro e use NMS em **janela sem bordas**. A aba recebe os eventos nativos, envia a transcrição e fala as respostas. O HUD sozinho não é um cliente completo de conversa.

| Ação | Controle |
| --- | --- |
| Começar a gravar / terminar e enviar | F8, uma vez para cada ação |
| Cancelar gravação, resposta e voz | F9 |
| Capturar a janela visível do NMS para OCR | F10 |
| Falar pelo navegador | Segurar o botão e soltar para enviar |
| Limpar o chat do personagem | Nova conversa |

As gravações têm limite de 60 segundos. O trabalho de áudio fica fora da thread dos atalhos/HUD. Falhas de registro de atalhos aparecem no diagnóstico.

Whisper tiny/base multilíngue transcreve na CPU/int8. A voz de saída usa as opções disponíveis no navegador/Windows. Raciocínio interno identificado pelo provedor é filtrado do texto e da voz; isso não muda o tipo de modelo carregado.

## O que vem do save

**Não precisa abrir o NMS para ler um save que já existe.** Durante o jogo, novidades chegam depois do próximo salvamento. Ori não lê a memória do processo nem observa a tela continuamente.

| Informação | Suporte atual |
| --- | --- |
| Units, Nanites, Quicksilver | Campos reconhecidos, quando presentes |
| Bases | Nomes e dados disponíveis de posição/endereço |
| Localização | Último endereço salvo |
| Inventário | Entradas legíveis de inventários suportados do jogador, depósitos, cargueiro, naves e veículos |
| Objetivos, lore e planos pessoais | Registros feitos no diário do Ori |
| Livro completo de missões do NMS | Ainda não importado |
| Tela atual | Captura solicitada e OCR revisado |

IDs de itens podem não estar traduzidos. IDs binários ilegíveis são omitidos com aviso. Uma seção vazia pode significar campo não suportado ou save não vinculado; não prova que o personagem não tem itens.

O arquivo original é somente lido. O leitor PC suporta blocos LZ4 com limites de tamanho e mapa de chaves versionado. JSON legível também é aceito. O libNOM CLI opcional recebe uma cópia temporária.

Vincule o arquivo ao personagem certo. O watcher verifica mudanças a cada quatro segundos e espera a gravação estabilizar. Origem e horário permanecem visíveis.

## Por que separei os fatos da resposta da IA

Nos testes, o modelo pequeno recebeu valores corretos e mesmo assim misturou moedas com contagens de inventário. Também inventou a função de bases apenas pelo nome.

Por isso, pedidos explícitos de resumo e estatísticas usam uma **resposta direta do leitor de save**. O Python formata os valores do snapshot daquele personagem, sem pedir à IA para reescrever os números. A fonte aparece no identificador da resposta. Sugestões incluídas nessa rota são identificadas como sugestões do aplicativo, não missões salvas.

A conversa geral continua usando o modelo escolhido. Ele pode interpretar errado e inventar informações. Instruções ajudam, mas não garantem precisão. Um nome de base não comprova que ali exista fábrica, pesquisa, recurso ou missão.

O modelo recebe contexto selecionado: diário, objetivos, histórico recente e resumo do save. Não recebe cada slot de inventário nem todas as conversas a cada pergunta. A busca de itens usa texto/IDs; ainda não existe um catálogo completo de nomes e receitas do jogo.

## Memória, identidade e diário

Cada personagem separa conversas, memórias fixas, diário e snapshots.

O Ori local **não herda minha memória do ChatGPT**, e-mails, histórico do navegador ou informações pessoais. Para guardar algo, uso uma memória ou registro explicitamente:

> Ori, remember my name is David.

> Ori, registra objetivo: construir um observatório perto da base principal.

> Ori, registra lore: esta colônia é a capital da minha rede de exploração.

> Pelos meus objetivos registrados, o que podemos fazer agora? Separe fatos de ideias.

Observações revisadas e resumos gerados também entram no diário, com a origem identificada. Lore continua sendo ficção do usuário.

**Nova conversa** apaga as mensagens do personagem e cancela a resposta atual. Mantém memórias, diário e save vinculado. Entradas do diário podem ser excluídas separadamente e exportadas como JSON.

## Captura e OCR

F10 captura a região visível da janela do NMS. Deixe o jogo sem outras janelas cobrindo a imagem. Também dá para enviar uma imagem.

O OCR tenta Windows OCR e depois RapidOCR na CPU. Revise nomes e números antes de confirmar. A captura só vira contexto do diário após confirmação. Capturas descartadas continuam locais até limpeza manual.

## Parte técnica

1. O navegador envia texto ou uma gravação curta ao Flask em `127.0.0.1:8765`.
2. Whisper transcreve o áudio localmente; texto digitado pula essa etapa.
3. SQLite carrega os dados do personagem. O leitor mantém snapshots históricos do save.
4. Pedidos reconhecidos de estatísticas usam a resposta direta; conversa geral vai ao Ollama ou Gemini autorizado.
5. A resposta chega por NDJSON, com texto na tela e frases encaminhadas à voz do navegador.
6. O serviço Windows cuida de atalhos, gravação limitada e HUD Tk.

Esta versão não pesquisa a web sozinha, não controla o jogo e não tem visão contínua.

Os módulos principais são `app.py` (API), `grounding.py` (relatórios diretos), `providers.py` (provedores), `memory.py` (SQLite/contexto), `game.py` e `save_reader.py` (saves), `desktop.py` e `capture.py` (desktop/OCR). A interface está em `static/` e `templates/`; o launcher é `launch.py`.

## Dados e estabilidade

O padrão do launcher é **.runtime/userdata**. `NMS_COMPANION_RUNTIME` altera o runtime; `NMS_COMPANION_DATA` altera apenas a pasta de dados.

Banco, configurações, modelos, capturas, áudio, logs, dumps e credenciais ficam fora dos commits. Os logs locais são **logs/orion.log**, com rotação, e **fault.log**, para falhas de baixo nível quando disponível. Os logs do aplicativo não registram deliberadamente prompts ou chaves.

Ollama/Gemini recebem o texto selecionado. Áudio e OCR são locais; as gravações e imagens brutas não vão ao Gemini. O Google recebe o contexto de texto quando a nuvem é autorizada.

Timeout não prova que o Ollama esteja desligado. Carregamento e prompts longos podem demorar. Confira serviço, modelo e tempo de espera antes de repetir.

Houve um travamento relatado ao abrir o NMS. O dump encontrado estava vazio e não permitiu determinar a causa. Esta atualização melhora cancelamento, limites de trabalho, instâncias duplicadas e logs. O teste real de estabilidade/FPS com o jogo continua necessário.

## Desenvolvimento e testes

Depois da preparação das dependências:

```powershell
New-Item -ItemType Directory -Force .tmp, .test-data | Out-Null
$env:PYTHONPATH = (Join-Path (Get-Location) '.packages') + ';' + (Join-Path (Get-Location) 'tests')
$env:NMS_COMPANION_DATA = Join-Path (Get-Location) '.test-data'
$env:TEMP = Join-Path (Get-Location) '.tmp'
$env:TMP = $env:TEMP
python -m unittest discover -s tests -v
```

Se os pacotes estiverem em `.runtime/packages`, use esse caminho. Execute com dados de teste, sem usar o diário real.

Os testes cobrem leitor, isolamento, parâmetros, streaming, cancelamento, relatórios diretos, memória, diário e launcher. O teste de navegador usa um provedor fictício. Os testes reais do Ollama confirmaram conexão e também reproduziram respostas factuais incorretas do Liquid.

Ainda faltam validar a sessão completa com NMS, microfone físico, atalhos nativos e FPS. Mais detalhes em [testes](docs/TESTING.md), [diagnóstico](docs/TROUBLESHOOTING.md), [arquitetura](docs/ARCHITECTURE.md), [privacidade](docs/PRIVACY.md) e [mudanças](CHANGELOG.md).

## Próximos passos

Quero evoluir o Ori aos poucos, principalmente nomes/receitas de itens, busca melhor e validação de voz e desempenho no jogo. Um seguidor nativo dentro do NMS ainda é pesquisa.

Ainda não escolhi uma licença geral para o projeto. As licenças das dependências e dos modelos continuam separadas. É uma ferramenta de fã, sem afiliação com a Hello Games.
