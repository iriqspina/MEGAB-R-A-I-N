---
name: orquestracao1
description: Orquestra entrega complexa com um orquestrador único resolvido por medição, até cinco workers paralelos com escopos separados, /grelhar opcional com STOP real, /quaseultracode em projeto grande, as lentes /hypadododiabo e /advogadododiabo, e uma única revisão adversarial final com effort adaptado ao risco e à cota. Use quando o usuário digitar /orquestracao1, pedir orquestração multiagente, falar em estagiários ou workers em paralelo, ou pedir decomposição com revisão adversarial.
---

# orquestracao1 — o orquestrador coordena, workers executam, o revisor questiona

**v0.5 · 260905.** Conduzir uma entrega complexa com um único responsável pela
decisão final. Separar execução, síntese, revisão adversarial e decisão humana.

## Contrato imutável

1. Usar **um único orquestrador**, resolvido por medição e nunca por slug fixo.
   `ORQUESTRADOR_RESOLVIDO` é o agente de ponta que ocupa a raiz da conversa e
   tem cota saudável medida agora. Ordem de preferência: o modelo que o <USUARIO>
   já colocou na raiz; se ele não designou, o mais capaz com cota entre os
   harnesses disponíveis. Registrar no checkpoint: harnesses e modelos listados,
   escolhido, cota medida e horário. Só o orquestrador decompõe, aceita ou
   rejeita trabalho, consolida o candidato e apresenta a entrega ao <USUARIO>.
2. Usar **até 5 workers**, com `high`/`xhigh` conforme a tarefa, no harness que
   tiver cota. Paralelizar só por independência real: cada worker recebe um
   artefato, uma responsabilidade e um escopo de escrita exclusivo. Dois writers
   no mesmo arquivo é falha, não paralelismo. O worker entrega ao orquestrador;
   nunca apresenta o resultado final como se fosse ele.
3. Usar **Fable como revisor questionador primário**, no máximo uma chamada por
   entrega, somente depois de o orquestrador ter um candidato final verificado e quando
   a entrega não trivial tiver risco material. Se a saúde/cota medida mostrar
   `FABLE_PERTO_DO_LIMITE`, usar **Kimi `>=3` saudável** como único fallback,
   sem chamar Fable antes. Há no máximo **uma chamada de revisor** por entrega.
   Usar `MEDIUM` por padrão elegível; `LOW` só por cota ou revisão estreita, com
   downgrade declarado; `HIGH`/`XHIGH` só por flag grande, cota medida e
   justificativa registrada. Fable ou Kimi questionam; não executam, editam,
   chamam ferramenta ou conversam com workers.
4. O **orquestrador decide** se vale abrir `/grelhar`; <USUARIO> não precisa declarar que
   a pulou. Se ativada, fazer uma pergunta por vez, em campo livre, encerrar o
   turno e esperar resposta explícita. Não usar opção preselecionada,
   auto-resposta, simulação do <USUARIO> ou avanço por timeout.
5. Depois de a grelha terminar ou ser pulada, entrar em **modo autônomo**: não
   fazer novas perguntas; decidir apenas o operacional reversível e dentro do
   escopo; registrar suposições e entregar. Decisão concreta de produto que ficou
   sem resposta vira limite explícito, nunca escolha fingida. Só parar por
   bloqueio material de segurança ou autoridade não concedida.
6. Declarar quando Fable não rodou. Nunca substituir “revisão Fable” por revisão
   do próprio orquestrador nem escrever que houve revisão independente quando não houve.
7. Tratar `/hypadododiabo` e `/advogadododiabo` como lentes opcionais de análise,
   não como workers ou revisores finais. Sugerir sem ativar; se ambas forem
   aceitas, rodar uma vez cada sobre os mesmos fatos e proibir loop entre elas.
8. Poder ativar `/quaseultracode` em projeto grande somente por invocação ou
   aceite explícito. O orquestrador continua orquestrador; o modo adiciona ideal-first,
   teto de 5h `[HEURÍSTICA]`, workers persistentes, checkpoints, Headhunter e
   gate anti-scope-creep sem rebaixar a qualidade-alvo.

Estas regras específicas vencem defaults mais gerais. Nesta skill, “uma pergunta
por vez” substitui o agrupamento de uma fronteira inteira previsto pela
`/grelhar` v1.0.

## Invocação curta

Em qualquer projeto onde o plugin do megabrain esteja instalado, a chamada
mínima é uma linha:

```text
/orquestracao1 <objetivo em uma frase>
```

Isso já implica os defaults e dispensa redescrever a topologia: orquestrador
resolvido por medição, até 5 workers paralelos, grelha decidida pelo
orquestrador, lentes desligadas e uma revisão adversarial final quando a
entrega tiver risco material.

Modificadores opcionais, na mesma linha, só quando o default não serve:

| Escrever | Efeito |
|---|---|
| `sem grelha` | pula a grelha e entra direto em modo autônomo |
| `com hype` | roda `/hypadododiabo` uma vez sobre o pacote factual |
| `com advogado` | roda `/advogadododiabo` uma vez sobre o mesmo pacote |
| `sozinho` | zero workers; o orquestrador executa tudo |
| `N estagiários` | teto de workers paralelos, com `N <= 5` |
| `sem revisor` | força `FABLE_OFF` e assume a revisão interna do orquestrador |
| `projeto grande` | avalia `/quaseultracode` antes de decompor |

