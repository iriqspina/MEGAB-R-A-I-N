# Neuroninhos — plano de integração dos modelos locais ao harness megabrain

Data: 2026-09-09 · Autor: agente Opus 5 (despacho da sessão 260909) · Status: **plano, nada implementado**

---

## TL;DR

1. **A analogia com Claude/Codex quebra em 3 dos 4 pontos.** Modelo local entra por HTTP (não por CLI), não recebe skill nenhuma (nem os workers Claude/Codex recebem — o motor desliga skills de propósito) e não tem cota externa. O que sobra de verdadeiramente análogo é só o **contrato de schema**. A "cota" honesta de um modelo local é **VRAM residente + churn de recarga**, e o "reset da janela" é o `keep_alive`.
2. **Achado de bloqueio, medido agora:** existem **três cópias divergentes** de `apps/automations/automations.py` (árvore principal + 2 worktrees das sessões paralelas). As duas worktrees nasceram do commit `f9a8ac0`, que **não tem** `pick_provider`/`resolve_role_provider` — essas funções só existem como mudança **não commitada** na árvore principal. Ou seja: a sessão que está desenhando "Ollama como candidato dentro de `pick_provider`" está trabalhando num arquivo onde essa função não existe.
3. **Segundo achado:** `memoria/estado/DECISOES.md` entrada 260909h descreve a correção do `parse_response` como VERIFICADA, mas o código corrigido **não está na árvore principal** — está só na worktree `silly-cartwright-33a986`. Decisão registrada como pronta, código não materializado (é exatamente a lição 260818).
4. **Ollama está de pé e medido** (0.33.3, porta 11434, 13 modelos, `nomic-embed-text` residente). **LM Studio está instalado mas com o servidor DESLIGADO** (`lms status` = OFF, porta 1234 sem listener) e só tem 3 modelos, um deles de embedding. Não liguei o servidor — isso muda o estado da máquina dele e é decisão do <USUARIO>.
5. **O template portável** (`neuroninhos/template/`) está desenhado aqui em 10 arquivos, stdlib puro, com uma correção importante em cima do que a sessão paralela escreveu: **mandar `num_ctx` fixo é seguro no `llama3.1` (4,9 GB) e é armadilha de deadlock nos modelos grandes dele (17–23 GB)** — a lição 260825 já custou um travamento de serviço.
6. **9 tarefas sequenciadas** (N0–N9) na Parte 4, cada uma pegável sozinha por um agente futuro. A N0 é bloqueio: reconciliar as três cópias antes de qualquer implementação.
7. **6 perguntas** dependem do <USUARIO> (Parte 5) — principalmente: LM Studio entra ou não, qual modelo, e se local roda automático ou só sob pedido.

---

## 🗣️ EM PORTUGUÊS

O megabrain hoje manda tarefa pra dois programas de fora (Claude e Codex) que cobram por uso e têm limite mensal/semanal. Você pediu pra fazer o mesmo com os modelos que rodam **dentro da sua máquina** (Ollama e LM Studio) — esses não cobram nada e não têm limite de plano.

**O que muda pra você:** o recurso escasso deixa de ser dinheiro/cota e passa a ser a **sua placa de vídeo** (a RTX 4070). Um modelo grande carregado ocupa 17–23 GB e vai brigar por GPU com Photoshop e Illustrator abertos. Então "de graça" não é "pode usar à vontade" — é "pode usar quando você não estiver desenhando".

**O que dói se der errado:** já aconteceu antes (registrado nas lições) — mandar um pedido com um tamanho de contexto diferente do que o modelo já tinha carregado **travou o serviço do Ollama** e só voltou com reinício. Então o cuidado principal do template é nunca mandar parâmetro "às cegas".

---

## Parte 0 — Estado medido hoje (evidência, não memória)

Tudo abaixo foi verificado por chamada real em 2026-09-09, não deduzido. Comando entre parênteses.

### Ollama — de pé

| Item | Valor medido | Como |
|---|---|---|
| Versão | 0.33.3 | `ollama --version` |
| Porta | 11434 LISTENING (PID 28124) | `netstat -ano` |
| Modelos em disco | 13 | `ollama list` |
| Residente agora | `nomic-embed-text:latest`, 323 MB, 100% GPU, ctx 2048 | `ollama ps` |
| `OLLAMA_KEEP_ALIVE` | `30m` (global, no ambiente) | `env` |
| `OLLAMA_MAX_LOADED_MODELS` | `2` (global) | `env` |
| Binário | `<USER_HOME>\AppData\Local\Programs\Ollama\ollama` | `which ollama` |

Os 13 modelos, por porte: `llama3.1:latest` 4,9 GB · `gemma4:latest` 9,6 GB · `qwen3.8-2bit-ptbr` e `hf.co/unsloth/Qwen3.8-27B-GGUF:UD-IQ2_XXS` 9,9 GB · `qwen3.8-ptbr`, `qwen-design`, `qwen3.8:27b-q4km` 17 GB · `qwen-br`, `qwen-design-br`, `qwen-code`, `qwen-deep`, `qwen3.6` 23 GB · `nomic-embed-text` 274 MB (embedding).

### LM Studio — instalado, servidor desligado

| Item | Valor medido | Como |
|---|---|---|
| CLI | `<USER_HOME>\.lmstudio\bin\lms` funciona | `which lms`, `lms version` |
| Servidor | **OFF** | `lms status` → "Server: OFF" |
| Porta 1234 | sem listener | `netstat -ano` |
| Modelos | 3, 11,13 GB total | `lms ls` |

