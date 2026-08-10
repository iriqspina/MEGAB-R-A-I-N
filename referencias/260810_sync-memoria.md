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

## Global (uma vez) vs. por projeto (repetido)

Os três agentes suportam um arquivo de memória **global**, no diretório do
usuário, que carrega em toda sessão, de qualquer projeto — configure uma
vez, nunca mais repita por projeto:

| Agente | Arquivo global | Arquivo por projeto (sobrepõe o global) |
|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md` | `CLAUDE.md` na raiz do projeto |
| Gemini CLI | `~/.gemini/GEMINI.md` | `GEMINI.md` na raiz do projeto |
| Kimi CLI / Kimi Code | `~/.kimi/AGENTS.md` | `AGENTS.md` (ou `./.kimi/AGENTS.md`) na raiz do projeto |

Identidade (nome, preferências, formato obrigatório de resposta) é a
mesma em todo lugar → use o **global**. Regra que só vale num projeto
específico → arquivo por projeto (ele tem prioridade sobre o global).

## O que você precisa fazer, dependendo de quem você é

Os três agentes resolvem import com a mesma sintaxe — `@caminho/arquivo.md`
— seja no arquivo global ou no de projeto. Isso lê o arquivo de destino em
tempo real, sem duplicar texto: mudou a fonte, mudou em todo lugar sem
rodar nada de novo.

1. Abra (ou crie) o arquivo global do seu agente (tabela acima).
2. Garanta que contenha a linha: `@<caminho-completo-do-arquivo-de-identidade>`
3. Se a linha já existir, não faça nada — já está sincronizado por
   definição (é referência, não cópia).

**Cuidado com espaço no caminho.** `@` costuma parsear até o próximo
espaço em branco — se a pasta do arquivo de identidade tem espaço no nome
(comum em pasta pessoal tipo "Meus Documentos" ou nome com espaço duplo),
o import pode cortar o caminho no meio e falhar silenciosamente. Nesse
caso use o modo conteúdo abaixo em vez de import — ele não depende de
path parsing nenhum.

### Alternativa sem @import: modo conteúdo (recomendado se o caminho tem espaço)

`bin/mb-sync-memoria.py --source <identidade> --target all --modo
conteudo --dir <pasta>` injeta o CONTEÚDO do arquivo de identidade dentro
de `CLAUDE.md`/`GEMINI.md`/`AGENTS.md`, entre marcadores
(`<!-- MEGABRAIN:AUTO-SYNC:START/END -->`) — idempotente, atualiza sem
duplicar, funciona pros três agentes, sem depender de sintaxe de import.
`--dir "%USERPROFILE%"` (Windows) ou `--dir ~` (Linux/Mac) instala global.

Pra instalar só num agente: troque `--target all` por `--target
claude|gemini|kimi`.

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
