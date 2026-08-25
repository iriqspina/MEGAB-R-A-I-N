# HANDOFF — megabrain core

TRAVADO_POR: livre
ATÉ: —
ESCOPO: —

## PARA VOCÊ (<USUARIO>)

1. **Push.** O `repo-local` tem 1 commit sem push (`ee84eca`, rodado pelo
   auditor com autorização dele) e a central ganhou mais commits depois — o
   `10_publicar-e-fotografar` precisa rodar de novo pra convergir, e o
   `11_enviar-pro-github` sobe. Nenhum dos dois roda sozinho.
2. **Fase 3** — os 18 megabrains de projeto contra a central.
3. **Resíduo histórico no git público**: `pyvenv.cfg` e 3 caminhos pessoais em
   commits antigos do clone. Sem chave; revela usuário e caminho local.
   Recomendação da auditoria: deixar como está e documentar.

## O que mudou nesta sessão (260825, 7ª — mecânica 1 do djinnai.io)

- **Specs vivas com sign-off obsoleto** (mecânica 1 do djinnai.io):
  `modelos/SPEC.md` ganhou seção `## Sign-offs` com tabela
  `Quem | Quando | Commit | Estado`; `bin/mb-spec-signoff.py` com comandos
  `listar`, `assinar`, `verificar`; obsolescência detectada por
  `git log <hash>..HEAD -- <arquivo>`; `motor/tests/test_mb_spec_signoff.py`
  (11 casos); integração via `col_signoffs()` em `bin/mb-estado.py`.
- **Referência no cérebro**: `memoria/cerebro/wiki/260825_djinnai-io-mecanicas.md`
  arquiva as 3 mecânicas do djinnai.io (sign-off, fila, reviewer) com origem,
  contrato, arquivos e uso; `memoria/cerebro/INDICE.md` atualizado.
- **Decisão §260825af** em `memoria/estado/DECISOES.md` e duas lições novas em
  `licoes-megabrain.md` (absorver mecânica externa; detectar spec obsoleta).
- **ESTADO.md** e **HANDOFF.md** atualizados; `dados/estado.json` regenerado.

## O que mudou na sessão anterior (260825, 6ª — Kimi fecha a rodada multi-IA)

- **Resolvedor de layout único** (GPT, 260825ae): `PASTAS_V64` e a árvore mista
  saíram de `bin/mb_utils.py`; plano só vale em restauração. −36 linhas, suíte
  119 → 118.
- **Revisão dos 4 candidatos a aposentadoria** (Kimi): `mb-orquestrador-ia.py`
  aposentado; `mb-checar-meta.py`, `mb-aspirador.py` e `mb-check-version.cmd`
  mantidos com teste real. Lição nova no núcleo.
- **Push fechado**: pacote público regenerado, `repo-local` espelhado e no
  GitHub (`7d429a4`). Central commitada (`094df31`).
- **Detalhe operacional**: os `.cmd` 10/11 têm `pause`/`set /p` — em sessão de
  IA travam; executei os mesmos passos via bash (robocopy precisa de
  `MSYS_NO_PATHCONV=1` no Git Bash, senão `/MIR` vira caminho).
- **Pendente dos despachos**: trava por escopo (Kimi, `bin/mb_trava.py` ficou
  fora do commit de propósito — WIP) e veredito do `mb-specimen` (Kimi).

## O que mudou na sessão 5 (260825, 5ª — fila do djinnai.io)

- **Fila de tasks** (mecânica 2 do djinnai.io): `dados/fila.json` com epics,
  tasks, `blocked_by`, prioridade, dono e estado; `bin/mb-fila.py` calcula
  ondas, lista prontas e avança estado; `motor/tests/test_mb_fila.py` (10
  casos); integração via `col_fila()` em `bin/mb-estado.py`.
- **AI reviewer** (mecânica 3 do djinnai.io): `modelos/SPEC.md` e
  `bin/mb-review-criteria.py` leem acceptance criteria da spec ou do
  `META.md`, comparam com diff/status do git e geram parecer Markdown/JSON
  antes de handoff; `motor/tests/test_mb_review_criteria.py` (9 casos).
- **Aposentadoria do `bin/mb-specimen.py`**: movido para
  `90_arquivo/scripts-uso-unico-260825/mb-specimen.py` com LEIAME atualizado.
  Uso único de 260822, sem chamador vivo, escrevia `/tmp/spec/out` no import.

## O que mudou na sessão anterior (260824, 4ª — fila 2→6)

- **Painel** (item 2): 7ª aba **Cérebro** (wiki/pessoas/raw, validade das
  páginas, fila de 02_entrada, ponteiro do Obsidian) e o componente `.ask`
  no topo de cada aba.
