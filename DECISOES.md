# DECISOES — megabrain core

## 260813 — criar arquivos de estado/handoff/decisões na pasta core
- Decisão: criar `ESTADO.md`, `HANDOFF.md` e `DECISOES.md` em `<PROJETOS_ROOT>\MEGA B R A I N`, em vez de dentro de `_github-repo-local/`.
- Alternativa descartada: manter o controle de estado só no git de `_github-repo-local/`. Motivo: a pasta core é a fonte canônica para todas as IAs, e o handoff precisa estar visível antes de qualquer sync para o repo.

## 260813 — pasta core do megabrain
- Decisão: tratar `<PROJETOS_ROOT>\MEGA B R A I N` como fonte da verdade do protocolo megabrain.
- Alternativa descartada: deixar cada IA inferir a pasta a partir do contexto. Motivo: evita divergência quando múltiplos agentes operam em cópias diferentes.

## 260813 — publicar ESTADO/HANDOFF/DECISOES no repo público
- Decisão: permitir que `ESTADO.md`, `HANDOFF.md` e `DECISOES.md` gerados na central sejam sanitizados e incluídos em `260810_github-export/` (e consequentemente em `_github-repo-local/`).
- Alternativa descartada: excluí-los do template público. Motivo: são arquivos de operação do protocolo e não contêm dados pessoais; disponibilizá-los no repo público ajuda quem clona a entender o estado atual sem expor a pasta central.

## 260813 — aspirador de código não destrutivo
- Decisão: criar `bin/mb-aspirador.py` com default dry-run, backup obrigatório e aplicação apenas de correções mecânicas seguras. Imports não usados são reportados, não removidos automaticamente.
- Alternativa descartada: fazer o aspirador aplicar também remoções via AST (imports) ou apagar arquivos vazios. Motivo: remoções semânticas e deletes são destrutivos; o objetivo é "aspirar poeira", não alterar lógica ou apagar conteúdo.
- Decisão: gerar relatório em Markdown (leitura humana rápida) e HTML (visual rico + metadados estruturados para IA). O HTML inclui JSON-LD, `<meta>` tags, cards, tabela, snippets com contexto e a documentação da ferramenta embutida.
- Alternativa descartada: gerar apenas Markdown ou usar um template externo. Motivo: Markdown é pobre para IA extrair métricas; template externo adiciona dependência de arquivo. HTML autocontido serve usuário e modelo sem configuração extra.
- Decisão: salvar relatório em `.mb-aspirador/relatorio-YYYYMMDD-HHMMSS.md` e backups em `.mb-aspirador/backups/<timestamp>/`, dentro do diretório varrido.
- Alternativa descartada: salvar na pasta central do megabrain. Motivo: o relatório e o backup pertencem ao projeto sendo limpo, não ao megabrain.

## 260814 — separação entre aspirador, relatório DNA e relatório de projeto
- Decisão: o aspirador é um componente do megabrain, não um coletor de informacionais para o relatório. Ele aparece no relatório DNA como nó da árvore de desenvolvimento e a ferramenta gera seu próprio relatório de auditoria quando rodada num projeto.
- Alternativa descartada: fazer o aspirador varrer `.md`/`.txt` da raiz do projeto para compor documentação. Motivo: confunde limpeza de código com geração de documentação; o relatório DNA já carrega essa informação de forma estruturada.
- Decisão: criar `bin/mb-relatorio-dna.py` que gera `MEGABRAIN-RELATORIO-DNA.html` na pasta central. O HTML é autocontido, interativo, com árvore de desenvolvimento visual (skill tree), explicação de cada componente e seção "Para a IA". Esse relatório é o DNA do megabrain: tendo ele, uma IA pode replicar/adaptar o protocolo.
- Alternativa descartada: gerar apenas Markdown ou manter documentação espalhada em `MEGABRAIN.md` + `SKILL.md` + referências. Motivo: o usuário precisa de um artefato único, bonito e navegável; HTML rico une visual humano e metadados para IA.
- Decisão: separar relatório DNA (template/canônico do megabrain) de relatório de projeto (instância aplicada a um projeto específico, ex.: TLOU). O DNA é copiado para dentro de `MEGABRAIN/` do projeto durante o sync; o relatório de projeto é gerado na raiz do projeto quando necessário.
- Alternativa descartada: um único relatório servir de DNA e de documentação de projeto. Motivo: o DNA precisa ser estável e genérico; o relatório de projeto inclui contexto específico (decisões, estado, lições) que não pode poluir o template.
- Decisão: backup automático do relatório DNA em `.dna-backup/` antes de sobrescrever. Cada versão mantém o HTML anterior com timestamp.
- Alternativa descartada: sobrescrever o relatório sem backup. Motivo: o DNA é o ativo que não pode ser perdido; backup permite rollback e auditoria de versões.