Modificador só aperta o contrato; nunca afrouxa proibição dura. `sem revisor`
numa entrega com risco material vira limite declarado na entrega, jamais uma
revisão fingida. Se o projeto tiver instruções próprias que conflitem com este
contrato, as instruções do projeto vencem e a divergência é registrada.

## Cabeçalho fixo de resposta (v0.3 · 260905, pedido do <USUARIO>)

Toda resposta dada enquanto uma entrega `/orquestracao1` estiver ativa — abertura,
pergunta da grelha, status, devolução de worker, entrega final — começa com três
blocos, nesta ordem, antes de qualquer corpo:

```text
📌 Prompt de origem: "<o prompt literal que abriu a orquestração>"
🧭 O que entendi: <prompt retrabalhado em até 3 linhas — objetivo, entregável, critério>
TL;DR: <a resposta ou o estado atual em 1–3 linhas>
```

Regras:

- `Prompt de origem` é o pedido que ABRIU a orquestração, citado literalmente
  (cortar com `[…]` só o que não muda o sentido). Não é a última mensagem dele.
  Só muda se o <USUARIO> reescopar; aí registrar a troca no checkpoint.
- `O que entendi` é o PROMPT RETRABALHADO do alinhamento pré-prompt, atualizado
  quando o entendimento mudar (grelha respondida, limite descoberto).
  **Forma (v0.4 · 260905, pedido dele):** em tópicos numerados, e sempre que a ideia
  passar mais fácil visualmente, um infográfico no lugar da prosa — no terminal,
  diagrama em caixa/seta dentro de bloco de código; em artefato Traycer/HTML, mermaid.
  O infográfico nunca vai sozinho: uma linha de apoio escrito embaixo diz o que ele
  mostra. Fluxo, papéis, antes/depois e dependência são casos de infográfico;
  critério, número e restrição continuam em texto.
- `TL;DR` é o de sempre; o corpo segue o nível N0–N3 do contrato de resposta
  (`referencias/260818_padrao-resposta.md`).
- Os três blocos são curtos: juntos, no máximo ~8 linhas. Existem pra ele
  conferir de relance que o agente ainda está fazendo o que foi pedido.
- Vale pra qualquer agente que esteja no papel de orquestrador; worker não
  responde ao <USUARIO>, então não usa o cabeçalho.

## Papéis

| Papel | Pode | Não pode | Saída |
|---|---|---|---|
| Orquestrador resolvido, único | enquadrar, optar pela grelha, decompor, despachar, sintetizar, verificar, reparar uma vez, apresentar | delegar a decisão final ou fingir revisão externa | plano, candidato final, entrega final |
| Worker de análise (`high`/`xhigh`) | arquitetura, análise, pesquisa delimitada, crítica técnica quando o brief pedir | coordenar outros papéis, editar fora do escopo, apresentar ao <USUARIO> | artefato ou parecer com evidência |
| Worker de implementação (`high`) | implementação, teste, automação e inspeção delimitada | decidir requisito humano, tocar produção sem autorização, apresentar ao <USUARIO> | diff, arquivos, comandos e resultados |
| `/hypadododiabo`, lente positiva | construir o melhor caso defensável, com condições, custos, experimento e kill criteria | fazer propaganda, inventar probabilidade, decidir produto | upside condicionado e `SEGUIR` / `TESTAR PEQUENO` / `ADIAR` / `NÃO SEGUIR` |
| `/advogadododiabo`, lente de downside | expor risco material e custo do erro quando o contraste for útil | aparecer em conversa ordinária, conversar em loop com a lente positiva | downside defensável para síntese do orquestrador |
| `/quaseultracode`, modo de projeto grande | definir ideal antes do plano, controlar ciclo e delta, manter workers/checkpoints | substituir o orquestrador, rebaixar rubrica por modelo ou comprimir projeto acima de 5h | resultado validado, delta, limites, backlog e próximo ciclo |
| Fable adaptativo, revisor final primário | levantar as objeções fortes contra o candidato comprimido no effort justificado | executar, editar, chamar ferramenta, pedir correção ao worker, receber histórico bruto | veredito, objeções, saúde/cota e effort usado para o orquestrador |
| Kimi `>=3`, fallback questionador | revisar o mesmo candidato comprimido quando `FABLE_PERTO_DO_LIMITE` e sua saúde/cota estiverem medidas | substituir Fable por conveniência, receber histórico bruto, falar com workers, executar ou editar | veredito, modelo exato, saúde/cota, effort e justificativa do fallback |
| <USUARIO> | decidir gosto, prioridade, autorização e risco aceitável quando a grelha for aberta | ser simulado por agente; precisar declarar que pulou a grelha | resposta humana explícita |

Antes de criar ou reconfigurar agentes no Traycer, ler o guia de seleção de
agentes. Medir perfis e cotas antes de escrever briefs. Não despachar um worker
para descobrir depois que o provedor estava indisponível.

## Roteador de modos e lentes

No início de uma nova conversa ou projeto, oferecer uma vez, sem pergunta e sem
ativar nada:

> Modos opcionais: /orquestracao1 para trabalho multiagente · /hypadododiabo para explorar o melhor caso com limites reais.

Se o início for um projeto grande, sugerir `/quaseultracode` uma vez. Não
sugerir em conversa ordinária ou tarefa pequena.

Durante o andamento, sugerir somente numa transição material: novo escopo,
decisão difícil, bloqueio, pré-implementação de risco, pré-entrega não trivial
ou análise unilateral. `/advogadododiabo` só merece sugestão quando downside ou
custo do erro requer contraste; não usar como ritual de toda entrega.

