---
name: traycer
description: Pipeline do Traycer rodando sob os gates do megabrain — onde a grelha entra, qual modelo faz o quê, o que vira artefato do Traycer e o que tem que voltar pra ESTADO/HANDOFF/DECISOES. Use quando o usuário digitar /traycer, falar em "epic", "core flow", "tech plan", "ticket breakdown", "execute" ou "phase" do Traycer, abrir ou retomar um epic, escolher qual agente roda um ticket, ou perguntar por que o Traycer está perguntando/decidindo algo.
---

# traycer — o Traycer como executor dos gates

**v1.0 · 260825.** O Traycer não substitui o megabrain: ele é o **motor do
Gate 3 ao 5** com orquestração multi-agente embutida. Os gates 0, 1, 6 e 7
continuam fora dele — e é exatamente aí que as sessões vazam. Esta skill é o
contrato entre os dois. Instalação auditada em 260825 na máquina do <USUARIO>.

O nome do arquivo é `SKILL.md` sem prefixo de data de propósito: o loader lê
esse path exato. A data está no cabeçalho.

**Crédito e escopo (260825).** Traycer é produto de terceiro, proprietário —
`traycer.ai` / `docs.traycer.ai`. Esta skill **não deriva de código ou texto
deles**: é documentação de interoperabilidade, escrita a partir do
comportamento observado da ferramenta em 260825. Nomes de fase (epic, core
flow, tech plan, ticket breakdown, execute) são a nomenclatura deles, usada
como referência. Nenhuma licença é reivindicada sobre o produto; a licença
desta skill é a do megabrain.

## Em uma linha

O Traycer planeja em artefatos e despacha agentes-filhos que escrevem código.
O megabrain diz **quando** planejar, **quem** executa e **o que precisa
sobreviver** ao fim do epic. Rodar Traycer sem os gates = slop com orquestração
bonita.

## Mapa: gate → onde acontece no Traycer

| Gate | Onde | Regra dura |
|---|---|---|
| **0 ASSUMIR** | ANTES de abrir o epic | `mb-preflight.py`, `git pull`, ler ESTADO → HANDOFF → fim de DECISOES → LICOES, checar `TRAVADO_POR`. Epic aberto sem isso herda premissa velha. |
| **1 ENQUADRAR** | ANTES do `traycer-core-flows` | Roda `/grelhar`. O artefato Core Flows é o **espelho do entendimento**, não o lugar de descobri-lo. |
| **2 ORÇAR** | ao abrir o epic | 1 epic = 1 entrega. Vários artefatos delimitados > um documento gigante (o próprio Traycer manda isso). >85% de contexto no chat do epic → HANDOFF e novo chat. |
| **3 GERAR** | `traycer-tech-plan` → `traycer-ticket-breakdown` → `traycer-execute` | Peça compartilhada (tema, script de `bin/`, componente, skill): `python bin\mb-mapa-refs.py NOME` e citar quem consome ANTES do ticket. |
| **4 AUDITAR** | `traycer-artifact-critique` no plano, antes de quebrar em ticket | Erro de plano custa o epic inteiro; erro de ticket custa um ticket. **1 reparo só** — se o plano ainda está ruim, o erro é do Gate 1. |
| **5 VERIFICAR** | `traycer-review`, harness DIFERENTE do que implementou | Testar caminho, não confiar. Recalcular número. Contradiz DECISOES? |
| **6 BASTÃO** | fim do epic, FORA do Traycer | Epic fechado não é handoff. ESTADO (5 linhas) + HANDOFF (feito · aberto · próximo passo com verbo e objeto · `TRAVADO_POR: livre`) + DECISOES em append com a alternativa descartada. |
| **7 APRENDER** | fim do epic | `/registrar-licao`. Fato de conteúdo não é lição — vai pro cérebro via `/ingerir`. |

## A sobreposição que ninguém percebe

O `traycer-tech-plan` tem **readiness check** próprio: ele lista o que ficou
vago e pede confirmação antes de escrever o plano. Isso e o Gate 1 fazem o
mesmo trabalho.

**Não rode os dois.** A grelha vem primeiro e é mais funda (lê ESTADO,
DECISOES, cérebro e DNA antes de abrir a boca; o readiness check só olha a
conversa). Quando o readiness check aparecer com a lista vazia ou curta, é
sinal de que a grelha funcionou — siga. Se aparecer longo, a grelha foi rasa:
volte pro Gate 1 em vez de responder item a item no chat do Traycer.

Mesma lógica de precedência das skills de terceiros: `traycer-review` →
**Gate 5** · `traycer-artifact-critique` → **Gate 4** · `traycer-housekeeping`
→ **Gate 6**. Duas passadas no mesmo texto é teatro, não auditoria.

## Roteamento de modelo — modo otimizado

Fonte viva: `~/.traycer/agent-selection-guide.md` (o Traycer lê esse arquivo
pra escolher harness sozinho). Está sincronizado com esta seção; mudou aqui,
muda lá.

- **Planejar** (core flows, tech plan, ticket breakdown) → Claude **Opus**,
  reasoning alto. Único ponto em que a qualidade da decisão paga o token.
