# Próximos marcos

Implementados nesta cópia: diário por personagem com categorias livres, trechos de conversa revisados, resumos de sessão revisados, prazos manuais que seguem para novas conversas, voz PT/EN configurável, leitor PC LZ4, importação JSON, watcher, OCR revisado, HUD/atalhos Windows e diagnósticos. Fauna, diário de missões do NMS e temporizadores ativos de fragatas ainda não são importados.

Próximo marco de validação: iniciar na sessão normal do Windows, configurar um provedor real e realizar o teste de 30 minutos no NMS sem bordas descrito em TESTING.md. Um marco de dados futuro é pesquisar campos estáveis para fauna e missões e verificar se os horários das fragatas existem no save atual; só importar depois de validar a estrutura em saves representativos e manter a leitura somente de dados.

Evoluções possíveis:
- Tradução de IDs e catálogo de receitas com fonte e versão do jogo.
- Indexação de lugares antigos por busca mais inteligente.
- Associação de glifos de portal e rotas entre registros verificados.
- Melhoria de OCR para interface em português e telas específicas.
- Voz local opcional com modelos licenciados.
- Pesquisa isolada sobre entidade/seguidor no jogo, sem tratar isso como capacidade pronta.
