# ESTADO — megabrain core

- Versão ativa: 3.9
- Fase: concluída / aguardando próxima rodada
- Última ação: auditoria do estado do megabrain após atualização do Claude;
  corrigida regressão de caminho absoluto em `skills/megabrain/SKILL.md`
  (`<MEGABRAIN_ROOT>/` → `<MEGABRAIN_ROOT>/`); atualizado
  `README.md` para listar todos os scripts de `bin/` (antes citava só 2);
  removida pasta `MEGABRAIN/` criada acidentalmente na central por uso errado
  de `mb-check-version.py` contra a própria central; adicionada proteção no
  próprio `mb-check-version.py` para recusar `--projeto` apontando para a
  central; regenerado `260810_github-export/` com `dna/`,
  `mb-relatorio-projeto.py` e exclusão de pastas internas (`_to_delete/`,
  `alteracoes-pendentes/`); sincronizado com `_github-repo-local/` e
  commitado/push para o GitHub público.
- Próximo passo: propagar v3.9 para projetos derivados (Rodada, TLOU/portfólio,
  Jarvis, Financeiro da Silva) quando o <USUARIO> pedir; replicar SKILL.md
  atualizado para o plugin managed do Kimi se necessário.
- Alerta: nenhum
