# Auditoria independente — arquitetura e UX humana/IA

Data: 2026-09-16. Agente: `codex-auditoria-arquitetura-260916`.

TL;DR: sete inconsistências verificáveis no estado anterior à implementação da
plataforma. A correção delegada a este agente foi somente a classificação de
saúde de cota em `resolve_route_v2`; os demais achados foram entregues ao host.

## Escopo e limites

- Inspeção inicialmente somente leitura; a execução V6 existente
  `260916_175608_306d11cb` foi preservada. Nenhuma nova run, chamada de modelo,
  consulta externa de cota ou operação Git foi realizada.
- Os números e as linhas dos achados abaixo se referem à inspeção inicial. O host
  trabalha simultaneamente nos demais arquivos; consultar os backups do baseline
  para comparar com esse estado anterior.
- Não houve auditoria visual de tela renderizada nesta frente. Código e HTML
  demonstram os comportamentos descritos, sem certificar fidelidade visual.
- Evidência-base: [baseline.json](<<MEGABRAIN_ROOT>/evidence/260916_plataforma/baseline.json>).

## 1. P1 — Pendência humana concluída reaparece no painel

`secao_para_voce()` usa `re.search` e captura a primeira seção PARA VOCÊ do
HANDOFF. Ela ainda pede aprovação da paleta clara e autorização de commit,
embora o próprio HANDOFF já registre aprovação, commit e publicação. A função
foi reproduzida isoladamente em memória e retornou os dois pedidos antigos.

Evidências: `bin/mb-relatorio-vivo.py:290-309`,
`memoria/estado/HANDOFF.md:40-47` versus `55-60`,
`00_painel/RELATORIO.html:427`.
[Parser anterior](<<MEGABRAIN_ROOT>/evidence/260916_plataforma/backup/bin/mb-relatorio-vivo.py:290>) ·
[HANDOFF anterior](<<MEGABRAIN_ROOT>/evidence/260916_plataforma/backup/memoria/estado/HANDOFF.md:40>).

Impacto humano: repete uma decisão já tomada. Impacto IA: pode reabrir trabalho
encerrado e gerar tarefas falsas. Recomendação: bloco vigente identificado
explicitamente, separado do histórico. Trade-off: atualizar o produtor do
HANDOFF; trocar simplesmente primeira por última ocorrência não resolve um
arquivo com registros tanto prependidos quanto anexados.

## 2. P1 — Consulta de cota com erro recebe selo de saudável

Antes da correção, `resolve_route_v2()` considerava medida qualquer resposta cujo
status não fosse `NAO_MEDIDO`. O adaptador também retorna `auth_required`,
`error`, `rate_limited` e `unavailable`. Esses quatro casos caíam na razão
`auto: cotas medidas saudáveis; perfil normal`. Todos foram reproduzidos em
memória, com consultas e gravação substituídas, e depois por testes isolados.

Evidências: `apps/automations/automations.py:465-476` no estado anterior;
`apps/ia-quota-widget/providers.py:8` define os status.
[Código anterior](<<MEGABRAIN_ROOT>/evidence/260916_plataforma/backup/apps/automations/automations.py:465>) ·
[Contrato do adaptador](<<MEGABRAIN_ROOT>/apps/ia-quota-widget/providers.py:8>).

Impacto humano: confiança sem medição. Impacto IA: rota justificada por evidência
inexistente. Recomendação aplicada: só afirmar saúde quando consulta, data e
todas as janelas pertinentes sustentarem isso; preservar os perfis explícitos
com alerta. Trade-off: dados incompletos ficam como não confirmados, sem bloquear
o trabalho nem mudar permissões. Detalhes e testes ao fim deste laudo.

## 3. P1 — Contexto de subprojeto é substituído pelo da central

Dentro da raiz de projetos, `achar_projeto()` retornava o primeiro nível antes
de procurar o marcador mais próximo. O caminho real
`<MEGABRAIN_ROOT>\pets` retornou a central, embora existam
`pets/ESTADO.md` e `pets/MEGABRAIN`. Reproduzido isoladamente em memória.

Evidências: `bin/mb-contexto.py:67-81`.
[Resolvedor anterior](<<MEGABRAIN_ROOT>/evidence/260916_plataforma/backup/bin/mb-contexto.py:67>) ·
[Estado do Pets](<<MEGABRAIN_ROOT>/pets/ESTADO.md:1>).

