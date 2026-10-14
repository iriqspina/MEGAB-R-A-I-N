# Decisões respondíveis · v1.0 · 261010

Motor genérico extraído da página Decisões do Portfólio (aprovada pelo <USUARIO> em 10/10/2026).
- `decisoes-respondiveis.js` — `DecisoesRespondiveis.iniciar({chave, titulo, secoes:[{id, titulo, perguntas}]})`.
  Pergunta: `{id, n, tipo:'escolha'|'texto', titulo, porque, rec, opcoes:[{v, t, d, meta, vis, extra:'texto'|'data'}],
  valor, linha, ph, sug, img}`. Marcação: `<div data-dr-sec="ID">`, opcionais `data-dr-status` e `data-dr-dot`.
- Liga `CursorFerramentas` sozinho quando o script dele está na página (chip na barra do rodapé).
- `exemplo-fonte.html` + `build.py` → `exemplo.html` autocontido (publicado: https://claude.ai/artifact/BSSRapsDUqBGxRS4hoHbmp).
- Envio: claude.ai → `comments.sendToClaude` + `artifact.publish({'respostas.json'})`; fora → Copiar/Baixar.
Testado em 261010: render das caixas, campo extra, sugestão, progresso, resumo, copiar, aviso fora do claude.ai.
Não testado: envio real no claude.ai (depende do clique do <USUARIO> e da permissão de comentário).
