# megabrain-mod

O megabrain morando dentro do Claude Code (o Claude no terminal e na aba Code do app).

## Em 3 linhas

- **O que é:** como o display de uma mesa de som: uma faixa fixa acima do campo onde você digita e um painel (`/mb`) que mostram o estado do megabrain sem você abrir pasta nenhuma.
- **O que faz:** mostra se o projeto está travado, quantos arquivos o Claude mexeu e se ele atualizou ESTADO/HANDOFF; confere cada resposta do Claude (palavras banidas, TL;DR no topo); segura comandos perigosos e arquivos que não se editam.
- **O que NÃO faz:** não apaga nada, não altera arquivo seu (só **lê** ESTADO.md e HANDOFF.md), não manda nada pra internet, não guarda conversa. Fechou o Claude, ele some.

## Como ligar

1. Clique em `01_acoes\15_ABRIR-CLAUDE-COM-MOD.cmd`. Abre o Claude no terminal, já na central, com o mod ligado.
2. A faixa aparece acima do campo de digitar. Digite `/mb` pra abrir o painel.

No app (aba Code): carrega em toda sessão quando `CLAUDE_CODE_PLUGIN_DIRS` (bloco `env` de `<USER_HOME>\.claude\settings.json`) aponta pra esta pasta.

## Como alterar

Tudo que dá pra mudar está em **um arquivo só**: `AJUSTES.ts` (nesta pasta).

1. Abra no VS Code ou no Bloco de Notas.
2. Troque `true` por `false` pra desligar uma peça, ou mexa nas listas (cada item entre aspas, com vírgula no fim).
3. Salve. Com o Claude aberto pelo botão, o mod recarrega sozinho.

Também dá pra pedir: *"no megabrain-mod, desliga o TL;DR"* — o Claude edita o `AJUSTES.ts` por você.

`/mb-ajustes` mostra o caminho do arquivo e o que está ligado agora.

Se quebrar (faltou aspa ou vírgula): aparece uma linha cinza dizendo que o megabrain-mod não carregou. Peça *"conserta o AJUSTES.ts do megabrain-mod"*. Seu projeto não é afetado.

## As peças

| peça | o que você vê | liga/desliga em AJUSTES.ts |
|---|---|---|
| Faixa | `🧠 megabrain · projeto · trava livre · ✏️ 4 · bastão: falta HANDOFF · AUDITAR ✓` | `faixa` |
| Bússola | embaixo da faixa: `🧭 começou: "…"` e `↳ agora (pedido 3): "…"` (8 palavras cada; texto inteiro no `/mb`) | `bussola` |
| Sessões | na faixa: `🗂 14 sessões · 4 agora`; `/sessoes` (ou botão "sessões") lista Claude no app e no terminal, Codex 1, Codex 2 e ZCode com título, projeto e há quanto tempo mexeu. Só lê o disco (`coletor/mb_sessoes.py`) | `sessoes`, `sessoesJanelaHoras`, `sessoesAtualizarSegundos`, `python` |
| Painel `/mb` | estado vigente, TL;DR, trava, PARA VOCÊ e os gates desta sessão | sempre ligado |
| Vigia de slop | aviso na tela quando o Claude usa palavra banida + bilhete escondido pra ele corrigir | `vigiaSlop`, `avisarOClaude`, `palavrasBanidas` |
| TL;DR no topo | aviso quando resposta longa não abre com TL;DR | `exigirTldr`, `tldrAPartirDeLinhas` |
| Guarda de comandos | `git push`, `git commit`, `rm -r`... pedem sua autorização | `guardaComandos`, `comandosVigiados` |
| Arquivos protegidos | recusa editar `.env`, cópia gerada (`_github/export`...) e `.cmd` por `edit_block` | `protegerArquivos`, `arquivosSecretos`, `pastasGeradas` |
| Lembretes | avisa o Claude: `.cmd` precisa CRLF; arquivo novo em `00_PARA-VOCE` precisa `AAMMDD_` | `lembrarCmd`, `exigirDataNoNome`, `pastasComData` |

## Limites (o que ele não enxerga)

- A guarda no modo `'perguntar'` usa a caixa de autorização do próprio Claude. No modo sem permissões (bypass), o Claude pode aprovar sozinho. Pra trava de verdade: `guardaComandos: 'bloquear'`.
- Só conta arquivos mexidos pelas ferramentas de escrita do Claude e do Desktop Commander. Arquivo gerado por script Python não entra na conta.
- O gate VERIFICAR não é medido (número recalculado, arquivo aberto, link testado continuam com o Claude).

## O que tem nesta pasta

| arquivo | o que é | precisa mexer? |
|---|---|---|
| `AJUSTES.ts` | os botões e listas | sim, é o seu |
| `hooks/regras.ts` | as regras (o que é slop, que comando é perigoso) | não |
| `hooks/register.tsx` | liga cada peça ao momento certo do Claude | não |
| `types/index.d.ts` | o que o mod guarda durante a sessão | não |
| `tests/` | rede de segurança: `claude plugin test "motor\mods\megabrain-mod"` | não |
| `.claude-plugin/plugin.json` | nome e versão do mod | não |

Criado em 261006 (v0.1.0, Claude Code 2.1.292). v0.2.0 em 261009: bússola (1º pedido e pedido atual), Claude Code 2.1.293. v0.3.0 em 261009: sessões de IA do PC.
