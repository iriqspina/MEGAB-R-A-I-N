# Contrato tecnico do ledger GLM de relatorios

Esta e documentacao entre agentes. O usuario recebe a entrada visual da tarefa
no aplicativo MegaBrain, nunca este arquivo como relatorio.

## Limite da garantia

`bin/mb_relatorios_glm.py` e `bin/mb-relatorios-glm.py` nao despacham modelos,
nao modificam o HTML, nao executam os comandos informados e nao observam imagens.
Verificam arquivos reais, hashes, dimensoes/pixels PNG, identidade declarada,
separacao de sessoes, criterios e cadeia de revisao. A observacao deve ser
realizada pelo Codex/Claude/humano que assina a inspecao. Nenhum JSON local
constitui assinatura criptografica ou prova independente da honestidade de
quem o preenche. Nao preencher observacao a partir de existencia de arquivo.

Aprender aqui significa preservar exemplares e correcoes verificadas e usa-los
como contexto nas proximas producoes; nao altera pesos do GLM e nao promete
ausencia de erros futuros. Sessao nova recebe brief, exemplar e achados reais.

## Arquivos e autoria

1. Relatorio final: HTML estavel dentro de `PROJETO/00_PARA-VOCE/`.
2. Manifesto unico: `PROJETO/evidence/TAREFA/manifest.json`.
3. Evidencia de producao: `result.json` real do wrapper
   `apps/megabrain-dashboard/model_clients.py`, preservado por ciclo.
4. Fragmentos, capturas, revisoes e logs: area tecnica do projeto.
5. Indice: `.automations/relatorios-glm/index.json`, schema `1`, `project`
   absoluto e `reports: {caminho_relativo_html: caminho_relativo_manifesto}`.
   Nao apagar associacoes para escapar do gate. Manifesto associado ausente
   bloqueia. Indice ausente significa nao medido, nunca conformidade.

O resultado normal exige `vendor="glm"`, `status="completed"`, `exit_code=0`,
`session_id` real nao vazio, `actual_model="GLM-5.3"`,
`effort_requested="max"`, `effort_verified=true` e `model_io_metadata` nao
vazio. Cada linha precisa de `model.modelId="GLM-5.3"`, `body_effort="max"`
e `provider_effort="max"`. Flash, modelo apenas solicitado, catalogo local
sem requisicao comprovada e falha de ferramenta nao passam.

Sem `--fragment`, o HTML deve ser a saida textual literal do produtor, com
apenas normalizacao de quebras CRLF/LF, espaco externo e remocao de um unico
par de fences HTML. Com `--fragment`, o arquivo fonte precisa ser exatamente
essa saida, e o fragmento inteiro deve ocorrer uma unica vez no HTML final.
`mechanical_integration` registra fonte/hash, resultado/hash, destino/hash e
metodo `compose-pop-cursor-history`. Permite montar POP, cursor e historico;
nao permite reescrever o fragmento substantivo. A revisao confere que o
fragmento esteja visivel e que os acrescimos nao introduzam outra narrativa.

## CLI

Executar da central; caminhos relativos nos argumentos sao relativos a
`--project`, nao ao cwd. Todos os arquivos de evidencia precisam estar dentro
do projeto. Nao usar links simbolicos, junctions, hardlinks ou `..` nos
argumentos. Recursos locais de render sao descobertos transitivamente
(HTML/CSS/SVG: src, poster, data, srcset, stylesheet, CSS url/import).
Usar `--asset` para dependencias adicionais, como recursos carregados por JS.
Fontes e imagens remotas de render bloqueiam a entrega ate congeladas localmente.

```powershell
python bin/mb-relatorios-glm.py --project "<RAIZ_DO_PROJETO>" --manifest evidence/TAREFA/manifest.json init --report 00_PARA-VOCE/TAREFA/RELATORIO.html --production evidence/TAREFA/producao-1/result.json --fragment evidence/TAREFA/producao-1/fragment.html
python bin/mb-relatorios-glm.py --project "<RAIZ_DO_PROJETO>" --manifest evidence/TAREFA/manifest.json status
python bin/mb-relatorios-glm.py --project "<RAIZ_DO_PROJETO>" --manifest evidence/TAREFA/manifest.json revise --review evidence/TAREFA/revisao-1.json
python bin/mb-relatorios-glm.py --project "<RAIZ_DO_PROJETO>" --manifest evidence/TAREFA/manifest.json verify --inspection evidence/TAREFA/inspecao-1.json
python bin/mb-relatorios-glm.py --project "<RAIZ_DO_PROJETO>" --manifest evidence/TAREFA/manifest.json deliver
python bin/mb-relatorios-glm.py --project "<RAIZ_DO_PROJETO>" --manifest evidence/TAREFA/manifest.json promote --slug estrutura-aprovada
```

