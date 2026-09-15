# Agent Flow Board — uso opcional do MEGABRAIN (a pedido do dono, 260915)

Quadro vivo que mostra as sessões de IA (claude, zcode, codex) como nós num mapa, com
cartões do que cada agente está fazendo. É o app de terceiros **Agent Flow**
(`github.com/patoles/agent-flow`, licença Apache-2.0) rodando **100% local** via npx,
na porta 3001. Nada sai da máquina.

## Como usar

- **Ícone:** `00_PARA-VOCE\BOARD-DE-AGENTES.lnk` (fixe na barra de tarefas: clique
  direito no ícone → *Fixar na barra de tarefas*; ou abra `01_acoes\13_ABRIR-BOARD-DE-AGENTES.cmd`).
- **Abre = roda.** O atalho sobe o server escondido e abre o board numa janela própria.
  Primeira vez pode demorar ~45 s (baixa o pacote).
- **Fecha = para.** Quando a janela do board é fechada, o server para sozinho
  (`bin\mb-board.ps1` monitora a janela).
- **Parar a força:** `powershell -File "<MEGABRAIN_ROOT>\bin\mb-board.ps1" -Parar`

## O que entra no quadro

- Sessões **claude** e **codex**: automáticas (hooks já instalados / leitura de rollouts).
- Sessões **zcode (GLM)**: automáticas para sessões **novas** (hooks registrados no config
  do zcode em 260915; sessões abertas antes não aparecem).
- Sessões só aparecem se rodarem **dentro de `S:\projetos multi i.a`** (o server é lançado
  nessa raiz de propósito, para cobrir todos os projetos).

## Arquivos

- `bin\mb-board.ps1` — motor (abrir/parar/monitor de janela).
- `01_acoes\13_ABRIR-BOARD-DE-AGENTES.cmd` — botão humano.
- `00_PARA-VOCE\BOARD-DE-AGENTES.lnk` — atalho para a barra de tarefas.
- O app em si mora no cache do npx do Windows; não é instalado globalmente.

## Como remover (se um dia quiser)

1. Apagar os 3 arquivos acima.
2. Remover as entradas `agent-flow` de `<USER_HOME>\.claude\settings.json` → `hooks`
   (deixou de ser necessário).
3. `npx clear-npx-cache` ou apagar `%LocalAppData%\npm-cache\_npx` (opcional, libera disco).
