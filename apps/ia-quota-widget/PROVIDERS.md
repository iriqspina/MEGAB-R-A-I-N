# `providers.py` — de onde vem cada número

Módulo de leitura de cota. Só stdlib. A UI chama `fetch_provider(provider_id)`
e recebe sempre o mesmo formato, com falha virando `status` em vez de exceção.

Evidência das fontes, com endpoints e resultados de sonda:
artefato Traycer `260908-widget-fontes`.

## Contrato

```python
fetch_provider("claude") -> {
    "provider":   "claude",
    "label":      "Claude",
    "status":     "ok" | "unavailable" | "auth_required" | "error" | "rate_limited",
    "source":     "api.anthropic.com/api/oauth/usage",
    "fetched_at": "2026-09-08T16:45:05+00:00",   # só quando status == "ok"
    "windows": [
        {"id": "session",             "label": "Sessão",         "used_percent": 37.0, "resets_at": "..."},
        {"id": "weekly_scoped:Fable", "label": "Semana · Fable", "used_percent": 28.0, "resets_at": "..."},
    ],
    "message":    "Plano max.",
}
```

`PROVIDER_IDS = ("codex", "claude", "zai", "gemini_cli", "antigravity", "gemini_web")`.
`fetch_all()` percorre todos.

### O que cada status quer dizer

Escolher errado aqui é pior que errar o número, porque muda o que o <USUARIO> faz a seguir.

| Status | Significado | O que a UI deve dizer |
| --- | --- | --- |
| `ok` | Leitura boa, agora | Percentual + horário de renovação |
| `auth_required` | A fonte existe, a credencial não serve | O passo para destravar (está em `message`) |
| `rate_limited` | HTTP 429 do fornecedor | "consultas demais", tentar no próximo ciclo |
| `error` | Falha **transitória**: rede caiu, processo travou, JSON torto | Erro honesto + último valor bom com a idade |
| `unavailable` | Esta fonte **não existe nesta máquina** ou não tem método autorizado | Estado permanente, sem promessa de voltar |

`error` nunca vira `unavailable`. Dizer "não tem essa fonte" sobre algo que
existe e só não respondeu agora manda o usuário procurar problema no lugar errado.

## Regras que o código impõe

1. **Só leitura.** Nenhum adaptador escreve em arquivo de credencial nem renova
   token. Vencido → `auth_required` com a instrução.
2. **`None` nunca vira `0`.** O próprio esquema do Codex diz: *"clients must not
   infer recovery from percentages or reset times"*. Barra sem dado é barra
   vazia rotulada, não barra zerada.
3. **Uma fonte por produto.** `gemini_cli` e `antigravity` são cotas diferentes
   e nunca são fundidas num card só.
4. **Contagem local de token nunca vira percentual de cota.** `account/usage/read`
   do Codex e os `.jsonl` do Claude respondem "quanto rodei aqui", não
   "quanto posso rodar ainda".
5. **Prazo finito em tudo**, inclusive no subprocesso.
6. **Nada de segredo sai daqui** — nem em `message`, nem em exceção, nem em log.
   `_sanitized()` devolve a versão publicável (sem `label` e sem `message`).

## Fontes, uma a uma

### `codex`

`codex app-server --listen stdio://`, JSON-RPC 2.0 por stdio, sem o cabeçalho
`jsonrpc` no fio. Protocolo documentado em <https://learn.chatgpt.com/docs/app-server>.

Sequência em `CODEX_STEPS`: `initialize` → `initialized` (notificação) →
`account/read {"refreshToken": false}` → `account/rateLimits/read` com
**`params: null`**.

Duas armadilhas medidas, as duas custaram tempo:

- `account/rateLimits/read` **recusa objeto vazio**: `{}` devolve
  `-32600 invalid type: map, expected unit`. Tem que ser `null`.
- **Tem que ser pergunta e resposta, uma de cada vez.** Escrever as quatro
  linhas de uma vez e fechar o stdin faz o servidor responder só ao
  `initialize` e sair em 1,2 s. Com o stdin aberto e leitura por turno:
  6 execuções seguidas, 6 × `ok`, 0,69–1,08 s.

