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

## 260824m — compreensor de padrões: um detector só, e a régua é o produto
DECISÃO: `bin/mb-compreensor.py` v1 entrega UM compreensor — templatizar. Ele
cruza pendências × cérebro × docs × estado × visuais × entrada × telemetria e
só reporta tema que apareça em ≥2 tipos de lugar, com ao menos um deles sendo
coisa que ele faz e guarda, e que não tenha modelo, skill, script em `bin/` ou
botão em `01_acoes/` cobrindo. Saída em `00_painel/AAMMDD_padroes.md` +
`.mb-log/padroes.json`, com bloco no slot de telemetria do painel.
ALTERNATIVA DESCARTADA: (a) os quatro compreensores de uma vez (parado, órfão,
ritmo) — ele escolheu escopo estreito; (b) painel estatístico de telemetria —
com 101 eventos em 6 dias, gráfico ali é enfeite; (c) afrouxar a régua até a
seção 2 encher: o primeiro rascunho devolvia "claude", "nota", "file" e
"markdown", e o certo foi apertar a régua e aceitar que hoje só os 2
declarados aparecem.
POR QUÊ: §7 da spec destravou quando a telemetria (§4) passou a existir. E o
compreensor é script em `bin/`, não skill — não aumenta a distância do plugin
1.6.4, que ele ainda não instalou.

## 260824n — data do evento é o relógio da central, não o de quem roda
DECISÃO: `mb_telemetria` ganhou `agora()`/`hoje()` fixados em
America/Sao_Paulo (zoneinfo, `-03:00` de reserva). A escrita usa isso pro `ts`
e pro nome do arquivo do dia; a leitura converte ts com fuso antes de contar.
`--corrigir-fuso [--aplicar]` conserta retroativamente com backup, guardando o
valor antigo em `ts_original` e sem tocar em log de hook.
ALTERNATIVA DESCARTADA: (a) `datetime.now()` local — é o bug: devolve o
relógio de quem roda, e a VM da ponte é UTC; (b) só registrar a lição e seguir
— o compreensor agrupa por dia e nasceria com 5 eventos deslocados em 3 horas.
POR QUÊ: entre 21h e meia-noite em SP, a ponte enxerga o dia seguinte.
`telemetria-260825.jsonl` nasceu às 22h38 de 260824. Mesma raiz da lição de
carimbo de arquivo do mesmo dia, agora fechada no código em vez de na regra.


## 260825a — a memória tinha dois arquivos e o índice lia o menor
DECISÃO: `memoria/nucleo/licoes-megabrain.md` é o canônico, ponto. As 8 lições
que só existiam no órfão da raiz foram fundidas nele (166 → 174), a órfã foi
pra `99_to_delete/260825_licoes-megabrain-ORFA-raiz.md` com backup em
`.mb-backup/260825_licoes-nucleo-antes-merge.md`, e `achar()` passou a separar
duas regras que estavam misturadas: nome CANÔNICO de `PASTAS_RAIZ` resolve
sempre na pasta lógica (tem um lugar só); caminho de MÁQUINA continua com
"arquivo real na cópia plana ganha" (muda de lugar por layout). Teste de
regressão em `test_mb_layout.py::test_orfao_na_raiz_nao_sombreia_canonico`.
ALTERNATIVA DESCARTADA: (a) manter a raiz como fonte e o núcleo virar link —
a raiz não é o que sobe pro pacote público nem o que `mb-check-version.py`
distribui pros 16 projetos; (b) fazer `achar()` gritar quando achar os dois,
como o auditor sugeriu — grito em função chamada por 28 módulos vira ruído em
todo script; o teste pega o caso na suíte, que é onde dói barato; (c) apagar
a órfã direto — 8 lições sem cópia, incluindo a de 260825.
POR QUÊ: o hook injetava "5 de 126+" escolhendo entre 8. 95% da memória estava
invisível pra todo agente, e o rótulo mentia duas vezes — no denominador e na
fonte. O índice agora tem 173 entradas medidas.

## 260825b — filtro que casa por pedaço de caminho não aceita entrada composta
DECISÃO: `IGNORAR_CENTRAL` em `bin/mb-relatorio-vivo.py` troca
`"_github/repo-local"` e `"_github/export"` por `"_github"`, e ganha um
`assert` que recusa qualquer entrada com barra na hora do import.
ALTERNATIVA DESCARTADA: mudar o casamento pra comparar caminho relativo
inteiro em vez de pedaço — cada entrada da lista precisaria virar prefixo
exato e as 20 entradas simples quebrariam junto.
POR QUÊ: as duas entradas compostas nunca casavam, então o rglob varria
`_github/` inteiro e cada documento aparecia 3× no HTML. `RELATORIO.html` caiu
de 948.500 pra 570.599 bytes (-40%) com uma linha. O comentário logo acima da
lista já previa o defeito — o que faltava era a garantia executável.

