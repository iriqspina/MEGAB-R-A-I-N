# HANDOFF — megabrain core

TRAVADO_POR: livre
ATÉ: —
ESCOPO: —

## PARA VOCÊ (<USUARIO>)

1. A parte técnica desta rodada está fechada. Abra
   `01_acoes/01_ABRIR-RELATORIO.cmd` para validar se o relatório de ~141 KB
   funciona como ponto único de entrada no uso real.
2. O histórico público ainda contém três caminhos locais antigos e o usuário
   `<USUARIO>`, sem chave/token/senha. Recomendação já medida: não reescrever o
   histórico; documentar se o repositório ganhar circulação relevante.

## O que foi fechado

1. A trava por arquivo deixou de ser rascunho: `bin/mb_trava.py` usa criação
   exclusiva, dono/PID/prazo, expiração, reentrada e escrita atômica.
2. O read-modify-write está protegido antes da leitura em HANDOFF, PROGRESSO,
   fila, sign-offs, lições e sincronização projeto → central; estado, relatório
   e índices também recusam outro dono.
3. `DECISOES.md` recusa IDs repetidos desde 260825. O preflight também bloqueia
   duplicata e arquivo canônico órfão na raiz.
4. A colisão `260825y` foi resolvida com rastro: AI reviewer manteve o endereço
   citado; a decisão offline virou `260825ag`.
5. As cinco lições recriadas na raiz foram fundidas no núcleo. A órfã foi
   removida e `mb-sync-projeto-para-central.py` agora resolve a fonte canônica
   com `u.achar()`.
6. As três mecânicas do djinnai.io estão implementadas: fila de tasks, reviewer
   de acceptance criteria e sign-off de spec com detecção de obsolescência.
7. Os 19 megabrains de projeto foram auditados e convertidos em cópias magras;
   a central é o único dono da máquina. Fase 3 concluída: todas as cópias em v7.5,
   0 divergências (decisão §260825b0).

## Verificação

- `python bin/mb-testar.py` → 141/141.
- `python bin/mb-preflight.py --repo . --forcar` → PODE COMEÇAR.
- `python bin/mb_trava.py conferir-ids` → IDs únicos desde 260825.
- Dois processos disputando o mesmo arquivo → o segundo sai 1 sem alterar o
  conteúdo; `mb-fila` tem prova funcional desse contrato.
- `python bin/mb-auditar-copias.py` → 19 cópias, todas em v7.5, formato magra,
  0 mortos, 0 velhos, 0 KB de peso morto. Fase 3 concluída (decisão §260825b0).
- `git diff --check` → limpo antes da consolidação.

## Arquivos centrais desta entrega

- Trava: `bin/mb_trava.py`, `motor/tests/test_mb_trava.py`, `.gitignore`.
- Escritores: `mb-sync.py`, `mb-relatorio-vivo.py`, `mb-estado.py`, `mb-fila.py`,
  `mb-spec-signoff.py`, `mb-sync-projeto-para-central.py`,
  `mb-indice-licoes.py`, `mb-indice-cerebro.py`.
- Contrato: `motor/skills/megabrain/SKILL.md`, `memoria/nucleo/MEGABRAIN.md`,
  decisão `260825ad` e lição “travar só no save ainda perde atualização”.

## Próximo passo técnico

Nenhum obrigatório. Em nova mudança: preflight → `mb-sync.py lock` para presença
→ `mb_trava.py` no arquivo real → teste → estado/handoff → release → commit.

<!-- mb-sync:lock:start -->
USUARIO: SYSTEM
TRAVADO_POR: codex-consolidador
ATE: 2026-08-25 14:19
ESCOPO:
  - bin/
  - motor/tests/
  - memoria/estado/
  - memoria/nucleo/
  - memoria/cerebro/
  - dados/
  - 00_painel/
  - 90_arquivo/
<!-- mb-sync:lock:end -->
