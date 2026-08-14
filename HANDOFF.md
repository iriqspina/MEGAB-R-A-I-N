# HANDOFF — megabrain core

TRAVADO_POR: kimi
ATÉ: 2026-08-14 04:00
ESCOPO:
  - bin/mb-relatorio-dna.py
  - bin/mb-check-version.py
  - bin/mb-generate-template.py
  - MEGABRAIN-RELATORIO-DNA.html
  - DECISOES.md
  - ESTADO.md
  - HANDOFF.md
  - VERSAO.txt
  - 260810_github-export/
  - _github-repo-local/

## O que foi feito
- Corrigido o entendimento sobre aspirador: ferramenta de revisão de código pós-implementação, não coletora de informacionais.
- Definida arquitetura: relatório DNA (template canônico do megabrain) separado de relatório de projeto.
- Atualizado `DECISOES.md` com separação de responsabilidades, backup de DNA e versionamento portátil.

## O que está em andamento
- Criar gerador `bin/mb-relatorio-dna.py` que produz HTML interativo com árvore de desenvolvimento visual (skill tree).
- Tornar `mb-check-version.py` portátil (env var + auto-detect) e capaz de verificar contra git remote.
- Atualizar template público e sincronizar com `_github-repo-local`.

## Próximo passo concreto
Finalizar scripts, rodar gerador, testar localmente, sincronizar para `_github-repo-local`, commitar e fazer push para `origin/main`.

## Arquivos tocados
- `DECISOES.md`
- `ESTADO.md`
- `HANDOFF.md`

<!-- mb-sync:lock:start -->
TRAVADO_POR: kimi
ATÉ: 2026-08-14 04:00
<!-- mb-sync:lock:end -->
