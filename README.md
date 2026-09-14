# MEGABRAIN

MEGABRAIN é um protocolo local-first para organizar trabalho com mais de uma
IA sem perder o contexto, a decisão ou a prova do que foi feito. Ele separa
planejamento, execução, revisão e passagem de bastão em arquivos que podem ser
auditados no projeto.

## O que ele entrega

- Orquestração V6 para tarefas novas: Claude planeja e revisa; Codex/Sol
  produz; a decisão e a verificação continuam explícitas.
- Codex Spark para workers leves — checklist, sondagem, varredura e extração —
  somente quando a cota exclusiva dele está medida como saudável.
- Medição de cota antes, durante e depois de uma execução. A rota usa a leitura
  ao vivo; o histórico compacto só revela padrões de uso.
- Skills, scripts, locks por arquivo, estado, handoff e testes para reduzir
  retrabalho entre pessoas e agentes.

## Cotas IA na tela — instale com 1 clique (recomendado)

O MEGABRAIN vem com um **widget de cotas na tela** (`apps/ia-quota-widget`):
um quadradinho sempre visível que mostra quanto você já usou de cada IA
(Codex, Claude, Z.ai, Gemini…) em cada janela de limite — 5 horas, semana,
mês — com uma barrinha colorida por janela.

Por que usar: cota é o recurso que mais se perde por falta de visão. Com o
widget, você vê antes de abrir um chat se vale trocar de IA, se a semana
está no fim ou se a janela de 5 horas acabou de renovar. Ele lê as
credenciais que JÁ EXISTEM no seu computador (as mesmas que os CLIs Codex,
Claude e Gemini usam) — não pede senha, não guarda token, não manda nada
pra fora.

Instalação: entre em `apps/ia-quota-widget` e dê dois cliques em
**`INSTALAR-E-ABRIR.cmd`**. O script faz tudo sozinho: cria o ambiente
Python privado do widget, instala as dependências, cria o atalho na área de
trabalho, configura pra abrir junto com o Windows e já abre o widget. Rodar
de novo é seguro — só atualiza, nunca duplica. Se o Python não estiver
instalado, ele aponta o download. Pra não abrir junto com o Windows:
`Win+R` → `shell:startup` → apague o atalho "Cotas IA".

Como usar no dia a dia: cada IA é um card. **Segure e arraste o nome** de
uma IA até a coluna de bolinhas à esquerda para tirá-la da vista; arraste a
bolinha de volta para a lista, na altura entre dois cards, e ela volta
exatamente ali. Arraste um card por cima dos outros para reordenar. Duplo
clique no cabeçalho ajusta o tamanho ao conteúdo; `Ctrl+,` abre as
configurações (fonte, cores, frequência de consulta, avisos de limite).

## Começo rápido

1. Instale o widget de cotas: dois cliques em
   `apps/ia-quota-widget/INSTALAR-E-ABRIR.cmd` (ver seção acima).
2. Leia [SKILL.md](SKILL.md) para entender os gates e os limites de autonomia.
3. Rode `python bin/mb-inicio-sessao.py` para listar as skills disponíveis.
4. Para uma entrega multiagente, use `/orquestracao1` e crie um brief com
   objetivo, critérios verificáveis e contexto.
5. Antes de aplicar uma proposta, valide o artefato real. `review_approved`
   confirma revisão textual; não substitui teste, build ou inspeção visual.

## Privacidade e limites

O export público é gerado por `bin/mb-generate-template.py`. Ele exclui dados
locais, entregas pessoais, logs, memória de conteúdo, credenciais, builds e o
aplicativo Pets. Nunca publique a pasta central privada diretamente.

Este repositório não inclui licença de uso. A visibilidade pública não concede
permissão automática para copiar, redistribuir ou usar o conteúdo além do que a
lei permitir; para outro uso, fale com o titular.

## Estrutura

- `motor/skills/`: instruções canônicas para agentes.
- `apps/automations/`: motor local da orquestração.
- `apps/ia-quota-widget/`: widget de cotas na tela (instalação de 1 clique).
- `bin/`: scripts de verificação, sincronização e export.
- `docs/`: referências e documentação.

Consulte a primeira linha de `VERSAO.txt` para a versão atual.
