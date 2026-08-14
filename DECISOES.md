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
