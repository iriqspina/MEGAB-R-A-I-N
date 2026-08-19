---
name: megabrain
description: Protocolo de execução multi-agente — gates de entrega anti-slop, Duplo Diamante para projetos de design, roteamento de arquitetura (skill vs script vs subagente) e camada de projeto (fases macro, regras de ouro). Use quando o usuário digitar /megabrain ou /metaprotocolo, escrever "megabrain" ou "metaclaude", pedir para "rodar no modo completo" ou "caprichar", abrir ou retomar um projeto com ESTADO.md/HANDOFF.md, passar trabalho de um agente para o outro, iniciar entrega complexa (proposta, deck, peça de cliente, relatório, código), pedir para revisar um prompt/brief/workflow, ou perguntar como evitar respostas genéricas de IA.
---

# megabrain — protocolo operacional

**v5.0 · 2026-08-16.** Base: v4.9 do repositório. Mudou: numeração de gates
consistente com o TL;DR, modo leve/completo explícito, Gate 5 confere a cópia
que rodou, Gate 7 grava sob autorização permanente, `5b` virou `5.1`.

Protocolo multi-agente e agnóstico de modelo — roda igual em qualquer CLI ou
chat de IA com acesso a arquivo (Claude Code, Kimi CLI, ou colado direto
numa conversa via `referencias/260810_PROMPT-PORTATIL.md`).

**Estrutura:** este arquivo (gates de entrega + multi-agente),
`MEGABRAIN.md` (fases macro de projeto, artefatos, regras de ouro, níveis
de adoção) e `referencias/260810_*.md` (execução: anti-slop, metaprompts,
Duplo Diamante, roteamento de código, evaluation, prompt portátil).

Rode os gates abaixo em **entrega**: arquivo, peça, proposta, deck, código,
análise. Em pergunta rápida ou conversa casual, **não rode** — aqui o
protocolo é o próprio slop.

## Localizar a instalação do usuário

Antes de usar scripts, referências ou caminhos do MEGABRAIN, defina
`<MEGABRAIN_ROOT>` para **a instalação deste usuário**, nunca para a pasta de
quem criou o protocolo.

1. Procure, nesta ordem: `MEGABRAIN/` dentro do projeto atual; a variável de
   ambiente `MEGABRAIN_CENTRAL`; e uma pasta ancestral ou do workspace que
   contenha `VERSAO.txt`, `MEGABRAIN.md`, `bin/mb-check-version.py` e
   `referencias/`.
2. Se encontrar uma única pasta válida, diga o caminho encontrado e use-o em
   todos os comandos desta sessão.
3. Se houver mais de uma pasta válida, mostre as opções e peça para o usuário
   escolher. Não presuma qual cópia é a central.
4. Se não encontrar nenhuma, faça uma pergunta objetiva antes de continuar:
   **“Em qual pasta deste computador você salvou o MEGABRAIN? Cole o caminho
   da pasta raiz.”** Depois valide os quatro itens acima. Se ele ainda não o
   instalou, pergunte onde quer salvá-lo e oriente somente os passos de
   instalação compatíveis com o ambiente dele.

Nunca escreva uma letra de unidade, caminho absoluto pessoal ou pasta de outro
usuário no protocolo. Depois de resolvido, substitua exemplos como
`<MEGABRAIN_ROOT>/bin/mb-sync.py` pelo caminho local confirmado.

## TL;DR

`0 assumir → 1 enquadrar → 2 orçar contexto → 3 gerar → 4 auditar (+1 reparo) → 5 verificar e amarrar pontas → 6 passar o bastão → 7 registrar`

Os dois que ninguém pula: **4 (auditar)** separa entrega de slop; **6
(bastão)** impede o outro agente de começar do zero.

## Modo leve × modo completo

Escolha antes de começar e diga qual escolheu — protocolo rodado por reflexo
custa contexto e não melhora nada.

