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
3. **Mecânica 1 do djinnai.io** (specs vivas com sign-off obsoleto): está na
   fila como próxima. Quer implementar, arquivar como referência ou descartar?
4. **Resíduo histórico no git público**: `pyvenv.cfg` e 3 caminhos pessoais em
   commits antigos do clone. Sem chave; revela usuário e caminho local.
   Recomendação da auditoria: deixar como está e documentar.

## O que mudou nesta sessão (260825, 5ª — fila do djinnai.io)

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

Sessão de trabalho seguinte: decidir sobre a **mecânica 1 do djinnai.io**
(specs vivas com sign-off obsoleto) — implementar, arquivar como referência no
`cerebro/wiki/`, ou descartar. Depois disso: push da central, Fase 3 dos
megabrains de projeto, e trava por escopo com histórico.

## Arquivos tocados

- `bin/`: mb-fila.py (novo) · mb-review-criteria.py (novo) ·
  mb_telemetria.py · mb-mapa-refs.py · mb-migrar-motor.py · mb-testar.py ·
  mb-obsidian.py · mb_utils.py · mb_workspace.py · mb-relatorio-vivo.py ·
  mb-contexto.py · mb-check-version.py · mb-generate-template.py ·
  mb-build-plugin-claude.py · mb-preflight.py · mb-indice-licoes.py ·
  mb-aspirador.py · mb-observar.py · mb-orquestrador-ia.py · mb-patch-v5.py ·
  mb-sync-projeto-para-central.py · mb-relatorio-dna.py ·
  mb-recuperar-megabrain.py · mb-arrumar.py · mb_visual.py · mb-checar-meta.py
- `motor/tests/`: test_mb_fila.py (novo) · test_mb_review_criteria.py (novo) ·
  test_mb_layout.py · test_mb_telemetria.py + os 4 antigos com raiz achada por
  subida
- `motor/modelos/`: SPEC.md (novo)
- `dados/`: fila.json (novo) · estado.json (regenerado)
- `90_arquivo/scripts-uso-unico-260825/`: mb-specimen.py (aposentado) ·
  LEIAME.md
- `memoria/`: ESTADO · HANDOFF · DECISOES (+2) · licoes · VERSAO · CHECKLIST ·
  MEGABRAIN.md · README.md
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
