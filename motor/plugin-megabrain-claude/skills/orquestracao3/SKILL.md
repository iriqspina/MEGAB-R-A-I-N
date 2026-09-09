---
name: orquestracao3
description: Camada opcional sobre /orquestracao1 para entrega com risco material de plano incompleto — dois pontos de ponta assimétricos (orquestrador decide, adversário cross-vendor só aponta lacuna), política de modelo/effort por papel calculada a partir do consumo real (não escolhida no meio da tarefa), e plano de execução tipado (PLANO.json) com fechamento de grafo contra o git. Use quando o usuário digitar /orquestracao3, pedir "modo maratona", pedir orquestração com adversário/segundo orquestrador, ou quando o plano de uma entrega grande precisar ser verificável em vez de prosa.
---

# orquestracao3 — orquestracao1 com dois pontos de ponta e política calculada

**v0.1 · 260906.** Não substitui `/orquestracao1`: acrescenta três coisas por
cima do mesmo contrato (um orquestrador único, workers paralelos, grelha
opcional, lentes `/hypadododiabo`/`/advogadododiabo`). Chamada só por
invocação — não altera hook nem roteiro sempre-ativo do `/megabrain` core.
Origem: sessão de design em `motor/referencias/260906_orquestracao-3.md` e
`260906_modo-maratona.md`; instalado e corrigido nesta sessão (260906) porque
o pacote original assumia layout de central (`VERSAO.txt`/`MEGABRAIN.md` na
raiz, arquivos em subpastas) que não bate com o layout real desta central
(`motor/` + `memoria/estado/` + `bin/`, arquivos soltos).

## Quando usar em vez de só `/orquestracao1`

- Entrega com risco material de **plano incompleto** — muitos arquivos,
  migração, refactor arquitetural — onde "esqueceu um caso" custa caro.
- Sessão longa (janela de 5h) em que você quer o **modo maratona**: dois
  papéis de ponta reservados o tempo todo, sem precisar acompanhar quota.
- Quando o plano precisa ser **dado verificável** (JSON com schema), não
  prosa que esconde buraco.

Tarefa pequena, N0, ou entrega sem risco material: `/orquestracao1` sozinho
(ou nada) continua sendo o default. Esta camada é peso extra, não teto.

## O que muda em relação a `/orquestracao1`

1. **Dois pontos de ponta, não um.** O `orquestrador` decide; um segundo
   papel, `adversário`, de outro fornecedor, só aponta o que falta no plano
   — nunca propõe solução. Um modelo auditando o próprio plano tem viés de
   completude; o segundo, com papel invertido, não tem.
2. **A política de modelo/effort é calculada, não escolhida.**
   `python bin/mb-orcamento.py --json > memoria/estado/politica.json` no
   início da sessão (rodar manualmente — ver "Hooks opcionais" abaixo).
   Todo papel usa o par `(modelo, effort)` que está em `politica.json`;
   ninguém escolhe modelo no meio da tarefa.
3. **Plano vira dado.** A saída do enquadramento passa a validar contra
   `motor/modelos/plano/PLANO.schema.json`, com as 15 chaves de
   `motor/modelos/plano/260906_checklist-cobertura-v1.md` respondidas.
   `na` sem justificativa (`nota`) não passa do gate.

## Papéis

| Papel | Onde entra | Modelo/effort | Trava |
|---|---|---|---|
| `talker` | recebe o pedido, decompõe, reporta | `politica.json.papeis.talker` | mid-tier — roda em toda mensagem |
| `orquestrador` | enquadra, delega, julga | `politica.json.papeis.orquestrador` | ponta — nunca degrada abaixo de Opus 5/Fable |
| `adversário` | só aponta lacuna no plano, antes da execução | `politica.json.papeis.adversario` | ponta, sempre no **Codex** — quota separada, cross-vendor |
| `worker` | execução, em worktree | `politica.json.papeis.worker` | barato, effort baixo por desenho |
| `revisor` | gate de merge / revisão do candidato final | `politica.json.papeis.revisor` | cross-vendor do lado oposto a quem gerou (é o mesmo papel do Fable/Kimi de `/orquestracao1`, com o Codex como par default) |

Invariante do **modo maratona**: sob pressão de quota (fase `vermelho` em
`politica.json`) corta-se **escopo** — `fanout_max` cai, effort de
worker/talker cai — nunca **verificação**. `orquestrador` e `adversário`
nunca somem, só perdem effort (`high`→`medium`).

## Fluxo — encaixe nos passos de `/orquestracao1`

