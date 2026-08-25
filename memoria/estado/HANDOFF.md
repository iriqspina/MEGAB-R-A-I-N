# HANDOFF — megabrain core

TRAVADO_POR: livre
ATÉ: —
ESCOPO: —

## PARA VOCÊ (<USUARIO>)

1. ~~**Reinstale o plugin 1.6.3**~~ — FEITO (260824, confirmado por ele ao
   Kimi). Mudou a skill
   megabrain (layout motor\) e a /ingerir (wikilink + mapa do cérebro).
2. **Obsidian: FEITO** — instalado por você, vault registrado e aberto no
   cérebro. Vault `Downloads` removido por você (260824). Sobrou só decidir se
   apaga o `.obsidian\` que ficou dentro de `<USER_HOME>\Downloads`.
   Quando quiser, abra o grafo (Ctrl+G) e me diga se a leitura serve.
3. **Olhe a aba Cérebro** no relatório (00_painel\RELATORIO.html) e me diga se
   a leitura serve. É a aba nova, junto com a caixa "você perguntou".
4. **Nota do portfólio**: `<PROJETOS_ROOT>\Portfolio\260824_nota_megabrain-como-case.md`
   — decisões que são suas (case ou bastidor, quanto mostrar, formato).
5. Sessões à parte quando quiser: Ollama+reindex · pesquisa de modos (item 7,
   pausado por você) · triagem de 04_visuais · legado dos agentes.

## O que mudou nesta sessão (260824, 4ª — fila 2→6)

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

## Próximo passo

Sessão de trabalho seguinte: escolher entre (a) compreensores de padrões
(spec §7, agora que a telemetria existe), (b) pesquisa de referências de
modos pra você estudar, ou (c) o case do portfólio.

## Arquivos tocados

- `bin/`: mb_telemetria.py · mb-mapa-refs.py · mb-migrar-motor.py ·
  mb-testar.py · mb-obsidian.py (novos) · mb_utils.py · mb_workspace.py ·
  mb-relatorio-vivo.py · mb-contexto.py · mb-check-version.py ·
  mb-generate-template.py · mb-build-plugin-claude.py · mb-preflight.py ·
  mb-indice-licoes.py · mb-aspirador.py · mb-observar.py ·
  mb-orquestrador-ia.py · mb-patch-v5.py · mb-sync-projeto-para-central.py ·
  mb-relatorio-dna.py · mb-recuperar-megabrain.py · mb-arrumar.py ·
  mb_visual.py · mb-checar-meta.py
- `motor/tests/`: test_mb_layout.py e test_mb_telemetria.py (novos) + os 4
  antigos com raiz achada por subida
- `01_acoes/`: 260824_abrir-cerebro-obsidian.cmd (novo) · sincronizar-projetos ·
  novo-projeto · refresh-plugin-kimi (só os caminhos, por reescrita de bytes)
- `motor/gerenteneuron/`: gerente.py · app.py · router.py · aspirar.cmd
- `memoria/`: ESTADO · HANDOFF · DECISOES (+6) · licoes (+4) · VERSAO ·
  CHECKLIST · MEGABRAIN.md · README.md · pendencias/260824_portfolio-megabrain
- `03_docs/260824_megabrain-do-zero.html` (boards 15, 15B e o índice)
- `.gitignore` · `.claude/CLAUDE.md` · `memoria/cerebro/.obsidian/`

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