| | Quando | Gates |
|---|---|---|
| **Leve** | resposta única, rascunho interno, exploração, nada sai da conversa | 1 · 4 · 5 |
| **Completo** | vai para cliente, para produção, para o repo, ou outro agente continua | 0 a 7 |
| **Nenhum** | pergunta rápida, papo, dúvida factual | — |

Subir de leve para completo no meio é permitido e barato. Descer não: se o
material já saiu, ele já saiu.

---

## 0. Gate ASSUMIR — multi-agente

Antes de tocar em qualquer arquivo de `projetos/<nome>/`:

1. `git pull`
2. Leia nesta ordem: `ESTADO.md` → `HANDOFF.md` → o fim de `DECISOES.md` →
   `LICOES.md`. **Não varra a árvore antes disso.**
3. Cheque a trava em `HANDOFF.md`:
   - `TRAVADO_POR:` é o outro agente **e** `ATÉ:` no futuro → não escreva nos
     caminhos em `ESCOPO:`. Trabalhe em outro lugar ou avise quem opera.
   - Trava vencida ou `livre` → assuma: escreva seu nome, `ATÉ:` agora+2h,
     `ESCOPO:` com os caminhos que você vai tocar.
4. **Verifique a versão do megabrain** do projeto contra a central:
   - Rode `python "<MEGABRAIN_ROOT>/bin/mb-check-version.py" --projeto <pasta-do-projeto>`.
   - Se o projeto não tiver `MEGABRAIN/`, o script cria da central — use a central.
   - Se a central for mais nova: o script sincroniza automaticamente para o projeto.
   - Se o projeto for mais novo: o script avisa e sai com código 2. **Pare e pergunte ao usuário** se deve subir as mudanças para a central (`mb-sync-projeto-para-central.py`) ou manter o projeto local.
   - Se indefinido: pergunte antes de sobrescrever.
   - **Nunca use um megabrain de projeto desatualizado sem sincronizar primeiro.**
5. **Confirme caminhos relevantes no início do projeto.** Antes de criar repos, subir arquivos ou pedir credenciais, valide com o usuário onde cada artefato deve morar (local, pasta compartilhada, GitHub privado/público, etc.). Não suba nada para Git sem confirmação explícita, a menos que ele já tenha autorizado permanentemente para aquele repo.
6. Só então planeje.

Script que torna a trava garantia, e nao disciplina de markdown:

```
python bin/mb-sync.py --dir <projeto> status
python bin/mb-sync.py --dir <projeto> lock --agente <seu-nome> --escopo caminho/ [--horas 2]
python bin/mb-sync.py --dir <projeto> release --agente <seu-nome>
```

`status` sai com codigo 0 (livre, pode escrever) ou 1 (travado por outro).
`release` recusa liberar trava alheia dentro do prazo; `--force` existe, mas e
decisao consciente.

**Output do outro agente é rascunho, não verdade.** Se você está retomando
trabalho de outro agente, audite antes de construir em cima. O erro caro do
pipeline multi-agente é herdar uma premissa errada e ampliá-la por três
etapas.

### Divisão de trabalho entre agentes (default sugerido)

| | Agente de contexto grande / custo baixo | Agente de julgamento / síntese | Agente de fallback (opcional) |
|---|---|---|---|
| Recebe | varredura, extração, leitura longa, boilerplate, refactor mecânico, primeira passada | enquadramento, decisão de design, auditoria, texto final, entrega final | o que os outros dois fariam — sem papel fixo |
| Entrega | material bruto + resumo | artefato pronto | mesmo padrão dos gates de quem está substituindo |

Não é hierarquia, é economia de token. Inverta quando fizer sentido pro
projeto. Um terceiro agente sem setup dedicado entra só como fallback —
mesmos arquivos de estado, mesmo Gate 0, sem versão separada do
protocolo.

---

## 1. Gate ENQUADRAR — antes de qualquer token de output

Responda internamente. Se algo estiver vago, **pergunte antes de produzir**
(máx. 2 perguntas objetivas).

1. **Artefato** — qual o objeto final e em que app ele é aberto? (.pptx,
   .fig, .md, código, imagem)
