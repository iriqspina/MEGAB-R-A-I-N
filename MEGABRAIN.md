# MEGABRAIN v3 · pipeline local completa (com camada pessoal)

**TL;DR:** este arquivo é o canônico local — substitui `PIPELINE.md` como
documento-mestre. Junta a camada macro (fases de projeto, artefatos, regras
de ouro, níveis de adoção — herdadas do `PIPELINE.md` v2) com a camada micro
multi-agente (gates de entrega, Claude+Kimi, roteamento) que agora vive em
`skills/megabrain/SKILL.md`. A versão que sobe pro GitHub é
`260810_github-export/` — igual na estrutura, sem nada pessoal.

Versão: ver `VERSAO.txt`. Lições vivas: `licoes-megabrain.md`.
Referências de execução: `referencias/260810_*.md`.

---

## 1 · Relação entre os três arquivos

| Arquivo | Escopo | Editar aqui? |
|---|---|---|
| `skills/megabrain/SKILL.md` | Router do `/megabrain` — gates de entrega, multi-agente (Claude+Kimi), roteamento de arquitetura | Sim — é o que dispara |
| `skills/gerenteneuron/SKILL.md` | Roteador unificado de chat multi-IA local (`/gerenteneuron`) — escolhe modelo por custo/capacidade | Sim |
| `260810_MEGABRAIN.md` (este) | Camada de projeto: fases macro, artefatos, regras de ouro, níveis de adoção, biblioteca visual pessoal | Sim |
| `260810_memoria-pessoal.md` | Perfil de identidade (nome, TDAH, formato de resposta obrigatório) — fonte da sincronização entre agentes, nunca sai desta pasta | Sim |
| `PIPELINE.md` | v2, congelado — mantido por histórico, não recebe mudança nova | Não |

`PIPELINE.md` continua no disco (não apago nem renomeio arquivo já escrito)
com um aviso de descontinuação no topo apontando pra cá.

---

## 1b · Migração v4.0: diferenciação de usuário

Desde a v4.0 o megabrain carrega um campo `USUARIO:` em dois lugares:

1. No `HANDOFF.md` de cada projeto — a trava de handoff agora registra para
   qual pessoa o agente está trabalhando.
2. Nos arquivos de identidade sincronizados — `CLAUDE.md`, `GEMINI.md` e
   `AGENTS.md` passam a declarar o perfil logo no início.

### Por que isso importa

Antes da v4.0 o protocolo assumia implicitamente um único operador. Se outra
pessoa usar o pacote (fork, clone ou máquina compartilhada), o `HANDOFF.md`
não dizia para quem a trava estava ativa e os agentes não sabiam qual perfil
carregar. A v4.0 torna isso explícito sem quebrar projetos antigos.

### O que acontece quando um projeto derivado sincroniza automaticamente

Quando `mb-check-version.py` copia a central para dentro do `MEGABRAIN/` do
projeto, os scripts novos passam a:

- Detectar `USUARIO:` do arquivo de identidade do projeto
  (`260810_memoria-pessoal.md` na raiz do projeto ou da central).
- Gravar `USUARIO:` no `HANDOFF.md` toda vez que alguém rodar
  `mb-sync.py lock`.
- Injetar `USUARIO:` nos arquivos de identidade quando alguém rodar
  `mb-sync-memoria.py`.

Projetos antigos continuam funcionando: se não houver arquivo de identidade,
o campo aparece como `<USUARIO>` e o script indica que é preciso configurar.

### Como configurar no seu projeto derivado (ou depois de um fork/clone)

1. Crie um arquivo de identidade na raiz do seu projeto ou da central com o
   nome `260810_memoria-pessoal.md`.
2. No início dele, coloque:
   ```
   USUARIO: Seu Nome
   ```
3. Rode a sincronização de identidade:
   ```
   python MEGABRAIN/bin/mb-sync-memoria.py --source 260810_memoria-pessoal.md --target all --dir .
   ```
4. A partir daí, toda trava de handoff vai registrar o nome automaticamente:
   ```
   python MEGABRAIN/bin/mb-sync.py lock --agente Kimi --escopo pasta/arquivo
   ```

### Como trocar de perfil ou adicionar outro usuário

- Para forçar um nome só na trava atual: use `--usuario` no `mb-sync.py` ou
  `mb-sync-memoria.py`.
- Para mudar o padrão do projeto: edite `USUARIO:` no
  `260810_memoria-pessoal.md` e rode `mb-sync-memoria.py` de novo.
- Para múltiplos perfis no mesmo computador: mantenha arquivos de identidade
  separados (ex.: `260810_memoria-pessoal-fulano.md`) e passe `--source` e
  `--usuario` explicitamente.

### Uso offline e recuperação

