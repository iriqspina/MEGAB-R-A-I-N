# ESTADO — megabrain core

- Versão ativa: 4.0
- Fase: concluída / entregue no GitHub e propagada para projetos derivados
- Última ação: implementada diferenciação de usuário no protocolo e
  propagada para todos os projetos derivados.
  - `bin/mb_utils.py`: novos helpers `extract_usuario` e `detectar_usuario`.
  - `bin/mb-sync.py`: campo `USUARIO:` no `HANDOFF.md`, detectado de
    `260810_memoria-pessoal.md` ou via `--usuario`.
  - `bin/mb-sync-memoria.py`: propaga `USUARIO:` para `CLAUDE.md`,
    `GEMINI.md` e `AGENTS.md`; suporta `--usuario` para forçar perfil.
  - `260810_memoria-pessoal.md` e arquivos em
    `260810_backup-raiz-perfil/` atualizados com `USUARIO: <USUARIO> (Iriq)`.
  - `referencias/260810_sync-memoria.md` documenta o novo campo.
  - Push da central para `https://github.com/iriqspina/MEGAB-R-A-I-N.git`.
  - Projetos derivados sincronizados: Financeiro da Silva, Jarvis, Rodada
    (com push), TLOU (commit local; sem remote).
- Próximo passo: configurar remote do TLOU se o <USUARIO> quiser push;
  adotar bibliotecas do `requirements.txt` quando o ambiente permitir.
- Alerta: nenhum
