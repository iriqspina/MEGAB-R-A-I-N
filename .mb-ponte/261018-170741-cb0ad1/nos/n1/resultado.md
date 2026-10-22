# Nó n1 · Revisão independente da ponte · resultado

Revisor: GLM/ZCode (sessão ponte, ordem 261018-170741-cb0ad1). Papel: revisor, somente leitura — este `resultado.md` é a única escrita.

## TL;DR

Nenhum defeito grave comprovado. A ponte está bem construída nos pontos críticos pedidos (autenticação, injeção, instância de prova, caminhos). Encontrei **8 achados médios e 11 menores**, sendo os mais importantes: (1) janela de corrida na fila que pode abrir **duas ordens no mesmo projeto ao mesmo tempo** — agravada pela mudança de hoje que lançou o supervisor via WMI (até 60 s entre reivindicar o lote e indexar a ordem); (2) lote pode ficar travado "Na fila" para sempre se o servidor morrer no meio do lançamento; (3) comentário **complemento nunca recebe o status final** ("Juntado à ordem em andamento" fica eterno); (4) ambiente do filho não cobre todas as chaves de API (GEMINI_/GOOGLE_/AWS…; `CLAUDE_CODE_MESSAGING_TOKEN` existe de fato nesta máquina e passa); (5) a rota `bridge/send` agora pode travar o event loop até 60 s (powershell/WMI na rota async); (6) a suíte completa está **vermelha (2 falhas)** por mudanças de hoje fora dos arquivos da ponte. A suíte da ponte em si: **19/19 verde**.

⚠️ O código continuou mudando durante a revisão (outra sessão do Claude ativa): `central_bridge.py` 17:04→17:12, `BridgePanel.tsx` →17:09, `central_server.py` →17:17, `ReportFrame.tsx`/`bridge.css` →17:19, `central_returns.py` 17:14, `central_reports.py` **17:27**. Esta revisão reflete o estado de ~17:30 de 18/10/2026; itens podem ter sido corrigidos depois.

## O que foi revisado (arquivos)

1. `apps/megabrain-dashboard/central_bridge.py` (novo, versão 17:12 — inclui a mecânica `_fora_da_sessao`/WMI e `supervisor.json` que não existiam às 17:04).
2. `bin/mb-ponte.py` (16:57, sem mudança durante a revisão).
3. `apps/megabrain-dashboard/central_server.py` (17:17) vs `evidence/261018_ponte-orquestradores/backup/central_server.py` (16:45).
4. `apps/megabrain-dashboard/central_store.py` — método `patch` (16:57) vs backup.
5. `web/src/BridgePanel.tsx` (17:09, novo), `bridge.css` (17:19, novo), `ReportFrame.tsx` (17:19) vs backups.
6. `tests/test_central_bridge.py` (17:12 — ganhou `test_background_launch_...` durante a revisão).
7. Toque rápido (apareceu no meio da revisão, fora do escopo da ordem): `central_attachments.py` (17:20, anexos de imagem nos comentários que alimentam a ponte) — não auditado a fundo.

## Como verificou

