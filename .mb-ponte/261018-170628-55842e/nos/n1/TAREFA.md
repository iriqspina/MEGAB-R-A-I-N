# Nó n1 · Revisar plano de prints e mapa

Papel: **revisor** · aberto por n0 (planejador, GPT) · profundidade 1.
Projeto: `<MEGABRAIN_ROOT>` · ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e` (pedido original em pedido.json).

## Tarefa
Contexto: ordem 261018-170628-55842e, planejador n0 GPT Codex 1. Leia plano.json e nos/n0/TAREFA.md desta ordem. A startup, estado/trava e cotas foram conferidos pelo n0 (18/10 17:07); GLM/ZCode ativo, snapshot fresco. Você é revisor independente GLM; não implemente nem abra outros nós nem conclua a ordem.

Pedido: revise o plano antes da produção por escopo, premissa, risco e verificação. Confira o contrato proposto com central_server.py, central_reports.py, web/src/ReportFrame.tsx, web/src/api.ts e cursor-ferramentas.js canônico. Proponha somente correções materiais; identifique contrato incompatível se houver. Critérios: isolamento entre projetos, limites/autenticação, preservação de rascunhos, vincular anexos e ponte, revisão do mapa por GPT e testes reais. Registre APROVADO ou AJUSTAR com achados curtos no resultado.md do seu nó. Pode também escrever evidence/261018_ponte-orquestradores/revisao-plano-glm.md, sem tocar fontes. Não fazer chamadas de rede externas ou perguntas ao usuário.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e/nos/n1/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.
