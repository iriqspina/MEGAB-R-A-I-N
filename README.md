# MEGABRAIN

**Versão atual: v6.4 (2026-08-22).** A versão vale o que está em `VERSAO.txt`
(changelog completo na central privada; aqui só a entrada vigente). Skill
`megabrain` v5.4 · plugin Claude/Cowork v1.2.0.

Protocolo de execução para agentes de IA (Claude Code, Kimi CLI, Gemini CLI
como fallback opcional, ou colado direto em qualquer chat) — pensado para
dois ou mais agentes trabalhando no mesmo projeto sem pisar um no outro, e
para impedir que entregas de IA saiam genéricas.

Para uma explicação visual e curta, gere o relatório institucional com
`python relatorio-megabrain/gerar.py` (sai `RELATORIO.html`, uma tela por
assunto). O HTML não vem no pacote: edite a fonte e regenere.

## O que tem aqui

- `skills/megabrain/SKILL.md` — o protocolo: gates de entrega (enquadrar → gerar → auditar →
  verificar → passar o bastão → aprender), o gate de assumir trabalho
  multi-agente, Duplo Diamante para projetos de design, roteamento de
  arquitetura.
- `skills/ingerir/SKILL.md` — a camada de conhecimento (v6.2+): fontes brutas
  em `cerebro/raw/` viram páginas de wiki (um tópico por arquivo) e cards de
  pessoas, com `cerebro/INDICE.md` mantido pelo `/ingerir`. Lição de
  processo fica no `/registrar-licao`; fato de conteúdo fica no cérebro.
- `plugin-megabrain-claude/` — o mesmo protocolo empacotado como plugin
  Cowork/Claude (`.claude-plugin/plugin.json` + `hooks/` + `skills/`):
  `megabrain`, `ingerir`, `registrar-licao`. Gerado por
  `bin/mb-build-plugin-claude.py`; instala por arquivo `.plugin`.
- `gerenteneuron/` — app local de chat unificado multi-IA. Roda no navegador,
  sem dependências externas, e escolhe o modelo mais barato capaz de responder
  bem (ou deixa o usuário escolher manualmente).
- `MEGABRAIN.md` — a camada de projeto: fases macro (estado → spec →
  implementar → publicar), artefatos, regras de ouro, níveis de adoção.
- `referencias/` — a camada de execução, carregada sob demanda: anti-slop
  (léxico e estrutura banidos com teste), metaprompts (padrões e templates
  colecionáveis), engenharia de contexto, avaliação/rubricas, Duplo
  Diamante completo, roteamento quando o design vira código, sincronização
  de identidade entre agentes, governança comercial, Amarrador de Pontas,
  Contraditor, teammates econômicos e um prompt portátil pra colar em
  qualquer IA sem instalar nada.
- `bin/` — scripts testados do protocolo:
  - `mb-sync.py` — trava de handoff multi-agente em `HANDOFF.md`.
  - `mb-sync-memoria.py` — sincroniza um arquivo de identidade local para
    `CLAUDE.md`/`GEMINI.md`/`AGENTS.md`, idempotente.
  - `mb-check-version.py` — compara a versão do megabrain de um projeto com
    a central e sincroniza quando necessário.
  - `mb-generate-template.py` — gera o pacote público sanitizado
    (`260810_github-export/`).
  - `mb-aspirador.py` — limpeza mecânica e não destrutiva de código
    (dry-run por padrão, backup obrigatório).
  - `mb-relatorio-dna.py` — gera o relatório DNA do protocolo em `dna/`.
  - `mb-relatorio-projeto.py` — gera o relatório de instância de um
    projeto específico (`RELATORIO.html`), com materiais consolidados e
    botões de ação HTTPS/âncora passados por `--acao "Rótulo|URL"`.
  - `mb-sync-projeto-para-central.py` — sobe alterações de um projeto para
    a central do megabrain quando o projeto ficou mais novo.
  - `mb-preflight.py` — abertura de sessão: git atrás/sem push, skill
    instalada × repo, fatos vencidos, resíduo de nome legado. Gate 0 começa
    por ele.
  - `mb-relatorio-vivo.py` — relatório vivo da central: versão atual ×
    anterior, commit, push pendente e versão puxada por projeto.
  - `mb-build-plugin-claude.py` — regenera e empacota o plugin Claude/Cowork
    a partir das fontes (`--check` acusa drift).
  - `mb-backup-central.py` / `mb-recuperar-megabrain.py` — backup zip da
    central e recuperação de um projeto a partir dele.
  - `mb-contexto.py`, `mb-painel.py`, `mb-arrumar.py`, `mb-indice-licoes.py`
    — injeção de contexto por hook, painel da central, arrumação mecânica e
    índice de lições. `mb_utils.py` é a biblioteca comum (resolvedor de
    pastas da central).