Impacto humano: briefing repetido ou decisões do projeto errado. Impacto IA:
META e alinhamento inadequados para a tarefa. Recomendação: marcador mais
próximo primeiro; contexto central como herança explícita. Trade-off: definir
marcadores suficientes para não transformar exemplos em subprojetos. Correção
reservada ao host, sem edição por esta frente.

## 4. P2 — Substituição atômica não impede perda de atualização concorrente

Motor e widget leem `dados/orcamento_ia.json`, alteram uma chave e substituem o
arquivo inteiro. A leitura e a gravação não compartilham trava entre processos.
Se ambos lerem a mesma versão, a segunda gravação pode apagar a atualização do
primeiro. `os.replace` impede arquivo pela metade, mas não esse conflito.

Evidências: `apps/automations/automations.py:171-179` e `45-51`;
`apps/ia-quota-widget/widget_app/budget_status.py:21-39`.
[Escrita do motor](<<MEGABRAIN_ROOT>/apps/automations/automations.py:171>) ·
[Escrita do widget](<<MEGABRAIN_ROOT>/apps/ia-quota-widget/widget_app/budget_status.py:21>).

Impacto humano: dados podem retroceder ou desaparecer. Impacto IA: registro
compartilhado perde confiabilidade. Recomendação: trava abrangendo leitura e
gravação ou um arquivo por provedor. Trade-off: espera curta mantendo o formato
atual versus adaptação dos consumidores. Condição de corrida demonstrada pelo
código; nenhuma perda no arquivo real foi afirmada. Não corrigido nesta rodada,
por limite explícito do escopo.

## 5. P2 — Triagem tem instruções concorrentes e controles desconectados

O hook mandava retrabalhar e confirmar intenções em TODO prompt, enquanto a skill
isenta conversa e correção simples. O corte de relevância era fixo em `0.55` e a
primeira mensagem aceitava lições abaixo dele. `roles.sensitivity` governa apenas
o ramo `auto` da escolha de provedor; os dois papéis leves atuais usam
`spark_preferido`, portanto essa configuração não controla esses papéis nem a
triagem dos prompts.

Evidências anteriores: `bin/mb-contexto.py:121-130`, `43`, `188`;
`motor/skills/megabrain/SKILL.md:49-51`;
`apps/automations/automations.py:369-386`;
`apps/automations/config/automations.json:53-56`.
[Hook anterior](<<MEGABRAIN_ROOT>/evidence/260916_plataforma/backup/bin/mb-contexto.py:121>) ·
[Configuração do motor](<<MEGABRAIN_ROOT>/apps/automations/config/automations.json:53>).

Impacto humano: confirmação demais e um controle de sensibilidade com significado
inesperado. Impacto IA: precisa arbitrar instruções conflitantes. Recomendação:
triagem central retorna categoria, sinais, gatilhos e razão; controles separados
para relevância, intervenção e economia. Trade-off: mais configuração explícita,
mas significado verificável. Sensibilidade não concede autorização nem altera
permissões ou exigência de prova.

## 6. P2 — Organizador só cria arquivos soltos datados

`mb-entrega.py` rejeitava nomes com diretório e gravava diretamente em
`00_PARA-VOCE`, sem categoria fixa ou entrada estável. O baseline registra pastas
datadas misturadas com pastas técnicas de execuções e arquivos soltos.

Evidências anteriores: `bin/mb-entrega.py:13-21`;
`evidence/260916_plataforma/baseline.json:37-86`.
[Organizador anterior](<<MEGABRAIN_ROOT>/evidence/260916_plataforma/backup/bin/mb-entrega.py:13>) ·
[Inventário anterior](<<MEGABRAIN_ROOT>/evidence/260916_plataforma/baseline.json:37>).

Impacto humano: depende de lembrar data ou nome técnico. Impacto IA: falta contrato
de categoria e arquivo principal. Recomendação: catálogo fixo sobre os arquivos
existentes, com título, categoria e entrada principal. Trade-off: catálogo precisa
ser regenerado, mas preservar destinos inicialmente evita links quebrados e
migração destrutiva.

## 7. P2 — Caminhos de leitura têm menos ações que comandos

Em PRA VOCÊ AGORA, o botão copiar só era criado para comandos `.cmd`, `.py`,
`.ps1`, `.bat` ou `python`. O caminho completo de um `.html` ficava como texto;
o único botão abria o HANDOFF. Na aba de documentos havia links, mas caminhos
relativos e nenhuma cópia do caminho absoluto.

