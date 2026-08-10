# Sincronizar memória entre agentes (Claude Code, Kimi CLI, Gemini CLI)

Parte do protocolo **megabrain** — extensão do Gate 0 (assumir). Rode isto
antes de trabalhar se `.megabrain/memoria-global.md` for mais recente que a
última sincronização, ou se um agente novo estiver sendo configurado pela
primeira vez neste projeto. Isto não é sugestão — trate como garantia do
protocolo, igual ao resto do Gate 0.

## Por que isto existe

`.megabrain/memoria-global.md` é a **fonte única** de identidade e regras de
comportamento do Henrique (Iriq): nome, contexto, formato obrigatório de
diagnóstico técnico. Cada agente (Claude Code, Gemini CLI, Kimi CLI) lê
memória de um jeito diferente — arquivo diferente, mecanismo diferente. Sem
este gate a informação diverge entre eles silenciosamente. Já aconteceu uma
vez: duas cópias do mesmo texto em lugares diferentes, uma desatualizada em
relação à outra, sem ninguém perceber até comparar as duas.

**Regra dura: nunca edite a cópia sincronizada.** Edite sempre
`.megabrain/memoria-global.md` e rode a sincronização de novo. Editar a
cópia é o mesmo erro que reescrever `DECISOES.md` — perde a fonte de
verdade.

## O que você precisa fazer, dependendo de quem você é

Não copie o conteúdo cegamente para todo lugar. O mecanismo de import muda
por agente — identifique quem você é antes de agir (nome do binário,
variável de ambiente, ou pergunte ao Henrique se não tiver certeza) e siga
só a seção correspondente.

### Se você é Claude Code
Arquivo de memória: `CLAUDE.md` na raiz do repo.
Claude Code resolve imports com sintaxe `@caminho/arquivo.md` — isso lê o
arquivo de destino em tempo real, não duplica texto.
1. Abra (ou crie) `CLAUDE.md` na raiz do projeto.
2. Garanta que contenha a linha: `@.megabrain/memoria-global.md`
3. Se a linha já existir, não faça nada — já está sincronizado por
   definição (é referência, não cópia; sempre reflete a versão atual).

### Se você é Gemini CLI
Arquivo de memória: `GEMINI.md` na raiz do projeto (existe também
`~/.gemini/GEMINI.md` para regra global entre projetos — não use essa aqui,
esta regra é por projeto).
Gemini CLI também resolve `@arquivo.md` nativamente, mesma lógica do
Claude Code.
1. Abra (ou crie) `GEMINI.md` na raiz do projeto.
2. Garanta a linha: `@.megabrain/memoria-global.md`
3. Se já existir, não faça nada.

### Se você é Kimi CLI
Arquivo de memória: `AGENTS.md` na raiz do projeto.
**Import por `@arquivo.md` não está confirmado para Kimi CLI no momento em
que isto foi escrito** — trate como não suportado até verificar o
contrário. Nesse caso a sincronização precisa copiar o conteúdo de fato,
não apontar para ele.
1. Rode: `python .megabrain/mb-sync.py --target kimi`
2. O script escreve o conteúdo de `memoria-global.md` dentro de
   `AGENTS.md`, entre os marcadores `<!-- MEGABRAIN:AUTO-SYNC:START -->` e
   `<!-- MEGABRAIN:AUTO-SYNC:END -->` — idempotente, não duplica se rodar
   de novo.
3. Sem acesso para rodar script (ambiente restrito)? Copie o conteúdo
   manualmente entre esses mesmos marcadores, nunca em outro lugar do
   arquivo, e confira que os marcadores não existem duplicados.

## Depois de sincronizar

Confirme visualmente que o arquivo de destino reflete o conteúdo atual da
fonte — não assuma que o script/import funcionou. Isso é o próprio Gate 5
(verificar) do megabrain aplicado aqui.

## Quando rodar isto de novo

- Sempre que `.megabrain/memoria-global.md` mudar.
- Ao configurar um agente novo neste projeto pela primeira vez.
- Se o Henrique disser "sincroniza a memória" ou "roda o mb-sync".
- Se você notar qualquer divergência entre o que está sincronizado e a
  fonte — pare o que está fazendo e sincronize antes de continuar.
