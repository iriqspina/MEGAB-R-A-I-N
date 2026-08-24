# DECISOES — megabrain core

## 260813 — criar arquivos de estado/handoff/decisões na pasta core
- Decisão: criar `ESTADO.md`, `HANDOFF.md` e `DECISOES.md` em `<PROJETOS_ROOT>\MEGA B R A I N`, em vez de dentro de `_github/repo-local/`.
- Alternativa descartada: manter o controle de estado só no git de `_github/repo-local/`. Motivo: a pasta core é a fonte canônica para todas as IAs, e o handoff precisa estar visível antes de qualquer sync para o repo.

## 260813 — pasta core do megabrain
- Decisão: tratar `<PROJETOS_ROOT>\MEGA B R A I N` como fonte da verdade do protocolo megabrain.
- Alternativa descartada: deixar cada IA inferir a pasta a partir do contexto. Motivo: evita divergência quando múltiplos agentes operam em cópias diferentes.

## 260813 — publicar ESTADO/HANDOFF/DECISOES no repo público
- Decisão: permitir que `ESTADO.md`, `HANDOFF.md` e `DECISOES.md` gerados na central sejam sanitizados e incluídos em `_github/export/` (e consequentemente em `_github/repo-local/`).
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
  `Financeiro da Silva/01_acoes/gerar_relatorio.py`.

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

## 260814 — modo offline do megabrain
- Decisão: garantir que a cópia `MEGABRAIN/` dentro de cada projeto derivado
  seja auto-suficiente quando o GitHub ou a internet estiverem
  indisponíveis. Criar `OFFLINE.md` na central, adicioná-lo ao mapeamento
  de sincronização, e implementar `--offline` em `mb-check-version.py`
  (desativa consultas de rede e deixa claro que a cópia local continua
  funcionando).
- Alternativa descartada: deixar o protocolo dependendo do git remoto para
  qualquer operação. Motivo: o <USUARIO> pediu explicitamente uma versão
  local funcional; projetos reais não podem parar quando o remoto cai.
- Decisão: manter a sincronização central -> projeto como mecanismo
  principal de atualização, mas documentar que, uma vez sincronizado, o
  projeto vive sozinho. O modo offline é opt-in por flag, não padrão,
  para não esconder falhas de rede de quem quer saber.

## 260814 — redundância contra falha de fontes
- Decisão: adicionar scripts de backup (`mb-backup-central.py`) e
  recuperação (`mb-recuperar-megabrain.py`) para evitar que a perda da
  central, do GitHub ou da pasta `MEGABRAIN/` de um projeto deixe o
  usuário sem protocolo. O backup é um zip padrão, sem dependências
  externas; a recuperação aceita backup zip, outro projeto ou a central
  local, e detecta a fonte automaticamente quando possível.
- Alternativa descartada: confiar apenas no git remoto como fonte de
  recuperação. Motivo: o <USUARIO> deixou claro que "links" (fontes) podem
  quebrar; ter só o GitHub é ponto único de falha.
- Decisão: os scripts de backup e recuperação usam apenas stdlib
  (`zipfile`, `shutil`) e `mb_utils.py`, mantendo portabilidade
  zero-dependência.



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
  `Financeiro da Silva/01_acoes/gerar_relatorio.py`.

## 260814 — Codex ganha router próprio sem duplicar o protocolo

- Decisão: criar `skills/codex-megabrain/` como router nativo do Codex. A
  skill resolve `<MEGABRAIN_ROOT>`, usa a skill central e as referências sob
  demanda, adapta autorização/planejamento/verificação ao Codex e é instalada
  em `~/.codex/skills/` por vínculo para a fonte central.
- Alternativa descartada: copiar integralmente `skills/megabrain/SKILL.md`
  para uma segunda skill. Motivo: duas cópias longas do mesmo protocolo
  divergiriam e queimariam contexto; o router mantém uma fonte operacional.

## 260814 — roteamento GPT-5.6 fica no guia multi-IA

- Decisão: registrar Sol, Terra, Luna e os esforços `low` a `max` em
  `referencias/260813_multi-ia.md`, que já é o ponto oficial de escolha de
  modelo do MEGABRAIN. Usar `medium` como ponto de partida, elevar esforço
  somente com ganho mensurável e reservar `max` para casos críticos.
- Alternativa descartada: espalhar recomendações de modelo dentro de
  `MEGABRAIN.md`, da skill agnóstica e da skill do Codex. Motivo: repetição
  aumenta custo de contexto e envelhece em ritmos diferentes.

## 260814 — ações rápidas no relatório de projeto

- Decisão: `mb-relatorio-projeto.py` recebe `--acao "Rótulo|URL"` repetível e mostra botões no card “Ação imediata”. Aceita somente URLs HTTPS ou âncoras internas; URLs externas abrem em nova aba com `noopener noreferrer`.
- Alternativa descartada: inserir HTML livre dentro dos Markdown do projeto ou links para `.cmd` locais. Motivo: HTML livre quebra a regra de que a fonte é Markdown e abre vetor de script; navegador não deve executar `.cmd` por link e isso ainda não resolve o uso fora do Windows.
- Aplicação: o MIMDE usa `RELATORIO-MIMDE.html` como interface única de leitura, com botões para LinkedIn, Workana, 99Freelas e Tracker.
## 260815 — pipeline comercial e aprendizado sobem para o core

- Decisão: criar `referencias/260815_pipeline-governanca-aprendizado.md` e tornar o Gate AMARRAR PONTAS parte da skill central. A referência reúne aprovações humanas, Amarrador de Pontas, Contraditor, Teammates por custo, gate financeiro, dinheiro versus momentum, dogfooding sanitizado e promoção entre projetos.
- Motivo: o usuário determinou que as mecânicas discutidas no MIMDE sempre alimentem o MEGABRAIN; deixá-las apenas no projeto produziria divergência e impediria reuso em Rodada, Design Diamond, Diretoria e projetos futuros.
- Alternativa descartada: copiar todos os arquivos e números do MIMDE para o core. Motivo: preços, despesas, clientes e metas são contexto específico; o core recebe apenas o mecanismo sanitizado e portátil.
- Decisão: quando o usuário declarar promoção obrigatória de uma classe de aprendizado, a versão sanitizada sobe no mesmo ciclo, sem esperar três repetições. A regra de três continua valendo para transformar lição em automação/skill ampla.
- Alternativa descartada: deixar a promoção como item de handoff. Motivo: “sempre” exige garantia operacional na sessão corrente, não promessa para outro agente.

## 260815 — piso de ticket inclui fixo alocado e teste do portfólio

- Decisão: o gate financeiro passa a exigir capacidade faturável, rateio causal da operação fixa, piso completo por serviço e validação mensal sem dupla contagem. Desconto, horas e limite tributário entram como testes de estresse.
- Motivo: o primeiro modelo MIMDE subtraía os fixos no cenário mensal, mas não nos pisos unitários. O portfólio principal passava por causa do mix, enquanto serviços isolados podiam ficar abaixo dos 30% prometidos.
- Alternativa descartada: manter fixos apenas na conta mensal. Motivo: isso permite subsídio cruzado invisível e torna a tabela insegura quando o mix vendido muda.

## 260815 — estado operacional não pertence ao pacote público

- Decisão: excluir `ESTADO.md`, `HANDOFF.md`, `DECISOES.md` e `RELATORIO.html` da central no export; sanitizar também HTML, JSON, YAML, CSS e JavaScript; fazer o gerador falhar se encontrar caminhos ou identificadores pessoais conhecidos.
- Motivo: a auditoria pré-push encontrou no pacote já publicado caminhos locais, nomes de projetos e valor financeiro vindos do relatório e das decisões operacionais. O README já declarava que cada projeto deve criar o próprio estado.
- Alternativa descartada: confiar apenas em substituição textual de nome e caminho. Motivo: mesmo sem nome explícito, decisões e relatórios carregam contexto privado que não pertence ao protocolo distribuível.

## 260815 — corrigir a branch atual sem reescrever o histórico automaticamente

- Decisão: remover os arquivos privados da versão corrente em `b13a2bc` e registrar que o histórico anterior ainda pode contê-los.
- Motivo: a autorização recebida cobria commit e push do estado atual; reescrever commits publicados e fazer force-push é uma ação destrutiva de outro nível.
- Alternativa descartada: limpar todo o histórico e forçar `main` no mesmo movimento. Motivo: isso quebra clones e referências existentes e exige autorização específica após definir exatamente o conteúdo a expurgar.

## 260815 — localização do MEGABRAIN guiada pelo usuário

- Decisão: toda IA que usar o protocolo deve localizar a instalação pela cópia
  do projeto, `MEGABRAIN_CENTRAL` ou marcadores da pasta; sem resultado ou com
  ambiguidade, pergunta ao usuário pelo caminho antes de montar comandos.
- Motivo: caminhos de unidade e diretórios pessoais não se transferem entre
  máquinas, e uma pergunta curta evita instalação, leitura e Git no local
  errado.
- Alternativa descartada: publicar um caminho-padrão ou depender de o usuário
  editar o prompt manualmente. Motivo: recria a dependência do computador de
  origem e adiciona atrito justamente na primeira execução.

## 260815 — export ignora cópia derivada do core

- Decisão: o gerador público exclui `MEGABRAIN/` da central e remove a cópia
  legada equivalente no destino antes de gerar.
- Motivo: o diretório é uma sincronização local derivada; duplicá-lo no pacote
  público pode manter conteúdo obsoleto e invalidar a auditoria de privacidade.
- Alternativa descartada: manter a pasta no export e apenas ignorá-la na
  validação. Motivo: esconderia um arquivo público desatualizado em vez de
  eliminar a causa da divergência.

## 260815 — relatório da central explica antes de documentar

- Decisão: reconstruir `RELATORIO.html` como apresentação institucional para
  um leitor sem contexto, usando o padrão visual do MIMDE e seis painéis por
  pergunta: Começar, Entender, Usar, Na prática, Limites e Fontes.
- Motivo: o relatório anterior concentrava material operacional, mas não
  respondia com rapidez o que é o MEGABRAIN, por que existe e o que muda no
  trabalho. Um amigo não deve precisar entender a árvore de arquivos antes do
  conceito.
- Alternativa descartada: aplicar apenas o CSS do MIMDE ao relatório antigo.
  Motivo: a hierarquia de conteúdo continuaria dirigida ao operador interno;
  trocar a pele não corrigiria o leitor nem a decisão de cada tela.
- Decisão: manter a apresentação e suas fontes fora do pacote público
  sanitizado enquanto ela citar MIMDE, Design Diamond e Rodada.
- Alternativa descartada: publicar os exemplos locais por serem pouco
  sensíveis. Motivo: o pacote público já separa protocolo genérico de contexto
  pessoal; a nova peça não deve reabrir essa fronteira por acidente.

## 260815 — apresentação pública usa categorias genéricas

- Decisão: distribuir `RELATORIO.html` e `relatorio-megabrain/` no pacote
  público a partir da v4.12, substituindo os três projetos locais por serviços,
  design e aprovação.
- Motivo: <USUARIO> quer apresentar o MEGABRAIN ao Douglas pelo próprio
  checkout; o artefato precisa viajar com o repositório e continuar
  compreensível sem expor contexto privado.
- Alternativa descartada: manter o HTML somente na central e enviá-lo como
  arquivo avulso. Motivo: separaria resultado e fonte, impediria regeneração e
  deixaria o commit sem o principal artefato da apresentação.

## 260816 — GerenteNeuron como app local de chat multi-IA

- Decisão: criar `gerenteneuron/`, app local que roda só com stdlib Python
  (`http.server`) e unifica o acesso a OpenAI, Anthropic, Gemini, Moonshot/Kimi
  e Ollama local num único chat no navegador.
- Alternativa descartada: usar Flask/FastAPI/Electron. Motivo: evita instalar
  dependências externas e mantém a filosofia de portabilidade zero-config do
  MEGABRAIN; `http.server` da stdlib é suficiente para um app local.