2. **Leitor** — quem consome e que decisão essa pessoa toma depois de
   ler/ver?
3. **Critério de aprovação** — escreva 3 critérios verificáveis *antes* de
   gerar.
4. **Restrição dura** — prazo, formato, marca, tom, limite técnico.
5. **Contraexemplo** — como seria a versão óbvia e genérica disso? Nomeie.
   Você vai evitá-la.

> Item 5 é o truque mais barato do kit. Nomear o slop esperado reduz a
> chance de produzi-lo.

### 1b. Se for projeto de design

Antes de tudo: **o projeto já tem um router/comando próprio** (uma skill que
já sabe em que fase o projeto está)? Use-o em vez de aplicar o Duplo
Diamante genérico na mão.

Se não houver, declare **em qual fase do Duplo Diamante** você está — e não
misture os modos:

```
◇ 1 Pesquisa (divergir) → 2 Análise (convergir) ◇ 3 Ideação (divergir) → 4 Design (convergir) ◇
```

- Julgar durante a divergência mata as ideias boas; divergir durante a
  convergência impede a decisão.
- Não passe da fase 2 sem enunciar o problema numa **frase falseável**.
- Fidelidade proporcional à certeza. Alta fidelidade cedo compra
  comprometimento emocional e trava a exploração.
- Trave grade, escala tipográfica (máx. 5 passos), paleta (máx. 3 famílias +
  neutros) e espaçamento **antes** de compor.
- Stage gates: fim da fase 2 (problema definido) e fim da fase 4 (solução
  final). Não antes.
- **Referência antes de adjetivo.** Como montar e usar a biblioteca:
  `referencias/260810_galerias-referencia.md` — só nas fases divergentes
  (1 e 3).
- **Se o artefato final vira código** (landing, app UI, componente), o
  Estágio 4 sai daqui: `referencias/260810_impeccable-routing.md`. Pixel e
  papel continuam neste protocolo.

Roteiro dos 4 estágios: `referencias/260810_design-projects.md`

**Fase do Duplo Diamante entra no `ESTADO.md`.** É o campo que evita o outro
agente reabrir uma fase já fechada.

---

## 2. Gate ORÇAR CONTEXTO

Contexto é orçamento, não depósito. Num pipeline de dois agentes, é
orçamento **compartilhado**: o que você queima é contexto que o outro não
terá.

- **Leia sob demanda.** Nunca despeje repositório/pasta inteira. Glob →
  Grep → Read do trecho.
- **Checkpoint em arquivo.** Tarefa longa: escreva estado/decisões num
  `.md`. Contexto longo degrada (context rot); o arquivo não.
- **Delegue o barulho.** Varredura, coleta, leitura ampla → subagente ou o
  outro modelo. Receba só a conclusão.
- **Ferramenta mínima viável.** Se você não consegue dizer com certeza qual
  ferramenta usar, o conjunto está inchado.
- **Exemplos canônicos, não exaustivos.** 2–3 representativos batem 15 casos
  de borda.
- Acima de ~85%: escreva `HANDOFF.md`, commite e recomece. Não tente
  terminar no fio.

Detalhe: `referencias/260810_context-engineering.md`

---

## 3. Gate GERAR

- Estrutura antes de prosa. Esqueleto → preencher.
- Uma afirmação por parágrafo.
- Toda alegação factual sobre o mundo atual → **buscar antes**, nunca de
  memória (preços, cargos, versões, leis, datas).
- Números, datas, preços: verificados ou marcados `[ESTIMATIVA]`.
- Específico > geral. "Reduz 40% do tempo de export" > "melhora a
  eficiência".

### 3b. WordPress / builders: preserve o que o usuário tocou

Se o usuário editou algo no editor visual (WordPress, Figma, Webflow, etc.),
esse estado é a versão final dele — não um rascunho para ser refeito.

- **Nunca use `resetBlocks`, re-criar do zero ou sobrescrever o arquivo**
  sem avisar o que vai perder.
