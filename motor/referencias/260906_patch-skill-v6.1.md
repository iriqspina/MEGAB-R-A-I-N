# Patch da SKILL.md — orquestração 3 (v6.0 → v6.1)

Três edições cirúrgicas. Nada é removido; o roteiro continua com 8 gates.

---

## 1. Cabeçalho de versão

Trocar a linha de versão por:

```
**v6.1 · 2026-09-06.** Base: v6.0. Mudou: entra a camada **orquestração 3**
(dois pontos de ponta assimétricos, política de modelo/effort calculada por
orçamento, plano tipado e fechamento de grafo). Detalhe:
`referencias/260906_orquestracao-3.md`. Nada do roteiro v6.0 saiu.
```

---

## 2. Seção "Multi-agente (resumo)" — substituir pelo bloco abaixo

```md
## Multi-agente (resumo)

Barato/contexto grande: varredura, extração, leitura longa, 1ª passada, refactor
mecânico → entrega bruto + resumo. Julgamento: enquadrar, decidir, auditar,
texto final → entrega o artefato. É economia de token, não hierarquia. Trava e
bastão: HANDOFF + `bin/mb-sync.py` (status/lock/release).

**Orquestração 3** — dois pontos de ponta, não um: o `orquestrador` decide e o
`adversário` (outro fornecedor, quota separada) só aponta o que falta no plano.
Modelo e effort de cada papel saem de `memoria/estado/politica.json`, gerado por
`bin/mb-orcamento.py` — não se escolhe no meio da tarefa. Sob pressão de quota
corta-se escopo, nunca verificação: os dois papéis de ponta não degradam.
Papéis, fases e encaixe gate a gate: `referencias/260906_orquestracao-3.md`.
```

---

## 3. Quatro linhas dentro dos gates existentes

**Gate 0 ASSUMIR** — acrescentar ao fim do bullet:

```
  Política da sessão: `python bin/mb-orcamento.py --json >
  memoria/estado/politica.json` (o preflight já chama). Uma linha de status.
```

**Gate 1 ENQUADRAR** — acrescentar ao fim do bullet:

```
  Entrega (não rascunho) → plano sai em `PLANO.json` no schema
  `modelos/plano/PLANO.schema.json`, com as 15 chaves de cobertura respondidas
  (`modelos/plano/260906_checklist-cobertura-v1.md`). `na` sem justificativa
  não passa.
```

**Gate 4 AUDITAR** — acrescentar antes de "**1 reparo só**":

```
  Antes do reparo: rodar o adversário (Codex, papel invertido — acha lacuna,
  não propõe solução; mínimo 5). Lacuna bloqueante recusada exige linha em
  DECISOES.md.
```

**Gate 5 VERIFICAR** — acrescentar ao fim do bullet:

```
  `python bin/mb-fechamento-grafo.py` — arquivos declarados no plano vs. tocados
  no git. Divergência é falha de planejamento (Gate 1), vai pro `falhas.jsonl`.
```

---

## 4. Hooks (`~/.claude/settings.json`)

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command",
        "command": "python \"%MEGABRAIN_CENTRAL%/bin/mb-orcamento.py\" --json > \"%MEGABRAIN_CENTRAL%/memoria/estado/politica.json\" && python \"%MEGABRAIN_CENTRAL%/bin/mb-orcamento.py\"" }] }
    ],
    "SubagentStop": [
      { "hooks": [
        { "type": "command", "command": "python \"%MEGABRAIN_CENTRAL%/bin/mb-fechamento-grafo.py\"" },
        { "type": "command", "command": "python \"%MEGABRAIN_CENTRAL%/bin/mb-orcamento.py\" --json > \"%MEGABRAIN_CENTRAL%/memoria/estado/politica.json\"" }
      ] }
    ]
  }
}
```

No Windows, confirme se seu Claude Code expande `%VAR%` no campo `command`.
Se não expandir, troque pelo caminho absoluto da sua central — é a exceção
consciente à regra de nunca chumbar caminho, e vale só no seu settings local.

---

## 5. Registro em DECISOES.md

```
2026-09-06 · orquestração 3 adotada no megabrain.
Escolhido: planejador + adversário assimétrico, adversário no Codex por quota
separada, política de modelo calculada por orçamento de janela de 5h.
Descartado: dois orquestradores simétricos (dobra custo no ponto mais caro,
produz consenso falso) e degradar o gate de ponta sob pressão de quota
(o retrabalho que isso gera custa mais que a economia).
Pendente: calibrar limite_5h_tokens e limite_semanal_tokens contra /usage
na primeira semana — antes disso os percentuais são chute com formato bonito.
```