`init` nao sobrescreve manifesto existente. `status` e somente leitura e sai
`2` quando bloqueado; `ready` sem `delivered_at` ainda nao e entrega concluida.
`revise` e `verify` podem terminar com sucesso registrando apenas uma etapa;
nao significam gate final aprovado. `deliver` exige o gate inteiro e registra
a data. Integracao nativa usa `find_manifest(root, report)` e
`status(root, manifest)`; exibir como concluido exige `state="ready"` mais
`delivered_at` preenchido. Captura, teste de abrir no app e apresentacao nativa
sao provas diferentes. Este ledger nao substitui o recibo de apresentacao.

## Revisao independente

JSON de revisao exige `artifact_sha256` de `status`, `reviewer` com vendor
`codex`, `claude` ou `human` e `session_id` real diferente do produtor,
`criteria` e `findings`. Nunca rotular dois subagentes como contas diferentes.

Os seis criterios sao obrigatorios, sem duplicatas:
`understanding`, `organization`, `hierarchy`, `functional_layout`,
`finalized_references`, `factuality`. Cada um tem `id`, `verdict` (`pass` ou
`fail`), `observation` concreta e `evidence` com lista de arquivos existentes.
Um `passed=true` isolado e recusado. Exemplo de elemento de `criteria`:

```json
{"id":"hierarchy","verdict":"pass","observation":"O resultado aparece antes das acoes; fonte e data permanecem junto ao numero.","evidence":["evidence/TAREFA/desktop-1440.png"]}
```

`findings` e uma lista explicita, vazia quando nao ha defeitos observados.
Cada achado tem `id` estavel, `criterion` dentre os seis, `status` (`open` ou
`resolved`), `observation` e `evidence`. Resolvido exige ainda `resolution`
e `acceptance_test` concretos. Achados abertos do ciclo anterior nao podem
desaparecer; reaparecem como abertos ou resolvidos com prova. Nenhum achado
aberto ou criterio reprovado atravessa `deliver`/`promote`.

## Inspecao visual e funcional

Formato de `inspecao-1.json` (as observacoes abaixo sao apenas estrutura;
substituir pelo que foi realmente visto):

```json
{
  "artifact_sha256": "HASH_COMPOSTO_DO_STATUS",
  "inspector": {"vendor":"codex","session_id":"ID_REAL_OUTRO_QUE_O_PRODUTOR"},
  "actually_viewed": true,
  "captures": [
    {"viewport_width":1440,"path":"evidence/TAREFA/desktop-1440.png","verdict":"pass","observation":"Descrever hierarquia, organizacao e controles observados no desktop."},
    {"viewport_width":390,"path":"evidence/TAREFA/mobile-390.png","verdict":"pass","observation":"Descrever leitura, quebra e controles observados no celular."}
  ],
  "tests": [
    {"command":"COMANDO_REAL_EXECUTADO","exit_code":0,"log":"evidence/TAREFA/controles.log","observation":"Descrever quais controles responderam e o resultado observado."}
  ]
}
```

PNG deve ter largura fisica de 1440 e 390 respectivamente, portanto capturar
em escala 1. Altura pode variar. Arquivo deve conter pixels PNG validos, sem
entrelacamento. Checksum, dimensoes e conteudo comprimido sao conferidos;
fixture sintetica dos testes nunca deve ser usada como prova da entrega.
Logs precisam existir e nao estar vazios. O comando nao e executado pelo
ledger: o revisor assina a observacao e fornece a evidencia da execucao real.

## Correcao e invalidacao