- Preservar: nomes de blocos, classes custom, content width/container,
  estilos inline do painel, ordem manual, metadados de layout.
- Mudanças devem ser cirúrgicas: atualizar só os atributos que precisam
  mudar (`updateBlockAttributes`), manipular `post_content` preservando o
  resto, ou usar hooks/filtros.
- Se for inevitável reconstruir, liste ao usuário o que será perdido e
  peça confirmação. Depois, restaure metadados e configurações de layout.

---

## 4. Gate AUDITAR — anti-slop (obrigatório)

Releia o que gerou e **reescreva**. Listas completas:
`referencias/260810_anti-slop.md`

### 4.1 Léxico
Se apareceu, reescreva a frase inteira (não troque o sinônimo — a frase era
vazia):

EN: `delve, tapestry, testament to, ever-evolving landscape, navigate the
complexities, unlock, harness, leverage, robust, seamless, game-changer,
elevate, empower, cutting-edge, revolutionize, holistic, synergy, myriad,
plethora, meticulous, crucial, pivotal, underscores, realm, beacon, curated,
streamline, transformative, foster`

PT: `no mundo de hoje, no cenário atual, cada vez mais, de forma eficaz, é
importante ressaltar, vale destacar, em suma, nesse sentido, dessa forma,
por fim, revolucionar, potencializar, alavancar, robusto, impactante,
entregar valor, jornada (vazio), ecossistema (vazio), curadoria (vazia), de
forma holística, sinergia, disruptivo, imersivo, solução completa, ponta a
ponta`

### 4.2 Estrutura
- ❌ "Não é apenas X — é Y" (antítese oca)
- ❌ Regra de três compulsiva ("rápido, simples e poderoso")
- ❌ Travessão como muleta de ritmo (máx. 1 a cada 3 parágrafos)
- ❌ Parágrafo final que repete o que acabou de ser dito
- ❌ Bullets `**Rótulo:** frase` **quando é reflexo, não escolha** — ver
  seção 8
- ❌ Abrir reafirmando a pergunta do usuário
- ❌ Fechar com "Me avise se quiser..." / "Espero que ajude!"
- ❌ Hedge empilhado ("pode potencialmente às vezes") — escolha o grau de
  certeza e assuma
- ❌ Todos os parágrafos com o mesmo comprimento
- ❌ Conectivo mentiroso: se remover "além disso" não muda o sentido, ele
  fingia uma relação lógica

### 4.3 Substância
- **"E daí?"** — remova o parágrafo. A peça perdeu algo? Se não, corte.
- **Substituição de marca** — troque o cliente pelo concorrente. Ainda faz
  sentido? Então é sobre a categoria. Especifique.
- **Trade-off** — toda recomendação declara o que custa? Sem contrapartida
  é folheto de vendas.
- **Fonte** — todo número, data, preço, cargo, versão é verificado ou
  rotulado `[ESTIMATIVA]`?

### 4.4 Compressão
Reescreva 30% menor. Se nada essencial se perdeu, **entregue a versão
menor.** Slop comprime sem perda; argumento denso resiste.

### 4.5 Se for peça visual
Léxico visual banido: gradiente roxo→azul · mesh gradient sem motivo ·
glassmorphism não motivado · Inter/Poppins/Montserrat como default sem
justificativa · radius 8px em tudo · drop shadow em tudo · foto de banco
com gente apontando pra laptop · grid de 3 cards ícone+headline+3 linhas ·
dashboard fake · tudo centralizado · isométrico genérico · mockup de
iPhone flutuando em 3/4.

Testes: print sem logo (dá pra saber de quem é?) · hierarquia em 3 segundos
· contraste WCAG AA (4.5:1 / 3:1) · toda decisão visual tem motivo
declarável.

### 4.6 Auditoria cruzada (só multi-agente)
Quando o material veio do outro agente, some estes:
- A premissa de partida foi **verificada** ou herdada de confiança?
- Alguma afirmação factual chegou sem fonte e sem `[ESTIMATIVA]`?
- O outro agente decidiu algo que deveria estar em `DECISOES.md` e não
  está? Registre agora.

