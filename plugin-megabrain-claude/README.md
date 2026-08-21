# plugin-megabrain-claude — plugin Cowork/Claude do megabrain (v1.1.0)

Plugin no formato Claude (`.claude-plugin/plugin.json` + `hooks/hooks.json` +
`skills/`), irmão do `plugin-megabrain/` (Kimi) que vive na central.

## O que faz

- **Hook SessionStart** (`scripts/260821_session-start.js`): injeta o núcleo
  do protocolo (texto de `megabrain-core`) e carrega o arquivo de lições mais
  recente da pasta conectada (`licoes-megabrain.md`, `METAPROTOCOLO-LICOES.md`,
  `LICOES.md`, `LESSONS.md`; até 2 níveis; escolha por mtime — "por recência",
  não por embeddings, que não existem no sandbox Cowork).
- **Skill `megabrain`**: cópia 1:1 de `skills/megabrain/SKILL.md` deste repo
  (v5.0), exceto a linha `description:` do frontmatter (removidos os gatilhos
  legados `/metaprotocolo` e `metaclaude`).
- **Skill `registrar-licao`**: cópia 1:1 de
  `plugin-megabrain/skills/registrar-licao/SKILL.md` da central, exceto 1 linha
  que citava `~/.kimi-code/SYSTEM.md` (generalizada para "SYSTEM.md do plugin
  ou do agente"). A outra menção a `SYSTEM.md` (item 5 de "Como isso costuma
  dar errado") já era genérica e ficou intacta.

## Origem e auditoria

Construído originalmente numa sessão Claude Cowork em 260821 (entregue como
`.plugin` na conversa; o arquivo baixado não foi encontrado nesta máquina).
Reconstruído nesta sessão Kimi (260821) a partir das fontes versionadas — as
duas skills são deterministicamente idênticas à especificação da sessão Cowork
(diff 1:1 contra as fontes, conferido no commit de introdução). O hook foi
reescrito seguindo a especificação da nota
`260821_pendencia-nome-metaprotocolo-residual.md`: núcleo megabrain-core +
lições por recência. Se o `.plugin` original reaparecer, auditar o hook dele
contra este.

Ajustes do núcleo injetado vs `megabrain-core` original (mínimos, de
perspectiva/roteamento): "compartilhado com o Claude" → "com o outro agente";
`/megabrain:licao` → skill `registrar-licao`; `/megabrain:rodar` → skill
`megabrain`.

## Instalação

Compactar esta pasta como `.zip`/`.plugin` e instalar no Claude (Cowork ou
Desktop com suporte a plugins). A pasta `.claude-plugin/` precisa ir junto.

## Limite declarado

Validado: JSON do manifest e dos hooks, sintaxe do script (`node --check`),
smoke test do hook com saída JSON no formato `hookSpecificOutput`. NÃO
validado dentro de uma sessão Claude de verdade — o primeiro uso real é o
teste final.
