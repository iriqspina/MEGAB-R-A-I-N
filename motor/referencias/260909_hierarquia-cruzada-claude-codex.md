# Hierarquia cruzada Claude ↔ Codex/GPT — referência viva

Mapeamento relativo de "força"/posição na hierarquia entre as famílias de
modelo Claude (Anthropic) e Codex/GPT (OpenAI), pra decidir automaticamente
qual usar quando o pedido não especifica. **Muda com o tempo** — cada entrada
é datada; nunca sobrescrever uma entrada antiga, só acrescentar uma nova
quando o mapeamento mudar, pra manter o histórico.

Confiança: hipótese do <USUARIO>, registrada como tal — não é preço nem
benchmark verificado por um agente. Preço Anthropic real (confirmado via
skill `claude-api`, cache 260624): Fable 5.1/5 US$10/US$50 por milhão de
tokens (entrada/saída) — o mais caro e mais capaz da Anthropic; Opus 5
US$5/US$25; Sonnet 5 US$2/US$10. Não há tabela de preço OpenAI equivalente
carregada nesta sessão — o lado Codex/GPT do mapeamento é [ESTIMATIVA] do
<USUARIO>, não confirmado.

## 260909 — mapeamento inicial

| Nível | Claude | Codex/GPT | Fonte/confiança |
|---|---|---|---|
| Fronteira | Fable 5.1 (`claude-fable-5-1`) | GPT 6 Astra | [ESTIMATIVA] <USUARIO> — "imagino que". Astra citado em `cerebro/wiki/260909_videos-orquestracao-claude-codex.md` (vídeo "GPT 6 Astra + GPT Images 2.5", Chase AI), não confirmado como nome oficial de tier de preço. |
| Coordenador/meio | Opus 5 (`claude-opus-5`) | GPT Sol (`gpt-5.6-sol`, já configurado em `apps/automations/config/automations.json` como provider `codex`, effort `high`) | [ESTIMATIVA] <USUARIO> |
| Worker leve | — (Sonnet 5/Haiku 4.5 não mapeados ainda) | GPT-5.3-Codex-Spark (`gpt-5.3-codex-spark`, provider `spark`, effort `low`) | Spark já é bucket de cota SEPARADO do Codex principal (confirmado — ver nota abaixo), não só um "nível" nominal |

## Achado confirmado (não é hipótese): Spark tem folga separada do Codex principal

Medido em 260909 ~20:09–23:20 UTC via `providers.fetch_provider("codex")`:

- `codex:primary` (Sol, janela de 7 dias): **70% usado**, ritmo `desacelerar`
  (uso ideal neste ponto seria ~12%, está 58 pontos adiantado; ~147h/6,1 dias
  até resetar).
- `codex_bengalfox:primary` (Spark, janela de 5h): 10% usado, ritmo `ok`.
- `codex_bengalfox:secondary` (Spark, janela de 7 dias): 5% usado, ritmo `ok`.

Confirma o palpite do <USUARIO>: Spark tem headroom (folga) real e separado
agora. Não confirma que o TETO nominal do Spark seja maior — só que o
consumo dele está bem mais baixo neste momento. Em 260910,
`roles.probe`/`roles.checklist` passaram a usar `spark_preferido`: escolhem
Spark somente se a leitura do bucket separado estiver `ok`; sem medida ou em
ritmo ruim, voltam ao padrão explícito Codex. O papel `candidate` (quem escreve
o código de verdade) continua fixo em `codex` (Sol) — decisão mantida em 260909
(ver `pets/DECISOES.md` e o plano da sessão), não reaberta aqui apesar da
pressão medida no Sol.

## Como isso deve ser usado

`apps/automations/automations.py::pick_provider()` (260909) usa o `status`
de `budget_pacing.provider_pacing()` pra desempatar entre candidatos do
MESMO papel configurável (`probe`/`checklist`) — nunca troca automaticamente
`candidate`/`review`/`plan` por hierarquia cruzada. Este documento é a
referência humana por trás da ordem de preferência, não uma tabela que o
código lê diretamente.

## 260910 — medição que vira dado, sem tratar passado como cota atual

Cada run V6 registra o recorte de cota dos providers Claude, Codex/Sol e Spark
em três momentos: **antes**, em cada despacho/retorno e **depois**.
`quota-lifecycle.jsonl` conserva a evidência por run; a central recompõe
`dados/telemetria-orquestracao.json` com 240 eventos recentes completos e
agrega o anterior por dia e provider. Assim, o MEGABRAIN compara padrões reais
de disponibilidade e consumo sem guardar uma pilha de snapshots velhos, sem
cota inventada e sem deixar a coleta provocar rate limit: só os dois limites da
run forçam leitura nova; o meio reaproveita o cache e o declara.

O roteamento continua guiado pela leitura ao vivo. Uma porcentagem histórica
serve para detectar tendência, nunca para autorizar despacho hoje.
