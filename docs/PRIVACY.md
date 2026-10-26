# Dados e conexões

O servidor é local, em 127.0.0.1. Não publique essa porta na rede.

## Armazenamento

Por padrão, launch.py mantém os dados privados em .runtime/userdata. O banco SQLite contém conversas, notas, diário, snapshots normalizados e medições de tempo, separados por personagem. Capturas ficam em uma pasta do personagem. Arquivos de áudio temporários são removidos após transcrição.

O arquivo settings.json contém preferências e caminhos de saves, sem a chave Gemini. A chave usa Windows Credential Manager; GEMINI_API_KEY é uma alternativa. O endereço do Ollama é configurável e deve apontar para um servidor em que você confie.

## Fluxos

- Microfone → transcrição local CPU → texto.
- Captura da região visível do NMS → OCR local → revisão → anotação.
- Save vinculado → leitura estável → normalização local → snapshot.
- Pergunta + persona + notas/diário selecionados + dados relevantes do último save → provedor escolhido.

Ollama recebe esse texto no endereço configurado. Gemini recebe esse texto nos servidores do Google quando seu processamento é habilitado. A aplicação não envia áudio nem screenshots brutos ao Gemini. Consulte os termos, quota e faturamento do seu projeto no AI Studio.

A primeira preparação baixa dependências Python, o mapa de chaves e, ao usar transcrição, os pesos do Whisper. Esses downloads são distintos das chamadas de conversa.

## Retenção e exclusão

Histórico pode ser limpo pela interface. Entradas do diário podem ser excluídas individualmente e exportadas em JSON. Excluir uma anotação não remove automaticamente o PNG anexado. Capturas descartadas também permanecem na pasta local até limpeza manual.

Os arquivos originais do NMS são abertos somente para leitura. O leitor externo opcional recebe uma cópia temporária, nunca o original. Formatos não reconhecidos não produzem atualização do contexto.

Pacotes, configurações, banco, capturas e modelos ficam fora dos commits. Antes de compartilhar uma cópia manual da pasta, exclua os diretórios de runtime e teste.

## Interface preference and direct reports

The EN/PT web-interface preference is stored in browser localStorage. It does not send user text to a translation service. A direct Save reader report requires an explicit facts-mode request and is formatted locally. Default chat sends selected context to the configured provider and displays a separate local reference of verified save facts. Local Ori does not import ChatGPT account memory or unrelated personal records.
