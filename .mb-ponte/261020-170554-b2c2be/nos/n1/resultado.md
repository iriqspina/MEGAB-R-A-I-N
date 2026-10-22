# Resultado do worker n1 - cursor e espera por projeto

## Entrega
Implementacao local executada e testada. Nao concluida a ordem-raiz. Revisao independente e integracao final pertencem ao n0.

Estado operacional confirmado no app real: projeto MEGABRAIN em `aguardando`, revision 1, e ponte `auto=false` (revision 5 na configuracao inicial). A ordem autorizada continuou nas sessoes existentes. Nao encerrei processos de trabalhadores nem outros projetos.

## Contrato implementado
- GET/PUT `/api/projects/{pid}/control`, documento SQLite `project-control:<pid>`, modo ativo/aguardando/pausado, revision obrigatoria e conflito 409.
- Aguardar: recebe conclusoes em curso; barra novas ordens, novos nos/CLIs, pedidos da mesa, despacho manual e reabertura por complemento. Etapas internas de um executor ja iniciado podem concluir.
- Pausar: alem disso, verifica a barreira antes da proxima chamada de modelo no executor cooperante. Nao mata a chamada em andamento. Etapa interrompida preserva artefatos; novo pedido explicito e necessario para sua continuacao.
- Retomar: acao explicita no controle; nenhuma chegada de relatorio ou temporizador altera esse estado. Nao liga `auto` automaticamente; a preferencia anterior e preservada.
- Recebimento de comentarios e reconciliacao de conclusoes permanecem ativos. Complementos pendentes nao disparam retomada enquanto bloqueado.
- Cursor: item Controle do projeto abre duas bolinhas agrupadas com contornos sobrepostos, hitboxes separadas, nome real do projeto, estado, Retomar e Fechar. Mouse, Enter/setas/Tab e toque em viewport mobile testados. Erro/conflito nao confirma sucesso.
- Mesma funcao nos relatorios via ponte autenticada de mensagens, com fonte/origem/token/hash e projeto do ReportFrame. Fonte canonica do cursor, copia publica e inline do relatorio sincronizadas.

## Verificacao
1. `final-targeted-tests.txt`: 67 testes Python passaram, 4 subtests, incluindo ponte, conclusoes, fila, workflows, controle e isolamento. Recorte novo: 7 testes de controle.
2. `python-tests.txt`: suite ampla, 392 passaram + 202 subtests; 1 falhou. `baseline-tests.txt` reproduz a mesma falha com central_server.py, central_reports.py e fonte do cursor anteriores carregados em memoria: teste nativo de comentarios compara nota sem `attachment_details: []` com nota normalizada que ja inclui esse campo. Nao corrigi esse contrato antigo nem declarei suite inteira verde.
3. `frontend-tests.txt`: 43 testes JavaScript passaram. `gateway-tests.txt`: 24 passaram, incluindo contrato das duas rotas novas.
4. `build.txt`: TypeScript e build Vite passaram; aviso de pacote JS maior que 500 kB permanece.
5. `ui-results.json` + `isolated-touch-confirmed.json`: 10 registros confirmados em 1440 e 390 px, tres estados, persistencia ao reabrir, hitboxes, mensagem de conflito e ida/volta pelo relatorio. Desktop usa mouse/teclado e mobile usa eventos de toque. Nenhuma gravacao da copia vazou para o banco real. O app real gerou 1 evento durante a ultima prova; documentos, comentarios e historico reais nao mudaram nesse intervalo. Prova anterior `isolated-keyboard.json` tambem concluiu sem alteracao alguma no banco real.
6. Capturas inspecionadas: `cursor-1440.png`, `cursor-390.png`, `report-1440.png`, `report-390.png`. A captura mobile do relatorio representa o painel estreito real com rolagem, nao a pagina inteira.
7. `native-proof.json`: servidor/app nativo carregado, hashes de assets servidos iguais a web/dist, modo aguardando e auto=false. Recibos nativos `0c10cf15a1014dcdb6823f40f159ef49` e `f70ec96a36254f0c9552b66469b17c71` confirmam apresentacao ok:true da mesma entrada. `/api/report-audit` foi consultado e salvo em `report-audit.json`; primeira tentativa teve timeout de 10 s, repeticao com 55 s concluiu.

## Apresentacao e limites reais
Entrada preservada e atualizada no topo: `<MEGABRAIN_ROOT>/00_PARA-VOCE/261020_bapp-planejamento/PLANEJAMENTO-BAPP.html`. Historico e decisoes existentes mantidos. Ilustracao rotulada e explicacao curta, detalhes recolhidos.