Aplicar cooldown por estágio. Registrar `SUGERIDO`, `ATIVADO`, `RECUSADO` ou
`NAO_APLICAVEL`; não repetir modo recusado no mesmo estágio e não interromper
conversa ordinária, status, esclarecimento ou correção local óbvia. Uma mudança
material de estágio pode liberar nova sugestão. Sugestão nunca equivale a
consentimento.

Considerar `/quaseultracode` também em novo escopo, bloqueio relevante,
pré-implementação de risco ou quando o ciclo precisa atravessar sessões. Se a
estimativa ideal ultrapassar 5h, registrar `ULTRACODE_REAL` e entregar mapa de
continuação; não vender o mesmo trabalho como ciclo curto.

## Estado persistente

Guardar o estado num artifact, ticket ou arquivo de handoff; não depender do
histórico da conversa. Usar exatamente um destes estados:

```text
ENQUADRANDO
AGUARDANDO_<USUARIO>
PLANEJADO
EXECUTANDO
SINTETIZANDO
CANDIDATO_FINAL
REVISANDO_COM_FABLE
REPARANDO
VERIFICADO
APRESENTADO
FALHA_DECLARADA
```

Registrar no checkpoint:

- objetivo e decisão que a entrega precisa permitir;
- critérios verificáveis e restrições duras;
- estado da grelha: `ATIVA`, `CONCLUIDA` ou `PULADA`;
- modos/lentes sugeridos, ativados ou recusados no estágio atual;
- lentes já executadas sobre o pacote factual, para impedir repetição e loop;
- classificação `QUASEULTRACODE`, `ULTRACODE_REAL` ou `NAO_APLICAVEL`, quando
  o modo for avaliado;
- ideal, orçamento `[HEURÍSTICA]`, tempo consumido, marcos e delta restante;
- papéis, modelos, reasoning e escopos de escrita;
- arquivos/artefatos de entrada e saída;
- orçamento e estado das cotas;
- resolução `FABLE_LATEST`: modelos listados, versão compatível escolhida e
  saúde/cota medida; quando houver fallback, modelo Kimi exato (`>=3`),
  saúde/cota, effort e justificativa;
- evidências, incertezas, falhas e próximo verbo + objeto;
- ledger de ações sensíveis: ação, motivo, alvo, flags e resultado.

`REVISANDO_COM_FABLE` só pode suceder `CANDIDATO_FINAL`. `APRESENTADO` só pode
suceder `VERIFICADO`. Se o fluxo precisar mentir sobre essa ordem para avançar,
marcar `FALHA_DECLARADA` e parar.

## Inputs mínimos

Não despachar antes de resolver estes inputs por inspeção, pela grelha opcional
ou por premissas seguras registradas:

1. Pedido literal e artefato final.
2. Leitor e decisão que ele toma com o artefato.
3. Três critérios verificáveis.
4. Restrição dura e ações que exigem autorização separada.
5. Fontes canônicas, estado real, trava e trabalho não commitado.
6. Ferramentas, modelos, perfis e cotas realmente disponíveis.
7. Limite de escrita de cada worker.

Fato observável é trabalho do agente: abrir arquivo, medir runtime, consultar
estado. Gosto, prioridade, aceite de risco e autorização são do <USUARIO>. No
modo autônomo, não inventar sua fala: decidir só o operacional reversível e
registrar a premissa conservadora. Decisão concreta de produto não respondida
limita o resultado.

## Outputs obrigatórios

1. **Plano de execução:** dependências, paralelismo possível e dono de cada
   saída.
2. **Brief por worker:** objetivo, inputs mínimos, escopo, restrições, critérios,
   formato de resposta e proibições.
3. **Evidência de execução:** diff, arquivo, log, teste ou medição proporcional ao
   risco.
4. **Candidato final do orquestrador:** consolidado e verificado antes do revisor final.
5. **Registro da revisão:** `FABLE_OFF`, `FABLE_REVISOU_LOW_DECLARADO`,
   `FABLE_REVISOU_MEDIUM`, `FABLE_REVISOU_HIGH`, `FABLE_REVISOU_XHIGH`,
   `FABLE_NAO_EXECUTADO`, `KIMI_FALLBACK_REVISOU_*` ou
   `KIMI_FALLBACK_NAO_EXECUTADO`, com modelo exato, saúde/cota, effort, flag e
   motivo. O fallback Kimi só vale após `FABLE_PERTO_DO_LIMITE` medido.
6. **Entrega final do orquestrador:** resultado, evidência, limites e decisão pendente.
7. **Ledger de modos:** estágio, sugestão, aceite/recusa, motivo e resultado;
   nenhuma sugestão conta como ativação.
8. **Fechamento Quase Ultracode, quando ativo:** resultado validado, delta para
   o ideal, limites, backlog positivo priorizado e sugestão do próximo ciclo.

## Fluxo

### 0. Confirmar identidade e estado

1. Resolver `ORQUESTRADOR_RESOLVIDO`: listar harnesses, perfis e modelos
   realmente disponíveis, medir cota e fixar quem ocupa a raiz. O agente atual
   só assume o papel se for o resolvido; caso contrário, transferir. Registrar
   a lista observada, o escolhido, a cota e o horário da medição.
2. Ler as instruções do projeto, estado, handoff, fim das decisões, lições e
   trava antes de escrever.
3. Medir Git, arquivos e runtime. Saída de outro agente continua rascunho até
   existir e ser inspecionada.
4. Ler o registro de papéis do Traycer e não sobrepor responsabilidade já
   assumida.