### Reparo
**Uma rodada, limitada.** Loop de autocrítica sem limite converge para uma
média homogênea — corrige slop léxico e introduz slop estrutural. Se após 1
reparo ainda está ruim, o problema é o enquadramento (Gate 1), não a
redação.

---

## 5. Gate VERIFICAR

- Arquivo abre no app de destino? Formato correto? Convenção de nome
  consistente com o resto do projeto?
- Links e caminhos existem? **Teste o caminho, não confie na citação.**
- Números conferem (recalcule, não copie)?
- Datas conferidas contra hoje?
- Contradiz algo já registrado em `DECISOES.md`?

**Se o que você auditou é um protocolo, skill, plugin ou script versionado:**
confira o arquivo que o agente **realmente carregou** — tamanho, data e hash —
contra a fonte no repositório. Repo limpo não prova protocolo funcionando; a
cópia instalada pode ter meses de deriva. Este gate existe porque essa falha
já aconteceu com o próprio megabrain.

Alto risco (cliente, dinheiro, prazo público): delegue a verificação a um
subagente — ou **ao outro modelo** — passando **só o artefato e a rubrica**,
sem o histórico. Contexto zero é a característica útil, não a limitação.

Rubricas prontas: `referencias/260810_evaluation-gates.md`

### 5.1 Amarrar pontas — antes de qualquer coisa sair

### Relatório único por projeto

Se a instância tiver `RELATORIO.html`, trate-o como a porta de entrada de
usuário e IA. Ao criar ou alterar informação em `.md`, regenere o relatório
antes de entregar. O Markdown continua sendo a fonte da verdade: não crie outro
relatório nem um Markdown duplicado para "resumir" o que já existe. Use
`bin/mb-relatorio-projeto.py`; por padrão ele reúne todos os `.md` informacionais
da instância e deixa só `MEGABRAIN/`, `.git/`, caches e dependências de fora.

Antes de uma aprovação humana, envio externo, fechamento semanal ou handoff,
varra estado, tracker, decisões e fontes por dúvida aberta, número velho,
prazo, dependência e decisão sem dono. Descubra sozinho o que for leitura
segura; leve ao usuário no máximo cinco perguntas prioritárias, cada uma com
evidência, impacto e recomendação.

Se houver cliente, dinheiro, multi-IA, Contraditor, Teammates ou dogfooding,
carregue `referencias/260815_pipeline-governanca-aprendizado.md`. O recurso
mais barato capaz vem primeiro; escalar exige falha observada ou alto custo
do erro. Toda comunicação, proposta, preço e entrega continua sob aprovação
humana.

## 6. Gate PASSAR O BASTÃO

Antes de encerrar a sessão, sempre. Não é opcional e não é resumo bonito —
é o insumo do próximo agente.

1. **Esgote execução autônoma antes de qualquer pedido ao usuário.** Se a
   skill `/conclusao-megabrain` estiver instalada nesta máquina, rode. Se não
   estiver — ela não faz parte deste pacote —, faça o equivalente na mão:
   liste o que falta, resolva sozinho tudo que for automação local ou
   ferramenta já logada, e leve ao usuário só o que depende dele, agrupado
   numa pergunta só.
2. Reescreva `ESTADO.md` (5 linhas, sobrescreve).
3. Reescreva `HANDOFF.md`: o que fez, o que ficou aberto, o próximo passo
   concreto, arquivos tocados, e `TRAVADO_POR: livre`.
4. Anexe a `DECISOES.md` toda decisão tomada **com a alternativa
   descartada**. Decisão sem alternativa registrada volta a ser
   rediscutida daqui a duas semanas.
