# Sincronizar identidade entre agentes (Claude Code, Kimi CLI, Gemini CLI)

Extensão do Gate 0 (assumir) — não confundir com o Gate 0/6 de **estado de
projeto** (`ESTADO.md`/`HANDOFF.md`). Isto sincroniza **quem é a pessoa e
como ela quer resposta** — perfil, preferências, formato obrigatório — não
o que o projeto está fazendo agora.

Rode isto ao configurar um agente novo num projeto, ou sempre que o
arquivo de identidade mudar.

## Por que isto existe

Um arquivo de identidade por pessoa (nome, contexto, formato obrigatório de
resposta, preferências fixas) é a **fonte única**. Cada agente lê memória
de um jeito diferente — arquivo diferente, mecanismo diferente. Sem este
gate a informação diverge entre eles silenciosamente: já aconteceu de duas
cópias do mesmo texto ficarem em lugares diferentes, uma desatualizada em
relação à outra, sem ninguém perceber até comparar as duas.

**Regra dura: nunca edite a cópia sincronizada.** Edite sempre o arquivo
de identidade fonte e rode a sincronização de novo. Editar a cópia é o
mesmo erro de reescrever `DECISOES.md` — perde a fonte de verdade.

**Este arquivo de identidade nunca vai pro repositório público do
protocolo.** É dado pessoal de quem opera, não conteúdo de pipeline —
fica local, ou num repo privado do próprio projeto.

## O que você precisa fazer, dependendo de quem você é

Não copie o conteúdo cegamente pra todo lugar. O mecanismo de import muda
por agente — identifique quem você é antes de agir (nome do binário,
variável de ambiente, ou pergunte se não tiver certeza) e siga só a seção
correspondente.

### Se você é Claude Code
Arquivo de memória: `CLAUDE.md` na raiz do repo.
Claude Code resolve imports com sintaxe `@caminho/arquivo.md` — isso lê o
arquivo de destino em tempo real, não duplica texto.
1. Abra (ou crie) `CLAUDE.md` na raiz do projeto.
2. Garanta que contenha a linha: `@<caminho-do-arquivo-de-identidade>`
3. Se a linha já existir, não faça nada — já está sincronizado por
   definição (é referência, não cópia; sempre reflete a versão atual).

### Se você é Gemini CLI
Arquivo de memória: `GEMINI.md` na raiz do projeto (existe também um
arquivo global de usuário para regra que vale em todo projeto — não use
esse aqui, esta regra é por projeto).
Gemini CLI também resolve `@arquivo.md` nativamente, mesma lógica do
Claude Code.
1. Abra (ou crie) `GEMINI.md` na raiz do projeto.
2. Garanta a linha: `@<caminho-do-arquivo-de-identidade>`
3. Se já existir, não faça nada.

### Se você é Kimi CLI
Arquivo de memória: `AGENTS.md` na raiz do projeto.
**Import por `@arquivo.md` não está confirmado para Kimi CLI no momento em
que isto foi escrito** — trate como não suportado até verificar o
contrário. Nesse caso a sincronização precisa copiar o conteúdo de fato,
não apontar pra ele.
1. Rode o script de sincronização (ex.: `mb-sync-memoria.py --target
   kimi`, se o projeto tiver um).
2. O script escreve o conteúdo do arquivo de identidade dentro de
   `AGENTS.md`, entre marcadores (`<!-- MEGABRAIN:AUTO-SYNC:START -->` /
   `END`) — idempotente, não duplica se rodar de novo.
3. Sem script disponível? Copie o conteúdo manualmente entre esses mesmos
   marcadores, nunca em outro lugar do arquivo, e confira que os
   marcadores não existem duplicados.

## Depois de sincronizar

Confirme visualmente que o arquivo de destino reflete o conteúdo atual da
fonte — não assuma que o script/import funcionou. Isso é o próprio Gate 5
(verificar) aplicado aqui.

## Quando rodar isto de novo

- Sempre que o arquivo de identidade mudar.
- Ao configurar um agente novo neste projeto pela primeira vez.
- Se a pessoa pedir "sincroniza minha identidade" ou equivalente.
- Se notar qualquer divergência entre o que está sincronizado e a fonte —
  pare o que está fazendo e sincronize antes de continuar.
