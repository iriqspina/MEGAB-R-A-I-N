---
name: orquestracao2
description: Compatibilidade MEGABRAIN V5 para retomar ou reproduzir fluxos históricos de loop e swarm entre Claude, Codex e Spark. Use somente por pedido explícito ou execução existente; novos trabalhos usam /orquestracao1 V6.
---

# Orquestração 2 · V5 de compatibilidade

## Quando usar

Esta é a V5 preservada para retomar uma execução histórica ou reproduzir um fluxo que o <USUARIO> pedir explicitamente. Trabalho novo usa `/orquestracao1` (V6), que planeja, faz revisão independente do plano, produz e faz revisão final com rota registrada.

## Contrato de entrada

1. Leia estado, handoff, decisões, lições e trava do projeto real. Na central, eles ficam em `memoria/estado/` e `memoria/nucleo/`.
2. Escreva no projeto um brief JSON com `objective`, `criteria`, `context` e, se necessário, `initial_candidate` e `assertions`.
3. Fontes adicionais são arquivos explícitos dentro do projeto; não carregue o cérebro inteiro. A prévia não consome chamadas:

```text
python <CENTRAL>/bin/mb-orquestracao.py prepare --projeto <PROJETO> --brief <BRIEF_ABSOLUTO> --flow-version 1
python <CENTRAL>/bin/mb-orquestracao.py run --projeto <PROJETO> --brief <BRIEF_ABSOLUTO> --mode loop --flow-version 1
```

## Limites V5

- Loop: Claude planeja; Codex produz/corrige; Claude revisa. O modo `swarm` usa Spark apenas em tarefa delimitada e nunca como aprovador.
- Assinaturas existentes apenas; sem API key, crédito extra, compra ou troca silenciosa de modelo.
- `review_approved` é revisão textual. Código, artefato visual e publicação exigem verificação separada pelo orquestrador, dentro do escopo autorizado.
- Estado e provas ficam em `<PROJETO>/.automations/runs/ID/`. Execuções V5 novas entregam em `<PROJETO>/00_PARA-VOCE/orquestracao2-ID/`. Execuções históricas mantêm a pasta de saída original para não quebrar links ou retomadas.
- `status`, `stop` e `resume` usam o manifesto congelado da própria execução. `stop` impede novo despacho; a chamada já em curso termina por retorno ou prazo.

## Fechamento

O worker propõe; o orquestrador decide, executa o que foi autorizado, verifica e atualiza estado/handoff/decisões sob trava. Commit, push e publicação dependem de pedido explícito.

Fonte canônica: `motor/skills/orquestracao2/SKILL.md`. Os plugins Claude, Codex e Kimi são cópias derivadas.
