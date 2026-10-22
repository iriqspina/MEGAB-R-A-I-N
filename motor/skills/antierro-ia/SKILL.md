---
name: antierro-ia
description: Prevenir, monitorar e aprender erros POR IA — gates de pré-entrega por categoria, dados separados por IA (erro de uma não vira regra de outra) e re-teste de limites que expira quando a IA melhora. Use em toda entrega não trivial, ao registrar lição/erro, ao abrir sessão que vai entregar algo visual ou editar arquivo de produção, e quando um revisor apontar achados.
---

# antierro-ia — erros previstos, medidos e desaprendidos por IA

Fonte canônica: `<MEGABRAIN_CENTRAL>/motor/skills/antierro-ia/` (resolva
`<MEGABRAIN_CENTRAL>` procurando `bin/` + `VERSAO.txt` + `MEGABRAIN.md`;
ex.: `<MEGABRAIN_ROOT>`). Cópia derivada pode existir em
`~/.zcode/skills/`, `~/.claude/skills` etc. — **edite só na fonte canônica**.

## REGRA DE OURO

Gates universais valem para toda IA. Limitações valem SÓ para a IA cujo
arquivo em `ias/` as comprova com evidência datada. Erro de uma IA nunca
migra para outra sem reprodução registrada nas duas.

## ATIVAR (quando)

1. Entrega não trivial de qualquer tipo (peça, código, relatório, deploy).
2. Início de sessão que vai: editar arquivo de produção/tema, entregar algo
   visual, ou interpretar termo ambíguo do <USUARIO>.
3. Ao registrar lição nova ou receber achado de revisor/humano.

## PASSOS (contrato, qualquer agente, qualquer fornecedor)

1. **Identifique-se** por metadado que você JÁ tem (cliente, modelo, versão
   declarada no seu ambiente). Nunca gaste chamada de modelo só para isso.
   Não sabe a versão? Escreva `versao: NAO_MEDIDA` — não invente.
2. **Leia seus limites vigentes**: `ias/<sua-ia>/limites.jsonl` (linhas com
   `status:"ativa"`). Máx. 10 linhas — se não conseguir ler, aplique os gates
   universais de `gates.md` e siga.
3. **Aplique os gates** das categorias envolvidas na tarefa (`gates.md`).
   Gate bloqueia a entrega até passar ou até o achado virar ocorrência
   declarada com mitigacao.
4. **Registre ocorrências** ao fechar (inclusive achados de revisor):
   `python <CENTRAL>/motor/skills/antierro-ia/bin/antierro.py registrar --ia <sua-ia> --categoria <slug> --texto "<achado em 1 linha>" --evidencia "<path>" [--severidade P1|P2|P3] [--achado_por auto|revisor|humano]`
5. **Nunca afirme sem prova**: frase factual em entrega humana cita o path da
   evidência. Sem prova = escreva "NÃO VERIFICADO".
6. **Limite vencido não é regra velha congelada**: antes de confiar numa
   mitigacao, rode `.../antierro.py vencidos`. Limite com `expira_em` vencido
   exige re-teste (`retestes/`) antes de valer. Passar 2× seguidas =
   `superado` (gate relaxa, histórico preservado).

## ESTRUTURA

- `categorias.md` — taxonomia estável (slugs). Não renomeie slugs; crie novo e markte o velho `sucessor`.
- `gates.md` — checklists executáveis por categoria (comando barato incluso).
- `ias/<ia>/perfil.md` — quem é a IA (cliente, modelos, ferramentas medidas).
- `ias/<ia>/limites.jsonl` — limitações com evidência + expiração + re-teste.
- `ias/<ia>/ocorrencias.jsonl` — erros reais (append-only, id único).
- `ias/_universal/limites.jsonl` — só por promoção: mesma falha reproduzida
  em 2+ IAs com evidências.
- `retestes/<id>/` — fixture + esperado + custo. `INDICE-RETESTE.json` é
  gerado pelo CLI (`antierro.py reindex`); não edite à mão.

## REGISTRAR LIÇÃO → DADO POR IA

Lição nova nasce com `categoria` (slug de `categorias.md`), `ia`, `modelo`,
`versao`, `evidencia` (path) e `escopo: ia`. Vira `universal` somente com
reprodução em 2+ IAs registrada. Limitação ligada a capacidade do modelo
(ex.: ler imagem) carrega `expira_em` (30 dias ou troca de versão) e
`reteste`. Erro superado fica `status: superado` — nunca apagado.

## PROPAGAÇÃO CENTRAL → PROJETOS

Ocorrência nasce no `evidence/` do projeto; sobe ao central por acréscimo
(`registrar`). Projetos não mantêm cópia da skill: consomem pela fonte
canônica no startup (o catálogo `motor/skills` já é lido no início de
sessão). Novo gate/limite relevante para projetos entra como linha no
`referencias/atualizacoes-projetos.json` da central (mecanismo existente).

## HISTÓRIA

- 261019 · criação a pedido do <USUARIO>, com parecer duplo (Claude Opus
  xhigh + ZCode GLM independente): `Portfolio/evidence/261019_revisao-ia/`.
  Sementes: 11 ocorrências reais do ZCode/GLM-5.3 (sessão da pausa img2).

## Relatórios: GLM compõe, Codex/Claude revisam (261020)

Ao criar, regenerar ou corrigir relatório humano, aplicar `/relatorios-glm` (fonte central `motor/skills/relatorios-glm/SKILL.md`). GLM principal MAX é compositor obrigatório; Codex/Claude revisam fontes, imagens e controles e podem fornecer modelos finalizados. Última correção substantiva volta ao GLM. Exceção apenas crédito extremo comprovado sem reset útil; falha técnica não troca produtor. Esta regra específica prevalece sobre papéis genéricos anteriores somente para relatórios. Evitar Claude MAX e ultracode. Gate `bin/mb-relatorios-glm.py`, evidência e exemplo promovido por prova; nunca prometer erro zero ou recarga de chats abertos.