1. Leitura integral dos arquivos + `diff -u` contra os backups de `evidence/261018_ponte-orquestradores/backup/`.
2. Suíte da ponte: `python -m unittest test_central_bridge` → **19/19 OK** (5,3 s).
3. Suíte completa da central: `unittest discover` → **308 testes, 2 falhas, 3 skips**; as 2 falhas isoladas e rastreadas até a origem (ver achado M6).
4. Smoke real: `python bin/mb-ponte.py vendors` → claude/gpt/glm ativos, gemini inativo ("Não está entre as assinaturas registradas") — bate com `dados/orcamento_ia.json` real (chaves `claude`, `codex`, `zai`, `gemini_cli` ausente) e com `shutil.which` desta máquina (`claude.EXE`, `codex.EXE` nativos; `zcode.CMD`, `gemini.CMD` via npm).
5. Prova empírica de subprocess: `Popen` de `.CMD` inexistente com args contendo `& | %` no Python 3.14.6 → `FileNotFoundError` **sem** `ValueError` (não há validação de caracteres em args de batch nesta versão — testado, não presumido).
6. `zcode.CMD` lido: usa `%dp0%`, não `$basedir` → a mitigação `_npm_entrada` nunca dispara no Windows (achado m1).
7. `.gitignore`: `git check-ignore` exit 1 e `git status` mostra `?? .mb-ponte/` (achado M7).
8. Ambiente: única variável sensível presente agora é `CLAUDE_CODE_MESSAGING_TOKEN`, que **não** é removida por `ambiente()` (achado M4).
9. `isolated_server.py`: `MB_ISOLATED=1` no spawn + whitelist `COPY_ONLY` + `test_isolated_server.py:43` lista `bridge/send` e `orders/stop` como bloqueados — tripla defesa da instância de prova, confirmada por teste.

## Achados — médio

**M1 · Corrida na fila pode abrir duas ordens no mesmo projeto** — `central_bridge.py:948-983` (tick) vs `:866-907` (receber). `tick` reivindica o lote e chama `_abrir` **sem** checar `_ordem_ativa`; `_ordem_ativa` só é consultada em `receber`. Cenário: lote entra em `estado='lancando'`; comentário C chega → como o lote não está mais `aguardando`, C inicia um **novo** lote; a ordem 1 só entra no índice depois de `_abrir` terminar — que hoje inclui `_fora_da_sessao` (powershell/WMI, timeout 60 s) → janela de até ~1 min; 60 s depois o tick abre a **ordem 2** com C enquanto a 1ª está `na_fila/em_andamento` → dois planejadores simultâneos no mesmo projeto (as próprias regras de ordem avisam sobre sessões paralelas). Antes do WMI a janela era de milissegundos; a mudança de hoje a ampliou muito. Correção sugerida: `tick` checar `_ordem_ativa(pid)` antes de `_abrir` e virar complemento (ou re-agendar o lote). Lógica confirmada por leitura; não reproduzida em execução.

**M2 · Lote travado em `lancando` sem recuperação** — `central_bridge.py:956-982`. Se o processo morrer (crash, energia, kill) entre a reivindicação (`estado='lancando'`) e o put final (`'lancado'`), o lote fica preso: `tick` pula tudo que não é `aguardando`, ninguém relança, e os comentários ficam com o rótulo "Na fila da ponte" para sempre. O `except Conflict` silencioso do put final tem o mesmo efeito. Falta um timeout/expiração para lote `lancando`.

**M3 · Complemento nunca recebe status final** — `central_bridge.py:885-888` grava o complemento em `complementos.jsonl` e marca o comentário "Juntado à ordem em andamento ({v})", mas `reconciliar` (`:1005-1006`) só atualiza os ids em `o['comentarios']` do índice — que contêm apenas os comentários originais de `_abrir` (`:939`). Com a ordem concluída, o complemento continua dizendo "em andamento": rótulo que mente ao <USUARIO>. Correção: incluir o id do complemento no índice (ou reconciliar também os ids de `complementos.jsonl`).

**M4 · Ambiente do filho vaza classes de segredo fora da lista** — `central_bridge.py:53-55, 227-228`. `_SEM_API = ('ANTHROPIC_','OPENAI_','ZAI_')` + `_SESSAO` não cobrem `GEMINI_API_KEY`, `GOOGLE_*`, `ZHIPUAI_*`, credenciais AWS (Bedrock: `CLAUDE_CODE_USE_BEDROCK` é removida, mas `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` não), `GH_TOKEN` etc. O docstring promete "chaves de API saem do ambiente... nunca API paga" — hoje isso vale para Anthropic/OpenAI/Z.ai, não para o resto; o caso concreto aqui: `CLAUDE_CODE_MESSAGING_TOKEN` presente no ambiente e repassada aos filhos (impacto pequeno, mesma máquina/usuário, mas é o tipo de vazamento que o código se propôs a evitar). Hoje não há GEMINI_API_KEY na máquina, então é potencial, não ativo.