Se nenhum agente de ponta com cota saudável estiver disponível, informar que a
topologia exigida não está disponível e parar antes de executar a entrega. Não
rebaixar o orquestrador para um modelo de volume por conveniência.

### 0A. Procedimento de resolução do orquestrador

Quem mede é o agente que recebeu a invocação, no turno em que ela chega — não vale
cota lida em sessão anterior. A resolução tem três passos e sempre termina registrada:

1. **Listar** harnesses, perfis e modelos realmente disponíveis agora.
2. **Medir** cada candidato na fonte que aquele provedor expõe:

| Fonte | O que ela dá | Quando o dado é considerado fresco |
|---|---|---|
| percentual por janela do provedor | uso agregado da conta | medido neste turno |
| campo por modelo, quando existir | uso do modelo específico | medido neste turno |
| execução bem-sucedida de um agente naquele harness | disponibilidade, não cota | dentro desta sessão |

3. **Escolher** por esta ordem, registrando o motivo: (a) o agente que o <USUARIO>
   colocou na raiz, se a medição não o mostrar no teto; (b) o mais capaz entre os que
   sobraram com folga medida; (c) parar e declarar, se nenhum tiver folga.

Provedor que não expõe percentual não vira exceção silenciosa: registrar
`COTA_NAO_EXPOSTA`, tratar disponibilidade comprovada por execução como saúde
**parcial**, e nunca promovê-lo a orquestrador quando existir um candidato com cota
medida. Cota agregada da conta não substitui a do modelo: a conta pode estar em 65%
enquanto o modelo que você quer usar está em 90%.

Se o preferido estiver no teto, o desvio para outro harness é obrigatório e vai no
checkpoint com a medição que o justificou. Preferência do <USUARIO> é desempate entre
candidatos saudáveis, nunca autorização para usar um candidato no limite.

### 0B. Perfil regular — quem faz o quê por padrão (<USUARIO>, 260905)

Vale para tarefa regular (N1 comum, N3 sem flag grande). É o ponto de partida; a
medição de 0A pode desviar por cota, nunca por preferência de modelo.

