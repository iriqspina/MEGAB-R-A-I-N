---
name: quaseultracode
description: Conduz projetos grandes em ciclos de até 5 horas, definindo primeiro o resultado ideal, mantendo a qualidade-alvo independente de harness/model/effort, coordenando workers persistentes e entregando o delta restante sem esconder limites. Use quando o usuário digitar /quaseultracode, pedir uma execução grande próxima do padrão Ultracode com orçamento menor, ou aceitar essa sugestão num projeto cujo ideal estimado caiba em até 5 horas; não acione em conversa ordinária ou tarefa pequena.
---

# quaseultracode — ideal primeiro, ciclo finito

**v0.1 · 260904.** Aproximar um projeto grande do resultado ideal com orçamento
controlado, evidência verificável e continuidade explícita. Reduzir escopo ou
paralelismo quando a capacidade cair; nunca reduzir silenciosamente o padrão de
qualidade.

## Contrato

1. Definir o output ideal e critérios verificáveis **antes** do plano.
2. Manter a qualidade-alvo independente de harness, modelo e effort. Limitação
   de capacidade muda estratégia, decomposição, redundância e escopo do ciclo;
   não muda o que conta como correto.
3. Usar como orçamento inicial cerca de 70% do tempo/custo estimado para um
   ciclo Ultracode equivalente, rotulado `[HEURÍSTICA]`, com teto de 5 horas.
4. Se a estimativa do ciclo ideal ultrapassar 5 horas, classificar
   `ULTRACODE_REAL`, não comprimir artificialmente e entregar um mapa de
   continuação por marcos.
5. Continuar além do plano somente quando o próximo bloco de tempo comprar
   evidência, decisão ou qualidade mensurável. “Aproveitar para melhorar” não é
   justificativa.
6. Persistir workers úteis entre marcos, mas persistir estado no disco. Nenhum
   worker é fonte única de memória.
7. Rodar um Headhunter de Evolução read-only com `/hypadododiabo` em paralelo
   nos marcos. Ele sugere; nunca altera baseline, requisito ou fonte.
8. Submeter toda evolução ao gate anti-scope-creep antes de aceitar no ciclo.
9. Preservar decisão concreta de produto, gosto, prioridade, gasto e risco para
   o <USUARIO>.
10. Não usar Fable ou advogado do diabo em conversa comum. Dentro de
    `/orquestracao1`, resolver `FABLE_LATEST` na família Fable compatível e usar
    effort adaptativo — `MEDIUM` padrão elegível, `LOW` declarado por
    cota/escopo estreito, `HIGH/XHIGH` por flag grande — somente quando o gate
    não trivial justificar. Se `FABLE_PERTO_DO_LIMITE` for medido, só Kimi
    `>=3` saudável pode fazer o fallback questionador único, isolado dos
    workers e com modelo, saúde/cota, effort e justificativa registrados.
11. Tratar `/grelhar` como opcional. Se encerrada ou pulada, não fazer novas
    perguntas; operar autonomamente apenas no reversível e in-scope.
12. Aplicar duas passagens a toda sugestão: A cria o caminho para o ideal; B
    tenta rejeitá-lo com o teste **casa ≠ cabana** e classifica `SOLUÇÃO`,
    `PONTE` ou `DISTRAÇÃO` antes de o item chegar ao Sol.

## Gate de entrada

Não usar este modo para tarefa pequena, status, esclarecimento ou correção
local óbvia. Registrar `QUASEULTRACODE_NAO_APLICAVEL` e executar normalmente.

Classificar como projeto grande quando houver pelo menos dois destes sinais:

- múltiplos artefatos ou consumidores;
- dependências entre etapas;
- mais de uma especialidade ou worker útil;
- validação de runtime, integração ou regressão;
- risco material de implementação ou apresentação;
- necessidade de checkpoints que atravessem sessão.

Sugestão não ativa o modo. Ativar apenas por invocação direta ou aceite humano
inequívoco. Em conversa ordinária, não sugerir.

## Estado persistente

Salvar um checkpoint canônico antes de despachar workers:

```text
classificacao: QUASEULTRACODE | ULTRACODE_REAL | NAO_APLICAVEL
estado: IDEAL_DEFINIDO | PLANEJADO | EXECUTANDO | MARCO | VERIFICANDO | ENTREGUE | BLOQUEADO
grelha: ATIVA | CONCLUIDA | PULADA
ideal:
criterios:
restricoes:
estimativa_ultracode:
orcamento_quaseultracode:
tempo_consumido:
workers_e_cotas:
baseline:
evidencias:
delta_para_ideal:
backlog_positivo:
rejeitadas_log_interno:
limites_de_decisao:
proximo_marco:
```

Atualizar no fim de cada marco e antes de qualquer transição de agente. Não
usar transcript como única memória.

## Fluxo

### 1. Definir o ideal antes do plano

Escrever:

1. artefato ideal e leitor;
2. decisão que o resultado permite;
3. critérios funcionais, visuais, técnicos e de prova;
4. restrições duras e zonas protegidas;
5. baseline conhecido e lacunas;
6. definição observável de concluído.

