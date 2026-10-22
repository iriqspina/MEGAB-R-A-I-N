# Revisão independente n2 — contrato e skill opcional

TL;DR — Contrato alinhado ao pedido, com ressalvas verificáveis antes do aceite. A skill não induz agrupamento indevido de Salvar/Apagar, mas tem uma contraindicação ampla demais que contradiz parcialmente seu próprio exemplo. Esta revisão documental não aprova implementação nem conclui a ordem.

## 1. Escopo e método

Leitura de plano.json, pedido.json, brief-implementacao.md e motor/skills/agrupar-acoes/SKILL.md nesta ordem. Conferência adicional do glossário central, cuja linha 29 define retorno como aviso de relatório novo. AGENTS.md fornecido na sessão e início do arquivo local conferidos. Consultados estado/handoff centrais e diretório de travas; o HANDOFF não fica na raiz. Nenhum startup, filho, despacho, teste operacional ou mudança de configuração foi executado.

Critérios: fidelidade ao pedido literal; distinção entre espera/pausa e retomada; preservação de trabalho e independência dos controles. Os achados abaixo são lacunas do contrato, não defeitos comprovados do código em implementação por n1.

## 2. Achados e correções propostas

1. Alta prioridade — definir a unidade de trabalho permitida durante a espera. Plano linha 4 e brief linha 7 permitem terminar “trabalhos já iniciados”, mas bloqueiam novas execuções. Uma ordem já aberta pode conter etapas ainda não iniciadas; não está inequívoco se elas continuam em espera. Correção: declarar a unidade (ordem, nó ou processo), registrar quais unidades estavam iniciadas na transição e explicitar se etapas dependentes pertencem à conclusão permitida. Teste: ordem com etapa A em curso e B pendente; comparar B em espera e em pausa. Se ambas bloquearem exatamente os mesmos passos, documentar por que existem dois controles ou corrigir a distinção. Não decidir silenciosamente pelo usuário.

2. Alta prioridade — delimitar a exceção para esta ordem. Brief linha 5 exige bloquear despacho automático sem encerrar a ordem autorizada. Isso é compatível com o pedido, mas não deve virar exceção geral para toda ordem antiga, complemento futuro ou ação manual. Correção: limitar eventual exceção ao ID desta ordem e ao trabalho necessário para cumprir este pedido, mantendo o projeto em espera ao fim. Teste: outra ordem do mesmo projeto não começa; outro projeto não é pausado; chegada de relatório ou expiração de tempo não libera trabalho. A exceção não pode permitir que esta ordem ignore um novo comando humano de pausa.

3. Alta prioridade — tornar a retomada determinística. Brief linha 7 pede Retomar explícito, persistência e controle de conflitos, mas não diz se Retomar reativa automação previamente desligada nem o destino da fila. Correção: preservar a preferência anterior de automação, não ligar auto por padrão e definir se a fila é apenas liberada ou executada imediatamente. Revalidar cada item antes de executar; não repetir itens concluídos. Testes: auto inicialmente desligado continua desligado; pausa sobrevive a reinício; comando antigo de outra aba não desfaz pausa mais recente; um item em fila só executa uma vez após retomada autorizada.

4. Média prioridade — exigir verificação no instante do despacho e continuidade dos retornos. O brief já cobre caminhos manuais, complementos e persistência; falta explicitar a disputa entre pausa e disparo simultâneo. Correção: revalidar o estado imediatamente antes de iniciar a etapa, com a mesma proteção de concorrência usada na transição. Definir como tratar um processo já iniciado nesse limite, sem prometer interrupção retroativa. Testes: pausa concorrente a despacho; relatório de trabalho em curso recebido em espera e pausa; histórico, comentários e rascunhos preservados; falha ao salvar estado mostra erro e não mostra sucesso. Processo externo não integrado permanece limite declarado.

5. Média prioridade — ajustar a contraindicação da skill. Linha 21 manda separar quando “as consequências [...] forem diferentes”. Aguardar e Pausar têm consequências diferentes por definição, embora linhas 8 e 14 admitam agrupamento de estados relacionados. Correção curta: “Mantenha separado quando diferenças de consequência, permissão ou objeto tornarem a proximidade ambígua ou aumentarem o risco de acionamento errado; diferenças compreensíveis não impedem agrupamento por si só.” Manter integralmente a proibição de aproximar Apagar e Salvar apenas pelo objeto compartilhado.

## 3. Dois casos solicitados

1. Aguardar retorno e Pausar projeto — agrupamento visual é candidato coerente: mesmo projeto e intenção de controlar continuidade, com efeitos distintos. A skill exige nomes, foco e áreas de clique independentes, sobreposição decorativa, teste de toque/teclado e persistência. Não induz fusão funcional. Aprovação visual permanece pendente de captura e interação reais; a frase da linha 21 precisa do ajuste acima para não rejeitar automaticamente o próprio caso de origem. Texto explicativo deve dizer que retorno recebido não retoma execução.

2. Salvar e Apagar — manter separados. Compartilhar o arquivo afetado não compensa a diferença de intenção e risco de perda; a skill declara esse exemplo expressamente na linha 21. Não induz agrupamento indevido. Mesmo com opção de desfazer, proximidade não se justifica automaticamente. Conferência documental somente: nenhuma interface deste par foi testada.

## 4. Preservação e encaminhamento

O brief restringe corretamente arquivos, exige backups, preserva decisões e evidências anteriores, veda banco real nos testes e não autoriza encerrar processos externos. A skill é explicitamente opcional e não autoriza instalação em outros projetos. Não há motivo documental para ampliar escopo ou refazer o planejamento do bapp.

Parecer: alinhado com ressalvas; incorporar ou responder aos achados 1–5 antes do aceite final. n0 decide o contrato; n1 implementa e apresenta prova. Pendentes nesta revisão: código final, testes, build, capturas nas duas larguras, apresentação nativa e estado operacional efetivo de espera. Nada disso foi presumido a partir do plano.

## 5. Arquivos e verificação

Único arquivo criado por n2: .mb-ponte/261020-170554-b2c2be/nos/n2/resultado.md. Nenhuma alteração em código, skill, plano, pedido, brief, configuração, estado/handoff ou ordem-raiz. Resultado escrito em UTF-8 e relido para confirmar conteúdo. Revisão estática por confronto entre fontes; sem alegação de teste de execução.