## 260825c — versão tem uma fonte, e é VERSAO.txt
DECISÃO: nenhum título, cabeçalho ou JSON repete número de versão. O h1 do
relatório passa a compor o nome do projeto (de `PROGRESSO.json`, com o sufixo
de versão removido por regex) + `versao_resumida(VERSAO.txt)`. `MEGABRAIN.md`
e `README.md` perderam o número e ganharam a regra no lugar.
ALTERNATIVA DESCARTADA: (a) atualizar os quatro números na mão — é o que já
tinha sido feito antes e eles divergiram de novo em 3 dias; (b) um script que
sincroniza número em todo lugar — quatro cópias sincronizadas continuam sendo
quatro cópias.
POR QUÊ: `MEGABRAIN.md` dizia v3, `README.md` v6.5, o h1 do relatório v6.7 e o
subtítulo v7.1, com o disco em v7.4. É a primeira linha que toda IA nova lê, e
a primeira coisa que o <USUARIO> olha pra saber onde está.

## 260825d — o Gate 5 vira botão em vez de disciplina
DECISÃO: `01_acoes/00_ABRIR-RELATORIO.cmd` regenera o relatório e abre no
navegador. Nome com `00_` pra ordenar primeiro na pasta. Se o python falhar,
abre a última versão gerada em vez de não abrir nada.
ALTERNATIVA DESCARTADA: (a) só um atalho pro HTML — abriria conteúdo vencido,
que é exatamente o defeito; (b) hook que regenera a cada escrita de `.md` —
regeneração custa segundos e ele escreve `.md` o tempo todo.
POR QUÊ: `01_acoes/` tem 10 botões e nenhum abria o artefato que existe pra ser
lido. E em 24/08 os três `.md` foram tocados 2 minutos depois da última
geração: o "relatório vivo" recarregava a cada 15s um conteúdo vencido desde o
minuto seguinte ao nascimento. Regra de ouro 21 aplicada — garantia é script.

## 260825e — skill instalada é a que o harness lista, não a que está na central
DECISÃO: as 5 skills (`megabrain`, `ingerir`, `grelhar`, `traycer`,
`conclusao-megabrain`) foram instaladas em `~/.claude/skills/` e copiadas pro
plugin do Kimi; `260824_refresh-plugin-kimi.cmd` ganhou a variável
`SKILLS_EXTRA` pra levar skill nova daqui em diante, sempre de
`motor/skills/<nome>` — nunca da cópia dentro do plugin.
ALTERNATIVA DESCARTADA: instalar o `.plugin` v1.7.0 no Claude — o mecanismo de
marketplace não é acionável de fora e `~/.claude/plugins/data/megabrain-inline`
está vazio desde 21/08. A lição 260805 já dizia: o hook não sobrevive à
portabilidade, a skill sim.
POR QUÊ: `enabledPlugins` tinha só figma; o Claude rodava o protocolo há dias
sem nenhuma skill do megabrain carregada, e o `ESTADO.md` afirmava o contrário.
O Kimi tinha 4 de 7. Verificado nesta sessão: o harness listou as 5.

## 260825f — caminho de dados fixo mata relatório em silêncio
DECISÃO: `mb-relatorio-agentes.py` lê `licoes-recorrencia.json` por
`u.pasta(c, "dna")` em vez de `c / "dna"`. E `eventos_hoje()` normaliza o campo
de resumo pra texto antes do `html.escape()`.
ALTERNATIVA DESCARTADA: try/except em volta da geração — engoliria o próximo
defeito do mesmo jeito.
POR QUÊ: dois defeitos com a mesma forma. O primeiro (achado do GPT) fazia o
relatório concluir "nenhuma candidata a regra" com os dados presentes em
`motor/dna/`. O segundo derrubava a geração inteira com `AttributeError`
quando um evento trazia `arquivo` como lista — o relatório de hoje não gerava.
Campo de log é dado de fora: o tipo não é promessa.

## 260825g — o contrato de resposta apontava pra um caminho morto nos 5 agentes
DECISÃO: `memoria/identidade/260810_memoria-pessoal.md` corrigido pra
`motor\referencias\260818_padrao-resposta.md` e propagado pelos 6 destinos
(`~/.claude/CLAUDE.md`, `~/.gemini/GEMINI.md`, `~/.kimi/AGENTS.md`,
`~/.kimi-code/AGENTS.md`, `~/.codex/AGENTS.md`, output style).
ALTERNATIVA DESCARTADA: corrigir os 6 destinos na mão — a fonte continuaria
errada e o próximo sync propagaria o erro de volta, que é o defeito real.
POR QUÊ: o caminho morreu na migração v7.1 (24/08) e ninguém consertou a
fonte. Todo agente lia "contrato completo em <caminho inexistente>". O
`.claude/CLAUDE.md` do projeto estava certo — o que escondeu o problema.


## 260825h — sanitizar por substring deixa o resto do nome composto no pacote
DECISÃO: `bin/mb-generate-template.py` ganha o token COMPOSTO inteiro na lista
de substituição (o domínio pessoal, 13 caracteres, que a ordenação por tamanho
faz ganhar do primeiro nome, de 8), e um detector novo em `PADROES_PRIVADOS`
que recusa o pacote quando encontra placeholder colado em letra — a forma do
defeito, não o nome específico. Sobrenome SOLTO fica fora da lista de
propósito, com o motivo escrito no código.
ALTERNATIVA DESCARTADA: (a) acrescentar o sobrenome solto à lista, que foi a
recomendação do Kimi — testado e reprovado na hora: ele casa dentro de
`iriqspina`, o username público do GitHub, e a URL do repositório no pacote
virou `<USUARIO><USUARIO>`; (b) corrigir os 5 arquivos do export na mão — o
export é derivado, regenerar desfaz; (c) tirar `ALINHAMENTO-AGENTES.md` do
pacote, que resolveria estes 5 casos e nenhum futuro (segue na fila como
decisão dele, junto com o arquivamento dos vencidos).
POR QUÊ: a substituição é de substring, então o primeiro nome dentro do
domínio pessoal era trocado e o sobrenome sobrava colado ao placeholder, no
pacote público, em 4 arquivos. O detector é o que impede a terceira vez: o
gerador já tinha sido mordido em 260821 pela sanitização da própria cópia — e
mordeu de novo nesta sessão, barrando o comentário que eu escrevi com o
exemplo literal dentro. Ficou registrado no código pra não repetir.

