---
name: hypadododiabo
description: Explora o melhor caso defensável de uma opção sem virar propaganda, separando upside, evidência, condições, limites, custos, experimento reversível e critérios de interrupção. Use somente quando o usuário digitar /hypadododiabo, pedir o melhor caso realista de uma ideia, solicitar uma lente positiva com limites ou quiser contrapor uma análise excessivamente unilateral; não acione em conversa ordinária, status ou ajuste local óbvio.
---

# hypadododiabo — ampliar o melhor caso sem vender fantasia

**v0.1 · 260904.** Investigar quanto valor uma opção pode criar se as condições
necessárias forem reais. Fortalecer o caso positivo até seu limite defensável e
preservar evidência, custo e autoridade humana.

## Contrato

1. Tratar esta skill como **lente opcional**, nunca como aprovação automática.
2. Ampliar o upside por mecanismo causal: explicar o que melhora, para quem e
   por quê. Não usar entusiasmo como evidência.
3. Separar fato, inferência e hipótese. Citar a fonte de todo número ou marcar
   `[ESTIMATIVA]`; nunca fabricar probabilidade.
4. Declarar condições necessárias, limites, custos, dependências e custo de
   oportunidade. Um melhor caso sem preço é propaganda.
5. Propor o menor experimento reversível capaz de reduzir a incerteza, dentro
   da autoridade já concedida.
6. Definir **kill criteria** observáveis antes do experimento. Não mover a meta
   depois de ver um resultado ruim.
7. Terminar com exatamente um veredito: `SEGUIR`, `TESTAR PEQUENO`, `ADIAR` ou
   `NÃO SEGUIR`.
8. Se o melhor caso ainda for significativamente negativo, reconhecer que o
   outro caminho está correto. Não forçar equilíbrio artificial.
9. Não decidir produto, gosto, prioridade, gasto ou risco aceitável em nome do
   <USUARIO>. Decisão concreta não respondida vira limite explícito.
10. Quando atuar como Headhunter de `/quaseultracode`, submeter toda oportunidade
    à segunda leitura “casa ≠ cabana” antes de enviá-la ao Sol.

## Quando não rodar

Não acionar por inferência em conversa ordinária, pergunta rápida, status,
correção local óbvia ou tarefa N0. Uma sugestão do roteador não ativa a skill;
é preciso pedido explícito ou aceite humano inequívoco.

Se a ideia já tem evidência suficiente e a tarefa é apenas executar, seguir a
tarefa. Se o problema principal é downside ou risco, sugerir
`/advogadododiabo` somente numa transição material. Se o trabalho exige
decomposição multiagente, sugerir `/orquestracao1` sem ativá-la.

## Inputs mínimos

Usar o que já existe no pedido e nas fontes canônicas. Não abrir grelha só para
preencher um template.

1. Opção sob análise e alternativa real.
2. Resultado positivo procurado e quem recebe o valor.
3. Evidência disponível e lacunas relevantes.
4. Restrições duras: tempo, dinheiro, marca, segurança, autorização e
   reversibilidade.
5. Decisões de produto já tomadas pelo <USUARIO>.

Se faltar uma decisão concreta e a grelha já tiver sido pulada ou encerrada,
não perguntar: limitar a análise, registrar a incerteza e não escolher por ele.

## Método

### 1. Fixar a hipótese positiva

Escrever uma frase falseável:

```text
Se <condições observáveis>, então <mecanismo> pode produzir <resultado>,
medido por <sinal>, sem ultrapassar <limite>.
```

Trocar “pode dar certo” por uma cadeia verificável. Não confundir mercado
endereçável, desejo do time ou referência estética com demanda comprovada.

### 2. Montar o melhor caso defensável

Listar:

- upside específico e beneficiário;
- mecanismo que liga a opção ao upside;
- evidência a favor, com fonte;
- condições que precisam ser verdadeiras;
- sinais antecedentes que apareceriam cedo se a hipótese estiver correta.

Manter o melhor caso dentro do que a evidência permite. Rotular inferência e
`[ESTIMATIVA]` no próprio item.

### 3. Cobrar o preço do melhor caso

Registrar limites técnicos, custos diretos, custo de oportunidade, dependências
e danos possíveis. Distinguir custo recuperável de decisão irreversível.

Não esconder uma condição crítica no rodapé. Se uma condição improvável ou não
controlável sustenta todo o upside, rebaixar o veredito.

### 4. Desenhar o experimento reversível

Definir:

