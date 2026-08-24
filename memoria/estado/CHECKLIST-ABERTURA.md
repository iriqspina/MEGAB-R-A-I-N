# Checklist de abertura — megabrain core

## 260818 — auditoria pausada antes do sync de identidade

- **Checar:** se o subagente coder (agent-4 / task agent-je3rze2w) terminou
  todos os itens F1–F13. Se sim, coletar o output.log.
- **Por quê:** sem isso a próxima sessão pode repetir trabalho já feito ou
  tentar rodar sync sobre arquivos que ainda estão sendo editados.
- **Como:** `TaskOutput agent-je3rze2w` ou `ls .mb-backup/260818/` para
  confirmar que os arquivos velhos foram movidos.
- **RESOLVIDO:** não

## 260818 — plugin Kimi possivelmente desatualizado

- **Checar:** diff entre `skills/megabrain/SKILL.md` central e
  `<USER_HOME>/.kimi-code/plugins/managed/megabrain/skills/megabrain/SKILL.md`;
  idem `MEGABRAIN.md`.
- **Por quê:** `skills/megabrain/SKILL.md` e `MEGABRAIN.md` da central foram
  editados depois que o refresh do plugin rodou no subagente.
- **Como:** `diff` seguido de `robocopy` das linhas 48–50 do
  `01_acoes/260824_sincronizar-projetos.cmd` se necessário.
- **RESOLVIDO:** não

## 260818 — identidade ainda não propagada pros agentes

- **Checar:** se `01_acoes/260824_sincronizar-identidade.cmd` já foi rodado nesta
  sessão e se os blocos AUTO-SYNC em `~/.claude/CLAUDE.md`,
  `~/.gemini/GEMINI.md`, `~/.kimi/AGENTS.md`, `~/.kimi-code/AGENTS.md` e
  `~/.codex/AGENTS.md` batem com `260810_memoria-pessoal.md`.
- **Por quê:** o contrato de resposta só vale se todos os agentes o receberem
  igual. Rodar sem conferir reproduz a divergência que esta sessão tentou
  eliminar.
- **Como:** rode o .cmd e depois `diff` ou `grep` pelos marcadores
  `MEGABRAIN:AUTO-SYNC`.
- **RESOLVIDO:** não

## 260818 — output style do Claude

- **Checar:** se `~/.claude/output-styles/megabrain.md` existe e se
  `~/.claude/settings.json` contém `"outputStyle": "megabrain"`.
- **Por quê:** sem settings.json apontando pro estilo, o arquivo gerado fica
  inerte.
- **Como:** `cat ~/.claude/settings.json` e `ls ~/.claude/output-styles/`.
- **RESOLVIDO:** não

## 260818 — commits pendentes no repo local

- **Checar:** status de `_github/repo-local` (3 commits à frente de
  `origin/main`, 6 arquivos modificados, RELATORIO.html untracked).
- **Por quê:** o repo público está desatualizado; a sanitização do
  gerenteneuron SKILL.md foi corrigida no working tree mas não commitada.
- **Como:** `git -C _github/repo-local status --short` e decidir com o
  usuário sobre commit/push (push em repo público exige autorização).
- **RESOLVIDO:** não

## 260822 — o relatório agora tem tema, e o tema mora fora do gerador
- Checar: se o relatório abrir com cara diferente do esperado, olhe
  `data-tema` no `<html>` e a chave `mb-relatorio:tema` no localStorage antes
  de suspeitar do gerador.
- Por quê: a cor não está mais em `tokens.css` — está em
  `modelos/visuais/temas/NN-*.css`, e a escolha do leitor persiste entre
  sessões. Editar `tokens.css` esperando mudar a aparência não funciona mais.
- Como: `python bin/mb_visual.py --listar` e abrir
  `modelos/visuais/temas/` para ver quais temas existem.

## 260822 — 04_visuais/ é do humano; não trate movimentação como bagunça
- Checar: antes de "organizar" `04_visuais/`, confirme que os arquivos em
  `01_sim/` e `02_nao/` foram postos lá pelo <USUARIO>.
- Por quê: a triagem dele É o dado. Um agente "arrumando" a pasta apaga a
  única fonte que temos do gosto dele — e os `.txt` de motivo em `02_nao/`
  valem mais que qualquer briefing.
- Como: nenhum script lê essa pasta. Leia, nunca reorganize sem pedir.

## 260822 — screenshot de site só pelo Chrome dele
- Checar: antes de planejar captura de página web, lembre que o container
  não alcança a web aberta.
- Por quê: Playwright está instalado e funciona, mas todo host externo dá
  `ERR_CONNECTION_RESET` (o proxy só libera npm/pypi). Perdi ~5 min
  descobrindo isso.
- Como: usar `mcp__claude-in-chrome__*` no navegador do <USUARIO>
  (autorização permanente). Para render local, embutir fontes via
  `@fontsource` do npm como data URI e usar `wait_until='load'`.

## 260824 — push da v7 não confirmado
- Checar: `.mb-log\push.log` tem entrada DEPOIS de 24/08 18:30? Painel (bloco
  git) mostra "nada pendente de push"?
- Por quê: o log parava em 15:23 (pré-v7) com mensagem quebrada "='"; o
  publicar foi corrigido no logout, mas o push pode não ter rodado — o GitHub
  pode estar sem a v7 inteira.
- Como: abrir 00_painel\RELATORIO.html; se pendente, rodar
  01_acoes\260824_publicar-e-fotografar.cmd → 260824_enviar-pro-github.cmd.

- RESOLVIDO: 260824 (tarde) — push confirmado direto no remoto via git
  ls-remote no container: GitHub = repo-local = cf73db8; painel regenerando.

## 260824 — plugin instalado pode não ser o 1.6.1
- Checar: /root/.claude/plugins/synced/megabrain/.claude-plugin/plugin.json
  == 1.6.1? (nesta sessão ainda constava 1.3.0 depois de ele dizer que
  instalou — o sync da conta pode demorar/ter falhado)
- Por quê: skill velha carregada = regras antigas (31 KB, caminhos v6).
- Como: cat no arquivo acima no começo da sessão; se velho, pedir pra ele
  reinstalar dist\260824_megabrain-v1.6.1.plugin.

## 260824 — layout v7: caminhos antigos morreram
- Checar: antes de citar caminho, resolver via bin/mb_utils.achar()/pasta()
  (04_relatorios→00_painel · 05_scripts→01_acoes · 0X_→memoria/ · cmds com
  prefixo 260824 e nome de verbo).
- Por quê: instrução com caminho velho manda o humano pra pasta que não
  existe; hook local aponta pra bin\ (bin fica na raiz — não mover).
- Como: na dúvida, ls na raiz + mb_utils; o mapa real está no board 15 do
  03_docs\260824_megabrain-do-zero.html.

## 260824b — plugin Cowork reinstalado no fim do dia; confirmar 1.6.1
- Checar: /root/.claude/plugins/synced/megabrain/.claude-plugin/plugin.json
  == 1.6.1 E a skill megabrain carregada é a v6.0 enxuta (~10 KB).
- Por quê: ele desinstalou/reinstalou em 260824 à noite justamente pra isso;
  se ainda constar 1.3.0, o sync da conta falhou de novo e a skill carregada
  é velha (caminhos v6).
- Como: cat no plugin.json acima logo na abertura; conferir tamanho/gatilhos
  da SKILL.md que o plugin serviu.
