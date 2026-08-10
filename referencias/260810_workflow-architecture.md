# Arquitetura de workflow: onde colocar cada coisa

Primitivas de customização de um agente. Escolher errado é a causa nº1 de
"o agente não seguiu minha regra".

---

## Tabela de decisão

| Primitiva | Carregamento | Custo | Garantia | Use para |
|---|---|---|---|---|
| **System prompt / instruções fixas** | Toda sessão, sempre | Alto (permanente) | ❌ pedido | Preferências pessoais, convenções invioláveis, tom |
| **Skill** (`/nome`) | Sob demanda ou por gatilho | ~zero quando inativa | ❌ pedido | Procedimento repetível, conhecimento de domínio |
| **Agente separado** | Invocado | Contexto isolado | ❌ pedido | Trabalho barulhento, verificação independente |
| **Script / hook / .cmd** | Evento ou execução direta | Baixo | ✅ **determinístico** | Formatação, lint, backup, validação obrigatória |

### A regra que resolve 80% da frustração
**Instrução em markdown é pedido, não garantia.** O modelo pode não seguir.
Se algo *precisa* acontecer sempre e sem falha — rodar prettier, versionar com
data, bloquear deploy — isso é script, nunca instrução em markdown.

Corolário no MEGABRAIN: os portões de publicação vivem em `.cmd` (script que
roda os portões sozinho e pausa antes do irreversível), não numa skill que
pede "lembre de validar".

---

## System prompt — o que entra

✅ Entra:
- Preferências de resposta (TL;DR primeiro, tom, idioma)
- Convenções de arquivo/versionamento
- Stack e ferramentas fixas
- O que **nunca** fazer
- Um ponteiro curto para o protocolo (não o protocolo inteiro)

❌ Não entra:
- Procedimento longo → vira skill
- Conhecimento de domínio → vira arquivo de referência
- Qualquer coisa relevante em menos de 30% das sessões
- Documentação → vira README

**Teste:** essa linha vale a pena ser lida em *toda* conversa, inclusive nas
triviais? Não? Fora.

---

## Skills — como escrever uma que funciona

### Frontmatter
```yaml
---
name: kebab-case-max-64-chars
description: O que faz E quando usar. Máx 1024 chars. Sem tags XML.
---
```

A `description` é o **único** texto que o modelo vê antes de decidir disparar.
Ela precisa conter os gatilhos literais: as palavras que a pessoa realmente
digita.

- ❌ `description: Ajuda com design.`
- ✅ `description: Roda o protocolo de projeto de design (Duplo Diamante).
  Use quando a pessoa digitar /design-diamond, iniciar projeto visual novo,
  perguntar "onde estamos" num projeto, ou pedir para definir o próximo passo.`

### Corpo
- Máx. ~500 linhas. Passou disso, fatie em `references/` e aponte.
- Um caminho feliz claro.
- **Seção obrigatória: "Como isso costuma dar errado".** Isso vale mais para
  confiabilidade que todas as instruções do caminho feliz. Liste os modos de
  falha reais que você já viu.
- Tabelas > prosa para roteamento.

### Estrutura de pasta
```
minha-skill/
  SKILL.md          # nível 2 — carregado ao disparar
  references/*.md   # nível 3 — carregado sob demanda
  templates/*       # colável
  scripts/*         # executável (garantia real)
```

---

## Agentes separados

**Específico bate genérico.** Especificidade compra seleção de ferramenta
melhor e contexto mais apertado.

- ❌ "agente de QA"
- ✅ "auditar contraste WCAG AA nas 6 telas exportadas em /export e devolver
  só as falhas com valores"

Não delegue: decisão que depende do histórico da conversa · trabalho criativo
que precisa do contexto acumulado · qualquer coisa que o agente teria que
redescobrir do zero (o start a frio é o custo real).

---

## Fluxo padrão para tarefa não-trivial

```
1. Enquadrar        → Gate 1 (referencias/gates-entrega.md)
2. Planejar         → spec ANTES de editar/gerar
3. Delegar ruído    → agente separado
4. Executar         → skill de formato
5. Auditar          → Gate 4 anti-slop
6. Verificar        → abre? números batem? caminhos existem?
7. Registrar        → licoes-metaprotocolo.md
```

Etapa 2 é a mais pulada e a mais cara de pular.

---

## Quando promover uma lição a skill/regra

Gatilho: **a mesma lição apareceu 3 vezes.**

```
1× → nota em licoes-metaprotocolo.md
2× → nota + tag de recorrência
3× → vire regra do PIPELINE.md ou skill própria, e limpe as notas
```

Lição que se repete não é memória — é processo não escrito.

---

## Como isso costuma dar errado

1. **Colocar procedimento no system prompt.** Ele fica longo, o modelo ignora
   o meio, e você paga o custo em toda sessão.
2. **Description de skill vaga.** A skill nunca dispara e você culpa o modelo.
3. **Esperar garantia de markdown.** Se é crítico, é script.
4. **Agente genérico.** Entra frio, sai raso.
5. **Skill sem "como dá errado".** Funciona na demo, quebra no uso real.
6. **Skills demais com escopo sobreposto.** O modelo não sabe qual disparar.
   Funde ou delimita.