| Papel | Padrão Claude | Equivalente Codex | Equivalente Kimi | Effort |
|---|---|---|---|---|
| Orquestrador (N0, único que cria agentes) | **Opus 5** | gpt-6-astra | — (não orquestra) | Opus 5: `LOW` a `XHIGH` por conta própria, escolhendo pelo risco (cota compartilhada com Sonnet/Haiku, não com Fable). gpt-6-astra: `LOW`/`MEDIUM` |
| Copiloto do orquestrador (N0', lê o plano, decomposição e briefs do Opus antes do despacho; devolve objeções e sugestões; não cria agentes, não edita, não fala com o <USUARIO>) | **Fable** | gpt-6-astra | — | `LOW` (`MEDIUM` só se o Opus pedir e a cota Fable estiver verde) |
| Executor-coordenador (N1, briefa e aceita, não edita) | Opus 5 ou Sonnet | gpt-5.6-sol | — | `MEDIUM` |
| Revisor final (N1, só lê) | **mínimo Sonnet `XHIGH` · máximo Fable `MEDIUM`** | mínimo gpt-5.6-sol `XHIGH` · máximo gpt-6-astra `MEDIUM` | Kimi `>=3` thinking, só como fallback medido | dentro da faixa; ver §7 |
| Worker de edição (N2, 1 writer por ambiente) | Sonnet | gpt-5.6-sol | Kimi 2.7 (cota > 20 %) | `LOW`; sobe para `MEDIUM` após 1 falha de evidência |
| Worker de checagem (N2: hash, grep, contagem) | Haiku | — | — | padrão |

Regras do perfil:

1. **Fable e gpt-6-astra só em `LOW`/`MEDIUM` por conta própria.** Fable tem cota
   própria (campo "Fable" no Claude Max), por isso é o mais limitado; `HIGH`, `XHIGH`
   ou `MAX` nele ou no Astra exigem pergunta ao <USUARIO> no turno, com a flag que
   justifica; sem resposta, ficar em `MEDIUM` e registrar `EFFORT_ALTO_NAO_AUTORIZADO`.
   **Opus 5 como orquestrador é exceção:** divide cota com Sonnet/Haiku, não com Fable,
   e pode usar `HIGH`/`XHIGH` sem perguntar quando a decomposição ou o aceite pedirem;
   `MAX` continua exigindo pergunta. Sonnet `XHIGH` não é frontier: é o piso do revisor.
2. **Fable é revisor, não orquestrador.** Só entra em `MEDIUM` (teto do perfil). Fable
   `HIGH` ou acima cai na regra 1.
3. **Escolha do revisor dentro da faixa:** Sonnet `XHIGH` para entrega sem flag grande
   ou quando Fable estiver perto do limite medido; Fable `MEDIUM` quando houver risco
   material (produção, rollback difícil, evidência incerta). Registrar qual e por quê.
4. **Família do revisor ≠ família do executor** quando houver duas com cota verde.
5. **Cascata, não prestígio:** começar no modelo/effort mais barato da linha; subir um
   degrau só após falha de evidência registrada. "Caprichar" não é flag.
6. Cota medida antes de cada despacho (0A). Kimi não expõe cota ao Traycer: ler em
   `kimi.ai/settings/subscription?tab=quota` pela aba logada do Chrome.
7. Fora do perfil regular (ex.: `/quaseultracode`, deploy em produção, dado irreversível),
   o <USUARIO> escolhe a árvore; propor a tabela acima com os desvios marcados.
8. **Copiloto Fable low (<USUARIO>, 260905).** O Opus 5 orquestra; o Fable low é criado
   por ele no início como ajudante de planejamento e orquestração. Fluxo: Opus escreve
   plano + decomposição + briefs em arquivo → Fable low lê e devolve, em arquivo, no
   máximo 5 objeções ou melhorias (escopo esquecido, writer duplo, gate sem evidência,
   pergunta que deveria ir ao <USUARIO>, risco não medido) → Opus decide e despacha.
   Repetir no checkpoint de meio de execução e antes do candidato final. O copiloto
   **não substitui o revisor final** (§7: Sonnet `XHIGH` a Fable `MEDIUM`, uma chamada);
   se o revisor final for Fable, o copiloto conta como a mesma família e o Opus registra
   isso. O copiloto não cria agentes, não edita produto, não fala com o <USUARIO> e não
   recebe histórico bruto: recebe o plano comprimido e os briefs. Se a cota Fable estiver
   amarela ou vermelha, o Opus registra `COPILOTO_OFF` e segue sozinho.
9. **Rodapé de cota (<USUARIO>, 260905).** Enquanto qualquer provedor em uso nesta
   orquestração estiver com **65 % ou mais** de uma janela consumida, toda resposta ao
   <USUARIO> termina com uma linha de cota, no formato
   `⛽ Claude 5h 80% (reset 01:20) · 7d 27% · Codex 7d 74% · Kimi mês 99% (12/09)`,
   só com os provedores que passaram de 65 %. Fonte: `traycer_get_provider_profile_rate_limits`
   no turno; se a leitura vier vazia, usar a última válida com a hora e marcar `(última leitura HH:MM)`;
   Kimi vem de `kimi.ai/settings/subscription?tab=quota` ou de print dele. Abaixo de 65 % em
   todos, sem rodapé. A linha não substitui o gate de cota antes de despacho (regra 6).

### 1. Decidir se `/grelhar` entra

O orquestrador ativa a grelha quando uma decisão humana precisa ser resolvida antes da
execução. <USUARIO> pode encerrá-la, mas não precisa declarar que foi pulada. Se
o orquestrador não a abrir, registrar `PULADA`. Usar `ATIVA`, `CONCLUIDA` ou `PULADA`.

Se `ATIVA`:

1. Carregar `/grelhar` para separar fatos de decisões.
2. Resolver fatos localmente antes de perguntar.
3. Escolher a primeira decisão da fronteira atual.
4. Fazer **uma** pergunta clara, com impacto e recomendação, em campo livre e
   sem opções marcadas.
5. Mudar o estado para `AGUARDANDO_<USUARIO>` e **encerrar o turno**.
6. Depois da resposta, registrar a decisão, recalcular a fronteira e repetir ou
   encerrar a grelha.

Durante `AGUARDANDO_<USUARIO>`, é proibido despachar agentes, editar arquivos,
executar a recomendação ou interpretar silêncio como concordância. Só uma
resposta real — inclusive uma ordem explícita de corte como “toca”, “chega” ou
“pula” — destrava o próximo passo.

Só o orquestrador que abriu a pergunta pode fechá-la. Usar a mensagem real do usuário;
se outro agente apenas relatar a resposta, verificar o transcript de origem e o
`<user_message>` antes de tratá-la como autorização. Decisão registrada em fonte
canônica também vale. Telefone sem fio não fecha gate humano.

Se `CONCLUIDA` ou `PULADA`, não fazer nova pergunta. Entrar no modo autônomo,
escolher somente a operação segura, reversível e in-scope, marcar o que não foi
confirmado e prosseguir. Não tomar decisão concreta de produto em nome do
<USUARIO>; tratá-la como limite da entrega. Autoridade ausente para ação material
é bloqueio declarado.

### 2. Fixar o problema e os critérios

Escrever uma frase falseável para o problema. Separar:

- o que precisa mudar;
- o que deve permanecer idêntico;
- como cada critério será medido;
- o que fica fora desta rodada;
- o que exige nova autorização.

Não iniciar otimização ou design enquanto “melhor” ainda significar apenas gosto
ou adjetivo. No modo autônomo, escolher a interpretação de menor risco e
registrar a incerteza em vez de perguntar de novo.

### 2A. Sugerir ou aplicar lentes opcionais

Na transição entre enquadramento e execução, avaliar se a análise está
unilateral. Não interromper o trabalho só para cumprir simetria.

1. Se houver upside plausível subexplorado, sugerir `/hypadododiabo` uma vez.
2. Se houver downside material ou alto custo do erro, sugerir
   `/advogadododiabo` uma vez.
3. Não ativar nenhuma lente sem aceite explícito. Registrar recusa e respeitar
   o cooldown do estágio.
4. Se ambas forem ativadas, entregar o mesmo pacote factual a cada lente, uma
   vez, e sintetizar condições, evidência, reversibilidade e custo do erro.
5. Proibir que uma lente responda à outra. A síntese pertence ao orquestrador.

`/hypadododiabo` deve produzir upside, evidência, condições, limites, custos,
experimento reversível, kill criteria e um veredito entre `SEGUIR`,
`TESTAR PEQUENO`, `ADIAR` ou `NÃO SEGUIR`. Se o melhor caso continuar ruim,
preservar `NÃO SEGUIR`; não fabricar defesa. Nenhuma lente decide produto pelo
<USUARIO> ou substitui o candidato final.

### 2B. Ativar `/quaseultracode` em projeto grande

Se o pedido direto ou aceite humano ativar o modo:

1. Carregar `/quaseultracode` e definir output ideal, leitor, decisão, critérios
   e restrições antes de decompor.
2. Estimar o ciclo Ultracode e calcular o orçamento de cerca de 70%
   `[HEURÍSTICA]`, limitado a 5h.
3. Se o ideal estimado ultrapassar 5h, classificar `ULTRACODE_REAL`, executar
   somente um primeiro marco seguro e entregar mapa de continuação.
4. Manter a qualidade-alvo independente de harness/model/effort. Compensar
   capacidade menor com lotes menores, serialização e mais prova; declarar o
   delta que permanecer.
5. Manter workers úteis entre marcos e checkpoints no disco. Nenhum worker
   substitui o orquestrador ou vira fonte única de estado.
6. Rodar o Headhunter de Evolução read-only com `/hypadododiabo` nos marcos. Ele
   só sugere; toda evolução passa pelo gate anti-scope-creep da skill.
7. Continuar tempo extra apenas se comprar evidência, decisão ou qualidade
   mensurável.

Se o modo foi apenas sugerido, não executar estes passos. Registrar o estado e
seguir a orquestração comum.

### 3. Orçar e decompor

1. Consultar o guia de seleção e a cota do perfil antes do primeiro despacho.
2. Fazer um grafo simples de dependências. Paralelizar apenas tarefas sem input
   pendente entre si.
3. Dar a cada worker um artefato, uma responsabilidade e um limite de escrita.
4. Impedir dois writers no mesmo arquivo. Se duas análises precisam do mesmo
   alvo, deixá-las read-only e manter um único escritor.
5. Salvar briefs autocontidos no disco quando a tarefa for longa. Passar o
   caminho, não o histórico inteiro.

Preferir Sonnet `xhigh` para arquitetura ambígua e Codex `high` para
implementação/teste. Usar só um deles quando a decomposição não justificar dois.
“Mais agentes” não é critério de qualidade.

### 4. Executar com workers

Cada brief deve conter:

```text
PAPEL
OBJETIVO
INPUTS CANÔNICOS
ESCOPO DE LEITURA
ESCOPO DE ESCRITA
CRITÉRIOS DE ACEITE
PROIBIÇÕES
FORMATO DA DEVOLUÇÃO
```

O orquestrador acompanha pelo estado e pelos artefatos. Não usa respostas de worker como
prova sem abrir os arquivos e conferir os testes. Resposta assíncrona pendente
não autoriza polling insistente nem trabalho duplicado.

Em `/quaseultracode`, preferir workers persistentes entre marcos quando isso
preservar contexto de domínio. Mesmo assim, gravar cada checkpoint e brief no
disco; troca por cota ou harness não pode apagar estado.

### 5. Sintetizar e formar o candidato final

1. Conferir cada saída contra seu brief.
2. Resolver contradições com evidência; não por votação entre modelos.
3. Integrar num único candidato.
4. Rodar lint, testes, inspeção visual ou cálculo necessários.
5. Auditar e reparar o candidato uma vez contra os critérios.
6. Registrar `CANDIDATO_FINAL` somente quando o orquestrador aceitaria apresentar o
   trabalho mesmo se o revisor final estivesse indisponível.

Fable não serve para descobrir que o candidato nem abria, que o teste não rodou
ou que faltava requisito conhecido.

### 6. Decidir se a revisão questionadora está `OFF` ou elegível

Chamar Fable somente em entrega **N1 complexa ou N3** com risco material de
decisão, implementação ou apresentação. Ainda é obrigatório existir candidato
final real.

Não chamar Fable, Kimi ou outro advogado do diabo em:

- conversa ordinária ou tarefa N0;
- esclarecimento ou status;
- ajuste pequeno;
- correção local óbvia;
- entrega rotineira coberta por template já provado.

Na dúvida, **não chamar**. Registrar `FABLE_OFF`, executar uma revisão interna
curta do orquestrador e seguir. Isso não é fallback por falha: o gate não era necessário.

### 7. Resolver `FABLE_LATEST`, medir saúde, rotear effort e chamar uma vez

Tratar `FABLE_LATEST` como alias lógico, nunca como slug fixo:

1. Listar os modelos atuais do harness Claude.
2. Filtrar somente a família Fable com versão `>= 5.1` e compatível com o
   runtime atual.
3. Preferir a maior versão compatível realmente listada.
4. Se a única opção for `claude-fable-5-1[1m]`, usar exatamente essa.
5. Se nenhuma Fable compatível existir, registrar `FABLE_NAO_EXECUTADO`; não
   inventar sucessor e não trocar por Sonnet, Opus ou outra família.
6. Gravar no checkpoint: alias, lista observada, modelo resolvido, versão,
   compatibilidade e horário da medição.

Medir imediatamente antes da revisão a disponibilidade real e a cota do Fable
resolvido. Tratar como `FABLE_PERTO_DO_LIMITE` somente quando a medição atual
mostrar que ele não tem cota saudável para a revisão no effort roteado; não usar
percentual histórico ou palpite. Se Fable estiver saudável, ele é o único
revisor chamado. Se estiver perto do limite, medir também a disponibilidade real
e a cota de Kimi compatível `>=3`.

Kimi é permitido somente com `FABLE_PERTO_DO_LIMITE` registrado e se o modelo
Kimi `>=3` passar a medição de saúde/cota. Sem Kimi saudável, registrar
`KIMI_FALLBACK_NAO_EXECUTADO`; não inventar sucessor, não trocar por outra
família e não chamar Fable depois. A ausência de Fable compatível também não
autoriza Kimi: registrar `FABLE_NAO_EXECUTADO`.

Modelo e effort são decisões separadas. Resolver `FABLE_LATEST`, medir saúde e
decidir o revisor primeiro; só depois escolher o esforço abaixo.

Escolher e registrar exatamente um nível para o revisor selecionado:

| Estado | Quando usar | Registro obrigatório |
|---|---|---|
| `OFF` | conversa comum, N0, status, ajuste pequeno ou entrega sem risco material | `FABLE_OFF` + motivo; nenhuma chamada |
| `MEDIUM` | revisão final elegível normal | `FABLE_REVISOU_MEDIUM` ou `KIMI_FALLBACK_REVISOU_MEDIUM`, modelo exato, saúde/cota e escopo |
| `LOW` | cota crítica ou revisão estreita e delimitada | `FABLE_REVISOU_LOW_DECLARADO` ou `KIMI_FALLBACK_REVISOU_LOW_DECLARADO`, cota, downgrade, risco aceito e o que ficou fora |
| `HIGH` | uma flag grande com custo de erro ou rollback difícil · **só com autorização do <USUARIO> no turno (0B regra 1)** | `FABLE_REVISOU_HIGH` ou `KIMI_FALLBACK_REVISOU_HIGH`, flag, cota, justificativa e a mensagem dele que autorizou |
| `XHIGH` | múltiplas flags grandes, raio alto e evidência materialmente incerta · **só com autorização do <USUARIO> no turno** | `FABLE_REVISOU_XHIGH` ou `KIMI_FALLBACK_REVISOU_XHIGH`, flags, cota, justificativa e a mensagem dele que autorizou |

Sonnet `XHIGH` como revisor é o piso do perfil regular (0B) e não entra na regra de
autorização: a regra vale para Fable e gpt-6-astra (cota própria/apertada). Opus 5 no
papel de orquestrador pode ir a `HIGH`/`XHIGH` sem perguntar (0B regra 1).

Flags grandes: ação irreversível ou destrutiva, segurança, produção, custo/raio
alto, rollback difícil ou evidência incerta. Não elevar por prestígio, tamanho
do texto ou desejo de “caprichar”. Se `LOW` não puder examinar com segurança um
risco material, não fingir cobertura: usar `FABLE_NAO_EXECUTADO` ou
`KIMI_FALLBACK_NAO_EXECUTADO` e declarar o bloqueio.

O padrão de entrega elegível é `MEDIUM`. `LOW` é downgrade; `HIGH`/`XHIGH` são exceções
justificadas **e autorizadas por ele no turno**. Fable e Kimi `>=3` usam o mesmo padrão adaptativo. Em qualquer
effort, executar uma única chamada final de revisor.

Enviar somente este schema comprimido, derivado do contrato do Contraditor
MIMDE. Não incluir ID de agente, path de workspace, transcript nem defesa do
autor:

```text
artefato_ou_diff: conteúdo final ou resumo fiel do diff
objetivo_e_leitor: uma frase para cada
numeros_e_fontes: somente medições essenciais e sua origem
restricoes_duras: lista curta
rubrica_de_aprovacao: checklist verificável
```

Enviar este pacote somente ao revisor selecionado — Fable saudável ou fallback
Kimi `>=3` saudável. Kimi recebe o mesmo candidato final e rubrica; nunca o
transcript, o histórico de workers ou caminhos adicionais. Proibir explicitamente
no brief:

- pedir ou ler o histórico bruto;
- falar com Sonnet, Codex ou qualquer worker;
- editar arquivo ou executar comando;
- refazer a solução;
- alongar a resposta com objeções cosméticas.

Pedir no máximo três objeções escolhidas pelo custo do erro. Cada uma deve citar
evidência do pacote, declarar impacto e dizer o que a provaria errada. O revisor
selecionado devolve um destes vereditos:

```text
PROSSEGUIR
REVISAR
PARAR
```

Para cada objeção: critério afetado, evidência ausente/contrária e correção
mínima. O orquestrador decide o que procede, repara e verifica. **Não chamar Fable nem
Kimi de novo** depois do reparo. Registrar modelo exato, effort, saúde/cota
medida e justificativa; se Kimi foi usado, registrar também
`FABLE_PERTO_DO_LIMITE` e que não houve chamada Fable.

### 8. Fallback sem revisor final

Se Fable não estiver perto do limite, mas estiver indisponível, incompatível,
falhar ou não devolver material útil, não usar Kimi por conveniência. Se Fable
estiver perto do limite e não houver Kimi `>=3` saudável, aplicar o mesmo
fallback honesto:

1. Registrar `FABLE_NAO_EXECUTADO` ou `KIMI_FALLBACK_NAO_EXECUTADO`, o modelo,
   a saúde/cota medida e o motivo literal.
2. Não chamar outro revisor silenciosamente nem testar Fable antes de Kimi.
3. Fazer apenas os gates próprios do orquestrador já previstos, rotulando-os como
   verificação do orquestrador.
4. Apresentar ao <USUARIO>: “candidato verificado pelo orquestrador, sem revisão Fable ou
   Kimi independente”.
5. Se o risco exigir revisão independente, parar por bloqueio material de
   segurança/autoridade; não abrir nova pergunta depois da grelha.

Fallback preserva honestidade; não preserva independência.

### 9. Apresentar e registrar

Só o orquestrador fala a entrega final ao <USUARIO>. Começar pelo resultado, citar paths e
evidência, separar limite de falha e terminar com o próximo passo concreto.

Registrar estado, decisões novas e uma lição somente quando algo da execução
mudar comportamento futuro. Não fazer commit, push, deploy, publicação,
atualização ou reinício sem a autorização específica dessa etapa.

## Aplicação preparada: Portfolio em Opera/Chromium sem aceleração

Usar como primeiro exercício real, sem executá-lo só por carregar a skill:

1. orquestrador decide a grelha; encerrada ou pulada, não pergunta de novo nem decide
   direção visual/produto pelo <USUARIO>. Preservar o navegador escolhido.
2. Comprovar versão, aceleração desligada, viewport efetivo, cache, rota e
   estado provocado. HTTP não aprova performance visual; metas vêm do baseline.
3. Sonnet `xhigh` mapeia pipeline e gargalos em modo read-only; Codex `high`
   implementa a mudança mínima na fonte autorizada, com backup e testes.
4. orquestrador compara antes/depois no mesmo runtime, verifica regressão e forma o
   candidato. Fable adaptativo só entra se houver risco material e saúde/cota
   suficiente; se estiver `FABLE_PERTO_DO_LIMITE`, Kimi `>=3` saudável recebe o
   mesmo pacote comprimido em uma única chamada. Caso contrário, registrar
   `FABLE_OFF` ou a indisponibilidade sem inventar revisor.
5. Produção fica fora do fluxo até autorização explícita e checklist de deploy.

## Falhas e resposta

| Falha | Resposta |
|---|---|
| agente raiz não é o orquestrador resolvido | transferir ou parar; não assumir o papel por conveniência |
| grelha ativa e resposta pendente | perguntar uma vez e STOP real |
| grelha encerrada/pulada | não perguntar; decidir só o operacional reversível e registrar |
| decisão concreta de produto sem resposta | declarar limite; não escolher pelo <USUARIO> |
| worker sem cota | reduzir o plano ou selecionar equivalente permitido; registrar |
| mais de 5 workers ou paralelismo sem independência | cortar para 5, serializar o resto e registrar o motivo |
| dois writers no mesmo arquivo | cancelar sobreposição e reatribuir um único escritor |
| saída existe só no chat | tratar como rascunho até gravar e inspecionar |
| teste não roda | não marcar candidato final; registrar bloqueio literal |
| Fable chamado cedo | descartar a revisão e só chamar depois do candidato final |
| tarefa N0/ajuste pequeno | `FABLE_OFF`; não chamar Fable nem Kimi; revisão interna curta |
| modo apenas sugerido | não ativar; aguardar aceite explícito ou seguir no modo atual |
| modo recusado no estágio | registrar e não sugerir novamente até transição material |
| hypado e advogado entram em pingue-pongue | interromper; sintetizar uma vez a partir dos dois pareceres |
| `/quaseultracode` em tarefa pequena | marcar `NAO_APLICAVEL` e usar fluxo comum |
| estimativa ideal acima de 5h | marcar `ULTRACODE_REAL`; primeiro marco seguro + mapa de continuação |
| harness/model abaixo do necessário | preservar rubrica; reduzir lote/paralelismo, aumentar prova e declarar delta |
| Headhunter tenta mudar baseline | rejeitar; aplicar gate anti-scope-creep e manter sugestão no backlog |
| Fable perto do limite | medir Kimi `>=3`; se saudável, usar só Kimi e registrar saúde, modelo, effort e justificativa |
| Kimi `>=3` sem saúde/cota | `KIMI_FALLBACK_NAO_EXECUTADO`; não inventar sucessor nem chamar Fable depois |
| Fable sem cota/sem resposta fora de `FABLE_PERTO_DO_LIMITE` | usar `FABLE_NAO_EXECUTADO`; nunca fingir revisão |
| `FABLE_LATEST` sem versão compatível | não substituir por outra família; `FABLE_NAO_EXECUTADO` |
| slug Fable fixado como permanente | listar modelos e resolver a maior versão compatível novamente |
| `LOW` cobre risco amplo sem declaração | rejeitar review; registrar downgrade e escopo ou não executar |
| `HIGH/XHIGH` sem flag grande/cota | rebaixar para `MEDIUM`; registrar a escolha correta |
| Fable ou Kimi tenta executar ou falar com worker | interromper; preservar apenas objeções válidas |
| reparo quebra critério anterior | voltar a `SINTETIZANDO`, verificar de novo e não fazer segunda chamada de revisor |
| resposta de orquestração sem o cabeçalho fixo (prompt de origem · o que entendi · TL;DR) | reescrever com os três blocos antes do corpo; não é opcional em status nem em pergunta de grelha |
| terminal/helper ausente | registrar falha de infraestrutura; atualizar/reiniciar só com checkpoint e autorização |

## Orçamento

- Medir cotas antes dos briefs; não recriar o mesmo lote em provedores que já
  estavam indisponíveis.
- Dar contexto amplo somente ao orquestrador. Workers recebem briefs e fontes mínimas.
- Salvar o brief no disco para não retransmitir histórico.
- Usar paralelismo por independência, não para duplicar o mesmo raciocínio.
- Reservar uma chamada final de revisor no effort roteado: Fable saudável ou,
  exclusivamente em `FABLE_PERTO_DO_LIMITE`, Kimi `>=3` saudável. `MEDIUM` é o
  padrão elegível e qualquer desvio precisa de cota/flag registrada.
- Em `/quaseultracode`, registrar 70% do ciclo Ultracode `[HEURÍSTICA]`, teto
  de 5h, e parar quando tempo extra não comprar evidência, decisão ou qualidade.
- Encerrar agents/workers quando o escopo terminar; não deixá-los como donos
  implícitos do projeto.