Os 3: `google/gemma-4-e4b` (7,5 B, arch gemma4, 6,33 GB) · `locate-anything.cpp` (4,72 GB, modelo de localização em imagem, não é LLM de texto) · `text-embedding-nomic-embed-text-v1.5` (embedding, 84 MB).

**Só existe 1 LLM de texto utilizável no LM Studio hoje: o `gemma-4-e4b`.** Isso é material pra decisão da Parte 5.

### API do LM Studio (documentação oficial, buscada hoje — não de memória)

- Base: `http://localhost:1234/v1`, porta padrão 1234.
- Endpoints: `GET /v1/models`, `POST /v1/responses`, `POST /v1/chat/completions`, `POST /v1/embeddings`, `POST /v1/completions`.
- **Sem autenticação / sem API key.**
- **Saída estruturada:** só em `/v1/chat/completions`, via `response_format: {"type":"json_schema","json_schema":{"name":…,"strict":"true","schema":{…}}}`. Doc avisa: modelos abaixo de 7 B costumam não dar conta. O JSON volta como **string** em `choices[0].message.content` e precisa de parse manual. Não combina com streaming.
- **TTL / auto-evict:** parâmetro `"ttl"` no corpo do request, em **segundos**. Padrão de modelo carregado por JIT: **60 minutos (3600 s)**. Auto-evict ligado por padrão = no máximo 1 modelo JIT residente por vez.
- **JIT loading:** pedir um modelo não carregado carrega ele sozinho na primeira chamada.
- **Contexto NÃO é parâmetro de request.** É parâmetro de carga: `lms load -c/--context-length <n>`, junto de `--gpu <ratio>`, `--parallel <n>`, `--ttl <s>`, `--identifier <nome>`.

### As três cópias divergentes de `automations.py`

| Cópia | Linhas | `class Quotas` | `pick_provider` | `resolve_role_provider` | `parse_response` corrigido |
|---|---|---|---|---|---|
| `apps/automations/automations.py` (principal, não commitada) | 640 | sim | **sim** | **sim** | **não** (linha 341, predicado antigo) |
| worktree `exciting-satoshi-93280f` | 534 | sim | não | não | não (linha 227) |
| worktree `silly-cartwright-33a986` | 520 | sim | não | não | **sim** (linha 218, critério posicional) |
| commit `f9a8ac0` (HEAD, base das duas worktrees) | — | sim | não | não | não |

Worktree `exciting-satoshi-93280f` = a sessão do Ollama-como-worker (`task_ca62646b`): já criou `apps/automations/local_worker.py` (107 linhas, `health()` + `call()`), `tests/test_local_worker.py`, e um bloco `"ollama"` em `config/automations.json`. Também tocou `memoria/estado/DECISOES.md` e `memoria/nucleo/licoes-megabrain.md`.

Worktree `silly-cartwright-33a986` = a sessão do bug do `parse_response` (`task_24b8ef34`).

### A skill `/neuroninhos` não existe como comando ainda

`grep -rn neuroninhos` na central acha o arquivo em 3 lugares (`motor/skills/neuroninhos/SKILL.md`, `neuroninhos/ESTADO.md`, `neuroninhos/HANDOFF.md`) e **em nenhum builder de plugin**. `bin/mb-build-plugin-claude.py` tem uma lista **fixa** de skills a empacotar (linhas ~90–106) e `neuroninhos` não está nela; o mesmo vale pro builder do Codex. Confirmação independente: a lista de skills carregadas nesta sessão não inclui `neuroninhos`. Hoje digitar `/neuroninhos` não carrega nada.

---

## Parte 1 — O que "entrar no harness megabrain" significa de verdade pra um modelo local

### 1.1 Como Claude e Codex entram hoje (4 camadas, lidas em `apps/automations/automations.py`)

1. **Camada de invocação:** um binário de linha de comando (`claude`, `codex`) chamado por `subprocess.run` com flags que **neutralizam o ambiente do usuário** — `--safe-mode --tools "" --strict-mcp-config --mcp-config '{"mcpServers":{}}' --no-session-persistence` no Claude; `--ignore-user-config --ephemeral --sandbox read-only -c approval_policy="never" -c project_doc_max_bytes=0` no Codex. Mais `clean_env()`, que apaga toda variável `ANTHROPIC_*`/`OPENAI_*` pra nunca cair em cobrança por API.
2. **Camada de contrato:** schema JSON obrigatório (`--json-schema` / `--output-schema`) + `validate()` no retorno + fingerprint da etapa.
3. **Camada de contexto/identidade:** o plugin megabrain com as skills. **Aqui está a primeira quebra:** o motor de orquestração **desliga skills de propósito** — `-c skills.include_instructions=false`, `-c features.skip_host_skill_discovery=true`, `--tools ""`. O worker Claude/Codex do `apps/automations` **não recebe skill nenhuma**. O que ele recebe é a constante `SYSTEM` (9 linhas) mais o pacote.
4. **Camada de cota:** `providers.py` lê a cota real → `budget_pacing.py` classifica ritmo (`ok`/`desacelerar`/`pause`/`NAO_MEDIDO`) → `pick_provider()` desempata pelo par (ritmo, `effort` como proxy de capacidade) → `Engine.call()` corta duro em ≥100%.

### 1.2 Onde a analogia se mantém

**Só a camada 2 (contrato de schema) transfere inteira.** E ela transfere bem:

- Ollama: `"format": "json"` garante só sintaxe. Versões recentes aceitam um **objeto de schema** em `format` — isso não foi sondado nesta sessão, fica como [A VERIFICAR] na tarefa N1.
- LM Studio: `response_format` com `json_schema` + `strict`, com sampling restrito por gramática em GGUF. É a garantia **mais forte** dos dois.