- **Antes do passo 0 (identidade/estado)** — rodar
  `python bin/mb-orcamento.py --json > memoria/estado/politica.json`
  (ou só `python bin/mb-orcamento.py` pra ler a fase em texto). Isso
  substitui a resolução manual do 0A pelos pares já calculados.
- **Passo 2 (fixar o problema)** — a saída não é mais prosa: preencher
  `PLANO.json` no schema de `motor/modelos/plano/PLANO.schema.json`. Cada
  item leva `id`, `arquivos_alvo` (caminho real — `?` é proibido), `dono`,
  `criterio_de_pronto` (verificável, ≥15 chars, nada de "funciona bem"),
  `risco`, `depende_de` (resolvendo pra um `id` que existe no plano). A
  seção `cobertura` responde as 15 chaves com `status` + `nota` por chave.
- **Antes do passo 5 (candidato final)** — rodar o **adversário**: Codex
  recebe o plano já preenchido com o prompt de papel invertido ("não
  melhore este plano, ache o que falta nele"), mínimo 5 lacunas em
  `lacunas_adversario`. Lacuna `bloqueante` com `resolucao: recusada` exige
  linha em `DECISOES.md` — é o único caminho do plano sair do gate.
- **Depois da execução, antes de apresentar** — rodar
  `python bin/mb-fechamento-grafo.py` (lê `PLANO.json` da sessão e
  `git status --porcelain`). Divergência — arquivo tocado fora do plano,
  ou item declarado e não tocado — é falha de **planejamento**, gravada em
  `falhas.jsonl`. Não editar o resultado pra empatar: registrar e levar ao
  <USUARIO>.
- **Gate 7 / aprender** — toda omissão real que escapou vira linha nova em
  `motor/modelos/plano/260906_checklist-cobertura-v1.md`. É esse loop que
  faz a ausência de item convergir a ~0, não o tamanho do modelo.

## Hooks opcionais (não instalados por padrão)

Esta skill roda por invocação — não altera `~/.claude/settings.json`. Se
quiser o cálculo automático toda sessão (`SessionStart`) e o fechamento de
grafo automático a cada subagente (`SubagentStop`), o bloco pronto está em
`motor/referencias/260906_patch-skill-v6.1.md` (seção 4). **Antes de
instalar**: confirmar se o Claude Code deste ambiente expande
`%MEGABRAIN_CENTRAL%` dentro do campo `command` do hook — se não expandir,
trocar pelo caminho absoluto da central nesse `settings.json` **local**
(nunca versionar caminho absoluto em arquivo compartilhado).

## Limites honestos

- **Não existe endpoint oficial de quota do Max.** `bin/mb-orcamento.py` lê
  os transcripts locais (`~/.claude/projects/**/*.jsonl`), mesma técnica do
  `ccusage`. Os tetos em `~/.megabrain/orcamento.json` são chute inicial —
  o teste desta instalação (260906) devolveu 373% do semanal e 324% do
  frontier com os valores padrão. **Calibrar contra `/usage` na primeira
  semana é obrigatório**, senão a fase (verde/amarelo/vermelho) é painel
  bonito medindo nada. Pendência aberta, não resolvida por esta instalação.
- Consumo via Codex sai de outra bolsa e não aparece nesses transcripts —
  a fase calculada só enxerga o lado Claude.
- Dois orquestradores simétricos (ambos planejando) foi descartado: dobra
  custo no ponto mais caro e produz consenso falso. A assimetria (um
  planeja, outro só contesta) é o que dá valor.

## Referências

- `motor/referencias/260906_orquestracao-3.md` — papéis, encaixe gate a
  gate do roteiro `/megabrain` core, classes de falha do fechamento de grafo
- `motor/referencias/260906_modo-maratona.md` — desenho original do modo
  maratona (caminhos `~/.megabrain/` — nesta central os scripts moram em
  `bin/` e a política em `memoria/estado/politica.json`, ver acima)
- `motor/referencias/260906_patch-skill-v6.1.md` — patch original pensado
  pra editar `motor/skills/megabrain/SKILL.md` direto; **não aplicado**
  nesta instalação porque a skill já está em v6.1 (260824, outro conteúdo)
  e porque orquestração 3 ficou como skill opcional em vez de mudança no
  roteiro sempre-ativo — mantido só como registro histórico
- `motor/modelos/plano/PLANO.schema.json` — schema do plano tipado
- `motor/modelos/plano/260906_checklist-cobertura-v1.md` — as 15 chaves de
  cobertura + como o adversário usa o plano