Evidências anteriores: `bin/mb-relatorio-vivo.py:1281-1296`, `1461-1464`;
`00_painel/RELATORIO.html:427`.
[Gerador anterior](<<MEGABRAIN_ROOT>/evidence/260916_plataforma/backup/bin/mb-relatorio-vivo.py:1281>).

Impacto humano: seleção manual ou navegação intermediária para chegar ao material.
Impacto IA: comandos são copiáveis, mas artefatos de decisão ficam difíceis de
localizar. Recomendação: componente comum com título, abrir, copiar caminho
absoluto e indicação de existência. Trade-off: abertura varia por navegador;
cópia deve permanecer disponível quando a abertura não for suportada.

## Correção delimitada aplicada e comprovada

Arquivos escritos por esta frente:

1. [automations.py](<<MEGABRAIN_ROOT>/apps/automations/automations.py:454>),
   somente o corpo de `resolve_route_v2`.
2. [test_route_health_260916.py](<<MEGABRAIN_ROOT>/apps/automations/tests/test_route_health_260916.py:1>).
3. Este laudo e a cópia anterior autorizada em
   [backup/apps/automations/automations.py](<<MEGABRAIN_ROOT>/evidence/260916_plataforma/backup/apps/automations/automations.py>).

Comportamento corrigido:

- Erro de consulta nunca recebe classificação saudável.
- A data `fetched_at` precisa existir, ter fuso e estar entre agora e 300 segundos
  atrás. Esse prazo reutiliza a validade do cache já existente em `Quotas.snapshot`;
  não introduz consulta extra nem inventa data onde falta.
- Todas as janelas pertinentes ao modelo precisam estar presentes no detalhamento
  de ritmo, com dados consistentes e prazo de renovação futuro. Janelas específicas
  de outro modelo Claude são ignoradas, seguindo o recorte já usado em `Engine.call`.
- Redução conservadora para `micro` continua quando existe sinal de desacelerar ou
  pausar. Se o sinal é incompleto, a razão informa que saúde não foi confirmada.
- Perfil explícito e papéis escolhidos são preservados com alerta. Rota persistida
  continua sendo retornada intacta, sem nova consulta, preservando retomadas.
- Não foram modificados permissões, orçamento compartilhado, adaptadores ou
  configuração de modelos.

### Antes e depois

Comando novo executado antes da alteração:
`python -X utf8 -B -m unittest discover -s apps/automations/tests -p test_route_health_260916.py -v`

Resultado: `Ran 12 tests`; `FAILED (failures=25)`. O total de falhas inclui
subcasos; não significa 25 métodos de teste. A saída demonstrou erro de consulta,
data ausente/vencida, janela incompleta e razão incorreta para perfil explícito.

Depois da alteração, mesmo comando: `Ran 12 tests in 0.226s` — `OK`.

Recorte existente executado sem editar testes anteriores:
`python -X utf8 -B -m unittest discover -s apps/automations/tests -p test_engine.py -q`

Resultado: `Ran 55 tests in 1.055s` — `OK`.

Os testes são locais, sem rede nem modelos. Cobrem erros de leitura, duas janelas
com uma desconhecida, ausência de janelas/ritmo, timestamps inválidos/sem fuso,
janela vencida, preservação de perfil explícito, sinal legado de desaceleração,
detalhe degradado sob resumo saudável, falha parcial entre provedores e retomada.

### Integridade e reversão

SHA-256 anterior:
`927e97f13a58c952ce222db72f670923db9b9dff33953eede6c056622896c185`

SHA-256 após a correção:
`e4b47e81111728c6f14236b6419629157421ff6287f7a0477b1ab3d9fc35315b`

Comparação binária confirmou prefixo e sufixo fora de `resolve_route_v2` idênticos
ao backup. Foram preservados inclusive os terminadores mistos: 546 CRLF antes e
depois. O delta de 3.889 bytes está restrito à função.

Reversão segura: tomar novamente a trava, conferir o SHA-256 atual e restaurar
somente o trecho `def resolve_route_v2` até antes de `def role_v2` a partir do backup.
Restaurar o arquivo inteiro só é adequado se o hash ainda corresponder ao pós-fix
acima; caso contrário preservam-se as alterações posteriores de outros agentes.
O teste novo documenta o defeito e pode ser mantido para impedir sua reintrodução.

Limitação intencional: rotas antigas persistidas não são reescritas, inclusive
quando contêm uma razão antiga incorreta. Esse comportamento preserva a execução
e a retomada; correção retroativa de histórico não foi autorizada nesta frente.