- Decisão: implementar roteador heurístico por custo/capacidade (`quick`,
  `standard`, `deep`) com override manual e fallback automático para o próximo
  modelo disponível ou mock.
- Alternativa descartada: treinar um classificador de ML para escolher o modelo.
  Motivo: mais caro, opaco e lento de validar; regras explicáveis permitem
  ajuste rápido e auditoria imediata.
- Decisão: credenciais ficam em `gerenteneuron/.env` e dados locais em
  `gerenteneuron/data/`, ambos fora do Git; `.env.example` serve de template.
- Alternativa descartada: armazenar configuração no repositório. Motivo: chaves
  de API não podem ser versionadas; dados de conversa são pessoais e devem
  ficar no PC do usuário.
- Decisão: criar skill `/gerenteneuron` em `skills/gerenteneuron/SKILL.md` para
  integrar o app ao protocolo MEGABRAIN sem duplicar os gates.
- Alternativa descartada: absorver a funcionalidade dentro de
  `skills/megabrain/SKILL.md`. Motivo: a skill central já tem escopo definido;
  misturar interface de chat com protocolo de entrega poluiria ambos.

## 260816 — GerenteNeuron como gerente geral de projetos

- Decisão: evoluir o GerenteNeuron para ter uma aba "Gerente" que recebe
  pedidos gerais, identifica o projeto ativo pela mensagem, classifica a
  intenção (status/ação/pergunta) e indica qual skill invocar (`/portfolio`,
  `/rodada`, `/financeirodasilva`, `/megabrain` etc.).
- Alternativa descartada: fazer o GerenteNeuron varrer o disco em busca de
  projetos. Motivo: viola a política de acesso local e exporia estrutura de
  pastas pessoais; melhor que o usuário cadastre explicitamente os projetos em
  `projetos.json`.
- Decisão: o GerenteNeuron **orquestra e sugere**, mas não executa ações em
  outros agentes automaticamente. Ele monta o prompt e aponta a skill certa;
  a execução continua no agente/skill de destino.
- Alternativa descartada: integrar o GerenteNeuron diretamente ao runtime do
  Kimi/Codex para invocar skills sozinho. Motivo: aumenta complexidade e
  depende de APIs internas dos agentes que não são estáveis; a sugestão
  explícita mantém o usuário no controle e funciona em qualquer ambiente.
- Decisão: catálogo de projetos fica em `gerenteneuron/projetos.json`, fora do
  Git, com template versionado em `projetos.json.example`.
- Alternativa descartada: hardcodear a lista de projetos do <USUARIO> no código.
  Motivo: projetos mudam e a lista é pessoal; não pode ir para o repo público.

## 260816 — instalação da auditoria v5.1 na central real (não só no pacote entregue)

- Decisão: a auditoria v5.1 (14 achados) tinha sido corrigida só no pacote público (`MEGABRAIN-v5.1.zip` / `_github/export/`) numa sessão anterior; a central real (`bin/`, `dna/`, `skills/megabrain/SKILL.md`, `VERSAO.txt`) continuava em v4.12. Esta sessão aplicou os mesmos fixes na central, arquivo por arquivo, distinguindo mudança funcional real de ruído de sanitização (o pacote público troca caminhos pessoais reais por `<MEGABRAIN_ROOT>`/`<USUARIO>`; copiar esses arquivos de volta pra central quebraria os scripts que dependem do caminho real).
- Alternativa descartada: copiar o pacote público inteiro por cima da central (era a instrução original passada ao usuário). Motivo: `mb-generate-template.py` e `mb-sync-projeto-para-central.py` têm o caminho absoluto real da central como valor funcional (`CENTRAL_DEFAULT`, tabela de sanitização) — a versão do pacote tem esse mesmo valor substituído por placeholder, e sobrescrever quebraria o próprio gerador. Também `MEGABRAIN.md`/`README.md` da central têm seções pessoais (roteamento de projetos, seção 8/8b/8c) que o gerador público remove de propósito; sobrescrever apagaria conteúdo real sem necessidade.
- Decisão: `bin/mb-check-version.cmd` tinha um bug real (não relacionado à auditoria): caminho hardcoded pra central com o "M" cortado (`<PROJETOS_ROOT>\EGA B R A I  N\...`), citação quebrada no comentário. Reescrito pra usar `%~dp0` (resolve o próprio `bin/` sem precisar do caminho absoluto).
- Decisão: os `.cmd` da raiz continuam em estrutura flat com prefixo de data (convenção já usada na central), não migraram para a pasta `scripts/` que o pacote público usa. Só o conteúdo interno foi corrigido (detecção dinâmica de Python, sem caminho pessoal hardcoded), ajustando `%~dp0..` do pacote pra `%~dp0` já que a central não tem a subpasta extra.
- Decisão: `260810_MEGABRAIN.md` (duplicata datada, idêntica a `MEGABRAIN.md`) movida pra `_to_delete/`. A v5.1 removeu essa duplicata de `mb-check-version.py`, `mb-sync-projeto-para-central.py` e `260824_novo-projeto.cmd`; manter o arquivo físico sem nenhum script apontando pra ele era lixo puro.
- Decisão: rodar `mb-check-version.py --force --auto` nos 11 projetos ativos da pasta multi i.a em vez de aguardar cada projeto detectar a versão nova sozinho. Motivo: pedido explícito do usuário ("todos da pasta do multi i.a").
- Limitação encontrada: a ponte usada nesta sessão pra mexer no PC do usuário roda um Linux sandboxed sem permissão de `unlink` (delete) em arquivos do drive montado, e sem acesso de rede. Isso quebra duas coisas do git: (1) todo comando de escrita do git deixa um `.lock` órfão que bloqueia o próximo comando, exigindo mover o lock pra fora antes de cada chamada; (2) `git push` não tem rede pra alcançar o GitHub. Documentado aqui pra próxima sessão não perder tempo redescobrindo — mova (`mv`, não `rm`) qualquer `.git/*.lock` ou `.git/objects/**/tmp_obj_*` órfão antes de cada comando de escrita, e nunca tente `push` por essa ponte — rode do terminal local.

## 260816 — roteamento local-first e intervenção do usuário no GerenteNeuron

- Decisão: implementar estratégias de roteamento `local_code`, `cheap`,
  `standard`, `deep` no `gerenteneuron/router.py`. Código/debug/refactor vão
  para Ollama local primeiro; revisão/auditoria/decisão crítica sobem para
  modelos pagos fortes.
- Alternativa descartada: sempre escolher o modelo mais barato independente do
  tipo de tarefa. Motivo: código é barato e seguro no local; julgamento exige
  modelo pago forte. Misturar as duas coisas gera ou gasto desnecessário ou
  resposta fraca.
- Decisão: botão "Reforçar" permite ao usuário subir a estratégia quando a
  resposta automática é insuficiente, sem precisar trocar de aba ou modelo
  manualmente.
- Alternativa descartada: fazer o app detectar sozinho quando a resposta é
  fraca e reenviar. Motivo: detecção automática de qualidade é instável e
  gasta tokens; o usuário sabe melhor quando precisa de mais capacidade.
- Decisão: registrar cada interação e feedback em `data/feedback.jsonl` e
  expor `/api/eval` com estatísticas e sugestões de ajuste.
- Alternativa descartada: depender só da intuição para calibrar o roteador.
  Motivo: sem dados, o ajuste vira adivinhação; o feedback do usuário é a
  fonte mais confiável de qualidade.
- Decisão: testar conectividade de cada API ao salvar configuração e mostrar
  status na UI.
- Alternativa descartada: confiar que a key está certa sem testar. Motivo:
  keys inválidas, expiradas ou sem crédito só aparecem no primeiro uso; testar
  antecipa o erro.

## 260816 — cofre local de credenciais do GerenteNeuron

- Decisão: criar cofre criptografado em `gerenteneuron/vault/` para armazenar
  todas as API keys e credenciais, protegido por senha mestre escolhida pelo
  usuário e com chave de recuperação.
- Alternativa descartada: manter credenciais em `.env` texto plano. Motivo:
  `.env` é prático mas não protege contra acesso local; um cofre criptografado
  é mais adequado quando múltiplas keys sensíveis ficam no mesmo lugar.
- Decisão: usar `cryptography.fernet` com PBKDF2-HMAC-SHA256 e 600.000
  iterações. A chave simétrica dos dados é aleatória e protegida separadamente
  pela senha e pela chave de recuperação.
- Alternativa descartada: usar DPAPI do Windows ou `hashlib` puro. Motivo:
  DPAPI amarra ao login Windows e não permite senha escolhida; `hashlib` puro
  não oferece AES seguro. `cryptography` é a biblioteca padrão para isso.
- Decisão: instalar `cryptography` em ambiente virtual `gerenteneuron/.venv`
  via `setup-crypto.py`, sem poluir o Python global.
- Alternativa descartada: exigir que o usuário instale manualmente. Motivo:
  o processo precisa ser reproduzível e o usuário é leigo; um script de setup
  reduz erro.
- Decisão: o app mantém o cofre desbloqueado em memória do servidor após o
  usuário digitar a senha uma vez. Não armazena a senha nem a chave real em
  disco durante a execução.
- Alternativa descartada: pedir senha a cada requisição. Motivo: inviável
  para uma interface de chat; o servidor local é confiável enquanto rodar.
- Decisão: "esqueci a senha" funciona via chave de recuperação salva em
  `vault/recovery.key`. Sem essa chave, os dados são irrecuperáveis.
- Alternativa descartada: backdoor ou recuperação automática. Motivo:
  quebraria a segurança do cofre.

## 260816 — sincronização do GerenteNeuron com o repo público local
- Decisão: manter a pasta central `<PROJETOS_ROOT>\MEGA B R A I N` como
  fonte de trabalho e usar `_github/export/` como pacote público limpo.
- Alternativa descartada: editar diretamente dentro de `_github/repo-local/`.
  Motivo: a central guarda dados locais (`.venv`, `vault/`, `data/`,
  `projetos.json`) que não podem ir parar no repo.
- Decisão: sincronizar `_github/export/gerenteneuron/` →
  `_github/repo-local/gerenteneuron/` antes do commit.
- Alternativa descartada: commitar a central. Motivo: a central contém dados
  pessoais e ambiente virtual.
- Decisão: preservar `vault.py` no repo local mesmo ele não existindo no
  export, porque `app.py` e `mb-vault.py` importam dele.
- Alternativa descartada: remover `vault.py` e renomear `mb-vault.py`. Motivo:
  exigiria refatorar imports em vários arquivos sem necessidade nesta rodada.
- Decisão: commit local em `_github/repo-local/` agora; push remoto só com
  autorização explícita do usuário.
- Alternativa descartada: fazer push automático. Motivo: o repositório é
  público e pode conter ajustes que o usuário queira revisar antes de publicar.
- Decisão: atualizar `.gitignore` para ignorar `gerenteneuron/.venv/`,
  `gerenteneuron/vault/`, `gerenteneuron/data/`, `gerenteneuron/.env` e caches.
- Alternativa descartada: confiar apenas na exclusão manual. Motivo: o lock do
  `.venv` já havia sido commitado acidentalmente; `.gitignore` previne
  recorrência.

## 260816 — GerenteNeuron: preço como dado, não como código
- Decisão: criar `gerenteneuron/pricing.json` como fonte única de catálogo de
  modelos e preço por 1M de tokens, e derivar dele a ordem da fila do roteador.
- Alternativa descartada: manter `estimar_custo` dentro de cada provider e a
  lista `MODELOS_POR_ESTRATEGIA` escrita à mão em `router.py`. Motivo: eram
  cinco fontes divergentes; conferido em 2026-08-16 contra as páginas oficiais
  da Anthropic e do Google, os preços erravam por até 5× e metade dos IDs já
  tinha saído de linha, enquanto o app anunciava escolher o mais barato.