## 260814 — versionamento automático e caminhos portáteis
- Decisão: scripts do megabrain passam a aceitar a variável de ambiente `MEGABRAIN_CENTRAL` e o argumento `--central`. Quando nenhum dos dois é fornecido, detectam a central a partir do diretório do próprio script (`bin/../`). Isso torna o pacote utilizável em qualquer máquina sem editar caminhos absolutos.
- Alternativa descartada: manter `<MEGABRAIN_ROOT>` hardcoded nos scripts. Motivo: caminhos absolutos do PC do <USUARIO> quebram em qualquer outro computador.
- Decisão: `mb-check-version.py` ganha modo `--verificar-git` que consulta o remote do repositório (via `git ls-remote` ou API pública do GitHub) e avisa se há versão mais recente. O fluxo padrão continua comparando `VERSAO.txt` local contra a central.
- Alternativa descartada: fazer download automático e silencioso da nova versão. Motivo: o usuário disse explicitamente que é leigo e prefere confirmar antes; automação total sem aviso esconde o que mudou.
- Decisão: o repositório público do GitHub é a fonte canônica externa do megabrain. Quem clona recebe o DNA e pode rodar `mb-check-version.py --verificar-git` para saber se está desatualizado.
- Alternativa descartada: distribuir o megabrain só por pasta local/compartilhada. Motivo: o amigo do <USUARIO> precisa baixar de forma simples e o git é o canal natural.