## 260825i — crédito da skill /traycer: interoperabilidade, não derivação
DECISÃO: `motor/skills/traycer/SKILL.md` ganha bloco de crédito declarando
Traycer como produto proprietário de terceiro (`traycer.ai`), que a skill NÃO
deriva de código ou texto deles — é documentação de interoperabilidade escrita
a partir do comportamento observado — e que nenhuma licença é reivindicada
sobre o produto. Plugin regenerado e a skill re-sincronizada nos dois agentes.
ALTERNATIVA DESCARTADA: declarar uma licença para a integração, como o
inventário do Kimi sugeriu — seria reivindicar relação de licenciamento que
não existe. Crédito honesto é dizer o que a coisa é, não carimbar licença.
POR QUÊ: as outras origens têm crédito e licença no ponto de uso (ECC MIT em
`mb-slop-visual.py:10`, Pocock MIT em `grelhar/SKILL.md:9`); Traycer era a
única viva sem nada. E a resposta certa aqui não é a mesma das outras, porque
a relação é outra.


## 260825j — a central vira repositório git, e este versiona dado pessoal
DECISÃO: `git init` na central, sem remote e sem push. `.gitignore` PRÓPRIO,
diferente do público: ficam de fora credenciais (`gerenteneuron/.env`,
`.venv`, `vault`), `_github/` (é git aninhado — viraria gitlink quebrado),
`.mb-backup/` (28 MB regeneráveis), `.mb-log/` (o hook escreve a cada prompt)
e os índices com embedding. Dado pessoal ENTRA: `licoes-megabrain.md` e
`260810_memoria-pessoal.md` são exatamente o que precisa ser recuperável.
`.gitattributes` com `* -text`: backup byte-exato.
ALTERNATIVA DESCARTADA: (a) herdar o `.gitignore` do pacote público — ele
exclui `licoes-megabrain.md`, ou seja, o repo não versionaria justamente o
arquivo que motivou criá-lo; (b) continuar com zip periódico — o último
completo era de 22/08, três dias e quatro sessões atrás.
POR QUÊ: 5 agentes escrevendo no mesmo disco e nenhuma detecção de conflito.
O auditor pegou um agente-irmão escrevendo em `META.md` às 09:50 com a trava
marcando `livre`. Sem git, decisão sobrescrita some sem diff.

## 260825k — /conclusao-megabrain vira ponteiro pro Gate 6
DECISÃO: a skill perde o corpo e passa a mandar executar o Gate 6 da skill
`megabrain`. O comando continua existindo; some a segunda fonte de verdade.
ALTERNATIVA DESCARTADA: matar de vez — quebra um hábito dele sem ganho, já
que o custo era a divergência, não a existência do comando.
POR QUÊ: duplicava o Gate 6 inteiro e divergia dele — carregava o teto de
"máx. 2 perguntas por rodada" que a decisão 260824 revogou. E estava instalada
nos dois agentes, contradizendo o protocolo em produção.

## 260825l — o número das ações é declarado, não é a ordem da pasta
DECISÃO: `bin/mb_registro.py` guarda `ACOES` (11), `ROTINA` (7) e
`SKILLS_DELE` (13). O número vem de lá; `bin/mb-numerar-acoes.py` renomeia o
disco pra bater (`01_` a `11_`) e o relatório monta o painel da mesma fonte.
Botão novo entra no fim com o próximo livre; número aposentado nunca é reusado.
O prefixo entra no NOME DO ARQUIVO, não só no HTML.
ALTERNATIVA DESCARTADA: (a) numerar pela ordem alfabética da pasta — entra um
botão e "o script 3" vira outro na semana seguinte, quebrando toda frase já
dita; (b) número só no relatório — é na PASTA que ele se perde, foi o que ele
descreveu.
POR QUÊ: pedido dele em 260825 — "aí vc fala clica ali no script 3 e fica
fácil de achar, não por nome". Número só cumpre isso se for estável.

## 260825m — filtro por nome de pasta: a terceira ocorrência vira assert
DECISÃO: `PULAR_DIRS` em `bin/mb-preflight.py` troca `"_github/export"` por
`"_github"`, ganha `"90_arquivo"` e um `assert` que recusa barra no import —
igual ao de `IGNORAR_CENTRAL` (260825b).
ALTERNATIVA DESCARTADA: só documentar — é a 3ª vez que a mesma família de bug
aparece (relatório, cópia de central, preflight) e lição não executa nada.
POR QUÊ: a entrada composta nunca casava e dois cheques varriam o export
inteiro à toa. Junto: um `manifest.json` de migração ARQUIVADA fazia o
preflight sair com veredito PENDÊNCIA toda abertura de sessão — gate que
acusa história treina a ignorar o gate.

