---
name: orquestracao1
description: Orquestração MEGABRAIN V6 primária: execução local limitada entre Claude e Codex, com plano revisado antes da produção, rota explícita, evidências e entrega humana. Use para trabalho multiagente novo; não agenda tarefas nem aplica mudanças por conta própria.
---

# Orquestração 1 · V6 primária

## Quando usar

Use para uma entrega nova que se beneficia de dois papéis independentes. A V6 substitui os modos antigos 1, 3 e 4 como entrada padrão: ela guarda o estado e as fontes do projeto, revisa o plano antes de produzir e revisa o resultado antes da entrega. O motor não escreve no projeto-alvo, não publica e não transforma revisão textual em validação de código.

Não use para uma pergunta simples, para agendamento, nem para retomar uma execução histórica V5; neste último caso use `/orquestracao2`.

## Entrada e preparação

1. Leia `ESTADO.md`, `HANDOFF.md`, o fim de `DECISOES.md`, `LICOES.md` e a trava do projeto. Na central, eles vivem em `memoria/estado/` e `memoria/nucleo/`.
2. Crie um brief JSON dentro do projeto com `objective`, `criteria` (lista verificável), `context` e, se preciso, `assertions` com textos esperados. Fonte adicional só entra por arquivo explícito dentro do projeto.
3. Faça a prévia antes do despacho. Ela não gasta chamadas nem usa cota antiga:

```text
python <CENTRAL>/bin/mb-orquestracao.py prepare --projeto <PROJETO> --brief <BRIEF_ABSOLUTO> --flow-version 2
```

O perfil é `micro`, `normal`, `frontier` ou `auto`. `auto` é conservador: enquanto a cota não estiver medida, usa `normal` e declara isso na rota; não finge escolher o modelo mais barato.

## Fluxo V6

1. Claude planeja. Codex revisa o plano de forma independente. Se o plano não passar, o motor repara/revisa dentro do limite ou entrega `plan_rejected` sem produzir um candidato enganoso.
2. Codex produz/corrige a partir do plano aprovado. Claude faz revisão final independente.
3. Cada execução congela brief, fontes, configuração, rota e respostas em `<PROJETO>/.automations/runs/ID/`. O documento humano vai para `<PROJETO>/00_PARA-VOCE/orquestracao1-ID/`.
4. `review_approved` significa somente que a revisão textual passou. O orquestrador ainda testa, abre o artefato ou valida o runtime quando isso fizer parte do escopo autorizado.

```text
python <CENTRAL>/bin/mb-orquestracao.py run --projeto <PROJETO> --brief <BRIEF_ABSOLUTO> --mode loop --flow-version 2
python <CENTRAL>/bin/mb-orquestracao.py status --projeto <PROJETO> --id <ID>
python <CENTRAL>/bin/mb-orquestracao.py stop --projeto <PROJETO> --id <ID>
```

`status`, `stop` e `resume` leem a configuração congelada no manifesto da execução; uma atualização posterior da V6 não torna uma execução antiga ilegível. `stop` impede novos despachos e a chamada em curso termina por retorno ou prazo.

## Limites e fechamento

- Clientes usam assinaturas existentes. Não use API key, compra, crédito extra ou troca silenciosa de modelo como fallback.
- **Workers no Codex:** para sondagem, checklist, varredura, extração e teste
  delimitado, tente primeiro o **Codex Spark** (`provider: spark`) quando sua
  própria leitura de cota estiver `ok`. Spark usa o bucket
  `codex_bengalfox`, separado do Codex/Sol; registre e respeite cada um de
  forma independente. Se Spark não estiver medido/saudável ou a tarefa exigir
  implementação, decisão, revisão independente ou aceite, use o papel forte
  configurado. Spark não é aprovador e a V6 não o aceita nos quatro estágios
  principais.
- **Telemetria de cota:** o motor mede Claude, Codex/Sol e Spark antes de abrir
  a run, registra a amostra associada a cada despacho e mede novamente ao
  fechar, inclusive quando a run falha. As evidências ficam em
  `.automations/runs/ID/quota-lifecycle.jsonl`; a central recompõe
  `dados/telemetria-orquestracao.json` com os últimos 240 eventos exatos e o
  passado agregado por dia/modelo. A escolha continua usando a leitura atual:
  histórico serve para enxergar padrão, não para fingir que uma cota antiga é
  a de agora.
- Cota sem medição é `NAO_MEDIDO`. Cota, contexto e tokens são coisas diferentes e só entram no relatório quando houver fonte registrada.
- Workers propõem; o orquestrador decide, executa o que foi autorizado e presta contas ao <USUARIO>.
- Ao fim, valide o que foi realmente feito, atualize estado/handoff/decisões com trava e registre a lição. Commit ou push continuam dependendo de pedido explícito.

## Verificação do motor

```text
python <CENTRAL>/bin/mb-orquestracao.py doctor --projeto <PROJETO>
python <CENTRAL>/bin/mb-orquestracao.py probe --projeto <PROJETO> --flow-version 2
python -B -X utf8 -m unittest discover -s <CENTRAL>/apps/automations/tests -v
```

Fonte canônica: `motor/skills/orquestracao1/SKILL.md`. Os plugins Claude, Codex e Kimi são cópias derivadas; a fonte manda.
