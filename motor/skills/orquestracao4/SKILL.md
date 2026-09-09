---
name: orquestracao4
description: Perfil opcional para coordenar Codex, Claude e Gemini com clientes nativos, checagem frequente de quota/contexto/tokens, esforço adaptado ao uso real e failover quando uma ponte como Traycer reconecta. Use quando o usuário digitar /orquestracao4 ou pedir este fluxo.
---

# orquestracao4 — Codex e Claude com orçamento medido

**v0.1 · 260908.** Camada opcional sobre `/orquestracao1` para o fluxo pessoal
do <USUARIO>. O foco é coordenar os clientes nativos do Codex e do Claude,
usar o Gemini quando fizer sentido e manter a tarefa recuperável quando uma
ponte externa cai. Não altera o contrato sempre ativo do `/megabrain` nem o
roteamento geral de `/orquestracao1`.

Esta skill é um perfil de operação, não um ranking permanente de modelos. O
nome de um modelo na documentação não prova acesso na conta; o esforço que o
seletor oferece e o uso restante precisam ser conferidos no cliente.

## Invocação

```text
/orquestracao4 <objetivo em uma frase>
```

Modificadores úteis: `sem gemini`, `traycer só teste`, `sem fanout`,
`somente planejamento`. Um modificador não autoriza publicação, candidatura,
compra, commit, push ou ação irreversível.

## Quando usar

- Entrega que precisa combinar Codex e Claude sem depender de um hub único.
- Sessão em que quota, contexto e tokens precisam ser verificados antes de
  cada mudança de papel.
- Trabalho que precisa continuar em cliente nativo quando Traycer reconecta.
- Planejamento, código, auditoria ou entrega com handoff entre agentes.

Tarefa N0 ou leitura curta continua em `/orquestracao1` ou sem modo. Esta
camada adiciona disciplina de passagem e não deve virar ritual em toda pergunta.

## Perfil de recursos conhecido

Dados de assinatura e conta, em 08/09/2026:

- **ChatGPT Plus com Codex:** informado pelo <USUARIO>. A disponibilidade de
  modelo, esforço e quota deve ser conferida no Usage do cliente; a página de
  modelos da OpenAI não substitui essa medição.
- **Claude Max 5x:** informado pelo <USUARIO>. Claude e Claude Code dividem o
  uso do plano; consultar `/status` no Claude Code antes de uma escalada.
- **Google AI Plus (2 TB):** confirmado no Google One por captura fornecida
  pelo <USUARIO>, com cobrança mostrada de R$49,99/mês e assinatura desde
  28/03/2023. A captura confirma o plano pessoal, não o limite efetivo da
  janela atual do Gemini.

Não registrar URL pessoal, cookie, token, senha ou identificador de conta nos
artefatos do projeto.

## Papéis e esforço padrão

O Codex continua sendo o orquestrador desta camada. O modelo e o esforço abaixo
são a rota preferida; antes de despachar, conferir se a combinação existe no
seletor da conta. Ausência não autoriza substituição silenciosa.

| Etapa | Papel | Modelo e esforço | Saída mínima |
|---|---|---|---|
| Enquadrar | Codex | GPT-6 Astra · medium | objetivo, escopo e aceite |
| Revisar plano curto | Codex | GPT-6 Astra · low | lacunas e ajuste de baixo custo |
| Levantar fatos | Claude | Fable 5 · low | fatos, fontes, lacunas e caminhos |
| Apoio externo | Gemini | AI Plus, conforme acesso visível | fonte, achado e limite conhecido |
| Resolver | Codex | GPT-5.6 Sol · high | decisão, implementação ou diagnóstico |
| Revisar independente | Claude | Fable 5 · medium | problemas localizados e evidências |
| Validar | Codex | GPT-5.6 Sol · high | teste, runtime ou comportamento real |
| Escalar | Claude | Opus 5 · high | decisão de alto risco ainda aberta |
| Consolidar | Codex | GPT-6 Astra · medium | resultado, provas e pendências |

