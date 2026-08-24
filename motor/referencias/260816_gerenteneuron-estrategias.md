# Estratégias de roteamento do GerenteNeuron

Referência viva sobre como o GerenteNeuron escolhe qual IA chamar e como
refinar essas escolhas com uso real.

## Princípios

1. **Custo primeiro, capacidade depois.** Comece pelo modelo mais barato que
   provavelmente resolve. Suba só se a resposta for fraca ou o usuário pedir.
2. **Local para código.** Ollama/Qwen local processa código, debugging e
   refactor sem gastar tokens pagos. A RTX 4070 de 12 GB comporta Qwen 3 8B
   quantizado bem para tarefas focadas.
3. **Pago para revisão.** Modelos caros (Claude Opus, GPT Sol) entram para
   auditoria, decisão de design e texto final — não para primeira passada.
4. **O usuário pode interferir.** Override manual e botão "Reforçar" existem
   justamente porque o roteador erra.

## Estratégias atuais

| Estratégia | Gatilho | Modelos tentados (ordem) |
|---|---|---|
| `local_code` | palavras como código, debug, função, script, python, html, css, api, erro, bug | Ollama Qwen → Kimi K2 → GPT Luna |
| `cheap` | pergunta curta, resumir, extrair, listar, definir | Ollama Qwen → Kimi K2 → GPT Luna → Gemini Flash |
| `standard` | explanação, decisão moderada, texto médio | Kimi K1.5 → GPT Terra → Claude Sonnet → Gemini Pro |
| `deep` | arquitetura, auditoria, decisão crítica, texto longo | GPT Sol → Claude Opus → Gemini Pro |

## Como subir e descer de modelo

- **Auto:** o roteador decide pela mensagem.
- **Manual:** o usuário escolhe provedor/modelo no topo.
- **Boost:** depois de uma resposta, o usuário clica em "Reforçar" para
  reenviar a mesma mensagem na estratégia imediatamente acima.

## Feedback e aprendizado

Cada interação é registrada em `gerenteneuron/data/feedback.jsonl` com:
- timestamp, estratégia, provider, modelo, custo estimado;
- feedback do usuário (👍/👎);
- erros de API.

O endpoint `/api/eval` retorna estatísticas e sugestões, como:
- "Estratégia X tem 40% de feedback negativo — revisar regras."
- "Modelo Y falha em 20% das vezes — verificar disponibilidade."

Use esses dados para ajustar `router.py`, não para adivinhar.

## Anti-padrões

- Usar modelo pago para todo prompt. Quebra o objetivo de economia.
- Usar modelo local para decisão final de alto risco. A quantização e o
  tamanho menor geram alucinação em tarefas de julgamento.
- Boostar sem motivo. Só reforça se a resposta realmente foi fraca.

## Atualização de preços

Os preços embutidos em cada provider são [ESTIMATIVA]. Para custos reais,
atualize `gerenteneuron/pricing.json` (a ser implementado) ou use os valores
oficiais das APIs e marque a fonte.

## Integração com MEGABRAIN

- Quando o GerenteNeuron aponta para `/portfolio`, `/rodada`, `/megabrain`
  etc., a execução continua na skill de destino.
- O roteador de IAs do GerenteNeuron é uma camada técnica; os gates de
  entrega do MEGABRAIN continuam valendo para qualquer artefato.
