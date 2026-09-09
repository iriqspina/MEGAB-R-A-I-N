---
name: orquestracao5
description: Motor local MEGABRAIN de loops e swarm entre Claude Code, Codex Sol e Spark, com estado do projeto, fontes delimitadas, revisão, reparo e entrega organizada. Use /orquestracao5 ou pedido de interação automatizada entre Claude e Codex. Não é agendamento.
---

# Orquestração 5 — execução local com evidência

## Encaixe no MEGABRAIN

O MEGABRAIN governa objetivo, fontes, autorização, qualidade e fechamento. Este modo executa a troca entre agentes. Complementa /orquestracao4 (papéis e uso medido); não substitui /orquestracao1, não promete o plano tipado de /orquestracao3 nem os ciclos longos de /quaseultracode.

Localize a central por MEGABRAIN_CENTRAL ou pela instalação MEGABRAIN com bin/mb-orquestracao.py. A fonte do motor é apps/automations/automations.py; não copiar um segundo motor para o projeto. Se o driver não estiver disponível, informe a ausência sem inventar um fallback.

## Contrato de entrada

1. Leia estado, handoff, decisões, lições e trava do projeto real. Na central ficam em memoria/estado/ e memoria/nucleo/; projetos comuns usam a raiz. Confirme escopo pelo pedido, sem reconfirmar o que já foi autorizado.
2. Escreva no projeto um brief JSON com objective, criteria (lista verificável), context e, opcionalmente, initial_candidate e assertions [{"contains":"texto"}]. Fontes adicionais precisam ser arquivos explícitos dentro do projeto; não carregar o cérebro inteiro. O orquestrador faz a pesquisa relevante antes, usando o índice do cérebro.
3. O driver captura estado, recortes de decisões/lições e fontes com caminho/hash, marca ausências e congela o pacote. Use prepare para inspecionar esse pacote sem gastar chamadas.

```text
python <CENTRAL>/bin/mb-orquestracao.py prepare --projeto <PROJETO> --brief <BRIEF_ABSOLUTO> --source cerebro/wiki/fonte.md
python <CENTRAL>/bin/mb-orquestracao.py run --projeto <PROJETO> --brief <BRIEF_ABSOLUTO> --mode loop
```

## Papéis adaptados ao <USUARIO>

- Loop: Claude Fable low planeja; Sol high produz/corrige; Fable medium revisa. Até duas revisões na configuração padrão.
- Swarm: Spark low extrai requisitos enquanto Fable low analisa riscos; depois planejamento, produção e revisão. Só usar quando as frentes acrescentarem evidência.
- Spark recebe tarefas delimitadas e sua cota é separada. Não aprova entrega nem substitui Sol por causa de saldo livre. Modelo/effort ficam no config do motor; ausência ou limite não autoriza troca silenciosa.
- Clientes usam assinaturas existentes. Nenhuma API key, crédito extra ou bypass como fallback. Cota indisponível é NAO_MEDIDO. Cada etapa registra contexto, uso retornado, configuração e resultado.
- Workers recebem texto e devolvem proposta estruturada; não aplicam patches nem executam código. Só o orquestrador fala com <USUARIO>.

## Saída, validação e organização

Estado/evidência por execução: <PROJETO>/.automations/runs/ID/. Documento para <USUARIO>: <PROJETO>/00_PARA-VOCE/orquestracao5-ID/. O driver coloca resultado e candidato nessa pasta automaticamente, inclusive aviso de falha; nenhum documento humano solto na raiz.

review_approved é revisão textual aprovada; code_executed=false permanece explícito. O orquestrador verifica fatos, roda testes/build ou abre o artefato conforme o trabalho, aplica somente o escopo autorizado e fecha ESTADO/HANDOFF/DECISOES com trava. Não marque a tarefa concluída só porque dois modelos concordaram.

Retomada usa manifesto e fontes congelados; não relê conteúdo novo em silêncio. Etapa falha ou abandonada não repete automaticamente. Status/resume/stop recebem --projeto e --id. stop impede novos despachos; a chamada atual termina por retorno ou prazo. Ordem direta de parar ao orquestrador interrompe imediatamente conforme o contrato do usuário.

Documentos concluídos que ainda são referência vão para _arquivo/<período>/; pontuais antigos sem uso podem ser apagados sob a autorização do usuário, após conferir referências. Nunca apagar backup de produção, trabalho corrente ou conteúdo de outro agente por conveniência. Commit/push dependem do pedido explícito e seguem o export privado/público da central.

## Verificação

```text
python <CENTRAL>/bin/mb-orquestracao.py doctor --projeto <PROJETO>
python <CENTRAL>/bin/mb-orquestracao.py probe --projeto <PROJETO>
python -m unittest discover -s <CENTRAL>/apps/automations/tests -v
```

O teste de comunicação confirma transporte, não qualidade universal. Guarde a lição no projeto e cite a pasta completa de entrega. Fonte desta skill: motor/skills/orquestracao5/SKILL.md; os geradores Claude/Codex e a instalação direta são consumidores.
