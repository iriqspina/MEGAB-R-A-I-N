---
name: conclusao-megabrain
description: Ponteiro para o Gate 6 (PASSAR O BASTÃO) da skill megabrain — esgotar execução autônoma antes de pedir algo, e fechar ESTADO/HANDOFF/DECISOES/lições na entrega. Use quando o usuário digitar /conclusao-megabrain, disser "fecha isso", "encerra o projeto", "passa o bastão", ou quando uma entrega chegar em estado verificável.
---

# /conclusao-megabrain — ponteiro para o Gate 6

**v2.0 · 260825.** Esta skill não tem mais corpo próprio. **Execute o Gate 6
da skill `megabrain`** (`motor/skills/megabrain/SKILL.md`, seção "6 PASSAR O
BASTÃO") e pare por aqui.

## Por que virou ponteiro

Ela duplicava o Gate 6 inteiro — esgotar execução autônoma, fechar
ESTADO/HANDOFF/DECISOES, regra de push — e **divergiu**: carregava um teto de
"máx. 2 perguntas por rodada" que a decisão 260824 revogou. Duas fontes para o
mesmo procedimento significam que a cópia envelhece em silêncio e o agente
obedece a versão errada sem saber que existe outra.

Decisão 260825k. O comando continua existindo porque o hábito é dele; o que
some é a segunda fonte de verdade.

## O que o Gate 6 já cobre e ficava repetido aqui

| Assunto | Onde está agora |
|---|---|
| Esgotar execução autônoma antes de pedir | Gate 6, primeira linha |
| Teto de perguntas | **não existe** — Gate 1 roda a grelha completa (`/grelhar`) |
| Fechar ESTADO / HANDOFF / DECISOES | Gate 6, os 5 campos do handoff |
| Confirmar antes de `git push` | Gate 6 + contrato de ações do usuário |
| O que nunca vai pro pacote público | `bin/mb-generate-template.py` (garantia executável, não regra em markdown) |
| Registrar lição | Gate 7 |

Se você veio parar aqui procurando uma dessas regras, ela está no Gate 6 — e
é lá que ela é mantida.