A camada 3 também "transfere" — por um motivo desconfortável mas honesto: **como o motor já desliga skills pros workers da nuvem, o modelo local não está em desvantagem nenhuma.** Todos os workers do `apps/automations` são iguais nesse ponto: recebem prompt de sistema + pacote, nada mais. Isso significa que "dar o harness megabrain pro modelo local" **não é dar skill pra ele** — é escrever o prompt de sistema certo pra ele. Ver N6.

### 1.3 Onde a analogia quebra — dizer isso claro

**Quebra 1 — não existe CLI-com-skills, e não faz falta.** Ollama e LM Studio se falam por HTTP. Não há binário pra invocar com flags de contenção. Mas existe um problema **equivalente e pior**: enquanto Claude/Codex herdam ambiente por variável (resolvido por `clean_env()`), o Ollama herda ambiente **pelo servidor**, não pelo request — `OLLAMA_KEEP_ALIVE=30m` e `OLLAMA_MAX_LOADED_MODELS=2` estão setados globalmente na máquina do <USUARIO> e valem pra qualquer chamador. O `clean_env()` do modelo local é **mandar toda opção explícita no corpo do request** — que é exatamente o item 3 da skill stub e a lição já registrada.

Mas com uma ressalva que a skill stub ainda não tem e que é a correção mais importante deste plano — ver 1.5.

**Quebra 2 — não existe cota externa; existe VRAM.** Não há endpoint de saldo, não há janela de 5 h, não há reset semanal. Traduções honestas:

| Conceito do harness | Equivalente local honesto | Como se mede |
|---|---|---|
| `used_percent` da janela | modelo residente ocupa quanto da VRAM | `ollama ps` (coluna SIZE + PROCESSOR) |
| limite da janela | `OLLAMA_MAX_LOADED_MODELS=2`; auto-evict do LM Studio = 1 | `env`; doc LM Studio |
| `resets_at` | `keep_alive` / `ttl` | request ou global |
| `status: pause` (cota estourada) | servidor fora do ar, ou modelo ausente, ou VRAM insuficiente | `GET /api/tags`, `GET /v1/models` |
| custo por token | latência + contenção com Photoshop/Illustrator na mesma 4070 | tok/s medido |

O `local_worker.py` da sessão paralela já acertou isso: devolve `windows: []` e usa `status` como sinal de **disponibilidade**, nunca inventando 0% de uso. Está certo, é o desenho correto, e este plano não o refaz.

**Quebra 3 — `effort` não existe, e usar ele como proxy é gambiarra com efeito colateral certo.** `pick_provider()` desempata por `_EFFORT_RANK` (`low`=0 … `max`=4). A config da worktree paralela põe `"effort": "low"` no bloco `ollama`. Consequência mecânica: na sensibilidade `equilibrado` (padrão) e na `capaz`, **o Ollama perde sempre** pra qualquer candidato de effort maior enquanto esse candidato não estiver `desacelerar`/`pause`. O comportamento resultante ("local só entra quando a nuvem apertou") provavelmente é o desejado — mas ele sai de um campo que significa outra coisa. Decisão explícita necessária: ou (a) manter `effort:"low"` e **documentar** que ali ele é "rank de capacidade", ou (b) dar ao provider local um campo próprio (`capability_rank`) e ensinar `pick_provider` a lê-lo. Recomendo (a) por agora — mudança zero em `pick_provider`, e o efeito é o certo.

**Quebra 4 — paralelismo é ilusório.** `max_workers` do motor vai até 4. Um servidor Ollama com `MAX_LOADED_MODELS=2` **serializa**. Despachar 3 etapas em paralelo pro local não dá 3× — dá fila, e no pior caso dá troca de modelo (recarga de 17–23 GB). O template precisa expor "quantas chamadas locais simultâneas" como limite próprio, e o padrão honesto é **1**.

### 1.4 Definição operacional proposta

> **"Entrar no harness megabrain", para um modelo local, significa:** ser chamável pela mesma função de despacho que Claude/Codex, sob o mesmo envelope `{system, schema, input}`, devolvendo JSON validado pelo mesmo `validate()`, com **disponibilidade medida por sonda real** entrando no mesmo `pick_provider()` — e com um orçamento próprio que é de **VRAM e latência**, não de cota.
>
> **Não significa:** ter skills, ter plugin, ter cota, ou substituir Claude/Codex em etapa de plano/candidato/revisão.

### 1.5 A correção mais importante em cima do que já existe

`local_worker.py` (worktree `exciting-satoshi-93280f`, função `call`) manda **sempre** `options.num_ctx` explícito e `keep_alive: "60s"`. O docstring cita corretamente a lição de nunca herdar contexto global. **Mas a lição 260825 tem uma segunda metade que o código não reflete:**

> "em modelo grande, **OMITIR `num_ctx`** na requisição e deixar o que já está carregado, ou fixar o mesmo valor do preset em todos os chamadores. Antes de disparar lote de teste, conferir `ollama ps` e casar o CONTEXT."

O incidente real: o `qwen-deep` (23 GB) estava residente com ctx 16384; um request com `num_ctx: 8192` forçou descarregar/recarregar 23 GB com o modelo em uso → `llama-server` em "Stopping..." com GPU a 100%, 3870 s de CPU acumulado, requests seguintes estourando timeout de 300 s. **Só reinício de serviço resolveu.**

As duas metades não se contradizem — elas se aplicam a regimes diferentes:

- **Modelo pequeno e não residente** (`llama3.1:latest`, 4,9 GB): mandar `num_ctx` explícito é **correto e seguro**. Recarga é barata. A escolha da sessão paralela está certa **para o modelo que ela configurou**.
- **Modelo grande e/ou já residente** (17–23 GB): mandar `num_ctx` diferente do residente é **a receita exata do deadlock**. Ali a regra é: ler `ollama ps` primeiro; se residente, **casar o CONTEXT ou omitir**; só mandar valor explícito se não estiver carregado.