**M5 · `bridge/send` pode travar a central até 60 s** — `central_server.py` (rota `POST /api/projects/{pid}/bridge/send`, `async def`) chama `ponte.enviar_agora` → `_abrir` → `iniciar_planejador` → `lancar_segundo_plano` → `_fora_da_sessao` (`central_bridge.py:534-552`), que roda `subprocess.run(powershell…, timeout=60)` **na thread do event loop**. Enquanto isso, toda a API (inclusive o app do <USUARIO>) para de responder. O `tick` está protegido (`asyncio.to_thread` no watcher); a rota manual não. Correção: rodar o lançamento via `to_thread`, ou mover o powershell para fora do caminho da requisição.

**M6 · Suíte completa vermelha (2 falhas de hoje, fora dos arquivos da ponte)** —
- `central_returns.py:11` (17:14) adicionou o evento `report_answered` a `IMPORTANT_KINDS` sem atualizar o teste-guarda `tests/test_central_returns.py:63`, que congela o conjunto → `AssertionError: 'report_answered'`.
- `central_reports.py:115` (17:27, **durante** esta revisão) trocou o rótulo "Comentar neste protótipo: clique no ponto desejado" por "Comentar neste relatório: …" sem atualizar `tests/test_central_reports.py:85`.
A suíte da ponte em si está verde; mas o estado entregue hoje falha `discover` (308 testes, 2 falhas). O teste-guarda de returns fez exatamente o trabalho dele — o código novo passou por cima sem atualizá-lo.

**M7 · `.mb-ponte/` fora do `.gitignore`** — verificado (`git status` mostra `?? .mb-ponte/`; `check-ignore` não ignora). `pedido.json` guarda o texto literal dos comentários do <USUARIO>; um `git add -A` futuro (ou o fluxo de export GitHub) pode levar a conversa para commit/público. Correção barata: linha `.mb-ponte/` no `.gitignore` (e checar o validador de privacidade do export).

**M8 · Servidor remoto também abre sessões de IA** — `real_store` (`central_server.py:31`) é verdadeiro para o processo `--remote` (8767): pelo túnel, um dispositivo pareado (Pixel) com sessão válida pode disparar `bridge/send`, que abre processos no PC. Tem autenticação + CSRF + gateway key (não é a brecha "sem auth" que a ordem pediu para procurar) e parece intencional ("app real"), mas as rotas de widget de cotas bloqueiam remoto explicitamente e a ponte não — registrar como decisão de design a confirmar com o <USUARIO>.

## Achados — menor

