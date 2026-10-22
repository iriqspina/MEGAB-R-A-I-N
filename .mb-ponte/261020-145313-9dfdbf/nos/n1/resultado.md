# Nó n1 · Revisão: cursor, catálogo e ponte app:home · 261020-145313-9dfdbf

Veredito: **sem achados graves**. 2 médios (decisão de escopo e lacuna de prova), 4 leves. As 4 mudanças do n0 conferem contra o backup, os 20 testes da ponte passam e o app real foi reiniciado com prova.

## Achados

1. **[médio] Ponte despacha TODO comentário da rota, não só `app:home`** — `apps/megabrain-dashboard/central_server.py:224`. O item 6 da auditoria pedia que notas da mesa (`app:home`) entrassem na ponte; a implementação chama `ponte.receber` para qualquer comentário criado em `POST /api/projects/{pid}/comments` — inclusive `module:*` (notas em módulos de quadro) e alvo `project`. Cada nota solta passa a abrir/complementar uma ordem de IA após a janela de 60 s por projeto. Mitigantes reais: o lote agrupa comentários próximos (`central_bridge.py` ~880, dedupe por id), `auto` é desligável por projeto e o comentário ganha status visível ("Na fila para…"). A direção é coerente com o espírito da auditoria ("não depender de resgate manual"), mas é expansão de despacho automático sem assinatura explícita do <USUARIO> → pendência de decisão dele: manter para tudo ou restringir a `app:home` + respostas de relatório.

2. **[médio] Prova não exerce as duas mudanças mais específicas da ordem** — `evidence/261020_comentarios-app-home/saida/depois/resultado.json`: as regiões `painel-acao` (`.home-panel-actions` sem `data-cf-ignorar`) e `modulo-alca` (`data-cf-alca` no `module-head`) ficaram `alvo: null` nos dois viewports (elementos fora da viewport da mesa; o harness não rola até painéis nem abre board de projeto). As 8 regiões medidas passam, mas a mudança 2 do TAREFA foi verificada só por leitura de código, sem prova de interação. Rodada extra do `repro-cursor.mjs` com um painel visível/board aberto cobre a lacuna.

3. **[leve] `select` × segurar segue vermelho na prova (2 viewports)** — `evidence/.../repro-cursor.mjs` espera leque sobre `.home-catalog select`, mas `CursorTools.tsx:65` mantém `select` em `ignorar` de propósito (o dropdown continua usável; medição `cliques=1`). Não é regressão (vermelho também no antes); é expectativa do harness divergente da decisão de implementação. Ajustar a expectativa do harness ou documentar a decisão.

4. **[leve] Com a ferramenta Comentar ativa, arrastar/mover fica bloqueado** — `data-cf-alca` não entra em `ignorarAlvo` (`CursorTools.tsx:63`); o motor previne `pointerdown`/`click`/`mousedown` em fase de captura (`web/public/cursor-ferramentas-v1.2.js:308-309,354,376-383,387`), então com Comentar ativo não dá mais para arrastar painel pelo título nem mover a barra lateral (`.rail-move-handle`) — antes o `data-cf-ignorar` devolvia o gesto à página. Em Interagir (padrão) nada mudou: alças protegidas por `[data-cf-alca]`, `.rail-move-handle`, `.react-resizable-handle` (+ `data-cf-ignorar` permanente em `grid-gesture.tsx:82`); digitar intacto (`input,textarea,[contenteditable]` nas duas listas). Comportamento declarado no comentário do código; registro como mudança percebida, não defeito.

5. **[leve] Custo da primeira leitura em "Todos os projetos"** — `HomeCatalog.tsx:119-121` pede `ProjectDetail` de todo projeto com `report_count>0` (23 projetos na prova) pela fila de 3 simultâneas (`HomeDesk.tsx:18`). Termina e a prova carregou as 233, mas a mesa agora dispara até 23 leituras onde antes eram 1–2. Sem loop no efeito (deps via `missingKey`; `request` deduplica por inflight/queue), chave `pid:file_id` única, projeto removido cai graciosamente no modo "todos", campos `report_count`/`delivery_count` existem no servidor (`central_sources.py:148`).

