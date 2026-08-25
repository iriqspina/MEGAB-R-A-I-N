# ESTADO — megabrain core

MODO: otimizado

TL;DR: v7.5 no disco. As 7 pendências da auditoria foram decididas por ele em
260825 ("toca tudo com as suas recomendações") e executadas — a central virou
repositório git, 6 artefatos de saída viraram 3, as 11 ações estão numeradas
com o número no nome do arquivo, e o painel abre skills e comandos por clique.
Suíte 118/118 (o resolvedor de dois layouts foi cortado em 260825ae: um formato
só na central, plano só em restauração). Preflight PODE COMEÇAR. BLOQUEIO: nenhum.

ONDE ESTAMOS: fases 1 (diagnóstico) e 2 (consolidação) fechadas. Falta a fase
3 — varrer os 18 megabrains de projeto contra a central. As lições já batem
(183 nas cópias conferidas), mas ninguém auditou versão, skills e estrutura
projeto a projeto.

## O que o painel entrega agora

Abrir `01_acoes\01_ABRIR-RELATORIO.cmd` (ou o próprio `RELATORIO.html`):
- **O que você clica** — as 11 ações, numeradas 1 a 11, cada uma expansível
  com "o que faz" e "quando usar". O número vem de `bin/mb_registro.py`, não
  da ordem da pasta, e está no NOME do arquivo — então "roda o 5" vale na
  pasta e no painel, hoje e daqui a três meses.
- **Comandos de manutenção** — 7, sem número de propósito.
- **Suas skills** — 13, agrupadas por origem (protocolo, plugin, projeto,
  Matt Pocock), com gatilho. As ~31 de plugin de terceiro ficam de fora.
- O estado do que você expandiu sobrevive ao reload de 15 s.

## Consertado em 260825 (tudo verificado)

Encanamento: memória partida (8 → 186 lições indexadas) · relatório triplicado
e depois quebrado (948.500 → ~580.000 B, e ele não gerava por `AttributeError`)
· quatro versões diferentes nos arquivos de abertura · contrato de resposta
apontando pra caminho morto nos 6 destinos · `mb-relatorio-agentes` lendo `dna/`
plano (12 candidatas onde aparecia zero) · sanitização deixando o sobrenome no
pacote público · CRLF de 13 `.cmd` (o sync imprimia 18 OK e copiava zero byte
desde 24/08) · `PULAR_DIRS` do preflight com a mesma entrada composta.

Estrutura: git init com `.gitignore` próprio (versiona dado pessoal — é o que
precisa ser recuperável) e `.gitattributes` byte-exato · 11 ações numeradas ·
4 scripts de uso único e 3 artefatos sem leitor pra `90_arquivo` · Gate 2 com
sinal medível · `/conclusao-megabrain` vira ponteiro · 3 skills do Pocock
instaladas · META nova.

Decisões 260825a–p em `DECISOES.md`. 13 lições novas no núcleo.

## Fila (nada bloqueado, tudo dele)

1. **Push.** O `repo-local` tem 1 commit sem push (`ee84eca`, rodado pelo
   auditor com autorização dele) e a central ganhou mais 4 commits depois do
   bump — o `10_publicar-e-fotografar` precisa rodar de novo pra convergir, e
   o `11_enviar-pro-github` é o que sobe. Nenhum dos dois roda sozinho.
2. **Fase 3** — os 18 megabrains de projeto contra a central.
3. **Trava por escopo.** Ficou pra depois do git de propósito: com histórico,
   perda virou recuperável e a trava certa é mais leve do que era. Hoje
   `TRAVADO_POR` é honra — só `mb-sync.py` lê.
4. ~~**`mb-specimen.py`** escreve em `/tmp/spec/out` no import~~ — APOSENTADO
   pra `90_arquivo/scripts-uso-unico-260825/` (260825). Uso único de 260822,
   sem chamador vivo.
5. **Fila de tasks do djinnai.io** implementada: `dados/fila.json`,
   `bin/mb-fila.py`, `motor/tests/test_mb_fila.py`, integração em
   `dados/estado.json:fila`. Veredito da mecânica 2 em
   `memoria/estado/DECISOES.md` §260825x.
6. **AI reviewer contra acceptance criteria** implementado:
   `modelos/SPEC.md`, `bin/mb-review-criteria.py`,
   `motor/tests/test_mb_review_criteria.py`. Veredito da mecânica 3 em
   `memoria/estado/DECISOES.md` §260825y.
7. **Resíduo histórico no git público**: `pyvenv.cfg` e 3 caminhos pessoais em
   commits antigos do clone. Sem chave; revela usuário e caminho local.

SEGURADO: nada foi apagado em 260825. `90_arquivo/artefatos-aposentados-260825`,
`90_arquivo/scripts-uso-unico-260825`, `90_arquivo/estado-vencido-260825`,
`99_to_delete/260825_licoes-megabrain-ORFA-raiz.md`,
`.mb-backup/260825_licoes-nucleo-antes-merge.md`,
`.mb-backup/260825_cmd-crlf-1016`. Fora isso: Tema 02 Wildfire · Figma v1 ·
04_visuais/00_entrada · motor/dna/usuario/.

ÚLTIMA AÇÃO (260825, 4 agentes no mesmo epic): auditoria multi-IA, grelha de
14 perguntas respondida por ele em duas rodadas, e a execução completa de
Q8–Q16. Suíte 48 → 70 → 79. Central em git com 4 commits.