Nomear a versão reduzida que seria produzida por pressa e recusá-la como alvo.
Um plano sem ideal apenas otimiza atividade.

### 2. Estimar e classificar

Estimar o tempo/custo de um ciclo Ultracode capaz de cumprir o ideal. Declarar
premissas e rotular o número `[HEURÍSTICA]`.

```text
orcamento_quaseultracode = min(0,70 × estimativa_ultracode, 5h) [HEURÍSTICA]
```

- estimativa do ideal `<= 5h`: classificar `QUASEULTRACODE`;
- estimativa do ideal `> 5h`: classificar `ULTRACODE_REAL`, executar apenas um
  primeiro marco seguro se autorizado e entregar o mapa de continuação;
- tarefa pequena: `NAO_APLICAVEL`.

Não representar 70% como garantia de custo ou de completude. O teto é por
ciclo, não licença para ocupar cinco horas quando os critérios já passaram.

### 3. Resolver grelha e autoridade

O orquestrador decide se abre `/grelhar`. Se abrir, fazer uma pergunta por vez e
STOP real. Se encerrar ou pular, não perguntar novamente. Decisão concreta não
respondida entra em `limites_de_decisao`; não virar escolha fingida.

### 4. Planejar por marcos

Só agora decompor. Para cada marco, definir:

- output e critério de aceite;
- dependências e dono;
- arquivos de leitura e escrita;
- prova necessária;
- tempo `[HEURÍSTICA]` e condição de corte;
- checkpoint de entrada e saída.

Separar workers por responsabilidade e manter um único writer por arquivo.
Checar cotas antes do brief. Escrever briefs autocontidos com objetivo, inputs,
escopo, critérios, proibições e formato da devolução.

### 5. Executar com workers persistentes

Reusar o mesmo worker quando continuidade de domínio reduzir risco. Trocar
worker apenas por indisponibilidade, especialidade ou falha comprovada; registrar
o handoff no disco.

Capacidade insuficiente não autoriza fingimento:

- menos workers: serializar e reduzir paralelismo;
- cota curta: fechar o marco atual, checkpoint e delta;
- harness/model low ou medium: reduzir tamanho dos lotes, aumentar testes
  determinísticos, fornecer exemplos canônicos e reservar julgamento ao papel
  competente;
- ferramenta ausente: usar alternativa verificável ou declarar limite.

Nunca afirmar que um worker executou, mediu ou revisou sem artefato ou log.

### 6. Rodar o Headhunter de Evolução por marcos

Nos marcos `IDEAL_DEFINIDO`, `INTEGRADO` e `PRE_ENTREGA`, abrir uma faixa
read-only em paralelo. Aplicar `/hypadododiabo` ao snapshot do marco para buscar
melhorias com upside real.

O Headhunter devolve somente:

```text
sugestao:
upside_e_mecanismo:
evidencia:
condicoes:
custo_estimado:
reversibilidade:
impacto_nos_criterios:
experimento_reversivel:
kill_criteria:
decisao_de_produto_envolvida:
```

Ele não edita, não muda baseline, não redefine ideal e não pede trabalho a
workers. Toda oportunidade passa pela segunda leitura abaixo antes de chegar ao
Sol. Sugestão sem evidência é descartada ou, se houver caminho real de prova,
classificada apenas como ponte.

### 6A. Fazer a dupla passagem “casa ≠ cabana”

Aplicar a qualquer sugestão de worker, Headhunter ou orquestrador:

**Passo A — construir.** Criar a melhor sugestão ou caminho para alcançar o
output ideal, com mecanismo e evidência disponíveis. Não rebaixar o ideal para
o que o harness consegue produzir.

**Passo B — tentar rejeitar.** Reler apenas a sugestão, o ideal, o baseline e a
rubrica. Perguntar:

1. Isto entrega o critério ideal ou apenas se parece com ele?
2. É relevante para a decisão e superior ao baseline?
3. Usa uma proxy adequada ou troca o objeto pedido por outro mais fácil?
4. A cadeia causal até o ideal está explícita e testável?
5. Existe custo, condição, evidência, prazo/etapa, próximo passo e kill criteria?

Aplicar o teste literal: se o pedido é **casa**, uma **cabana** não é solução.
Ela só pode ser `PONTE` quando houver uma cadeia causal real e aceita até a casa;
nunca renomear a cabana como casa.

Classificar:

- `SOLUÇÃO`: atende diretamente um ou mais critérios do ideal, supera ou
  preserva o baseline e tem prova adequada;
- `PONTE`: não entrega o ideal, mas possui cadeia causal explícita até ele,
  condição, prazo/etapa com fonte ou `[ESTIMATIVA]`, evidência, próximo passo,
  custo e kill criteria;
- `DISTRAÇÃO`: irrelevante, boba, inferior ao baseline, proxy inadequada ou sem
  cadeia causal testável.

Descartar sugestão óbvia que apenas repete o baseline e qualquer alternativa
inferior. `DISTRAÇÃO` não entra no backlog apresentado. Registrar rejeitadas
somente num log interno curto — identificador, resumo e razão — para evitar
redescoberta sem poluir a entrega.

