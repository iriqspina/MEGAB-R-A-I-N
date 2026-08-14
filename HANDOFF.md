# HANDOFF — megabrain core

TRAVADO_POR: livre
ATÉ: -
ESCOPO: -

## O que foi feito
- Implementada diferenciação de usuário no megabrain (v4.0):
  - `bin/mb_utils.py`: helpers `extract_usuario` e `detectar_usuario`
    leem o campo `USUARIO:` do arquivo de identidade.
  - `bin/mb-sync.py`: a trava em `HANDOFF.md` agora grava `USUARIO:`
    junto com `TRAVADO_POR`, `ATE` e `ESCOPO`. O nome é detectado de
    `260810_memoria-pessoal.md` ou pode ser forçado com `--usuario`.
  - `mb-sync-memoria.py`: sincroniza o campo `USUARIO:` para
    `CLAUDE.md`, `GEMINI.md` e `AGENTS.md`; suporta `--usuario` para
    sobrescrever o valor detectado.
  - `260810_memoria-pessoal.md` e os backups em
    `260810_backup-raiz-perfil/` atualizados com
    `USUARIO: <USUARIO> (Iriq)`.
  - `referencias/260810_sync-memoria.md` ganhou seção explicando o campo.
- Documentação de migração v4.0 adicionada para projetos derivados e
  quem forkar/clonar o repo:
  - `MEGABRAIN.md` e `260810_MEGABRAIN.md`: nova seção 1b explicando o
    que mudou, por que importa, como configurar e como trocar/adicionar
    perfis.
  - `README.md`: seção "Migração v4.0 — diferenciação de usuário" com
    passos rápidos.
- `VERSAO.txt` atualizado para v4.1 (bump para disparar sincronização da
  documentação de migração v4.0 nos projetos derivados).
- Template público `260810_github-export/` regenerado e sincronizado com
  `_github-repo-local/` via robocopy.
- Push da central para `https://github.com/iriqspina/MEGAB-R-A-I-N.git`
  (commits `3e0a888`, `ac34a29`, `db386a0`, `0786a5d` e o da v4.1).
- Projetos derivados sincronizados com v4.0:
  - Financeiro da Silva (não é repo git; atualizado localmente).
  - Jarvis (não é repo git; atualizado localmente).
  - Rodada: sincronizado e push para
    `https://github.com/iriqspina/rodada.git` (commit `91a24e4`).
    Removido `MEGABRAIN/bin/__pycache__/` e `.mb-aspirador/` do commit;
    adicionadas essas pastas ao `.gitignore` do projeto.
  - TLOU (`Portfolio/The Last of Us - Part II`): sincronizado e commitado
    localmente (commit `60dcdc8`); não tem remote configurado, então push
    não foi feito. Criado `.gitignore` básico excluindo `__pycache__/` e
    `.mb-aspirador/` do megabrain.
- Testes manuais: lock/release com detecção automática de usuário;
  sincronização de identidade com injeção de `USUARIO:` nos três destinos.

## O que ficou aberto
- Re-sincronizar os quatro projetos derivados para receber a documentação
  de migração v4.0 recém-adicionada.
- Configurar remote do repo TLOU se o <USUARIO> quiser push.
- Adotar bibliotecas de `requirements.txt` quando o ambiente permitir.
- Melhorias visuais na árvore de desenvolvimento do DNA — item antigo.
- Integração automática de download + atualização de DNA a partir do git —
  item antigo.

## Próximo passo concreto
Rodar `python MEGABRAIN/bin/mb-check-version.py --projeto <pasta> --auto` nos
quatro projetos derivados para propagar a documentação v4.0. Depois,
configurar remote do TLOU se desejado.

## Arquivos tocados
- `bin/mb_utils.py`
- `bin/mb-sync.py`
- `bin/mb-sync-memoria.py`
- `260810_memoria-pessoal.md`
- `260810_backup-raiz-perfil/260810_AGENTS.md`
- `260810_backup-raiz-perfil/260810_CLAUDE.md`
- `260810_backup-raiz-perfil/260810_GEMINI.md`
- `referencias/260810_sync-memoria.md`
- `MEGABRAIN.md`
- `260810_MEGABRAIN.md`
- `README.md`
- `VERSAO.txt`
- `ESTADO.md`, `HANDOFF.md`, `DECISOES.md`
- `260810_github-export/` (regenerado)
- `_github-repo-local/` (sincronizado, commit/push)
- Projetos derivados: `Financeiro da Silva/`, `Jarvis/`, `Rodada/`,
  `Portfolio/The Last of Us - Part II/`

<!-- mb-sync:lock:start -->
TRAVADO_POR: livre
<!-- mb-sync:lock:end -->
