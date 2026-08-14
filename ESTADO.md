# ESTADO — megabrain core

- Versão ativa: 4.0
- Fase: concluída / entregue no GitHub e propagada para projetos derivados
- Última ação: implementada diferenciação de usuário no protocolo.
  - `bin/mb_utils.py`: novos helpers `extract_usuario` e `detectar_usuario`.
  - `bin/mb-sync.py`: campo `USUARIO:` no `HANDOFF.md`, detectado de
    `260810_memoria-pessoal.md` ou via `--usuario`.
  - `bin/mb-sync-memoria.py`: propaga `USUARIO:` para `CLAUDE.md`,
    `GEMINI.md` e `AGENTS.md`; suporta `--usuario` para forçar perfil.
  - `260810_memoria-pessoal.md` e arquivos em
    `260810_backup-raiz-perfil/` atualizados com `USUARIO: <USUARIO> (Iriq)`.
  - `referencias/260810_sync-memoria.md` documenta o novo campo.
  - `VERSAO.txt` bump para v4.0; template público regenerado; central
    sincronizada com `_github-repo-local/` e push para
    `https://github.com/iriqspina/MEGAB-R-A-I-N.git`.
- Próximo passo: propagar megabrain v4.0 para projetos derivados (Rodada,
  TLOU, Jarvis, Financeiro da Silva); configurar remote do TLOU se quiser
  push; adotar bibliotecas do `requirements.txt` quando o ambiente permitir.
- Alerta: nenhum