1. **Shim npm via `.CMD`** — `central_bridge.py:134-164`: `_npm_entrada` procura a sintaxe `$basedir/...` do shim **sh**, mas `shutil.which` no Windows nunca devolve o arquivo sem extensão (PATHEXT) e o `.CMD` real usa `%dp0%` → mitigação nunca dispara; `zcode`/`gemini` são lançados pelo `.CMD` (passa pelo cmd.exe). Hoje é seguro porque o argv leva só o template fixo de prompt + caminhos (texto livre do <USUARIO> vai em `TAREFA.md`/`prompt.txt`, nunca em argv — bom design); mas se um dia texto livre for para argv, é vetor de injeção via cmd.exe. Prova: conteúdo de `zcode.CMD` + teste de Popen (sem ValueError no 3.14).
2. **Fallback WMI silencioso** — `central_bridge.py:564-572`: se WMI/powershell falhar (política, WMI off, timeout), cai para `Popen` dentro do job — exatamente o problema da lição 260903 que a mudança queria resolver — sem evento/log visível (só `supervisor.json` com `via='popen'`). Além disso o caminho WMI real **não é provado por teste** (o teste mocka `_fora_da_sessao`); se o powershell+WMI não funcionar nesta máquina, o motivo do redesign desaparece em silêncio.
3. **`parar` no modo janela tem janela cega** — `central_bridge.py:650-662` + `abrir.sh` (`:603-613`): entre `lancar_janela` e o primeiro `_marcar` (pid do bash), o botão grava `PARAR` que **ninguém lê** (o script da janela não confere o flag) e responde `parados: [n0]` — a janela abre e a sessão roda mesmo assim; no fim, `_marcar --rc` sobrescreve o status para concluído/falhou.
4. **`_indexar` desiste em silêncio** — `central_bridge.py:848-858`: 5 conflitos seguidos → ordem existe no disco mas fora do índice (sem reconciliação, sem detecção de ordem ativa → alimenta M1). Probabilidade baixa.
5. **Reuso de PID** — `_vivo` (`:93-112`) não distingue PID reciclado no Windows → nó morto pode parecer vivo ("em andamento" para sempre). [HIPÓTESE — sem ocorrência observada; mitigável guardando data de início do processo.] Detalhe POSIX: `EPERM` é tratado como morto (irrelevante aqui).
6. **`_patch` cego além de 250 comentários** — `central_store.py:85` (`LIMIT 250`) + busca linear em `central_bridge.py:832`: comentário antigo fora da janela não recebe atualização de status.
7. **`bool()` permissivo em `salvar_config`** — `central_bridge.py:819`: `"false"` (string) vira `True`.
8. **`concluir` sem verificação de quem chama** — `central_bridge.py:665-676`: qualquer nó pode concluir a ordem inteira e `por` vem de `MB_PONTE_NO` sem prova (governança, não barreira).
9. **`_gravar` pode explodir após o Popen** — `central_bridge.py:75-86` + `:499`: esgotadas as ~10,5 s de retry do `os.replace`, a exceção sobe depois de a CLI já ter sido aberta → CLI órfã rodando, nó `iniciando`→`sem processo vivo` (falso "falhou"). Raro; [HIPÓTESE].
10. **`test_stop_flag` não prova a morte do filho** — `tests/test_central_bridge.py:180-187`: se `taskkill` falhasse, `wait(30)` estouraria → `rc=-9` → status `interrompido` → teste passaria com o filho dormindo por até 120 s. O teste nunca confere o pid do filho.
11. **Custo do observador** — `reconciliar` (a cada 3 s, em 2 processos: app local + gateway) lê `no.json`+caudas de log de cada nó de cada ordem não-final, e `_patch` faz um `listing` por comentário. OK no volume atual; cresce com o índice (cap 300).

## O que está correto (com prova)

