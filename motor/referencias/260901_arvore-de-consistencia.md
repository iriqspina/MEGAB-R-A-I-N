# Árvore de consistência — quando uma convenção muda, tudo que a repete muda junto (v1, 260901)

Origem: <USUARIO>, 260901, Estagi_a_rio — "sempre renomeie tudo equivalente… se eu mudar o
jeito que nomeio, organizo ou faço processos de trabalho ou criativos, precisa ajudar em
certos lugares certas coisas, como uma árvore de alterações que vai se mudando mas precisa
manter consistente tudo". Mesma família das lições 260807 (pasta-âncora renomeada apodrece
caminho em todas as superfícies) e 260830 (reorg = varrer docs por caminho antigo E conferir
sobras). Aqui vira método com arquivo por projeto.

## O que é

Cada projeto sob megabrain mantém `ARVORE-DE-CONSISTENCIA.md` na raiz, com um bloco por
**convenção** (nome de arquivo, versão, nome de board/frame/camada, estrutura de pasta,
processo, regra criativa medida). Cada bloco tem:

- **DONO** — a fonte da regra (o padrão dele, um LEIAME, a skill, o acervo). Só um.
- **DEPENDENTES** — todo lugar que repete a regra: nomes no Figma, nomes de export, pastas,
  LEIAMEs, HANDOFF, skill de projeto, wiki, memória do agente, scripts que acham coisa por
  nome.
- **Regra de propagação** — o que acontece quando o dono muda (ex.: "versão nova = pasta
  nova + rename de página/seção/frames/nota + linha no LEIAME").
- **Registro de propagações** no fim do arquivo: data, o que mudou, onde foi aplicado.

## Como usar (Gate 3 · gerar e Gate 6 · bastão)

1. Antes de criar nome, pasta ou board novo: procurar o bloco do dono. Se não existe, criar o
   bloco — o nome nasce já com a lista de dependentes.
2. O <USUARIO> muda uma regra (novo padrão de nome, nova organização, novo processo, nova
   correção de gosto): abrir o bloco, `grep` pelo valor velho em todos os dependentes,
   aplicar em todos na mesma sessão, `grep` de novo (zero fora de nota histórica), checar
   prefixo duplicado (`04_04`), registrar a propagação.
3. Renomear no Figma = `use_figma` com rename por padrão (`name.replace(/· v3$/, '· v4')`),
   nunca à mão um por um; conferir com dump read-only depois.
4. Nunca renomear o que é dele (pasta do cliente, .ai, export original). Dependente que
   mora lá é só citação: atualiza-se a citação.
5. HANDOFF recebe uma linha "propagação: <regra> → <N lugares>". Se sobrou lugar sem
   atualizar (sem acesso, arquivo aberto no app dele), dizer qual.

## Sinais de que um dependente ficou pra trás
- Nome de board/frame com versão diferente da pasta de export mais nova.
- LEIAME "Atual:" apontando pra pasta que não é a última.
- Script/skill achando camada por nome que não existe mais (retorno vazio).
- Caminho antigo em skill instalada, memória do agente ou nota dentro do Figma.

## Primeiro exemplar
`<PROJETOS_ROOT>\Estagi_a_rio\ARVORE-DE-CONSISTENCIA.md` — 8 convenções (nome de
export, versão, frames, camadas, pastas do job, pasta do cliente, processo, regras criativas),
primeira propagação registrada: v3 → v4 em 260901.
