---
name: megabrain
description: Protocolo de execução multi-agente — gates de entrega anti-slop, Duplo Diamante para projetos de design, roteamento de arquitetura (skill vs script vs subagente) e camada de projeto (fases macro, regras de ouro). Use quando o usuário digitar /megabrain, escrever "megabrain", pedir para "rodar no modo completo" ou "caprichar", abrir ou retomar um projeto com ESTADO.md/HANDOFF.md, passar trabalho de um agente para o outro, iniciar entrega complexa (proposta, deck, peça de cliente, relatório, código), pedir para revisar um prompt/brief/workflow, ou perguntar como evitar respostas genéricas de IA.
---

# megabrain — protocolo operacional (roteiro curto)

**v6.0 · 2026-08-24.** Base: v5.7. Mudou: a skill virou ROTEIRO (corte "tirar
peso", decisão 260824) — 1 passo por linha, detalhe profundo em `referencias/`,
aberto só quando o passo está em execução e há dúvida. Texto integral anterior:
`referencias/260824_skill-completa-v5.md` (nada foi perdido). Layout v7.0 da
central (memoria/ + 00_painel + 01_acoes). Modo único **otimizado**. Termo
oficial: **megabrain do projeto** (a pasta MEGABRAIN\ dentro de cada projeto).
"megabrian" = megabrain.

## Modo de operação (decisão 260824)

Modo único **otimizado**: melhor resultado sem gasto à toa. Tarefa mecânica /
varredura / extração → modelo equivalente que dá conta (Sonnet, Kimi, local
COMPROVADO). Julgamento, auditoria, decisão e entrega final → modelo de ponta —
que também DESENVOLVE quando a tarefa pede; revisar é só uma das funções dele.
Modelo local fraco gerando resposta: nunca, nem como fallback. Modos
leve/padrão: pausados (spec: `03_docs/260824_spec-fase2.md`).

Quando rodar gates: **entrega** (arquivo, peça, código, análise que sai da
conversa) = completo 0–7 · **rascunho/exploração** = leve 1·4·5 · **pergunta,
papo** = nenhum (rodar protocolo em papo é o próprio slop). Subir de leve pra
completo no meio é barato; descer não existe.

## Localizar a instalação

`<MEGABRAIN_ROOT>` = a central DESTE usuário. Procure: `MEGABRAIN/` dentro do
projeto → variável `MEGABRAIN_CENTRAL` → pasta com `VERSAO.txt` + `MEGABRAIN.md`
+ `bin/`. Central v7.0: `memoria/{nucleo,estado,identidade,cerebro,pendencias}`
· `00_painel` (RELATORIO.html) · `01_acoes` (.cmd que o humano clica) ·
`02_entrada` (fontes que o humano joga) · `03_docs` · `04_visuais` (acervo do
humano — nenhum script lê; a triagem dele É dado) · máquina na raiz: `bin dna
skills referencias modelos tests plugin-* gerenteneuron dist` · `_github/
{export,repo-local}`. Megabrains de projeto e centrais antigas são planos ou
numerados — sempre resolva caminho canônico via `bin/mb_utils.achar()`/`pasta()`,
nunca chumbe. Nunca escreva caminho absoluto de outro usuário. Mais de uma
central válida → pergunte qual.

## Gates — o roteiro

`0 assumir → 1 enquadrar → 2 orçar → 3 gerar → 4 auditar → 5 verificar → 6 bastão → 7 aprender`
Os dois que ninguém pula: **4** (separa entrega de slop) e **6** (o próximo
agente não começa do zero). Detalhe passo a passo, quando precisar:
`referencias/260810_gates-entrega.md`.

- **0 ASSUMIR** — 1º pedido da sessão: `python bin/mb-preflight.py --repo <ROOT>`.
  `git pull`. Ler `ESTADO.md → HANDOFF.md → fim de DECISOES.md → LICOES.md`
  (o que o hook já injetou, não reler). Trava: `TRAVADO_POR:` no HANDOFF —
  `bin/mb-sync.py` lock/release. Versão: `bin/mb-check-version.py --projeto <p>`
  (cria/atualiza o megabrain do projeto e o `cerebro/`; projeto mais novo que a
  central = parar e perguntar). Fonte que o usuário trouxe → `02_entrada` ou
  `cerebro/raw` + `/ingerir`. Output de outro agente = rascunho: audite antes
  de construir em cima. Caminhos e repos novos: confirmar com o usuário antes.
- **1 ENQUADRAR** — artefato e app de destino? leitor e decisão dele? 3 critérios
  verificáveis? restrição dura? contraexemplo genérico nomeado (o slop esperado)?
  Vago → perguntar antes (máx. 2). Design → Duplo Diamante, fase declarada no
  ESTADO, referência antes de adjetivo: `referencias/260810_design-projects.md`
  (+ `260810_galerias-referencia.md`, `260810_impeccable-routing.md` se vira código).
- **2 ORÇAR CONTEXTO** — orçamento compartilhado: ler sob demanda (Glob→Grep→
  trecho), checkpoint em .md, delegar varredura pro modelo barato, exemplos
  canônicos e não exaustivos; >85% de contexto → HANDOFF + commit + recomeçar.
  `referencias/260810_context-engineering.md`.
- **3 GERAR** — estrutura antes de prosa; uma afirmação por parágrafo; fato do
  mundo atual → buscar, nunca de memória; número/data/preço verificado ou
  `[ESTIMATIVA]`; específico > geral. WordPress/Figma/builders: o que o usuário
  tocou é versão final — mudança cirúrgica, nunca recriar sem avisar o custo.
- **4 AUDITAR** — reler e REESCREVER (anúncio sem mudança = teatro): léxico e
  estrutura banidos + testes de substância ("e daí?", troca de marca, trade-off,
  fonte) em `referencias/260810_anti-slop.md`; reescrever 30% menor e entregar a
  menor se nada se perdeu; peça visual → léxico visual banido (mesmo arquivo);
  material de outro agente → premissas verificadas? decisão não registrada?
  **1 reparo só** — se ainda está ruim, o erro é do Gate 1.
- **5 VERIFICAR** — abre no app? caminho existe (TESTAR, não confiar)? número
  recalculado? data conferida? contradiz DECISOES? Skill/protocolo/script:
  conferir a cópia CARREGADA (tamanho/data/hash) contra a fonte — repo limpo não
  prova skill atualizada. Alto risco → subagente verificador com contexto zero e
  rubrica: `referencias/260810_evaluation-gates.md`. Mexeu em `.md` → regenerar o
  relatório (`bin/mb-relatorio-vivo.py`) antes de entregar; relatório é UM por
  instância (RELATORIO.html), velho vai pra `90_arquivo/relatorios-antigos/`.
  Amarrar pontas antes de aprovação/envio/handoff: varrer dúvida aberta, número
  velho, prazo, decisão sem dono — levar ao usuário no máx. 5 perguntas com
  evidência + impacto + recomendação. Cliente/dinheiro/multi-IA →
  `referencias/260815_pipeline-governanca-aprendizado.md`.
- **6 PASSAR O BASTÃO** — esgotar execução autônoma antes de pedir qualquer coisa;
  reescrever ESTADO (5 linhas) e HANDOFF (feito · aberto · próximo passo com
  verbo e objeto · PARA VOCÊ · `TRAVADO_POR: livre`); DECISOES: append com a
  alternativa descartada. Git: commit local ok; push por ambiente — cloud com
  repo como fonte da sessão = push direto; cloud sem = commitar e apontar
  `01_acoes/260824_publicar-e-fotografar.cmd` e DEPOIS
  `01_acoes/260824_enviar-pro-github.cmd`; **git nunca pela pasta montada do
  bridge**. Central mudou → `bin/mb-check-version.py` nos projetos ativos;
  versão/commit mudou → regenerar o relatório vivo.
- **7 APRENDER** — tarefa não-trivial vira lição `GATILHO/LIÇÃO/ATALHO`, gravada
  direto (autorização permanente): vale em qualquer projeto → `memoria/nucleo/
  licoes-megabrain.md` · específica → `LICOES.md` do projeto. Fato de conteúdo
  (cliente, mercado, ferramenta) NÃO é lição: vai pro cérebro via `/ingerir`.
  Lição 3× → regra ou skill (`dna/licoes-recorrencia.json` marca sozinho).

## Visual: mecânica antes de CSS

Antes de escrever HTML/CSS: escolher uma mecânica pronta em `modelos/visuais/`
(`import mb_visual as v; v.render(id, dados)`; catálogo `modelos/visuais/
CATALOGO.md`). Cor sai do TEMA (`modelos/visuais/temas/`, cascata `:not()`
padrão Pico, nunca `!important`), não da mecânica — `#hex` solto em mecânica é
bug. ⚠️ Token de estado (`--ok/--warn/--signal`) ≠ hierarquia (rótulo/eyebrow =
`--ink-faint`). Falta peça → criar mecânica com cabeçalho `@mb-visual`, nunca
one-off. Planta do relatório é fixa (D/W/E/C/R; slot vazio não some).

## Multi-agente (resumo)

Barato/contexto grande: varredura, extração, leitura longa, 1ª passada, refactor
mecânico → entrega bruto + resumo. Julgamento: enquadrar, decidir, auditar,
texto final → entrega o artefato. É economia de token, não hierarquia. Trava e
bastão: HANDOFF + `bin/mb-sync.py` (status/lock/release).

## Precedência e roteamento

Formato pedido pelo usuário **vence** o protocolo (que governa conteúdo, não
estrutura). Roteamento: regra sempre viva → identidade/AGENTS.md (curto) ·
procedimento repetível → skill · garantia → hook/script em `bin/` · trabalho
barulhento → subagente/modelo barato · conhecimento pesado raro → `referencias/`
· estado entre sessões → `memoria/estado/` · conteúdo citável por path →
`cerebro/` (raw → `/ingerir` → wiki) · fases macro do projeto → `MEGABRAIN.md` ·
fora do sandbox (home, delete, SO) → `/kimi`
(`referencias/260811_kimi-handoff.md`). Skill/AGENTS = pedido; hook/script =
garantia. Arquitetura em detalhe: `referencias/260810_workflow-architecture.md`.

## Referências — abrir só quando o passo pedir

`260810_gates-entrega.md` gates em detalhe · `260810_anti-slop.md` léxico/
estrutura/substância banidos · `260810_metaprompt-patterns.md` + `-templates.md`
construir prompt/brief · `260810_context-engineering.md` contexto ·
`260810_workflow-architecture.md` skill×hook×subagente ·
`260810_design-projects.md` Duplo Diamante · `260810_galerias-referencia.md`
referência visual · `260810_impeccable-routing.md` UI que vira código ·
`260810_evaluation-gates.md` rubricas · `260810_PROMPT-PORTATIL.md` protocolo
sem skills · `260810_sync-memoria.md` identidade multi-agente ·
`260818_padrao-resposta.md` voz e níveis N0–N3 · `260811_kimi-handoff.md` parede
de sandbox · `260815_pipeline-governanca-aprendizado.md` cliente/dinheiro/
governança · `260824_skill-completa-v5.md` texto integral pré-corte.

## Como isso costuma dar errado (top 6)

Gate como teatro (anunciar ✅ sem reescrever) · pular o Gate 0 · handoff vago
("continuar o projeto" não é próximo passo) · herdar premissa do outro agente
sem verificar · loop de crítica além de 1 reparo · auditar o repo achando que
auditou a cópia carregada. Lista completa: `referencias/260824_skill-completa-v5.md`.