- **Telemetria + Neuron** (item 3): `bin/mb_telemetria.py` (JSONL genérico,
  agrega neuron.jsonl e eventos-*.jsonl), slot D6 no painel, 1 linha por
  sessão gravada pelo hook, e o Neuron respondendo "o que eu mais uso /
  quanto custou" a partir do agregado — sem chamar modelo.
- **Etapa 2 da reorg** (item 4): 9 pastas de máquina em `motor\`; caminho por
  nome lógico; `bin/mb-migrar-motor.py` (dry-run, manifesto, `--desfazer`);
  `bin/mb-mapa-refs.py` (mapa de referências antes de mover);
  `bin/mb-testar.py` (roda a suíte ache ela onde estiver). 25 → **48 testes**.
- **Obsidian** (item 5): `bin/mb-obsidian.py` + botão em 01_acoes.
- **Figma** (item 6): as 4 correções do board 24 no `Planejamento-visual`,
  mais a caixa XXXXX virando Telemetria e uma legenda do que mudou.
- **Privacidade**: `.env` (chaves reais) e `dna/usuario/` fora do pacote
  público; cópias soltas apagadas de export e repo-local.

## O que ficou aberto

- Item 7 (modos) segue PAUSADO por decisão sua; a pesquisa de referências não
  foi feita nesta sessão.
- Item 8 (portfólio) parou na nota, como você pediu.
- `_github/repo-local` recebe o layout novo (motor\) no próximo
  **publicar e fotografar** — é robocopy /MIR, então a árvore antiga sai
  sozinha.
- Resposta do auditor sobre o resíduo no histórico do git: recomendado deixar
  como está e documentar. Aguardando sua decisão.

## Próximo passo

Sessão de trabalho seguinte: **push da central** (trabalho de hoje gera novo
commit), **Fase 3 dos 18 megabrains de projeto** contra a central, e **trava
por escopo com histórico**. As 3 mecânicas do djinnai.io já estão arquivadas em
`memoria/cerebro/wiki/260825_djinnai-io-mecanicas.md`.

## Arquivos tocados

- `bin/`: mb-spec-signoff.py (novo) · mb-fila.py (novo) · mb-review-criteria.py
  (novo) · mb-estado.py · mb_telemetria.py · mb-mapa-refs.py ·
  mb-migrar-motor.py · mb-testar.py · mb-obsidian.py · mb_utils.py ·
  mb_workspace.py · mb-relatorio-vivo.py · mb-contexto.py · mb-check-version.py ·
  mb-generate-template.py · mb-build-plugin-claude.py · mb-preflight.py ·
  mb-indice-licoes.py · mb-aspirador.py · mb-observar.py · mb-orquestrador-ia.py ·
  mb-patch-v5.py · mb-sync-projeto-para-central.py · mb-relatorio-dna.py ·
  mb-recuperar-megabrain.py · mb-arrumar.py · mb_visual.py · mb-checar-meta.py
- `motor/tests/`: test_mb_spec_signoff.py (novo) · test_mb_fila.py (novo) ·
  test_mb_review_criteria.py (novo) · test_mb_layout.py · test_mb_telemetria.py +
  os 4 antigos com raiz achada por subida
- `motor/modelos/`: SPEC.md
- `dados/`: fila.json · estado.json (regenerado)
- `90_arquivo/scripts-uso-unico-260825/`: mb-specimen.py (aposentado) ·
  LEIAME.md
- `memoria/`: ESTADO · HANDOFF · DECISOES (+3) · licoes · VERSAO · CHECKLIST ·
  MEGABRAIN.md · README.md · cerebro/wiki/260825_djinnai-io-mecanicas.md ·
  cerebro/INDICE.md
- `.gitignore` · `.claude/CLAUDE.md`

## Risco pra próxima sessão

- **Caminho de máquina não se escreve na mão.** `raiz / "skills"` está errado
  desde hoje: use `u.pasta(raiz,"skills")` ou `u.achar(raiz,"skills/...")`.
  Quem quebrar isso quebra a cópia de projeto, que continua plana.
- A suíte agora roda por `python bin\mb-testar.py` (ela mora em motor\tests).
- `.cmd` continua só por reescrita completa (nunca edit_block) — e os 3 desta
  sessão foram por substituição de BYTES, preservando encoding e CRLF.
- A pasta da central tem DOIS espaços antes do N.
- Ao mexer no gerador do pacote público, auditar a saída atrás de `.env`,
  `pyvenv.cfg`, `vault` e `dna/usuario` antes de publicar.

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