Portanto a regra do template não é "sempre explícito" nem "sempre omitir" — é **condicional à residência**, e a sonda de residência é obrigatória antes do despacho. Mesma coisa pro `keep_alive`: o global do <USUARIO> é `30m`; mandar `60s` num modelo de 23 GB **encurta a janela de segurança** que a própria lição diz reduzir a chance de deadlock. Em modelo grande, `keep_alive` do request nunca deve ser menor que o global.

Corolário operacional (lição 260830): qualquer rotina que reinicie o Ollama pra aplicar env var precisa matar `llama-server.exe` além de `ollama`/`ollama app`, e conferir `Get-Process -Name "llama-server"` vazio antes de medir — órfão segurando contexto CUDA já fez medição parecer regressão de flag.

---

## Parte 2 — Desenho do template portável (`neuroninhos/template/`)

### 2.1 Princípios

1. **Stdlib puro** — mesma restrição do `automations.py`. Sem `requests`, sem SDK. `urllib.request` + `json` bastam pros dois runtimes.
2. **Um contrato, dois runtimes** — o chamador nunca escreve `if ollama … else lmstudio`. Adaptador por runtime, interface única.
3. **Sonda real, nunca proxy inventado** (lição 260825): saúde é `GET /api/tags` (Ollama) e `GET /v1/models` (LM Studio) — a operação mais barata da API de verdade. **Checar porta aberta não é health check**: dá o mesmo valor com servidor sadio e com modelo ausente.
4. **Nada de estado pessoal dentro do template** — caminho de modelo, nome de máquina e pasta de projeto ficam no `neuroninhos.json` do destino, nunca no código (lição 260816 sobre varrer disco / gravar caminho pessoal).
5. **Toda pasta criada em runtime entra no EXCLUIR do `bin/mb-generate-template.py` no dia em que nasce** (lição 260819) — vale pra `medicoes/` da tarefa N8.
6. **Degradação honesta** — falha de sonda vira `status`, nunca exceção que derruba o ciclo, e nunca `0%` inventado.

### 2.2 Árvore de arquivos proposta

```
neuroninhos/template/
├── README.md                  # o que é, o que assume, como instalar, o que NÃO faz
├── neuroninhos.json           # config do destino (a única coisa que muda por máquina)
├── neuroninhos.schema.json    # schema do acima; validado no load, igual load_config()
├── detectar.py                # sonda: instalado? de pé? quais modelos? o que está residente?
├── cliente.py                 # despacho único, os dois runtimes, com a guarda de residência
├── medir.py                   # benchmark: tok/s + split CPU/GPU por candidato (lição 260825)
├── instalar.cmd               # copia o template pro projeto destino e registra a config
├── perfis/
│   ├── classificador.md       # prompt de sistema + schema: rótulo fechado
│   ├── micro.md               # resumo/extração curta
│   └── rotina.md              # tarefa repetitiva com formato fixo
└── testes/
    ├── test_detectar.py
    └── test_cliente.py
```

### 2.3 `neuroninhos.json` — a config

Formato proposto (valores abaixo são os **medidos hoje** na máquina do <USUARIO>, não chutes; num outro destino o `instalar.cmd` regrava a partir do `detectar.py`):

```json
{
  "versao": 1,
  "runtimes": {
    "ollama": {
      "ativo": true,
      "url": "http://127.0.0.1:11434",
      "modelo": "llama3.1:latest",
      "modelo_fallback": null,
      "context_tokens": 8192,
      "max_output_tokens": 512,
      "keep_alive": "30m",
      "health_timeout_seconds": 3,
      "dispatch_timeout_seconds": 45,
      "limite_gb_sem_confirmacao": 12
    },
    "lmstudio": {
      "ativo": false,
      "url": "http://127.0.0.1:1234/v1",
      "modelo": "google/gemma-4-e4b",
      "ttl_seconds": 1800,
      "context_tokens": 8192,
      "max_output_tokens": 512,
      "health_timeout_seconds": 3,
      "dispatch_timeout_seconds": 60,
      "iniciar_servidor_automaticamente": false
    }
  },
  "chamadas_simultaneas": 1,
  "perfil_padrao": "micro",
  "registrar_medicoes": true
}
```

Campos que merecem justificativa:

- `keep_alive: "30m"` — **casa com o global do <USUARIO>**, em vez de brigar com ele (ver 1.5). Se a máquina destino não tiver global, 30m continua sendo um padrão são.
- `limite_gb_sem_confirmacao: 12` — a 4070 tem 12 GB. Modelo acima disso **vai** fazer offload pra CPU. O template não deve carregar um modelo desses sem alguém ter pedido explicitamente. (Não é o mesmo que proibir: a lição 260825 mostra que MoE grande com offload bate denso médio — a regra é *não fazer sozinho*, não *nunca fazer*.)
- `iniciar_servidor_automaticamente: false` — o servidor do LM Studio está OFF hoje. Ligar servidor é mudança de estado de máquina; padrão é não fazer.
- `chamadas_simultaneas: 1` — ver Quebra 4.

### 2.4 `detectar.py` — contrato de saída

Uma função por runtime, mesma forma de retorno, compatível com o que `Quotas.snapshot()` devolve (pra encaixar em `pick_provider` sem tradução):

