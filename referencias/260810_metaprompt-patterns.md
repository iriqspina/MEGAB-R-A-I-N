# Metaprompt: padrões que funcionam

Metaprompt = usar o modelo para construir/refinar a instrução que o modelo vai
executar. O ganho não é mágica: é que a instrução explícita substitui a
adivinhação probabilística.

---

## Anatomia base — RTCRFE

Toda instrução séria tem seis blocos. Faltando um, o modelo preenche com o
default (= slop).

| Bloco | Pergunta que responde | Erro comum |
|---|---|---|
| **R**ole | De que ponto de vista? | Papel genérico ("você é um assistente útil") — não restringe nada |
| **T**ask | Qual o verbo e o objeto? | Verbo vago ("ajude com") |
| **C**ontext | O que preciso saber que não é óbvio? | Contexto demais; despejo de arquivo |
| **R**estrictions | O que NÃO fazer? | Ausente — é o bloco mais esquecido e o mais eficaz |
| **F**ormat | Como o output é estruturado e onde ele abre? | "Formato livre" |
| **E**xamples | Como se parece o certo? | Exemplos de casos de borda em vez de canônicos |

### Sobre Restrictions (espaço negativo)
O bloco de maior retorno. O modelo colapsa para o padrão mais provável — dizer
o que evitar é a única forma de sair dele.

```
NÃO: abrir reafirmando a pergunta · usar "não é apenas X, é Y" ·
     terminar com parágrafo-resumo · usar as palavras [lista] ·
     bullets onde a relação entre itens importa · hedge empilhado
```

### Sobre Examples
**Exemplos canônicos diversos > lista exaustiva de casos de borda.** 2–3
exemplos que retratam o comportamento esperado batem 15 regras de exceção.
Empilhar edge case degrada.

---

## Padrão 1 — Rubrica antes da geração

Escreva o critério de aprovação **antes** de gerar. Sem rubrica, a autocrítica
vira opinião.

```
Antes de escrever, defina 3 critérios verificáveis de sucesso desta peça.
Mostre os critérios. Depois gere. Depois pontue a sua própria saída
de 1–5 em cada critério, com a evidência (cite o trecho).
Se algum critério < 4, reescreva só o que falhou.
```

Por que funciona: transforma "está bom?" (não falseável) em "atende ao
critério 2?" (falseável).

---

## Padrão 2 — Dois passos com reparo limitado

```
Passo 1: gere.
Passo 2: critique contra a rubrica, apontando trechos específicos.
Passo 3: reescreva UMA vez. Não itere além disso.
```

⚠️ **Limite de 1 é técnico, não estilístico.** Loops de auto-refinamento sem
limite convergem para uma média homogênea: corrigem slop léxico e introduzem
slop estrutural. Se após 1 reparo continua ruim, o problema está no
enquadramento.

---

## Padrão 3 — A versão ruim primeiro

O mais barato do arquivo.

```
Primeiro, escreva a versão óbvia e genérica que qualquer IA produziria
para este pedido. Rotule como DESCARTAR.
Depois escreva a versão real, que não pode compartilhar nenhuma
frase, estrutura ou ângulo com a descartada.
```

Por que funciona: força o modelo a *localizar* o modo default e depois se
afastar dele, em vez de apenas ser instruído a "ser criativo".

---

## Padrão 4 — Red team / advogado do diabo

```
Assuma o papel de quem vai rejeitar este trabalho. Liste as 3 objeções
mais fortes — não as fáceis. Depois responda a cada uma revisando a peça,
ou declare explicitamente por que a objeção é aceitável.
```

Usar em: proposta comercial, decisão de arquitetura, argumento de design,
orçamento.

---

## Padrão 5 — Decomposição (metaprompt escreve o brief)

Para tarefa grande, separe **quem especifica** de **quem executa**.

```
Fase A: NÃO execute. Escreva a especificação completa do trabalho —
        entregável, restrições, critérios, riscos, sequência.
Fase B: [após aprovação] execute exatamente a especificação.
```

No MEGABRAIN isto é a fase SPEC → TICKETS → IMPLEMENTAR: a spec aprovada é o
contrato; quem executa recebe a spec, não o histórico da conversa.

---

## Padrão 6 — Grau de certeza obrigatório

Contra o hedge empilhado.

```
Marque cada afirmação factual: [VERIFICADO] com fonte,
[INFERIDO] com o raciocínio, ou [ESTIMATIVA] com a margem.
Não use "pode", "talvez", "possivelmente" como substituto do rótulo.
```

---

## Padrão 7 — Refinar um prompt existente

Cole o prompt ruim e rode:

```
Analise este prompt como engenheiro de prompt.
1. Que blocos de RTCRFE estão faltando?
2. Que ambiguidade permite mais de uma interpretação válida?
3. Que default indesejado o modelo vai assumir no silêncio?
4. Reescreva. Mostre um diff do que mudou e por quê.
```

---

## Padrão 8 — Ancoragem por referência, não por adjetivo

Adjetivo ("moderno", "profissional", "clean", "impactante") não restringe —
cada um significa mil coisas. Referência concreta restringe.

```
❌ "tom profissional e moderno"
✅ "tom do [exemplo colado]. Frases curtas, zero adjetivo de venda,
    números específicos, admite o que não sabe."
```

Vale igualmente para direção visual: referência > descrição.

---

## Ordem que importa

1. Restrições e formato **antes** do conteúdo longo — o modelo pesa o início e
   o fim mais que o meio.
2. Exemplos **depois** das regras — o exemplo ilustra a regra, não a substitui.
3. Instrução crítica **repetida no fim** de prompt longo.
4. Uma tarefa por prompt. Duas tarefas = duas chamadas ou uma decomposição
   explícita.

---

## Anti-padrões

| Anti-padrão | Por quê |
|---|---|
| "Seja criativo / pense fora da caixa" | Zero restrição. Não muda a distribuição. |
| "Você é um especialista de classe mundial em..." | Superlativo não adiciona capacidade. Especifique o ponto de vista real. |
| Empilhar 20 regras de exceção | Degrada. Use 2–3 exemplos canônicos. |
| "Não cometa erros" | Não acionável. |
| Prompt-monólito de 3000 palavras | Meio do contexto perde peso. Decomponha. |
| Pedir para "verificar duas vezes" sem critério | Vira teatro. Dê a rubrica. |
| Loop de refino sem limite | Converge para mingau homogêneo. |