5. Git:
   - `git add -A && git commit -m "<agente>: <o que mudou>"` (commit local pode ser automático).
   - **Antes de `git push`, confirme com o usuário.** Não suba prioritariamente; só empurre se ele aprovar ou se já tiver autorização explícita permanente para este repo.
   - Se este trabalho alterou arquivos em `<MEGABRAIN_ROOT>/`, rode `python "<MEGABRAIN_ROOT>/bin/mb-sync-projeto-para-central.py" --projeto <pasta-do-projeto>` para subir a versão do projeto para a central, ou deixe claro no `HANDOFF.md` que a central ficou mais nova e os projetos devem sincronizar no próximo `Gate 0`.
6. **Propagação do megabrain core:**
   - Se você alterou `<MEGABRAIN_ROOT>/skills/megabrain/SKILL.md`, `MEGABRAIN.md`, `referencias/` ou `VERSAO.txt`, a central ficou mais nova que os projetos.
   - Antes de encerrar, rode `mb-check-version.py` nos projetos ativos para propagar a versão central. Se um projeto estiver mais novo, pare e pergunte ao usuário antes de sobrescrever.
   - Se não puder rodar nos projetos, anote no `HANDOFF.md` que a sincronização é obrigatória na próxima sessão.

Um handoff que diz "continuar o projeto" não é handoff. Próximo passo tem
verbo e objeto.

---

## 7. Gate APRENDER

Ao fim de tarefa não-trivial, escreva a entrada. Se o dono desta instalação
já deu autorização permanente para registrar lições, **grave direto** — não
pergunte "quer que eu registre?", porque a pergunta custa mais que a linha.
Sem autorização declarada, apresente a entrada pronta e peça só o "ok".

```
## YYMMDD — <contexto em até 5 palavras>
GATILHO: quando essa situação reaparece
LIÇÃO: o que deu errado ou foi descoberto
ATALHO: o que fazer direto da próxima vez
```

Dois destinos: **global** (vale pra qualquer projeto) ou **do projeto**
(`projetos/<nome>/LICOES.md` — específica de um cliente/produto). Regra:
*seria útil num projeto completamente diferente?* Sim → global. Não →
projeto. Sempre **append**, nunca reescreva.

Lição 3× vira skill própria ou regra em `MEGABRAIN.md`.

Se o usuário declarou que uma classe de mecânica deve sempre alimentar o
MEGABRAIN, promova a versão sanitizada para a fonte central no mesmo ciclo;
não deixe apenas como nota do projeto.

---

## 8. Precedência de formato

**Formato que o usuário pediu explicitamente vence este protocolo.** O
protocolo governa o **conteúdo** dentro das seções, nunca a estrutura
delas. Ordem: **formato pedido > protocolo > default do modelo.**

---

## 9. Roteamento de arquitetura

| Preciso de... | Use |
|---|---|
| Regra que vale em toda sessão, nos dois agentes | `AGENTS.md` (curto — custa contexto sempre) |
| Procedimento repetível sob demanda | Skill dedicada |
| Router de projeto (já sabe a fase, o estado) | Skill/comando do próprio projeto |
| Trabalho barulhento sem sujar contexto | Subagente, ou o outro modelo |
| Garantia determinística (não "pedido") | Hook / script |
| Conhecimento pesado e raro | Referência em `referencias/260810_*.md`, sob demanda |
| Estado que atravessa sessões e modelos | `ESTADO.md`, `HANDOFF.md`, `DECISOES.md`, `LICOES.md` |
| Fases macro do projeto, artefatos, regras de ouro | `MEGABRAIN.md` |
| Ação que o sandbox conectado não alcança (pasta home, caminho fora do que foi conectado, delete/rename bloqueado, ação de SO) | `/kimi` — Kimi CLI roda local, sem sandbox (`referencias/260811_kimi-handoff.md`) |

⚠️ `AGENTS.md` e skills são **pedidos, não garantias**. Se algo precisa
acontecer sempre e sem falha, é hook ou script.

Detalhe: `referencias/260810_workflow-architecture.md`

---

## 10. Referências (carregue sob demanda)

Todas em `referencias/`.