```python
{
  "provider": "ollama" | "lmstudio",
  "status": "ok" | "pause",          # nunca NAO_MEDIDO: falha de sonda é pause conhecido
  "windows": [],                      # sempre vazio: não há cota externa
  "fetched_at": "<iso8601>",
  "reason": None | "servidor_fora" | "modelo_ausente" | "cli_ausente",
  "local": {                          # extensão específica de modelo local
    "instalado": bool,                # binário existe no PATH
    "servidor_de_pe": bool,
    "modelos": ["nome", ...],
    "residente": [{"nome":…, "size":…, "processor":…, "context": int}],
    "vram_livre_estimada_gb": float | None
  }
}
```

Detecção por runtime, em ordem (barato → caro), tudo read-only:

| Passo | Ollama | LM Studio |
|---|---|---|
| instalado? | `shutil.which("ollama")` | `shutil.which("lms")` ou `~/.lmstudio/bin/lms` |
| servidor de pé? | `GET {url}/api/tags` | `GET {url}/models` |
| modelos | corpo do `/api/tags` (`models[].name`) | corpo do `/v1/models` (`data[].id`) |
| residência | `ollama ps` (texto) ou `GET /api/ps` (JSON, preferir) | `lms ps` |
| contexto residente | coluna CONTEXT do `ps` | `lms ps` |

Comparação de nome de modelo: igual ao que `pets/backend/integrations.py:probe_local` já faz — nome exato **ou** base antes do `:`. O `local_worker.py` da sessão paralela já replicou isso; o template deve usar a mesma regra pra os três concordarem.

### 2.5 `cliente.py` — despacho

Interface única: `call(config, runtime, envelope, folder=None)` onde `envelope = {"system":…, "schema":…, "input":…}` — **o mesmo envelope que `Engine.call()` já monta**. Retorna `(valor, telemetria)`, mesma forma que `parse_response()`.

**Ollama** → `POST {url}/api/chat`

```jsonc
{
  "model": "<modelo>",
  "messages": [{"role":"system","content":"<system>"},
               {"role":"user","content":"<json de {schema,input}>"}],
  "format": "json",              // ou o objeto de schema, se N1 confirmar suporte
  "stream": false,
  "keep_alive": "30m",
  "options": { "num_predict": 512 /* , "num_ctx": … CONDICIONAL — ver abaixo */ }
}
```

**Guarda de residência (o ponto novo deste plano):** antes de montar `options`, chamar a sonda de residência.

1. Modelo **não residente** e tamanho `< limite_gb_sem_confirmacao` → mandar `num_ctx` explícito da config. Seguro.
2. Modelo **residente** → ler o CONTEXT residente. Se igual ao configurado, mandar (inofensivo). Se diferente, **omitir `num_ctx`** e registrar um aviso na telemetria (`"num_ctx_omitido": {"configurado": 8192, "residente": 16384}`). Nunca forçar a troca.
3. Modelo **não residente** e tamanho `>= limite` → **não despachar sozinho**; devolver `status: pause`, `reason: "modelo_grande_sem_confirmacao"`. Quem quiser força passa flag explícita.
4. `keep_alive` do request nunca menor que o global `OLLAMA_KEEP_ALIVE`, quando ele existir.

**LM Studio** → `POST {url}/chat/completions`

```jsonc
{
  "model": "google/gemma-4-e4b",
  "messages": [ /* idem */ ],
  "response_format": {"type":"json_schema",
    "json_schema":{"name":"contrato","strict":"true","schema": /* o schema do envelope */ }},
  "stream": false,
  "ttl": 1800,
  "max_tokens": 512
}
```

Assimetrias que o adaptador precisa absorver (todas confirmadas na doc oficial hoje):

1. **Contexto não é parâmetro de request no LM Studio.** É de carga (`lms load -c N`). Se o `context_tokens` da config não bate com o que está carregado, o cliente **não pode corrigir pelo request** — só pode avisar. Opção: o `instalar.cmd` documenta o `lms load -c` correspondente; o `detectar.py` reporta divergência.
2. **`ttl` em segundos e no corpo do request**, contra `keep_alive` em string (`"30m"`) no Ollama. O `neuroninhos.json` guarda os dois em unidades naturais de cada um; nada de "unidade unificada" que ninguém consegue ler.
3. **JIT + auto-evict:** pedir um modelo não carregado **carrega ele sozinho** e, por padrão, **descarrega o anterior**. Isso é a diferença de comportamento mais perigosa vs Ollama (`MAX_LOADED_MODELS=2`): no LM Studio, mandar duas tarefas com modelos diferentes força evict-e-recarrega em série. `chamadas_simultaneas: 1` já cobre; documentar mesmo assim.
4. **Saída estruturada vem como string** em `choices[0].message.content` e precisa de `json.loads`. No Ollama vem em `message.content`, também string. Mesmo tratamento, campos diferentes.
5. **Doc avisa que modelo < 7 B costuma não sustentar schema.** O `gemma-4-e4b` tem 7,5 B — em cima da linha. Só medição resolve (N1).
6. **Sem API key**, mas o servidor escuta em localhost. Não expor a porta pra fora; não é área deste plano, mas vale a linha.

Reforço da lição 260819: modelo pequeno/quantizado **ecoa o formato** em vez de responder (o qwen 2-bit devolveu `DESVIO|<1 frase de motivo>` literal). Por isso o parse tem que **recusar** o que não bate o schema, nunca "interpretar". `validate()` do motor já faz isso — o cliente só não pode adivinhar nada antes dele.

### 2.6 `medir.py` — a sonda de 5 minutos

Implementação direta do atalho da lição 260825, que é o que impede "otimizar" o parâmetro errado:

