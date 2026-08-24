# Catálogo visual do megabrain

**Antes de inventar um visual, procure aqui.** Escolher um id e preencher
os dados custa muito menos token do que escrever HTML e CSS do zero — e o
resultado já sai no tema do sistema, com contraste conferido e responsivo.

```python
import mb_visual as v
html = v.render("kpi-linha", {"itens": [...]})   # peça
css  = v.css()                                    # tokens + estilo
```

Formas prontas de dados: `modelos/visuais/exemplos.json` (copie e troque os
valores). Galeria renderizada: `00_painel/CATALOGO-VISUAL.html`
(`python bin/mb_visual.py --catalogo`).

Status aceitos em toda mecânica: `ok` ✓ · `ativo` ● · `espera` ○ · `trava` ✕.
O glifo é derivado pelo renderizador — não passe.

| id | quando usar | dados | custo |
|---|---|---|---|
| `barra-segmentos` | uma população repartida — 16 projetos por versão, tokens por fase, tarefas por estado | `titulo, total, segmentos[]{rotulo, n, status}` | ~3 linhas por segmento. Largura calculada pelo renderizador (n/total). |
| `fluxo-etapas` | uma sequência que tem estado — gates 0→7, pipeline de publicação, fases do Duplo Diamante | `titulo, legenda, etapas[]{n, titulo, det, status}` | ~15 linhas de dados; zero CSS novo |
| `kpi-linha` | 3 a 6 números que dão o retrato em 3 segundos — versão, commits, projetos, pendências | `itens[]{valor, rotulo, det, status}` | ~8 linhas de dados. A mecânica mais barata do catálogo. |
| `mapa-camadas` | arquitetura empilhada — onde mora o quê e o que desce pra onde. Ordem: de cima (fonte) pra baixo (consumo). | `titulo, legenda, camadas[]{nome, papel, itens[]{rotulo, det, status}}` | ~20 linhas. Substitui um parágrafo inteiro de "onde fica cada coisa". |
| `matriz` | comparar opções por critério — antes×depois, ferramenta A×B, o que cada camada cobre | `titulo, legenda, colunas[]{rotulo}, linhas[]{rotulo, celulas[]{v, status}}` | ~2 linhas por célula. Use no lugar de 3 parágrafos de comparação. |
| `semaforo` | lista de coisas que estão OK / esperando / travadas — saúde do sistema, checklist de saída | `titulo, itens[]{rotulo, estado, det}` | ~3 linhas por item. Use quando o leitor precisa varrer, não ler. |
| `timeline` | histórico datado — versões, decisões, sessões. Ordem: mais recente em cima. | `titulo, itens[]{data, titulo, det, status}` | ~4 linhas por item |
| `trilha-dupla` | mostrar onde o trabalho passa da máquina pra pessoa — e onde ele empaca esperando alguém | `titulo, legenda, raias[]{nome, papel, blocos[]{titulo, det, status}}` | a mecânica mais cara em dados (~25 linhas) e a que mais explica |

## Onde cada uma aparece na planta do relatório

| slot | mecânica |
|---|---|
| D2 | `kpi-linha` |
| D4 | `semaforo` |
| D5 | `barra-segmentos` |
| W1 | `fluxo-etapas` |
| W2 | `trilha-dupla` |
| W3 | `mapa-camadas` |
| W4 | `timeline` |
| — | `matriz` (sem slot fixo ainda) |

## Como adicionar uma mecânica

1. Copie um `.html` de `mecanicas/` — o cabeçalho `<!--@mb-visual -->` é obrigatório
   (`id`, `nome`, `quando`, `dados`, `custo`).
2. Só use variáveis de `tokens.css`. `#hex` solto numa mecânica é bug.
3. Adicione uma entrada em `exemplos.json` — sem exemplo, a galeria acusa.
4. Rode `python bin/mb_visual.py --catalogo` e confira no navegador.

Fonte de layout no Figma: arquivo **megabrain** (prancheta MECÂNICAS).
Desenhar lá e ajustar o `.html` conserta todo lugar onde a peça aparece.
