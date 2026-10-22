# gates.md — checklists executáveis por categoria (bloqueiam a entrega)

Gate = passo ANTES de abrir a entrega pro humano. Passou, grava a prova em
`evidence/<tarefa>/qa-checklist.md` (item a item, com hora real de `date`).
Sem checklist gravado, a entrega não abre. Comando entre crases é o mínimo
mecânico; adapte ao projeto mantendo a prova.

## bater-referencias (GATE 0 — universal, antes de CRIAR, EDITAR ou AFIRMAR qualquer coisa não trivial)

Pedido literal do <USUARIO> (261019): "bata as referencias antes de fazer as coisas".
1. LISTE as referências que governam o que você vai fazer e CONFIRA CADA UMA antes de escrever:
   padrão visual do projeto/POP; biblioteca de ícones; `VOCABULARIO.json`; relatório-irmão da
   mesma pasta (o que ele já faz); regras do AGENTS/CLAUDE do projeto; lições da categoria em
   `ias/<sua-ia>/`; e a FONTE de cada dado que você vai afirmar.
2. A checagem cobre TODOS os elementos, não só os óbvios (a regra de ícone vale para botão,
   seta, selo e título igualmente — conferir elemento por elemento, não seção por seção).
3. Divergência entre referência e o que você ia fazer = achado registrado ANTES de escrever
   (categoria propria), não depois.
4. No `qa-checklist.md` da entrega, citar QUAIS referências foram batidas (path de cada uma).

## edicao-de-arquivo (antes de fechar qualquer edição de arquivo existente)

1. Backup do original (bytes) ANTES do primeiro write.
2. Edição por replace de trecho exato ou tmp + `os.replace` (nunca regravar
   arquivo inteiro lido como texto se o original não é UTF-8-LF puro).
3. Conferir: contagem de quebras CRLF/LF antes == depois; linhas diferentes
   == só o alvo (`git diff --no-index` ou diff python serve).
4. Lock de escrita (PermissionError): tentar tmp + `os.replace` com retry;
   nunca desistir silenciosamente nem apagar para recriar.

## teste-do-reparo (antes de declarar reparo feito)

1. Escrever/estender teste que FALHA antes do reparo e PASSA depois (prova os
   dois lados: rodar com o código antigo se possível, ou simular a entrada).
2. Rodar a suíte INTEIRA, não só o teste novo.
3. Nome do teste novo citado no registro de estado da tarefa.

## leitura-de-imagem (sempre que a decisão depende de imagem)

1. Sem visão comprovada nesta sessão? Declare "CEGO PARA IMAGEM" e passe a
   leitura para IA com visão ANTES de interpretar. Ferramenta externa de
   análise de imagem: prompt NEUTRO de transcrição literal + cruzamento com
   fonte em disco; divergência vira achado, não verdade.
2. Nunca escrever "conferi o print" sem visão real. O não-visto sai
   "NÃO VERIFICADO".

## verificacao-visual + entrega-visual (entrega HTML/peça visual)

1. Prints REGENERADOS DEPOIS da última edição (mtime do print > mtime do
   HTML), página INTEIRA, 1440 e 390, guardados em evidence.
2. Auditoria DOM headless que BLOQUEIA se: scrollWidth > viewport (390 e
   1440); img com naturalWidth=0; headings fora de ordem (h1→h3 sem h2);
   classe usada e não definida; filho decorativo de grid sem
   `grid-column:1/-1`; etiqueta "ilustração" em print real (e recíproca);
   h2 de assunto sem img/svg no escopo; onclick sem função; sem role=status
   em caixa de resposta; peso HTML+imagens acima do teto do canal (app:
   8 MB/imagem, 35 MB total, 64 MB HTML).
3. Ícone: biblioteca SVG do projeto (nunca emoji NEM glyph decorativo ✓↩✎↓) — em título,
   botão, seta e selo, elemento por elemento; tipografia e tokens do padrão vigente; legenda
   descritiva escolhida pelo CONTEÚDO da imagem, não pelo nome do arquivo.
3b. Badge/círculo numerado: conferir centralização real (inline-flex precisa de
   justify+align center) e contraste do número; ampliar e olhar como o humano faria.
4. QA lido por IA COM VISÃO (o print gerado não é prova por si).
5. Decisão respondível: opções equivalentes (sem pré-destaque da hipótese do
   executor), opção "outra coisa" + texto, resposta chega ao canal certo.

## interpretacao-de-termo + escopo-e-roteamento

1. Termo do <USUARIO> fora do glossário + 2 leituras possíveis + consequências
   diferentes = ECO antes de agir; artefato grande espera confirmação.
2. Ação que desfaz decisão humana anterior: reversibilidade de 1 passo
   declarada + confirmação pedida, ou não executa.
3. Despacho de peça visual nova: rota preferida do usuário (criação × revisão)
   consultada; ferramenta exclusiva registrada quando justificar concentrar.

## registro-e-evidencia + afirmacao-sem-prova + contagem

1. Horário só de fonte real (`date`, timestamp de arquivo); nunca placeholder
   com "x"/"~". Registro gravado ANTES da afirmação que o cita.
2. Toda frase factual em entrega humana cita path da prova; sem prova =
   "NÃO VERIFICADO".
3. Contagem afirmada = contada na hora (wc/grep -c), com comando citado.

## shell-e-ambiente (Windows + Git Bash)

1. Python inline: heredoc `<<'PYEOF'`, nunca `python -c` com crases/barras.
2. Caminho do central: espaço duplo (`MEGA B R A I  N`); robocopy via .cmd.
3. Processo que pode pedir input: `</dev/null` no fim.
4. Reinício simples autorizado; matar processo fora disso pergunta.
