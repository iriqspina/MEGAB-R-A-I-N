# Ícones dos relatórios vivos · v1 · 261011

Pedido do <USUARIO> (nota 3, relatório do Portfólio, 11/10/2026): "utilizaria ícones e uma forma padronizada de
comunicação… ir guardando e usando coisas que já temos geradas. Se possível gera como svg os ícones".

- `icones.svg` — fonte única: sprite com 31 `<symbol id="i-…">`, grade 24, traço 1.75, pontas redondas,
  cor por `currentColor`. Exceção: `i-s` é o S do logo HS (preenchido, mesmo path do site e da reunião do Marcelinho).
- Uso: colar o sprite uma vez no `<body>` (oculto) e chamar `<svg class="ic"><use href="#i-nome"/></svg>`.
  Funciona em arquivo único, sem rede.
- `demo.html` — vitrine com o nome de cada ícone (gerada por `gerar_demo.py`).
- Primeiro consumidor: `Portfolio/evidence/261011_alinhamento-v2/build_report_v2.py` (relatório 261010_DECISOES.html).

Nomes: tema, site, email, curriculo, caderno, status, historico, em-uso, aberto, pausa, camadas (abrir no
Figma), abrir, pasta, copiar, imagem, comparar, etiqueta (vocabulário), microfone, cursor, check, alerta,
cadeado, relogio, despacho, lupa, grafico, pessoas, lapis, seta, vinculo, s.
Regra: ícone novo entra aqui com o mesmo traço antes de ser usado num relatório; não usar emoji no lugar.
