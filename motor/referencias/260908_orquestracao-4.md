# orquestração 4 — perfil pessoal Codex + Claude + Gemini

**v1.0 · 2026-09-08.** Camada opcional do MegaBrain para o fluxo real do
<USUARIO>: ChatGPT Plus com Codex, Claude Max 5x e Google AI Plus (2 TB). Não
substitui `/orquestracao1`; define uma topologia de clientes, esforço e
checagem para uma conta pessoal em que a quota pode variar e o Traycer está
reconectando.

## Problema falseável

Uma ponte única pode interromper a entrega mesmo quando Codex e Claude ainda
estão disponíveis. O perfil precisa permitir que o <USUARIO> veja o modelo, o
esforço e o estado de uso, troque de cliente sem perder o contexto e saiba
quando uma substituição muda a qualidade ou o custo.

## Decisão

Usar Codex como orquestrador em cliente nativo, Claude como worker/revisor e
Gemini AI Plus como apoio externo condicionado ao limite visível. O encontro
entre os agentes é feito por arquivos de estado e handoff; Traycer pode ser
testado, mas não é dependência da entrega.

## Rota de modelos

| Função | Rota preferida | Motivo | Condição |
|---|---|---|---|
| Enquadrar | Codex GPT-6 Astra · medium | transforma pedido em escopo e aceite | conferir acesso no seletor |
| Crítica curta do plano | Codex GPT-6 Astra · low | encontra lacuna barata antes do fanout | não substitui o revisor final |
| Fatos e leitura | Claude Fable 5 · low | volume com resposta curta | conferir limite do Fable |
| Pesquisa/apoio | Gemini AI Plus | usa recurso externo quando agrega prova | limite real em Configurações |
| Resolver | Codex GPT-5.6 Sol · high | decisão técnica e execução difícil | manter evidência de teste |
| Revisar | Claude Fable 5 · medium | segunda leitura cross-vendor | não editar candidato |
| Validar | Codex GPT-5.6 Sol · high | runtime, teste e navegador real | esforço disponível confirmado |
| Escalar | Claude Opus 5 · high | alto risco ainda aberto | decisão explícita de escalada |
| Consolidar | Codex GPT-6 Astra · medium | junta fatos, provas e pendências | escrever handoff |

Modelo documentado não é acesso confirmado. A escolha é válida somente depois
de conferir o seletor e o indicador do cliente; falta de acesso vira fato
reportado, não troca automática.

## Orçamento em três camadas

O perfil separa:

1. **Quota:** permissão de uso do serviço na janela da assinatura.
2. **Contexto:** espaço restante da conversa e dos arquivos.
3. **Tokens:** unidade de conteúdo processado.

Os checkpoints ocorrem antes de cada despacho, depois de cada worker, antes de
high/Opus, antes de abrir conversa nova e antes do handoff final. A tela ou
comando observado entra no registro. Ausência do medidor vira `NAO_MEDIDO`.

| Estado | Ação | O que permanece protegido |
|---|---|---|
| Verde medido | executar a rota prevista | revisão, teste e handoff |
| Amarelo medido | reduzir fanout e tamanho das respostas | verificação final |
| Vermelho medido | cortar escopo e salvar estado | verificação final |
| Não medido | não declarar disponibilidade; perguntar antes de escalar | decisão do usuário |

A régua `40/70/85` é uma heurística de contexto, não uma quota oficial. A
telemetria da central continua sendo o sinal operacional principal; acima de
80 mil caracteres injetados ou 40 arquivos, o handoff deve ser salvo e o
contexto reduzido.

## Plataforma

O padrão é VS Code ou Windows Terminal com Codex nativo e Claude Code nativo em
duas abas. `ESTADO.md`, `HANDOFF.md` e `DECISOES.md` carregam a continuidade.
Worktrees isolam frentes de código; um writer por arquivo evita lost update.

Trade-off: passagem manual curta entre clientes. Benefício: o fluxo não fica
preso ao estado de uma ponte.

Traycer entra como teste de conveniência:

1. ida e volta simples entre os agentes;
2. `Get-Location` ou outro comando local sem escrita;
3. se reconectar ou perder resposta, registrar evidência e migrar para os
   clientes nativos;
4. não repetir a ponte sem limite.

Não usar API keys ou créditos adicionais para compensar limites de uma
assinatura sem autorização separada. Isso mudaria a origem da cobrança e do
controle de quota.

## O que a conta do <USUARIO> confirma

O Google One mostrado em 08/09/2026 confirma **Google AI Plus (2 TB)**,
assinante desde 28/03/2023, com R$49,99/mês na tela. A captura não é copiada
para este arquivo e a URL pessoal não entra no projeto. O limite atual de uso
de Gemini ainda deve ser consultado dentro do Gemini.

O Claude Max 5x e o ChatGPT Plus com Codex são dados informados pelo <USUARIO>;
o uso restante dos dois não foi medido nesta referência. As páginas públicas
confirmam produtos e modelos, não o estado individual de login, quota ou
esforço.

## Critérios de pronto

- `/orquestracao4` existe como camada opcional e não altera o default do
  `/megabrain`.
- Papéis, modelos e esforços têm condição de disponibilidade explícita.
- Quota, contexto e tokens aparecem como sinais diferentes.
- Há checkpoint antes de despacho, escalada, conversa nova e handoff.
- Traycer tem teste de saúde e failover nativo documentados.
- Nenhum caminho pessoal, token, URL de conta ou cobrança de API é gravado.
- A cópia Claude e o plugin Codex podem ser derivados da fonte sem edição
  manual.

## Fontes públicas consultadas

- [OpenAI — modelos](https://developers.openai.com/api/docs/models)
- [OpenAI — Codex com plano ChatGPT](https://help.openai.com/pt-br/articles/11369540-usar-o-codex-com-seu-plano-chatgpt)
- [Anthropic — status dos modelos](https://docs.anthropic.com/en/docs/about-claude/model-deprecations)
- [Anthropic — Claude Code no Max](https://support.anthropic.com/en/articles/11145838-using-claude-code-with-your-max-plan)
- [Google — limites do Gemini](https://support.google.com/gemini/answer/16275805?hl=pt-BR)
- [Google — planos no Brasil](https://gemini.google/br/subscriptions/?hl=pt-BR)
- [Traycer](https://traycer.ai/)