Janelas saem de `rateLimitsByLimitId` (uma entrada por `limit_id`; cai para
`rateLimits` quando o mapa não vem), com `primary` e `secondary` virando
janelas separadas. `resetsAt` é **epoch em segundos**.

**A ordem das janelas é ordenada por `limit_id`, não pela ordem do payload**
(`providers.py:400`). Com mais de um bucket, herdar a ordem do dicionário faria
os rótulos trocarem de lugar entre atualizações e pareceria bug para quem olha.
Há teste travando isso (`test_ordem_das_janelas_nao_depende_da_ordem_do_payload`);
não trocar o `sorted()` por iteração direta.

Ressalva honesta: nesta conta o mapa veio com **um** bucket só. O caminho N>1
está exercitado em fixture, nunca com dado real.

Binário: `IA_QUOTA_CODEX_BIN` sobrepõe; senão `shutil.which("codex")`.

**Nunca chamar:** `account/rateLimits/resetCredits/consume` (gasta crédito de
reset) nem `account/login/*`.

### `claude`

`GET https://api.anthropic.com/api/oauth/usage`, com `Authorization: Bearer` do
`claudeAiOauth.accessToken` de `~/.claude/.credentials.json` e o cabeçalho
`anthropic-beta: oauth-2025-04-20`.

`expiresAt` é epoch em **milissegundos**; token vencido nem chega a gastar uma
chamada. Plano (`subscriptionType`) sai do próprio arquivo, sem rede.

Parsing: `limits[]` é a fonte primária — é dela que sai a **cota por modelo**,
em `weekly_scoped` com `scope.model.display_name`. Os campos nomeados
(`five_hour`, `seven_day`) são fallback. Bucket desconhecido é ignorado em vez
de quebrar: os nomes internos mudam sem aviso (já apareceram `nimbus_quill`,
`iguana_necktie`).

O CLI do Claude **não** expõe subcomando de uso; `/usage` só existe dentro da
sessão interativa. HTTP é a única rota programável.

### `zai` (260913)

`GET https://api.z.ai/api/monitor/usage/quota/limit`, cabeçalho `Authorization`
com a chave crua (com `Bearer ` também respondeu 200 na sonda). Endpoint **não
documentado** pela Z.ai: é o que as ferramentas de uso do próprio Coding Plan e
plugins comunitários consultam (openusage.sh, opencode-glm-quota). Pode mudar
sem aviso. Não consome crédito: duas leituras seguidas devolveram o mesmo
`currentValue`.

Chave, na ordem (primeira que não for recusada com 401/403):

1. `ZAI_API_KEY` do ambiente;
2. `%USERPROFILE%\.config\zai\cli-key.dpapi` — a chave fixa `megabrain-cli-fixo`
   dos launchers GLM, gravada por `bin/zai/import-key-from-clipboard.ps1` com
   `ConvertFrom-SecureString` (hex de blob DPAPI, texto UTF-16LE). Aberta com
   `CryptUnprotectData` via `ctypes`, só em memória;
3. `builtin:zai-coding-plan` em `%USERPROFILE%\.zcode\v2\config.json`, se `enabled`.

As chaves 2 e 3 são diferentes (conferido por comparação, sem imprimir) e da
mesma conta. Nenhuma é gravada, renovada ou copiada.

Resposta real sanitizada (plano pro, 260913):

```json
{"code": 200, "success": true, "data": {"level": "pro", "limits": [
  {"type": "CREDIT_LIMIT", "unit": 3, "number": 5, "usage": 12000, "currentValue": 144,
   "remaining": 11855, "percentage": 1, "nextResetTime": 1789347502491},
  {"type": "CREDIT_LIMIT", "unit": 6, "number": 1, "usage": 60000, "currentValue": 266,
   "remaining": 59733, "percentage": 1, "nextResetTime": 1789834746970}]}}
```

