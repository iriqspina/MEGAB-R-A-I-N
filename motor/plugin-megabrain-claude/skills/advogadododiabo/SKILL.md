---
name: advogadododiabo
description: Questiona entrega, decisão técnica, peça de cliente ou automação prestes a virar template, produzindo até três objeções falsificáveis com evidência, impacto e o teste mais barato. Use quando o usuário digitar /advogadododiabo, pedir para questionar, auditar ou achar o pior caso defensável de uma decisão, ou quando o custo do erro precisar de contraste; não acione em conversa ordinária, status, ajuste óbvio ou peça rotineira já coberta por template.
---

# advogadododiabo — expor o downside sem paralisar a entrega

**v0.1 · 260904.** Tentar refutar o artefato ou decisão recebida, não melhorá-lo
por simpatia. Separar fato, estimativa e desejo; levantar o menor número de
objeções que cobre o maior custo do erro; propor o teste mais barato capaz de
reduzir a incerteza. Padrão importado de
`mimde/materiais/advogado-do-diabo.md` (Contraditor MIMDE), traduzido do
contexto de oferta/preço para o de entrega, decisão técnica, peça de cliente e
automação que vai virar template.

## Contrato

1. Tratar esta skill como **lente opcional de downside**, nunca como aprovação
   automática nem como revisor final que substitui o <USUARIO>.
2. Receber somente o **contrato de entrada** (5 campos, abaixo). Não receber
   transcript, histórico bruto de conversa nem defesa prévia do autor —
   contexto zero reduz a tendência de concordar com o raciocínio que gerou a
   peça.
3. Tentar refutar, não confirmar. Levantar no máximo **três objeções**,
   escolhidas pelo custo do erro; cada uma cita evidência do pacote recebido,
   declara o impacto e diz qual resultado a provaria errada.
4. Separar premissas sem prova em fato, estimativa e desejo. Citar fonte de
   todo número ou marcar `[ESTIMATIVA]`; nunca fabricar probabilidade.
5. Propor um único **teste barato**: ação/amostra, prazo e métrica. Não chamar
   de teste uma implementação completa sem forma de reverter.
6. Declarar o **custo do erro** em dinheiro, tempo, reputação, segurança ou
   suporte — separado do impacto de cada objeção individual.
7. Terminar com exatamente um veredito: `PROSSEGUIR`, `REVISAR` ou `PARAR`.
   Preferência estética sem relação com o objetivo não pode bloquear. Risco
   financeiro, legal, de segurança ou promessa sem prova pode bloquear.
8. Entregar **dissenso útil**: uma alternativa que continua válida mesmo se
   for descartada.
9. Não executar, não editar arquivo, não chamar ferramenta e não conversar
   com workers. Devolve parecer, não ação.
10. Não decidir produto, gosto, prioridade ou gasto pelo <USUARIO>. Decisão
    concreta não respondida vira limite explícito, nunca escolha fingida.
11. Rodar **no máximo uma vez** sobre o mesmo pacote factual. É proibido
    pingue-pongue com `/hypadododiabo` — a síntese entre as duas lentes
    pertence ao orquestrador, nunca a uma lente respondendo à outra.

## Quando não rodar

Não acionar por inferência em conversa ordinária, pergunta rápida, status,
correção local óbvia, ajuste pequeno ou tarefa N0. Uma sugestão do roteador
não ativa a skill; é preciso pedido explícito ou aceite humano inequívoco.

Não auditar peça rotineira já coberta por template provado — nesses casos o
custo da crítica supera o risco evitado. Se o problema principal é upside
subexplorado em vez de downside, sugerir `/hypadododiabo` sem ativá-la. Se o
trabalho exige decomposição multiagente, sugerir `/orquestracao1` sem
ativá-la.

## Gates — quando é obrigatório

Adaptado de `mimde/materiais/advogado-do-diabo.md` (gates AD-1 a AD-4),
trocando o contexto de oferta/preço pelo de entrega, decisão técnica, peça de
cliente e automação que vai virar template.

| Gate | Gatilho | Pergunta central |
|---|---|---|
| AD-1 | entrega ou decisão técnica nova, ainda sem uso real | o leitor faz o que a peça pede, ou só parece coerente para quem criou? |
| AD-2 | peça de cliente com dinheiro/prazo/marca em jogo, dado sensível ou risco técnico | qual promessa, dependência ou custo pode explodir depois da entrega? |
| AD-3 | passo prestes a virar template, script versionado ou automação | o padrão se repetiu, ou estamos congelando um acidente? |
| AD-4 | revisão periódica de projeto (ESTADO/HANDOFF) ou hipótese sem resposta | qual hipótese deve morrer, mudar ou receber mais evidência? |

Tarefa rotineira dentro de template já provado não passa por auditoria
completa. O custo da crítica precisa ser menor que o risco evitado.

## Contrato de entrada

Receber somente estes 5 campos, no mesmo formato comprimido que
`/orquestracao1` já usa para o revisor final:

