# DECISOES — megabrain core

## 260813 — criar arquivos de estado/handoff/decisões na pasta core
- Decisão: criar `ESTADO.md`, `HANDOFF.md` e `DECISOES.md` em `<PROJETOS_ROOT>\MEGA B R A I N`, em vez de dentro de `_github-repo-local/`.
- Alternativa descartada: manter o controle de estado só no git de `_github-repo-local/`. Motivo: a pasta core é a fonte canônica para todas as IAs, e o handoff precisa estar visível antes de qualquer sync para o repo.

## 260813 — pasta core do megabrain
- Decisão: tratar `<PROJETOS_ROOT>\MEGA B R A I N` como fonte da verdade do protocolo megabrain.
- Alternativa descartada: deixar cada IA inferir a pasta a partir do contexto. Motivo: evita divergência quando múltiplos agentes operam em cópias diferentes.
