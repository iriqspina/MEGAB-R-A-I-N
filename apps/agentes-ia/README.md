# Agentes IA — universo invisível (família Cotas IA)

Widget sem fundo que mostra os processos vivos do dono (ZCode, Claude, Codex)
como **bolinhas-universo** flutuando direto na área de trabalho: cada bolinha
brilha na cor da fase, diz o projeto e a etapa, e o resto do desktop continua
clicável (o mouse passa por fora das bolinhas). Sem abas, painel, névoa ou
moldura; o board embutido (modo Mapa/webview) foi removido em 260916.

## Uso

- Abrir: `INSTALAR-E-ABRIR.cmd` (ou `launch.vbs`, ou o atalho
  `01_acoes/13_ABRIR-BOARD-DE-AGENTES.cmd` na central). Fechar o widget
  **para o server** do board (porta 3001).
- Controles: hover (ou clique) no canto superior esquerdo revela a pill —
  botão amarelo **Visão geral** (câmera enquadra todas as bolinhas ativas,
  folga 40 px), ⟳ reexibir, menu de contexto (organizar em grade, sempre no
  topo, parar server, fechar).
- Bolinha: arrastar (posição persistente), duplo-clique colapsa em mini
  bolinha, botão direito foca/esconde/zerar, tooltip com a ação do momento;
  popups fantasma sobem com trechos de comando.
- Câmera: roda do mouse 0,5×–7× no cursor; "Visão geral" pode ir abaixo de
  0,5× para enquadrar 100% dos processos.
- Inativo some sozinho: concluído há ~8 s ou sem eventos por ~10 min; volta
  se a sessão retomar.
- Settings: `~/.agentes-ia/settings.json` (posições por sessão, topmost).

## Detalhes

- Fonte de dados: server do board (`localhost:3001`) via SSE — mesma ponte
  de hooks das fases 1–3 (ZCode/Claude/Codex).
- Requisito: venv do Cotas IA (`apps/ia-quota-widget/.venv`, PySide6).
- Entrega e prova da versão universo:
  `00_PARA-VOCE/260916_agentes-ia-universo/` (LEIA-ME + print real).
- Espelho fiel desta versão (fonte de runs V6, <20 KB por parte):
  `Marketeiro/pesquisa/260916_agentes-ia-widget-p1.py` + `-p2.py`.
