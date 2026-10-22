# Revisão independente (somente leitura) · ordem 261020-145313-9dfdbf

Você é o **revisor**. Não edite código do app; escreva só o seu parecer em `resultado.md` da sua pasta de nó.
Projeto: `<MEGABRAIN_ROOT>/apps/megabrain-dashboard`. Backups do "antes": `<MEGABRAIN_ROOT>/evidence/261020_comentarios-app-home/backup/`.

## O que o Claude (n0) mudou — confira cada um contra o backup (diff)
1. `web/src/CursorTools.tsx` — listas `ignorarAlvo` (modo Comentar) e `ignorar` (gesto segurar 0,4 s). Pedido do <USUARIO>: "quando uso a ferramenta de comentar em cima de um botão, em vez de comentar ela clica no botão" e "em algumas áreas o comentário não fixa, nada acontece".
2. `web/src/HomeDesk.tsx`, `web/src/App.tsx`, `web/src/MultiReportWorkspace.tsx` — alças de arrastar passaram de `data-cf-ignorar` para `data-cf-alca`; barras de ações de painel perderam `data-cf-ignorar`.
3. `web/src/HomeCatalog.tsx` + `web/src/home-desk.css` — seletor de projeto com "Todos os projetos" como padrão; só relatórios HTML/PDF (sem imagens/áudio/texto), em cartões com ícone do tipo e nome completo embaixo; ordem recente primeiro.
4. `central_server.py` rota `POST /api/projects/{pid}/comments` agora chama `ponte.receber` (notas da mesa `app:home` entram na ponte); teste novo em `tests/test_central_bridge.py`.

## Procure
- Algum lugar onde segurar/comentar agora atrapalha arrastar painel, redimensionar, mover a barra lateral ou digitar.
- Regressão de tipo/estado no HomeCatalog (fila de leitura `request`, efeito em loop, chave React duplicada, projeto removido).
- A rota de comentário: duplicação no lote da ponte, exceção sem captura, efeito em comentários de quadro (`module:`) que não deveria existir.
- Prova: `evidence/261020_comentarios-app-home/saida/antes` × `saida/depois` (resultado.json e PNGs) — os números batem com o que foi dito?

## Formato do parecer
Lista de achados com gravidade (grave/médio/leve), arquivo:linha e motivo; ou "sem achados graves". Seja específico; sem elogio.