## 260814 — relatório DNA vira pasta (`dna/`), não arquivo solto
- Decisão: `bin/mb-relatorio-dna.py` passa a gravar em `MEGABRAIN\dna\` —
  `RELATORIO-DNA.html` (o artefato principal, mesma importância de antes) +
  `dna.json` (mesmos dados em JSON puro, pra script/IA consumir sem parsear
  HTML) + `README.md` (índice de uma linha) + `.dna-backup/` (histórico,
  antes solto na raiz da central). HTML legado de versões < 260814 é migrado
  automaticamente pro backup na primeira execução, não fica perdido nem
  sobrescrito sem rastro.
- Alternativa descartada: manter arquivo único solto na raiz. Motivo: pedido
  explícito do <USUARIO> — a pasta deixa o DNA no mesmo formato de "pasta com
  propósito único" que o resto do projeto usa (`referencias/`, `skills/`,
  `bin/`), e abre espaço pra crescer (JSON estruturado, backups) sem poluir
  a raiz da central.
- Decisão: `mb-check-version.py` sincroniza a pasta `dna/` inteira pro
  projeto (mapeamento `("dna", "dna")`), não mais o arquivo solto.

## 260814 — gerador genérico de relatório de projeto (`mb-relatorio-projeto.py`)
- Decisão: criar `bin/mb-relatorio-projeto.py`, o item que ficava aberto no
  HANDOFF desde a v3.7 ("gerador de relatório de projeto específico").
  Generaliza o padrão já usado manualmente no Financeiro da Silva
  (`RELATORIO.html` escrito à mão) em um script parametrizável: qualquer
  projeto passa `--projeto`, `--titulo`, `--plano` (+ opcionais `--extra`,
  `--skill`, `--tldr`, `--megabrain-central`) e recebe um HTML único que
  concentra contexto específico + geral, estado/handoff, situação viva,
  próximas ações e dados pendentes (auto-extraídos de `- [ ]`/`- [x]` de
  todas as fontes lidas, com a fonte de cada item).
- Alternativa descartada: continuar escrevendo `RELATORIO.html` à mão por
  projeto. Motivo: viola a regra de ouro 4 (gerado nunca se edita — o
  `RELATORIO.html` do Financeiro da Silva era HTML escrito direto, sem
  gerador, contradizendo a própria regra); também não escala pra outros
  projetos sem reescrever do zero cada vez.
- Decisão: o relatório de projeto lê `ESTADO.md`/`HANDOFF.md`/`DECISOES.md`
  do projeto **como referência**, sem mover ou duplicar os arquivos —
  handoff concentrado na leitura (seção "Estado e handoff" do relatório),
  fonte continua sendo os `.md`. Projeto sem esses três arquivos (nível 1-2
  de adoção, ex.: Financeiro da Silva) usa o próprio arquivo `--plano` como
  fonte combinada de estado + decisões, e o relatório declara isso
  explicitamente em vez de fingir uma seção vazia.
- Alternativa descartada: mover ESTADO/HANDOFF/DECISOES pra dentro do
  relatório ou exigir que todo projeto os tenha. Motivo: pedido explícito do
  <USUARIO> foi "não precisa mudar os md de lugar, só usar como referência";
  exigir os três arquivos em projeto pessoal pequeno é burocracia sem uso —
  a tabela de níveis de adoção (seção 7) já cobre esse caso.
- Referência de uso completo (todos os argumentos preenchidos):
  `Financeiro da Silva/05_scripts/gerar_relatorio.py`.

## 260814 — "caminhos" vira "resolução" no relatório de projeto
- Decisão: renomear a seção `id="caminhos"` do `mb-relatorio-projeto.py` pra
  `id="fontes"` (tabela de caminho de arquivo, só isso) e criar uma seção
  nova, `id="resolucao"` ("Resolução — alternativas pra resolver agora"),
  posicionada acima de "Situação viva". A seção varre `--plano` + `--extra`
  por headings `##`/`###` cujo título bate com palavras-chave ("plano de
  ação", "estratégia", "alternativas", "resolução", "o que fazer"...) e
  copia esses trechos em destaque, sem duplicar/mover nada do arquivo fonte.
- Motivo: pedido explícito do <USUARIO> — "caminhos" no relatório dele
  significava "rotas pra resolver a questão financeira" (alternativas de
  decisão), não "caminho de pasta/arquivo". A ambiguidade só apareceu na
  prática, lendo o relatório do Financeiro da Silva.
- Alternativa descartada: manter "caminhos" só pra arquivo e criar um termo
  novo pras alternativas de decisão sem integrá-lo ao gerador (ex.: pedir
  pro <USUARIO> escrever as alternativas direto no `PLANO.md` sem extração
  automática). Motivo: quebraria a filosofia de concentração — a ideia é o
  relatório destacar automaticamente o que já existe no `.md` fonte, não
  exigir reescrever o conteúdo em outro lugar.
- Novos argumentos: `--sem-resolucao` (desliga a extração) e
  `--resolucao-titulo PALAVRA` (repetível, adiciona palavra-chave própria
  do domínio do projeto).
- Aplicado no Financeiro da Silva no mesmo commit: `PLANO.md` ganhou o fato
  "R$ 1.300 confirmados no débito" (informado por <USUARIO> em 14/08,
  checagem direta — não é estimativa) mais uma subseção "Uso do débito
  disponível" dentro de "Plano de ação para 20/08" com 3 alternativas
  (concentrar no Nubank / usar parcial / guardar tudo), cada uma com o
  porquê antes do como e uma recomendação (não três opções empatadas) — a
  seção "Resolução" do `RELATORIO.html` já extrai isso automaticamente.

## 260814 — caminhos absolutos não podem voltar pro SKILL.md
- Decisão: manter `<MEGABRAIN_ROOT>` como placeholder no `skills/megabrain/SKILL.md`, não substituir por `<MEGABRAIN_ROOT>/` mesmo que a central do <USUARIO> esteja nesse caminho.
- Alternativa descartada: deixar o caminho absoluto no SKILL.md da central, confiando que o `mb-generate-template.py` vai sanitizar no template público. Motivo: o SKILL.md da central também é copiado para dentro de projetos (`MEGABRAIN/skills/megabrain/SKILL.md`) e pode ser usado em outra máquina — caminho absoluto quebra fora do PC do <USUARIO> e vaza a estrutura de pasta pessoal.