- Decisão: `pricing.json` carrega `verificado_em`, `revalidar_em_dias` e a URL
  da fonte de cada provedor; vencida a validade, o app mostra aviso no topo do
  chat e `mb-modelos.py --conferir` sai com código 1.
- Alternativa descartada: confiar em revisão manual periódica. Motivo: regra de
  ouro 21 — garantia real é script, não disciplina de markdown.
- Decisão: `mb-modelos.py --conferir` consulta a API viva de OpenAI, Gemini,
  Moonshot e Ollama e acusa modelo declarado que o provedor não oferece mais.
- Alternativa descartada: buscar preço automaticamente na web. Motivo: preço não
  é exposto por API; a conferência de catálogo é automatizável, a de preço não.
- Decisão: a Anthropic fica sem conferência automática, com a URL oficial no
  próprio JSON. Motivo: não há endpoint público de listagem.

## 260816 — GerenteNeuron: testes antes de qualquer nova função
- Decisão: `gerenteneuron/tests/test_gerenteneuron.py`, 32 casos em stdlib pura,
  cobrindo pricing, classificação, montagem de fila, propagação de histórico,
  checagem de origem HTTP, casamento de projeto e leitura da chave de
  recuperação. Roda com `testar.cmd`.
- Alternativa descartada: adotar pytest. Motivo: o achado M3 da auditoria v5.1
  foi exatamente prometer dependência que ninguém usa; `unittest` já basta.
- Decisão: teste escrito junto com a correção, não depois. Um dos casos
  encontrou falso positivo real no `gerente.py` no mesmo dia.
- Alternativa descartada: validar manualmente pelo navegador. Motivo: o app
  rodava e respondia com o chat sem memória — teste manual não pega isso.

## 260816 — GerenteNeuron: origem HTTP e superfície do cofre
- Decisão: o servidor recusa requisição com `Origin` ou `Host` fora do
  localhost, e ecoa a origem em vez de `Access-Control-Allow-Origin: *`.
- Alternativa descartada: manter CORS aberto por ser app local. Motivo: com o
  navegador como cliente, qualquer aba aberta conseguia POSTar em `/api/chat`
  e gastar as chaves, ou tentar senha no cofre em loop.
- Decisão: `/api/vault/unlock` trava 5 minutos após 5 senhas erradas.
- Alternativa descartada: confiar só no PBKDF2 de 600k iterações. Motivo: lento
  não é o mesmo que limitado; travar é barato e torna a tentativa ruidosa.
- Decisão: `recovery.key` ganha aviso no próprio arquivo mandando movê-lo para
  fora da pasta do cofre, e permissão 0600.
- Alternativa descartada: parar de gravar o arquivo e só imprimir a chave uma
  vez. Motivo: perder a chave significa perder os dados; o risco de não anotar
  é maior que o de ter o arquivo, desde que o aviso seja explícito.
- Decisão: `reset --recovery` aceita a chave crua ou o conteúdo inteiro do
  arquivo colado. Motivo: o cabeçalho de aviso fazia o paste legítimo falhar.

## 260816 — GerenteNeuron: nomes de arquivo de código sem prefixo de data
- Decisão: os módulos novos (`precos.py`, `pricing.json`, `mb-modelos.py`,
  `tests/`) entram sem prefixo `YYMMDD_`, seguindo a convenção já estabelecida
  dentro de `gerenteneuron/`.
- Alternativa descartada: aplicar `YYMMDD_` a todo arquivo tocado, conforme a
  regra geral do usuário. Motivo: renomear módulo Python quebra todo `import`
  que o referencia, e o achado B1 da auditoria v5.1 já classificou prefixo de
  data em executável chamado pelo nome como ruído. A regra continua valendo para
  documento acumulável (relatório, auditoria, entregável avulso).

## 260816 — GerenteNeuron: chave de recuperação nasce fora do cofre
- Decisão: `Vault.criar()` grava a chave de recuperação em
  `%USERPROFILE%\gerenteneuron-chave-de-recuperacao.txt` por padrão, e
  `setup-vault.py` recusa qualquer `--saida` dentro da pasta do cofre.
- Alternativa descartada: manter em `vault/recovery.key` e instruir o usuário a
  mover. Motivo: ninguém move arquivo depois — o default é o que fica. Cofre e
  chave na mesma pasta anulam a senha mestre para quem acessa o disco.
- Alternativa descartada: não gravar arquivo nenhum, só imprimir a chave uma
  vez. Motivo: perder a chave significa perder as credenciais; o risco de não
  anotar é maior que o de ter o arquivo num lugar seguro.
- Decisão: o app avisa no console e em `/api/vault/status` se encontrar um
  `recovery.key` remanescente dentro da pasta do cofre.

## 260816 — GerenteNeuron: instalador único
- Decisão: `configurar.py` / `configurar.cmd` faz venv, cofre, cadastro de keys,
  teste de conectividade e conferência de preço num comando só, idempotente.
- Alternativa descartada: manter os quatro scripts separados documentados no
  README. Motivo: o passo que mais importava para a segurança (mover a chave de
  recuperação) era o quinto item de uma lista — e o usuário não chegou nele
  porque a pasta do cofre nem existia ainda. Fricção de setup vira risco.
- Os scripts individuais continuam existindo para quem quiser o caminho manual.

## 260816 — relatório de projeto descobre toda fonte Markdown
- Decisão: `mb-relatorio-projeto.py` inclui automaticamente todo `.md`
  informacional da instância. `--extra` passa a ordenar/destacar fontes, não a
  ser uma lista manual obrigatória. Só `MEGABRAIN/`, `.git/`, caches e
  dependências são excluídos; `--sem-todos-md` exige escolha explícita.
- Alternativa descartada: criar outro relatório ou um Markdown-resumo para IA.
  Motivo: criaria uma segunda fonte de verdade e deixaria informação nova
  invisível sem manutenção manual. O Markdown é fonte; `RELATORIO.html` é a
  leitura única para pessoa e IA.

## 260816 — apresentação institucional segue a linguagem do MIMDE
- Decisão: aplicar ao `RELATORIO.html` institucional o sistema visual do
  console MIMDE — rail escuro, painéis por decisão, topbar, herói editorial,
  grade com bordas e vermelho de sinal — preservando os seis painéis e a
  hierarquia para quem ainda não conhece o MEGABRAIN.
- Alternativa descartada: copiar o HTML do MIMDE ou alterar apenas o CSS.
  Motivo: o MIMDE é uma console operacional de caixa e aquisição; o
  MEGABRAIN precisa explicar conceito, funcionamento, uso, habilidades,
  limites e fontes. A aparência é reaproveitada, a narrativa é própria.
- Decisão: apresentar relatório vivo, routers de projeto e GerenteNeuron como
  capacidades atuais no painel "Na prática".
- Alternativa descartada: manter apenas exemplos genéricos de serviço/design.
  Motivo: o relatório deve mostrar as habilidades que existem, sem prometer
  autonomia externa ou esconder o humano nos gates.

## 260816 — tema opt-in para relatórios de projeto
- Decisão: adicionar `--tema megabrain` a `mb-relatorio-projeto.py`. Ele aplica
  a linguagem visual MIMDE/MEGABRAIN sem modificar o layout padrão do gerador.
- Alternativa descartada: trocar o CSS padrão de todos os relatórios ou criar
  um HTML manual exclusivo por projeto. Motivo: a primeira opção muda projetos
  sem pedido; a segunda recria uma saída que diverge da fonte Markdown.

## 260818 — workflow de alinhamento entre Claude e Kimi para skills compartilhadas
- Decisão: criar `ALINHAMENTO-AGENTES.md` na central do megabrain como ponto de
coordenação para skills e comandos usados pelo <USUARIO> em ambos os agentes.
Ambos leem e escrevem no mesmo arquivo, usam `mb-sync.py` para travar, e
registram skills em coordenação com status, editor, data e revisão pendente.
Toda skill compartilhada vive em `<USER_HOME>/.kimi-code/skills/<nome>/SKILL.md`
(um único lugar), independentemente de quem a criou.
- Alternativa descartada: cada agente manter sua própria cópia de skills em
pastas separadas ou depender de memória de sessão. Motivo: isso reproduziria o
problema atual — entregas invisíveis para o outro agente, duplicidade e perda de
contexto entre sessões.
- Decisão: antes de criar uma skill, o agente deve verificar se ela já existe;
se existir, auditar e editar incrementalmente; se não existir, criar e registrar
em `ALINHAMENTO-AGENTES.md`.
- Alternativa descartada: permitir reescritas do zero sem justificativa. Motivo:
escrever por cima de uma skill existente apaga decisões e lições acumuladas do
outro agente.

## 260818 — merge específico de /logout-projeto e /sync-portfoliohs entre Claude e Kimi
- Decisão: as skills `/logout-projeto` e `/sync-portfoliohs` foram fundidas a
partir de duas fontes — a versão original do Claude (skills de conta,
`/root/.claude/skills/synced/`) e a versão criada do zero pelo Kimi em
`<USER_HOME>/.kimi-code/skills/`. A versão final unificada foi gravada em
`<USER_HOME>/.kimi-code/skills/logout-projeto/SKILL.md` e
`<USER_HOME>/.kimi-code/skills/sync-portfoliohs/SKILL.md`. A cópia de
trabalho/disco comum é o único lugar que o Kimi lê ao vivo; a cópia de conta do
Claude só se atualiza quando o <USUARIO> salva o `.skill` correspondente na
conta dele.
- Alternativa descartada: considerar as duas versões como iguais sem revisão, ou
deixar cada agente com sua própria cópia. Motivo: a versão do Kimi para
`/sync-portfoliohs` continha 2 erros de fato (site de produção e CMS ativo) que
só a versão do Claude corrigia; sem merge, o Kimi propagaria erros em sessões
futuras.
- Decisão: quando uma skill compartilhada tiver versão em skills de conta do
Claude e versão em disco do Kimi, o merge deve ser feito na cópia de disco, e o
Claude deve entregar a mesma versão em chat para o <USUARIO> atualizar a conta.
- Alternativa descartada: sincronização automática entre conta Claude e disco
local. Motivo: não há API/meio automático disponível; o canal é manual via
arquivo entregue em chat.

## 260818 — mb-sync-projeto-para-central.py e mb-check-version.py: merge em vez de replace
- Decisão: os dois scripts de sync (`bin/mb-sync-projeto-para-central.py`,
projeto→central, e `bin/mb-check-version.py`, central→projeto) faziam
`rmtree` + `copytree` em toda pasta do MAPEAMENTO (principalmente
`referencias/`) antes de copiar. Isso apaga qualquer arquivo do destino que
não exista na origem — ex.: um projeto que sincroniza pra central com um
`MEGABRAIN/referencias/` enxuto apagaria o `referencias/` genérico da
central (anti-slop.md, context-engineering.md etc.), e vice-versa. Troquei
os dois por `shutil.copytree(src, dst, dirs_exist_ok=True)` — merge real:
sobrescreve arquivo com o mesmo nome (a origem continua sendo fonte da
verdade pro que ela de fato tem), preserva o que só existe no destino.
`mb-check-version.py` manteve a checagem de `resolve_within`/`base` antes de
escrever (proteção contra escrever fora da pasta do projeto).
- Alternativa descartada: manter `rmtree`+`copytree` e só documentar o risco
em nota, sem corrigir o script. Motivo: o <USUARIO> pediu correção real
("armadilha real, não teórica") — documentar sem corrigir deixa a mesma
armadilha pronta pra disparar na próxima sincronização de qualquer projeto.
- Testado: `mb-check-version.py --projeto ".../Portfólio - <AUTOR>"
--auto --offline` rodou limpo, criou `MEGABRAIN/` do zero no projeto
(primeira sincronização, sem destino prévio — mesmo caminho de código do
merge, sem erro).


