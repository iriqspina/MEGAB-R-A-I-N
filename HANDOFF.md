# HANDOFF — megabrain core

TRAVADO_POR: livre
ATÉ: -
ESCOPO: -

## O que foi feito
- Criado `bin/mb-relatorio-dna.py` que gera `MEGABRAIN-RELATORIO-DNA.html`: HTML autocontido, interativo, com árvore de desenvolvimento visual (skill tree) e seção "Para a IA".
- Atualizado `bin/mb-check-version.py`: detecta central automaticamente (env `MEGABRAIN_CENTRAL` ou diretório do script), sincroniza `bin/` e o relatório DNA, e adicionou `--verificar-git`.
- Atualizado `bin/mb-generate-template.py`: portátil, inclui scripts de versionamento/relatório/aspirador, cria `.gitignore` e exclui `skills/conclusao-megabrain`.
- Corrigido `bin/mb-aspirador.py`: não coleta mais informacionais da raiz do projeto; mantém apenas notas locais em `.mb-aspirador/`.
- Atualizada `referencias/260813_aspirador-codigo.md` para refletir a função corrigida do aspirador.
- Bump `VERSAO.txt` para v3.7.
- Sincronizado pacote público e feito push para `https://github.com/iriqspina/MEGAB-R-A-I-N.git`.

## O que ficou aberto
- Melhorias visuais na árvore de desenvolvimento (responsividade, mais nós, animações).
- Gerador de relatório de projeto específico (instância aplicada, ex.: TLOU).
- Integração automática de download + atualização de DNA a partir do git.

## Próximo passo concreto
Quando quiser evoluir o visual da árvore ou criar o gerador de relatório de projeto, rode `python bin/mb-relatorio-dna.py` e sincronize para `_github-repo-local`.

## Arquivos tocados
- `bin/mb-relatorio-dna.py` (novo)
- `bin/mb-check-version.py`
- `bin/mb-generate-template.py`
- `bin/mb-aspirador.py`
- `referencias/260813_aspirador-codigo.md`
- `MEGABRAIN-RELATORIO-DNA.html` (gerado)
- `.gitignore` (novo)
- `VERSAO.txt`
- `DECISOES.md`
- `ESTADO.md`
- `HANDOFF.md`
- `260810_github-export/`
- `_github-repo-local/`

<!-- mb-sync:lock:start -->
TRAVADO_POR: livre
<!-- mb-sync:lock:end -->