## 260814 — pastas internas ficam fora do template público
- Decisão: adicionar `_to_delete/` e `alteracoes-pendentes/` à lista `EXCLUIR` do `bin/mb-generate-template.py`. Essas pastas são de uso interno da central e não devem ir para o repo público.
- Alternativa descartada: deixar o gerador copiar tudo que não está na lista antiga. Motivo: `_to_delete/` contém arquivos temporários de decisão e `alteracoes-pendentes/` contém trabalho em andamento específico do <USUARIO> — ambos poluiriam o pacote público sem agregar valor.

## 260814 — módulo utilitário compartilhado `bin/mb_utils.py`
- Decisão: criar `bin/mb_utils.py` com path containment, I/O atômica, file locking leve, escaping de HTML/JSON e helpers CLI, usando apenas stdlib. Os scripts `mb-sync.py`, `mb-check-version.py`, `mb-generate-template.py`, `mb-relatorio-projeto.py`, `mb-relatorio-dna.py` e `mb-aspirador.py` passam a importá-lo.
- Alternativa descartada: replicar as correções em cada script individualmente. Motivo: funções de segurança e I/O duplicadas divergem e geram bugs; centralizar reduz manutenção e garante comportamento uniforme.

## 260814 — file locking sem dependência externa
- Decisão: implementar trava de arquivo via `os.open(..., O_CREAT | O_EXCL)` em `mb_utils.py`, usada por `mb-sync.py`, em vez de adicionar `filelock` como dependência obrigatória.
- Alternativa descartada: usar `filelock` (PyPI) para locking entre processos. Motivo: o ambiente do <USUARIO> não tem `filelock` instalado e adicionar dependência quebraria portabilidade zero-config; a solução com `O_EXCL` é suficiente para o cenário de handoff entre agentes.

## 260814 — path traversal bloqueado em todos os scripts
- Decisão: validar `--dir`, `--projeto`, `--saida`, `--central`, `--extra`, `--skill`, `--backup-dir` e caminhos relativos de entrada com `Path.resolve()` + `is_relative_to()` (via `mb_utils.resolve_within`). Scripts recusam operação se o caminho escapar da área permitida.
- Alternativa descartada: confiar nos caminhos passados pelo usuário/agente. Motivo: vários scripts fazem `shutil.rmtree` ou leitura/escrita de arquivos; caminhos maliciosos ou acidentais (`../../etc`) poderiam corromper dados fora do projeto.

## 260814 — escrita atômica para arquivos sensíveis
- Decisão: usar `tempfile.mkstemp` + `os.replace` (via `mb_utils.atomic_write_text`) para `HANDOFF.md`, relatórios HTML/JSON, `VERSAO.txt` do template e README do DNA.
- Alternativa descartada: manter `path.write_text()` direto. Motivo: escrita direta pode deixar arquivo parcialmente escrito se o processo for interrompido; `os.replace` garante que o leitor sempre veja o arquivo antigo ou o novo, nunca um estado intermediário.

## 260814 — escaping de HTML e JSON-LD nos relatórios
- Decisão: escapar href de links markdown (`html.escape(..., quote=True)`) e escapar `</` e `<!--` em JSON-LD embutido (`mb_utils.html_json_safe`) nos relatórios de projeto e DNA.
- Alternativa descartada: confiar que o conteúdo dos `.md` fonte é seguro. Motivo: os arquivos fonte podem conter links ou textos controlados pelo usuário/IA; sem escaping, relatórios gerados ficam vulneráveis a XSS e quebra de `<script>`.

## 260814 — `requirements.txt` com bibliotecas recomendadas
- Decisão: adicionar `requirements.txt` listando 10 bibliotecas/padrões recomendados (filelock, platformdirs, mistune, nh3, pydantic, pydantic-settings, structlog, watchdog, rich, pytest, ruff), mas manter os scripts funcionando sem elas.
- Alternativa descartada: instalar as bibliotecas agora e refatorar scripts para dependerem delas. Motivo: o ambiente não tem as bibliotecas instaladas e instalar sem ambiente isolado poderia quebrar outros projetos; o arquivo serve como roteiro de adoção gradual.

