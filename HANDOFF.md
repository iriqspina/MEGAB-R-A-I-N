# HANDOFF — megabrain core

TRAVADO_POR: livre
ATÉ: -
ESCOPO: -

## O que foi feito
- Redundância contra pontos únicos de falha implementada no megabrain
  (v4.3):
  - `bin/mb-backup-central.py`: cria backup zip da pasta central do
    megabrain (`.mb-backup/central-YYYYMMDD-HHMMSS.zip`), excluindo
    `.git`, `__pycache__`, caches e pastas geradas.
  - `bin/mb-recuperar-megabrain.py`: recupera a pasta `MEGABRAIN/` de um
    projeto a partir de um backup zip, de outro projeto que ainda tenha
    `MEGABRAIN/`, da central local, ou detecta automaticamente a melhor
    fonte disponível.
  - `OFFLINE.md` atualizado com instruções de backup e recuperação.
  - `MEGABRAIN.md`, `260810_MEGABRAIN.md` e `README.md` ganharam seção
    "Uso offline e recuperação" com exemplos de comando.
- Modo offline implementado anteriormente (v4.2):
  - `OFFLINE.md` e flag `--offline` em `mb-check-version.py`.
- Diferenciação de usuário implementada anteriormente (v4.0/v4.1):
  - Campo `USUARIO:` no `HANDOFF.md` e nos arquivos de identidade;
  - documentação de migração v4.0.
- `VERSAO.txt` atualizado para v4.3.
- Template público `260810_github-export/` regenerado e sincronizado com
  `_github-repo-local/` via robocopy.
- Push da central para `https://github.com/iriqspina/MEGAB-R-A-I-N.git`.
- Projetos derivados serão sincronizados com v4.3 na sequência.
- Testes manuais: backup da central criado com sucesso; recuperação de
  projeto a partir do backup zip funcionou; recuperação a partir de outro
  projeto funcionou.

## O que ficou aberto
- Propagar v4.3 para Financeiro da Silva, Jarvis, Rodada e TLOU.
- Configurar remote do repo TLOU se o <USUARIO> quiser push.
- Adotar bibliotecas de `requirements.txt` quando o ambiente permitir.
- Melhorias visuais na árvore de desenvolvimento do DNA — item antigo.
- Integração automática de download + atualização de DNA a partir do git —
  item antigo.

## Próximo passo concreto
Configurar remote do TLOU e fazer push, ou deixar o commit local até que
o <USUARIO> defina onde o repo deve morar. A entrega v4.3 está concluída.

## Arquivos tocados
- `bin/mb-backup-central.py` (novo)
- `bin/mb-recuperar-megabrain.py` (novo)
- `bin/mb_utils.py`
- `bin/mb-sync.py`
- `bin/mb-sync-memoria.py`
- `bin/mb-check-version.py`
- `260810_memoria-pessoal.md`
- `260810_backup-raiz-perfil/260810_AGENTS.md`
- `260810_backup-raiz-perfil/260810_CLAUDE.md`
- `260810_backup-raiz-perfil/260810_GEMINI.md`
- `referencias/260810_sync-memoria.md`
- `MEGABRAIN.md`
- `260810_MEGABRAIN.md`
- `README.md`
- `OFFLINE.md`
- `VERSAO.txt`
- `ESTADO.md`, `HANDOFF.md`, `DECISOES.md`
- `260810_github-export/` (regenerado)
- `_github-repo-local/` (sincronizado, commit/push)
- Projetos derivados: `Financeiro da Silva/`, `Jarvis/`, `Rodada/`,
  `Portfolio/The Last of Us - Part II/`

<!-- mb-sync:lock:start -->
TRAVADO_POR: livre
<!-- mb-sync:lock:end -->
