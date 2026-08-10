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
- `bin/` — dois scripts testados: `mb-sync.py` (trava de handoff
  multi-agente em `HANDOFF.md`) e `mb-sync-memoria.py` (sincroniza um
  arquivo de identidade local para `CLAUDE.md`/`GEMINI.md`/`AGENTS.md`,
  idempotente).

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
