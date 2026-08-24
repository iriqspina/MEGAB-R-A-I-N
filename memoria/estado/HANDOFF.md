# HANDOFF — megabrain core

TRAVADO_POR: livre
ATÉ: —
ESCOPO: —

## PARA VOCÊ (<USUARIO>)

1. **Confirmar o push da v7:** abra `00_painel\RELATORIO.html` → bloco git.
   Se mostrar "commit local SEM PUSH": rode
   `01_acoes\260824_publicar-e-fotografar.cmd` e DEPOIS
   `01_acoes\260824_enviar-pro-github.cmd`. O publicar foi corrigido no
   logout (lia o VERSAO.txt no lugar antigo e a mensagem de commit saía
   quebrada — "='").
2. Sessões à parte quando quiser: Ollama+reindex · Obsidian · pesquisa de
   modos · Figma (board 24) · triagem de 04_visuais.

## O que mudou no logout (260824, claude · Cowork)

- `01_acoes/260824_publicar-e-fotografar.cmd`: caminho do VERSAO.txt
  atualizado pra `memoria\nucleo\` + fallback quando a mensagem vier vazia.
- Lições novas em `memoria/nucleo/licoes-megabrain.md` (4) e itens novos no
  `memoria/estado/CHECKLIST-ABERTURA.md` (3).
- Estas escritas são PÓS-push: entram na próxima foto (publicar).

## O que ficou aberto

- Push da v7 (item 1 acima) — critério de pronto: `.mb-log\push.log` com
  entrada nova (depois de 24/08 18:30) e painel mostrando "nada pendente".
- Etapa 2 da reorg (motor\): APROVADA em princípio; método = o da etapa 1 +
  revisão das ~170 refs ambíguas linha a linha + 25 testes. bin\ NÃO sai da
  raiz (hook local em ~/.claude/settings.json aponta pra ele).
- Agregador de telemetria no painel (neuron.jsonl + .mb-log → aba/slot) ·
  script "contribuir" · /ingerir dos vídeos do YouTube (raw).

## Próximo passo

Na próxima sessão de trabalho: rodar o Gate 0, conferir plugin instalado
(= 1.6.1?) e push confirmado; então executar a **etapa 2 da reorg** (gerar
grep por-arquivo das refs de skills/modelos/dna/referencias/tests/plugins,
revisar, mover pra motor\, reapontar, rodar 25 testes, atualizar board 15).

## Risco pra próxima sessão

- Skill carregada pode ser a velha até o Cowork sincronizar o plugin 1.6.1 —
  conferir `/root/.claude/plugins/synced/megabrain/.claude-plugin/plugin.json`.
- Layout v7: caminhos antigos morreram; usar mb_utils.achar()/pasta().
- Git nunca pela pasta montada do bridge. Tema 02 e 04_visuais intocáveis.

## Arquivos tocados (logout)

`01_acoes/260824_publicar-e-fotografar.cmd` · `memoria/estado/ESTADO.md` ·
`memoria/estado/HANDOFF.md` · `memoria/estado/CHECKLIST-ABERTURA.md` ·
`memoria/nucleo/licoes-megabrain.md`