A rota mb-abrir-entrega foi executada duas vezes e retornou recibos nativos positivos. A captura QScreen da janela nativa (`app-native-final.png`) mostrou a posicao de leitura de outro relatorio, portanto NAO certifica o planejamento em primeiro plano. A prova visual do planejamento e dos controles esta na instancia isolada. Nao alterei o layout do usuario para forcar outra captura.

O script de reinicio recusou PID nao identificado e nao matou nada. A janela estava sem listener no instante da verificacao; abertura pela rota oficial e reforco do lancador nativo via WMI fizeram o app responder. PID real conferido: 79140. Nao alego reinicio de um processo que nao foi encerrado por mim.

O gateway remoto foi atualizado e testado SOMENTE em disco; nao houve publicacao. O Pixel fora de casa depende de publicar essa allowlist pela frente autorizada; nao afirmo funcionamento remoto/fisico deste controle. Processos externos nao cooperantes e modulos antigos ja carregados nao passam a obedecer so porque a fonte mudou.

A barreira e cooperativa, checada nas entradas e antes dos lancamentos. Nao equivale a suspensao do sistema operacional nem interrupcao atomica de uma chamada que ja atravessou a checagem.

## Arquivos e reversao
Lista exata e hashes: `evidence/261020_cursor-pausa/manifesto-arquivos.json`. Diff contra backups: `alteracoes.diff`. Backups das fontes editadas em `backup/`; fonte do cursor permite regenerar copia publica/dist. Arquivos novos principais: central_project_control.py e test_central_project_control.py. Nao editar estado/handoff globais, skills nem git.

Arquivos alterados/gerados nesta entrega:
- `motor\modelos\interacoes\261010_cursor-ferramentas\cursor-ferramentas.js`
- `apps\megabrain-dashboard\260910_LICOES.md`
- `apps\megabrain-dashboard\central_bridge.py`
- `apps\megabrain-dashboard\central_dispatch.py`
- `apps\megabrain-dashboard\central_jobs.py`
- `apps\megabrain-dashboard\central_reports.py`
- `apps\megabrain-dashboard\central_server.py`
- `apps\megabrain-dashboard\central_workflows.py`
- `apps\megabrain-dashboard\remote\gateway.contract.test.mjs`
- `apps\megabrain-dashboard\remote\gateway.mjs`
- `apps\megabrain-dashboard\scripts\isolated_server.py`
- `apps\megabrain-dashboard\tests\test_isolated_server.py`
- `apps\megabrain-dashboard\web\src\CursorTools.tsx`
- `apps\megabrain-dashboard\web\src\ReportFrame.tsx`
- `00_PARA-VOCE\261020_bapp-planejamento\PLANEJAMENTO-BAPP.html`
- `apps/megabrain-dashboard/central_project_control.py`
- `apps/megabrain-dashboard/tests/test_central_project_control.py`
- `apps/megabrain-dashboard/web/public/cursor-ferramentas-v1.2.js`
- `apps\megabrain-dashboard\web\dist\cursor-ferramentas-v1.2.js`
- `apps\megabrain-dashboard\web\dist\index.html`
- `apps\megabrain-dashboard\web\dist\manifest.webmanifest`
- `apps\megabrain-dashboard\web\dist\assets\index-Cp5jIj0B.css`
- `apps\megabrain-dashboard\web\dist\assets\index-DdpkO9_h.js`
- `apps\megabrain-dashboard\web\dist\assets\megabrain-cerebro-rosa-Bd6cr9Vd.png`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_agentes.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_atividade.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_backup.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_celular.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_comentar.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_compartilhar.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_cotas.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_decisoes.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_desenhar.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_historico.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_inicio.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_mesa.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_organizar.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_pedido.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_processos.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_projetos.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_referencias.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_relatorios.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_retornos.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_sessoes.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_tema.svg`
- `apps\megabrain-dashboard\web\dist\tutorial\261014_voz.svg`

## Para o n0
- Conferir diff/provas e fazer a revisao independente; nao abrir automaticamente nova CLI enquanto o projeto aguarda. A implementacao nao tem excecao escondida para revisores desta ordem.
- Fechamento da ordem-raiz, skill opcional e registros globais continuam com n0. Nenhuma conclusao de ordem-raiz foi enviada.
- Manter declaradas a falha preexistente da suite, a ausencia de prova de primeiro plano nativo e a nao publicacao do gateway.
- Licao tecnica registrada no arquivo existente `apps/megabrain-dashboard/260910_LICOES.md`: auto=false nao cobre todos os despachos; leitura SQLite precisa fechar a conexao explicitamente no Windows.