1. **Autenticação/CSRF das rotas novas** — `/api/bridge/vendors`, `/api/projects/{pid}/bridge` (GET/PUT), `/bridge/send`, `/orders/{oid}/stop` passam pelo middleware (sessão + CSRF + Host/Origin; remoto exige gateway key) — `central_server.py:60-104`. A rota de stop valida o formato da ordem por regex (`\d{6}-\d{6}-[a-f0-9]{6}`) — sem travessia.
2. **Instância de prova não abre IA de jeito nenhum** — `real_store=False` quando `MB_ISOLATED=1`/`MB_PONTE=0`/store injetado; `receber` devolve `estado='prova'` **sem** rótulo de fila; `tick` retorna; `enviar_agora` recusa; `isolated_server` bloqueia `bridge/send` e `stop` pela whitelist `COPY_ONLY`; `test_isolated_server.py:43` lista as rotas bloqueadas; `test_probe_instance_never_opens_sessions` cobre o comportamento. Defesa em camadas de verdade.
3. **Injeção em argv contornada por design** — texto livre (comentários, tarefas, coordenação) vai por arquivo (`TAREFA.md`, `prompt.txt`); o argv leva apenas template fixo + caminhos; ids de nó validados (`n\d{1,3}`); no script bash da janela o prompt entra por `"$(cat prompt.txt)"` e os caminhos por aspas POSIX — nenhuma interpolação de texto do usuário no script.
4. **Lançamento WMI sem injeção** — o script PowerShell é fixo (sem interpolação) e o comando chega por variável de ambiente + `list2cmdline` (`central_bridge.py:534-552`); `supervisor.json` registra pid/via; `estado_ordem` usa `supervisor_pid` **ou** `supervisor.json` (fecha o vão entre lançar e o supervisor escrever). A gravação de `iniciando` antes do lançamento e o comentário "depois disso só o supervisor escreve no.json" corrigem a corrida de escrita dupla que existia às 17:04.
5. **Concorrência do store** — reivindicação do lote por `put` com revision (só uma instância lança); alocação de nó por `mkdir` exclusivo (atômico no Windows); `store.patch` em `BEGIN IMMEDIATE` (merge atômico, preserva campos do <USUARIO>); `_gravar` com tmp + `os.replace` e retries — sólido para o padrão de uso.
6. **Estados honestos nos casos principais** — supervisor morto → `sem processo vivo` → `falhou` (testado com pid inexistente); `CORRIGIDO_VERIFICADO` nunca é sobrescrito; resultado da ordem flui para o comentário com pendências (testado); cota vira aviso, não bloqueio.
7. **Contas certas** — `CODEX_HOME` fixado em `~/.codex` (Codex 1) para o filho gpt; vars de sessão (`CLAUDECODE`, `CODEX_API_KEY/BASE_URL`, `CLAUDE_CODE_USE_*`) removidas — tudo testado (`test_cli_commands_use_official_headless_modes_and_codex_one_home`).
8. **Anexos (aparição durante a revisão)** — `central_attachments.py` só aceita id gerado pelo servidor, exige igualdade de caminho/campos, protege contra symlink/junction/hardlink, limita tamanho e pixels; os comentários levam **caminhos absolutos** que o planejador consegue abrir — coerente com a ponte. Não auditado a fundo (fora do escopo desta ordem).

## O que ficou pendente

1. **Para o autor (Claude, sessão ativa hoje):** corrigir M1 (checar ordem ativa no tick), M2 (expiração de lote `lancando`), M3 (status final do complemento), M5 (tirar powershell da rota async), M6 (atualizar os 2 testes-guarda de returns/reports), M7 (`.mb-ponte/` no `.gitignore`). M4 e os menores ficam à sua avaliação.
2. **Decisão do <USUARIO> (via n0, não urgente):** confirmar se o acesso pelo celular (servidor remoto) pode abrir sessões de IA no PC (M8). Hoje pode; se não puder, um `if remote` nas rotas de lançamento resolve.
3. **Não provado por esta revisão:** o caminho WMI real (teste é mock) e o modo janela fim a fim — exigiriam abrir processos de verdade, fora do contrato somente-leitura desta ordem. Sugestão de prova barata depois: despachar um nó real de teste e conferir `supervisor.json` (`via='wmi'`) + sobrevivência ao fechamento da sessão.
4. **Escopo:** `central_attachments.py` apareceu durante a revisão e não foi auditado a fundo (leitura rápida only). Se a ordem quiser, vira nó de revisão próprio.

Provas desta revisão: suíte da ponte 19/19 OK; suíte completa 308 testes com 2 falhas identificadas e rastreadas; smoke `mb-ponte.py vendors` conferido contra `dados/orcamento_ia.json` e o PATH real; diffs contra `evidence/261018_ponte-orquestradores/backup/`; `git check-ignore`/`git status`; leitura do `zcode.CMD` real; teste empírico de `Popen(.CMD)` no Python 3.14.6. Nenhum outro arquivo do projeto foi criado, editado ou apagado (efeito colateral esperado de rodar testes: `__pycache__` e temporários do sistema).