6. **[leve] Contador inclui relatórios históricos** — `catalogReports` (`HomeCatalog.tsx`) inclui entregas `historical` junto com as correntes, ordenadas por grupo (corrente antes, histórica depois, cada grupo por data desc). "Recente primeiro" vale dentro dos grupos; um histórico de ontem fica abaixo de um corrente de mês passado, e o 233 da prova inclui versões antigas. Decisão razoável para "apenas relatórios completos"; registro o efeito.

7. **[info] n0 sem `resultado.md` no disco** — `nos/n0/` tem só TAREFA/no.json/revisao-tarefa.md/saida.log vazio no momento desta revisão; o parecer do planejador ainda não foi gravado. As mudanças em si foram conferidas diretamente no código/evidência.

## O que foi verificado (e passou)

- **Diff contra backup**: `CursorTools.tsx`, `HomeDesk.tsx`, `App.tsx`, `MultiReportWorkspace.tsx`, `HomeCatalog.tsx`, `home-desk.css`, `central_server.py` — exatamente o descrito no item 1–4 do TAREFA; `edit_catalog.py` é só a etapa intermediária de edição (o fonte final tem `at` e ordenação por data a mais que o script).
- **Motor cursor v1.5** (inalterado nesta ordem; mesmo sha em `public` e `dist`): modo Comentar segura o clique em captura (nota abre, botão não dispara); clique-fantasma pós-leque engolido por `engolir` (700 ms); `.topbar/.project-rail/.organize-controls/.board-tools` saíram do `ignorar` e o leque agora abre ali com clique preservado.
- **Rota da ponte**: `if created` + `try/except` com log (comentário salvo não se perde); lote deduplica por id; sem duplicação com a rota de respostas de relatório, que já chamava `ponte.receber antes` desta ordem (backup `central_server.py:339`; rotas e comentários distintos).
- **Testes**: `python -m unittest tests.test_central_bridge` → 20/20 OK, incluindo o novo `test_note_on_the_app_desk_enters_the_bridge_like_a_report_reply` (nota `app:home` → estado `fila`, comentário persistido com `ponte`, reenvio idempotente não duplica o lote).
- **Build/deploy**: `web/dist` reconstruído 20/10 15:11 (`index-Cam60l15.js` + CSS novo) contém `data-cf-alca`, `home-report-tile`, "Todos os projetos"; assets antigos removidos; instância isolada da prova serve esse mesmo build.
- **Reinício do app real**: `evidence/261020_comentarios-app-home/restart.json` — WM_CLOSE + relançamento por WMI fora do job, pid 59012→74304, listeners 8766/8767 migrados, `/api/health` ok, DB backupado antes (`backup-nativo/central-1792519950.sqlite3`), checagem de jobs ativos antes de fechar.
- **Números da prova (antes × depois)**: antes 5/24 (390) e 7/24 (1440) ok — topbar segurar clicava o botão, `select`/`link` comentar clicavam em vez de comentar, rail segurar clicava. Depois: 11 regiões medidas × 2 modos, tudo ok exceto `select`×segurar (item 3). Catálogo: default "Todos os projetos" nos dois viewports (DOM), contagem 233, tiles só HTML (12 visíveis + "Mostrar todos os 233"), 0 nomes cortados (medição `scrollWidth`), módulos só no filtro por projeto (6 para MegaBrain, 41 relatórios); PNGs 1440/390 e do filtro conferidos por análise de imagem (quebra de nome por hífen é o `overflow-wrap:anywhere` intencional do CSS; "Intergir" lido pela visão era texto pequeno — no código está "Interagir").

## Pendências

1. <USUARIO> decidir o item 1 (despacho automático para `module:`/`project` ou só `app:home` + respostas).
2. Rodada extra do harness cobrindo `painel-acao` e `modulo-alca` com painel visível/board aberto (item 2).
3. Ajustar expectativa do harness para `select`×segurar (item 3).

Nada foi editado no código do app por este nó; revisão somente leitura + execução de testes/harness existentes.