## 260825n — 6 artefatos de saída viram 3, critério: um leitor por artefato
DECISÃO: `PAINEL-MEGABRAIN.html` (2,7 MB), `CATALOGO-VISUAL.html` e o gerador
`bin/mb-painel.py` vão pra `90_arquivo/artefatos-aposentados-260825/` com
LEIAME. `mb_visual.py --catalogo` para de gerar o gêmeo HTML (fica sob demanda
em `--catalogo-html CAMINHO`). Ficam: `RELATORIO.html` (ele, ao vivo),
`RELATORIO-DNA.html` (terceiro replicando o protocolo) e `CATALOGO.md`
(agente montando peça). Fecha a decisão de 260824 que ficou pela metade.
ALTERNATIVA DESCARTADA: (a) manter o PAINEL como anexo linkado, que era a
decisão de 260824 — 260 dias depois não havia um único `href` apontando pra
ele; ninguém constrói o link porque ninguém abre; (b) fundir tudo num arquivo
— foi rejeitado em 260824 por peso, e continua certo.
POR QUÊ: o contrato dizia "direcionado a usuário E IA" (MEGABRAIN.md §5b) e
essa frase É a origem do inchaço. Nada que sirva os dois ao mesmo tempo
sobrevive sem virar despejo.

## 260825o — Gate 2 deixa de ser sensação e passa a ter número
DECISÃO: `bin/mb-contexto.py` registra `contexto_injetado` (chars + peças +
sessão) na telemetria a cada prompt. O Gate 2 troca ">85% de contexto" por
dois sinais que o agente REALMENTE sabe: 80 mil chars injetados ou 40 arquivos
lidos na sessão → HANDOFF + commit + recomeçar.
ALTERNATIVA DESCARTADA: (a) descer o Gate 2 pra nota do Gate 6 — era a saída
honesta se não houvesse medidor, mas o hook já calculava `len(bloco)` e só não
guardava; (b) manter o percentual — nenhum agente conhece a própria janela.
POR QUÊ: regra de ouro 21 — garantia real é script, não markdown. Um gate que
só pode ser cumprido por sensação não é gate.

## 260825p — o painel mostra as skills DELE, não as 44 instaladas
DECISÃO: `SKILLS_DELE` em `bin/mb_registro.py` declara 13 — as 5 do protocolo,
`registrar-licao`, as 4 de projeto e as 3 do Matt Pocock — com o que faz e o
gatilho, cada uma expansível no painel. As ~31 de plugin de terceiro
(cloudflare, figma, adobe, wordpress, canva) não entram.
ALTERNATIVA DESCARTADA: (a) listar as 44 — é o problema que ele descreveu
("fico olhando vários e perdido"), agora com 31 itens que ele não escreveu nem
mantém; (b) varrer `~/.claude/skills/` e filtrar por heurística — não existe
sinal confiável de autoria no diretório, e lista declarada ele controla.
POR QUÊ: pedido dele — "todas as skills e explicadas caso vc clicar,
expandindo". "Todas" que importa é o conjunto dele.


## 260825q — fase 3: as 19 cópias de projeto auditadas e limpas
DECISÃO: `bin/mb-auditar-copias.py` nasce como o verificador das cópias —
versão × central, arquivo que a central já aposentou, `.cmd` com nome velho,
contagem de lições. Rodado com `--limpar`: **300 arquivos movidos** (não
apagados) pra `<projeto>/90_arquivo/aposentados-260825/`, cada pasta com
LEIAME explicando o motivo de cada arquivo. As 19 cópias foram sincronizadas
pra v7.5. A lição própria do TLOU (`260816 — resetBlocks apaga o que o usuário
editou`) foi fundida na central antes de sobrescrever a cópia.
ALTERNATIVA DESCARTADA: (a) deixar as cópias como estão porque "são
descartáveis" — 6 delas serviam `PAINEL-MEGABRAIN.html` e 8 `.cmd` com nome de
260810, ou seja, quem abrisse a pasta MEGABRAIN de um projeto recebia a
experiência de 10 de agosto; (b) apagar direto — regra dele, poda com rede;
(c) sobrescrever o `licoes-megabrain.md` do TLOU sem olhar — teria perdido a
única lição que só existia lá. Mesma armadilha da 260825a, 8 horas depois.
POR QUÊ: a reorganização de pastas melhorou a central e parou na fronteira.
31 MB de peso morto espalhado em 19 lugares, e o sync só ACRESCENTA — nunca
remove — então nada saía sozinho.

## 260825r — a cópia de projeto carrega 68× mais máquina do que conteúdo
DECISÃO (medida registrada, escolha PENDENTE dele): cada cópia tem **7.080 KB
de máquina** (bin, skills, referencias, modelos, dna — tudo idêntico à central)
contra **104 KB de estado próprio** (ESTADO, HANDOFF, DECISOES, META,
PROGRESSO). São **182 MB em 19 cópias** pra guardar ~2 MB de coisa única.
Isso reenquadra a pergunta "plano × aninhado": as duas respondem à pergunta
errada. A pergunta certa é se o projeto precisa carregar a máquina.
ALTERNATIVA DESCARTADA: nenhuma ainda — a decisão é dele e está registrada
com os três caminhos e o custo de cada um em ESTADO.md.
POR QUÊ: o custo do formato plano é real e mensurável — 63 linhas de
resolvedor (`pasta()` + `achar()`), 29 de tabela, 12 dos 79 testes, 100
chamadas em 24 de 34 scripts — e dois dos bugs de 260825 nasceram na costura
entre os dois formatos. Mas trocar plano por aninhado paga a migração e NÃO
elimina o resolvedor. Só a cópia magra elimina.

