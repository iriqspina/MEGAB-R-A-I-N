# Mapa do harness (cidade MegaBrain, animado e editável) · v1.1 · 261018

Fonte técnica para agentes. A peça para o <USUARIO> é o HTML gerado; ele não lê este arquivo.

## Peças

| Arquivo | Papel |
|---|---|
| `dados/harness-mapa.json` | FONTE editável: bairros, estações, linhas, cenários, legenda (≤ 7), ligações, notas, histórico |
| `motor/modelos/harness-mapa/mapa.css` | visual (tokens POP v1.2, claro/escuro, 1440 e 390 px) |
| `motor/modelos/harness-mapa/mapa.js` | núcleo sem DOM (aplicar/diff/medir/desenho, exportado no Node) + interface |
| `bin/mb-harness-mapa.py` | valida, fotografa (só leitura), embute tudo e grava a saída fixa |
| `motor/tests/test_mb_harness_mapa.py` | planta, remendos, paridade Python × JS, fotografia, CLI |
| `00_PARA-VOCE/261011_harnesses/261017_MAPA-DO-HARNESS.html` | SAÍDA FIXA. Nunca renomear: o rascunho do visor do app é preso ao caminho (fid = sha256 do caminho) |

## Comandos

```
python bin/mb-harness-mapa.py                      # valida, fotografa e gera a saída fixa
python bin/mb-harness-mapa.py --validar            # só valida (sai 2 com a lista de problemas)
python bin/mb-harness-mapa.py --sem-fotografia     # não lê banco nem arquivos vivos
python bin/mb-harness-mapa.py --aplicar-remendos respostas.json   # funde e gera de novo
python bin/mb-harness-mapa.py --aplicar-remendos x.json --sem-gerar
```

`--aplicar-remendos` aceita a lista pura, o pacote de “Exportar”, o `respostas.json` do app
(`respostas.mapa_harness`) ou o comentário inteiro. Antes de gravar: valida a planta atual,
aplica tudo ou nada, valida o resultado, copia a fonte para `.mb-backup/harness-mapa/` e
acrescenta uma linha em `historico` com o `lote`. O mapa usa `lotes_aplicados` para limpar do
rascunho o que já entrou na planta.

Editar a planta NÃO muda o harness. Depois de aplicar os remendos, a IA ainda precisa levar a
mudança para os arquivos reais citados em `arquivos` de cada estação (e marcar `verificado`
só com prova).

## Formato (resumo)

- `estacoes[]`: `id` (a-z0-9_), `nome` (1–3 palavras, ≤ 28 letras), `descricao` (≤ 20 palavras),
  `bairro`, `quem` (chave de `responsaveis`), `condicao`, `x`/`y` (mundo ~1380×800),
  `arquivos[]` (arquivo:linha), `verificado` (só com prova), `nota_prova`, `tecnico`, `rotulo`
  (`cima|baixo|esq|dir`), `tipo` (`estacao|placa|deposito`; placa e depósito não entram em linha).
- `linhas[]`: `estacoes` em ordem (≥ 2), `cor`, `gatilho`, `frequencia`, `esperas[]` (mão),
  `volta {de, para, max, lado}` (ajuste: volta para estação anterior), `curva_cedo[]` (curva logo
  na saída daquela estação). A ordem do array define as faixas paralelas nas baldeações.
- `cenarios[]`: `linha`, `pedido`, `resultado` (`aprovado|volta_1x|espera`).
- `bairros[]`: `faixa` (`topo|base`) para Regras e Armazém; `rotulo_lado` (`esq|dir`).

## Ajuste r1 da crítica de design (v1.1, 261018)

- Topo em 2 linhas: título + `subtitulo` (o que é o harness; `subtitulo_curto` no celular) e, na barra
  presa, Tocar/Passo/Reiniciar/velocidade + régua de paradas (clicável) + narração + Ver/Editar/Lista.
  Chips das linhas embaixo (são a legenda de cor). `narracao_inicial` é o texto de repouso.
- O mapa inteiro cabe na altura da tela: o JS mede o que vem antes do palco (`--mh-acima`) e a
  proporção do desenho (`--ar`); a largura máxima do palco sai disso (mínimo 960 px).
- Placas grandes “COMEÇA AQUI / CHEGA AQUI” nas pontas mais comuns das linhas; legenda dentro do
  palco (quem faz no canto da faixa de Regras; símbolos no canto do Armazém); `legenda` ≤ 7 itens.
- Estação: letra de quem faz dentro do anel (`responsaveis.*.sigla`; `curto` na legenda); `papel:
  "revisao"` vira losango; anel com casco (aparece no tema claro). Bairros neutros com pictograma
  (`BZ_ICON` no JS) e silhuetas de prédios a 6 % nos cantos livres. Cor saturada só nas linhas.
