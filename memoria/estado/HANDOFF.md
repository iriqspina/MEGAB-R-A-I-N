# HANDOFF — megabrain core

TRAVADO_POR: livre
ATÉ: —
ESCOPO: —

## PARA VOCÊ (<USUARIO>)

1. **Teste do plugin:** abra uma sessão NOVA e rode `/megabrain`. Se a skill
   carregar enxuta (roteiro curto, caminhos v7), a reinstalação do 1.6.1
   pegou. Se vier a velha, o sync da conta falhou — reinstale o `.plugin`
   de `dist\` de novo.
2. **Quando quiser (sem pressa):** resíduo `metaprotocolo` nos diretórios
   dos agentes — é plugin velho ainda registrado + dumps de memória
   importados (2026-08-15). Plugin velho sai desinstalando; dumps de memória
   não se reescrevem. É a única coisa segurando o `legado: limpo` do
   preflight.
3. Sessões à parte quando quiser: Ollama+reindex · Obsidian · pesquisa de
   modos · Figma (board 24) · triagem de 04_visuais.

## O que mudou nesta sessão (260824 tarde/noite, claude · Cowork)

- **Bug do painel RESOLVIDO:** `01_acoes/260824_enviar-pro-github.cmd`
  reescrito — parêntese sem escape no bloco if abortava o batch depois do
  push (". foi inesperado neste momento"); agora sem parênteses em blocos,
  guard `where python`, relatório com errorlevel + saída no push.log.
  Verificado: rodada 16:26 logou cf73db8 + "relatorio OK", painel regenerou.
- `01_acoes/260824_novo-projeto.cmd`: corrigido bug fatal de expansão
  (%PROJETOS% em bloco if → sempre cancelava na primeira rodada).
- `01_acoes/260824_refresh-plugin-kimi.cmd`: parêntese cosmético escapado;
  RODADO — skills do Kimi (CLI + desktop) voltaram a bater com a fonte.
- Push v7 confirmado direto no remoto (ls-remote: GitHub = local = cf73db8).
- Revisão geral: preflight git✓ skills✓ fatos✓ legado✗(só agentes/histórico),
  suíte 25/25, demais 5 .cmd auditados e limpos.

## O que ficou aberto

- Teste do plugin 1.6.1 (item 1 acima) — critério de pronto: sessão nova
  carrega a skill v6.0 enxuta.
- Etapa 2 da reorg (motor\): APROVADA em princípio; método = o da etapa 1 +
  revisão das ~170 refs ambíguas linha a linha + 25 testes. bin\ NÃO sai da
  raiz (hook local em ~/.claude/settings.json aponta pra ele).
- Legado dos agentes (item 2 acima, decisão dele).
- Agregador de telemetria no painel (neuron.jsonl + .mb-log → aba/slot) ·
  script "contribuir" · /ingerir dos vídeos do YouTube (raw).

## Próximo passo

Na próxima sessão de TRABALHO: Gate 0 (conferir plugin == 1.6.1 pelo
checklist de abertura), depois executar a **etapa 2 da reorg** (grep
por-arquivo das refs de skills/modelos/dna/referencias/tests/plugins,
revisar, mover pra motor\, reapontar, rodar 25 testes, atualizar board 15).

## Arquivos tocados

- `01_acoes/260824_enviar-pro-github.cmd` (reescrito, manhã)
- `01_acoes/260824_novo-projeto.cmd` (reescrito, tarde)
- `01_acoes/260824_refresh-plugin-kimi.cmd` (reescrito, tarde)
- `memoria/estado/{ESTADO,HANDOFF,DECISOES,CHECKLIST-ABERTURA}.md`
- `memoria/nucleo/licoes-megabrain.md`
- `00_painel/RELATORIO.html` (regenerado pelo fluxo corrigido)

## Risco pra próxima sessão

- **NUNCA editar .cmd com edit_block/patch via bridge** — corrompe encoding/
  CRLF (aconteceu hoje; lição registrada). Só reescrita completa via
  container.
- Skill carregada pode AINDA ser a velha se o sync do plugin falhou —
  conferir plugin.json antes de confiar (checklist de abertura).
- A pasta da central tem DOIS espaços antes do N (`MEGA B R A I  N`) —
  caminho com um espaço dá ENOENT.
- Git nunca pela pasta montada do bridge; .cmd/git/python nativos rodam bem
  via Desktop Commander (pause estoura timeout do MCP — mandar Enter ou
  force_terminate depois de checar por arquivo/log).
- Layout v7: caminhos antigos morreram; usar mb_utils.achar()/pasta().
  Tema 02 e 04_visuais intocáveis.