## 260825s — o que a IA roda nos gates precisa estar declarado em algum lugar
DECISÃO: `mb_registro.py` ganha a lista `AGENTE` — `mb-preflight` (Gate 0),
`mb-mapa-refs` (Gate 3), `mb-slop-visual` (Gate 4) — com o gate, o que faz e
**o que quebra se não rodar**. Aparece no painel numa seção própria, rotulada
"não é pra você clicar". `ROTINA` foi de 7 pra 13.
ALTERNATIVA DESCARTADA: (a) jogar no ROTINA — polui o painel dele com comando
que ele nunca vai digitar; (b) deixar só na SKILL.md, que é onde já estava —
`mb-mapa-refs.py` tem 4 citações em SKILL.md e ZERO execuções em 6 dias de log.
POR QUÊ: levantamento do auditor por evidência de chamador. É a melhor regra
do Gate 3 ("lista de quem quebra é verificação; 'tem certeza?' não é") e
ninguém roda. Ver é a primeira condição de cobrar.


## 260825t — uma fonte de dados, duas renderizações: o relatório vira um só
DECISÃO: nasce `bin/mb-estado.py` → `dados/estado.json` (schema 1), a fonte
única legível por máquina: versão, meta, estado, git, memória, decisões, uso
por agente, padrões, as 19 cópias de projeto e o registro de ações/skills.
Contrato do arquivo: todo número carrega `_fonte`; campo não medido vem `null`,
nunca zero; `--campo versao.atual` lê um valor sem abrir o JSON. O
`RELATORIO.html` passa a RENDERIZAR esse JSON, e com isso absorve
`RELATORIO-AGENTES.html` (seção D11) e `AAMMDD_padroes.md` (D12), mais a
auditoria de cópias (D13) e um bloco "Para a IA" (D14). O Gate 0 da skill
`megabrain` manda ler o JSON ANTES da prosa. **`00_painel/` passa a ter 1
arquivo.**
ALTERNATIVA DESCARTADA: (a) mais uma rodada de "consolidar os HTMLs" — foi o
que 260822 e 260824 fizeram, e os dois voltaram a inchar em dias; (b) o
relatório continuar servindo IA e humano no mesmo arquivo, como a lição 260813
pedia — é justamente a frase que produziu 2,7 MB de painel; (c) markdown
agregado como fonte de máquina — é o que existia, e é o que faz cada IA
escrever seu próprio parser.
POR QUÊ: a causa de "um relatório só" ter sido decidido 3× e nunca fechar não
era disciplina. Cada artefato novo nasceu porque uma IA precisava de um dado e
o único jeito de obter era parsear prosa — então nascia mais um leitor com
leitura própria do mesmo dado. Com o JSON existindo, a resposta pra "preciso
desse dado" deixa de ser "crio um relatório" e passa a ser "acrescento um campo
no coletor". Resolve também "funcionar pra todas as IAs equivalentemente":
Claude, Kimi, GPT, Gemini, Codex e Qwen local leem o MESMO arquivo, sem saber
em que layout a central está.

## 260825u — reestruturar pasta não é o que faz o megabrain funcionar pra IA
DECISÃO: **não** haverá nova reorganização de pastas nesta rodada, apesar da
autorização. Entra uma pasta só — `dados/` — e nada é movido. O ganho pedido
("foco na IA e processamento de dados") vem da CAMADA DE DADOS, não da árvore.
ALTERNATIVA DESCARTADA: mover pastas de novo pra uma árvore "AI-first". Custo
medido da última reorg (v7.1): ~2.300 citações, 63 linhas de resolvedor, 29 de
tabela, 12 dos 79 testes, e **dois dos bugs de 260825 nasceram na costura** que
ela criou. Ganho pra IA: zero — nenhuma IA lê melhor por a pasta se chamar
`03_dados` em vez de `dados`.
POR QUÊ: o que trava uma IA hoje não é onde o arquivo está — `u.achar()` já
resolve isso nos três layouts. É que o dado só existe como prosa. Mover pasta
paga o custo alto da migração pra comprar exatamente nada do que foi pedido.
Se depois da cópia magra (260825r) a árvore ainda incomodar, aí sim — com o
resolvedor já eliminado, a migração fica barata.