O Astra low é uma revisão rápida do enquadramento; o Astra medium fecha uma
decisão ou consolida uma entrega. O Opus 5 não entra por prestígio: só quando
uma decisão de alto risco permanece aberta depois da revisão independente.

## Fluxo operacional

1. **Assumir.** Rodar o Gate 0 do `/megabrain`, conferir a trava e ler o estado
   real. Registrar o objetivo e o escopo autorizado no handoff.
2. **Medir antes de despachar.** Conferir modelo/effort disponível e os três
   sinais de uso descritos abaixo. Se um sinal não estiver exposto, marcar
   `NAO_MEDIDO`; nunca preencher percentual por sensação.
3. **Enquadrar.** Codex Astra medium define artefato, leitor, critérios,
   arquivos-alvo e o que fica fora. Astra low pode fazer uma crítica curta
   antes de qualquer worker.
4. **Levantar fatos.** Claude Fable low lê somente o escopo e devolve fatos com
   origem, lacunas e caminhos. Gemini só entra quando oferecer uma fonte ou
   capacidade que o Codex/Claude não tenham no contexto disponível.
5. **Resolver.** Codex Sol high executa ou decide dentro do escopo. Um writer
   por arquivo compartilhado; frentes de código simultâneas usam worktrees.
6. **Revisar.** Claude Fable medium recebe o candidato e os critérios, mas não
   edita o arquivo principal nesta rodada. Devolve problema, impacto e prova.
7. **Validar.** Codex Sol confere testes, build, HTTP, runtime e, em mudança
   visual, navegador real com viewport e estado provocado.
8. **Consolidar.** Codex Astra medium fecha o resultado em `HANDOFF.md`, com
   feito, aberto, próximo passo, evidências e `TRAVADO_POR`.

Tarefa pequena pode usar só uma etapa. O orquestrador declara as etapas
puladas e por quê; não convoca a equipe inteira por padrão.

## Os três medidores

Quota, contexto e tokens respondem a perguntas diferentes:

1. **Quota do plano:** quanto o serviço ainda permite na janela de uso. É
   específica da conta e do produto.
2. **Contexto:** quanto da conversa, dos arquivos e dos retornos ainda cabe na
   janela do modelo.
3. **Tokens:** unidade de conteúdo processado. Não é uma carteira de tokens
   restante no plano.

### Checkpoints obrigatórios

Medir e registrar uma linha curta nestes pontos:

- antes do primeiro despacho;
- depois de cada retorno de worker;
- antes de Sol high ou Opus 5 high;
- antes de abrir conversa nova;
- antes de passar o bastão ou apresentar o candidato final.

Formato mínimo:

```text
USO: Codex=[MEDIDO|NAO_MEDIDO] · Claude=[MEDIDO|NAO_MEDIDO] · Gemini=[MEDIDO|NAO_MEDIDO]
CONTEXTO: [telemetria ou NAO_MEDIDO] · MODELO: [modelo] · EFFORT: [effort]
DECISAO: [continuar|reduzir fanout|encurtar saída|salvar handoff|parar e perguntar]
EVIDENCIA: [tela, comando, status ou caminho]
```

Sinais por cliente:

- Codex: indicador Usage/limite do cliente. Não inferir acesso do Plus a
  partir de uma página geral de modelos.
- Claude Code: `/status`; Max 5x compartilha uso entre Claude e Claude Code.
- Gemini: Gemini → Configurações → Limites de uso. AI Plus tem características
  gerais anunciadas, mas a tela da conta decide o limite disponível naquele
  momento.

### Adaptação sem chute

- **Verde:** manter o esforço previsto e o fanout que o escopo exige.
- **Amarelo:** reduzir fanout, encurtar retornos e usar low/medium onde a
  tarefa permitir; preservar a revisão e a validação.