A pasta `MEGABRAIN/` dentro de cada projeto é uma cópia local completa do
protocolo. Se o GitHub ou a internet caírem, os scripts continuam
funcionando direto de lá. Para sincronizar sem consultar a rede:

```
python MEGABRAIN/bin/mb-check-version.py --projeto "caminho/do/projeto" --offline
```

Para não depender só do GitHub, faça backup da central:

```
cd <pasta-central>
python bin/mb-backup-central.py
```

Se a pasta `MEGABRAIN/` de um projeto sumir, recupere de um backup zip,
de outro projeto ou da central:

```
python MEGABRAIN/bin/mb-recuperar-megabrain.py --projeto "caminho/do/projeto" --fonte "backup.zip"
```

Mais detalhes: `MEGABRAIN/OFFLINE.md`.

---

## 2 · Fases do projeto (macro — herdado do PIPELINE.md v2)

```
estado → grelhar → spec → tickets → implementar → validar → publicar → registrar
```

1. **ESTADO** — medir antes de dizer. Toda sessão começa lendo o estado real
   (git, build, testes, o que está no ar) e devolve um retrato de 5 linhas,
   TL;DR primeiro. Sinal que não se mediu vira `?`, nunca chute.
2. **GRELHAR** — entender antes de especificar. Interrogatório até fechar
   cada ramo. O que se aprende vira termo no `CONTEXT.md` ou decisão
   registrada — nunca fica só na conversa.
3. **SPEC** — uma por feature, viva, em `.scratch/<feature>/spec.md`, com
   critérios de aceite verificáveis. Sonda de 2 minutos antes: suposição de
   viabilidade vira linha SIM/NÃO medida antes de entrar na spec.
4. **TICKETS** — decomposição com dependência (`Blocked by`, prioridade,
   critério de aceite próprio).
5. **IMPLEMENTAR** — um ticket por vez, TDD por fatia. Revisão em dois eixos
   (padrão do repo + fidelidade à spec) antes do commit. Nunca código sem
   spec.
6. **VALIDAR** — o número sai do harness, nunca de documento. Teste que
   afirmava o bug e não afirma mais: reaponta se mudou de lugar, apaga se o
   defeito sumiu — nunca remenda pra defender o erro.
7. **PUBLICAR** — portões impossíveis de pular, pausa antes do irreversível.
   Build → verificar artefato → auditoria → harness → **pausa** → deploy →
   smoke → linha no CHANGELOG. O agente prepara e testa, nunca executa
   deploy ou migração: entrega `.cmd` pronto que roda os portões e pausa.
8. **REGISTRAR** — sessão sem rastro não aconteceu. Diário ganha entrada;
   lição nova entra no arquivo de lições (GATILHO/LIÇÃO/ATALHO) sem pedir
   permissão. Lição 3× vira regra deste arquivo ou de uma skill.

## 3 · Artefatos (o que existe em todo projeto adulto)

