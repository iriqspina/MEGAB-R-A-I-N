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

Slots no CONTEÚDO (nunca no setor inteiro — o gerador substitui o dado,
o cabeçalho e os controles ficam):

- `hero-status` → pill + sub + frescor do header
- `orc-gates` → trilha de gates da ÚLTIMA RUN FORMAL IDENTIFICADA (com legenda dizendo qual)
- `orc-runs` → cards de run (estado preciso: "REVISÃO APROVADA" ≠ entrega; evidência copiável)
- `orc-cotas` → cotas com DATA da leitura e fonte (fotografia, não "ao vivo")
- `acoes-voce` → passos do HANDOFF "PARA VOCÊ"
- `saude-chips` → medidores de saúde
- `anel-projetos` / `tabela-projetos` → resumo N/M + tabela de cópias
- `telemetria-geral` (details) → envolve `fig-share` e `fig-spark`
- `pane-acoes` / `pane-skills` / `pane-cerebro` / `pane-docs` → panes locais
  (EXCEÇÃO EXPLÍCITA à navegação antiga por abas do relatório oficial:
  aqui o conteúdo vive no mesmo arquivo e design, sem pular de pele)

Convenção de interação: `data-diz="…"` mostra toast; `data-copia="…"` copia
para a área de transferência (fallback `execCommand`, foco devolvido ao
origem); `<a href real>` navega E avisa. Toast constrói nós com
`textContent` (conteúdo do gerador nunca vira HTML). Chips/anel têm
`role="button"` + `tabindex="0"` + Enter/Espaço via delegação; botões nativos
com `type="button"`. Nunca entregar elemento clicável sem um dos três — nem
promessa que a página não cumpre (v1.1: pill diz "GERAÇÃO …" em vez de
"ATUALIZA 15s" falso; dropdown lista os 31 de verdade; abas usam fragmentos
`#acoes #skills #cerebro #docs #historico #painel` do relatório oficial).

## Tema claro (opção · 260915)

v1.3: o template carrega os DOIS temas embutidos (escuro = default; claro por
`html[data-tema="claro"]`). O botão "Tema:" no header alterna sem recarregar e
salva a escolha (`localStorage['megabrain.pop.tema']`); preferência salva válida
vence o tema do arquivo; sem JS o botão fica visivelmente desabilitado e o
relatório segue legível. Paleta clara própria (contraste AA medido, mín. 5.7:1
nos textos reais) — não é filtro invertido. A fonte das definições nos geradores
é `bin/mb_pop_tema.py`; este template carrega cópia espelhada (o teste
`motor/tests/test_mb_relatorio_pop_tema.py` impede divergência).

## Como testar

Abrir em Chrome e conferir: cada botão copia/abre/avisa; `details` abre;
mascote fala (clique ou Enter); barra de leitura no topo cresce no scroll;
`prefers-reduced-motion` desliga animações. Tema: botão do header alterna,
recarregar mantém a escolha; prova funcional completa com
`node bin/mb-verificar-pop-tema.mjs <html>`.

## Estado (260914)

v1 aprovada visualmente pelo <USUARIO>; v1.1 corrige os 5 bloqueantes + 6
médios da revisão Codex Sol high. **v1.2** (pedido do <USUARIO>: "tá enorme
e não fala das orquestrações"): setor ORQUESTRAÇÕES protagonista (gates da
run identificada, runs com estado preciso, cotas com data da leitura,
papéis por modelo), página encolhida (hero compacto, saúde+cópias fundidos
no setor ESTADO DA CENTRAL com details, telemetria rebaixada), e as abas
Ações/Skills/Cérebro/Documentos viram PANES neste mesmo design — fim da
incoerência com o relatório oficial antigo. Correções orquestradas pelo
Astra low (8 itens P1/P2) aplicadas e retestadas.
Dívida para a adoção: hrefs `file:///` absolutos amarram ao disco S: — o
gerador resolve URLs relativas no momento de gerar. Relatório oficial
(`00_painel/RELATORIO.html`) segue intocado; adotar o POP lá é decisão do
<USUARIO> registrada em DECISOES 260914.