## 260818 — contrato de resposta único propagado a todos os agentes
- Decisão: criar `referencias/260818_padrao-resposta.md` como contrato canônico
genérico de voz, níveis de detalhe, entendimento de projeto e ações; injetar a
versão condensada no arquivo de identidade `260810_memoria-pessoal.md` e
propagar para todos os agentes via `mb-sync-memoria.py`.
- Alternativa descartada: manter um output style/AGENTS.md separado por agente.
Motivo: fonte única evita divergência; agente novo recebe o bloco, não uma
adaptação manual.

## 260818 — canais de entrega do contrato por agente
- Decisão: Kimi, Gemini e Codex recebem o contrato pelo bloco AUTO-SYNC em seus
arquivos de memória global (`~/.kimi-code/AGENTS.md`, `~/.gemini/GEMINI.md`,
`~/.codex/AGENTS.md`); Claude recebe o bloco em `~/.claude/CLAUDE.md` mais o
output style `~/.claude/output-styles/megabrain.md` com
`keep-coding-instructions: true`, que entra no system prompt.
- Alternativa descartada: migrar todos para um único `AGENTS.md` cross-agent.
Motivo: Claude Code não lê `AGENTS.md` nativamente; output style é o mecanismo
mais forte disponível para padronizar a forma de responder dele.

## 260818 — resolução da divergência "caixa alta" no formato de resposta
- Decisão: a primeira frase de cada parte resume a parte inteira, **sem**
caixa alta. A regra 17 de `MEGABRAIN.md` continua valendo assim. A lição
260804 que pedia "CAIXA ALTA" fica histórica, mas o padrão atual é sem caixa
alta.
- Alternativa descartada: manter a caixa alta da lição 260804. Motivo: é
agressivo visual, inconsistente com a regra 17 e não melhora a clareza.

## 260818 — fonte do plugin Kimi na central
- Decisão: criar `plugin-megabrain/` na central contendo `SYSTEM.md`,
`kimi.plugin.json`, `hooks/`, `commands/`, `seed/`, `skills/megabrain-core/` e
`skills/registrar-licao/`; a pasta é replicada para o plugin gerenciado pelo
`260824_sincronizar-projetos.cmd`.
- Alternativa descartada: deixar esses arquivos apenas no plugin gerenciado em
`<USER_HOME>/.kimi-code/plugins/managed/megabrain/`. Motivo: sem fonte na
central, o plugin não é reproduzível e vira ponto único de falha.

## 260818 — plugin-megabrain fora do pacote público por ora
- Decisão: adicionar `plugin-megabrain` ao `EXCLUIR` de
`bin/mb-generate-template.py`, de modo que o wrapper do plugin não vá para o
pacote público até decisão explícita.
- Alternativa descartada: publicar o wrapper automaticamente junto com o resto
do export. Motivo: o wrapper contém configurações locais (hooks, paths) cuja
sanitização e publicação merecem revisão e decisão do usuário.

## 260818 — teste de permissão do cofre no Windows
- Decisão: a asserção de bits POSIX de `dados.enc` em
`gerenteneuron/tests/test_gerenteneuron.py` foi envolvida em
`if os.name != "nt"`, com comentário explicando que `chmod` no Windows não
aplica ACL e que `%USERPROFILE%` já tem ACL por usuário no NTFS. Não foi
adicionado `icacls` ao `vault.py`.
- Alternativa descartada: implementar chamada a `icacls` dentro de
`_restringir()`. Motivo: aumenta complexidade, depende de NTFS e pode falhar em
sistemas de arquivo que não suportam ACL; o ganho real de segurança é baixo
num perfil de usuário do Windows.

## 260818 — inclusão de Codex e output style na sincronização de identidade
- Decisão: os `.cmd` de instalação/sincronização de identidade passam a
escrever `~/.codex/AGENTS.md` e a gerar `~/.claude/output-styles/megabrain.md`
além dos quatro destinos anteriores.
- Alternativa descartada: deixar Codex fora do sync. Motivo: o usuário usa
Codex e o contrato de resposta precisa chegar a todos os agentes sem exceção.

## 260819 — retrabalho v6: escopo B (fases 0+1) e alinhamento com o <USUARIO>
- Decisão (<USUARIO>): executar a v6 em escopo B — fase 0 (fundação) + fase 1
(observabilidade) agora; fases 2-4 decididas depois, com dados reais de uso.
- Alternativa descartada: escopo A (fases 0-4 de uma vez). Motivo: o ponto
fraco medido do megabrain é a ausência de sinal de feedback; observabilidade
primeiro permite decidir o resto com dados em vez de suposição.
- Decisão (<USUARIO>): alinhamento pré-prompt em TODO prompt, com chave de
desligar por projeto/sessão. Implementação fica na fase 2 (junto do META.md).
- Alternativa descartada: só no prompt de abertura de tarefa. Motivo: o
<USUARIO> prefere alinhamento máximo; a rodada extra é aceita e a chave de
desligar cobre projetos nível 1.
- Decisão (<USUARIO>): logs de prompt/resposta em .mb-log/ sem limite de
retenção; poda manual.
- Alternativa descartada: 30 ou 90 dias com poda automática. Motivo:
histórico completo vale mais; o custo é só disco local.
- Decisão (<USUARIO>): mb-orquestrador-ia.py será fundido no GerenteNeuron
como modo (fase 4), não aposentado.
- Alternativa descartada: aposentar com backup. Motivo: preservar a
funcionalidade de orquestração multi-IA já construída.

## 260819 — v6 fases 0+1: decisões técnicas de implementação (claude)
- Decisão: evento com cwd fora da raiz de projetos cai em
<central>/.mb-log/fora-de-projeto/ em vez de criar .mb-log no cwd.
- Alternativa descartada: gravar sempre no cwd. Motivo: não espalhar pastas
de log por diretórios que não são projeto.
- Decisão: encoding UTF-8 de console virou função única u.utf8_console() em
mb_utils, chamada em 14 scripts CLI (inline só no orquestrador, que tem
sys.path próprio).
- Alternativa descartada: reconfigure inline em cada script. Motivo: um
lugar só pra manter; bin/ viaja completo nas cópias, então o import é seguro.
- Decisão: hook do Codex adiado — nenhum mecanismo de hook foi verificado no
Codex CLI instalado.
- Alternativa descartada: configurar notify no config.toml sem testar.
Motivo: a lição mais repetida do projeto é "registrado != disco"; não se
declara integração não testada.
- Decisão: a seção "atividade" do painel entrou como grupo de comandos
(MECANICAS), não como dados embutidos no HTML.
- Alternativa descartada: embutir os números no painel. Motivo: dado vivo
mora no RELATORIO-AGENTES.html, que regenera barato; o painel é hub.

## 260819 — v6 fases 2-4: decisões técnicas de fechamento (claude)
- Decisão: o juiz de meta (mb-checar-meta.py) usa format=json do Ollama e
recusa resposta fora do formato (exit 3, sem veredito).
- Alternativa descartada: parse de texto livre. Motivo: o qwen 2-bit ecoou a
instrução no primeiro teste e o parse ingênuo gravaria um falso DESVIO.
- Decisão: modelo default do scoring é qwen3.8-2bit-ptbr (override via
MEGABRAIN_MODELO_SCORING).
- Alternativa descartada: 27b-q4km. Motivo: 17 GB competem com
Figma/Photoshop na RTX 4070; o scoring é heurístico, não precisa do maior.
- Decisão: alinhamento pré-prompt implementado como instrução injetada por
hook (mb-contexto.py) na 1ª mensagem da sessão + lições por proximidade a
cada prompt com dedup por sessão.
- Alternativa descartada: reinjetar a instrução completa a cada prompt.
Motivo: custo de contexto por mensagem; a instrução vale pra sessão inteira
e as lições é que variam por prompt.
- Decisão: gate de drift compara export↔repo-local por hash direto e
central↔export por manifesto de hash da fonte gravado na geração.
- Alternativa descartada: hash direto central↔export. Motivo: o export é
sanitizado — nunca bateria; seria falso-positivo perpétuo.
- Decisão: aposentadoria de lição = mover pra seção "LIÇÕES APOSENTADAS"
com motivo e sucessor; o índice pula aposentadas; nunca deletar.
- Alternativa descartada: deletar a lição contraditória. Motivo: apagaria a
história do erro — o único conteúdo valioso do registro.
- Decisão: fusão do orquestrador = gerenteneuron/orquestrador.py com
defaults de pricing.json; bin/mb-orquestrador-ia.py vira stub que delega.
- Alternativa descartada: apagar o caminho antigo. Motivo: comandos
documentados em diálogos/notas antigas continuariam quebrando.
- Decisão: bin/.orquestrador/, PROGRESSO.json, RELATORIO-VIVO.html e META.md
da central ficam fora do export público.
- Alternativa descartada: sanitizar os diálogos antigos do orquestrador.
Motivo: são artefato de execução, não documentação — sanitizar dado morto
não paga o risco de vazamento.


## 260821 — plugin Cowork megabrain v1.1.0 versionado no repo (kimi)
- Decisão: o plugin Cowork/Claude mora em `_github/repo-local/plugin-megabrain-claude/`
  (raiz do repo), irmão lógico do `plugin-megabrain/` (Kimi).
- Alternativa descartada: `plugin-megabrain-claude/` só na central, fora do
  git. Motivo: a nota 260821 pedia explicitamente o plugin DENTRO do
  repositório pra não depender de sessão de chat pra reconstruir.
- Decisão: plugin reconstruído das fontes versionadas em vez de importar o
  `.plugin` baixado da conversa Cowork — o arquivo não foi encontrado nesta
  máquina (varredura completa). Skills = cópia 1:1 das fontes com as linhas
  declaradas editadas (diff conferido); hook reescrito pela especificação da
  nota (núcleo megabrain-core + lições por recência/mtime, sem embeddings,
  sem memória global por usuário).
- Alternativa descartada: parar e pedir o `.plugin` ao <USUARIO> antes de
  agir. Motivo: sessão em modo automático; a reconstrução das fontes elimina
  por construção qualquer divergência acidental da sessão Cowork, e o hook
  original fica marcado como "auditar se reaparecer" no README do plugin.
- Decisão: núcleo injetado pelo hook Cowork = texto de `megabrain-core` com 3
  ajustes mínimos de perspectiva/roteamento ("com o outro agente", skill
  `registrar-licao`, skill `megabrain`).
- Alternativa descartada: injetar o texto literal do megabrain-core. Motivo:
  o literal fala "compartilhado com o Claude" e cita comandos `/megabrain:*`
  que não existem no Cowork.
- Decisão: `git fetch` do Kimi passa; o 403 era do bridge Cowork. Remoto
  real confirmado: origin/main = e95ce00.
- Alternativa descartada: tratar o sync como não confirmado. Motivo:
  `git ls-remote origin HEAD` retornou o hash igual ao local — evidência
  direta, não cache.
- Achado sem ação (registrado, não executado): `plugin-megabrain/` (Kimi)
  não é versionado no repo — vive só na central. E as skills da conta Cowork
  (`synced/logout-projeto, modeloslocais, tlou`) não existem nesta máquina;
  resíduo `.metaprotocolo\licoes.md` só existia na cópia Kimi do
  logout-projeto (corrigido). Cópias Cowork seguem sem verificação.


## 260821 — auditoria do commit a7cfc7a (kimi) e correções de pipeline (claude)
- Decisão: a FONTE do plugin Cowork/Claude mora na central
  (`plugin-megabrain-claude/`); o repo público recebe a cópia derivada pelo
  `mb-generate-template.py`, como todo o resto do pacote.
- Alternativa descartada: manter o plugin direto em `_github/repo-local/`
  (onde o Kimi colocou). Motivo: o repo-local é espelho gerado — o
  `260824_publicar-e-fotografar.cmd` faz robocopy /MIR do export e apagaria a pasta
  na próxima publicação; além disso o gerador excluía `plugin-megabrain` por
  substring, então o plugin jamais entraria pelo caminho oficial. Registrado
  != disco, de novo.
- Decisão: as duas skills do plugin são DERIVADAS das fontes por
  `bin/mb-build-plugin-claude.py` (edições declaradas em código, `--check`
  acusa drift); só hook, manifesto e README são editados direto no plugin.
