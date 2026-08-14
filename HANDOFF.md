# HANDOFF — megabrain core

TRAVADO_POR: livre
ATÉ: -
ESCOPO: -

## O que foi feito
- Auditoria do estado do megabrain após atualização do Claude (v3.9):
  - Conferidos `ESTADO.md`, `HANDOFF.md`, `DECISOES.md`, `VERSAO.txt`,
    `MEGABRAIN.md`, `260810_MEGABRAIN.md`, `skills/megabrain/SKILL.md`,
    `bin/`, `dna/` e `licoes-megabrain.md`.
  - Corrigida regressão em `skills/megabrain/SKILL.md`: caminhos absolutos
    `<MEGABRAIN_ROOT>/` voltaram para `<MEGABRAIN_ROOT>/`
    (a decisão 260814 tornou os scripts portáteis; o caminho absoluto quebraria
    qualquer outra máquina e vazaria o path local no template público).
  - Atualizado `README.md`: antes citava apenas `mb-sync.py` e
    `mb-sync-memoria.py`; agora lista todo o toolbox (`mb-check-version.py`,
    `mb-generate-template.py`, `mb-aspirador.py`, `mb-relatorio-dna.py`,
    `mb-relatorio-projeto.py`, `mb-sync-projeto-para-central.py`).
  - Removida pasta `MEGABRAIN/` criada acidentalmente na raiz da central por
    uso errado de `mb-check-version.py --projeto` apontando para a própria
    central. A central não deve ter uma cópia de si mesma dentro dela.
  - Regenerado `260810_github-export/` com `mb-generate-template.py`:
    - inclui `dna/` (RELATORIO-DNA.html + dna.json + README.md);
    - inclui `bin/mb-relatorio-projeto.py`;
    - exclui `_to_delete/` e `alteracoes-pendentes/` (pastas internas,
      adicionadas à lista de exclusão do gerador);
    - remove `MEGABRAIN-RELATORIO-DNA.html` solto (substituído por `dna/`);
    - sanitização de caminhos/nomes pessoais confirmada.
  - Sincronizado `260810_github-export/` → `_github-repo-local/` com
    `robocopy /MIR /XD .git`.
  - Commit e push para o repositório público `iriqspina/MEGAB-R-A-I-N`.
  - Nova decisão registrada em `DECISOES.md` sobre a correção do caminho
    absoluto e a exclusão de pastas internas do template.
  - Nova lição global registrada em `licoes-megabrain.md` sobre caminhos
    absolutos no SKILL.md e o risco de poluir o template público.

## O que ficou aberto
- Propagar `bin/mb-relatorio-projeto.py` (com a seção "resolução") para os
  projetos que já têm router próprio (Rodada, TLOU/portfólio, Jarvis,
  Financeiro da Silva) — cada um precisa de um `gerar_relatorio.py` próprio
  com os caminhos certos de `--plano`/`--extra`/`--skill`.
- Melhorias visuais na árvore de desenvolvimento do DNA (responsividade,
  mais nós, animações) — item antigo, ainda não retomado.
- Integração automática de download + atualização de DNA a partir do git —
  item antigo, ainda não retomado.

## Próximo passo concreto
Quando for propagar pro Rodada/TLOU/Jarvis/Financeiro da Silva:
`python bin/mb-relatorio-projeto.py --projeto "<raiz do projeto>" --titulo
"<nome>" --plano "<arquivo vivo>" [--extra ...] [--skill "<SKILL.md do
router>"]`, depois criar o wrapper em `05_scripts/` (ou pasta equivalente)
igual ao do Financeiro da Silva. A seção "resolução" já funciona sem
configuração extra se o arquivo vivo tiver heading tipo "## Plano de ação"/
"## Estratégia" — senão usar `--resolucao-titulo` pra ensinar a palavra-chave
do domínio daquele projeto.

## Arquivos tocados
- `skills/megabrain/SKILL.md` (caminhos absolutos → `<MEGABRAIN_ROOT>`)
- `README.md` (lista completa de scripts)
- `bin/mb-generate-template.py` (exclui `_to_delete/` e `alteracoes-pendentes/`)
- `MEGABRAIN.md`
- `260810_MEGABRAIN.md`
- `VERSAO.txt`
- `DECISOES.md`
- `ESTADO.md`
- `HANDOFF.md`
- `licoes-megabrain.md`
- `260810_github-export/` (regenerado)
- `_github-repo-local/` (sincronizado via robocopy)

<!-- mb-sync:lock:start -->
TRAVADO_POR: livre
<!-- mb-sync:lock:end -->
