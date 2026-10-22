# Nó n0 · planejador Claude · ordem 261020-145313-9dfdbf · 6 notas da mesa (app:home)

Status: **corrigido pela IA · confira** (não é aprovação humana). Revisão independente: GLM n1 (`nos/n1/resultado.md`), sem achados graves; os 2 médios foram tratados.

## O que mudou (apps/megabrain-dashboard)
1. **Cursor — comentar em cima de botão clicava o botão; em algumas áreas nada acontecia** (notas nmv8cwcfq e nmv8czaxx, reincidentes).
   - Causa medida: o gesto segurar (0,4 s) ignorava regiões inteiras — `.topbar`, `.project-rail`, `.board-tools`, `.organize-controls` — então segurar sobre um botão ali não abria o leque e o botão era clicado; e o modo Comentar ignorava `select` e tudo que tinha `data-cf-ignorar` (títulos e barras de ação dos painéis), deixando o clique passar para o botão ou não fazendo nada.
   - `web/src/CursorTools.tsx`: `ignorarAlvo` sem `select`; `ignorar` sem as 4 regiões, mantendo só campos de digitar, iframes/mídia, modais e alças de arrastar (`[data-cf-alca]`, `.module-handle`, `.rail-move-handle`, `.react-resizable-handle`).
   - `web/src/HomeDesk.tsx`, `web/src/App.tsx`, `web/src/MultiReportWorkspace.tsx`: títulos-alça de painel/módulo/resposta trocaram `data-cf-ignorar` por `data-cf-alca` (comentar funciona; segurar continua com o arraste); barras de ações de painel e de resposta perderam `data-cf-ignorar`.
2. **Cotas IA junto do MegaBrain e configurações dentro dele** (nota nmv8czaxx, parte não reincidente): já existia — `central_desktop.py:92-94` chama `ensure_widget` no arranque e a engrenagem do widget abre `quota-settings` no MegaBrain (`apps/ia-quota-widget/widget_app/main_window.py:274`). Só conferido; widget vivo (PID 62436) depois dos 2 reinícios.
3. **"adicione" + "dropdown com Todos os projetos como padrão"** (notas 3d165244 e 2aee7c27): `web/src/HomeCatalog.tsx` — seletor "Projeto" começa em "Todos os projetos"; escolher um projeto filtra e mostra os módulos dele (em "todos", aviso para escolher).
4. **"só relatórios completos, ícone por tipo e nome embaixo"** (notas 19545827 rascunho + bf5e74af completa): o bloco virou "Relatórios" só com entregas HTML e PDF (imagens, áudio e texto saem; continuam na Biblioteca do projeto), em cartões com ícone + selo do tipo e o nome inteiro embaixo (sem reticências), recente primeiro. CSS em `web/src/home-desk.css`.
5. **Estrutural — notas da mesa entram sozinhas na ponte**: `central_server.py` rota `POST /api/projects/{pid}/comments` chama `ponte.receber` quando o alvo começa com `app:` (como as respostas de relatório já faziam). Notas de quadro (`module:*`) ficaram fora, leitura conservadora após a revisão GLM. Teste novo `tests/test_central_bridge.py::ApiTests::test_note_on_the_app_desk_enters_the_bridge_like_a_report_reply`.

## Como verifiquei
1. Teste CDP (Edge headless) na **instância isolada** (cópia do banco, porta 8768; nada gravado no banco real): `evidence/261020_comentarios-app-home/repro-cursor.mjs`.
   - Antes (`saida/antes/resultado.json`): em 1440 px, 5 falhas de botão clicado (topbar, lateral e link no segurar; select no Comentar e no segurar).
   - Depois (`saida/depois3/resultado.json`): 16/16 em 1440 px e 16/16 em 390 px, incluindo ações de painel e alças. Segurar sobre select e sobre alça de arrastar continua com a página, de propósito.
   - Catálogo: padrão "Todos os projetos", 233 relatórios só HTML, 0 nomes cortados; filtro MegaBrain = 41 relatórios + 6 módulos. Prints em `saida/depois3/catalogo-1440.png`, `catalogo-390.png`, `catalogo-filtro-*.png`.
2. `npm run build` OK (tsc + vite); `npm run test:ui` 12/12; Python `test_central_bridge`, `test_central_bridge_completion`, `test_central_security` e `test_isolated_server`: 51 OK.
3. App real reiniciado 2× (WM_CLOSE + WMI, autorização permanente): 59012 → 74304 → 73504, `/api/health` ok, HTML servido = `index-Cam60l15.js` do dist novo (`evidence/261020_comentarios-app-home/restart.json`, backup do banco em `backup-nativo/`).

## Pendências
1. <USUARIO>: conferir na própria janela (Comentar e segurar sobre botões do topo, da lateral e dos painéis; catálogo "Relatórios"). O efeito na janela dele não foi visto: o print nativo saiu tampado por outras janelas e foi descartado.
2. Decisão do <USUARIO>: notas de quadro (`module:*`) também devem ir sozinhas para a ponte? Hoje só as `app:*` vão.
3. Intermitente: numa de 3 rodadas, segurar no botão "Personalizar" de um painel em 1440 px clicou em vez de abrir o leque; não se repetiu nas 2 rodadas seguintes nem isolado.
4. Com a ferramenta Comentar ativa, arrastar painel pelo título fica bloqueado (é comentar); no modo Interagir o arraste segue igual.
5. "Todos os projetos" lê o catálogo de até 23 projetos pela fila de 3 (antes 1–2), e a contagem inclui entregas históricas (listadas por último).

Reversão: `evidence/261020_comentarios-app-home/backup/` (fontes, `central_server.py`, `web-dist-antes/`) + `npm run build` + reinício. Sem git, sem publicação.