## Como usar

1. Instale como skill no seu agente apontando pra este diretório. No Codex,
   use `skills/codex-megabrain/`; nos agentes que consomem o protocolo
   agnóstico, use `skills/megabrain/`. Para abrir o chat multi-IA local,
   use `skills/gerenteneuron/`. **Ou:**
2. Instale o plugin Cowork/Claude: `python bin/mb-build-plugin-claude.py`
   gera o `.plugin`; Cowork → plugins → instalar a partir de arquivo. As
   skills passam a responder como `megabrain:megabrain`, `megabrain:ingerir`
   e `megabrain:registrar-licao`. **Ou:**
3. Cole `referencias/260810_PROMPT-PORTATIL.md` no início de uma conversa
   com qualquer IA — não depende de arquivo nem de plataforma.

## Como adaptar pro seu projeto

Os 4 arquivos de estado multi-agente (`ESTADO.md`, `HANDOFF.md`,
`DECISOES.md`, `LICOES.md`) não vêm prontos aqui — são criados por projeto,
na raiz dele. `SKILL.md` gate 0 e gate 6 descrevem o formato.

O arquivo de identidade que `mb-sync-memoria.py` sincroniza (seu perfil,
preferências, formato de resposta) também não vem aqui — é pessoal, fica
no seu computador ou num repo privado, nunca neste pacote público. Ver
`referencias/260810_sync-memoria.md` para o protocolo.

O gerador público exclui `ESTADO.md`, `HANDOFF.md` e `DECISOES.md` da central,
porque esses arquivos descrevem a operação privada. O `RELATORIO.html`
institucional é sanitizado e distribuído; cada projeto cria o próprio estado e
seu relatório de instância.

## Uso offline

A pasta `MEGABRAIN/` dentro de cada projeto é uma cópia local completa do
protocolo. Se o GitHub ou a internet caírem, os scripts continuam
funcionando. Use:

```
python MEGABRAIN/bin/mb-check-version.py --projeto "caminho/do/projeto" --offline
```

Para backup da central:

```
cd <pasta-central>
python bin/mb-backup-central.py
```

Para recuperar um projeto:

```
python MEGABRAIN/bin/mb-recuperar-megabrain.py --projeto "caminho/do/projeto" --fonte "backup.zip"
```

Mais detalhes: `MEGABRAIN/OFFLINE.md`.

## Histórico — migração v4.0 (diferenciação de usuário)

Seção mantida só para quem vem de versão anterior à v4.0 (2026-08). Hoje o
`mb-check-version.py` cuida disso no Gate 0; o passo a passo abaixo é o manual.

A v4.0 introduziu o campo `USUARIO:` no `HANDOFF.md` e nos arquivos de
identidade (`CLAUDE.md`/`GEMINI.md`/`AGENTS.md`). Se você forkou/clonou o
repositório ou sincronizou um projeto derivado, configure seu perfil:

1. Crie `260810_memoria-pessoal.md` na raiz do projeto/central.
2. Adicione `USUARIO: Seu Nome` no início.
3. Rode:
   ```
   python MEGABRAIN/bin/mb-sync-memoria.py --source 260810_memoria-pessoal.md --target all --dir .
   ```
4. Use `python MEGABRAIN/bin/mb-sync.py lock --agente Kimi --escopo ...` —
   o `HANDOFF.md` vai registrar seu nome automaticamente.

Detalhes completos: `MEGABRAIN.md` seção 1b ou
`referencias/260810_sync-memoria.md`.
