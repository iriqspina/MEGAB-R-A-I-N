# Template POP de relatório · 260914

## O que é

Layout completo de relatório com o DNA escolhido pelo <USUARIO> em 260914:
**Raycast > Warp > Duolingo** (nessa ordem). Arquivo único, offline, zero
recurso remoto — mesma regra do relatório vivo.

Feito para TDAH: uma tela por setor, cor chapada por setor, ícone em toda
informação, dado como imagem, listas sem variância colapsadas, e **todo
clique responde** (toast, cópia ou link real) — protótipo mudo é protótipo
morto (lição 260914).

## DNA traduzido

| ref | o que entrou |
|---|---|
| Raycast | glow saturado roxo/rosa/azul do topo (`body::before`), título display com gradiente, chips de vidro |
| Duolingo | cores chapadas `#FF4B4B #58CC02 #1CB0F6 #FFC800` por setor, ícone em círculo, botões apertáveis (sombra dura que afunda no `:active`), mascote cérebro SVG com falas |
| Warp | número gigante amarelo, molduras `fig. 1/fig. 2` com legenda técnica mono, share-bar 96/3/1, spark de barras |

## Pontos de injeção pro gerador

- `data-slot="hero-status"` → pills + chips de estado (dados: PROGRESSO/estado.json)
- `data-slot="acoes-voce"` → passos do HANDOFF "PARA VOCÊ" (1 card por passo)
- `data-slot="saude-chips"` → testes/preflight/widget/lições
- `data-slot="fig-share"` → share por agente (barra-segmentos style)
- `data-slot="fig-spark"` → eventos por tipo (spark-barras style)
- `data-slot="anel-projetos"` + `data-slot="tabela-projetos"` → N/M em dia + details
- `.abas-resto` → panes que continuam no relatório oficial

Convenção de interação: `data-diz="…"` mostra toast; `data-copia="…"` copia
para a área de transferência (fallback `execCommand`, foco devolvido ao
origem); `<a href real>` navega E avisa. Toast constrói nós com
`textContent` (conteúdo do gerador nunca vira HTML). Chips/anel têm
`role="button"` + `tabindex="0"` + Enter/Espaço via delegação; botões nativos
com `type="button"`. Nunca entregar elemento clicável sem um dos três — nem
promessa que a página não cumpre (v1.1: pill diz "GERAÇÃO …" em vez de
"ATUALIZA 15s" falso; dropdown lista os 31 de verdade; abas usam fragmentos
`#acoes #skills #cerebro #docs #historico #painel` do relatório oficial).

## Como testar

Abrir em Chrome e conferir: cada botão copia/abre/avisa; `details` abre;
mascote fala (clique ou Enter); barra de leitura no topo cresce no scroll;
`prefers-reduced-motion` desliga animações.

## Estado (260914)

v1 aprovada visualmente pelo <USUARIO>; v1.1 corrige os 5 bloqueantes + 6
achados médios da revisão Codex Sol high (5/10 → retestado verde em todos:
7 data-slot reais, teclado em 8 controles, abas com fragmento, 31 linhas,
pill honesta, toast anti-XSS, type=button, reduced-motion com scroll).
Dívida para a adoção: hrefs `file:///` absolutos amarram ao disco S: — o
gerador resolve URLs relativas no momento de gerar. Relatório oficial
(`00_painel/RELATORIO.html`) segue intocado; adotar o POP lá é decisão do
<USUARIO> registrada em DECISOES 260914.