- **`percentage` é inteiro arredondado** (1 para 144/12 000 = 1,2 %). O parser
  usa `currentValue / usage`; `percentage` só entra quando os dois faltam.
- `nextResetTime` é epoch em **milissegundos**.
- `unit` × `number`: só `3 × 5` (5 h, renovava em 3,8 h) e `6 × 1` (semana,
  renovava em 5,8 d) estão mapeados, inferidos da própria renovação. Unidade
  desconhecida fica com `duration_minutes = None` e ritmo `NAO_MEDIDO`.
- `TIME_LIMIT` (cota de ferramentas MCP em outros planos) aparece rotulado
  "Ferramentas", **nunca visto com dado real**.

### `gemini_cli`

Dois POSTs em `https://cloudcode-pa.googleapis.com/v1internal`, com o
`access_token` de `~/.gemini/oauth_creds.json`:

1. `:loadCodeAssist` → resolve `cloudaicompanionProject` e `currentTier`.
2. `:retrieveUserQuota` com esse projeto → `buckets[]`.

Cada bucket traz **`remainingFraction`** (fração **restante**, 0–1), não
percentual usado: `used_percent = (1 - remainingFraction) * 100`. Bucket sem
`modelId` ou sem fração é descartado — mesma guarda do próprio Gemini CLI.

Estado hoje: `auth_required`. Para destravar sem custo: **abrir o `gemini` uma
vez e sair** — o CLI renova sozinho, e não custa inferência se nenhum prompt
for enviado.

#### Decisão travada: este módulo NÃO renova o token do Gemini — nem em memória

Não é esquecimento nem pendência. Foi proposto, avaliado e recusado pelo
orquestrador em 2026-09-08. Três motivos, do mais pesado para o mais leve:

1. **Escopo.** Este app é leitor de cota. Rodar fluxo OAuth contra
   `oauth2.googleapis.com` é agir *como* o usuário numa conta Google, não ler
   um arquivo — outra categoria de risco. "Em memória" muda onde o resultado
   para, não a natureza da chamada.
2. **Produto.** Token vencido é informação útil, não defeito a esconder.
   Renovar em silêncio mascara que a credencial do Gemini CLI está velha e o
   usuário nunca fica sabendo. `auth_required` com a instrução exata na
   `message` diz o que houve e o que fazer.
3. **Risco assimétrico** *(hipótese não confirmada, e não vale medir)*: se o
   endpoint de token rotacionar o `refresh_token` e não persistirmos o novo, o
   `oauth_creds.json` em disco fica com um refresh inválido e o **Gemini CLI do
   usuário quebra — quebrado pelo widget**. O prêmio é uma porcentagem num
   canto da tela; não paga a aposta.

Se alguém for "consertar" isso depois: leia os três pontos acima antes.

### `antigravity`

Produto separado do Gemini CLI, com cota própria. Não é OAuth HTTP: é um
language server local em porta loopback dinâmica.

Descoberta: `ANTIGRAVITY_LS_ADDRESS`, ou varredura de `netstat -ano` +
`tasklist` atrás de processo escutando em `127.0.0.1` cujo nome bata com
`antigravity` / `language_server` / `agy`. CSRF vem do HTML da raiz (`csrfToken":"`),
e vai no cabeçalho `x-codeium-csrf-token` do POST para
`/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary`.

#### NÃO VERIFICADO — o formato da resposta nunca foi visto com o servidor no ar

Tudo nesta seção veio da leitura do código de `evandrofadul/native-ai-usage-hud`,
**nenhuma linha veio de uma resposta real**. Na única medição desta máquina o
language server estava parado, então o que ficou verificado foi o estado
offline, não a cota.

Por isso `parse_antigravity_quota` faz varredura defensiva em vez de fixar um
caminho: percorre o JSON inteiro procurando entradas que tragam identificador
**e** medida (`usedPercent` ou `remainingFraction`), e descarta o resto. Entrada
sem medida não vira 0.

O widget **não** abre o IDE, e ninguém deve abri-lo só para medir. Sem processo,
`unavailable` com o motivo.

