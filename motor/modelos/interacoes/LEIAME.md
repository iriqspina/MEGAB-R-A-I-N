# Interações dos relatórios MEGABRAIN · v1.0 · 261010

Elemento obrigatório desde 10/10/2026 (pedido do <USUARIO>: "lembre-se disso como elemento necessário
principal e recrie para os relatórios megabrain dos projetos ... até mesmo fora do claude").

| peça | quando | fonte | página no claude.ai |
|---|---|---|---|
| Ferramentas do cursor | todo relatório HTML para o <USUARIO> | `261010_cursor-ferramentas/cursor-ferramentas.js` | https://claude.ai/artifact/FC9hWt3J2PJffLiRyAUd5d |
| Decisões respondíveis | relatório que pede decisão dele | `261010_decisoes-respondiveis/decisoes-respondiveis.js` | https://claude.ai/artifact/BSSRapsDUqBGxRS4hoHbmp |

Primeira aplicação aprovada: Portfólio · Decisões do Portfólio — https://claude.ai/artifact/P37Pxq3utnX1GRnQUZcHnj

## Como aplicar
1. Relatório gerado pelos scripts POP (`mb-relatorio-projeto.py`, `mb-relatorio-vivo.py`): já sai com o cursor.
2. HTML feito à mão: `python MEGABRAIN/bin/mb-interacoes.py caminho.html` (insere ou atualiza; idempotente).
3. Relatório com perguntas: partir de `261010_decisoes-respondiveis/exemplo-fonte.html`, trocar seções e
   perguntas, rodar o `build.py` (cola os dois componentes) e publicar.
   - claude.ai: `capabilities {"artifact": {}, "comments": {}}`; o envio manda comentário "Send to Claude"
     (acorda a sessão se o artefato estiver vigiado com auto-replies armed) e grava `respostas.json`
     (ler com Artifact read, path `respostas.json`).
   - fora do claude.ai (arquivo local, Codex, Kimi, Gemini): o botão Finalizar oferece Copiar respostas
     (colar no chat do agente) e Baixar respostas (`<chave>-respostas-AAMMDD.json` em Downloads).
4. Conferir antes de entregar: segurar 2 s abre o menu; Comentar cria nota; Finalizar mostra resumo;
   print 1440 px e 390 px (por emulação com meta viewport; janela headless estreita mente).

## Contrato das caixas de decisão
- Contexto visual antes das perguntas: imagem real ou ilustração rotulada + 2 a 4 linhas com ícone.
- Uma caixa por pergunta; "por que pergunto" em uma linha; recomendação marcada e rotulada.
- Alternativa quando há opções (com campo "outro"/data quando couber); texto quando precisa explicar,
  com sugestões clicáveis.
- Um único botão Finalizar; o resumo marca "sua escolha" × "recomendação"; notas do cursor entram junto.
- Respostas mais recentes aparecem no topo ao reabrir (regra recente primeiro).
