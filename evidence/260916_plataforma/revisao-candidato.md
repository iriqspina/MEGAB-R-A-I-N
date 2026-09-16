# Revisão independente do candidato — 260916

TL;DR: nenhum impeditivo factual permanece no escopo relido. O retorno direto
ao início foi implementado e a prova Qt em disco registra o fluxo completo.
As três correções apontadas nesta revisão foram confirmadas. Esta frente não
alterou código do candidato e não certifica integração universal entre clientes.

## Escopo

Somente `bin/mb_triagem.py`, `bin/mb_catalogo.py`,
`bin/mb_entregas_registro.py`, integrações em `bin/mb-contexto.py`,
`bin/mb-entrega.py`, `apps/megabrain-dashboard/dashboard.py`, bloco
`MB:PARA-VOCE` em `bin/mb-relatorio-vivo.py` e os três testes indicados pelo host.

Inspeção estática e reprodução em memória, sem abrir modelos, alterar
preferências, gerar catálogo ou gravar dados de teste no projeto. A reprodução
de `reload` extraiu somente essa função da árvore sintática e substituiu seus
consumidores por objetos simulados. A validação de tela pertence à frente do host.

## Achado inicial resolvido na última releitura

### P2 resolvido — Abrir entrega HTML deixava a entrada sem retorno direto

`LocalPage.acceptNavigationRequest` permite que um link HTML local navegue no
mesmo navegador interno. Na entrada, o único seletor passa a chamar “Visão
técnica”; não há botão de voltar ao catálogo. “Atualizar” chama `reload`, mas
`reload` retorna antes de `browser.load` se os dados do catálogo não mudaram,
mesmo quando a página atualmente exibida é a entrega.

Evidências:

- [Navegação local no mesmo navegador](<<MEGABRAIN_ROOT>/apps/megabrain-dashboard/dashboard.py:38>)
- [Botões da barra](<<MEGABRAIN_ROOT>/apps/megabrain-dashboard/dashboard.py:82>)
- [Retorno antecipado por fingerprint](<<MEGABRAIN_ROOT>/apps/megabrain-dashboard/dashboard.py:143>)

Reprodução: catálogo com dados inalterados, `self.inicio=True`, `last_html`
preenchido e navegador representando `entrega.html` após clique. A chamada de
`reload` terminou com **zero chamadas a `browser.load`** e zero regenerações.
Hoje o caminho indireto é alternar “Visão técnica” e depois “Início”.

Impacto: a entrada fixa deixa de estar imediatamente acessível depois do uso
principal, que é abrir uma entrega. O botão Atualizar não ajuda nesse cenário.

Correção mínima: botão explícito “Voltar ao início” que carregue a entrada
atual independentemente do fingerprint, ou separar atualização manual forçada
da atualização periódica. Preservar o comportamento do timer: ele não deve tirar
o usuário da entrega que está lendo. Verificar a sequência abrir entrega →
voltar ao início com dados inalterados, sem precisar alternar duas visões.

**Fechamento confirmado:** o botão dedicado “Início” chama `go_home`, define
`self.inicio=True`, invalida `last_html` e chama `reload(force=True)`.
O retorno antecipado por fingerprint agora é condicionado a `not force`.
A atualização periódica continua sem forçar a navegação.

Fontes relidas: [botão dedicado](<<MEGABRAIN_ROOT>/apps/megabrain-dashboard/dashboard.py:82>),
[go_home](<<MEGABRAIN_ROOT>/apps/megabrain-dashboard/dashboard.py:115>),
[reload](<<MEGABRAIN_ROOT>/apps/megabrain-dashboard/dashboard.py:142>).

Prova relida em disco: [ui-nativo.json](<<MEGABRAIN_ROOT>/evidence/260916_plataforma/ui-nativo.json>)
declara `pass: true` e seis verificações aprovadas: entrada no app, gravação da
preferência, encaminhamento da pasta ao sistema, abertura de entrega no app,
temporizador preservando a leitura e botão retornando ao início. O host produziu
essa prova com Qt real em modo offscreen e clique QTest; esta frente leu o
resultado e o trecho correspondente, sem repetir a execução.

## Achados corrigidos pelo host durante a revisão

### Contenção do destino de gravação

Primeira leitura: o catálogo validava os itens, mas construía diretamente
`root/00_PARA-VOCE/INICIO.html`; as preferências e o registro também montavam
`dados/...` sem resolver o destino. Uma junction para fora poderia escapar do
projeto na gravação.

