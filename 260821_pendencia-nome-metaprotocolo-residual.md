260821_pendencia-nome-metaprotocolo-residual

# Pendência: resíduo do nome antigo (metaprotocolo/metaclaude → megabrain) + scripts do mb-abertura desalinhados

Registrado numa sessão do portfoliohs (henriquespina.studio), NÃO numa sessão focada no megabrain — por
isso isso vira só uma nota, sem execução. Henrique pediu explicitamente: "só adiciona como nota... pra
depois qnd eu rodar e focar só no megabrain, essas coisas sejam implementadas. esse deve ser o novo jeito."
Ou seja: daqui pra frente, achado de problema no megabrain fora de sessão dedicada = vira nota aqui, não
vira ação na hora.

## O que gatilhou

No fim de uma resposta técnica eu chamei a skill "metaprotocolo" (pra registrar uma lição) e ela ainda
carrega a descrição antiga: "metaclaude — protocolo de execução de alto padrão: context engineering...".
O Henrique viu isso e pediu pra padronizar tudo pra "megabrain" — literalmente em todo código, termo,
nome e nomeação.

## O que encontrei (verificação rápida, 260821, de dentro da sessão do portfoliohs)

1. **Duas skills convivendo.** `ListSkills` mostra "megabrain" E "metaprotocolo" como skills SEPARADAS,
   ambas habilitadas, descrições sobrepostas (a de "megabrain" já cita "/megabrain, /metaprotocolo,
   metaclaude" como gatilhos alternativos — sinal de rename parcial, não completo). Isso é exatamente o
   "resíduo do nome antigo" que o preflight do `mb-abertura` é desenhado pra pegar.

2. **`mb-abertura` (a skill, versão instalada) referencia scripts que não existem no repo.** A doc da
   skill manda rodar:
   - `bin\mb-preflight.py`
   - `bin\mb-renomear.py`
   - `bin\mb-padronizar.py`
   - `scripts\MEGABRAIN-PADRONIZAR.cmd`

   Nenhum desses existe em `_github-repo-local\bin\` nem `_github-repo-local\scripts\` (conferi listando a
   pasta inteira). O que EXISTE em `bin\` é outro conjunto: `mb-arrumar.py`, `mb-aspirador.py`,
   `mb-backup-central.py`, `mb-checar-meta.py`, `mb-check-version.py`/`.cmd`, `mb-contexto.py`,
   `mb-generate-template.py`, `mb-indice-licoes.py`, `mb-observar.py`, `mb-orquestrador-ia.py`,
   `mb-painel.py`, `mb-patch-v5.py`, `mb-recuperar-megabrain.py`, `mb-relatorio-agentes.py`,
   `mb-relatorio-dna.py`, `mb-relatorio-projeto.py`, `mb-relatorio-vivo.py`, `mb-sync-memoria.py`,
   `mb-sync-projeto-para-central.py`, `mb-sync.py`, `mb_utils.py`.

   Ou seja: **a skill `mb-abertura` documenta uma ferramenta de padronização de nome que ou nunca foi
   commitada, ou foi renomeada/removida sem atualizar a skill.** Precisa decidir: escrever os scripts que
   faltam, ou atualizar a doc da skill pra apontar pro que existe de verdade.

3. **`git fetch` falhou** com `403` vindo de um proxy (`unable to access
   'https://github.com/iriqspina/MEGAB-R-A-I-N.git/'... Received HTTP code 403 from proxy after CONNECT`).
   Isso rodou de dentro do shell restrito da sessão cloud (sandbox sem rede livre) — bem provável que seja
   limitação do ambiente daquela sessão, não um problema real do repo/credenciais. Mas por causa disso,
   **não dá pra confirmar se o local está mesmo sincronizado com o remoto** — `git status` disse "up to
   date" só com base no que já estava em cache local, sem checar contra o GitHub de verdade. Confirmar
   isso numa sessão com acesso de rede normal (local, não cloud) antes de mexer em qualquer coisa.

## O que fazer numa sessão focada em megabrain

- Rodar preflight de verdade (ou escrever o script, se não existir) e chegar em `legado: limpo`.
- Decidir o destino de `skills\metaprotocolo` vs `skills\megabrain` (a doc do `mb-abertura` diz que quando
  os dois existem, a operação é APAGAR a versão antiga, não renomear).
- Cobrir as 5 divergências que a doc menciona além do nome: grafia da pasta raiz, arquivo de lição global,
  número do gate citado, raiz de projeto, nome da fonte de identidade.
- Confirmar sync real com o GitHub (fetch de verdade, fora de sandbox restrito) antes de aplicar qualquer
  rename com `--aplicar`.
- Verificar se os scripts `mb-preflight.py`/`mb-renomear.py`/`mb-padronizar.py`/`MEGABRAIN-PADRONIZAR.cmd`
  existem em algum lugar (outra pasta? branch? versão local não commitada no Henrique?) antes de assumir
  que precisam ser escritos do zero.

Origem: sessão Cowork (portfoliohs), 260821.

---

## Atualização 260821 (sessão Cowork dedicada ao megabrain, mais tarde no mesmo dia)

Sessão focada só em megabrain (como o Henrique pediu que fosse o novo jeito). Conectou
a pasta `MEGA B R A I N` e resolveu o que dava pra resolver do lado Cowork/conta:

**Item 2 confirmado por listagem direta** (não só grep): `bin/` (raiz e
`_github-repo-local/`) não tem `mb-preflight.py`, `mb-renomear.py`, `mb-padronizar.py`
nem `MEGABRAIN-PADRONIZAR.cmd`. O que existe é o conjunto v6
(`mb-check-version.py --gate-drift`, `mb-arrumar.py`, `mb-aspirador.py`,
`mb-contexto.py`, etc.). `mb-abertura` documenta ferramenta que não existe no repo —
segue sem dono decidido (escrever os scripts ou atualizar a doc da skill).

**Item 3 (sync GitHub) ainda sem confirmação — e agora com um dado a mais.**
`git fetch` rodado direto no computador do Henrique (não em sandbox de nuvem) deu o
mesmo 403 de proxy que a sessão do portfoliohs viu. Ou seja, não é limitação de
ambiente de sessão — é rede/proxy desta máquina bloqueando `github.com`. `git status`
local diz "up to date with origin/main", mas isso é cache, não confirmação real. HEAD
local: `e95ce00`.

**Achado extra, fora do escopo da nota original:** a skill/plugin Cowork da conta
(`megabrain`, `metaprotocolo` solta, plugin `metaprotocolo`) estava **muito mais
desatualizada do que o esperado** — anterior até à v5.0 do `skills/megabrain/SKILL.md`
do repo, sem falar da v6 (`bin/mb-contexto.py`, lição por embeddings em
`licoes-megabrain.md`). Essa sessão tinha montado um primeiro plugin Cowork
(`megabrain` v1.0.0) **antes** de ter acesso a esta pasta — baseado só no cache velho
da conta, com arquitetura errada (arquivo de lição por usuário, que não existe no
projeto real). Descartado. Reconstruído como v1.1.0: skill `megabrain` = cópia direta
de `_github-repo-local/skills/megabrain/SKILL.md` (v5.0), `registrar-licao` = mesma
versão que já roda em `plugin-megabrain` (Kimi, v3.3.0), hook de sessão injeta o núcleo
de `megabrain-core` + lê `licoes-megabrain.md` da pasta conectada por recência (não
embeddings — essa infra não existe no sandbox Cowork). Entregue ao Henrique fora deste
repositório (arquivo `.plugin` na conversa), porque o plugin Cowork da conta não é
versionado aqui.

**Ainda sem dono:** publicar esse plugin Cowork correto DENTRO deste repositório
(irmão de `plugin-megabrain`, ex.: `plugin-megabrain-claude/` ou similar) pra não
depender de uma sessão de chat pra reconstruir do zero da próxima vez.

Origem: sessão Cowork dedicada a megabrain, 260821.

---

## Fechamento 260821 (sessão Kimi, noite)

- **Item 3 (sync GitHub) RESOLVIDO:** `git fetch`/`git ls-remote` rodados do
  Kimi nesta máquina passam limpo — o 403 era específico do bridge da sessão
  Cowork, não da rede do Henrique. Remoto confirmado: `origin/main` HEAD =
  `e95ce00` = HEAD local. Repo estava de fato sincronizado.
- **Plugin Cowork publicado no repo:** `plugin-megabrain-claude/` (v1.1.0).
  O `.plugin` baixado da conversa Cowork NÃO foi encontrado nesta máquina
  (varredura em Downloads/Desktop/Documentos/perfil); o plugin foi
  reconstruído das fontes versionadas — skills com diff 1:1 conferido (1
  linha declarada em cada), hook reescrito pela especificação. Se o `.plugin`
  original reaparecer, auditar o hook dele contra o do repo.
- **Resíduo `.metaprotocolo\licoes.md`:** o caminho `~/.claude/skills/synced/`
  não existe nesta máquina (as 3 skills citadas vivem na conta Cowork, fora
  do alcance local). Das locais, só `~/.kimi-code/skills/logout-projeto/
  SKILL.md` tinha o resíduo — corrigido para `licoes-megabrain.md` na central.
  `tlou` e `modeloslocais` sem resíduo nas cópias locais; as cópias da conta
  Cowork seguem sem verificação (sem acesso).
- **Segue sem dono (inalterado):** `mb-abertura` documenta
  `mb-preflight.py`/`mb-renomear.py`/`mb-padronizar.py`/`MEGABRAIN-PADRONIZAR.cmd`,
  que não existem no repo. Decisão pendente: escrever os scripts ou atualizar
  a doc da skill.
- **Novo achado:** o `plugin-megabrain/` (Kimi) NÃO é versionado neste repo —
  vive só na central. O irmão Claude entrou versionado; o Kimi não. Decidir
  se o repo passa a versionar os dois ou nenhum.

Origem: sessão Kimi dedicada a megabrain, 260821.
