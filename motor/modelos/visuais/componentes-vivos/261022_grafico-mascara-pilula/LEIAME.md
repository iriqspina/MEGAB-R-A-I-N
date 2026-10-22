# GraficoPilula · v1.0.0 · 261022

Gráfico vivo dentro de uma **máscara invisível em formato de pílula** (sem fundo, sem borda; o desenho nunca sai da curva). Nasceu no Bubble, no rodapé da lateral, ao lado de Ajustes, para mostrar o uso de rede.

Pedido do <USUARIO> (22/10): "não tivesse num botão de pílula... tamanho proporcional... o gráfico dinâmico não saísse de uma máscara equivalente, porém invisível, do botão-pílula". Depois: "onda ficou muito boa" e "salve os outros desenvolvimentos como assets e materiais criados que podemos reutilizar estrutura e como inspiração".

## Estilos e status

| estilo | o que mostra | status |
|---|---|---|
| `onda` | linha suave do total (a+b), janela que cresce de 16 s até 60 s, degradê iridescente, ponto na cabeça com a cor da saúde | **aprovado pelo <USUARIO> e aplicado no Bubble** (`Bubble/app/bubble.js`, bloco "gráfico de rede no rodapé") |
| `espelho` | barras: b em cima, a embaixo, mesma escala (dá pra comparar envio e recebimento de relance) | inspiração, não aplicado |
| `liquido` | a pílula "enche" conforme (a+b)/teto, com o número dentro; cor = saúde | inspiração, não aplicado |

## Arquivos

- `grafico-mascara-pilula.js`: componente sem dependências (`GraficoPilula.montar(el, {tipo})` → `.amostra({a, b, saude, teto})`). A documentação de uso está no topo do arquivo.
- `demo.html` + `demo.png`: os 3 estilos com dados simulados, em tamanho real e ampliado (testado em 261022: 6 canvases pintados, sem erro).
- Prints e protótipo humano: `04_visuais/01_sim/componentes/261022_grafico-rede-pilula/`.
- Protótipo original com as 3 propostas, situações e decisões: `Bubble/00_PARA-VOCE/06_App-de-teste/261022_grafico-rede/261022_GRAFICO-REDE.html`.

## Reuso

1. Estrutura: qualquer série temporal pequena (CPU, fila, volume de áudio, mensagens/min) cabe no `onda`. O espelho serve para pares opostos (entra/sai, ganho/perda). O líquido serve para "quanto do limite já usei".
2. Tamanho: a proporção 84 × 30 imita a pílula do Bubble. Outros tamanhos funcionam, porque os traços escalam por `altura/30`.
3. Limites: as cores estão fixas no código (iridescente do Bubble e saúde verde/âmbar/vermelho) e são trocadas por `op.corUp`, `op.corDown` e `op.corTexto`. O texto do líquido usa `toLocaleString("pt-BR")`. Não está no catálogo do `mb_visual.py`, porque aquelas mecânicas são HTML estático gerado em Python e esta é viva (canvas + rAF).
4. Diferença da versão aplicada no Bubble: lá o código foi escrito direto no `bubble.js`, no estilo do arquivo, e lê `netStats.up + down`. Este arquivo é a extração genérica e não é importado pelo app.
