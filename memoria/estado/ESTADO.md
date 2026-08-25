# ESTADO — megabrain core

MODO: otimizado

TL;DR: v7.4 no disco (a versão é sempre a 1ª linha de `VERSAO.txt` — nenhum
outro arquivo repete o número desde 260825). Auditoria de 3 agentes fechada e
os consertos de encanamento aplicados: a memória voltou inteira (174 lições,
179 indexadas — eram 8), o relatório encolheu 40% e parou de triplicar, as 5
skills estão instaladas e listadas pelo harness no Claude e no Kimi, e o
contrato de resposta parou de apontar pra caminho morto nos 6 destinos.
Suíte 71/71. BLOQUEIO: nenhum.

ONDE ESTAMOS: fase de diagnóstico multi-IA concluída (Opus auditou protocolo e
experiência, GPT auditou código e testes, Kimi varreu origens). O que virou
conserto está em DECISOES 260825a–g. O que virou recomendação e AINDA É
DECISÃO DELE está listado abaixo em DECISÕES PENDENTES.

CONSERTADO EM 260825 (tudo verificado, não anunciado):
- Memória partida ao meio: `licoes-megabrain.md` órfão na raiz (8 lições)
  sombreava o canônico de `memoria/nucleo/` (166). Fundidas → 174, órfã em
  `99_to_delete/`, `achar()` corrigido, teste de regressão na suíte. O hook
  parou de dizer "126+" chumbado e passa a medir o total do índice.
- `RELATORIO.html`: 948.500 → 570.599 bytes. As entradas compostas em
  `IGNORAR_CENTRAL` nunca casavam e cada documento aparecia 3×. `assert` no
  import impede a repetição.
- O relatório NÃO GERAVA hoje: `AttributeError` em `eventos_hoje()` quando um
  evento traz `arquivo` como lista. Normalizado na leitura.
- Quatro versões diferentes (v3 / v6.5 / v6.7 / v7.1) nos arquivos que a IA lê
  na abertura, com o disco em v7.4. O h1 do relatório agora compõe de
  `VERSAO.txt`; `MEGABRAIN.md` e `README.md` perderam o número.
- `README.md` mandava rodar `relatorio-megabrain/gerar.py`, arquivado na v7.1.
- Skills: `~/.claude/skills/` não tinha nenhuma. Instaladas as 5 (megabrain,
  ingerir, grelhar, traycer, conclusao-megabrain) — o harness listou nesta
  sessão. Kimi foi de 4 pra 7, e `08_refresh-plugin-kimi.cmd` ganhou
  `SKILLS_EXTRA` pra não deixar skill nova pra trás de novo.
- Contrato de resposta apontava pra `referencias\` (morto na v7.1) na FONTE e
  nos 5 arquivos de identidade globais. Fonte corrigida e sync rodado nos 6.
- `mb-relatorio-agentes.py` lia `dna/` plano e concluía "nenhuma candidata"
  com os dados presentes em `motor/dna/` (achado do GPT).
- `01_acoes/01_ABRIR-RELATORIO.cmd`: o botão que faltava. Regenera e abre —
  o Gate 5 virou máquina em vez de disciplina.
- Docstring de `mb-sync.py` documentava `status --dir X`, que não roda: o
  `--dir` vem antes do subcomando.

DECISÕES PENDENTES (dele, não minhas — nada foi feito):
1. `git init` na central. Hoje não é repositório: conflito entre agentes não é
   detectável, perda não é recuperável, e `_github/repo-local` (espelho
   robocopy /MIR) é a única história — o último zip completo é de 22/08.
2. Consolidar 6 artefatos de saída em 3. `PAINEL-MEGABRAIN.html` (2,7 MB) não
   tem leitor e não tem link apontando pra ele; `RELATORIO-AGENTES.html` e
   `CATALOGO-VISUAL.html` estão parados desde 22/08. A decisão já existe pela
   metade em `DECISOES.md:1248` (260824).
3. Trava por escopo em vez de campo único no HANDOFF, ou fila
   `decisoes.d/<agente>-<ts>.md` com merge por script.
4. Teto de perguntas contraditório em 5 lugares (nenhum / 5 / 3 / 2 / 1).
5. `memoria/estado/` tem 7 arquivos e 3 estão vencidos (META de 19/08,
   CHECKLIST de 18/08, ALINHAMENTO de 18/08).
6. Gate 2 (orçar) é prosa sem medidor — vira sinal medível ou desce a nota do
   Gate 6.
7. As 7 skills do Matt Pocock seguem baixadas e paradas em `motor/dist/`;
   ele aprovou instalar 3 (writing-for-agents, research, wait-what).

SEGURADO: Tema 02 Wildfire · Figma v1 (arquivo megabrain) · 04_visuais/00_entrada
· motor/dna/usuario/ (imaculado) · 90_arquivo/migracao-v7-260824 e
90_arquivo/migracao-motor-260824 · `.mb-backup/260825_licoes-nucleo-antes-merge.md`
· `99_to_delete/260825_licoes-megabrain-ORFA-raiz.md` (nada apagado).

ACHADOS DE SEGURANÇA (corrigidos em 260824, reconferidos pelo GPT em 260825):
o `.env` do gerenteneuron nunca foi commitado (git log confirma) e não está
no export nem no clone; `dna/usuario/` bloqueado nas duas camadas (gerador +
.gitignore). Resíduo histórico: `pyvenv.cfg` e 3 caminhos pessoais antigos
seguem em commits antigos do clone local — sem chave, mas revelam o usuário.

ÚLTIMA AÇÃO (260825): auditoria multi-IA + os 11 consertos acima. Suíte 48 →
70 → 71 (o teste novo é o do órfão na raiz). Relatório regenerado ao fim,
como manda o Gate 5.