Qualquer mudanca no HTML ou nos recursos rastreados invalida revisao,
capturas, testes e estado da entrega. Mudanca em fonte de producao, fragmento,
revisao, screenshot ou log tambem bloqueia. O estado antigo permanece no
historico; a API de status nao apresenta sua entrega como atual.

Depois de devolver os achados ao GLM e obter nova producao real, preservar
outro `producao-N/result.json` e outro `fragment.html`, atualizar o HTML e usar:

```powershell
python bin/mb-relatorios-glm.py --project "RAIZ_ABSOLUTA" --manifest evidence/TAREFA/manifest.json refresh --production evidence/TAREFA/producao-2/result.json --fragment evidence/TAREFA/producao-2/fragment.html
```

`refresh` exige revisao anterior e mudanca real do artefato, arquiva o ciclo
inteiro e zera as provas atuais. Repetir dois ciclos de correcao sem reduzir
achados abertos/criterios reprovados exige nova sessao real. O limite de tres
sessoes e o limite independente de tres correcoes por execucao sao
**HEURISTICAS** de parada para reenquadrar, nao limites do vendor. Ha no
maximo o original mais tres `refresh`, mesmo quando a mesma sessao melhora.
O CLI nao reinicia sessoes nem despacha loops.

Reenquadrar depois do limite exige pedido humano explicito. `begin-task
--request` com `kind="human_reframe"` (campos `id`, `human_request`,
`reason`, `session_id`, `at` e `human_event`) so e aceito quando o ciclo
atual ja foi revogado com `revoke`, nenhuma entrega existe na execucao
corrente e nao ha outro reinicio pendente. `human_event` vincula o pedido a
uma mensagem digitada real:

```json
{"kind":"claude_transcript","transcript":"<HOME>/.claude/projects/<PROJETO>/SESSAO.jsonl","event_uuid":"UUID_DA_MENSAGEM","excerpt":"evidence/TAREFA/evento-humano.jsonl"}
```

O `excerpt` (dentro do projeto) e a linha literal do transcript: tipo
`user`, papel `user`, sem `isMeta`/`isSidechain`, conteudo de texto (nunca
`tool_result`), mesmo `uuid` e `sessionId` declarados, contendo o
`human_request` literal e o nome do arquivo do relatorio como palavra
inteira, com ou sem `.html`/`.htm` (`REPORT` e `REPORT.html.` casam;
`REPORT-OUTRO` e `REPORT.OUTRO.html` nao). O `timestamp` da propria
linha precisa ser posterior a criacao do ciclo revogado (mensagem antiga nao
autoriza execucao nova) e nao futuro. A linha precisa existir no transcript
sob `~/.claude/projects`, caminho absoluto e sem link/junction em nenhuma
pasta do caminho declarado. Cada evento e
consumido uma unica vez em todos os projetos: o registro compartilhado
`CENTRAL/.automations/relatorios-glm/autorizacoes-humanas.json` (com trava)
guarda projeto, relatorio, manifesto e ciclo revogado; a reserva acontece
antes de gravar o manifesto, entao falha parcial deixa o evento consumido,
nunca reutilizavel. Dois relatorios de mesmo nome em pastas diferentes: so
o primeiro reinicio usa a mensagem; pedir os dois exige duas mensagens.
Arquivo local nao e assinatura: o vinculo encarece uma autorizacao forjada,
nao a torna impossivel.

A nova execucao comeca no ciclo seguinte e registra `excluded_sessions`:
toda sessao GLM ja usada no manifesto fica recusada, portanto o primeiro
`refresh` exige sessao GLM inedita. Mesmo relatorio, mesmo manifesto e
historico preservado; achados abertos do ciclo revogado continuam
obrigatorios na revisao seguinte; os limites de tres sessoes e tres correcoes
recomecam so para essa execucao. Tarefa entregue continua usando
`human_followup`. Todos os writes usam
`mb_trava` por arquivo, JSON temporario e `os.replace`; um indice reservado
com manifesto ausente apos falha parcial fica bloqueado, nao aprovado.

## Excecao extrema de credito

Produtor normal e GLM obrigatorio. Fallback Codex/Claude exige ambos
`--credit-exception ARQUIVO.json` e `--deadline ISO_COM_FUSO` futuro.
Claude `max`/`ultra` continua proibido. O limiar `<=5%` restante e a idade
maxima de `300 s` sao **HEURISTICAS**, nao equivalencia de tokens/custo.