Releitura: `coletar` e `gerar` usam `caminho`; `registrar` resolve seu registro
por `caminho`; preferências e observações usam `destino_local`, que resolve e
verifica `is_relative_to(root)`.

Fontes atuais: [catálogo](<<MEGABRAIN_ROOT>/bin/mb_catalogo.py:22>),
[saída do catálogo](<<MEGABRAIN_ROOT>/bin/mb_catalogo.py:96>),
[preferências](<<MEGABRAIN_ROOT>/bin/mb_triagem.py:75>),
[registro](<<MEGABRAIN_ROOT>/bin/mb_entregas_registro.py:10>).

Situação: corrigido no código relido. A última releitura incluiu
[test_mb_plataforma_destinos.py](<<MEGABRAIN_ROOT>/motor/tests/test_mb_plataforma_destinos.py:11>):
os testes criam junction real no Windows, conferem o destino resolvido, tentam
as gravações e verificam que a pasta externa continua vazia. O host informou
3/3 testes aprovados; esta frente inspecionou os casos sem repetir a execução.

### Revisões opcionais não chegavam à instrução do hook

Primeira leitura: `classificar` calculava `opcionais`, mas `instrucao` os omitia.
O controle visual mudava o rótulo, sem transmitir as ações opcionais à IA.

Releitura: `instrucao` inclui “Passos opcionais”. A execução em memória de
`classificar('crie um relatorio', ...)` confirmou lista vazia no modo enxuto e
três orientações no criterioso; as instruções já diferem além do nome do nível.

Fonte atual: [instrução de triagem](<<MEGABRAIN_ROOT>/bin/mb_triagem.py:99>).
Situação: corrigido na versão relida.

## Limites preservados no código inspecionado

- `autoriza_execucao` permanece falso. Sensibilidade altera somente as revisões
  opcionais; obrigações e piso de verificação não diminuem no modo enxuto.
- Itens descobertos no legado entram como `nao_verificado`; não recebem aprovação
  humana ou estado pronto por inferência.
- Registro corrompido falha antes de substituir o catálogo. `INICIO.html` sem o
  marcador próprio é preservado. A proteção adicional em
  `dados/catalogo-geracao.json` compara o hash da saída existente, preservando
  edição humana mesmo quando o marcador do gerador permanece. Guardas relidas em
  [mb_catalogo.py:95](<<MEGABRAIN_ROOT>/bin/mb_catalogo.py:95>)
  e caso de edição humana em
  [test_mb_catalogo.py:37](<<MEGABRAIN_ROOT>/motor/tests/test_mb_catalogo.py:37>).
- `pronto` sem prova vira `em_revisao`; hash diferente do arquivo principal
  também rebaixa o estado. O novo caso
  [test_current_proof_expires_on_edit](<<MEGABRAIN_ROOT>/motor/tests/test_mb_catalogo.py:41>)
  começa com hash válido e estado pronto, altera o arquivo e exige em_revisao.
- O teste de sensibilidade em
  [test_mb_triagem.py:36](<<MEGABRAIN_ROOT>/motor/tests/test_mb_triagem.py:36>)
  verifica que a segunda lente aparece na instrução criteriosa e não na enxuta.
- O bloco atual de `PARA VOCÊ`, inclusive vazio, suprime o histórico; ausência
  do bloco conserva compatibilidade com o formato legado.
- Não foi encontrada, nos arquivos indicados, uma garantia de que a integração
  esteja instalada e ativa em todos os clientes de IA. A revisão não concede
  essa certificação; o hook e a função pura são fronteiras diferentes.

## Parecer

Não permanece impeditivo factual nos trechos e provas solicitados para esta
última releitura. O fluxo entrada → entrega → entrada está sustentado pelo
código corrigido e pela prova Qt registrada; as proteções de destino, edição
humana, prova obsoleta e sensibilidade têm guardas e casos de teste pertinentes.

Este é um parecer de escopo: não certifica ativação em todos os clientes de IA,
aparência em todas as telas, integração universal nem aprovação de toda a suíte
do repositório. A prova Qt foi produzida pelo host e relida aqui; os testes de
junction foram inspecionados e seu resultado 3/3 foi informado pelo host, sem
nova execução nesta frente. Arquivos fora do escopo não foram reabertos.
