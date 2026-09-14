# Correções finais — 260908

TL;DR: os cinco itens foram implementados; **167 testes e 28 subtestes passaram**, ante 150 e 28 na entrada. Esta rodada não consultou nenhum serviço real. Este documento complementa o relatório de UX anterior e substitui suas referências ao comportamento de idade, persistência e cadência.

## Mudanças e evidência

| Item | Resultado | Arquivo:linha |
| --- | --- | --- |
| Consulta pendente sobrevive a reconstruções | Layout, segunda fonte ligada e atualização de idade mantêm “consultando…” sem ressuscitar o número em cache. | `widget_app/main_window.py:295` |
| Dado antigo degrada mesmo com status ok | Idade ≥900 segundos ou idade desconhecida marca a leitura ok como antiga. O fallback após falha continua marcado como reutilizado, preservando a carência de cor dos dados recentes. | `widget_app/snapshot_store.py:20` |
| Envelhecimento sem nova resposta | O timer local existente de 30 segundos também redesenha os segmentos; a passagem do tempo pode degradar a cor sem uma resposta de rede. | `widget_app/main_window.py:303` |
| Menu mostra idade | Número acompanha age_label e “dado antigo” quando aplicável. Falhas com último dado bom também exibem idade. | `widget_app/main_window.py:432` |
| Overrides de execução não persistem | `--theme`, `--expanded` ou `--screenshot` criam sessão sem gravação de configurações, inclusive ao fechar. Nessa sessão, ajustes adicionais também são temporários. | `widget.py:46`, `widget_app/main_window.py:589` |
| Recuo independente por fonte | HTTP 429 inicia pausas de 240, 480 e 900 segundos, mantendo teto de 900. Sucesso zera o histórico; outros status não o zeram. Fontes saudáveis continuam separadas. | `widget_app/poll_backoff.py:5` |
| Recuo respeitado em todos os caminhos | Timer normal, atualização manual e religar provedor não antecipam a consulta limitada. Um timer preciso por fonte retoma ao vencer a pausa, sem esperar mais um ciclo global e sem consultar outras fontes. Não consulta fonte escondida ou já em voo. | `widget_app/main_window.py:347`, `widget_app/main_window.py:401`, `widget_app/main_window.py:421` |

## Captura do produto

![Qt.Tool: Codex antigo em cinza e Claude recente em verde, ambos com 40% fictícios rotulados](evidence/260908_final_stale_qt_tool_demo.png)

O script `evidence/260908_capture_age_demo.py` executa **widget.py por runpy, com as flags de produção Qt.Tool intactas**. Usa o modo demo explícito e injeta apenas os dados da demonstração: mesmo percentual fictício nos dois cards, Codex com leitura de duas horas, Claude com leitura atual. O banner identifica que não existe conexão real. O teste visual prova a cor degradada por idade sem esperar duas horas nem bater novamente no endpoint limitado. O screenshot foi aberto e inspecionado. Não é medição de cota real nem teste de foco nativo.

## Verificação

1. Comando: `.venv/Scripts/python.exe -m pytest tests -q` → **167 passed, 28 subtests passed**. Os 17 casos novos estão em `tests/test_final_fixes.py`; usam relógio controlado e respostas locais, não rede.
2. Cobertura: três gatilhos de reconstrução; idade antiga em sete temas; envelhecimento sem fetch; idade no menu; settings idêntico após tema/expansão/fechamento temporários; progressão/teto/reset de recuo; bloqueio nos três caminhos; retry de uma única fonte e exclusão de fonte escondida.
3. Um teste antigo usava data fixa e exigia “fresco” para sempre. Sua fixture agora usa o horário atual; a asserção de leitura recente foi preservada (`tests/test_snapshot_store.py:20`). Não removi testes.
4. Não existia recuo no código lido na entrada. Esta implementação fica na camada de janela e em PollBackoff; providers.py permanece intacto.
5. Captura encerrou normalmente; verificação de processos não encontrou widget.py nem o script de captura pendente. Sem git, instalação ou alterações fora da pasta do app.

## Limites e decisões

1. O recuo é mantido na memória da sessão; reiniciar o processo perde o histórico. Persisti-lo exigiria uma decisão adicional sobre estado operacional em disco e ficou fora deste escopo.
2. Os timers dependem do loop de eventos do Qt: processo suspenso não executa a tentativa no instante previsto; ao retomar, as guardas de idade e consulta continuam valendo.
3. A idade do dado pode ficar até o próximo tick local de 30 segundos sem redesenho. Nenhuma resposta de rede é necessária para atualizá-la.
4. Não foram alteradas as quatro dívidas explicitamente excluídas: barra de zero, escolha da primeira janela sem medição, origem do nome do card e comentário sobre cores sem número.
5. Não houve validação de backoff contra API real nem nova rodada de interação nativa. A suíte verifica a política e os caminhos do widget; a captura verifica renderização Qt.Tool com dados fictícios rotulados.
