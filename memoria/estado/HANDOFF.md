# HANDOFF — megabrain core

TRAVADO_POR: livre
ATÉ: —
ESCOPO: —

## PARA VOCÊ (<USUARIO>) — ordem importa

1. **Abrir o painel novo:** `00_painel\RELATORIO.html` (a pasta mudou de nome —
   era 04_relatorios). Abas em cima, modo no topo, ＋ fixa abas lado a lado,
   feedback na alça direita. Fonte e densidade nos botões da barra.
2. **Instalar o plugin novo no Cowork:** `dist\260824_megabrain-v1.6.1.plugin`
   — é o que ativa a skill enxuta (v6.0). Sem isso eu sigo carregando a regra
   velha nas próximas sessões.
3. **Publicar + push (nomes novos, mesma ordem):**
   `01_acoes\260824_publicar-e-fotografar.cmd` e DEPOIS
   `01_acoes\260824_enviar-pro-github.cmd`. Leva a v7.0 inteira pro GitHub.
4. **Sincronizar projetos:** `01_acoes\260824_sincronizar-projetos.cmd`.
5. Sessões à parte, quando quiser: religar Ollama (+reindexar) · instalar
   Obsidian (obsidian.md) · pesquisa sobre modos · Figma (4 correções).
6. Triagem visual segue esperando: `04_visuais\00_entrada\260822_FOLHA-DE-CONTATO.html`.

## O que mudou nesta sessão (260824, claude · Cowork — 3 rodadas)

- **Migração v7.0 (etapa 1):** 14 moves (memoria/{nucleo,estado,identidade,
  cerebro,pendencias} · 00_painel · 01_acoes · 02_entrada nova · 03_docs ·
  04_visuais · dist · _github/{export,repo-local} · relatorio-megabrain →
  90_arquivo), 8 .cmd renomeados por verbo com prefixo 260824, 44 arquivos
  reapontados, `mb_utils` com fallback pro layout v6.4 (centrais/cópias
  antigas seguem legíveis). Backup integral do que foi editado + manifest em
  `90_arquivo/migracao-v7-260824/`. Suíte 25/25. **Etapa 2 pendente:** agrupar
  pastas de código em `motor\` (sessão dedicada — ~170 refs ambíguas).
- **Skill v6.0 (tirar peso):** roteiro curto (~10 KB, era 31 KB/608 linhas);
  texto integral v5.7 preservado em `referencias/260824_skill-completa-v5.md`;
  fontes atualizadas em `skills/` e `plugin-megabrain-claude/`; builds 1.6.0 e
  1.6.1 validados (node --check + smoke) em `dist/`.
- **Cérebro:** convenção `VALIDADE:` (temporário × permanente) documentada no
  MODELO e LEIAMEs; `bin/mb-manutencao-cerebro.py` (avisa vencidas e fontes
  esquecidas em 02_entrada; `--arquivar` move pra 90_arquivo, nunca apaga;
  `--auto` = máx. 1x/7 dias); skill /ingerir ganhou a seção de manutenção.
- **Neuron:** `gerenteneuron/router.py` — triagem cheap/standard/deep
  DESLIGADA (classificador guardado no código), tudo na classe de ponta;
  telemetria por resposta em `.mb-log/neuron.jsonl` (modelo, custo, tokens,
  duração). Compila; os testes do app rodam no venv dele (não rodei daqui).
- **Painel v7:** novo `bin/mb_workspace.py` + gerador `mb-relatorio-vivo.py`
  reestruturado em 6 abas; workspace salvável (localStorage com namespace),
  controles de fonte (13–20px) e densidade com clamp, chip do modo (lê
  `MODO:` do META.md — gravado `otimizado`), aba Ações lida de `01_acoes/*.cmd`
  (descrição + copiar caminho), aba Skills lida de `skills/*/SKILL.md`, aba
  Esquema com o desenho central→GitHub→usuário→projetos, Histórico com a
  timeline; rail de feedback (like local + rascunho persistente + copiar pro
  chat + aviso de consentimento com o "~~mete o pau~~" riscado). Degrada sem
  JS e sem o módulo. Relatório regenerado.
- Doc `03_docs/260824_megabrain-do-zero.html` varrido pro layout novo; board
  15 = mapa v7 real; board 26 = placar (7/10). Versão 260823 segue em
  90_arquivo.
- `VERSAO.txt` ganhou a linha v7.0. NÃO commitei git (cloud sem repo-fonte)
  — o commit sai do publicar dele.

## O que ficou aberto

- Instalação do plugin 1.6.1 (dele) · push (dele) · sincronizar (dele).
- Etapa 2 da reorg (`motor\`) — sessão dedicada com greps por-arquivo.
- Script "contribuir" (PR peneirado, spec §3) · Figma (board 24) · pesquisa
  de modos · Ollama/reindex · Obsidian vault.
- Telemetria megabrain-side (pesos de skills agregados no painel) — o coletor
  do Neuron já grava; falta o agregador/visualização (spec §4).
- 2º vídeo do YouTube sem título (raw em memoria/cerebro/raw/, /ingerir resolve).

## Próximo passo (concreto)

Depois do push dele: **etapa 2 da reorg** (motor\, greps por arquivo, testes)
OU **agregador de telemetria no painel** — o que ele pedir primeiro. Antes de
qualquer coisa na próxima sessão: conferir se o plugin instalado já é 1.6.1
(`/root/.claude/plugins/synced/megabrain/.claude-plugin/plugin.json`).

## Risco pra próxima sessão

- A skill CARREGADA pode ser a velha até ele instalar 1.6.1 — conferir versão
  antes de assumir regra nova. Caminhos novos: memoria/estado/*, 00_painel,
  01_acoes (o layout antigo morreu; mb_utils resolve os dois).
- Git nunca pela pasta montada do bridge. Não redesenhar o Tema 02. Não mexer
  em 04_visuais (triagem é dado). `dna/usuario/` e `90_arquivo/migracao-v7-*`
  são intocáveis.
- O hook local (~/.claude/settings.json) aponta pra `bin/` — bin ficou na
  raiz DE PROPÓSITO; não mover na etapa 2 sem tratar esse ponteiro externo.

## Arquivos tocados

Migração: ver `90_arquivo/migracao-v7-260824/manifest.json` (lista completa).
Novos: `bin/mb-migrar-v7.py` · `bin/mb-manutencao-cerebro.py` ·
`bin/mb_workspace.py` · `referencias/260824_skill-completa-v5.md` ·
`02_entrada/LEIAME.md` · `dist/260824_megabrain-v1.6.{0,1}.plugin`.
Editados: `skills/megabrain/SKILL.md` (+cópia plugin) · `skills/ingerir/*` ·
`gerenteneuron/router.py` · `bin/mb-relatorio-vivo.py` ·
`memoria/nucleo/VERSAO.txt` · `memoria/estado/{ESTADO,HANDOFF,DECISOES,META}.md`
· `03_docs/260824_megabrain-do-zero.html` · `tests/test_scripts_destrutivos.py`.