## 260814 — diferenciação de usuário no megabrain
- Decisão: implementar campo `USUARIO:` no `HANDOFF.md` e propagá-lo pela
  trava de `mb-sync.py` (detectado de `260810_memoria-pessoal.md` ou via
  `--usuario`). `mb-sync-memoria.py` também lê e injeta `USUARIO:` em
  `CLAUDE.md`, `GEMINI.md` e `AGENTS.md`. `mb_utils.py` centraliza os
  helpers `extract_usuario` e `detectar_usuario`.
- Alternativa descartada: manter a suposição implícita de que só o
  <USUARIO> opera. Motivo: o <USUARIO> pediu explicitamente diferenciação de
  usuário; sem um campo declarado, o protocolo não consegue distinguir
  operadores num ambiente multi-usuário nem documentar para quem uma trava
  está ativa.
- Decisão: o nome padrão é detectado do arquivo de identidade pessoal
  (`260810_memoria-pessoal.md`), não hardcoded no script. Isso mantém o
  pacote portátil: outra pessoa que clone o repo pode trocar só o arquivo
  de identidade em vez de editar código.
- Alternativa descartada: hardcoded `<USUARIO>` como default em
  `mb-sync.py`. Motivo: vazaria nome pessoal no código e quebraria a
  premissa de que o template público é genérico.



## 260814 — card "Ação imediata" + 2 bugs corrigidos no conversor markdown
- Decisão: adicionar um card em destaque, `id="acao"`, logo abaixo do TL;DR
  (antes até do `<nav>`) — extrai UM heading do `--plano` marcado como "ação
  imediata"/"o que fazer agora"/"faça isto" e mostra a sequência única
  recomendada, numerada, com estilo visual bem diferente do resto do
  relatório (fundo escuro, número grande em círculo). Motivo: pedido
  explícito — "inclua um plano de ação muito óbvio... e muito claro no
  relatório". A seção "Resolução" já existente mostra alternativas
  concorrentes (várias rotas); "Ação imediata" é o oposto — um caminho só,
  sequencial, sem ambiguidade.
- Alternativa descartada: reaproveitar a seção "Resolução" pra isso.
  Motivo: misturaria dois modos de leitura diferentes (escolher entre
  opções vs. seguir uma sequência) na mesma seção — o pedido era por algo
  "muito óbvio", que exige separação visual clara.
- Bug 1 encontrado ao testar: o conversor markdown→HTML não juntava linhas
  indentadas de continuação dentro de um item de lista — todo item de lista
  (numerado ou com marcador) que quebrava em mais de uma linha por largura
  virava um `<li>` com só a primeira linha, e o resto saía como `<p>` solto
  fora da lista. Isso já estava quebrando conteúdo antigo do
  `PLANO.md` (seção "Estratégia") e quebrou o card novo também. Corrigido
  com uma função `consumir_continuacao()` que junta linhas indentadas
  subsequentes ao texto do item, parando em linha vazia, heading, tabela,
  citação, hr, ou novo item de lista.
- Bug 2 encontrado no mesmo teste: `extrair_secoes_resolucao()` (usada tanto
  pra "resolução" quanto pra "ação imediata") não excluía o H1 (título do
  documento) da varredura de headings. O H1 do `PLANO.md` continha "v11 ·
  ação imediata numerada..." no meio do texto — bateu como match falso da
  palavra-chave "ação imediata", e por ser heading de nível 1, a extração só
  para em outro heading de nível ≤1 (não existe outro H1 no arquivo) — então
  engoliu o arquivo inteiro pro dentro do card. Corrigido restringindo a
  varredura a `##`/`###`/`####` (nunca H1) — título de documento não é
  conteúdo de seção.
- Referência de uso completo (todos os argumentos preenchidos):
  `Financeiro da Silva/05_scripts/gerar_relatorio.py`.
