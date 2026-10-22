# Revis?o final independente n3 ? corre??es necess?rias

TL;DR ? N?o aprovo o aceite integral. A interface agrupada, a persist?ncia e os bloqueios b?sicos t?m prova, mas a espera diverge do contrato de n0, existe janela reproduzida entre pausa e lan?amento e falta estado persistente fora do di?logo. Nenhuma implementa??o foi editada; a ordem n?o foi conclu?da.

## 1. Escopo e base

Li TAREFA.md, pedido.json, plano.json, RESPOSTA-REVISAO-N0.md, resultados n2/n1, AGENTS.md, estado/handoff/decis?es centrais e a skill corrigida. Aguardei a publica??o de resultado.md de n1 antes deste parecer. N?o iniciei startup, filhos, modelos, sess?o de produ??o ou mudan?a de configura??o. A instru??o espec?fica de somente leitura e sa?da ?nica prevaleceu sobre rotinas gen?ricas que escreveriam outros arquivos.

Comparei fontes com evidence/261020_cursor-pausa/backup por diff delimitado, n?o com o Git inteiro. Conferi manifesto, c?digo, testes e provas apontadas por n1. A pesquisa r?pida no registro de mem?ria n?o foi usada como prova deste parecer. ESTADO/HANDOFF n?o est?o na raiz: consultei memoria/estado. A ?rea .mb-lock existe; nenhuma trava foi adquirida ou alterada nesta revis?o.

## 2. Achados verific?veis

### 2.1 Alta ? espera impede concluir etapas de ordem j? iniciada

Arquivos: apps/megabrain-dashboard/central_bridge.py:552 e :790; apps/megabrain-dashboard/tests/test_central_project_control.py:52. Contrato: RESPOSTA-REVISAO-N0.md, item 1.

As duas verifica??es chamam check_path sem informar elegibilidade da ordem. Assim, aguardando bloqueia todos os novos n?s, inclusive os necess?rios para terminar o pedido congelado de uma ordem cuja execu??o j? come?ou. O teste final foi alterado para exigir esse bloqueio; passar esse teste n?o prova o contrato aprovado. O resultado n1 assume explicitamente um contrato diferente, permitindo apenas etapas internas de outro executor.

Reprodu??o executada em pasta/banco tempor?rios: criar ordem sint?tica; marcar n0 como rodando com inicio preenchido, sem executar processo; gravar aguardando; chamar despachar com lan?ador falso. Resultado: ValueError ?Projeto aguardando. Retomada expl?cita necess?ria; nenhum processo foi encerrado.? Nenhum filho/processo real foi lan?ado.

Corre??o m?nima: identificar ordens realmente iniciadas na transi??o e autorizar exclusivamente suas etapas necess?rias em aguardando. Ordem apenas criada, ordem conclu?da/reaberta e complemento que amplia escopo continuam bloqueados. Pausado deve vetar tamb?m essas etapas eleg?veis. N?o basta repor etapa=True indiscriminadamente: isso aceitaria ordem criada sem execu??o. Adicionar teste A iniciada/B criada e testes de conclus?o/complemento. Atualizar textos humanos para o comportamento efetivamente aprovado.

### 2.2 Alta ? pausa confirmada pode ser atravessada antes de Popen

Arquivos: apps/megabrain-dashboard/central_bridge.py:622 e :643; apps/megabrain-dashboard/central_project_control.py:15. Tamb?m h? checagem isolada anterior ao despacho manual e ? chamada de modelo em central_workflows.py:203.

A leitura do estado e o in?cio do processo n?o compartilham exclus?o com save(). Depois de _verificar_no, ainda ocorrem prepara??o de ambiente/comando e abertura do log. Outro comando pode salvar pausado e receber sucesso antes de o supervisor executar Popen.

Reprodu??o determin?stica executada: banco tempor?rio ativo; substituir argv por fun??o que grava pausado e devolve comando fict?cio; substituir Popen por mock que registra a chamada e lan?a OSError REVIEW_NO_PROCESS. Resultado observado: modo=pausado, Popen_called=true, resultado do supervisor=falhou. O erro foi injetado para impedir qualquer processo; numa execu??o normal o lan?amento seria tentado depois da pausa confirmada. Isso n?o ? interrup??o retroativa de processo j? iniciado.

Corre??o m?nima: serializar transi??o e autoriza??o efetiva de lan?amento por projeto com mecanismo compartilhado pelos processos envolvidos, definindo o ponto de in?cio. Revalidar sob essa prote??o imediatamente antes do lan?amento e registrar o estado iniciado nesse limite; tratar falha sem sucesso aparente. Acrescentar teste concorrente determin?stico. A ressalva de n1 sobre controle cooperativo ? correta, mas n?o elimina esta lacuna do contrato; n?o prometer atomicidade atual.

### 2.3 M?dia ? estado desaparece quando o di?logo fecha

Arquivo: motor/modelos/interacoes/261010_cursor-ferramentas/cursor-ferramentas.js:424, :428, :430 e :577. Integra??o: apps/megabrain-dashboard/web/src/CursorTools.tsx:64.

O ?nico estado atual do projeto ? renderizado em [data-state] dentro de .cf-project-control. close() remove esse elemento. O chip persistente continua mostrando ferramenta de edi??o, e o indicador ?ponte desligada? do relat?rio representa auto, n?o aguardando/pausado. N?o h? apresenta??o persistente do estado carregado fora do di?logo. A prova de ?persist?ncia? reabre o di?logo; prova grava??o, n?o visibilidade cont?nua.

Reprodu??o pelo c?digo e capturas fornecidas: escolher aguardando, fechar o di?logo e observar o chip/relat?rio. report-1440.png e report-390.png n?o mostram indicador din?mico de aguardando/pausado. A se??o explicativa est?tica n?o substitui o estado real. O contrato n0 exige estado persistente e sa?da acess?vel fora do gesto.

