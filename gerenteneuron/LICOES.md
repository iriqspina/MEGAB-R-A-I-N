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
