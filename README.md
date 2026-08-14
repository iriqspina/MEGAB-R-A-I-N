# MEGABRAIN

Protocolo de execução para agentes de IA (Claude Code, Kimi CLI, Gemini CLI
como fallback opcional, ou colado direto em qualquer chat) — pensado para
dois ou mais agentes trabalhando no mesmo projeto sem pisar um no outro, e
para impedir que entregas de IA saiam genéricas.

## O que tem aqui

- `SKILL.md` — o protocolo: gates de entrega (enquadrar → gerar → auditar →
  verificar → passar o bastão → aprender), o gate de assumir trabalho
  multi-agente, Duplo Diamante para projetos de design, roteamento de
  arquitetura.
- `MEGABRAIN.md` — a camada de projeto: fases macro (estado → spec →
  implementar → publicar), artefatos, regras de ouro, níveis de adoção.
- `referencias/` — a camada de execução, carregada sob demanda: anti-slop
  (léxico e estrutura banidos com teste), metaprompts (padrões e templates
  colecionáveis), engenharia de contexto, avaliação/rubricas, Duplo
  Diamante completo, roteamento quando o design vira código, sincronização
  de identidade entre agentes, e um prompt portátil pra colar em qualquer
  IA sem instalar nada.
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
    projeto específico (`RELATORIO.html`).
  - `mb-sync-projeto-para-central.py` — sobe alterações de um projeto para
    a central do megabrain quando o projeto ficou mais novo.

## Como usar

1. Instale como skill no seu agente (Claude Code, Kimi CLI) apontando pra
   este diretório, **ou**
2. Cole `referencias/260810_PROMPT-PORTATIL.md` no início de uma conversa
   com qualquer IA — não depende de arquivo nem de plataforma.

## Como adaptar pro seu projeto

Os 4 arquivos de estado multi-agente (`ESTADO.md`, `HANDOFF.md`,
`DECISOES.md`, `LICOES.md`) não vêm prontos aqui — são criados por projeto,
na raiz dele. `SKILL.md` gate 0 e gate 6 descrevem o formato.

O arquivo de identidade que `mb-sync-memoria.py` sincroniza (seu perfil,
preferências, formato de resposta) também não vem aqui — é pessoal, fica
no seu computador ou num repo privado, nunca neste pacote público. Ver
`referencias/260810_sync-memoria.md` para o protocolo.

## Migração v4.0 — diferenciação de usuário

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