## 260825v — o relatório para de carregar conteúdo: 76% dele era despejo pra IA
DECISÃO: `conteudo_md()` em `bin/mb-relatorio-vivo.py` passa a emitir ÍNDICE
(título, caminho clicável, tamanho, quando mudou) em vez do texto dos 31
documentos. O conteúdo continua acessível — pelo arquivo. `dados/estado.json`
ganha o coletor `documentos` (41 itens) com o mesmo índice, e a nota
`como_usar` dizendo em letra que ele NÃO carrega conteúdo. A lição 260813
("relatório serve IA e humano — HTML + metadados + JSON-LD") foi **aposentada**
com rastro: a parte certa dela vive na 260825t; o que morreu foi o "no mesmo
arquivo".
Medido: `RELATORIO.html` **616.988 → 140.646 bytes (-77%)**; o despejo eram
470.972 bytes em 31 seções.
ALTERNATIVA DESCARTADA: (a) manter o despejo retrátil — 471 KB continuam sendo
gerados, lidos e desatualizando a cada `.md` tocado, só que escondidos; (b)
gerar dois HTMLs, um com conteúdo e um sem — é literalmente o problema que a
consolidação de hoje desfez; (c) JSON-LD embutido no HTML, como a 260813
pedia — seria uma TERCEIRA representação do mesmo dado, num arquivo que a IA
não vai abrir porque já tem o JSON.
POR QUÊ: pedido dele em 260825 — "foco na i.a., o humano qualquer coisa a gente
faz depois um layout visual só pro caba ler e clicar". Com a IA lendo o JSON,
o HTML não precisa mais carregar texto nenhum, e o que sobra é exatamente o
painel visual que ele quer redesenhar depois. O leitor humano ganha junto: ele
rolava e caía num poço de 31 seções sem navegação.

## 260825w — a ordem certa era IA primeiro, humano depois
DECISÃO (registro de método, não de código): a reestruturação do megabrain
segue a ordem **dado → IA → humano**. Primeiro a fonte única
(`dados/estado.json`, 260825t), depois o Gate 0 lendo ela, depois o índice no
lugar do despejo (260825v). O layout visual do painel fica pra uma rodada
dedicada, com ele conduzindo.
ALTERNATIVA DESCARTADA: começar pelo visual, que é o que "o relatório está
confuso" sugere à primeira leitura. Teria produzido um painel bonito por cima
de 617 KB de despejo — e o despejo voltaria a crescer, porque a causa (IA sem
dado estruturado) continuaria de pé.
POR QUÊ: ele nomeou a ordem — "foco na i.a., o humano a gente faz depois". E a
medição confirma que era a ordem certa: 76% do problema visual era consequência
da falta de dado estruturado, não de design. Consertada a causa, o painel caiu
para 141 KB e virou uma superfície pequena o bastante pra redesenhar de fato.

## 260825x — fila de tasks com dependências e ondas (djinnai.io mecânica 2)
DECISÃO: implementar a mecânica 2 do djinnai.io como board local.
- Fonte de dados: `dados/fila.json` — epics, tasks, `blocked_by`, prioridade, dono e estado.
- Script CLI: `bin/mb-fila.py` com subcomandos `listar`, `proxima`, `avancar <id>` e `json`.
- Cálculo de ondas: tasks sem dependências = onda 0; cada nível de bloqueio incrementa uma onda; ciclos levantam erro.
- Integração: `bin/mb-estado.py` ganha coletor `col_fila()` e exporta resumo no campo `fila` do `dados/estado.json`.
- Testes: `motor/tests/test_mb_fila.py` com 10 casos cobrindo ondas, ciclos, dependências desconhecidas e avanço de estado.
ALTERNATIVA DESCARTADA: (a) criar board só em markdown/prosa — reproduziria o problema que `dados/estado.json` resolveu (IA parseando texto); (b) despachar tasks para agentes reais automaticamente — exige orquestrador confiável que ainda não existe, e o valor da mecânica está em saber *o que está pronto*, não em executar sozinho.
POR QUÊ: o <USUARIO> escolheu implementar a mecânica 2, e a forma mais barata de trazer o conceito do Djinn é a fonte de dados + renderização — o mesmo padrão que fechou o relatório em 260825t. Não se adota o Helm/Kubernetes do Djinn; a mecânica é roubada, não o código.


## 260825z — o restaurador para de depender de "outro projeto" (passo 1 da cópia magra)
> **Era 260825x.** Renumerada em 260825 11:20: um agente-irmão gravou outra
> decisão com o MESMO id às 11:10 (fila de tasks, djinnai.io mecânica 2) e a
> trava marcava LIVRE — nenhum script lê `TRAVADO_POR` antes de escrever. Duas
> decisões com o mesmo endereço quebram toda citação cruzada. A dele ficou com
> o id porque chegou primeiro no arquivo; esta cedeu. É o A15 da auditoria
> acontecendo em cima da própria auditoria, pela segunda vez no dia.
DECISÃO: `bin/mb-recuperar-megabrain.py` reescrito. Fontes agora, em ordem de
confiança, cada uma com o que PROVA: (1) central viva; (2) **git da central**,
que não existia antes de hoje; (3) `.mb-backup/*.zip`; (4) `_github/repo-local`,
com aviso de que é sanitizado — sem lições nem identidade; (5) o `central` do
`.mb-origem.json` da própria cópia. **"Outro projeto" foi REMOVIDO.** Ganhou
`--listar-fontes` e, principalmente, `conferir()`: confere VERSAO.txt legível,
MEGABRAIN.md presente, e recusa restauração com menos de 5 arquivos. Quando a
central está viva, **delega a montagem pro `mb-check-version.py`** em vez de
copiar. 11 testes novos em `motor/tests/test_mb_recuperar.py` (suíte 88 → 99).
ALTERNATIVA DESCARTADA: (a) manter "outro projeto" como último recurso — é
exatamente a linha que obriga a manter 19 cópias gordas pra alimentar o
restaurador; redundância que só existe pra alimentar o plano de recuperação se
paga sozinha; (b) o restaurador montar a cópia por conta — foi o que a versão
antiga fazia e o teste de hoje pegou: `copytree` da central devolveu **3.371
arquivos** com `_github/`, `90_arquivo/` e `99_to_delete/` dentro. Quem sabe o
que uma cópia de projeto contém é o `mb-check-version.py`. Depois da delegação:
**143 arquivos**, layout plano, conferido.
POR QUÊ: condição dura levantada pelo auditor e aceita — não se remove
redundância antes de o caminho de recuperação funcionar sem ela. É o passo 1 da
ordem acordada: recuperar → piloto no Currículo → medir → os outros 18.

