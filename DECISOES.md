# DECISOES — megabrain core

## 260813 — criar arquivos de estado/handoff/decisões na pasta core
- Decisão: criar `ESTADO.md`, `HANDOFF.md` e `DECISOES.md` em `<PROJETOS_ROOT>\MEGA B R A I N`, em vez de dentro de `_github-repo-local/`.
- Alternativa descartada: manter o controle de estado só no git de `_github-repo-local/`. Motivo: a pasta core é a fonte canônica para todas as IAs, e o handoff precisa estar visível antes de qualquer sync para o repo.

## 260813 — pasta core do megabrain
- Decisão: tratar `<PROJETOS_ROOT>\MEGA B R A I N` como fonte da verdade do protocolo megabrain.
- Alternativa descartada: deixar cada IA inferir a pasta a partir do contexto. Motivo: evita divergência quando múltiplos agentes operam em cópias diferentes.

## 260813 — publicar ESTADO/HANDOFF/DECISOES no repo público
- Decisão: permitir que `ESTADO.md`, `HANDOFF.md` e `DECISOES.md` gerados na central sejam sanitizados e incluídos em `260810_github-export/` (e consequentemente em `_github-repo-local/`).
- Alternativa descartada: excluí-los do template público. Motivo: são arquivos de operação do protocolo e não contêm dados pessoais; disponibilizá-los no repo público ajuda quem clona a entender o estado atual sem expor a pasta central.
