---
name: neuroninhos
description: Gerencia os modelos locais do <USUARIO> (Ollama, LM Studio) como "filhos" do megabrain — integrados ao harness (skills, protocolo, ritmo de cota) e templatezáveis pra qualquer máquina/projeto. Use quando o usuário disser /neuroninhos, pedir para otimizar/integrar Ollama ou LM Studio ao megabrain, ou perguntar sobre modelo local como worker de orquestração.
---

# Neuroninhos — modelos locais do megabrain

Pedido de <USUARIO> em 260909: Ollama e LM Studio (modelos rodando na máquina dele,
sem cota externa) entram no harness megabrain do mesmo jeito que Claude/Codex —
com skill própria, ciente do protocolo, e melhorando com o uso. "São filhos do
megabrain agora": não é integração pontual, é um projeto que se mantém.

Fonte de verdade do desenho e do estado real: `neuroninhos/` na raiz da central
(pasta de projeto, não a skill). Ler `neuroninhos/ESTADO.md` antes de agir — o
plano detalhado de integração (Ollama primeiro, LM Studio depois) pode ainda
estar em produção por um agente separado; não descrever como pronto o que só
está planejado.

1. `neuroninhos/template/` guarda o template portável — o que templatizar
   (config, prompts de sistema, scripts de detecção/otimização) pra instalar o
   mesmo padrão em qualquer máquina/projeto que tenha Ollama e/ou LM Studio.
2. `neuroninhos/ESTADO.md`, `HANDOFF.md`, `DECISOES.md` seguem a mesma
   convenção usada em `pets/` — ler ESTADO → HANDOFF → fim de DECISOES antes de
   continuar o trabalho, igual a qualquer outro projeto da central.
3. Lição já registrada e válida aqui: Ollama herda contexto/parâmetros globais
   por padrão — sempre limitar `num_ctx`/`num_predict`/`keep_alive` explicitamente
   na chamada, nunca depender da configuração global do usuário (ver
   `memoria/nucleo/licoes-megabrain.md`, entrada sobre limitar contexto do Ollama).
4. Cota de modelo local não é escassa como Claude/Codex (sem limite externo),
   mas tem custo real de VRAM/latência na máquina do <USUARIO> — não tratar
   "sempre disponível" como "sempre grátis, pode saturar".
