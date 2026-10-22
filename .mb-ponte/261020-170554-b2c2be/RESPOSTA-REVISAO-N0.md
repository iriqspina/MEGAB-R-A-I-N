# Resposta n0 à revisão n2

Contrato conservador, interpretação do coordenador a conferir contra o comportamento final:

1. A unidade de espera é a ordem que já tinha execução iniciada no momento da transição. Seus nós necessários para entregar o pedido congelado podem terminar; ordens novas e retomadas após conclusão ficam bloqueadas. Complemento novo não concede ampliação automática de escopo. Pausa bloqueia também o início de novos nós dessas ordens, deixando processos já iniciados salvarem/terminarem. Nenhuma opção mata processos. Testar A ativo/B pendente e explicar a distinção no controle.
2. Esta ordem b2c2be já foi iniciada antes da espera; implementar o próprio pedido não é autorização geral de novas tarefas. Pausa humana posterior prevalece, inclusive para esta ordem. Não criar bypass permanente por ID. Não declarar bloqueio de processos externos não cooperantes.
3. Retomar é ação explícita: libera controle e preserva configuração auto existente; se auto estava desligado, continua desligado. A fila preservada é revalidada pelo mecanismo normal e recibos/identidade evitam duplicação. Não ligar auto implicitamente. Nenhum evento de retorno ou relógio retoma.
4. Exibir estado persistente e saída acessível fora do gesto de segurar. Definir alcance do projeto; erro/conflito não confirma sucesso. Provar hitboxes, teclado, duas larguras e estado persistente.
5. Skill corrigida: diferenças compreensíveis não impedem agrupamento; o critério é ambiguidade/risco. Salvar/Apagar permanece contraexemplo. Validação de formato será repetida após a alteração.

A revisão n2 é de contrato, não prova código. Revisão final independente deverá conferir estes critérios no resultado implementado.