Corre??o m?nima: indicador permanente do projeto e estado, com acesso por teclado a Retomar, atualizado ap?s PUT e nova consulta. Preservar nome/identidade do projeto ao abrir pelo chip. Testar ap?s fechar, recarregar e alternar projetos. N?o confundir auto=false com aguardando.

## 3. O que foi verificado e pode ser aceito no recorte

1. Executei novamente os 7 testes de test_central_project_control.py na vers?o final: todos passaram. Usam banco/pastas tempor?rios e lan?adores substitutos. Cobrem conflito de revis?o, persist?ncia, isolamento por pid, pausa nas entradas, bloqueio de timer/manual/complementos, conclus?es recebidas durante pausa e modo inv?lido sem grava??o. N?o significam teste com fornecedor real.
2. Executei caso adicional: auto inicialmente false, pausa e retomada expl?cita; auto permaneceu false. Executei mais quatro ticks ap?s a retomada da fila sint?tica; continuou exatamente um lan?amento registrado. Isso comprova este caso sequencial, n?o exclus?o concorrente universal.
3. Reproduzi os achados 2.1 e 2.2 sem lan?ar processos nem gravar dados reais. Popen foi mockado. N?o alterei arquivos de teste.
4. Li os logs de n1: recorte 67 passed + 4 subtests; frontend 43; gateway 24; build conclu?do. A su?te ampla registra 392 passed + 202 subtests e 1 failed. A prova baseline tamb?m registra a falha de coment?rio nativo; n?o atribuo essa falha a esta mudan?a nem declaro su?te inteira aprovada. Esses totais s?o evid?ncia de n1 lida, n?o reexecu??o minha.
5. Inspecionei cursor-1440.png, cursor-390.png, report-1440.png, report-390.png e app-native-final.png. Os bot?es t?m r?tulos distintos, ?reas separadas e agrupamento decorativo; o di?logo cabe nas duas larguras. O separador '?' anterior foi corrigido para '?'; acentos do controle est?o ?ntegros nas capturas.
6. Conferi probe.mjs, ui-results.json e isolated-touch-confirmed.json: transporte do relat?rio, conflito expl?cito, tr?s modos, reabertura e toque em viewport estreito t?m prova sint?tica. O roteiro abre o menu via JavaScript, for?a foco e usa Enter para entrar; Retomar ? acionado por mouse/toque. Portanto n?o certifica o percurso completo de retomada somente por teclado, setas/Tab ou dispositivo f?sico, apesar da formula??o ampla de n1. O c?digo oferece bot?es nativos e tratamento de Tab, mas falta prova desse percurso completo.
7. Fonte can?nica do cursor, c?pia p?blica e c?pia dist s?o textualmente iguais; o conte?do can?nico tamb?m aparece integralmente no HTML embutido. O retorno de erro do controle n?o usa sucesso falso: a Promise rejeita e o di?logo exibe N?o salvo; o conflito est? registrado na prova. Limito essa conclus?o ao transporte/controle conferido.
8. Skill agrupar-acoes corrigida: opcional, mant?m proibi??o de aproximar Salvar/Apagar por objeto comum e passa a distinguir diferen?a compreens?vel de ambiguidade. Nenhuma nova revis?o integral da skill foi necess?ria.

## 4. Integridade e limites de prova

O manifesto cont?m 46 entradas. Na minha confer?ncia, 45 hashes atuais coincidiam; central_dispatch.py divergia: esperado cc58703f016e803cfeb60c5e54eadbd97de07e329a421e073e0ae60e6419dc35; observado ccb393b36af32acfd98d9e972f10160d429af1520e99d24163b0a0da328b127b. A data desse arquivo era posterior ? publica??o do resultado n1 (17:25:04 contra 17:24:45, hora local observada). H? trabalho concorrente: n?o atribuo a diverg?ncia ao worker nem restauro backup. Antes do aceite, reconciliar autoria/diff e refazer prova/hash apenas do trecho afetado. O check_path permanece presente na vers?o lida.

native-proof.json registra modo aguardando, auto=false, assets iguais e recibo positivo. A captura nativa realmente mostra outro relat?rio; concordo com a ressalva de n1: apresenta??o recebida n?o certifica o planejamento em primeiro plano nem intera??o real com este controle. isolated-touch-confirmed.json registra 12 grava??es na c?pia, nenhuma fuga detectada, documentos/coment?rios/hist?rico reais sem altera??es e um evento real no intervalo; n?o chamar o banco inteiro de inalterado.

Gateway atualizado/testado em disco, sem publica??o: controle remoto/Pixel f?sico permanece n?o comprovado. N?o ampliar alcance para processos externos n?o cooperantes ou m?dulos antigos j? carregados. Nenhuma prova aqui demonstra suspens?o de processo em curso.

## 5. Encaminhamento e arquivo produzido

Parecer: CORRE??ES NECESS?RIAS antes do aceite integral. Resolver 2.1?2.3; conferir o arquivo concorrente e completar a prova de retomada por teclado. As provas aprovadas acima podem ser reaproveitadas quando os arquivos relevantes continuarem iguais. Fechamento e decis?o de integra??o permanecem com n0. N?o retomei o projeto nem a ponte autom?tica.

?nica sa?da persistente desta revis?o: .mb-ponte/261020-170554-b2c2be/nos/n3/resultado.md. Nenhuma edi??o de implementa??o, evid?ncia hist?rica, estado/handoff, skill ou Git. Os dados sint?ticos dos testes foram tempor?rios; a li??o operacional fica contida neste resultado para respeitar a sa?da ?nica: teste verde s? aprova o contrato que ele efetivamente testa.
