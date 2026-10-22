# Nó n1 · Revisão independente da ponte

Papel: **revisor** · aberto por n0 (planejador, GLM) · profundidade 1.
Projeto: `<MEGABRAIN_ROOT>` · ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261018-170741-cb0ad1` (pedido original em pedido.json).

## Tarefa
Revisão independente, SOMENTE LEITURA: não edite, crie nem apague nenhum arquivo do projeto (a única escrita permitida é o seu resultado.md desta ordem).

Código a revisar (feito pelo Claude hoje, 18/10/2026; app fora do Git, por isso compare com os backups):
- apps/megabrain-dashboard/central_bridge.py (novo) — ponte: IAs ativas, ordens em .mb-ponte/, nós planejador/orquestrador/worker/revisor, supervisor de processo, fila com espera, reconciliação do status dos comentários.
- bin/mb-ponte.py (novo) — linha de comando usada pelas IAs (despachar, aguardar, estado, concluir, parar, iniciar).
- apps/megabrain-dashboard/central_server.py — compare com evidence/261018_ponte-orquestradores/backup/central_server.py (gancho no POST /api/reports/{fid}/feedback, rotas /api/bridge/vendors, /api/projects/{pid}/bridge, /bridge/send, /bridge/orders/{oid}/stop, tick no watcher).
- apps/megabrain-dashboard/central_store.py — método patch (compare com o backup).
- apps/megabrain-dashboard/web/src/BridgePanel.tsx, bridge.css e ReportFrame.tsx (compare com o backup).
- testes: apps/megabrain-dashboard/tests/test_central_bridge.py.

Procure defeitos concretos, com arquivo:linha e cenário que quebra:
1. Segurança: injeção de comando nos argv/script bash da janela, caminho fora do projeto (ordem/nó), segredos vazando para a sessão filha, rota que abre processo sem autenticação/CSRF, instância de prova abrindo IA.
2. Concorrência: dois watchers (app local e remoto no mesmo processo) lançando a mesma ordem; corrida no índice bridge-orders; complemento perdido.
3. Processos no Windows: supervisor desacoplado, kill da árvore, detecção de processo vivo, pythonw vs python, CODEX_HOME do Codex 1.
4. Estados errados mostrados ao <USUARIO> (rótulo que mente, ordem que fica "em andamento" para sempre).
5. Testes que não provam o que dizem.
Classifique cada achado: grave / médio / menor. Diga também o que está correto. Sem achado inventado: se não tiver prova, marque como hipótese.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261018-170741-cb0ad1/nos/n1/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.
