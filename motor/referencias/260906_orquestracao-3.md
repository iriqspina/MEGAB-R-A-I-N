# orquestração 3 — camada de orquestração multi-agente do megabrain

**v1.0 · 2026-09-06.** Encaixa nos gates existentes; não substitui nenhum.
Entra em **2 ORÇAR** (política de modelo/effort), **1 ENQUADRAR** (plano tipado),
**4 AUDITAR** (adversário) e **5 VERIFICAR** (fechamento de grafo).
Complementa a seção "Multi-agente (resumo)" da SKILL.md com o *quem-roda-o-quê*.

## O que muda em relação ao modo otimizado atual

A skill já diz: mecânico → modelo equivalente; julgamento → modelo de ponta.
A orquestração 3 mantém isso e acrescenta três coisas:

1. **Dois pontos de ponta, não um.** O modelo de ponta que decide (`orquestrador`)
   e um segundo, de outro fornecedor, cujo único trabalho é achar o que falta
   no plano (`adversário`). Um modelo auditando o próprio plano tem viés de
   completude; o segundo, com papel invertido, não tem.
2. **A política de modelo é calculada, não escolhida.** `bin/mb-orcamento.py`
   lê o consumo real e devolve modelo + effort por papel. Ninguém decide isso
   no meio da tarefa.
3. **Plano vira dado.** Prosa esconde buraco; campo vazio não. Saída do Gate 1
   passa a validar contra `modelos/plano/PLANO.schema.json`.

## Papéis

| Papel | Onde entra | Trava |
|---|---|---|
| `talker` | recebe seus prompts, decompõe, reporta | mid-tier — roda em toda mensagem |
| `orquestrador` | Gate 1 e 2, delega, julga | ponta, **nunca degrada abaixo de Opus 5** |
| `adversário` | Gate 4, só aponta lacuna | ponta, no **Codex** (quota separada) |
| `worker` | Gate 3, execução em worktree | barato, effort baixo por desenho |
| `revisor` | Gate 5, gate de merge | cross-vendor do lado oposto ao que gerou |

Invariante: sob pressão de orçamento, corta-se **escopo**, nunca verificação.
Os dois papéis de ponta continuam ligados em vermelho. Detalhe das fases e da
instalação de hooks: `referencias/260906_modo-maratona.md`.

## Encaixe gate a gate

- **Gate 0 ASSUMIR** — o preflight passa a rodar `bin/mb-orcamento.py --json >
  memoria/estado/politica.json`. Uma linha de status no início da sessão.
- **Gate 1 ENQUADRAR** — a saída deixa de ser prosa e vira `PLANO.json` no schema.
  Os 3 critérios verificáveis que a skill já pede viram `criterio_de_pronto`
  por item, com comando literal em `verificacao` quando existir. O contraexemplo
  genérico nomeado continua, agora em `escopo_fora`.
- **Gate 2 ORÇAR** — o orçamento de contexto ganha par: o de quota. O orquestrador
  lê `politica.json` e não cria mais subagentes que `fanout_max`.
- **Gate 3 GERAR** — worker roda no modelo e effort da política, em worktree.
- **Gate 4 AUDITAR** — antes do reparo único, roda o adversário. Mínimo 5 lacunas.
  Lacuna `bloqueante` recusada exige linha em `DECISOES.md` — é o único caminho
  do plano sair do gate. Isso não substitui o anti-slop, roda ao lado dele.
- **Gate 5 VERIFICAR** — `bin/mb-fechamento-grafo.py` compara arquivos declarados
  no plano com os que o git mostra tocados. Divergência é falha de **planejamento**,
  não de execução.
- **Gate 7 APRENDER** — toda omissão que escapou vira linha nova no checklist de
  cobertura. É esse loop que faz a ausência de elemento convergir a ~0 — não o
  tamanho do modelo. Depois de ~20 ciclos o checklist é específico do seu stack.

## Falhas registradas

`mb-fechamento-grafo.py` escreve em `falhas.jsonl` com estas classes:

- `plano-incompleto` — campo vazio, critério vago, dependência órfã, cobertura não respondida
- `plano-invalido` — JSON ilegível
- `arquivo-nao-previsto` — worker mexeu fora do plano
- `item-nao-executado` — declarado e não tocado

`arquivo-nao-previsto` recorrente aponta plano raso no Gate 1, não worker
desobediente. Trate como sinal de gate, não de execução.

## Limites honestos

- Não existe endpoint oficial de quota do Max. Tudo aqui é estimativa sobre os
  transcripts locais. Calibrar contra `/usage` na primeira semana é obrigatório,
  senão é painel bonito medindo nada.
- Consumo via Codex sai de outra bolsa e não aparece nesses transcripts.
- Dois orquestradores simétricos (ambos planejando) foi descartado: dobra o custo
  no ponto mais caro e produz consenso falso. A assimetria é o que dá valor.