1. menor unidade testável;
2. duração ou amostra, com fonte ou `[ESTIMATIVA]`;
3. baseline e métrica primária;
4. custo máximo e autoridade necessária;
5. evidência que favorece a hipótese;
6. kill criteria e plano de reversão.

Não chamar de experimento uma implementação completa sem rollback.

### 5. Julgar sem propaganda

Usar:

- `SEGUIR`: evidência e condições já sustentam execução dentro da autoridade;
- `TESTAR PEQUENO`: upside plausível, mas uma incerteza relevante pode ser
  reduzida por teste reversível;
- `ADIAR`: dependência, timing ou autoridade impede teste útil agora;
- `NÃO SEGUIR`: mesmo o melhor caso não compensa custos/limites ou depende de
  premissa sem caminho razoável de prova.

Não atribuir percentuais de sucesso sem base estatística. Quando houver
incerteza, descrevê-la qualitativamente e apontar qual evidência a reduziria.

## Saída obrigatória

```text
HIPÓTESE POSITIVA
<frase falseável>

UPSIDE E MECANISMO
<valor, beneficiário e cadeia causal>

EVIDÊNCIA
<fatos com fonte; inferências e [ESTIMATIVA] rotuladas>

CONDIÇÕES
<o que precisa ser verdade>

LIMITES E CUSTOS
<restrições, dependências e custo de oportunidade>

EXPERIMENTO REVERSÍVEL
<menor teste, baseline, métrica, custo máximo e rollback>

KILL CRITERIA
<sinais observáveis para interromper>

VEREDITO
SEGUIR | TESTAR PEQUENO | ADIAR | NÃO SEGUIR

LIMITE DE DECISÃO
<o que permanece escolha do <USUARIO>>
```

## Combinação com outras lentes

Quando o <USUARIO> ativar também `/advogadododiabo`, aplicar as duas lentes ao
mesmo pacote factual, uma vez cada:

1. `/hypadododiabo` constrói o melhor caso defensável.
2. `/advogadododiabo` constrói o downside defensável.
3. Comparar premissas, evidência, reversibilidade e custo do erro.
4. Encerrar com uma síntese; não fazer uma lente responder à outra em loop.

Em `/orquestracao1`, o Sol controla essa combinação antes do candidato final.
Ela não substitui o revisor final: quando o gate material o tornar aplicável,
`FABLE_LATEST` resolve a maior versão Fable compatível listada e a saúde/cota é
medida antes da chamada. Só se `FABLE_PERTO_DO_LIMITE` for medido, Kimi `>=3`
saudável pode revisar o mesmo candidato final e rubrica em uma única chamada,
sem workers. `MEDIUM` é o padrão; `LOW` é declarado por cota/escopo estreito e
`HIGH/XHIGH` exigem flag grande justificada. Sem Kimi `>=3` saudável, não
inventar substituto e declarar a indisponibilidade.

## Quando atuar como Headhunter de Evolução

No `/quaseultracode`, produzir o Passo A e não falar direto com o Sol ainda.
Entregar a oportunidade à segunda leitura com ideal, baseline e rubrica. O
Passo B tenta rejeitar a ideia e classifica:

- `SOLUÇÃO`: atende o ideal e não é inferior ao baseline;
- `PONTE`: tem cadeia causal explícita ao ideal, condição, prazo/etapa com fonte
  ou `[ESTIMATIVA]`, evidência, próximo passo, custo e kill criteria;
- `DISTRAÇÃO`: irrelevante, boba, inferior, óbvia ou proxy inadequada.

Somente `SOLUÇÃO` ou `PONTE` defensável chega ao Sol. `DISTRAÇÃO` entra apenas
num log interno curto para evitar redescoberta e não aparece no backlog entregue.

## Como isso costuma dar errado

1. **Entusiasmo vira dado.** Adjetivos ocupam o lugar de evidência.
2. **Probabilidade inventada.** Um percentual sem amostra cria precisão falsa.
3. **Piloto irreversível.** O “teste” já consome todo o orçamento ou publica.
4. **Kill criteria móveis.** Cada falha gera uma nova justificativa.
5. **Equilíbrio teatral.** O melhor caso segue ruim, mas recebe recomendação
   positiva para parecer otimista.
6. **Decisão terceirizada.** A análise escolhe prioridade de produto pelo
   <USUARIO> em vez de declarar o limite.
7. **Loop de lentes.** Hypado e advogado debatem até apagar as diferenças úteis.