### 7. Gate anti-scope-creep

Antes de incorporar qualquer sugestão, responder:

1. Qual evidência sustenta o upside?
2. Qual custo incremental e impacto no teto do ciclo?
3. A mudança é reversível? Qual rollback?
4. Qual critério ideal melhora e como medir?
5. Quais kill criteria encerram o teste?
6. Existe decisão concreta que pertence ao <USUARIO>?

Aceitar no ciclo somente `SOLUÇÃO` ou `PONTE` aprovada na segunda passagem e se
a sugestão for necessária para um critério do ideal
ou se tiver baixo custo, reversibilidade clara e ganho mensurável dentro do
orçamento. Caso contrário, registrar no backlog positivo priorizado. Se exigir
decisão do <USUARIO> e a grelha estiver encerrada/pulada, não aceitar: registrar
o limite, sem nova pergunta.

### 8. Verificar e decidir se o tempo extra compra algo

No fim de cada marco, comparar evidência com os critérios. Continuar somente se
o próximo bloco tiver uma compra explícita:

```text
TEMPO_EXTRA_COMPRA = EVIDENCIA | DECISAO | QUALIDADE_MENSURAVEL
```

Sem uma dessas três, parar o ciclo. Atualizar delta e backlog; não preencher o
tempo restante com polimento sem rubrica.

### 9. Fechar a entrega

Entregar:

1. resultado validado, com paths e provas;
2. critérios do ideal atendidos e não atendidos;
3. delta para o ideal, sem eufemismo;
4. limites de ferramenta, cota, modelo, runtime e autoridade;
5. backlog positivo priorizado por impacto, evidência, custo e reversibilidade,
   contendo somente `SOLUÇÃO` ou `PONTE` defensável;
6. sugestão objetiva do próximo ciclo;
7. classificação final e gasto real contra o orçamento `[HEURÍSTICA]`.

Dentro de `/orquestracao1`, somente o Sol apresenta. Fable roda no máximo uma
vez, após candidato final real e apenas para N1 complexo/N3 com risco material:
`MEDIUM` por padrão, `LOW` por cota/escopo estreito com downgrade declarado e
`HIGH/XHIGH` só por flag grande justificada. Resolver o modelo via
`FABLE_LATEST`; nunca inventar sucessor nem trocar por Sonnet/Opus.
Quando `FABLE_PERTO_DO_LIMITE` estiver medido, Kimi `>=3` saudável pode ser o
único fallback, com o candidato final e rubrica comprimida; sem Kimi saudável,
declarar a indisponibilidade. Nunca chamar Fable e Kimi no mesmo ciclo.
`/advogadododiabo` só entra quando
downside ou custo do erro merece contraste. Na dúvida, não chamar e registrar
revisão interna curta.

## Casos de decisão

| Entrada | Resposta |
|---|---|
| tarefa pequena | `NAO_APLICAVEL`; fluxo comum, sem advogado/revisor |
| projeto grande com ideal estimado em até 5h | calcular 70% `[HEURÍSTICA]`, executar por marcos |
| ideal estimado acima de 5h | `ULTRACODE_REAL`; primeiro marco seguro + mapa de continuação |
| cota insuficiente | manter ideal; serializar/reduzir escopo do ciclo; checkpoint + delta |
| boa sugestão do Headhunter | passar gate e incorporar só com ganho mensurável dentro do teto |
| sugestão com scope creep | backlog ou descarte; baseline intacto |
| harness low/medium | lotes menores, provas determinísticas e limites declarados; não fingir capacidade |
| “quero uma casa” e recebe cabana | rejeitar como `SOLUÇÃO`; proxy não atende o ideal |
| cabana temporária com cadeia real | admitir somente como `PONTE`, com etapa, custo e kill criteria |
| sugestão positiva irrelevante | `DISTRAÇÃO`; log interno curto, fora da entrega |
| melhoria superior ao baseline | `SOLUÇÃO` ou `PONTE` conforme o critério, com evidência apresentada |

## Como isso costuma dar errado

1. **Planejar antes do ideal.** A equipe otimiza o que é fácil, não o que
   aprova a entrega.
2. **70% vira promessa.** A heurística é tratada como cronograma garantido.
3. **Cinco horas viram meta.** O ciclo continua depois de os critérios passarem.
4. **Modelo fraco rebaixa a rubrica.** Limitação de execução é escondida como
   “qualidade suficiente”.
5. **Persistência vira dependência.** O estado mora só na memória do worker.
6. **Headhunter vira diretor.** Uma sugestão altera baseline sem gate humano.
7. **Backlog invade o ciclo.** Melhorias positivas competem com critérios
   obrigatórios sem custo comparado.
8. **Grelha reabre.** Depois da autonomia, uma decisão pendente vira nova
   entrevista em vez de limite explícito.
9. **Cabana vendida como casa.** Uma proxy fácil recebe o rótulo de solução e o
   objetivo é rebaixado ao alcance do harness.
10. **Cemitério de ideias na entrega.** Distrações rejeitadas poluem o backlog e
    parecem opções ainda abertas.
