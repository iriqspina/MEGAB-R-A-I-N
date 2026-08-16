# LICOES — GerenteNeuron

Append-only. Lição que serviria num projeto completamente diferente vai para o
global (`C:\Users\henri\.metaprotocolo\licoes.md`); o que é específico daqui
fica neste arquivo.

## 260816 — app entregue sem um teste sequer

GATILHO: qualquer app novo do megabrain que "compila e roda".
LIÇÃO: `python -m py_compile` passou em todos os arquivos e o app subia no
navegador — e mesmo assim o chat não tinha memória (o roteador descartava o
histórico antes de chamar o provedor), o classificador tinha três regras que
nunca disparavam, e o gerente casava projeto por substring. Nada disso aparece
em compilação ou em teste manual de uma mensagem só. É a repetição exata do
achado M4 da auditoria v5.1, dentro do projeto que nasceu depois dela.
ATALHO: `tests/` junto com o primeiro commit que tem lógica, não depois. Se o
componente decide alguma coisa (rota, preço, classificação), ele precisa de um
caso que falhe quando a decisão muda.

## 260816 — tabela de preço hardcoded em quatro lugares

GATILHO: código que escolhe entre serviços pagos.
LIÇÃO: cada provider carregava a própria `estimar_custo` com preços de memória,
e a ordem da fila do roteador era uma lista escrita à mão que não olhava para
esses preços. Conferido contra as fontes oficiais em 2026-08-16: os números
erravam por até 5× e metade dos modelos já tinha saído de linha. O app anunciava
"escolho o mais barato" e escolhia por uma lista arbitrária.
ATALHO: preço e catálogo em arquivo de dados único (`pricing.json`), ordenação
derivada dele, script que bate contra a API viva (`mb-modelos.py --conferir`) e
data de validade que o app mostra na tela. Fato sobre o mundo externo precisa de
carimbo de quando foi verificado.

## 260816 — CORS aberto num servidor local que guarda API key

GATILHO: qualquer servidor local que carrega credencial em memória.
LIÇÃO: `Access-Control-Allow-Origin: *` mais bind em 127.0.0.1 parece seguro
porque "só eu acesso". Não é: qualquer página aberta no navegador podia POSTar
em `/api/chat` e queimar crédito, ou tentar senha no cofre em loop. "Local" não
quer dizer isolado quando o cliente é o navegador.
ATALHO: validar `Origin` **e** `Host` (DNS rebinding), ecoar a origem só quando
ela é localhost, e limitar tentativa em endpoint de senha.

## 260816 — chave de recuperação guardada ao lado do cofre

GATILHO: qualquer esquema de senha mestre com recuperação.
LIÇÃO: `recovery.key` era gravado em `vault/`, na mesma pasta do `vault.json`.
Quem tem acesso ao disco tem os dois — a senha mestre vira decoração. E o
arquivo tinha cabeçalho de aviso, então colar o conteúdo inteiro no reset dava
"chave inválida".
ATALHO: aviso explícito no próprio arquivo mandando movê-lo para fora, permissão
0600, e o parser aceitando tanto a chave crua quanto o arquivo colado.

## 260816 — api_id do Anthropic escrito no formato de exibição, não da API

GATILHO: qualquer `api_id` novo em `pricing.json` para um modelo Anthropic.
LIÇÃO: `pricing.json` tinha `"api_id": "claude-haiku-4.5"` — copiado do nome de
exibição ("Claude Haiku 4.5") em vez do ID real da API, que usa hífen:
`claude-haiku-4-5`. `testar_anthropic` (connectors.py) tinha o mesmo valor
hardcoded como fallback. O teste de conectividade no diálogo "Configurar
chaves" mostrou HTTP 404 "model: claude-haiku-4.5" — os outros três provedores
pagos (OpenAI, Gemini, Moonshot) e o Ollama local funcionavam; só a Anthropic
caía. Conferido contra `platform.claude.com/docs/en/about-claude/models/overview`
em 2026-08-16.
ATALHO: `api_id` é ID de API, não rótulo de marketing — nunca copiar do nome
bonito (`nome`) para o `api_id`. Ponto (`.`) em nome de modelo quase sempre
virou hífen (`-`) na API. Depois de editar `pricing.json`, rodar
`modelos.cmd --conferir` (bate contra a API viva) além de `testar.cmd`.

## 260816 — diálogo "Configurar chaves" prometia cofre que não gravava

GATILHO: qualquer texto de UI que descreve onde a credencial é salva.
LIÇÃO: `templates/index.html` dizia "as chaves ficam salvas no cofre
criptografado (gerenteneuron/vault/)", mas o endpoint que o formulário chama
(`/api/config` → `_gravar_env` em `app.py`) grava `.env` em texto puro — o
cofre (`vault.py`/`mb-vault.py`) é um caminho separado que o usuário tem que
rodar por fora. `vault/` nem existia na pasta central quando isso foi visto.
Usuário lendo "cofre criptografado" no diálogo tem falsa sensação de segurança
sobre uma chave que está em texto puro no disco.
ATALHO: texto de UI sobre segurança tem que descrever o que aquele código
específico faz, não o que o projeto faz no geral. Se o app tem dois caminhos
(cofre vs `.env`), o diálogo que só grava um dos dois não pode falar do outro
como se fosse ele.
