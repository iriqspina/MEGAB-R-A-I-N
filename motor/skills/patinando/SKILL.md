---
name: patinando
description: Gatilho de auto-monitoramento contra perda de tempo — quando o agente percebe que está patinando (3+ tentativas no mesmo obstáculo sem avanço qualitativo, loops de reabrir/reexecutar, teoria nova a cada rodada), congela o estado do problema e escala para um modelo forte pedir diagnóstico pontual, em vez de continuar sozinho queimando token. Preferência do <USUARIO> (260918): Opus 5 High ou o equivalente forte da atualidade quando houver cota. Use quando ele digitar /patinando, quando notar o padrão em si mesmo, ou quando ele perguntar "você tá patinando?".
---

# /patinando — parar, congelar, escalar

**v1.0 · 260918.** Nasceu de caso real: 4 ciclos de fechar/editar/reabrir/provar
o OBS pra acertar um transformo de scene item (causa: campos `_rel` que só a UI
grava — fechável por quem soubesse ler o formato). Regra do <USUARIO>, vale em
qualquer projeto. Fonte canônica: `motor/skills/patinando/SKILL.md` da central
MEGABRAIN; cópia derivada em `~/.zcode/skills/patinando/`.

## Sinais de patinação (qualquer 1 já conta; 2 = certeza)

1. **3+ iterações** no mesmo obstáculo sem avanço qualitativo (o resultado não
   muda de patamar, só muda o parâmetro da tentativa).
2. Mesma ferramenta/ação **reexecutada em loop** (reabrir app, reprocessar
   arquivo, refazer request) esperando resultado diferente.
3. **Teoria nova a cada rodada** sem evidência nova que a motive — explicar
   o mesmo fracasso de formas diferentes é patinar com estilo.
4. O Gate 4 do megabrain já foi violado: mais de **1 reparo** na mesma peça.

## O que fazer (nesta ordem)

1. **Parar.** Não iniciar a próxima tentativa.
2. **Congelar o estado** (~5 linhas): o que eu quero alcançar · o que tentei
   (lista curta) · o que a evidência DURA diz (log/arquivo/número, não teoria)
   · a trava específica do momento.
3. **Escalar**: despachar subagente com o estado congelado pedindo
   **diagnóstico pontual da trava** (não a tarefa inteira). Preferência do
   <USUARIO>: **Opus 5 High ou o equivalente forte da atualidade** quando
   houver cota (`dados/orcamento_ia.json` na central); sem cota, o mais forte
   disponível no ambiente. Se o ambiente não permitir escolher modelo do
   subagente, dizer isso explicitamente no handoff em vez de fingir escala.
4. **Testar o diagnóstico recebido contra a evidência** antes de aplicar —
   material de outro modelo é rascunho (mesma regra do megabrain).
5. **Registrar** no handoff/lições: o que travou, quantas rodadas custou, o
   que escalou, se resolveu — alimenta o próprio gatilho da próxima vez.

## Contra-indicações

- Iteração LEGÍTIMA não é patinação: cada rodada com evidência nova e avanço
  de patamar (ex.: bwtest → análise de imagem → correção) é trabalho normal.
- Escalar não é delegar a tarefa: o diagnóstico vem de fora, a decisão e a
  execução continuam do agente da sessão.

## Via de escala concreta (260918, verificada)

- **Claude pelo terminal**: `claude -p "<estado congelado + pergunta pontual>"`
  (Claude Code CLI instalado; responde headless, lê arquivos e imagens locais
  com visão nativa). É o caminho do "Opus de verdade" quando a sessão roda em
  outro motor. Para verificação visual cega: passar só os caminhos das
  imagens + pergunta neutra — sem contar a conclusão da sessão.
- Dentro do próprio harness: subagente com contexto zero (mesmo motor, sem o
  viés da conversa) — segundo melhor, sempre disponível.

- **Codex CLI (OpenAI/GPT)** também disponível: `codex exec --skip-git-repo-check --sandbox read-only "<pergunta>" < /dev/null` (fora de repo git precisa da flag; stdin fechado evita travar). 260918: cota estourada até 19/09 13:08 — conferir limite antes de prometer.