- **Vermelho:** cortar escopo ou salvar handoff; não cortar o teste final.
- **Sem sinal:** não declarar verde, amarelo ou vermelho. Marcar
  `NAO_MEDIDO`, usar saídas curtas e pedir decisão antes de escalar.

A régua local `40% → 70% → 85%` pode ser usada como aviso de contexto, mas é
`[HEURISTICA]`, não limite oficial de nenhuma conta. Na central, o sinal mais
forte continua sendo a telemetria de `contexto_injetado`: acima de 80 mil
caracteres ou 40 arquivos lidos, salvar handoff e recomeçar com contexto menor.

Se o modelo/effort pedido não estiver disponível, informar a combinação
ausente, o impacto e a alternativa. Só substituir depois de decisão explícita;
preservar a verificação mesmo quando o orçamento apertar.

## Plataforma e failover

### Padrão

Usar **Codex nativo + Claude Code nativo** em duas abas do VS Code ou do
Windows Terminal. Manter uma pasta compartilhada com `ESTADO.md`,
`HANDOFF.md`, `DECISOES.md` e os artefatos da tarefa. Para código, separar
frentes em worktrees; para conteúdo, manter um writer por arquivo.

Esse arranjo reduz a dependência de uma ponte e conserva a continuidade no
disco. O trade-off é uma passagem manual curta entre os agentes.

### Traycer

Traycer é uma conveniência opcional, não o ponto único de falha:

1. Antes de uma entrega, executar uma chamada simples de ida e volta entre os
   agentes.
2. Executar um comando local sem escrita, como `Get-Location`.
3. Se houver reconexão, resposta perdida ou comando local que não retorna,
   registrar a evidência e seguir pelos clientes nativos.
4. Não repetir a ponte indefinidamente e não enviar uma tarefa crítica por ela
   sem esse teste.

Não criar API key nem ativar créditos de API para contornar limite de uma
assinatura sem autorização específica. Se a ponte falhar, a tarefa continua
por handoff, não por tentativas silenciosas de outro provedor.

## Handoff mínimo

Antes de trocar de conversa, agente ou cliente, salvar:

```text
OBJETIVO:
ESCOPO AUTORIZADO:
MODELO/EFFORT USADOS:
USO EVIDENCIAS:
FEITO:
ABERTO:
DECISÕES:
ARQUIVOS:
PRÓXIMO PASSO:
TRAVADO_POR: livre
```

O retorno de um agente é rascunho até existir no disco e passar pelo gate de
verificação. O orquestrador não apresenta uma opinião como fato de conta.

## Limites honestos

- Não existe aqui um contador universal de tokens restantes para os três
  serviços.
- A captura do Google One confirma o plano AI Plus pessoal, não o uso atual do
  Gemini.
- A cota do Codex não é inferida do modelo que aparece na documentação.
- O uso do Claude depende da janela, do modelo, do tamanho da mensagem, dos
  anexos e da complexidade da tarefa.
- Uma conexão estável do cliente não prova que o provedor ou a quota estejam
  disponíveis; registrar o estado observado.
- Gemini AI Plus não significa acesso à API do Google sem outra configuração;
  este perfil não cria cobrança de API.

## Referências atuais

- OpenAI: [modelos](https://developers.openai.com/api/docs/models) e
  [uso do Codex com plano ChatGPT](https://help.openai.com/pt-br/articles/11369540-usar-o-codex-com-seu-plano-chatgpt).
- Anthropic: [status dos modelos](https://docs.anthropic.com/en/docs/about-claude/model-deprecations)
  e [limites do Claude Code no Max](https://support.anthropic.com/en/articles/11145838-using-claude-code-with-your-max-plan).
- Google: [limites do Gemini](https://support.google.com/gemini/answer/16275805?hl=pt-BR)
  e [planos no Brasil](https://gemini.google/br/subscriptions/?hl=pt-BR).
- Plataforma: [Traycer](https://traycer.ai/) — capacidade anunciada de usar
  Codex e Claude lado a lado; estabilidade da conta do <USUARIO> precisa ser
  testada na sessão atual.