1. Mesmo prompt curto pra cada candidato de `neuroninhos.json`.
2. Registra tok/s, `ollama ps` (split CPU/GPU e CONTEXT), e tempo até o primeiro token.
3. `GET /api/show` por modelo: presença de `*.expert_used_count` denuncia MoE.
4. `ollama show --modelfile` → hash do `FROM` pra agrupar presets que são **o mesmo peso com nome diferente** (na máquina dele, 13 nomes provavelmente são bem menos blobs — os 23 GB repetidos são suspeitos).
5. Antes de medir: `Get-Process -Name "llama-server"` tem que voltar vazio depois de qualquer reinício (lição 260830), senão a medição mente.

Saída: `neuroninhos/medicoes/<data>_sonda.json`. É **isto** que escolhe o modelo padrão — não este documento.

### 2.7 `instalar.cmd` — o que torna o template "templatezável"

O megabrain já tem dois mecanismos de propagação: `01_acoes/04_novo-projeto.cmd` (scaffold de projeto novo, copia núcleo pra `<destino>\MEGABRAIN\`) e `bin/mb-generate-template.py` (export público sanitizado). O `instalar.cmd` deve **seguir o mesmo formato**, não inventar um terceiro:

1. Recebe pasta destino (ou usa a atual).
2. Roda `detectar.py` **antes de escrever qualquer coisa** — se nenhum runtime estiver instalado, para e diz isso, sem criar arquivo.
3. Copia `cliente.py`, `detectar.py`, `perfis/`, `neuroninhos.schema.json` pra `<destino>/neuroninhos/`.
4. **Gera** o `neuroninhos.json` a partir do que detectou (não copia um pronto com valores da máquina do <USUARIO>).
5. Cria `ESTADO.md`/`HANDOFF.md`/`DECISOES.md` do destino, convenção megabrain.
6. Imprime o que ficou faltando (ex.: "LM Studio instalado mas servidor OFF — rode `lms server start`").

Passo 4 é o que atende "templatezar a quaisquer locais" de verdade: o mesmo pacote em máquina diferente gera config diferente porque **mediu** a máquina, em vez de carregar o setup de uma.

---

## Parte 3 — Como isto se conecta à task paralela (sem refazer)

### 3.1 Divisão de escopo

| | Este plano (guarda-chuva) | `task_ca62646b` (worktree `exciting-satoshi-93280f`) |
|---|---|---|
| Pergunta | O que é um modelo local dentro do megabrain, e como isso vira template portável | Como o Ollama entra em `pick_provider`/`resolve_role_provider` do motor |
| Entrega | `neuroninhos/template/` + sequência de tarefas | `apps/automations/local_worker.py` + config + testes |
| Alcance | Qualquer projeto/máquina, os dois runtimes | Um ponto de integração, um runtime |

A worktree paralela **já resolveu bem** o adaptador Ollama pro motor: `health()` no formato de `Quotas.snapshot()`, `windows: []`, `status` como disponibilidade, `format:"json"`, `num_ctx`/`num_predict`/`keep_alive` explícitos, dump de payload/resposta na pasta da etapa. **Este plano não reescreve nada disso.** O que ele adiciona são três coisas que aquela sessão não tinha como saber:

1. **A guarda de residência** (1.5 / 2.5) — só vira necessária quando alguém apontar a config pro `qwen-deep`. Com `llama3.1` está seguro.
2. **O LM Studio** — fora do escopo dela por completo.
3. **A reconciliação** — abaixo.

### 3.2 O problema de reconciliação (bloqueia tudo)

As duas worktrees nasceram de `f9a8ac0`. A árvore principal tem, **não commitado**, todo o governor de cota da entrada 260909g (`class Quotas` com pacing, `pick_provider`, `resolve_role_provider`, `write_budget_status`, `role-choices.json`). Consequências concretas:

1. **A sessão do Ollama-como-worker está desenhando contra um arquivo onde `pick_provider` e `resolve_role_provider` não existem.** Não é erro dela — é o que estava no commit base. Mas o encaixe que ela produzir vai precisar de refit real, não de merge automático.
2. **`memoria/estado/DECISOES.md` 260909h diz que o `parse_response` foi corrigido e VERIFICADO (27/27 testes, replay do stdout real).** O código corrigido está na worktree `silly-cartwright-33a986`, **não na árvore principal** (`apps/automations/automations.py:341` ainda tem `if any(e.get("type") in ("error","turn.failed") for e in events)`). É a lição 260818 acontecendo agora: *entrega de outro agente é rascunho até estar materializado no disco* — e aqui a decisão já foi escrita como pronta.
3. **As duas worktrees editam o mesmo arquivo.** Merge dos dois de volta na principal (que também mexeu nele) = conflito em três vias. Lição 260826: coordenar **antes** de escrever, não depois.

**Ordem de merge recomendada** (menor conflito primeiro): principal (já está) → `silly-cartwright` (mudança pequena e cirúrgica no `parse_response`, ~4 linhas) → `exciting-satoshi` (arquivo novo `local_worker.py` + config + um ponto de encaixe). Rodar `apps/automations/tests` inteiro depois de cada passo, não só no fim.

### 3.3 O que este plano *não* decide

Se o Ollama deve ser candidato **em `pick_provider`** (escolha automática) ou só um provider chamável **explicitamente** por papel: isso é a Pergunta 3 da Parte 5. A implementação dos dois caminhos é a mesma até o último passo, então a decisão pode esperar até N5 sem custo.

---

## Parte 4 — "Workers pra fazer isso" e "melhorar conforme o uso": tarefas sequenciadas

Cada item abaixo é pegável sozinho por um agente futuro: tem entrada, saída e critério de aceite. **Nenhuma foi executada nem despachada** — execução é decisão do <USUARIO> com a sessão que me chamou.

### N0 — Reconciliar as três cópias de `automations.py` · **BLOQUEIO**
- **Entrada:** árvore principal + as 2 worktrees (Parte 0, tabela).
- **Fazer:** decidir com o <USUARIO> o destino de cada worktree; merge na ordem de 3.2; rodar `apps/automations/tests` completo após cada merge.
- **Aceite:** uma só cópia de `automations.py`; `parse_response` com o critério posicional; suíte verde; `git status` sem worktree pendente.
- **Por que primeiro:** qualquer código escrito antes disso nasce em cima de uma base que vai mudar.
- **Não é tarefa Neuroninhos** — é dívida da sessão principal. Mas bloqueia N5.

### N1 — Sonda de realidade dos modelos locais · ~30 min, sem alterar código
- **Fazer:** rodar o procedimento de `medir.py` (2.6) manualmente sobre os 13 modelos Ollama; agrupar por blob; identificar MoE. **Separadamente:** com autorização do <USUARIO>, `lms server start`, `GET /v1/models`, e uma chamada de teste ao `gemma-4-e4b` com `response_format` de schema real.
- **Aceite:** `neuroninhos/medicoes/260909_sonda.json` (ou data do dia) com tok/s, split CPU/GPU, contexto e MoE por candidato; veredito registrado sobre (a) se o Ollama 0.33.3 aceita objeto de schema em `format`, (b) se o `gemma-4-e4b` sustenta `strict` json_schema.
- **Por que antes de N2/N3:** os defaults do template saem daqui. Sem isso, `llama3.1:latest` é herança do Pets, não escolha medida.

### N2 — `template/detectar.py` + testes · isolado, não toca em nada existente
- **Aceite:** roda fora do repo; devolve o contrato de 2.4 pros dois runtimes; testes cobrem servidor fora, modelo ausente, CLI ausente e caminho feliz com resposta HTTP dublada; nenhuma exceção escapa.

### N3 — `template/cliente.py` + testes · depende de N1 (defaults) e N2 (sonda)
- **Aceite:** os 4 casos da guarda de residência (2.5) testados; adaptador LM Studio monta `response_format`/`ttl` corretos; parse recusa resposta fora do schema em vez de interpretar; telemetria registra `num_ctx_omitido` quando ocorre.

### N4 — Distribuir a skill `/neuroninhos` · pequena, mecânica, independente das outras
- **Fazer:** incluir `skills/neuroninhos/SKILL.md` nas listas de `bin/mb-build-plugin-claude.py` e `bin/mb-build-plugin-codex.py`, e nos testes `motor/tests/test_mb_build_plugin_*.py`. Atenção ao limite de 500 chars da `description` do manifesto (lição 260827).
- **Aceite:** builder gera plugin com a skill dentro; teste novo reprova se ela sumir; `/neuroninhos` carrega em sessão nova.
- **Nota:** hoje a skill existe só como fonte — verificado, não deduzido (Parte 0).

### N5 — Encaixar Ollama no motor · **depende de N0**
- **Fazer:** trazer `local_worker.py` da worktree pra árvore reconciliada; refit contra o `pick_provider`/`resolve_role_provider` reais; aplicar a guarda de residência de N3; resolver a Quebra 3 (`effort` vs `capability_rank`) conforme decisão da Parte 5.
- **Aceite:** suíte de `apps/automations` verde; um despacho real de etapa `probe` pro Ollama, com `events.jsonl` mostrando `before_dispatch` com o snapshot local; `Engine.call()` **não** corta por cota (não há janela) mas **corta** por `status: pause`.

### N6 — `template/perfis/` — a substituição honesta das skills · independente de N5
- **Fazer:** 3 perfis (`classificador`, `micro`, `rotina`), cada um = prompt de sistema curto + schema + **1 caso de aceite com entrada real gravada**. Base: a constante `SYSTEM` do motor, encurtada — modelo pequeno se perde em instrução longa.
- **Aceite:** cada perfil passa seu caso com o modelo padrão medido em N1; `classificador` **recusa** a entrada em que o modelo 2-bit ecoou o formato (lição 260819) em vez de gravar veredito falso.
- **Por que isso é "o harness":** ver 1.2 — nenhum worker do motor recebe skill; o que ele recebe é prompt de sistema. Perfil é a unidade certa.

### N7 — `template/instalar.cmd` + `neuroninhos.schema.json` · depende de N2, N3, N6
- **Aceite:** instalar numa pasta vazia de teste gera `neuroninhos.json` **derivado da detecção** (não copiado); recusa instalar quando nenhum runtime existe; imprime pendências; `neuroninhos/medicoes/` entra no EXCLUIR do `bin/mb-generate-template.py` no mesmo commit (lição 260819).

### N8 — O laço de melhoria contínua ("filhos que melhoram com o uso") · depende de N3
- **Fazer:** todo despacho local grava uma linha em `neuroninhos/medicoes/<AAMMDD>.jsonl`: runtime, modelo, perfil, tokens in/out, tok/s, se o schema validou de primeira, se a revisão aprovou, e `num_ctx_omitido`. Mais um `relatorio.py` que agrega: taxa de schema válido por perfil/modelo, latência mediana, quantas vezes o modelo grande foi recusado por VRAM.
- **Aceite:** 20 despachos reais produzem um relatório com pelo menos uma recomendação acionável (trocar modelo padrão de um perfil, ou encurtar um prompt).
- **Fundamento:** lição 260816 — *"heurísticas iniciais ajudam, mas erram em nuances do usuário. Sem registrar o que funcionou, o ajuste vira tentativa e erro."* Este é o único item que faz "melhorar conforme o uso" significar algo verificável em vez de intenção.

### N9 — Runtimes locais no widget de cotas · opcional, por último
- **Fazer:** um tile no `apps/ia-quota-widget` mostrando servidor de pé / modelo residente / contexto — **sem porcentagem de cota**, porque não existe.
- **Aceite:** o tile mostra "sem cota externa" explicitamente e nunca renderiza 0% ou 100%; `providers.py::_FETCHERS` ganha as entradas locais sem quebrar o poll dos outros 5.
- **Cuidado:** `fetch_provider` promete nunca levantar exceção (o poll dos outros cinco depende disso). Adaptador local tem que honrar o mesmo contrato.

**Ordem sugerida:** N0 → N1 → (N2, N4 em paralelo) → N3 → N6 → N5 → N7 → N8 → N9.
**Caminho mínimo pra ter algo útil rodando:** N1 → N2 → N3 → N6. Isso já dá um cliente local usável em qualquer projeto, sem tocar no motor.

---

## Parte 5 — Perguntas que dependem do <USUARIO>

1. **LM Studio entra ou fica de fora nesta rodada?** O servidor está OFF, e dos 3 modelos instalados só o `gemma-4-e4b` (7,5 B) é LLM de texto — os outros dois são um modelo de localização em imagem e um de embedding. O Ollama já tem 13 modelos e está de pé. Fazer os dois dobra o trabalho de N2/N3 por um ganho que hoje é 1 modelo. **Sugestão:** desenhar o template pros dois (a interface já está pronta acima), implementar Ollama primeiro e deixar o adaptador LM Studio atrás de `"ativo": false` até ele dizer que quer.
2. **Posso ligar o servidor do LM Studio pra medir?** `lms server start` carrega modelo na VRAM e muda o estado da máquina. Não fiz. Sem isso, tudo que este plano diz sobre LM Studio vem da doc oficial, não de medição na máquina dele.
3. **Modelo local roda automático ou só sob pedido?** Se entrar como candidato em `pick_provider`, o motor pode escolher local sozinho no meio de uma orquestração — e se o modelo escolhido for grande, isso trava a GPU no meio de trabalho de Photoshop/Illustrator. **Sugestão:** começar explícito (papel configurado como `"ollama"` à mão), e só depois de N8 ter dado dados considerar `"auto"`.
4. **Qual modelo padrão?** `llama3.1:latest` (4,9 GB, cabe folgado na 4070) é o que o Pets usa e o que a sessão paralela configurou. Os `qwen-*` de 17–23 GB são mais capazes mas fazem offload pra CPU. Só a sonda N1 responde de verdade — mas ele pode ter preferência de idioma (vários presets dele são `-ptbr`/`-br`).
5. **Conflito de `keep_alive`:** o global dele é `OLLAMA_KEEP_ALIVE=30m`; o código da sessão paralela manda `60s` por request, o que sobrescreve. Qual manda por política — a config dele ou a do harness? Este plano assume **a dele** (30m no `neuroninhos.json`).
6. **A skill `/neuroninhos` vai pros três harnesses (Claude, Codex, Kimi) ou só Claude?** N4 muda conforme.

---

## Parte 6 — Confiança e incertezas

**Alta confiança — medido nesta sessão, com o comando registrado na Parte 0:**
- Estado do Ollama (versão, porta, 13 modelos, residência, as duas env vars globais).
- Estado do LM Studio (CLI funciona, servidor OFF, porta 1234 sem listener, 3 modelos e quais são).
- As três cópias divergentes de `automations.py` e exatamente quais símbolos cada uma tem.
- `parse_response` corrigido existe só na worktree, não na principal, apesar de 260909h dizer VERIFICADO.
- A skill `neuroninhos` não está em nenhum builder de plugin nem carrega como comando.
- Superfície da API do LM Studio (endpoints, `response_format`/`json_schema`/`strict`, `ttl` em segundos, padrão 3600 s, JIT + auto-evict ligado, contexto só na carga) — **da documentação oficial buscada hoje**, não de memória.

**Confiança média — raciocínio em cima de evidência, não medição direta:**
- A guarda de residência (1.5): a lição 260825 é evidência forte de um incidente real, mas eu **não reproduzi** o deadlock nesta sessão, e não medi onde exatamente fica o limiar de tamanho. O `limite_gb_sem_confirmacao: 12` sai da VRAM da placa, não de teste.
- A previsão de que `effort:"low"` faz o Ollama sempre perder em `equilibrado`/`capaz`: li o código de `pick_provider` e é o que a ordenação diz, mas **não rodei** o caso.
- Que os 13 nomes do Ollama sejam bem menos blobs distintos: padrão de tamanhos repetidos (23 GB ×5, 17 GB ×3, 9,9 GB ×2) mais o precedente da lição 260825. **Hipótese**, resolve em N1.

**Não verificado — dito como não verificado:**
- Se o Ollama 0.33.3 aceita objeto de schema em `format` (quase certo pela versão, **não sondado**).
- Se o `gemma-4-e4b` sustenta `json_schema` com `strict` — está em 7,5 B, logo acima da linha que a própria doc dá como problemática.
- Throughput de qualquer coisa no LM Studio na máquina dele. Zero medição.
- Se `local_worker.py` da worktree passa nos próprios testes — não rodei, é worktree de outra sessão, e rodar lá seria mexer no trabalho dela.
- Quanto de degradação o Photoshop/Illustrator sofre com um worker local ativo. É o custo real do projeto e ninguém mediu.

**O que este documento não é:** não é código, não é medição de desempenho, e não é autorização pra nada. Nada aqui foi implementado; nenhuma tarefa foi despachada. `apps/automations/automations.py` não foi tocado por mim — só lido.
