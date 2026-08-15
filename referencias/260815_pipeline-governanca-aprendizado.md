# Pipeline de governança e aprendizado entre projetos

Carregue esta referência quando um projeto operar com cliente, dinheiro, aprovações humanas, múltiplas IAs ou quando o usuário exigir que seus aprendizados retroalimentem o MEGABRAIN.

## 1. Princípio central

Automação prepara, mede e recomenda. A pessoa responsável decide, autoriza comunicações externas, aprova preço/escopo e responde pelo resultado. O objetivo é reduzir repetição sem terceirizar responsabilidade.

## 2. Papéis separados

| Papel | Responsabilidade | Não pode |
|---|---|---|
| Diretor humano | Decide, aprova, envia e assume compromisso. | Ser substituído por consenso de modelos. |
| Agente principal | Integra contexto, propõe plano e entrega resultado. | Esconder dúvida material ou inventar decisão humana. |
| Amarrador de Pontas | Detecta dúvidas, números velhos, prazos, dependências e decisões sem dono. | Transformar toda ambiguidade em pergunta ao usuário. |
| Contraditor | Ataca premissas, riscos e custo do erro; propõe teste. | Criticar sem saída ou decidir por maioria. |
| Teammate | Executa subproblema delimitado com rubrica. | Expandir o escopo ou enviar algo externamente. |
| Verificador | Confere fatos, cálculo, teste e rastreabilidade. | Aprovar o próprio trabalho sem evidência. |

## 3. Amarrador de Pontas

Roda antes de aprovação humana, envio externo, fechamento semanal e handoff. Lê estado, handoff, decisões, lições, tracker e fontes declaradas.

Saída mínima: ID, tema, pergunta, evidência, impacto, recomendação, dono, prazo e estado.

Regras:

- descobrir sozinho tudo que for leitura segura;
- mostrar ao usuário no máximo cinco perguntas prioritárias;
- priorizar caixa, cliente, privacidade, prazo e bloqueio real;
- agrupar perguntas próximas;
- não inventar preço, imposto, disponibilidade, gosto ou credencial;
- reapareceu três vezes: o Contraditor avalia falha do processo e propõe regra, checklist, template ou automação.

## 4. Contraditor

Uma rodada de crítica deve produzir: premissa atacada, evidência disponível, três objeções no máximo, impacto, teste barato e recomendação. Risco financeiro, legal, de segurança ou promessa sem prova pode bloquear. Preferência sem evidência não bloqueia.

O Contraditor pode convocar Teammates ou outros modelos, mas recebe uma tarefa delimitada. O agente principal integra e o diretor humano decide.

## 5. Teammates e modelos por custo

Use o recurso mais barato capaz de passar na rubrica:

0. script/busca determinística;
1. modelo local ou econômico para extração, classificação e rascunho;
2. modelo leve para varredura longa e alternativas;
3. modelo intermediário para implementação e síntese;
4. modelo forte para arquitetura, risco alto e auditoria crítica.

Escalar só depois de falha observada, ambiguidade relevante ou alto custo do erro. Registrar tarefa, nível, motivo, resultado, custo/tempo e se escalou. Não presumir preço ou disponibilidade permanente de fornecedor; recalibrar pela conta real.

## 6. Portões humanos e caixa

Projetos comerciais devem declarar portões antes de:

- contato ou pesquisa nominal invasiva;
- proposta, preço, desconto, escopo ou prazo;
- início sem pagamento/escrow financiado;
- apresentação ao cliente;
- entrega/publicação;
- uso externo de dado, ativo, credencial ou comunicação.

Aceite, contrato e escrow sem data de liberação não são caixa. Tracker comercial é atualizado antes de novo contato ou follow-up. IA prepara; humano revisa e envia. Nada de bot, scraping ou disparo automatizado sem regra específica e autorização.

## 7. Gate financeiro para serviços

Preço deve separar remuneração do trabalho, custo direto, reserva de retrabalho, taxa do canal, reserva fiscal/compliance, custo fixo alocado e lucro. “Margem” sem dizer o que foi descontado é inválida.

Antes da proposta:

1. definir remuneração interna do trabalho e capacidade faturável mensal;
2. ratear custo fixo por hora faturável ou outra base causal declarada;
3. somar horas, retrabalho, custo direto e fixo alocado para obter o custo completo;
4. calcular o piso depois de reserva fiscal, taxa do canal e margem desejada;
5. verificar condição de pagamento e data provável do caixa;
6. abaixo da margem-alvo, reduzir escopo, elevar preço ou recusar;
7. desconto, urgência e revisão extra exigem recálculo e alçada explícita.

Validar em dois níveis: cada ticket precisa ficar acima de seu piso completo e o portfólio mensal precisa pagar todos os fixos uma única vez. O rateio não substitui o teste do mês.

Rodar ao menos dois estresses antes de publicar preço: desconto comercial e estouro de horas. Se qualquer um derrubar a margem, registrar o ponto de parada e a ação corretiva na proposta.

Projetar receita anualizada contra o limite do regime tributário, somando todas as receitas do mesmo negócio, não apenas a nova oferta. Depois da entrega, registrar horas e margem reais. Recalibrar após três trabalhos comparáveis ou 30 dias.

## 8. Dinheiro e momentum

Projetos que também servem para recuperar ritmo produtivo devem ter dois placares:

- **econômico:** recebido, margem, horas, pipeline e cobertura do custo fixo;
- **momentum:** blocos focados concluídos, próximas ações encerradas, ciclos completos e ativos reutilizáveis validados.

Atividade sem comprador, prova, decisão ou ganho de capacidade não pode virar substituto confortável da venda/entrega. Cada projeto define um teto para trabalho indireto e uma próxima ação com verbo, dono e prazo.

## 9. Dogfooding com sanitização

Usar produtos próprios em trabalho real é permitido quando o cliente entende o processo e a segurança é proporcional ao risco. Registrar atrito, versão, aprovação, tempo e incidente no projeto correspondente. Só promover padrão sanitizado: sem nome, credencial, arquivo ou informação estratégica do cliente.

Incidente de acesso, privacidade, perda de dados ou indisponibilidade pausa novas entradas até triagem humana.

## 10. Promoção para o MEGABRAIN

Ao fechar sessão ou ciclo:

1. registrar a lição específica no projeto;
2. perguntar: seria útil num projeto completamente diferente?;
3. se sim, criar uma versão sanitizada na fonte central do MEGABRAIN;
4. apontar de onde veio, sem carregar dado do cliente;
5. três repetições transformam a lição em regra, skill, template ou script;
6. sincronizar/exportar conforme o protocolo central e registrar o que ainda não foi publicado.

Se o usuário disser explicitamente que uma classe de mecânica deve “sempre ir ao MEGABRAIN”, a promoção sanitizada ocorre no mesmo ciclo; não fica apenas como candidata em handoff.

## 11. Checklist mínimo de fechamento

- [ ] portões humanos respeitados;
- [ ] caixa separado de aceite/escrow;
- [ ] margem e horas reais registradas;
- [ ] cinco pontas prioritárias ou menos;
- [ ] Contraditor usado onde risco justificava;
- [ ] Teammates registrados pelo custo real;
- [ ] aprendizado sanitizado promovido ou justificado como específico;
- [ ] próxima ação com verbo, dono e prazo.
