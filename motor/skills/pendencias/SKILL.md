---
name: pendencias
description: Radar de pendências dos projetos MEGABRAIN — listar, adicionar, concluir, remover, pausar e retomar pendências por conversa, alimentando o widget de desktop "Pendências". Use quando o usuário digitar /pendencias, pedir "o que tá pendente", "quais são as pendências", "adiciona uma pendência no projeto X", "pausa o projeto Y", "retoma o projeto Y", "marca como feito", ou quiser configurar a pasta de projetos do widget.
---

# pendencias — radar de pendências dos projetos

Registro único: `<MEGABRAIN_CENTRAL>/dados/pendencias.json` (na central do
usuário, ex.: `<MEGABRAIN_ROOT>\dados\pendencias.json`).
Escrito **somente** pelo CLI `bin/mb-pendencias.py` — nunca edite o JSON na
mão. O widget de desktop apenas lê esse arquivo (poll 60 s).

## Mapa de intenção → comando

Todo comando assume `python <MEGABRAIN_CENTRAL>/bin/mb-pendencias.py …`
(resolva `<MEGABRAIN_CENTRAL>` via `bin/mb_utils.achar()` ou a variável
`MEGABRAIN_CENTRAL`; em caso de dúvida, procure a pasta com `bin/` +
`VERSAO.txt` + `MEGABRAIN.md`).

| O usuário pede (exemplos) | Comando |
|---|---|
| "o que tá pendente?" / "meus projetos" | `listar` |
| lista em formato para outra IA processar | `listar --json` |
| incluir projetos pausados | `listar --todos` |
| "adiciona pendência no Marketeiro: X" | `add Marketeiro "X" --detalhe "opcional"` |
| "feito!" / "concluído" | `feito <projeto> <id ou parte do título>` |
| "tira essa pendência" | `rm <projeto> <id ou parte do título>` |
| "pausa o Pets" (projeto parado) | `pausar Pets` |
| "retoma o Pets" | `retomar Pets` |
| "esconde essa linha automática" | `ocultar-auto <projeto>` (volta quando o ESTADO.md mudar) |
| "varre de novo os projetos" | `scan` |
| "aponta pra outra pasta de projetos" | `raiz "S:\caminho"` + `scan` |

## Modelo de dados (o que o usuário precisa saber)

1. **Item auto** (por projeto): o `scan` extrai do `ESTADO.md` o próximo passo
   real ("Próximo passo:", "Gate seguinte:", "Pendente:"). A idade mostrada é
   a do arquivo — não é chute.
2. **Item manual**: o que for adicionado por conversa; viva até `feito`/`rm`.
3. **Projeto pausado**: `pausar` esconde do widget e preserva tudo; é o
   "colocar e tirar" para projeto parado. `retomar` devolve.
4. Feito/removido ficam no registro com data (histórico), não somem do JSON.

## Regras da skill

1. Projeto ambíguo no pedido ("portfolio")? O CLI aceita prefixo único; se
   casar mais de um, ele lista as opções — mostre-as e pergunte qual.
2. Ao **fechar um trabalho** num projeto (Gate 6 do megabrain), sugerir
   atualizar as pendências dele (`feito` do que concluiu; `add` do próximo
   passo deixado no HANDOFF). Nunca deixar o radar mentindo.
3. `scan` é barato e idempotente: preserve itens manuais e pausas — pode rodar
   sempre que terminar um `add`/`feito` numa sessão nova.
4. Não inventar pendência que não está no `listar`: se o usuário cita algo
   novo, é `add`, não afirmação.
5. Erro do CLI = reportar o texto do erro; não tentar editar o JSON.
6. Resposta curto: o `listar` já devolve formatado — cole com o caminho do
   registro no fim.

## Widget (produto na tela)

- Instalar/abrir: `apps/pendencias-widget/INSTALAR-E-ABRIR.cmd` (atalho +
  abertura; venv PySide6 reaproveitado do Cotas IA).
- ▴ expande, Esc recolhe, duplo clique no título alterna pill/card, duplo
  clique em item abre a pasta do projeto, rodapé "pausados: N" alterna
  visibilidade dos pausados.
- Pesquisa de planejamento e contrato: `apps/pendencias-widget/docs/
  260916_pesquisa-planejamento.md` e `apps/pendencias-widget/README.md`.

## Armadilhas conhecidas

- Rodar `scan` sem `raiz` gravada → o CLI pede `--raiz`; grave com `raiz`.
- Projetos são subpastas DIRETAS da raiz com `ESTADO.md` ou `MEGABRAIN/`;
  pastas comuns (sem os dois) ficam de fora de propósito.
- "TRAVADO_POR: livre" NÃO é pausa; só "PAUSADO"/"não retomar" sugerem pausa.
- Dois widgets abertos: o singleton barra o segundo ("já está em execução").