## 260825ag — a promessa de resiliência offline sai do canônico
> **Era 260825y.** Renumerada em 260825 12:15: um agente-irmão gravou o AI
> reviewer (mecânica 3 do djinnai.io) com o MESMO id, e esse já era citado por
> `ESTADO.md` e pela pendência da fila. Quem tem citação viva fica com o id;
> esta decisão não era citada em nenhum arquivo vivo, então cedeu. Segunda
> colisão de id no dia (a primeira foi 260825x) — a trava por escopo
> (260825ad) existe por causa disso.
DECISÃO: `MEGABRAIN.md`, seção "Uso offline e recuperação", perde a frase
"se o GitHub ou a internet caírem, os scripts continuam funcionando direto de
lá" e ganha a correção com rastro. A proteção real contra "a central sumiu"
passa a ser nomeada: git da central + `.mb-backup/*.zip`.
ALTERNATIVA DESCARTADA: apagar a frase em silêncio. O rastro é o que impede
alguém de reintroduzir a promessa daqui a um mês achando que é um recurso.
POR QUÊ: a central está no mesmo disco `S:`, na pasta ao lado — queda de rede
nunca afetou o funcionamento. A frase prometia uma proteção inexistente, e o
custo disso não é o texto: é ter impedido de construir a proteção de verdade
por quatro meses. Promessa falsa é pior que ausência.


## 260825aa — cópia magra: as 19 pastas de projeto viram um ponteiro
DECISÃO: `bin/mb-magra.py` converte a `MEGABRAIN/` de cada projeto para
`.mb-origem.json` + `LEIAME.md`. A máquina vive só na central. Executado nos
19: **3.631 arquivos movidos**, 3 vazamentos de `dna/usuario/` (Linkedolas) em
quarentena na central, **182.000 KB → 531 KB (−99,7%)**. Nada apagado: tudo
consolidado em `.mb-backup/260825_magra-arquivado.zip` (58 MB) e
`260825_fase3-aposentados-projetos.zip` (11 MB).
A classificação NÃO usa lista fixa: arquivo byte-idêntico em **5+ cópias** é
legado compartilhado por evidência — conteúdo de projeto não se repete em 5
projetos por acaso. O que não é reconhecido **fica** (44 preservados, listados
no relatório). `mb-check-version.py` aprendeu o formato: cópia que declara
`formato: magra` recebe só o ponteiro atualizado — sem isso o primeiro `--auto`
engordaria tudo de volta em silêncio.
ALTERNATIVA DESCARTADA: (a) plano ou aninhado, as duas opções que estavam na
mesa — as duas duplicam a máquina, e a medição (7.080 KB de máquina contra
104 KB de estado, que ainda por cima era cópia velha da central) mostrou que
ambas respondiam à pergunta errada; (b) manter o arquivado dentro de cada
projeto — 19 pastas de arquivo morto dentro de 19 projetos é exatamente o
problema que a magra resolve.
POR QUÊ: dois layouts vivos obrigavam `mb_utils` a resolver os dois — 63 linhas
de resolvedor, 100 chamadas em 24 de 34 scripts — e **dois dos bugs de 260825
nasceram nessa costura**. Sem cópia gorda não há costura. E o auditor provou
que nenhum dos 35 scripts precisa rodar de dentro de um projeto: os hooks
apontam pra central por caminho absoluto e nunca executaram da cópia.

## 260825ab — o "alias" que ignorava os próprios argumentos
DECISÃO: `mb-relatorio-projeto.py` rodado direto com `--projeto` ou `--saida`
passa a executar o modo legado (a página agregada daquele projeto) em vez de
delegar. Sem esses argumentos, continua delegando pro relatório da central.
ALTERNATIVA DESCARTADA: fazer os wrappers chamarem `mb-relatorio-vivo.py` — o
vivo grava o relatório da INSTÂNCIA, e os três wrappers querem a página
agregada de um projeto com título, plano e TL;DR próprios. São coisas
diferentes; o legado sabe fazer e continua existindo.
POR QUÊ: desde a v6.6 a delegação chamava o vivo **sem argumento nenhum** —
quem pedia o relatório de um projeto recebia o da central, sem erro. Ficou
assim quatro dias e só apareceu hoje, quando a cópia magra tirou o script de
dentro dos projetos e o wrapper do Financeiro da Silva morreu com
FileNotFoundError num arquivo que nunca foi escrito. É a mesma confusão do
"virou alias" que o canônico afirmava e foi corrigida hoje de manhã.