| Artefato | Papel |
|---|---|
| `CONTEXT.md` | glossário do domínio |
| regras do repo (`CLAUDE.md` ou equivalente) | regras fixas do projeto |
| `.scratch/<feature>/` | tracker vivo: spec, plano, grelha, issues |
| `docs/` | planos e handoffs, `YYMMDD` quando datado |
| `Atalhos\*.cmd` + `LEIAME` | dia a dia num clique, numerados |
| relatório de projeto (`RELATORIO.html`) | instância aplicada — contexto, estado/handoff, situação e pendências concentrados num HTML só; gerado por `bin/mb-relatorio-projeto.py` (ver seção 5b) — edita-se o gerador/fonte, nunca o HTML |
| `CHANGELOG.md` | o que subiu, mais novo primeiro |
| `_arquivo\_tmp\` | sondas e scripts de uma vez só |
| `MEGABRAIN\` | esta pipeline sincronizada (inclui `dna\` — relatório DNA do protocolo) — não editar a cópia |

## 4 · Regras de ouro (valem em todo projeto)

1. Nunca escrever código sem plano ou spec. Sem exceção.
2. Um comando de terminal por vez — prompt interativo engole a linha colada.
3. `YYMMDD` só fora do repo (exports, entregas). Dentro, nome estável.
4. Gerado nunca se edita — edita-se a fonte/o gerador.
5. Arquivo gigante se lê por trecho (Grep/offset), nunca inteiro sem necessidade.
6. Deploy, migração, irreversível: sempre `.cmd` pronto com pausa — nunca lista
   de comandos no chat.
7. Ao pedir ação, sempre o caminho completo da pasta/arquivo.
8. Local-first — dado pessoal não sobe pra serviço externo.
9. Medir > supor. `?` em vez de chute; hash e byte em vez de "deve estar igual".
10. Tela muda não se distingue de travada — tarefa longa nunca redireciona a
    saída inteira pra arquivo; dois relatores (tela + log) ou Tee.
11. Achado é endereço, não posição — nunca renumerar; derrubado fica riscado
    com o porquê; novo pega o próximo número livre.
12. Commit alheio pendente não sequestra arquivo novo — checar `git status`
    antes de versionar; havendo pendência, `git add <lista explícita>`.
13. Buscar comportamento por verbos e sinônimos, não pelo termo do enunciado.
14. Teste vermelho pós-conserto: reapontar ou apagar — nunca remendar seletor
    que defende erro.
15. Feedback de ação nasce no campo visual de quem clicou.
16. Navegador não executa `.cmd` por link — copiar caminho + Win+R, ou clique
    direto na pasta.
17. Formato de resposta padrão: TL;DR no topo; primeira frase de cada parte
    resume a parte; tópicos numerados.
18. Portar entre agentes/runtimes: hooks não atravessam, skills atravessam
    sem edição. Sempre-ativo e estático vai pro system prompt, não pro hook.
19. Memória/arquivo legado: normalizar pra UTF-8 puro antes de editar por
    programa.
20. Quadro que se monitora vira widget pinado + tarefa agendada.
21. **Garantia real é script, não markdown.** O que precisa acontecer sempre
    e sem falha vive em `.cmd`/script/hook, nunca só numa skill.
22. Formato pedido explicitamente vence o protocolo. Ordem: formato pedido >
    protocolo > default.

## 5 · Camada micro (gates de entrega + multi-agente)

Vive em `skills/megabrain/SKILL.md` — router completo: gates
assumir/enquadrar/orçar/gerar/auditar/reparar/verificar/bastão/aprender,
divisão Claude↔Kimi, roteamento de arquitetura (skill vs subagente vs hook
vs script), Duplo Diamante pra projeto de design. Não duplicado aqui —
edite lá.

## 5b · Relatório de projeto — template de consolidação

Desde 260814. Todo projeto pode gerar um **relatório de projeto**: o irmão
do relatório DNA (`MEGABRAIN\dna\`). O DNA descreve o **protocolo**
(genérico, estável); o relatório de projeto descreve a **instância** — um
único HTML, direcionado a usuário E IA, que concentra o que antes exigia
abrir vários `.md` soltos:

- **contexto específico** (`CONTEXT.md` do projeto) + **contexto geral**
  (resumo do `MEGABRAIN.md` central, quando acessível);
- **estado e handoff** — lê `ESTADO.md`/`HANDOFF.md`/`DECISOES.md` do
  projeto **como referência, sem mover os arquivos**; projeto nível 1-2 sem
  esses três arquivos usa o próprio arquivo vivo (`--plano`) como fonte de
  estado + decisões, e o relatório diz isso explicitamente em vez de fingir
  seção vazia;
- **situação viva** — o arquivo indicado em `--plano` (ex.: `PLANO.md`,
  `ESTADO.md`), renderizado por inteiro;
- **arquivos extra de domínio** — `--extra` (repetível): cada um vira sua
  própria seção;
- **ação imediata** (desde 260814) — card em destaque logo abaixo do TL;DR,
  visualmente separado (fundo escuro, checklist numerado grande) — extrai UM
  heading do `--plano` (palavra-chave "ação imediata"/"o que fazer agora"/
  "faça isto"...) e mostra como sequência óbvia "faça isto, depois isto".
  Diferente de "resolução" (que pode ter várias alternativas concorrentes)
  — aqui é o caminho único recomendado. `--sem-acao-imediata` desliga;
  `--acao-imediata-titulo PALAVRA` adiciona palavra-chave própria;
- **ações rápidas** (desde 260814) — `--acao "Rótulo|URL"` (repetível)
  coloca botões no card de ação para abrir uma URL HTTPS ou pular para uma
  âncora do próprio relatório. O gerador recusa `javascript:`, `file:` e
  outros esquemas; botão serve para ação que o usuário realmente precisa
  executar, não para abrir scripts locais;
- **resolução — alternativas pra resolver a situação** (desde 260814; nome
  antigo era "caminhos", trocado porque ficava ambíguo com caminho de
  arquivo) — varre `--plano` + `--extra` por headings `##`/`###` cujo texto
  bate com palavras-chave (`plano de ação`, `estratégia`, `alternativas`,
  `resolução`, `o que fazer`...) e destaca esses trechos numa seção própria,
  em cima da "situação viva" — sem duplicar o arquivo fonte, só recorta o
  que já existe. `--sem-resolucao` desliga; `--resolucao-titulo PALAVRA`
  (repetível) adiciona palavra-chave própria do domínio;
- **próximas ações** — lidas do `SKILL.md` router do projeto, se passado em
  `--skill`;
- **dados pendentes** — toda linha `- [ ]` / `- [x]` de qualquer arquivo
  lido entra automaticamente numa lista única "Dados pendentes", com a
  fonte de cada item — não precisa marcar pendência duas vezes;
