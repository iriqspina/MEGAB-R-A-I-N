# ESTADO — megabrain core

- Versão ativa: 4.3
- Fase: concluída / entregue no GitHub e propagada para projetos derivados
- Última ação: implementada redundância contra pontos únicos de falha.
  Criados `bin/mb-backup-central.py` (backup zip da central) e
  `bin/mb-recuperar-megabrain.py` (recupera `MEGABRAIN/` de um projeto a
  partir de backup zip, outro projeto ou central). Documentação de backup e
  recuperação adicionada a `OFFLINE.md`, `MEGABRAIN.md`,
  `260810_MEGABRAIN.md` e `README.md`. Bump para v4.3. Testes manuais de
  backup e recuperação passaram. Próximo passo: propagar v4.3 para os
  projetos derivados.
- Próximo passo: propagar v4.3 para Financeiro da Silva, Jarvis, Rodada e
  TLOU; configurar remote do TLOU se o <USUARIO> quiser push; adotar
  bibliotecas do `requirements.txt` quando o ambiente permitir.
- Alerta: nenhum