| Arquivo | Quando ler |
|---|---|
| `260810_gates-entrega.md` | Versao longa dos gates deste arquivo (camada micro, entrega a entrega) |
| `260810_anti-slop.md` | Escrita, copy, qualquer texto entregue |
| `260810_metaprompt-patterns.md` | Construir/refinar prompt ou brief |
| `260810_metaprompt-templates.md` | Templates T1–T8 prontos |
| `260810_context-engineering.md` | Tarefa longa, muitos arquivos, agente |
| `260810_workflow-architecture.md` | Decidir skill vs subagente vs hook |
| `260810_design-projects.md` | Projeto visual/design (Duplo Diamante) |
| `260810_galerias-referencia.md` | Direção visual concreta (Estágios 1 e 3) |
| `260810_impeccable-routing.md` | A entrega é interface que vira código |
| `260810_evaluation-gates.md` | Definir rubrica e avaliar output |
| `260810_PROMPT-PORTATIL.md` | Levar o protocolo pra uma IA sem skills |
| `260810_sync-memoria.md` | Configurar agente novo num projeto — sincronizar identidade em CLAUDE.md/GEMINI.md/AGENTS.md |
| `260818_padrao-resposta.md` | Forma de responder — voz, níveis de detalhe N0–N3, entendimento de projeto, ações; contrato único propagado a todos os agentes |
| `260811_kimi-handoff.md` | Tarefa bateu numa parede do sandbox (pasta home, caminho não conectado, delete/rename bloqueado) — empacotar pro Kimi |
| `260815_pipeline-governanca-aprendizado.md` | Cliente, dinheiro, aprovações, Amarrador, Contraditor, Teammates, momentum ou aprendizado entre projetos |

Painel de leitura e atalhos (todos os arquivos acima, com hash e botões de
comando): `PAINEL-MEGABRAIN.html`, gerado por `bin/mb-painel.py`. Serve o
humano, não o agente — o agente continua lendo os `.md` sob demanda.

Camada de projeto (fases macro, artefatos, regras de ouro, níveis de
adoção): `MEGABRAIN.md`. O arquivo de identidade que essa sincronização
usa como fonte é local ao seu projeto — nunca faz parte deste pacote.

---

## Como isso costuma dar errado

1. **Rodar os gates como teatro.** Anunciar "✅ auditoria concluída" sem
   reescrever nada. O gate só existe se o texto mudou.
2. **Pular o Gate 0.** Começar a trabalhar sem ler `ESTADO.md` é como o
   outro agente nunca tivesse existido. Todo o ganho do pipeline evapora
   aqui.
3. **Handoff vago.** "Continuar de onde parei" obriga o próximo agente a
   reconstruir contexto do zero — mais caro que ter feito tudo num modelo
   só.
4. **Confiar no output do outro modelo.** Premissa errada herdada e
   ampliada por três etapas é o modo de falha caro do multi-agente.
5. **Loop de crítica infinito.** Passa de 1 reparo, vira mingau homogêneo.
6. **Atropelar o formato do usuário.** Ver seção 8 — o formato dele vence.
7. **Confundir conciso com raso.** Anti-slop corta enchimento, não
   argumento. A compressão de 30% é sobre palavras.
8. **Aplicar em conversa casual.** O protocolo é pra entrega.
9. **Os dois agentes na mesma hora sem trava.** Merge conflict em `.md` é
   chato; em arquivo binário, é perda de trabalho. Respeite `TRAVADO_POR`.
10. **`DECISOES.md` reescrito.** É append-only. Reescrever apaga o registro
    de por que a alternativa foi descartada.
11. **Auditar o repo e achar que auditou o protocolo.** A cópia que o agente
    carregou pode ser outra, mais velha, com caminhos mortos. Confira hash e
    data antes de julgar — ver Gate 5.
12. **Duas cópias do mesmo arquivo tratadas como duas fontes.** Duplicata
    byte a byte hoje é fork silencioso na primeira edição. Uma fonte, o
    resto é cópia gerada.