```json
{
  "vendor":"glm",
  "account":"CONTA_REAL_DA_ASSINATURA",
  "status":"observed",
  "observed_at":"DATA_ISO_RECENTE_COM_FUSO",
  "all_applicable_windows_confirmed":true,
  "windows":[
    {"name":"JANELA_REAL","remaining_percent":4,"reset_at":"DATA_ISO_FUTURA_APOS_O_PRAZO"}
  ]
}
```

Incluir TODAS as janelas aplicaveis com saldo valido. Pelo menos uma janela
restritiva precisa estar extrema e sem reset util antes do prazo. Em vez de
`reset_at`, ausencia real de reset requer `reset_absence_confirmed=true` e
`reset_at=null`. Dado desconhecido, fonte antiga/futura, lista incompleta,
falha da ferramenta, reset passado ou reset util em janela extrema nao
autorizam fallback. Snapshot da excecao fica preservado no ciclo. Nao ha
troca global de conta ou consumo de API paga neste mecanismo.
O momento de validacao (`validated_at`) e congelado junto ao ciclo: entregar
depois nao torna retroativamente antiga uma leitura valida na producao.
O gate reconstroi a excecao a partir da fonte e do momento original; remover
a excecao do manifesto nao transforma fallback em producao GLM.

## Promocao para contexto reutilizavel

`promote` so funciona depois de `deliver` e revalida o gate inteiro. Copia
HTML, recursos e evidencias reais para
`CENTRAL/motor/modelos/relatorios/glm/promovidos/SLUG/HASH_DO_ARTEFATO/`,
com `provenance.json` atribuindo autor, revisores, criterios, fontes, hashes
e data. Atualiza somente o conjunto `promoted` no indice unico
`motor/modelos/relatorios/glm/indice.json`, preservando `master`, `references`
e demais campos. `technical_approval=VERIFICADO_TECNICAMENTE` nao e aprovacao
humana: `human_approval=NAO_MEDIDO`, com escopo explicito do exemplar.
Nao sobrescreve versao existente; repeticao idempotente confere a copia e a
procedencia antes de recuperar a associacao. A pasta e publicada por rename
somente apos copia e reconferencia, sem alterar o projeto de origem.
Esse exemplar e referencia finalizada para o proximo GLM, sujeito a revisao
contextual; nao vira template universal por ter passado uma vez.

## Revogacao de candidato ou exemplar

Defeito descoberto depois da entrega ou rejeicao humana real pode tirar o
artefato do conjunto ativo, preservando arquivos, prova e procedencia:

```powershell
python bin/mb-relatorios-glm.py --project "RAIZ_ABSOLUTA" --manifest evidence/TAREFA/manifest.json revoke --reason "MOTIVO_CONCRETO" --evidence evidence/TAREFA/rejeicao-literal.txt
```

`--artifact-sha256 HASH` aponta a um ciclo anterior do mesmo manifesto;
sem ele, revoga o ciclo atual. `--evidence` pode ser repetido. O comando exige
motivo e arquivos reais, marca o candidato como `rejected`, retira o hash de
`promoted`, registra `revocations` no indice unico e liga a revogacao ao ciclo.
Nao apaga nem reescreve a copia do exemplar ou seu `provenance.json`.
Pode rejeitar candidato ainda sem gate final ou ciclo antigo cujo HTML mudou.
O estado atual revogado bloqueia entrega e a ponte de abertura; o mesmo hash
na biblioteca nao pode ser promovido novamente sob outro slug. A nova
producao precisa corrigir e produzir outro hash, preservando a rejeicao no
historico. Evidencia de rejeicao nao vira inferencia de aprovacao humana.

Em cada gate, revisao e inspecao sao reconstruidas dos respectivos JSON
congelados e comparadas aos dados normalizados do manifesto. Apagar um
achado, criterio, veredito ou observador apenas no manifesto bloqueia.

## Verificacao do mecanismo

```powershell
python -m unittest motor.tests.test_mb_relatorios_glm -v
python -m py_compile bin/mb_relatorios_glm.py bin/mb-relatorios-glm.py
```
