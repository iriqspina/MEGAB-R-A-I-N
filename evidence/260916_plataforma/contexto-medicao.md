# Medição de contexto — diagnóstico independente, 260916

TL;DR: o medidor existe e há **177 eventos nos cinco logs citados**. O “zero”
da análise Claude foi causado por uma consulta com o formato de dados errado.
Isso é separado da ativação atual dos hooks nos clientes, ainda não certificada.

## Causa comprovada

Na linha 108 do transcript
`<USER_HOME>\.claude\projects\S--projetos-multi-i-a-MEGA-B-R-A-I--N\8564372e-8f16-4e7c-8582-936ec9647784.jsonl`,
a chamada `toolu_01THQqrQu24K6x7nWcMPBz9s` executou:

```python
ci = d.get('contexto_injetado')
```

Depois procurou `chars` dentro de `ci`. O formato real é:

```json
{"evento": "contexto_injetado", "chars": 10923, "pecas": 4}
```

O exemplo acima ilustra a estrutura; o recibo JSON contém as contagens e hashes
medidos sem copiar prompts, respostas ou configurações completas. A consulta
correta seleciona `d.get('evento') == 'contexto_injetado'` e lê `d['chars']` e
`d['pecas']` diretamente na raiz do evento.

O código canônico implementa essa gravação em
[mb-contexto.py:304](<<MEGABRAIN_ROOT>/bin/mb-contexto.py:304>);
o escritor coloca o nome na chave `evento` em
[mb_telemetria.py:106](<<MEGABRAIN_ROOT>/bin/mb_telemetria.py:106>).

## Contagem reproduzida

| Arquivo em .mb-log | Eventos corretos | Consulta errada do Claude |
|---|---:|---:|
| telemetria-260910.jsonl | 23 | 0 |
| telemetria-260911.jsonl | 41 | 0 |
| telemetria-260913.jsonl | 47 | 0 |
| telemetria-260914.jsonl | 33 | 0 |
| telemetria-260915.jsonl | 33 | 0 |
| Total dos cinco | **177** | **0** |

No conjunto de **22 arquivos** disponíveis, há **965 eventos contexto_injetado**.
Não houve linhas JSON inválidas nos cinco arquivos. O último evento dos cinco
é de **15/09/2026 às 17:42:04 -03:00**, identificado como agente `claude`, com
**10.923 caracteres**. Isso demonstra registro histórico, não execução do cliente
atualmente aberto.

Hashes individuais dos logs e dos arquivos de implementação/configuração
inspecionados estão no
[recibo estruturado](<<MEGABRAIN_ROOT>/evidence/260916_plataforma/contexto-medicao.json>).

## Teste controlado de main()

Quatro casos aprovados, executando a função `main()` real com `montar` e o
escritor de telemetria substituídos por funções simuladas:

1. Bloco não vazio: emite o bloco e solicita um evento, com quantidade de
   caracteres igual ao texto emitido e quantidade de peças correta.
2. Bloco vazio: não solicita evento.
3. Erro em `montar`: retorna sem evento e sem interromper a sessão.
4. Escritor retorna `False`: a função continua com saída normal e código zero.

Nenhum log de produção foi gravado pelo teste. Ele demonstra o comportamento
do medidor e sua falha silenciosa; não testa recuperação de conteúdo, persistência
real nem ativação do hook por um cliente de IA.

## Instalação observada e limites por cliente

1. **Claude:** a configuração de usuário atual não declara `UserPromptSubmit`.
   Seus hooks apontam ao `agent-flow/hook.js`, que não referencia `mb-contexto`
   nem MEGABRAIN. O plugin MEGABRAIN sincronizado inspecionado declara somente
   `SessionStart`. A ativação atual do medidor é **não verificada**. A ausência
   pode ser intencional ou não; não foi inferida sua causa e nada foi instalado.
2. **Kimi:** o manifesto instalado em `.kimi-code/plugins/managed/megabrain`
   declara `UserPromptSubmit`. O script chama `bin/mb-contexto.py --agente kimi`
   da central padrão, admitindo substituição por `MEGABRAIN_ROOT`. O script
   instalado e a fonte canônica têm SHA-256 idêntico:
   `74a8b3300b0dc83743abc092e12c7714d5c6e76ee3ae92d348ed3df2150a8c2e`.
   Processo em execução, habilitação do plugin e variável herdada não foram
   testados; declaração instalada não equivale a ativação comprovada.
3. **Codex:** a configuração de usuário inspecionada não mostra comando
   MEGABRAIN de contexto. Não foi executado novo ciclo de cliente; presença de
   skills não prova hook por prompt.
4. **ZCode:** o evento `UserPromptSubmit` observado chama `agent-flow/zcode-wrapper.js`,
   que delega ao `hook.js` compartilhado e não ao medidor de contexto. Não foi
   executado novo ciclo de cliente.

## Recomendação mínima

Corrigir a leitura e as afirmações derivadas do diagnóstico Claude, preservando
o medidor existente. A consulta correta deve usar o valor de `evento`. Não criar
outro medidor nem alterar configuração com base no falso zero.

Registrar **compatibilidade/ativação atual do Claude como pendência separada**.
Antes de qualquer alteração futura, validar um ciclo real em cliente novo e
confirmar qual configuração ele carrega; não presumir desativação acidental.

Esta métrica conta caracteres e peças injetados pelo hook. Ela não mede todos
os tokens da conversa nem percentual da janela de contexto. A falta de evento
posterior pode vir de ausência de acionamento, bloco vazio, erro em `montar` ou
falha de gravação silenciosa; a causa exige evidência do ciclo específico.

Nenhuma configuração externa, fonte compartilhada, instalação de hook ou log
de produção foi alterado por esta frente.
