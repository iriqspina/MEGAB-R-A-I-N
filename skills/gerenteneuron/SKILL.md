---
name: gerenteneuron
description: Gerente geral dos projetos do Henrique e chat multi-IA local. Use quando ele pedir status geral ("onde estamos", "status de tudo"), mandar um pedido sem dizer o projeto, pedir para abrir/rodar/consertar o app GerenteNeuron, mexer no cofre de credenciais, conferir a tabela de preços dos modelos (pricing.json), ou ajustar o roteamento por custo entre OpenAI, Anthropic, Gemini, Moonshot e Ollama local. Também cobre "qual skill eu uso pra isso".
---

# /gerenteneuron — gerente geral + chat multi-IA local

Ponto único de entrada. Duas funções que não se confundem:

1. **Gerente de projetos** — recebe pedido genérico, identifica projeto +
   intenção, e aponta a skill de destino. Não executa a entrega.
2. **Chat multi-IA** — conversa roteada por custo/capacidade entre provedores
   pagos e o Ollama local.

Raiz do app: `S:\projetos multi i.a\MEGA B R A I  N\gerenteneuron\`

---

## 0. Antes de qualquer coisa

Este projeto vive dentro do megabrain. Se a tarefa é **entrega** (mexer no
código, mudar roteamento, escrever doc), rode o Gate 0 do `/megabrain`: leia
`ESTADO.md` → `HANDOFF.md` → fim do `DECISOES.md` → `LICOES.md` deste projeto,
e cheque a trava em `HANDOFF.md`. Se é só perguntar o status, não precisa.

`LICOES.md` do projeto tem quatro entradas de 260816. Leia antes de repetir uma
delas.

---

## 1. Roteamento do pedido

| O que ele pediu | O que fazer |
|---|---|
| "onde estamos", "status de tudo" | Ler `projetos.json` + `ESTADO.md` de cada projeto listado |
| Pedido sem projeto nomeado | Identificar por palavra-chave em `projetos.json`, confirmar antes de agir |
| "abre o GerenteNeuron" | `run.cmd` |
| Resposta ruim / cara / modelo errado | Seção 3 (roteamento e preços) |
| "esqueci a senha", "não abre o cofre" | Seção 4 (cofre) |
| Mexer no código do app | Seção 5 (mudança segura) |

O gerente **orquestra, não substitui**. Quando ele apontar `/portfolio`,
`/rodada`, `/financeirodasilva` ou `/megabrain`, a execução real acontece lá,
com os gates da skill de destino.

Ele só conhece o que está em `projetos.json` — não varre o disco. Projeto que
"o GerenteNeuron não achou" quase sempre é projeto não cadastrado.

---

## 2. Abrir e operar

```
run.cmd                      abre o app em http://127.0.0.1:8787
testar.cmd                   32 testes, stdlib pura, sem dependência
modelos.cmd --listar         tabela de modelos ordenada por custo
modelos.cmd --conferir       bate pricing.json contra a API dos provedores
aspirar.cmd                  mb-aspirador no código do app
```

Sem `.venv`, os `.cmd` caem no Python do sistema. O `.venv` só existe por causa
do `cryptography` (cofre); o resto do app é stdlib pura.

---

## 3. Roteamento por custo — onde mexer

**`pricing.json` é a fonte única.** Lista de modelos, classe e preço por 1M de
tokens. A fila do roteador é **derivada** dele, do mais barato ao mais caro.
Trocar de modelo, mudar prioridade ou corrigir preço = editar esse JSON. Não
existe lista de modelos hardcoded em `config.py` nem tabela de preço dentro dos
providers — se você achar uma, é regressão.

Classes: `quick` (pergunta curta, extração), `standard` (explanação, síntese),
`deep` (arquitetura, auditoria, decisão). Estratégia `local_code` tenta o Ollama
antes de qualquer pago.

**Regra dura:** preço e ID de modelo são fato sobre o mundo externo. Nunca
escreva de memória. Confira na fonte, registre a URL em `pricing.json.fontes` e
atualize `verificado_em`. Depois de `revalidar_em_dias`, o app mostra aviso no
topo do chat e `modelos.cmd --conferir` sai com código 1.

Ajustar a classificação (que pergunta cai em que classe) é em
`router.py`: `TERMOS_DEEP`, `TERMOS_CODE`, `TERMOS_CHEAP`. Os termos passam por
normalização (sem acento, pontuação virando espaço, casamento de palavra
inteira) — por isso termo de duas palavras funciona e `api` não casa dentro de
`rapidez`. Mexeu ali, rode `testar.cmd`.

Se ele reclamar que "está gastando muito": leia `/api/eval` (ou
`data/feedback.jsonl`) antes de opinar. O rodapé de cada resposta já mostra
modelo, custo estimado e quais candidatos foram pulados.

---

## 4. Cofre de credenciais

```
python setup-crypto.py                      cria .venv e instala cryptography
.venv\Scripts\python setup-vault.py         cria o cofre e a senha mestre
.venv\Scripts\python mb-vault.py add CHAVE valor
.venv\Scripts\python mb-vault.py list
.venv\Scripts\python mb-vault.py reset --recovery <chave>
```

Fernet (AES-128-CBC + HMAC) com chave derivada por PBKDF2, 600k iterações. A
chave real dos dados é aleatória, protegida em paralelo pela senha mestre e pela
chave de recuperação.

**Diga isto ao Henrique se `vault/recovery.key` ainda existir:** enquanto a
chave de recuperação estiver na mesma pasta do cofre, a senha mestre não
protege contra quem tem acesso ao disco. O lugar dela é fora — pendrive ou
gerenciador de senhas.

O `reset` aceita a chave crua ou o conteúdo inteiro do `recovery.key` colado. A
chave usada é queimada e outra é gerada no mesmo passo.

Nunca escreva credencial em arquivo versionado. O diálogo "Configurar chaves"
grava `.env` em texto puro — funciona, mas o cofre é o caminho recomendado.

---

## 5. Mudança segura no app

1. `testar.cmd` **antes** de mexer — saber que estava verde.
2. Mudou roteamento, preço, classificação, cofre ou origem HTTP? Escreva o teste
   junto, não depois.
3. `testar.cmd` de novo. Vermelho é bug, não teste chato: dos 32 casos, um
   encontrou falso positivo real no `gerente.py` no dia em que foi escrito.
4. Mexeu em `pricing.json`? `modelos.cmd --conferir`.
5. Gate 6 do `/megabrain`: `ESTADO.md`, `HANDOFF.md`, `DECISOES.md` com a
   alternativa descartada, e lição em `LICOES.md`.

Invariantes que não podem cair:
- O servidor escuta só em `127.0.0.1` e recusa `Origin`/`Host` de fora do
  localhost. Sem isso, qualquer aba do navegador fala com a API e gasta as keys.
- `route()` repassa o histórico ao provedor. Se parar, o chat perde a memória —
  e isso não aparece em teste de uma mensagem só.
- Provedor sem key nunca entra na fila; o mock é sempre o último recurso, para o
  app nunca ficar mudo.

---

## Como isso costuma dar errado

- Esperar que o gerente adivinhe projeto não cadastrado em `projetos.json`.
- Confundir as abas: "status do portfólio" no Chat IA roteia um modelo, não
  invoca `/portfolio`.
- Editar preço direto no código do provider. Não existe mais lá — é
  `pricing.json`.
- Escrever ID ou preço de modelo de memória. Eles mudam; a tabela tem data de
  verificação por isso.
- Achar que "roda e responde" é verde. O app rodava e respondia com o chat sem
  memória por uma sessão inteira.
