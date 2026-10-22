# O que cada fixture prova (aplicador: rode sem mostrar o esperado ao testado)

- visao.png → a IA lê "K7Q-42" e cita o quadrado vermelho à direita, sem receber essas palavras no pedido. Passa = visão funcional nesta sessão.
- crlf-3linhas.txt → trocar só a linha 2 mantém 3 quebras CRLF e diff de exatamente 1 linha. Passa = edição de arquivo sem dano colateral.
- reparo_buggy.py + teste_do_reparo.py → o teste FALHA no código buggy; o reparo correto devolve [] e o teste passa. Passa = reparo com prova nos dois lados.
- gate-visual.html → auditoria/olho aponta ≥5 defeitos plantados: h3 sem h2, emoji em h2 sem imagem, .seta quebrando o grid de 2 colunas, figcaption fora de figure, img inexistente, classe .mono morta, onclick sem função. Passa = gate visual funciona.
Custo de cada: <1 min, sem chamada paga além da própria execução.
2 passes seguidos (antierro.py retestar) = limite superado; histórico preservado.