- `elevadores`: linha neutra até o Armazém (“lê no começo”, “grava no fim”); estação ausente é ignorada.
- Animação: rastro do trecho feito a 100 % e o resto da linha a 40 %; trem maior com halo; balão de até
  8 palavras colado no trem; o que está parado fica apagado durante o Tocar.
- “Mostrar o que está parado agora” é interruptor desligado por padrão; pílulas com palavra (`curto`
  da fotografia), perna até a estação e lugar escolhido por custo (rótulo, trilho, borda de quarteirão).
- Celular (≤ 760 px): barra de 1 linha (Tocar, Passo, seletor de linha, ⋯) + narração de até 2 linhas,
  presas no topo; Reiniciar, velocidade, Ver/Editar, tema, movimento e parados vão para o menu ⋯.
- Painel: mapa anda para a esquerda quando a estação fica embaixo dele; resumo em 3 linhas com ícone.
- Editar: aviso no topo do palco com “Entendi” (some em 6 s), “+” na cor da linha, ← Antes / Depois →,
  seletor começa vazio, Remover em vermelho separado, barra de edição presa abaixo da barra principal.
- Peso: o gerador embute CSS/JS sem recuo e sem comentários de linha inteira (`compactar`); a fonte
  aqui continua legível. Limite do HTML: 250 KB (o cursor sozinho pesa ~73 KB).

## Remendos (mesma semântica em `mapa.js:aplicarUm` e `mb-harness-mapa.py:aplicar_um`)

`mover`, `editar` (estacao: nome, descricao, quem, condicao, bairro, tecnico · linha: nome, cor,
gatilho, frequencia · bairro: nome, descricao, cor), `nova_estacao`, `remover_estacao` (recusa se
uma linha ficar com < 2), `nova_linha`, `remover_linha`, `ordem`, `incluir`, `nota`,
`remover_nota`. Qualquer mudança nova precisa entrar nos DOIS lados e no teste de paridade.

## Integração com o visor do app (medida na réplica, 261017)

- Sandbox `allow-scripts allow-forms`, CSP sem rede: tudo embutido; dados em `window.HARNESS`
  (com `<` escapado), nunca `<script type=application/json id>`.
- Rascunho: chave `mb-harness-mapa:v1` guarda só os remendos; gravação espaçada (1,2 s aqui +
  1,5 s no visor). Medida do espaço usa a mesma conta do servidor (`json.dumps` ASCII: acento = 6);
  aviso aos 80 %, compacta acima de 50 %, recusa gravar acima de 100 % (pede Exportar).
- Copiar só por `execCommand('copy')`; baixar é bloqueado; importar por `<input type=file>`.
- `confirm()` é ignorado no visor: remover sempre tem Desfazer (Ctrl+Z, 20 níveis).
- “Enviar mudanças para a IA” → `MegaBrainReport.saveFeedback({kind:'decisions', finalizado:true,
  respostas:{mapa_harness:{patches,...}}, resumo_texto})`; o <USUARIO> ainda clica “Salvar no projeto”.
- Cursor: estações com `data-cf-ancora="<linha>/<estacao>"`; no modo Editar, estações, trilhos e
  “+” ganham `data-cf-ignorar` (arrastar não abre o leque). Controles no topo; toast à esquerda.

## Fotografia (“Agora na cidade”)

Somente leitura: sessões de `apps/megabrain-dashboard/data/session-connections/*.json` (24 h),
banco `central.sqlite3` copiado por `mode=ro` + API de backup para pasta temporária fora do projeto
(jobs, events report_*, comments) e `dados/orcamento_ia.json`. Sempre datada, nunca “ao vivo”.
Fonte ausente vira aviso `NAO_MEDIDO`.

## Prova

`evidence/261017_cursor-harness/mapa/` (réplica do visor + QtWebEngine 6.11, prints Edge).

## Revisão GPT da ponte (261018)

- Régua no computador: um seletor com todas as paradas, alvo de 44 px; no celular os pontos são apenas indicação. Reiniciar, velocidade e preferências ficam no menu ⋯ também no computador.
- Narração reserva duas linhas estáveis. A pausa acompanha as palavras do texto exibido (3,5 palavras/s + 0,6 s, heurística de leitura), respeitando a velocidade escolhida.
- Começo/fim e orientação acompanham a linha selecionada; o celular usa cima→baixo. Pausar uma transição vertical congela o trem e retoma a mesma chegada.
- Editor usa orientação na própria barra, sem dica temporária sobre os trilhos. Provas e backup: evidence/261018_ponte-orquestradores/mapa-revisao-gpt/.
