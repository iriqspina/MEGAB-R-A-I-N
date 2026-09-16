# Widget Pendências — radar dos projetos MEGABRAIN

`/pendencias` na tela: pill recolhida com a contagem, card expandido com as
pendências por projeto. Subprojeto da família de widgets (Cotas IA, Agentes IA).

## Como funciona

- **Fonte da verdade:** `<CENTRAL>/dados/pendencias.json`, escrito SÓ pelo CLI
  `bin/mb-pendencias.py`. O widget apenas LÊ (poll 60 s + botão ↻).
- **Item automático:** o `scan` extrai do `ESTADO.md` de cada projeto o resumo
  (TL;DR) e o próximo passo ("Próximo passo:", "Gate seguinte:", "Pendente:").
  A linha "auto" aparece no card com a idade do arquivo; `ocultar-auto` esconde
  até o ESTADO.md mudar de conteúdo.
- **Item manual:** adicionado por conversa (`/pendencias`) ou CLI.
- **Pausar projeto:** some do widget, nada é apagado (`retomar` devolve).

## Instalar / abrir

Dê 2 cliques em `INSTALAR-E-ABRIR.cmd` (cria atalho na Área de Trabalho e abre).
Requisito: Python 3.10+ — reaproveita o venv do Cotas IA quando existe.

## CLI (o que qualquer IA usa)

```
python bin/mb-pendencias.py scan                  # varre a raiz gravada
python bin/mb-pendencias.py listar [--json] [--todos]
python bin/mb-pendencias.py add <projeto> "<titulo>" [--detalhe "..."]
python bin/mb-pendencias.py feito <projeto> <id|titulo>
python bin/mb-pendencias.py rm <projeto> <id|titulo>
python bin/mb-pendencias.py pausar <projeto>      # projeto parado some do widget
python bin/mb-pendencias.py retomar <projeto>
python bin/mb-pendencias.py ocultar-auto <projeto>  # esconde a linha auto
python bin/mb-pendencias.py raiz "<caminho>"      # outra pasta de projetos
python bin/mb-pendencias.py validar
```

## Interações do widget

- ▴ expande · ▾/Esc recolhe · duplo clique no título alterna pill/card.
- Duplo clique num item abre a pasta do projeto no Explorer.
- Arraste pelo cabeçalho; posição/estado persistem em `app/data/settings.json`.
- Rodapé: "pausados: N" clicável mostra/esconde os pausados.
- Item auto com 7+ dias fica âmbar (idade do ESTADO.md, não chute).

## Testes

`python -m unittest discover -s apps/pendencias-widget/tests` (core sem Qt).

## Pesquisa e decisões

`docs/260916_pesquisa-planejamento.md` (contrato, jornadas, riscos, critérios
de estado final e a segunda opinião da conta gpt2 em high).
