# Checklist de abertura — megabrain core

## 260818 — auditoria pausada antes do sync de identidade

- **Checar:** se o subagente coder (agent-4 / task agent-je3rze2w) terminou
  todos os itens F1–F13. Se sim, coletar o output.log.
- **Por quê:** sem isso a próxima sessão pode repetir trabalho já feito ou
  tentar rodar sync sobre arquivos que ainda estão sendo editados.
- **Como:** `TaskOutput agent-je3rze2w` ou `ls .mb-backup/260818/` para
  confirmar que os arquivos velhos foram movidos.
- **RESOLVIDO:** não

## 260818 — plugin Kimi possivelmente desatualizado

- **Checar:** diff entre `skills/megabrain/SKILL.md` central e
  `<USER_HOME>/.kimi-code/plugins/managed/megabrain/skills/megabrain/SKILL.md`;
  idem `MEGABRAIN.md`.
- **Por quê:** `skills/megabrain/SKILL.md` e `MEGABRAIN.md` da central foram
  editados depois que o refresh do plugin rodou no subagente.
- **Como:** `diff` seguido de `robocopy` das linhas 48–50 do
  `sincronizar-pipeline.cmd` se necessário.
- **RESOLVIDO:** não

## 260818 — identidade ainda não propagada pros agentes

- **Checar:** se `260810_sincronizar-identidade.cmd` já foi rodado nesta
  sessão e se os blocos AUTO-SYNC em `~/.claude/CLAUDE.md`,
  `~/.gemini/GEMINI.md`, `~/.kimi/AGENTS.md`, `~/.kimi-code/AGENTS.md` e
  `~/.codex/AGENTS.md` batem com `260810_memoria-pessoal.md`.
- **Por quê:** o contrato de resposta só vale se todos os agentes o receberem
  igual. Rodar sem conferir reproduz a divergência que esta sessão tentou
  eliminar.
- **Como:** rode o .cmd e depois `diff` ou `grep` pelos marcadores
  `MEGABRAIN:AUTO-SYNC`.
- **RESOLVIDO:** não

## 260818 — output style do Claude

- **Checar:** se `~/.claude/output-styles/megabrain.md` existe e se
  `~/.claude/settings.json` contém `"outputStyle": "megabrain"`.
- **Por quê:** sem settings.json apontando pro estilo, o arquivo gerado fica
  inerte.
- **Como:** `cat ~/.claude/settings.json` e `ls ~/.claude/output-styles/`.
- **RESOLVIDO:** não

## 260818 — commits pendentes no repo local

- **Checar:** status de `_github-repo-local` (3 commits à frente de
  `origin/main`, 6 arquivos modificados, RELATORIO.html untracked).
- **Por quê:** o repo público está desatualizado; a sanitização do
  gerenteneuron SKILL.md foi corrigida no working tree mas não commitada.
- **Como:** `git -C _github-repo-local status --short` e decidir com o
  usuário sobre commit/push (push em repo público exige autorização).
- **RESOLVIDO:** não