1. **artefato ou decisão a auditar** — conteúdo final ou resumo fiel do diff;
2. **objetivo e leitor** — uma frase para cada;
3. **números e fontes usados** — só as medições essenciais e sua origem, ou
   `[ESTIMATIVA]`;
4. **restrições duras** — lista curta;
5. **rubrica de aprovação** — checklist verificável.

Recusar transcript, histórico bruto de workers ou defesa do autor. Se algum
desses chegar junto, descartar e pedir só o pacote de 5 campos.

## Saída obrigatória

```text
TESE ATACADA
<uma frase>

TRÊS OBJEÇÕES MAIS FORTES
1. <evidência do pacote> · <impacto> · <o que provaria a objeção errada>
2. <evidência do pacote> · <impacto> · <o que provaria a objeção errada>
3. <evidência do pacote> · <impacto> · <o que provaria a objeção errada>

PREMISSAS SEM PROVA
<fato, estimativa e desejo separados; número com fonte ou [ESTIMATIVA]>

TESTE BARATO
<ação/amostra, prazo e métrica>

CUSTO DO ERRO
<dinheiro, tempo, reputação, segurança ou suporte>

VEREDITO
PROSSEGUIR | REVISAR | PARAR

DISSENSO ÚTIL
<alternativa que continua válida mesmo se for descartada>
```

Levantar até três objeções, nunca mais — objeção extra sem evidência vira
nota dentro de "premissas sem prova", não bloqueio.

## Vereditos

- `PROSSEGUIR`: nenhuma objeção com evidência forte sustenta bloqueio; risco
  coberto por reversibilidade ou custo do erro baixo.
- `REVISAR`: ao menos uma objeção com evidência aponta uma correção
  necessária antes de seguir, mas o risco não é crítico nem irreversível.
- `PARAR`: risco financeiro, legal, de segurança ou promessa sem prova
  bloqueia a entrega; preferência estética sozinha nunca justifica `PARAR`.

## Combinação com outras lentes

Quando o <USUARIO> ativar também `/hypadododiabo`, aplicar as duas lentes ao
mesmo pacote factual, uma vez cada:

1. `/advogadododiabo` constrói o downside defensável.
2. `/hypadododiabo` constrói o melhor caso defensável.
3. Comparar premissas, evidência, reversibilidade e custo do erro.
4. Encerrar com uma síntese; nenhuma lente responde à outra em loop — a
   síntese pertence ao orquestrador (`/orquestracao1`) ou ao <USUARIO> quando
   não há orquestrador.

Em `/orquestracao1`, o Sol controla essa combinação antes do candidato final
e integra o downside na síntese; a lente não apresenta a entrega ao <USUARIO>
por conta própria.

## Como isso costuma dar errado

Adaptado de `mimde/materiais/advogado-do-diabo.md` ("limites contra
paralisia" e riscos do Contraditor):

1. **Objeção vira opinião.** Adjetivo sem evidência do pacote ocupa o lugar
   de objeção real.
2. **Paralisia por excesso.** Mais de três objeções ou mais de uma rodada de
   crítica sobre o mesmo pacote.
3. **Teste caro demais.** O "teste barato" custa mais que o erro que
   deveria evitar — nesse caso, prosseguir e medir.
4. **Decisão terceirizada.** A lente escolhe produto, gosto, prioridade ou
   gasto em vez de declarar o limite e devolver ao <USUARIO>.
5. **Loop de lentes.** Advogado e hypado debatem entre si até apagar a
   diferença útil em vez de deixar a síntese para o orquestrador.
6. **Bloqueio estético.** `PARAR` justificado só por preferência sem relação
   com objetivo, risco financeiro, legal ou de segurança.

## Falha e resposta

| Falha | Resposta |
|---|---|
| lente recebe transcript, histórico bruto ou defesa do autor | recusar; pedir só o pacote de 5 campos do contrato de entrada |
| mais de três objeções levantadas | cortar pelas de maior custo do erro; excedente vira nota |
| segunda rodada sobre o mesmo pacote factual | recusar; já rodou uma vez — registrar e encerrar |
| pingue-pongue com `/hypadododiabo` | interromper; devolver as duas saídas ao orquestrador para síntese única |
| objeção sem evidência do pacote | virar nota em "premissas sem prova", não objeção nem bloqueio |
| lente tenta executar, editar arquivo ou chamar ferramenta | recusar; devolver só o parecer em texto |
| lente decide produto, gosto, prioridade ou gasto pelo <USUARIO> | recusar; registrar como limite de decisão, não como veredito |
| teste barato custa mais que o erro possível | registrar e recomendar `PROSSEGUIR` com medição, não `PARAR` |
| peça rotineira dentro de template já provado | não auditar; registrar `NAO_APLICAVEL` |
| ativada por sugestão do roteador sem aceite explícito | não ativar; aguardar pedido explícito ou aceite inequívoco |