- **fontes** (antes "caminhos") — tabela com o caminho absoluto de cada
  arquivo lido, com botão de copiar; é só a lista de arquivo/pasta, não
  confundir com a seção "resolução" acima.

Gerador: `bin/mb-relatorio-projeto.py --projeto PATH --titulo NOME --plano
ARQUIVO [--extra ARQUIVO]... [--skill ARQUIVO] [--tldr "frase"]
[--megabrain-central PATH] [--sem-resolucao] [--resolucao-titulo PALAVRA]...
[--sem-acao-imediata] [--acao-imediata-titulo PALAVRA] [--acao "Rótulo|URL"]...`. `--saida`
default é `RELATORIO.html` na raiz do projeto. Referência de uso completo
(todos os argumentos preenchidos):
`Financeiro da Silva/05_scripts/gerar_relatorio.py`.

Conversor markdown→HTML (`markdown_para_html`) junta linhas indentadas de
continuação dentro de um item de lista (`- texto` ou `N. texto` que quebra em
mais de uma linha por largura) — sem isso, cada linha de continuação virava
parágrafo solto fora da lista. Também nunca casa o `#` (H1, título do
documento) ao procurar heading de "resolução"/"ação imediata" — só `##`/`###`/
`####` — pra não confundir o título do arquivo com uma seção de conteúdo (já
aconteceu: um H1 com a frase "ação imediata" no meio do texto virou match
falso e engoliu o arquivo inteiro pra dentro do card).

Regra de ouro 4 vale igual aqui: **gerado nunca se edita**. O HTML de saída
não se toca na mão — edita-se o(s) `.md` fonte e roda-se o gerador de novo.

Não confundir com o relatório DNA nem tentar fundir os dois num arquivo só:
o DNA precisa ficar estável e genérico (é o que se copia pra replicar o
protocolo em outro lugar); o relatório de projeto carrega o que é
específico daquele projeto e poluiria o template se misturado.

## 6 · Biblioteca visual pessoal (âncoras concretas)

Metodologia genérica — como montar e usar qualquer biblioteca de referência —
está em `referencias/260810_galerias-referencia.md` (essa parte foi pro
GitHub, é método, não gosto pessoal). Aqui fica só a lista concreta:

- **Motion/web:** osmo.supply (execução: componentes, easings) ·
  tympanus.net/codrops (técnica com código aberto) · land-book.com (volume) ·
  siteinspire.com (curadoria seca) · lapa.ninja (seções isoladas) ·
  onepagelove.com (one-pagers) · awwwards.com (teto de ambição — enviesa pra
  espetáculo) · recent.design (mais multidisciplinar, gráfico + digital) ·
  refero.design (screenshots de UI real — a melhor pra Operate/Read) ·
  navbar.gallery · footer.design
- **UI/game UI:** gameuidatabase.com (HUD, menu, inventário) ·
  interfaceingame.com (por jogo e elemento) · artstation.com (material e
  atmosfera, não layout)

## 7 · Níveis de adoção por projeto

| Nível | O que o projeto tem | Quando |
|---|---|---|
| **1 · referência** | `MEGABRAIN\` + `CONTEXT.md` | projeto novo ou exploração |
| **2 · tracker** | + `.scratch/` com specs/tickets + regras do repo | entrou em desenvolvimento |
| **3 · ciclo completo** | + harness com carimbo + `Atalhos\` + relatório vivo + deploy com portões | produto no ar |

Todo projeto nasce no nível 1 (`novo-projeto.cmd`). Subir de nível é decisão
explícita, com spec — nunca por acidente.

## 8 · Roteamento de projetos pessoais → skill dedicada

(Seção removida no template público: os projetos pessoais do usuário são substituídos por exemplos genéricos.)

## 9 · Como esta pipeline evolui

1. Lição nova → arquivo de lições (GATILHO/LIÇÃO/ATALHO, data `YYMMDD`).
2. Lição reutilizável → versão sanitizada na fonte central; se o usuário
   declarou promoção obrigatória, isso acontece no mesmo ciclo.
3. Lição 3× → entra neste arquivo, na `SKILL.md`, num template ou script.
4. Editou a fonte → bump em `VERSAO.txt` (data + uma linha do que mudou).
5. Espalhar → `sincronizar-pipeline.cmd`.
6. A cópia dentro de cada projeto não se edita — a fonte manda.

## 10 · Versão multi-IA (opcional)

Para projetos que usam mais de um agente, o guia de escolha de modelo está em
`referencias/260813_multi-ia.md`. Ele é opcional: lido junto com este arquivo
quando o projeto é multi-agente, ou ignorado quando o projeto usa um só
agente. Se a leitura conjunta falhar ou pesar o contexto, use a referência
separada como fallback.

Origem: fusão entre pipeline de projeto v2 e protocolo multi-agente v3.
