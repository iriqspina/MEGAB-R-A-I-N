---
name: agrupar-acoes
description: Avalia se ações relacionadas devem compartilhar um agrupamento visual compacto sem perder significado, acesso ou segurança. Ferramenta opcional para menus, cursores e controles com ações próximas; use quando a relação entre ações puder melhorar compreensão ou economizar espaço, não em todo design.
---

# Agrupar ações relacionadas

Ferramenta de análise do MegaBrain, não regra obrigatória de layout. A referência de <USUARIO> é o par **Aguardar retorno / Pausar projeto** no cursor do bapp: bolinhas parcialmente mescladas comunicam proximidade. Isso não prova que a solução serve para outros pares nem autoriza redesenhar uma peça aprovada.

## Analisar antes de desenhar

1. Declare a fase do Duplo Diamante. Na análise, descreva o problema observável numa frase: quais controles ocupam espaço, quem os confunde e em qual tarefa. Ausência de teste de uso deve aparecer como hipótese.
2. Para cada ação, registre objeto afetado, resultado, duração, reversão, condição de uso e risco de clique errado. Consulte o glossário do projeto para termos humanos. Aparência parecida ou verbo semelhante não bastam para agrupar.
3. Compare as relações: mesmo objeto, mesma intenção ampla, estados alternativos, sequência ou ação principal com alternativa. Preserve diferenças que mudem a decisão. Se a pessoa precisa ler instruções para distinguir as ações, resolva nome e consequência antes da forma.
4. Compare uma opção separada e uma opção agrupada dentro da mesma grade, tipografia, cores e escala. Use a referência concreta do caso. Para ações próximas, considere contorno compartilhado, conexão ou sobreposição apenas decorativa; escolha pelo problema, não pela estética do exemplo.

## Decidir sem fundir funções

Agrupe quando a relação ajudar a prever onde encontrar as ações e a redução de espaço não prejudicar leitura, alvo de toque ou foco. Registre a contrapartida: proximidade pode aumentar ambiguidade e acionamento acidental.

Mantenha separado quando diferenças de consequência, permissão ou objeto tornarem a proximidade ambígua ou aumentarem o risco de acionamento errado. Diferenças compreensíveis não impedem agrupamento por si só. Uma ação destrutiva não deve ser confundida com uma reversível. Não aproxime Apagar de Salvar só porque ambos afetam um arquivo. Não use uma cor, hover ou ícone como única distinção.

Botões visualmente conectados continuam com nomes acessíveis, focos e áreas de clique independentes. Sobreposição decorativa não deve capturar o clique do vizinho. Teclado, toque, zoom e rótulos longos precisam continuar utilizáveis. Não reduza a área acionável apenas para caber mais controles.

## Verificar no destino

1. Apresente antes → proposta, com prova real ou diagrama rotulado ilustração, na entrada existente da tarefa. Diga se é hipótese, protótipo ou comportamento implementado.
2. Confira se cada clique aciona só a função escolhida, se o teclado alcança ambas, se foco e estado são visíveis e se o layout estreito preserva nomes e alvos.
3. Verifique o efeito real e persistência; ícone ou mensagem de sucesso não comprova alteração. Em controles de execução, teste bloqueio e retomada explícita, além da aparência.
4. Registre critério, resultado observado e limite. Aprovação de <USUARIO> para um caso não é regra universal. Se a pessoa errar a escolha ou a leitura, revise nomes/separação e preserve a versão anterior.

## Caso de origem

Pedido literal: `memoria/cerebro/raw/261020_cursor-pausa-design.md` na raiz central. No glossário vigente, retorno é aviso de relatório novo. No caso bapp, aguardar pode permitir concluir trabalho já iniciado; pausar bloqueia novas etapas. O contrato real do produto precisa dizer o que acontece com trabalho em curso e como retomar. A skill não cria nem presume esse comportamento.

Saída curta: problema observado; relação entre ações; comparação visual; escolha e contrapartida; prova e pendências. Não criar relatório concorrente, mudar a identidade visual ou instalar esta ferramenta em outros projetos sem escopo.
