# plugin-megabrain-claude — plugin Cowork/Claude do megabrain (v1.7.1)

Plugin no formato Claude (`.claude-plugin/plugin.json` + `hooks/hooks.json` +
`skills/`), irmão do `plugin-megabrain/` (Kimi). A **fonte** vive na central do
megabrain; o repositório público recebe a cópia sanitizada pelo
`bin/mb-generate-template.py` (mesmo caminho de todo o resto do pacote).

## O que faz

- **Skill `megabrain`** — cópia do `skills/megabrain/SKILL.md` da central
  (v5.0), exceto a linha `description:` do frontmatter (sem os gatilhos legados
  `/metaprotocolo` e `metaclaude`). É a skill que roda no Cowork.
- **Skill `orquestracao1`** — cópia literal da fonte canônica. Um único
  orquestrador, resolvido por medição de harness/modelo/cota e não por slug
  fixo; até 5 workers paralelos, cada um com escopo de escrita exclusivo;
  `FABLE_LATEST` resolve o revisor compatível e faz uma única revisão final com
  effort adaptativo; `/grelhar` é opcional e, quando ativa, faz uma pergunta por
  vez com STOP real — encerrada ou pulada, o fluxo segue autônomo. As lentes
  `/hypadododiabo` e `/advogadododiabo` são opcionais, não entram em loop e não
  substituem o revisor final.
- **Skill `hypadododiabo`** — cópia literal da fonte canônica. Constrói o melhor
  caso defensável com evidência, condições, custos, experimento reversível e
  kill criteria; nunca decide produto em nome do <USUARIO>.
- **Skill `advogadododiabo`** — cópia literal da fonte canônica. Lente de
  downside, par do `hypadododiabo`: levanta até três objeções falsificáveis
  com evidência, custo do erro e o teste mais barato; nunca decide produto e
  não entra em pingue-pongue com a lente positiva — a síntese é do orquestrador.
- **Skill `quaseultracode`** — cópia literal da fonte canônica. Executa projeto
  grande por marcos a partir do ideal, com teto de 5h `[HEURÍSTICA]`, workers
  persistentes, Headhunter read-only, dupla passagem “casa ≠ cabana” e delta
  explícito para o próximo ciclo.
- **Skill `ingerir`** — cópia literal da fonte canônica. Ingere fontes brutas de
  `cerebro/raw/` e destila em páginas de wiki e cards de pessoas, mantendo
  `cerebro/INDICE.md`.
- **Skill `grelhar`** — cópia literal da fonte canônica. Entrevista em rodadas
  que esvazia o briefing antes de produzir, uma pergunta por turno e STOP real
  até resposta explícita.
- **Skill `traycer`** — cópia literal da fonte canônica. Roda a pipeline do
  Traycer (epic, core flow, tech plan, ticket breakdown, execute) sob os gates
  do megabrain.
- **Skill `leigolanguage`** — cópia literal da fonte canônica. Explica decisão
  técnica para quem não é programador decidir, mostrando a consequência
  concreta de cada caminho.
- **Skill `conclusao-megabrain`** — cópia literal da fonte canônica. Ponteiro
  para o Gate 6 (PASSAR O BASTÃO): esgota execução autônoma antes de pedir algo
  e fecha ESTADO/HANDOFF/DECISOES/lições na entrega.
- **Skill `figma-flex`** — cópia literal da fonte canônica. Router agnóstico de
  contorno de limite de capability quando a IA atual não consegue executar
  diretamente o que foi pedido.
- **Skill `registrar-licao`** — cópia do `plugin-megabrain/skills/registrar-licao/SKILL.md`
  (Kimi), exceto: o gatilho `/megabrain:licao` vira `/registrar-licao`; a menção a
  `~/.kimi-code/SYSTEM.md` vira "SYSTEM.md do plugin ou do agente"; o parágrafo
  de abertura declara que o hook pode não rodar (ver limite abaixo).
- **Hook SessionStart** (`scripts/260821_session-start.js`) — injeta o núcleo
  do protocolo (texto de `megabrain-core`) e o arquivo de lições mais recente da
  pasta conectada (`licoes-megabrain.md`, `METAPROTOCOLO-LICOES.md`, `LICOES.md`,
  `LESSONS.md`; até 2 níveis; escolha por mtime). Sem embeddings e sem arquivo
  global por usuário (a v1.0.0 assumia `~/.megabrain/licoes.md`, que não existe
  no projeto real — descartada).

## Limite verificado — o hook NÃO roda no Cowork cloud

Verificado em 260821 numa sessão Cowork cloud com o plugin v1.0.0 instalado na
conta: o hook criaria `~/.megabrain/licoes.md` na primeira execução e injetaria
"megabrain — ativo nesta sessão" no contexto. Nenhum dos dois aconteceu. As
skills do plugin, sim, carregam (aparecem como `megabrain:megabrain` e
`megabrain:registrar-licao`). Conclusão: no Cowork cloud, o que vale é a skill;
o hook vale onde hooks de plugin rodam (Claude Code CLI / Desktop). Por isso a
skill `megabrain` continua mandando ler as lições no Gate 0 — não depende do
hook.

## Como regenerar e empacotar (1 comando)

```
python bin/mb-build-plugin-claude.py
```

Copia as skills das fontes (com as edições declaradas acima aplicadas por
código, não à mão), valida JSON/frontmatter/`node --check`, roda o hook num
smoke test e grava `YYMMDD_megabrain-v<versão>.plugin` na raiz da central.
`--check` só confere se a pasta está igual às fontes (exit 1 se drift) — é o
que o gate de drift usa.

## Instalação no Cowork

1. Cowork → plugins → instalar a partir de arquivo → o `.plugin` gerado.
2. Desinstalar o plugin `megabrain` v1.0.0 anterior (e qualquer `metaprotocolo`).
3. Confirmar: `ListSkills` mostra `megabrain:megabrain` e
   `megabrain:registrar-licao` com a descrição sem `/metaprotocolo`.

## Origem

Construído numa sessão Claude Cowork em 260821 (v1.0.0 descartada; v1.1.0
entregue como `.plugin` na conversa e nunca encontrada no disco). Reconstruído
das fontes pelo Kimi em 260821 (v1.1.0, commit `a7cfc7a`, direto no repo-local).
Em 260821 (claude, v1.1.1): fonte movida pra central, build script, sanitização
(o commit `a7cfc7a` levou nome e caminho pessoal pro repo público — corrigido
daqui em diante; o histórico do git mantém), hook marcado com o limite acima.
