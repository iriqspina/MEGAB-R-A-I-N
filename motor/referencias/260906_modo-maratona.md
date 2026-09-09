# Modo Maratona — orquestração 3 com orçamento automático

Objetivo: você abre a sessão, trabalha 5 horas, e nunca pensa em quota.
O sistema decide sozinho quem roda em qual modelo e com qual effort,
e **nunca** desliga os dois gates frontier.

## O invariante

Dos cinco papéis, dois são inegociáveis:

- **orquestrador** — planeja e julga
- **adversário** — procura o que falta no plano

Eles ficam travados em modelo frontier o tempo todo. A degradação por
orçamento acontece só em talker, workers, fan-out e rodadas de review.
Motivo: qualidade de plano é o que evita retrabalho, e retrabalho é o
que realmente queima quota. Cortar o gate para economizar é a economia
que sai mais cara.

Uma proteção extra: o adversário vive no **Codex**, não no Claude.
Isso significa que ele consome outra bolsa de quota. Quando o Claude
entra em vermelho, o adversário continua em `xhigh` sem custo na janela
que está estourando.

## As três fases

O governador calcula duas coisas: **queima** (quanto da janela gastável
já foi) e **ritmo** (se você está gastando acima do linear para as 5h).

| Fase | Gatilho | O que muda |
|---|---|---|
| **Verde** | queima < 55% e ritmo ok | Tudo no topo. Fan-out 4, review 2 rodadas. |
| **Amarelo** | queima ≥ 55%, ritmo ≥ 1.4x, ou semanal ≥ 75% | Talker e workers caem para `low`. Fan-out 2, review 1. Orquestrador vai a `medium`. |
| **Vermelho** | queima ≥ 85% ou semanal ≥ 92% | Workers migram para Codex Luna, talker vira Haiku. Fan-out 1. Os dois frontier continuam. |

Camada semanal separada: se o consumo frontier passar de 45% do teto
semanal, Fable 5.1 é bloqueado e Opus 5 assume o papel. Isso respeita o
limite de ~50% do semanal que o Fable tem no Max — sem que você precise
lembrar disso.

## O ciclo automático

1. **Início de sessão** — `orcamento.py` roda no `SessionStart`, grava a
   política em `~/.megabrain/politica.json` e imprime uma linha de status.
2. **A cada gate** — o orquestrador lê a política antes de planejar e
   escreve `fase` + `politica_id` no bloco `orcamento` do plano. Fica
   registrado sob qual regime aquele plano nasceu.
3. **A cada subagente encerrado** — `SubagentStop` roda o fechamento de
   grafo e recalcula. Se a fase mudou, o próximo fan-out já sai reduzido.
4. **Fim de janela** — quando faltam menos de 30 min com orçamento
   sobrando, o alerta sugere puxar a tarefa cara para agora, porque o
   saldo não acumula.

## Instalação

```bash
mkdir -p ~/.megabrain
cp orcamento.py fechamento-grafo.py ~/.megabrain/
chmod +x ~/.megabrain/*.py
cp PLANO.schema.json checklist-cobertura-v1.md ~/.megabrain/
```

Calibre o teto na primeira semana: rode `/usage` no Claude Code em três
momentos do dia e compare com a saída do script. Ajuste
`limite_5h_tokens` e `limite_semanal_tokens` em `~/.megabrain/orcamento.json`
até baterem. Sem essa calibração os números são chute com formato bonito.

### Hooks (`~/.claude/settings.json`)

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "python3 ~/.megabrain/orcamento.py --json > ~/.megabrain/politica.json && python3 ~/.megabrain/orcamento.py" }] }
    ],
    "SubagentStop": [
      { "hooks": [
          { "type": "command", "command": "python3 ~/.megabrain/fechamento-grafo.py" },
          { "type": "command", "command": "python3 ~/.megabrain/orcamento.py --json > ~/.megabrain/politica.json" }
      ] }
    ]
  }
}
```

### Comando manual

`.claude/commands/orcamento.md`:

```md
Rode `python3 ~/.megabrain/orcamento.py` e me diga em uma linha:
fase atual, quanto falta da janela, e se vale começar tarefa grande agora.
```

## Como o orquestrador consome a política

No system prompt do agente orquestrador:

> Antes de planejar, leia `~/.megabrain/politica.json`.
> Use `papeis.worker` como modelo e effort de todo subagente que você criar.
> Não crie mais subagentes em paralelo do que `papeis.fanout_max`.
> Não abra mais que `papeis.rodadas_review_max` ciclos de revisão.
> Se a fase for vermelho, reduza o escopo do plano em vez de reduzir a
> qualidade do gate: entregue menos itens, não itens mais mal planejados.

Essa última linha é o coração do modo. Sob pressão de orçamento, a
resposta certa é **cortar escopo**, nunca cortar verificação.

## Pontos de honestidade

- Não existe endpoint oficial de quota do Max. Isso é estimativa sobre
  transcripts locais, na mesma técnica do `ccusage`. Trate os percentuais
  como semáforo, não como saldo bancário.
- Os pesos por modelo são custo relativo aproximado, não a fórmula
  interna da Anthropic. Servem para comparar sessões entre si.
- A janela de 5h começa na sua primeira mensagem, não em hora fixa. O
  script arredonda para a hora cheia, que é o comportamento observado.
- Uso via Codex sai de outra bolsa e não aparece nesses transcripts. Se
  quiser o quadro completo, some o consumo reportado pelo Codex CLI à parte.
