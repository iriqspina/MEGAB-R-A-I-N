# Templates prontos para colar (T1–T8)

Preencha `[colchetes]`. Todos testáveis em qualquer IA.

---

## T1 — Brief de entrega (uso geral)

```
PAPEL: [de que ponto de vista específico — não "especialista de classe mundial"]
TAREFA: [verbo + objeto. Um só.]
CONTEXTO: [só o que não é óbvio. Não despeje.]
RESTRIÇÕES:
- Formato: [.pptx 16:9 / .docx / markdown / código em X]
- Tamanho: [páginas, slides, palavras, linhas]
- Tom: [referência concreta colada, não adjetivo]
- NÃO fazer: [lista explícita]
CRITÉRIOS DE SUCESSO (escreva antes de gerar, mostre-os):
1. [verificável]
2. [verificável]
3. [verificável]
EXEMPLO CANÔNICO: [1–3 exemplos representativos, não casos de borda]

Antes de gerar: descreva em uma linha a versão genérica que você
produziria por default. Rotule DESCARTAR. A versão real não pode
compartilhar frase, estrutura ou ângulo com ela.
Depois de gerar: pontue-se 1–5 em cada critério com citação do trecho.
Qualquer nota < 4, reescreva só o que falhou. Uma rodada.
```

---

## T2 — Refinar um prompt existente

```
Analise este prompt como engenheiro de prompt. Não o execute.

[COLE O PROMPT]

1. Que blocos faltam? (papel, tarefa, contexto, restrições, formato, exemplos)
2. Que ambiguidade permite mais de uma interpretação válida?
3. Que default indesejado o modelo vai assumir no silêncio?
4. Reescreva. Mostre um diff do que mudou e por quê.
```

---

## T3 — Red team

```
Assuma o papel de quem vai REJEITAR este trabalho — não um crítico
educado, quem tem motivo real para dizer não.

[COLE O ARTEFATO]

Liste as 3 objeções mais fortes. Não as fáceis.
Para cada uma: revise o artefato para responder, ou declare
explicitamente por que a objeção é aceitável e qual o custo de aceitá-la.
```

---

## T4 — Verificação independente (agente separado)

```
Você recebe um artefato e uma rubrica. Você não sabe como ele foi
produzido e não deve assumir boa intenção.

RUBRICA:
1. [critério]
2. [critério]
3. [critério]

ARTEFATO:
[colar]

Para cada critério: nota 1–5 + citação literal da evidência.
Nota sem citação não conta.
Depois: as 3 objeções mais fortes de quem rejeitaria isso.
Não sugira melhorias. Só avalie.
```

---

## T5 — Decomposição (spec antes de execução)

```
FASE A — NÃO EXECUTE.
Escreva a especificação completa deste trabalho:
- Entregável exato e formato
- Restrições (declaradas e inferidas)
- Critérios de aceite verificáveis
- Riscos e o que pode dar errado
- Sequência de passos com dependências
- O que está fora de escopo

Pare aqui. Aguarde aprovação.

FASE B — [após aprovação] execute exatamente a especificação aprovada.
Se encontrar algo que a spec não previu, pare e pergunte.
```

---

## T6 — Handoff de sessão (contexto acabando)

```
Escreva um handoff para retomar este trabalho numa sessão nova.
Máximo 40 linhas. Formato:

# OBJETIVO
[uma frase]
# DECIDIDO
[decisões travadas — não reabrir]
# ABERTO
[o que ainda precisa de decisão, e de quem]
# DESCARTADO
[o que foi tentado e rejeitado, com o motivo — não reciclar]
# ESTADO DOS ARQUIVOS
[caminhos + o que cada um contém]
# PRÓXIMO PASSO
[a primeira ação concreta da próxima sessão]
```

---

## T7 — Brief de projeto de design

```
FASE DO DUPLO DIAMANTE: [1 Pesquisa / 2 Análise / 3 Ideação / 4 Design]
MODO: [divergir / convergir]

PROBLEMA (uma frase falseável): [se não consegue escrever, você ainda
está na Fase 1]
USUÁRIO E DECISÃO: [quem, e o que essa pessoa faz depois]

RESTRIÇÕES TRAVADAS (antes de compor):
- Grade: [colunas / margens]
- Escala tipográfica: [máx. 5 passos]
- Paleta: [máx. 3 famílias + neutros, com hex]
- Espaçamento: [base, ex. 4/8]
- Formato final: [dimensão, DPI, perfil de cor, onde é aberto]

REFERÊNCIA VISUAL: [links ou descrição de peça concreta — não adjetivos]
ANTIRREFERÊNCIA: [o que evitar, com exemplo]
FIDELIDADE: [proporcional à certeza atual]

Antes de entregar, rode:
- Print sem logo: dá pra saber de quem é?
- Hierarquia em 3 segundos
- Contraste WCAG AA (4.5:1 / 3:1)
- Toda decisão visual tem motivo declarável
- Zero itens do léxico visual banido
```

---

## T8 — Registro de lição

```
## [YYMMDD] — [contexto em 4 palavras]
GATILHO: [quando essa situação reaparece]
LIÇÃO: [o que deu errado ou foi descoberto]
ATALHO: [o que fazer direto da próxima vez]
```

Registre só o que muda ação futura. Narrativa de sessão não entra.
Destino: `licoes-metaprotocolo.md` da fonte canônica do MEGABRAIN.
