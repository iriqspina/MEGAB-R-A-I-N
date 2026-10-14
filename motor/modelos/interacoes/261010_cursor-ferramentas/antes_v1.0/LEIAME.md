# Ferramentas do cursor · v1.0 · 261010

Ideia do <USUARIO> (Portfólio, 10/10/2026): segurar o botão esquerdo por 2 s, sem arrastar, abre um
menu em leque em volta do ponteiro; ali o cursor troca de ferramenta (Interagir ↔ Comentar).
Pedido literal: "salva essa ideia pq eu quero usar ela em outros casos, então seria bom ter um artefato só dela".

- `cursor-ferramentas.js` — fonte única. Sem dependências, injeta o próprio CSS, expõe `window.CursorFerramentas.iniciar(opções)`.
- `demo-fonte.html` + `build.py` → `demo.html` (autocontida). Publicada como artefato: https://claude.ai/artifact/FC9hWt3J2PJffLiRyAUd5d
- Comentar: `modo:'auto'` usa `comments.openComposer` quando a página roda no claude.ai com a capability `comments`;
  fora dele cria nota local (pino numerado + editor), guardada em localStorage (`chave`) e lida por `notas()`.
- Para artefato do claude.ai: colar o JS inline (CSP bloqueia arquivo externo fora das CDNs permitidas) e declarar
  `capabilities: {comments: {}}` (ou `{"composer_only": true}` se só abrir o composer).
- Consumidores: Portfólio · Decisões do Portfólio (`Portfolio/evidence/261010_decisoes/tools/build.py`), geradores POP (`bin/mb_pop_tema.html_interacoes`), `bin/mb-interacoes.py`, modelo `../261010_decisoes-respondiveis/`.

Testes feitos em 261010: segurar/cancelar ao mover, clique engolido após abrir o menu, troca de ferramenta,
nota local criada/editada/excluída, celular 390 px por emulação. Não testado: openComposer real (depende do clique humano no claude.ai).