- **Implementar** → Codex/GPT com reasoning alto.
- **Varredura, extração, refactor mecânico, 1ª passada** → CLI agent
  `260825_Kimi K2.7`. Mesma entrega, fração do custo.
- **Revisar** → harness **diferente** do que implementou. Implementou no
  Codex, revisa no Claude; implementou no Kimi, revisa no Codex. Auto-review
  é o modelo aprovando o próprio raciocínio.
- **Review de decisão de produto** (o construído bate com o combinado) →
  sempre Opus, nunca delega.
- Modelo local fraco gerando resposta: nunca, nem como fallback.

## Agentes configurados nesta máquina (260825)

Nativos, em Settings → Providers: **Claude Code**, **Codex**, **Kimi**,
OpenCode, Cursor e o resto da lista.

CLI agents customizados, em `~/.traycer/cli-agents/` (escopo usuário; escopo
projeto seria `.traycer/cli-agents/` na raiz do workspace):

- `260825_Kimi K2.7.sh` — Kimi com o `~/.kimi-code/config.toml` do <USUARIO>
  (`default_permission_mode = auto`, thinking, MCPs). Resolve o binário mais
  novo entre o managed do Traycer e o próprio.
- `260825_Claude Opus (assinatura).sh` — Opus limpando `ANTHROPIC_API_KEY`
  do ambiente pra cair na sessão da assinatura em vez da chave de API.

Regras de script (documentadas em docs.traycer.ai/extension/integrations/
custom-cli-agents): pelo menos uma de `TRAYCER_PROMPT` ou
`TRAYCER_PROMPT_TMP_FILE` tem que ser referenciada. **Use sempre o
TMP_FILE** — variável de ambiente no Windows morre em ~32KB e prompt de fase
passa disso. O arquivo temporário é apagado 30s depois: leia de uma vez.
Outras variáveis disponíveis: `TRAYCER_SYSTEM_PROMPT`, `TRAYCER_PHASE_ID`,
`TRAYCER_PHASE_BREAKDOWN_ID`, `TRAYCER_TASK_ID`. Arquivo `.sh` roda pelo Git
Bash (`C:\Program Files\Git`); `.ps1` usaria `$env:TRAYCER_PROMPT` e
`Get-Content -Raw`.

## Cobrança — a armadilha do Claude

Claude Code no Traycer tem dois modos de pagar: **assinatura** (OAuth, cota
mensal) e **API key** (por token, saldo do console). Se
`Settings → Providers → Claude Code → Env` tiver `ANTHROPIC_API_KEY` e o
saldo estiver zerado, o turno morre no meio com `billing_error` e o trabalho
da fase se perde. Foi o que aconteceu em 260825 no epic "Otimização Perfil
Linkedolas". Conferir em **Profiles & Limits**: se o perfil aparece como
"Claude API Key" e "Usage limits unavailable", está na chave, não na
assinatura.

Nunca deixe chave de API em texto puro: ela fica legível em
`~/.traycer/host/config/provider-overrides.json`.

## Duas lentes do execute — não são simétricas

O `traycer-execute` revisa cada batch por duas lentes, e a assimetria é a
parte que importa:

- **Produto** — visão do usuário e decisão de produto. Inegociável: qualquer
  desvio é consertado.
- **Técnico** — detalhe que emergiu no trabalho. Desvio que não muda o
  resultado nem quebra restrição declarada é aceitável **desde que
  registrado**.

"Registrado" no megabrain significa DECISOES.md, não um comentário no chat
do epic. Desvio técnico que só existe no histórico do Traycer não sobrevive
à próxima sessão.

## Como isso costuma dar errado (top 6)

1. **Abrir epic sem Gate 0** — o Traycer começa a planejar em cima de estado
   que ninguém leu, e o plano parece ótimo porque ninguém checou a premissa.
2. **Deixar o Traycer grelhar** — responder o readiness check item a item no
   chat em vez de rodar `/grelhar` antes. As respostas ficam soltas na
   conversa e não viram DECISOES.
3. **Auto-review** — mesmo harness implementa e revisa, e o batch passa.
4. **Epic fechado = tarefa entregue** — sem ESTADO/HANDOFF, a próxima sessão
   reabre o projeto do zero e o epic vira arqueologia.
5. **Artefato do Traycer como fonte da verdade** — ele é rascunho até existir
   no disco do projeto. Output de agente é rascunho, inclusive o do Traycer.
6. **Ticket de julgamento no modelo barato** — varredura sim, arquitetura
   não. Economia que custa o refactor inteiro.

## Referências

`~/.traycer/agent-selection-guide.md` roteamento que o Traycer lê ·
`~/.traycer/.claude/skills/traycer-*/SKILL.md` as skills do próprio Traycer,
já instaladas ·
`referencias/260810_gates-entrega.md` gates em detalhe ·
`referencias/260810_evaluation-gates.md` rubrica de verificador ·
`referencias/260815_pipeline-governanca-aprendizado.md` cliente/dinheiro/
multi-IA.
