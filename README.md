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

## Começo rápido

1. Leia [SKILL.md](SKILL.md) para entender os gates e os limites de autonomia.
2. Rode `python bin/mb-inicio-sessao.py` para listar as skills disponíveis.
3. Para uma entrega multiagente, use `/orquestracao1` e crie um brief com
   objetivo, critérios verificáveis e contexto.
4. Antes de aplicar uma proposta, valide o artefato real. `review_approved`
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
- `bin/`: scripts de verificação, sincronização e export.
- `docs/`: referências e documentação.

Consulte a primeira linha de `VERSAO.txt` para a versão atual.
