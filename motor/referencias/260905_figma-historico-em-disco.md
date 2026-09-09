# Histórico do Figma em disco, arquivo com boards únicos (260905)

**Decisão do <USUARIO>, 260905:** parar de acumular painel, board de comparação e frame de
versão dentro do Figma. O arquivo fica com **boards únicos** (um por superfície, sempre o
atual) e o histórico vira **snapshot no disco**. Uso declarado: **baixa frequência**.

## O padrão

Pasta `figma-historico/AAMMDD_<motivo>/` na raiz do projeto, com:

| Arquivo | Conteúdo | Responde |
|---|---|---|
| `<pagina>_<id>.png` | página inteira renderizada (`get_screenshot` no id da PÁGINA) | "como estava?" |
| `MAPA.json` | por página: total de nós; por board de topo: id, type, name, x, y, w, h, visible, descendentes, `hash` | "onde estava?" e "mudou?" |
| `NOTAS.md` (opcional) | o que mudou desde o snapshot anterior, em 5 linhas | contexto |

`hash` = djb2 sobre `id|type|x|y|w|h|visible|locked|name` de todos os descendentes do board,
ordenado por id. Hash igual = board intocado.

## Por que não dentro do Figma

Board de comparação dentro do arquivo pesa pra sempre, some quando alguém arrasta, e não
responde "mudou?" sem inspeção manual. O snapshot custou **2,1 MB e ~4 min** para 5 páginas /
4.469 nós no Portfolio (260905) e responde as três perguntas por leitura de arquivo.

**Limite honesto:** o snapshot **não restaura** nada. Ele prova o que existia e onde.
Desfazer é pelo histórico de versões do próprio Figma.

## Regras de comunicação no arquivo

- Um board por superfície, sempre o atual. Sem `v1`/`v2`/`cópia`/`antigo` no canvas.
- Pedido de alteração = grupo `Alteração - <assunto>`; quando entra no produto vira
  `FEITO - Alteração - <assunto> - AAMMDD` com visibilidade desligada. Nunca apagar.
- Estudo que não vai pro produto leva `NÃO IMPLEMENTAR` no nome.
- Antes de rodada que renomeie, mova ou apague em massa: tirar snapshot.

## Armadilha medida

`findAll` só existe em nó com filhos — um `RECTANGLE` solto no topo da página quebra o script
de leitura. Testar `'findAll' in c` antes de chamar.

## Primeiro exemplar

`Portfolio/figma-historico/` (LEIAME.md + `260905_pos-renomeacao/`),
com o script de leitura pronto para colar no `use_figma`.