**Quando alguém tiver o Antigravity aberto, conferir exatamente isto** (na
ordem; cada item que falhar invalida o passo seguinte):

1. A descoberta acha a porta? `discover_antigravity_bases()` devolve lista não
   vazia — e o nome de processo que casou (`antigravity` / `language_server` /
   `agy`) é mesmo do Antigravity, não de outro programa com nome parecido.
2. O `GET` na raiz devolve HTML com `csrfToken":"`? Se o formato mudou,
   `extract_csrf` volta `None` e o POST vai sem o cabeçalho.
3. O POST em `RetrieveUserQuotaSummary` aceita corpo `{}`, ou exige campo?
   Hoje mandamos `{}` por suposição.
4. **A forma da resposta**: onde ficam os buckets (chave e profundidade), o nome
   real do campo de medida, se é fração restante ou percentual usado, e o nome
   do campo de renovação. Capturar o JSON **sanitizado** (sem id de conta,
   e-mail ou token) e trocar a varredura por parser direto.
5. Se há janela por modelo, como no Gemini CLI, ou só um número agregado.

### `gemini_web`

`unavailable` permanente e proposital. Não foi encontrado nesta pesquisa método
de consulta compatível com a restrição de não usar cookie de navegador. Não
inferir a partir do Code Assist: é outro produto e outra cota.

## Unidades — a armadilha que mais dá erro silencioso

Cada fornecedor usa uma convenção diferente. Toda conversão passa pelos
helpers, nunca inline.

| Fonte | Percentual | Renovação | Helper |
| --- | --- | --- | --- |
| Codex | `usedPercent` 0–100 | `resetsAt` epoch **segundos** | `normalize_percent` · `normalize_epoch_seconds` |
| Claude | `percent` 0–100 | `resets_at` ISO com offset | `normalize_percent` · `normalize_iso` |
| Z.ai | `currentValue / usage` (`percentage` é inteiro) | `nextResetTime` epoch **ms** | `normalize_percent` · `normalize_epoch_seconds(ms/1000)` |
| Gemini CLI | `remainingFraction` 0–1 **restante** | `resetTime` ISO | `percent_from_remaining_fraction` · `normalize_iso` |
| Antigravity | a confirmar | a confirmar | os dois, por varredura |

`normalize_iso` tolera sufixo `Z`, fração de segundo com mais de 6 dígitos
(a Anthropic manda) e offset diferente de UTC. Tudo sai em ISO UTC.

## Testes

```
.venv\Scripts\python.exe -m pytest tests/ -q
```

`tests/test_providers.py` — 93 testes verdes junto com os do resto do app, em
~1 s. Nenhum toca rede, disco real ou credencial real: `_HttpStub` substitui
`_http`, `_StubHome` desvia `IA_QUOTA_HOME` para um diretório temporário, e os
tokens de fixture são a string `FAKE-NAO-E-TOKEN`.

Cobrem, por fonte: parser com payload sanitizado, `None` ≠ 0, HTTP 401/403/429/500,
falha de rede, JSON incompleto, campo faltando, percentual fora de 0–100,
`resets_at` ausente ou em formato inesperado, prazo do subprocesso, encerramento
educado do processo filho, e a distinção `error` × `unavailable`.

## Leitura manual

```
.venv\Scripts\python.exe providers.py
```

Imprime uma linha JSON sanitizada por provedor — sem plano, e-mail, id de conta
ou token. Útil para conferir o estado real antes de acreditar em relato.

## Variáveis de ambiente

| Variável | Para quê |
| --- | --- |
| `IA_QUOTA_HOME` | Sobrepõe o diretório de usuário (usado pelos testes) |
| `IA_QUOTA_CODEX_BIN` | Aponta um binário `codex` específico |
| `ZAI_API_KEY` | Chave do GLM Coding Plan, antes do DPAPI e do ZCode |
| `ANTIGRAVITY_LS_ADDRESS` | Endereço do language server, quando conhecido |