- Alternativa descartada: cópia editada à mão (como estava). Motivo: a lição
  mais repetida do projeto é cópia que drifta; derivação por código é
  garantia, edição manual é pedido.
- Decisão: fonte do plugin sem identificador pessoal (autor `iriqspina`,
  "autorização permanente dada na instalação" em vez do nome) — a cópia
  pública ainda passa pelo sanitizador, mas a fonte já nasce limpa.
- Alternativa descartada: confiar só no sanitizador. Motivo: o commit
  `a7cfc7a` provou que arquivo escrito direto no repo-local pula o
  sanitizador e vaza (11 linhas com nome/apelido/caminho local num repo que
  tinha zero).
- Decisão: o histórico do git NÃO foi reescrito nesta sessão; o working tree
  está limpo a partir deste commit e a decisão de force-push é do <USUARIO>
  (HANDOFF, PARA VOCÊ #4).
- Alternativa descartada: force-push automático. Motivo: reescrever `main`
  de um repo público sem o dono presente viola o Gate 0 item 5 (nada sobe pra
  git sem confirmação) e pode quebrar clones.
- Decisão: gerador — `plugin-megabrain/` e `.claude/` passam a ser excluídos
  COM barra; `*.plugin` excluído por sufixo; a forma com barra invertida do
  caminho local é derivada da forma com barra (`.replace("/", "\\")`).
- Alternativa descartada: deixar os literais. Motivo: `.claude` solto
  casava com `.claude-plugin/` (plugin.json ficava fora do pacote) e o
  literal `"S:\\projetos..."` no código escapava da própria sanitização — o
  caminho estava público desde a primeira publicação do gerador.
- Decisão: nota `260821_pendencia-nome-metaprotocolo-residual.md` sai do repo
  e vai pra `alteracoes-pendentes/260821-pendencia-nome-metaprotocolo/` com
  `DONO:`; o conteúdo original foi preservado integralmente + fechamento.
- Alternativa descartada: manter no repo "porque a nota pedia o plugin dentro
  do repositório". Motivo: o pedido era sobre o PLUGIN, não sobre a nota; a
  nota é narrativa pessoal e `alteracoes-pendentes/` é a fila com dono que o
  relatório vivo já acompanha (e o robocopy /MIR apagaria o arquivo de
  qualquer jeito).

## 260821 — v6.1: versão visível no relatório vivo e nos relatórios de projeto (claude)
- Decisão (<USUARIO>): topo do `RELATORIO-VIVO.html` mostra versão ATUAL do
  megabrain (VERSAO.txt) + commit local + origin/main conhecido + commits sem
  push, a versão ANTERIOR, e uma tabela com a versão que cada projeto puxou;
  o HTML anterior é guardado em `.mb-backup/relatorio-vivo/` sempre que
  versão ou commit mudam. `RELATORIO.html` de projeto abre com "puxou ×
  atual × estado".
- Alternativa descartada: snapshot do HTML a cada regeneração. Motivo: o
  relatório regenera a cada `--nota`/`--marcar` (e o navegador recarrega a
  cada 15s) — acumularia centenas de cópias iguais; a troca de versão/commit
  é o evento que importa. `--snapshot` força quando quiser.
- Decisão: a origem do pull fica em `MEGABRAIN/.mb-origem.json` (versão,
  commit da central, data), gravado pelo `mb-check-version.py`.
- Alternativa descartada: só VERSAO.txt na cópia. Motivo: VERSAO.txt diz a
  versão declarada, não o commit — e "registrado != disco" pede o hash.
- Decisão: card "PARA VOCÊ — o que fazer agora" no relatório vivo lê a seção
  `## PARA VOCÊ` do HANDOFF.md (fonte única; sem arquivo novo).
- Alternativa descartada: lista própria no PROGRESSO.json. Motivo: duplicaria
  estado que já mora no handoff, e o handoff é o que o próximo agente lê.
- Decisão: hora do relatório vivo exibida com dia/mês (`%d/%m %H:%M:%S`).
  Motivo: página que fica aberta por dias precisa dizer de que dia é o retrato.

## 260821 — mb-abertura: escrever o preflight, aposentar os scripts de rename (claude)
- Decisão: `bin/mb-preflight.py` escrito (git / skills instaladas vs fonte /
  fatos com `verificado_em` / resíduo de nome antigo; cache 8h em
  `.megabrain/`, ignorado pelo git; exit 0/2). A doc da `mb-abertura` deixa de
  citar `mb-renomear.py`, `mb-padronizar.py` e `MEGABRAIN-PADRONIZAR.cmd`.
- Alternativa descartada: escrever também os 3 scripts de renomeação.
  Motivo: a renomeação já foi feita à mão (Kimi varreu o local, esta sessão a
  conta e a fonte; skill central v5.1 sem gatilhos legados) — seriam scripts
  pra um problema que não existe mais; o cheque `legado` do preflight é o
  que garante que não volta.
- Decisão: no cheque `legado`, derivados que embutem texto de lição/decisão
  (PAINEL, RELATORIO-AGENTES, índices), backups e congelados (PIPELINE.md)
  contam como reconhecimento deliberado, não resíduo.
- Alternativa descartada: acusar tudo. Motivo: o preflight nunca daria
  `limpo` por causa de histórico que, por decisão anterior, não se apaga.

## 260821 — assimetria plugin Kimi × plugin Claude no repo (claude)
- Decisão: o repo versiona só o `plugin-megabrain-claude/`; o
  `plugin-megabrain/` (Kimi) segue fora do pacote (decisão 260818 mantida).
- Alternativa descartada: "os dois ou nenhum". Motivo: o plugin Claude
  precisa viajar como `.plugin` pra ser instalado e, sem fonte versionada, é
  reconstruído de chat (foi o que aconteceu 2× em 260821); o plugin Kimi é
  instalado por `260824_sincronizar-projetos.cmd` direto da central e carrega hooks
  com caminhos locais. Critério: o que precisa viajar, viaja.

## 260821 — hook do plugin não roda no Cowork cloud (claude)
- Achado verificado: com o plugin `megabrain` v1.0.0 instalado na conta, o
  hook SessionStart não executou nesta sessão Cowork cloud (o arquivo
  `~/.megabrain/licoes.md` que ele cria na 1ª execução não existia; nenhum
  contexto "megabrain — ativo nesta sessão" injetado). As skills do plugin
  carregam (`megabrain:megabrain`, `megabrain:registrar-licao`).
- Decisão: o hook fica no plugin (vale em Claude Code CLI / Desktop), mas a
  skill `megabrain` continua mandando ler as lições no Gate 0 e o README do
  plugin declara o limite. A validação "numa sessão Claude de verdade"
  pendente desde o Kimi não vai acontecer no Cowork; acontece no Claude Code.
- Alternativa descartada: tirar o hook. Motivo: custo zero onde não roda,
  valor real onde roda.

## 260821 — classificação dos 40 arquivos do `legado` (preflight) + bug de separador (kimi)
- Achado (bug): `LEGADO_PERMITIDO` usa tags com `/` mas o Windows monta
  caminho com `\` — `str(p)` nunca casava, e 8 arquivos permitidos vazavam
  como resíduo (4× `registrar-licao/SKILL.md`, 2× `plugin-megabrain-claude/
  README.md`, +2 cópias derivadas). Correção: `rel = p.as_posix()` antes do
  match. 40 → 32.
- Alternativa descartada: duplicar as tags com `\`. Motivo: duas formas da
  mesma tag é convite a drift; normalizar o caminho é uma linha.
- Classificação dos 40 (e dos 32 restantes):
  (a) memória/log de agente — 8 arquivos em `~/.codex/memories/`
      (MEMORY.md, memory_summary.md, raw_memories.md, 5 rollout_summaries
      de 260815). Decisão: NÃO apagar nem reescrever nesta sessão — log
      append-only de outro agente, fora do escopo autorizado (S:\), e
      reescrever histórico é o que o megabrain condena em DECISOES.md.
      Ressalva: MEMORY.md é memória VIVA do Codex (carrega em sessão); se o
      nome antigo voltar a influenciar comportamento, a limpeza é editar o
      nome ali, não apagar. ABERTO no HANDOFF pra decisão do <USUARIO>.
  (b) derivado gerado (PAINEL, RELATORIO-*, índices, backups): NÃO estava
      vazando — já era reconhecimento deliberado. O vazamento real era o bug
      de separador acima, corrigido.
  (c) fonte viva datada (`referencias/260804_*.md` da central): LIMPA, não
      aparece no resíduo. As ocorrências de `260804_*.md` no resíduo são
      cópias DENTRO do plugin velho (cache e instalado) — morrem com a
      desinstalação, não com edição. Nenhuma fonte viva tocada.
  (d) plugin velho ainda presente — 24 arquivos: cache
      `~/.codex/plugins/cache/claude-cowork/` (metaprotocolo 0.3.0 +
      anthropic-skills 1.0.0, 12 arq.) e plugin `metaprotocolo` ainda
      INSTALADO no Kimi CLI (`~/.kimi-code/plugins/managed/metaprotocolo/` +
      `installed.json`, 12 arq.). É resíduo real e o veredito PENDÊNCIA é a
      realidade: sai com a desinstalação (PARA VOCÊ #1, do <USUARIO> — conta
      Cowork e home dir fora do escopo da sessão).
- Alternativa descartada (para (d)): apagar o plugin velho do Kimi CLI e o
  cache do Codex nesta sessão. Motivo: fora do escopo autorizado de escrita
  (<PROJETOS_ROOT>\) e a remoção certa inclui a conta Cowork — é a
  ação do PARA VOCÊ #1, já do <USUARIO>.
- Veredito final do preflight: PENDÊNCIA com 32 arquivos = resíduo real
  localizado (memória do Codex + plugin velho). Antes: 40 com 8 inocentes.

## 260821 — sync de identidade: alvo `codex` existia no .cmd mas não no script (kimi)
- Decisão: `mb-sync-memoria.py` ganha o target `codex` (`AGENTS.md`) nas
  choices e no TARGET_FILE — os dois `.cmd` de identidade já chamavam
  `--target codex` desde 260818 e falhavam em silêncio (usage error). Os 6
  alvos foram rodados e verificados por conteúdo (bloco AUTO-SYNC idêntico à
  fonte + `USUARIO:`): CLAUDE.md, GEMINI.md, .kimi/AGENTS.md,
  .kimi-code/AGENTS.md, .codex/AGENTS.md, output-styles/megabrain.md.
- Alternativa descartada: tirar a linha `codex` dos `.cmd`. Motivo: o Codex é
  um dos agentes do <USUARIO> (decisão 260818); o errado era o script, não o
  chamador. `--target all` NÃO ganhou codex: mudaria o comportamento de
  chamadores existentes (mb-painel.py) sem necessidade — a fila explícita
  dos `.cmd` já cobre.
- Registro do ciclo 260818: VERSAO.txt ganhou a entrada retroativa v5.2
  (identidade + alinhamento multi-agente); DECISOES.md já tinha as 10
  entradas de 260818 — a lacuna era só de versão.

## 260821 — validação do plugin-megabrain-claude no Claude Code CLI (kimi)
- Achado: Claude Code CLI 2.1.221 instalado (`~/.local/bin/claude.exe`), plugin
  NÃO instalado (só figma no installed_plugins.json). Validação possível feita:
  (1) `claude plugin validate` no manifesto — passou; (2) hook
  `260821_session-start.js` rodado direto com `CLAUDE_PROJECT_DIR` apontando
  pra central — JSON SessionStart correto, núcleo injetado + lições do
  `licoes-megabrain.md` da central (7,5 KB); (3) smoke test interno do
  `mb-build-plugin-claude.py` — passou.
- BLOQUEIO (ABERTO): a prova end-to-end (`claude --plugin-dir ... -p`) falhou
  com "OAuth session expired" — relogar o Claude Code é ação do <USUARIO>.
  Depois do login, a validação é 1 comando (está no HANDOFF).
- Alternativa descartada: instalar o plugin no `installed_plugins.json` na mão
  pra testar sem API. Motivo: falsifica o estado de instalação do usuário e
  o teste continuaria sem provar o hook rodando de verdade.

## 260821 — SKILL.md v5.2: alinhamento ao fluxo v6 dos hooks (kimi)
- Decisão: Gate 0 da `skills/megabrain/SKILL.md` ganha a subseção "O que os
  hooks já injetam (v6)" — descreve o `mb-contexto.py` no UserPromptSubmit
  (1ª msg: META.md + alinhamento pré-prompt + top-5 lições por proximidade,
  corte 0,55; depois só novidades; vazio = custo zero), onde cada agente lê
  (settings.json do Claude / plugin Kimi / SessionStart do plugin Claude), e
  a regra "se o hook injetou, não releia". Gate 7 registra que a lição
  gravada alimenta o índice (`mb-indice-licoes.py`, recorrência 3×+ em
  `dna/licoes-recorrencia.json`).
- Alternativa descartada: seção nova fora dos gates. Motivo: o comportamento
  muda o que o agente faz no Gate 0 (não reler o que já veio) e no Gate 7
  (por que registrar) — a informação mora onde muda a ação.
- Propagação: `mb-build-plugin-claude.py` rederivou as skills do plugin
  (drift zero), `260824_publicar-e-fotografar.cmd` regenerou export + espelho +
  commit local `3fb7233` (v6.1+fixes) — push segue com o <USUARIO>.

## 260821 — stdin de hooks em bytes + utf-8-sig (mb-observar, mb-contexto) (kimi)
- Decisão: `mb-observar.py` e `mb-contexto.py` passam a ler o payload do hook
  via `sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")`.
  Corrige o teste `test_payload_com_bom_e_aceito`, vermelho nesta máquina
  desde antes desta sessão (não foi esta sessão que quebrou — o diff do
  commit prova; o "25/25" de 260819 era ambiente-dependente).
- Alternativa descartada: mexer no teste ou exigir PYTHONUTF8=1 no ambiente.
  Motivo: o hook roda sob a codepage que o console tiver; o script é que tem
  que ser imune — lição 260818 aplicada à entrada, não só à saída.
- Verificação: suíte 25/25 verde depois da correção; hook mb-contexto testado
  na mão com payload JSON (exit 0, contexto injetado).
- Também corrigido: `mb-build-plugin-claude.py` — `subprocess.run(text=True)`
  sem `encoding="utf-8"` matava o smoke test no Windows (reader thread
  cp1252); export regenerado de novo + commit local `5f9da50`.

## 260821 — redistribuição v6.1 pós-push (kimi)
- Fato: push da v6.1 confirmado (`git ls-remote`: origin/main = c17d35f =
  HEAD na época). `260824_sincronizar-projetos.cmd` rodado: 16 projetos OK; os 16
  receberam `MEGABRAIN/.mb-origem.json` via `mb-check-version.py --force`
  (o .cmd copia arquivos mas não grava a origem — só o script grava).
  Tabela do RELATORIO-VIVO.html: todos v6.1, commit c17d35f, estado "atual".
- Ressalva registrada: o aviso "DRIFT DETECTADO" dentro do .cmd é falso
  positivo sob Git Bash (o `chcp 65001` quebra o parse das linhas seguintes,
  o `python` embutido vira erro e o errorlevel dispara o aviso). O gate real
  (`python bin/mb-check-version.py --gate-drift` direto) passou antes e
  depois. Não corrigido nesta sessão (o .cmd roda certo em cmd.exe/PowerShell
  comum; o desvio só aparece quando invocado pelo Git Bash).

## 260822 — camada de conteúdo: cerebro/ + /ingerir (claude)
- Decisão: separar memória de **processo** (lições, decisões, estado) de memória de
  **conteúdo** (`cerebro/`: `raw/` fonte imutável → `/ingerir` → `wiki/` um tópico por
  arquivo + `pessoas/` + `INDICE.md`). Em cada projeto e na central; o Gate 0 cria o
  esqueleto (`mb-check-version.py` → `garantir_cerebro`). Nomes em PT-BR (pessoas/, não
  people/) — coerente com referencias/, modelos/, licoes. Decidido com o <USUARIO> (3
  perguntas, 260822).
- Alternativa descartada: Obsidian (tweet do @Bober_smart). Motivo: camada a mais
  entre o agente e o arquivo, contradiz o próprio artigo e a lição 260816 ("app local
  não precisa de framework"). Outra descartada: migrar `referencias/` e `licoes` pro
  formato wiki — já funcionam, já estão indexadas; migrar é custo sem ganho.
- Alternativa descartada: cerebro só na central. Motivo: briefing e cliente são do
  projeto; `/ingerir` lê os dois, regra "serviria em projeto diferente? → central".
- Propagação: `MAPEAMENTO` += `skills/ingerir/SKILL.md`, `modelos/`; `scripts/
  260824_sincronizar-projetos.cmd` copia skill + modelos + `mb-indice-cerebro.py` e roda
  `--so-cerebro` por projeto. `cerebro/` em `EXCLUIR` do gerador (nunca vai pro GitHub).

## 260822 — hook injeta páginas do cérebro (claude)
- Decisão: `mb-contexto.py` injeta até 3 páginas de `cerebro/` (score ≥ 0,55, só
  inéditas na sessão) em bloco próprio, com a instrução de citar path / dizer "não
  encontrado no cérebro". Reusa `mb-indice-licoes.py` (embed, cosseno, keyword) via
  import — um motor, dois índices (`dna/indice-licoes.json` e `<cerebro>/.indice-cerebro.json`).
- Alternativa descartada: um índice único misturando lições e páginas. Motivo: lição
  é "faça assim", página é "isso é verdade" — misturar na injeção confunde o agente
  sobre o que é regra e o que é fato.

## 260822 — raiz arrumada com mb-arrumar.py v2 (claude)
- Decisão: executáveis → `scripts/`, congelados → `_arquivo/`, instaláveis → `dist/`,
  referências sem data (4 divergentes = fork, regra 12) → `_arquivo/referencias-v1/`,
  2 idênticas + LEIAME.md/LEIAME.txt/requirements.txt → `_to_delete/`. Mover não
  renomeia (arquivo datado continua datado; canônico continua sem data — decisão
  260816 "prefixo de data não serve a arquivo canônico"). `remover` nunca apaga: vai
  pra `_to_delete/` (o bridge não apaga e o humano esvazia).
- Alternativa descartada: mover também os RELATORIO*.html/PAINEL pra `relatorios/`.
  Motivo: 4 scripts escrevem na raiz e o RELATORIO-VIVO fica aberto no navegador do
  <USUARIO> — mudar caminho quebra o hábito; fica pra um ciclo próprio.
- Verificação: `mb-arrumar.py --verificar` sem órfão; patches de `%~dp0..\` nos .cmd
  conferidos contra o texto real antes de aplicar; suíte 25/25; gate de drift
  regenerado.
- Efeito colateral corrigido: `mb-sync-memoria.py --target all --dir .` criou
  CLAUDE.md/GEMINI.md/AGENTS.md na raiz da central (modo import) — movidos pra
  `_to_delete/260822_sync-engano/`; o alvo certo na central é `.claude/CLAUDE.md`
  (`--target claude --dir .claude --modo conteudo`). Os alvos do home continuam com
  `scripts/260824_sincronizar-identidade.cmd` (PARA VOCÊ).

## 260822 — raiz zero: canônicos em pastas, resolvedor único (claude)
- Decisão (pedido do <USUARIO>: "nenhum arquivo solto"): `nucleo/ estado/
  identidade/ relatorios/` na central; `.gitignore` e pastas-ponto ficam.
  Um resolvedor (`mb_utils.achar`, tabela `PASTAS_RAIZ`) em vez de trocar
  caminho a caminho — os 16 projetos, o export público e qualquer central
  antiga continuam planos e funcionam sem mudança.
- Alternativa descartada: `docs/` única pra tudo. Motivo: mistura documento
  que muda toda sessão (estado/) com o que só muda em release (nucleo/) —
  e o gate de drift/manifesto olha só nucleo/.
- Alternativa descartada: export com a mesma árvore de pastas. Motivo: o
  GitHub só renderiza README na raiz e as cópias de projeto seguem o layout
  do pacote; o gerador achata as 4 pastas e o pacote público não muda.
- Alternativa descartada: mover `.gitignore`. Motivo: git exige na raiz.
- Risco aceito: scripts que o <USUARIO> tem instalados no home (hook do Kimi,
  plugin Claude) só pegam `nucleo/` depois do refresh (`scripts/260824_refresh-plugin-kimi.cmd`,
  `dist/` no Cowork). O hook do Kimi aceita os dois caminhos desde já.

## 260822 — pastas numeradas só onde o humano entra (claude)
- Decisão (pedido: "numere todas as pastas, se não quebrar"): numerar as 11
  pastas que o <USUARIO> abre; deixar sem número as 12 que só o código abre.
  Numerar tudo quebraria `bin/`, `referencias/`, `skills/` (MAPEAMENTO → cópias
  dos 16 projetos, robocopy dos .cmd, manifesto dos plugins exige `skills/`,
  `hooks/`, `commands/`), o export e o espelho do GitHub. A regra vira
  convenção legível: **número = lugar de gente; sem número = lugar de script.**
- Alternativa descartada: numerar tudo e reescrever os scripts. Motivo: 200+
  referências, duas cópias instaladas no home que só mudam com refresh, e
  ganho nulo — ninguém abre `bin/` pra "achar" algo.
- Alternativa descartada: numerar também `cerebro/` dentro dos projetos.
  Motivo: projeto tem a própria raiz; a numeração é da central.
- Mecanismo: `mb_utils.PASTAS_NUMERADAS` + `pasta()`; nada hardcoda o
  prefixo fora da tabela e dos .cmd (que são texto fixo por natureza).


## 260822 — push por ambiente (v6.5 / skill v5.5) (claude)
- Decisão: o item 5 do Gate 6 deixa de pedir confirmação de push a cada
  sessão. Autorização de commit/push no repo do megabrain é permanente.
  Mecânica por ambiente: sessão cloud com o repo como fonte → clone no
  container, commit, push; sem fonte → commit em `_github/repo-local/` e
  push pelo `01_acoes/260824_enviar-pro-github.cmd`. Git **nunca** pela pasta
  montada do bridge (sem rede, deixa `index.lock`/`HEAD.lock` órfãos).
- Alternativa descartada: continuar pedindo "posso dar push?". Motivo: a
  resposta é sempre sim e a pergunta custa um turno inteiro.
- Alternativa descartada: tentar push pelo bridge com credencial em env.
  Motivo: o VM do bridge não tem rede; 403 garantido e lixo de lock.
- Plugin Claude sobe pra v1.3.0 (skill v5.5 embutida). Regra: skill mudou →
  plugin.json sobe minor → rebuild em `dist/`. O `.plugin` v1.2.0 ficou
  com skill v5.4 e não deve mais ser instalado.

## 260822 — Um relatório por instância; o vivo é o relatório
DECISÃO: `mb-relatorio-vivo.py` absorve a agregação de `.md` e grava
`RELATORIO.html`. Vale para central e projeto. `mb-relatorio-projeto.py` mantém
o conversor de markdown (importado por importlib) e delega quando rodado direto.
ALTERNATIVAS DESCARTADAS: (a) só renomear o vivo para RELATORIO.html — barato,
mas perderia a agregação dos .md que o antigo fazia; (b) dar `--projeto` ao vivo
sem fundir — continuaria com dois arquivos por projeto, sem resolver o
"um relatório só"; (c) copiar as 400 linhas do conversor pra dentro do vivo —
criaria fork silencioso na primeira correção de bug.
POR QUÊ: duas páginas descrevendo a mesma instância é a falha nº 12 do próprio
protocolo (duas cópias tratadas como duas fontes).

## 260822 — Biblioteca visual em HTML+CSS puro, com renderizador
DECISÃO: `modelos/visuais/` (tokens.css + mecanicas/*.html + exemplos.json) e
`bin/mb_visual.py`. Peça visual vira dado: o agente escolhe um id e preenche.
ALTERNATIVAS DESCARTADAS: (a) Mermaid — barato de gerar, mas sem controle de
layout e dependente de renderer; (b) Mermaid pra fluxo + HTML pro resto — mais
superfície pra manter e dois dialetos visuais; (c) continuar escrevendo CSS por
peça — o custo que motivou o pedido.
POR QUÊ: o objetivo declarado pelo <USUARIO> é "gastar menos token criando e sim
adaptando, até virar apenas aplicação".

## 260822 — Figma como fonte de layout, HTML como fonte de dado
DECISÃO: arquivo `megabrain` no Figma (team <AUTOR>) tem a planta fixa do
relatório, a prancheta de mecânicas e os 16 tokens de cor em 2 modos. Figma manda
em posição/ordem/hierarquia; o gerador Python manda no dado.
ALTERNATIVA DESCARTADA: gerar o Figma a partir do HTML a cada mudança — inverteria
o sentido que ele pediu (planejar no Figma, aplicar no HTML) e transformaria o
arquivo em derivado descartável.
POR QUÊ: ele desenha melhor arrastando; e layout revisado por humano é a parte que
o agente erra mais barato deixando de decidir sozinho.

## 260822 — Relatório vencido em 90_arquivo/, não em .mb-backup/
DECISÃO: snapshots vão pra `90_arquivo/relatorios-antigos/` com `INDICE.md`.
ALTERNATIVA DESCARTADA: manter em `.mb-backup/relatorio-vivo/` — pasta oculta com
nome de backup, que ninguém abre.
POR QUÊ: relatório antigo é histórico consultável; a pasta 90_ é justamente a
numerada de humano.

## 260822 — Três temas × dois modos, com eixos independentes
DECISÃO: tema (identidade: cor, tipo, raio, densidade) e modo (direção da
luminosidade) são eixos separados no root — `data-tema` e `data-modo`. Custa
3+2 blocos de CSS, não 6, e escala para N temas.
ALTERNATIVA DESCARTADA: um atributo só (padrão Bootstrap `data-bs-theme`), com
seis combinações escritas à mão — dobra o CSS a cada tema novo e faz o modo
virar parte do nome do tema.
POR QUÊ: é o modelo do Primer e do Spectrum, e é o que a Linear descreve ao
gerar tema inteiro a partir de 3 variáveis.

## 260822 — Tema 02: duas cores e nada mais
DECISÃO: wildfire green = o que está vivo; vinho = o que trava e é seu.
"Espera" NÃO ganha uma terceira cor — é o mesmo verde com croma no chão, mais
borda tracejada. Corpo neutro de verdade (croma 0,006).
ALTERNATIVA DESCARTADA: adicionar âmbar para "espera", que é o reflexo de todo
dashboard. Rejeitada porque três cores de estado + um acento faz nada chamar
atenção — é a disciplina de racionamento do Modal.
POR QUÊ: "espera" é o estado mais frequente hoje (16 projetos atrás); se ele
tivesse cor própria e saturada, dominaria a página inteira.

## 260822 — Acervo visual separado da implementação
DECISÃO: `04_visuais/` é do humano (imagem, curadoria, sim/não, por eixo);
`modelos/visuais/` é do código (tokens, mecânicas, temas). Nenhum script lê
`04_visuais/` — ele pode mover e apagar à vontade.
ALTERNATIVA DESCARTADA: guardar referência dentro de `modelos/visuais/` junto
dos tokens. Rejeitada porque acoplaria curadoria a código: renomear uma
referência quebraria build.
POR QUÊ: ele pediu para arrastar entre pastas. Estado (entrada→sim/não) tem que
ser o primeiro nível; assunto (eixo) o segundo.

## 260822 — Specimen no lugar de screenshot
DECISÃO: referência visual entra no acervo como cartão que isola o MECANISMO,
gerado por `bin/mb-specimen.py`, com URL da fonte e campos roubar/não-roubar.
ALTERNATIVA DESCARTADA: print da landing page. Além de impossível daqui (o
container não alcança a web aberta), é 80% hero, envelhece com o site e não dá
para comparar lado a lado.
POR QUÊ: o acervo existe para decidir, não para admirar.

## 260824 — Um modo só por enquanto: máximo
DECISÃO: o megabrain roda no modo mais inteligente em tudo (lê tudo que bate,
modelo de ponta, conferência dupla em alto risco) até segunda ordem do
<USUARIO>. Modos viram preset depois, sob a escada leve/padrão/máximo.
ALTERNATIVA DESCARTADA: implementar já os modos (econômico/rápido/inteligente)
com MODO: no META. Rejeitada porque ele declarou não ter dor de custo — quer a
melhor resposta sempre; refinar modos agora seria feature sem usuário.
POR QUÊ: "quero sempre o melhor do megabrain, vamos otimizar esse modo
primeiro" (<USUARIO>, 260824).

## 260824 — Escada futura de modos: leve · padrão · máximo
DECISÃO: quando os modos forem ligados, são 3: leve (funde econômico+rápido;
gates 1·4·5, piso de leitura), padrão (roteiro completo, conferência simples,
injeção top-3), máximo (tudo). Escolha na implantação do projeto (novo-projeto
pergunta; default máximo), mudável via MODO: no META ou palavra no chat; modo
atual visível no relatório.
ALTERNATIVA DESCARTADA: manter os 4 rótulos originais. Rejeitada porque
econômico e rápido só diferiam em "modelo local gera resposta", que morreu na
decisão abaixo — sobravam dois nomes pro mesmo degrau e um buraco até o topo.
POR QUÊ: o próprio <USUARIO> apontou o gap; 3 degraus com distância real > 4 com
dois iguais.

## 260824 — Geração local sai de cena; local é só encanamento e busca
DECISÃO: nenhum modelo local (Qwen etc.) gera resposta em nenhum fluxo do
megabrain. Local = scripts determinísticos + embedding (nomic/Ollama) só pra
ranquear lições/wiki.
ALTERNATIVA DESCARTADA: manter Qwen local como fallback barato de geração.
Rejeitada pela preocupação de qualidade dele (power user, quer a resposta mais
lapidada) e porque fallback silencioso de qualidade é o pior tipo de surpresa.
POR QUÊ: pior caso aceitável com Ollama fora = busca pior; nunca resposta pior.

## 260824 — Gerente Neuron perde as faixas cheap/standard/deep
DECISÃO: a triagem por custo sai da interface; tudo vai ao modelo de ponta
enquanto o modo for máximo. O roteador fica no código, desligado, pra era das
faixas. Papel reafirmado: braço local (rodar scripts, segurar os botões do
painel, manter o índice de "onde está cada coisa").
ALTERNATIVA DESCARTADA: manter as 3 faixas com default deep. Rejeitada porque
escolha visível que nunca deve ser usada é atrito e risco de resposta fraca
por engano.
POR QUÊ: pedido explícito dele em 260824 ("tire essa escolha de modos").

## 260824 — Relatório dashboard-first; 4 HTMLs viram 1 painel + 2 anexos
DECISÃO: primeira dobra do RELATORIO.html = PARA VOCÊ + modo atual + versão/
push + botões das ações (.cmd, com "o que faz" em 1 linha) + skills à vista +
infos do projeto; histórico no fim, retrátil. RELATORIO-AGENTES.html é
absorvido como card; PAINEL-MEGABRAIN e CATALOGO-VISUAL ficam como anexos
linkados. Botões: por limitação de navegador, copiam comando e apontam arquivo;
execução real de script fica pra integração com o Gerente Neuron.
ALTERNATIVA DESCARTADA: fundir os 4 HTMLs num arquivo único. Rejeitada porque
PAINEL (2 MB) e CATALOGO deixariam o vivo lento de abrir.
POR QUÊ: ele quer 1 porta de entrada com UX de leigo e potência de power user.

## 260824 — Reorg de pastas: humano na frente, máquina atrás (aprovação pendente)
DECISÃO (proposta registrada, não executada): planta 00_painel / 01_acoes /
02_entrada / 03_docs / 04_visuais / 90 / 99 + motor\ + memoria\ + _github\.
Critério: pasta numerada = mão humana, nome que leigo clica. Execução só em
sessão dedicada (mapear → mover → reapontar → testar), nunca no impulso.
ALTERNATIVA DESCARTADA: renomear já, nesta sessão. Rejeitada porque cada pasta
renomeada quebra caminho em bin/, hooks e .cmd — sem bateria de teste é quebra
silenciosa.
POR QUÊ: pedido dele de UX de pastas pra leigo; risco controlado por migração
mapeada.

## 260824 — Obsidian entra como janela do cérebro, não como motor
DECISÃO: recomendar Obsidian apontado pro cérebro (vault sobre os .md
existentes; .obsidian no .gitignore). Estrutura continua raw/wiki/pessoas +
INDICE; alimentação continua /ingerir + índices.
ALTERNATIVA DESCARTADA: adotar a estrutura padrão Obsidian (daily notes,
templates, wikilink como citação oficial). Rejeitada porque criaria formato
paralelo que os scripts não leem e citação não testável por caminho.
POR QUÊ: o cérebro já é um vault compatível; ganho de navegação humana a custo
zero, sem acoplar o motor a um app.

## 260824b — Termo oficial: "megabrain do projeto"
DECISÃO: a pasta MEGABRAIN\ dentro de cada projeto passa a se chamar
"megabrain do projeto" em toda comunicação e documento. "Cópia de projeto"
sai de uso; se aparecer ambíguo em outro contexto, perguntar ao usuário —
salvo quando for óbvio que não é o megabrain. "megabrian" = typo de megabrain.
ALTERNATIVA DESCARTADA: manter "cópia de projeto". Rejeitada porque "cópia"
sugere backup/duplicata e confunde a função real (roteiro embarcado do
projeto).
POR QUÊ: pedido do <USUARIO>, 260824.

## 260824b — Máximo sem desperdício: modelo por tarefa
DECISÃO: dentro do modo máximo, tarefa mecânica/varredura roda no modelo
equivalente mais barato que dá conta (Sonnet, Kimi, local COMPROVADO);
julgamento, auditoria e entrega final ficam no modelo de ponta. Local ruim
gerando resposta segue proibido.
ALTERNATIVA DESCARTADA: "máximo = tudo no topo, sempre". Rejeitada por ele:
"quero ser inteligente mas nao gastão".
POR QUÊ: mesma qualidade final, custo menor; é a divisão de trabalho que a
skill já prescreve.

## 260824b — Neuron é pet observador; escolha de modelo sai dele
DECISÃO: o Gerente Neuron (apelido oficial: Neuron) não escolhe modelo — isso
fica com o processamento normal da sessão. Papel dele: visão geral do PC e
dos projetos, telemetria, botões do painel, índice de caminhos. Ideia "pet"
(presença/personalidade/avisos) anotada pra evolução futura.
ALTERNATIVA DESCARTADA: Neuron como roteador de modelos (decisão da manhã,
"um modo só, sempre o topo"). Substituída no mesmo dia pela redefinição de
papel — o roteador fica desligado e guardado no código.
POR QUÊ: ele quer o Neuron como "pet de PC que sabe tudo", não como decisor.

## 260824b — DNA do usuário: backup imaculado local das infos pessoais
DECISÃO: criada `dna/usuario/YYMMDD/` — cópia datada e intocável de
memoria/identidade + memoria/cerebro/pessoas. Nunca editar, nunca subir (no .gitignore).
Novo backup = pasta nova. Vocabulário fechado: "imaculado" = DNA; dna\ raiz =
protocolo+índices; foto no git = imaculado do código; dna\usuario\ =
imaculado do usuário. Primeiro backup: 260824.
ALTERNATIVA DESCARTADA: confiar só no git como backup do pessoal. Rejeitada
porque o pessoal NÃO vai pro git por design — precisava de cópia local.
POR QUÊ: "se um crashar tem esse backup" (<USUARIO>, 260824).

## 260824b — Feedback e contribuição: opt-in explícito + envio sempre genérico
DECISÃO: consentimento é necessário (lei de dados + confiança). Telemetria e
lições ficam locais por padrão; envio só se o usuário ativar, e só depois de
limpeza que remove nomes, caminhos e dados pessoais. Relatório ganha feedback
rail fixo à direita (like 1 clique + texto + envio de lição) com aviso cujo
texto mantém o "~~mete o pau~~ critica construtivamente" riscado. Valores de
telemetria nunca são generalizados (ex.: "RTX 4070" fica literal).
ALTERNATIVA DESCARTADA: envio automático anônimo sem pergunta. Rejeitada:
mesmo genérico, coleta sem aviso quebra a confiança que o megabrain vende.
POR QUÊ: ele quer dados pra evoluir o megabrain sem nunca tocar no pessoal
dos usuários.

## 260824b — Autorizações de execução (fase 2)
DECISÃO: autorizados por ele em 260824: (1) tirar peso — próxima sessão, item
único, com teste + rebuild do plugin; (2) painel workspace (abas, multi-painel
salvável, controles de tamanho/fonte, infográficos, feedback rail, aba do
esquema, componente pergunta-.ask); (3) Neuron-pet + telemetria/pesos de
skills; (4) reorg de pastas — APROVADA com condição "não quebrar nada" =
sessão dedicada mapear→mover→reapontar→testar; (5) Obsidian — ele instala,
vault em memoria/cerebro; (6) Figma — aplicar as 4 correções do board 24; (7)
cérebro temporário×permanente + skill de manutenção que avisa; (8) modos
seguem PAUSADOS no máximo + pesquisa de referências pra ele estudar.
ALTERNATIVA DESCARTADA: implementar tudo na mesma sessão da conversa.
Rejeitada: cada item mexe em peça instalada (skill, gerador, app) e merece
sessão com teste — meia-implementação em 8 frentes é como se quebra tudo.
POR QUÊ: regra dele "tudo que não falei pra segurar, dê" + Gate 2 (contexto
como orçamento).

## 260824c — Execução da fase 2 em lote (v7.0)
DECISÃO: com o "pode aplicar do 1 ao 10, sem 5, 6 e 8" do <USUARIO>, executados
na mesma sessão: reorg etapa 1 (layout humano/máquina, com backup e 25/25),
skill v6.0 enxuta + plugin 1.6.1, ciclo de vida do cérebro (VALIDADE +
mb-manutencao-cerebro.py), Neuron sem triagem + telemetria (neuron.jsonl) e
painel workspace (6 abas, workspace salvável, controles com clamp, rail de
feedback com consentimento). Itens adiados com motivo: etapa 2 da reorg
(motor\ — ~170 refs ambíguas, sessão dedicada), Figma board 24 (sessão de
Figma) e script "contribuir" (sem usuários externos ainda).
ALTERNATIVA DESCARTADA: (a) adiar tudo pra sessões separadas — rejeitada
porque ele pediu aplicação imediata e as peças eram independentes e testáveis;
(b) incluir motor\ no embalo — rejeitada pela condição dele "se não quebrar
nada": tokens ambíguos (skills/modelos/dna em prosa) pedem grep por arquivo.
POR QUÊ: cada item saiu com verificação própria (compile, suíte, checagem
estrutural do HTML gerado); o que não dava pra verificar hoje não entrou.

## 260824c — Renomeação dos .cmd por verbo, com data
DECISÃO: 01_acoes/ com nomes de ação: 260824_publicar-e-fotografar.cmd (era
publicar-github), 260824_enviar-pro-github.cmd (era push-github),
260824_sincronizar-projetos.cmd (era sincronizar-pipeline), demais com
prefixo 260824. Referências internas e docs atualizados em massa.
ALTERNATIVA DESCARTADA: manter os nomes técnicos antigos. Rejeitada pela
régua de UX dele: "nome que conecta no cérebro de um leigo".
POR QUÊ: o clique é a interface do humano com o sistema; verbo diz o que
acontece.

## 260824d — Blindagem do enviar-pro-github: log em vez de dump na tela
DECISÃO: no 260824_enviar-pro-github.cmd reescrito, a saída do python vai pro
.mb-log/push.log com checagem de errorlevel (relatorio OK / relatorio FALHOU
codigo N) e guard where python; o `type %LOG% | findstr | more` foi removido.
ALTERNATIVA DESCARTADA: manter o dump do log na tela — despejava o histórico
inteiro (linhas de commit gigantes) a cada rodada e paginava com more.
POR QUÊ: o dump não acrescentava nada e escondia o abort; falha de qualquer
etapa agora fica visível na janela E gravada no log.

## 260824e — Skills do Kimi divergentes: rodar o refresh oficial, não copiar na mão
DECISÃO: com o preflight acusando 2/2 cópias divergentes, a correção foi rodar
o próprio 01_acoes/260824_refresh-plugin-kimi.cmd (backup automático em
.mb-backup/plugin-kimi-20260824-1638, verificação de hash do hook).
ALTERNATIVA DESCARTADA: robocopy manual direto nos destinos, ou só reportar.
POR QUÊ: o remédio desenhado já existia com backup e verificação; preflight
voltou a ✓ na mesma hora e o caminho fica reproduzível.

## 260824f — Etapa 2 da reorg: a máquina mora em motor\, bin fica na raiz
DECISÃO: `skills, referencias, modelos, dna, tests, dist, plugin-megabrain,
plugin-megabrain-claude, gerenteneuron` foram pra `motor/`. A raiz passa a
mostrar só o que é do humano (00_painel, 01_acoes, 02_entrada, 03_docs,
04_visuais, memoria, 90_arquivo, 99_to_delete) + `bin/`. Caminho resolve por
nome lógico (`u.pasta`/`u.achar`, tabela em mb_utils), nunca na mão. O export
público espelha o layout novo; a cópia de projeto (MEGABRAIN\) continua PLANA
e o resolvedor cobre os dois. Migração por `bin/mb-migrar-motor.py` (dry-run
por padrão, manifesto em 90_arquivo/migracao-motor-260824, `--desfazer`).
ALTERNATIVA DESCARTADA: (a) levar `bin/` junto — o hook dos agentes aponta pra
ele por caminho absoluto em ~/.claude/settings.json, e mover exigiria mexer em
config fora da central; (b) reapontar as ~2.300 citações uma a uma — era a
receita pra quebrar em silêncio, e a condição dele era "não quebrar nada".
POR QUÊ: régua do <USUARIO> — raiz é a mão humana; o resto é casa de máquinas.
Suíte foi de 25 pra 48 testes (novos: layout nos dois formatos, sync de central
v7.1, telemetria) e passou verde antes e depois do move.

## 260824g — Telemetria local: formato genérico, 1 linha por sessão, nada sobe
DECISÃO: `bin/mb_telemetria.py` grava JSONL em `.mb-log/telemetria-YYMMDD.jsonl`
e agrega junto o que já existia (neuron.jsonl, eventos-*.jsonl). Campos são
livres (o formato recebe qualquer chave) e VALOR nunca é generalizado. O hook
`mb-contexto.py` registra 1 linha por SESSÃO (não por prompt). O painel ganhou
o slot D6 e o Neuron responde "o que eu mais uso / quanto custou" a partir do
agregado, sem chamar modelo nenhum.
ALTERNATIVA DESCARTADA: registrar por prompt — enche o log de ruído e não
responde nenhuma pergunta melhor do que 1 linha por sessão.
POR QUÊ: spec §4/§6. Dado local primeiro; envio só com opt-in e agregado.

## 260824h — Painel: aba Cérebro e a caixa "você perguntou" em toda aba
DECISÃO: 7ª aba (Cérebro) mostrando wiki/pessoas/raw, validade das páginas,
fila de 02_entrada e o ponteiro do Obsidian; e o componente `.ask` (rótulo em
linha própria + separador, lição do rótulo-que-lê-como-título) no topo de cada
aba, dizendo qual pergunta aquela aba responde.
ALTERNATIVA DESCARTADA: cérebro como slot dentro do Painel — ficava enterrado
no dashboard e o conteúdo é de outra natureza (conhecimento, não execução).
POR QUÊ: spec §1 pedia a aba Cérebro e o componente pergunta; ele validou o
padrão .ask por elogio explícito ("isso me ajudou mt").

## 260824i — Obsidian: vault em memoria/cerebro, config gerada e local
DECISÃO: `bin/mb-obsidian.py` prepara `.obsidian/` dentro de memoria/cerebro
(tema escuro, links relativos, anexo em raw/) sem sobrescrever config que já
exista, escreve um leia-me e abre o vault por `obsidian://open`. Botão:
`01_acoes/260824_abrir-cerebro-obsidian.cmd`. `.obsidian/` nunca sobe.
ALTERNATIVA DESCARTADA: apontar o vault pra `memoria/` inteira — estado,
núcleo e pendências são operação do protocolo, viram ruído no grafo.
POR QUÊ: decisão de 260824 (ele instala o app, o megabrain aponta o vault).

## 260824j — Figma: as 4 correções do board 24 aplicadas no Planejamento-visual
DECISÃO: (1) as duas caixas de "backup" viraram foto no git — "megabrain DNA"
= momento congelado, "megabrain do usuário" = a única central que se edita;
(2) a Skills duplicada saiu e a que ficou diz que é fonte única; (3) o cérebro
ganhou caixa (raw → wiki → pessoas) no lugar da Skills repetida; (4) o Usuário
deixou de ser guarda-chuva dos projetos e virou o carimbo que visita todos.
Bônus: a caixa "XXXXX" virou Telemetria. Legenda das correções acima do mapa.
ALTERNATIVA DESCARTADA: apagar caixas e redesenhar o mapa — mexeria nos
conectores e no traço dele; reescrever texto dentro das caixas existentes
manteve o desenho intacto.
POR QUÊ: fila aprovada 260824, item 6.

## 260824k — Credencial e backup pessoal saem do pacote público por nome exato
DECISÃO: `.env` entra em EXCLUIR_NOME_EXATO (match exato, preserva o
.env.example) e `dna/usuario` entra em EXCLUIR do mb-generate-template.py. As
cópias que já estavam em _github/export e _github/repo-local foram apagadas.
ALTERNATIVA DESCARTADA: confiar no .gitignore — ele barrou o commit, mas o
arquivo com 4 chaves de API já estava dentro do clone. Uma camada só não basta.
POR QUÊ: achado da varredura da etapa 2. Histórico do git conferido: `.env`
nunca foi rastreado nem commitado — só o .env.example.

## 260824l — Obsidian: registrar o vault na config, e o cérebro ganha grafo
DECISÃO: `bin/mb-obsidian.py` ganhou `--registrar` (escreve o vault em
%APPDATA%/obsidian/obsidian.json, com backup e recusando rodar com o app
aberto), `--conferir` (todo [[wikilink]] aponta pra arquivo que existe?) e
`--abrir` passou a registrar antes de chamar a URI. No cérebro nasceu
`260824_mapa-do-cerebro.md` — página-hub com wikilink pra tudo — e as páginas
existentes ganharam wikilink de fonte e vizinha. A skill `/ingerir` passa a
exigir wikilink além do caminho e a manter o mapa. Plugin vai a 1.6.3.
ALTERNATIVA DESCARTADA: (a) pedir pra ele clicar em "Open folder as vault" —
a URI dava "Vault not found" e o onboarding já tinha registrado a pasta
Downloads por engano; (b) trocar a convenção de caminho-entre-crase por
wikilink — os dois convivem: crase pra humano e pra IA ler, colchete pro grafo.
POR QUÊ: vault que abre vazio e grafo sem aresta entregam a sensação de app
quebrado. O grafo é o motivo de ter Obsidian aqui.
