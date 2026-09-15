# PADRÃO ÚNICO DE RELATÓRIO · POP v1.2 · 260915

Decisão do <USUARIO> (260915, esta sessão): **todo relatório equivalente, em todos os
projetos, usa UM padrão visual — o template POP v1.2**, o mesmo aprovado por ele em
260914 (DECISOES 260914). Fim das 8 famílias de estética.

## Temas: escuro (default) e claro (opção · 260915)

POP v1.2 é o padrão único de relatórios, com temas **escuro e claro**. Escuro é o
tema inicial padrão. Claro é uma opção de leitura (pedido do <USUARIO>: "facilita
minha leitura") que preserva estrutura, conteúdo e interações — paleta clara
própria com acentos escurecidos pra contraste AA medido (mínimo ≥ 4.5:1), não é
filtro invertido. O botão no cabeçalho ("Tema: claro/escuro") alterna sem
recarregar e salva a escolha (chave `megabrain.pop.tema`) quando o armazenamento
do navegador está disponível. Precedência: preferência salva válida → tema
inicial do arquivo → escuro. Os três geradores centrais aceitam `--tema
claro|escuro` (vivo e DNA; no `mb-relatorio-projeto.py` é `--tema-tela`, porque
`--tema` lá já escolhe o esqueleto); sem a opção, geram escuro. As definições
dos dois temas ficam incorporadas ao HTML (fonte compartilhada: `bin/mb_pop_tema.py`,
espelhada no template). A pele legado tem variante clara por seleção explícita
(`html[data-tema="claro"]`) — sem o atributo, tudo segue escuro. Prova funcional:
`node bin/mb-verificar-pop-tema.mjs <html>` (8 cenários + varredura de cliques
nos 2 temas + contraste computado + rede).

## Fonte única do padrão

`motor/modelos/relatorios/260914_pop/relatorio-pop.html` + o contrato no LEIAME ao lado.
Modelos concorrentes (260909_glass, 260909_vidro-claro) arquivados em
`90_arquivo/modelos-aposentados-260915/` — não usar mais.

## Contrato duro (o que torna um relatório "no padrão")

1. **Arquivo único, offline, zero recurso remoto** (mesma regra do relatório vivo).
2. **DNA Raycast > Warp > Duolingo**: glow saturado do topo, cores chapadas por setor,
   número-dado como herói (tabular), molduras `fig.` com legenda técnica, mascote com falas.
3. **TDAH**: ícone + texto em toda informação, anti-vertical (mais por tela, menos scroll),
   uma tela por setor, listas sem variância colapsadas.
4. **Todo clique responde** (lição "protótipo mudo é protótipo morto"): `data-diz` (toast),
   `data-copia` (clipboard com fallback), `<a>` real que navega e avisa; `role="button"`
   + Enter/Espaço onde não é botão nativo.
5. **Conteúdo entra por slots** (hero-status, orc-gates, orc-runs, orc-cotas, acoes-voce,
   saude-chips, anel-projetos/tabela-projetos, telemetria, panes) — o gerador troca o dado,
   o esqueleto e os controles ficam.
6. **Dado com fonte e data**: leitura fotografada ("cotas: leitura 14/09 21:37"), nunca
   "ao vivo" sem fonte; estado preciso ("REVISÃO APROVADA" ≠ entrega).

## Quem emite no padrão

- `bin/mb-relatorio-vivo.py` → `00_painel/RELATORIO.html` (vivo do megabrain)
- `bin/mb-relatorio-dna.py` → `motor/dna/RELATORIO-DNA.html`
- `bin/mb-relatorio-projeto.py` → relatórios de projeto (cópia MEGABRAIN/)
- geradores próprios dos projetos (Curriculo, Design Diamond, Financeiro da Silva,
  Linkedolas, mimde, Portfolio/TLOU) → pele POP no esqueleto de cada um
- `apps/megabrain-dashboard/` → dashboard com a marca POP (função intocada)

Pele sobre esqueleto antigo (arquivados e páginas que não valem reconstruir): camada
`<style id="mb-pop-skin">` injetada antes de `</head>`, adaptada às classes daquele
esqueleto — fundo escuro com auroras, vidro nos cartões, paleta Duolingo nos estados,
display pesado no h1, raio 10px. Nunca reescrever o conteúdo histórico, só a pele.

## Exceções (não são pele de relatório)

- `260914_narrado/` — apresentação narrada (audiovisual, voz + animação), classe própria.
- Evidências congeladas: `.automations/runs/`, backups, `.claude/worktrees/`, `.scratch/`,
  `99_to_delete/`, `.dna-backup/`, prints PNG.
- Relatórios `.md` — texto de trabalho, sem pele.

## Verificação obrigatória antes de entregar

Print headless 1440px revisado NA IMAGEM (título visível, contraste, nada desbotado —
animação de entrada engana o headless) + varredura de cliques com resposta. Sem print
passando, não é entrega (lição 260914).
