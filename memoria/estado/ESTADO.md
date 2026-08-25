# ESTADO — megabrain core

MODO: otimizado

TL;DR: v7.1 no disco — a máquina inteira mudou pra motor\ e a raiz ficou só
com o que é seu; telemetria local ligada; painel com aba Cérebro; Obsidian
INSTALADO por ele, vault registrado, aberto e com grafo de verdade (mapa +
wikilinks); Figma do board 24 corrigido. Suíte 48/48. Plugin 1.6.3 reinstalado
no Claude (260824, confirmado por ele); vault Downloads removido do Obsidian.
Lado Kimi verificado na mesma sessão: plugin em sync com a fonte, hook íntegro,
suíte 48/48.

ONDE ESTAMOS: fila 2→6 executada em uma sessão (o 7 ficou pausado por decisão
sua e o 8 virou nota na pasta do Portfolio). Painel: 7ª aba Cérebro + caixa
"você perguntou" em toda aba. Telemetria: bin/mb_telemetria.py + slot D6 +
Neuron respondendo sobre uso sem chamar modelo. Etapa 2: 9 pastas em motor\,
caminho por nome lógico (u.pasta/u.achar), migração com manifesto e --desfazer,
25→48 testes. Obsidian: vault preparado em memoria/cerebro + botão em
01_acoes. Figma: as 4 correções do board 24 + a caixa XXXXX virou Telemetria.

BLOQUEIO: nenhum.

ACHADOS DE SEGURANÇA (corrigidos): o .env do gerenteneuron, com 4 chaves de
API reais, estava sendo copiado pro _github/export e pro clone do repo — o
.gitignore barrou o commit (git log confirma: nunca foi rastreado), mas o
arquivo chegou no clone. Excluído do gerador por nome exato e as duas cópias
apagadas. Na mesma varredura, dna/usuario/ (backup imaculado) também saía no
pacote público — bloqueado.

SEGURADO: Tema 02 Wildfire · Figma v1 (arquivo megabrain) · 04_visuais/00_entrada
· motor/dna/usuario/ (imaculado) · 90_arquivo/migracao-v7-260824 e
90_arquivo/migracao-motor-260824 (backups das duas etapas).

AÇÃO ANTERIOR (260824, 4ª sessão): itens 2 a 6 da fila aprovada, cada um com
teste próprio; suíte verde antes e depois do move; export e painel
regenerados. Depois que ele instalou o Obsidian: vault do cérebro registrado
na config do app (a URI sozinha dava "Vault not found"), mapa-do-cerebro
criado com wikilinks, /ingerir passou a exigir wikilink, verificador de link
quebrado (mb-obsidian.py --conferir) e plugin 1.6.3.

ÚLTIMA AÇÃO (260824, 5ª sessão): §7 da spec — compreensor de padrões. Nasceu
`bin/mb-compreensor.py` (v1, um detector só: templatizar), com saída em
`00_painel/260824_padroes.md` + `.mb-log/padroes.json`, bloco no slot de
telemetria do painel e botão `01_acoes/260824_compreender-padroes.cmd`. O
primeiro rascunho devolveu slop ("claude", "nota", "file", "markdown") e a
régua foi apertada três vezes até só sobrar verdade — hoje ele aponta as 2
pendências `templatizar-*` paradas há 6 dias e diz honestamente que nada mais
passou. Junto veio o conserto do relógio: a telemetria gravava em UTC quando o
script rodava pela ponte, e 3 linhas tinham caído em `telemetria-260825.jsonl`
criado às 22h38 de 260824; `mb_telemetria` agora força America/Sao_Paulo na
escrita e converte na leitura, e `--corrigir-fuso --aplicar` consertou o que
já estava gravado (backup em `.mb-log/_backup-fuso-260824-2328`). Suíte 48 →
70. Plugin 1.6.4 SEGUE pendente de instalação por ele — nada nesta sessão
mexeu em skill, então o pacote continua válido.
