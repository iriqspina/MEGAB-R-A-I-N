# Checklist de abertura — MEGABRAIN core

Itens que mudaram de um jeito silencioso hoje (260909) e que uma sessão nova,
sem aviso, perderia tempo ou erraria por causa disso. Append-only — item
resolvido ganha `RESOLVIDO: <data>`, nunca se apaga.

## 260909 — histórico do git carregando 624 MB de binário do Pets
- Checar: `du -sh .git` antes de supor que o repositório está no tamanho normal.
- Por quê: uma sessão paralela (Fable 5.1) commitou `pets/` inteiro com os 2
  instaladores (370 MB + 254 MB) antes de outra sessão tirar do índice
  (`git rm --cached`, commit `6de598b`). Tirar do índice não tira do
  histórico já gravado — os blobs continuam ocupando espaço até alguém
  reescrever o histórico de propósito.
- Como: `git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | awk '$1=="blob"{print $3,$4}' | sort -rn | head` mostra os dois arquivos como, de longe, os maiores objetos do repositório.

## 260909 — pipeline de publicação não roda sem decisão sobre o item acima
- Checar: se o <USUARIO> pedir "publicar"/"subir pro GitHub"/"terminar o push",
  não presumir `git push` direto — este repo central não tem `remote`
  (proposital, DECISOES 260908c, privacidade). O caminho real é
  `01_acoes/*_enviar-pro-github.cmd` → `_github/repo-local` (export sanitizado).
- Por quê: rodar esse pipeline sem resolver o item do histórico acima carrega
  os 624 MB (e o conteúdo de `pets/`, que nunca devia ter ido pro git) pro
  clone público, se o sanitizador não estiver preparado pra excluir `pets/`
  especificamente.
- Como: confirmar com o <USUARIO> qual dos dois caminhos ele quer (aceitar
  o histórico como está, ou pedir reescrita local primeiro — segura, sem
  remote pra conflitar) ANTES de rodar o `.cmd`, e confirmar de novo antes
  do `.cmd` em si, por afetar repositório público.

## 260909 — múltiplas sessões simultâneas na mesma pasta central hoje
- Checar: `git log --oneline -15` antes de descrever "o que está commitado"
  — várias sessões (pelo menos 4-5 interativas, mais worktrees em
  `.claude/worktrees/`) escreveram no mesmo checkout sem se coordenar antes.
- Por quê: uma instrução genérica tipo "commite o que está pendente" mandada
  pra duas sessões ao mesmo tempo causou uma corrida real (não hipotética)
  entre um `git add` desta sessão e um commit de outra, minutos atrás.
- Como: antes de um commit/push amplo, checar `ps`/sessões ativas na mesma
  pasta (ou perguntar ao <USUARIO>) em vez de assumir exclusividade.

## 260913 — tarefa do Portfolio mudou de ação (wrapper VBS; não reverter sem ler)
- Checar: `\PortfolioHS-Local-Disponibilidade-260912` aponta para `WScript.exe "<PROJETOS_ROOT>\Portfolio\tools\260912_manter-local-hidden.vbs"` e `Portfolio\evidencias\260912_disponibilidade-local\260912_ultimo-estado.json` segue `healthy` com timestamp recente (a cada 2 min).
- Por quê: a ação antiga (`powershell -WindowStyle Hidden` direto) piscava uma janela de terminal roubando o foco a cada 2 min; "corrigir" a tarefa de volta reativa o sintoma que levou a sessão de 260913 a caçar.
- Como: `schtasks /query /tn "\PortfolioHS-Local-Disponibilidade-260912" /xml` (conferir Command/Arguments) e ler o JSON de estado.