## 260825ac — os 3 wrappers de projeto resolvem a central pelo ponteiro
DECISÃO: `Portfolio/gerar-relatorio.ps1`, `Curriculo/scripts/gerar-relatorio.py`
e `Financeiro da Silva/05_scripts/gerar_relatorio.py` passam a ler
`MEGABRAIN/.mb-origem.json` pra achar a central, com fallback pra
`MEGABRAIN/` (cópia cheia antiga). Os três foram executados e verificados.
ALTERNATIVA DESCARTADA: chumbar o caminho absoluto da central nos três — é
literalmente a lição 260807 ("pasta-mãe renomeada aposenta caminhos gravados em
TODAS as superfícies"), que já custou 2 `.cmd`, 10 skills e um widget.
POR QUÊ: o ponteiro já existia e já era escrito pelo sync em toda cópia. A
terceira opção estava no disco — não precisava ser inventada.

## 260825y — AI reviewer contra acceptance criteria (djinnai.io mecânica 3)
DECISÃO: implementar reviewer local de acceptance criteria.
- Fonte de critérios: `modelos/SPEC.md` (seção `## Acceptance Criteria`) ou `META.md` (campo `CRITÉRIO DE PRONTO`).
- Script: `bin/mb-review-criteria.py` — lê spec, extrai critérios, lê diff/status do git, aplica heurística local (palavras-chave no diff + arquivos alterados) e gera parecer Markdown ou JSON.
- Template: `modelos/SPEC.md` com seções Problema, Meta e Acceptance Criteria checklist.
- Testes: `motor/tests/test_mb_review_criteria.py` com 9 casos cobrindo extração de SPEC/META e heurística de evidência.
- Código de saída: 0 = aprovado, 1 = reprovado, 2 = sem spec/critérios.
ALTERNATIVA DESCARTADA: (a) chamar modelo de IA externo pra revisar — adiciona latência, custo e dependência de rede; a mecânica do Djinn é um gate, e gate precisa ser rápido e local; (b) escrever critérios só em DECISOES.md — espalha a spec pelo repositório em vez de ter um arquivo de entrada do reviewer.
POR QUÊ: o <USUARIO> escolheu implementar a mecânica 3. O valor do Djinn está em explicitar o critério ANTES de entregar e ter um passo de verificação obrigatório. A versão local é suficiente pra começar: evita handoff com critério esquecido e dá um parecer mensurável sem depender de API externa.

## 260825ae — resolvedor de dois layouts cortado: um formato só na central
DECISÃO: `u.pasta()` e `u.achar()` mantêm a API, mas a central passa a ter um único layout reconhecido: `memoria/` + `motor/`. Sai o fallback `PASTAS_V64` (`00_nucleo`, `01_estado` etc.) e sai a prioridade da árvore mista em que `skills/` plano vencia `motor/skills`. O plano permanece SOMENTE quando a pasta realmente existe — restauração cheia, backup anterior à cópia magra e arquivo de estado na raiz de projeto. Saldo: −36 linhas em `bin/mb_utils.py` e `motor/tests/test_mb_layout.py`; suíte 119 → 118 (o teste removido era o cenário morto "motor/ e skills/ coexistem"). Executado pelo auditor GPT com trava; medição antes do corte: zero consumidor de `PASTAS_V64` nas árvores vivas e nos 6 ZIPs locais.
ALTERNATIVA DESCARTADA: remover TODO fallback plano — quebraria os backups reais (o ZIP magro arquivado tem 3.632 entradas no formato plano) e o `mb-recuperar-megabrain.py`, que restaura e confere esse formato sob demanda.
POR QUÊ: depois da cópia magra (260825aa) só existe um formato vivo; o corte elimina compatibilidade hipotética e o cenário impossível de árvore mista sem amputar o plano de recuperação que tornou a magra reversível.

## 260825af — specs vivas com sign-off obsoleto (djinnai.io mecânica 1)
DECISÃO: implementar sign-off local de specs detectando obsolescência automaticamente.
- Fonte: `modelos/SPEC.md` ganha seção `## Sign-offs` com tabela `Quem | Quando | Commit | Estado`.
- Script: `bin/mb-spec-signoff.py` — `listar` todas as specs, `assinar <caminho> --quem`, `verificar [caminho]`. O sign-off registra o hash curto do HEAD; a obsolescência é detectada por `git log <hash-do-signoff>..HEAD -- <arquivo>`.
- Testes: `motor/tests/test_mb_spec_signoff.py` com 10 casos cobrindo extração, obsolescência, assinatura em spec nova/existente e formatação.
- Integração: `bin/mb-estado.py` expõe `signoffs` com total, ok, obsoletas, sem_signoff e detalhes.
ALTERNATIVA DESCARTADA: (a) usar timestamp de modificação do arquivo em vez de commit — não distingue mudança real de `touch` e quebra em checkout; (b) assinar com tag git anotada — introduz mutation no repo a cada aprovação de spec, e a mecânica precisa ser leve o bastante pra rodar várias vezes por sessão.
POR QUÊ: o <USUARIO> escolheu implementar a mecânica 1. O valor do Djinn está em saber que uma spec aprovada ainda é a spec vigente. Detectar obsolescência pelo git é preciso e não exige estado extra: o próprio histórico já conta quando o arquivo mudou. A integração no estado.json faz o painel alertar specs obsoletas sem precisar rodar nada à mão.
