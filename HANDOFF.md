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
  - `bin/mb-sync-memoria.py`: sincroniza o campo `USUARIO:` para
    `CLAUDE.md`, `GEMINI.md` e `AGENTS.md`; suporta `--usuario` para
    sobrescrever o valor detectado.
  - `260810_memoria-pessoal.md` e os backups em
    `260810_backup-raiz-perfil/` atualizados com
    `USUARIO: <USUARIO> (Iriq)`.
  - `referencias/260810_sync-memoria.md` ganhou seção explicando o campo.
- `VERSAO.txt` atualizado para v4.0.
- Template público `260810_github-export/` regenerado e sincronizado com
  `_github-repo-local/` via robocopy.
- Testes manuais: lock/release com detecção automática de usuário;
  sincronização de identidade com injeção de `USUARIO:` nos três destinos.

## O que ficou aberto
- Propagar megabrain v4.0 para projetos derivados (Rodada, TLOU, Jarvis,
  Financeiro da Silva).
- Configurar remote do repo TLOU se o <USUARIO> quiser push.
- Adotar bibliotecas de `requirements.txt` quando o ambiente permitir.
- Melhorias visuais na árvore de desenvolvimento do DNA — item antigo.
- Integração automática de download + atualização de DNA a partir do git —
  item antigo.

## Próximo passo concreto
Rodar `python "bin/mb-check-version.py" --projeto <pasta> --auto` nos
quatro projetos derivados para propagar v4.0. Para o TLOU, decidir se
configura um remote ou faz push manual.

## Arquivos tocados
- `bin/mb_utils.py`
- `bin/mb-sync.py`
- `bin/mb-sync-memoria.py`
- `260810_memoria-pessoal.md`
- `260810_backup-raiz-perfil/260810_AGENTS.md`
- `260810_backup-raiz-perfil/260810_CLAUDE.md`
- `260810_backup-raiz-perfil/260810_GEMINI.md`
- `referencias/260810_sync-memoria.md`
- `VERSAO.txt`
- `ESTADO.md`, `HANDOFF.md`, `DECISOES.md`
- `260810_github-export/` (regenerado)
- `_github-repo-local/` (sincronizado, commit/push)

<!-- mb-sync:lock:start -->
TRAVADO_POR: livre
<!-- mb-sync:lock:end -->
