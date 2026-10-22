# Nó n4 · Revisar e corrigir o mapa por GPT

Papel: **worker** · aberto por n0 (planejador, GPT) · profundidade 1.
Projeto: `<MEGABRAIN_ROOT>` · ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e` (pedido original em pedido.json).

## Tarefa
Você é worker GPT/Codex 1, outro fornecedor em relação ao mapa produzido pelo Claude. Objetivo: revisar e aperfeiçoar o mapa do harness conforme comentário humano #mh-mapa. Fontes: nos/n0/TAREFA.md/plano.json desta ordem, crítica e prints evidence/261017_cursor-harness/mapa/critica-r2/, progresso critica-r2.md e mapa-ajuste-r2.md. A crítica final foi StructuredOutput no Claude, não há .md completo conhecido; use imagens/medições e busque somente o scratch da sessão indicada se necessário. Leia skills pertinentes de auditoria visual e instruções locais. N0 já rodou startup, leu estado/trava e encaminhou plano para revisão GLM.

Arquivos EXCLUSIVOS: bin/mb-harness-mapa.py, dados/harness-mapa.json, motor/modelos/harness-mapa/*, motor/tests/test_mb_harness_mapa.py, HTML gerado 00_PARA-VOCE/261011_harnesses/261017_MAPA-DO-HARNESS.html. NÃO editar cursor-ferramentas, decisões, frontend, backend, estado global. HTML exclusivamente pelo gerador; backup em evidence/261018_ponte-orquestradores/mapa-revisao-gpt/backup antes. Não publicar/commit/git.

Condição dura de concorrência: só edite se NENHUM arquivo do mapa foi alterado nos últimos 20 minutos; confira de novo imediatamente antes de gravar. Outra sessão Claude abriu mapa-ajuste-r2 às16:51 trabalhando em scratch. Primeiro faça revisão independente com prints próprios em evidence/261018_ponte-orquestradores/mapa-revisao-gpt/. Ao detectar alteração concorrente, registre e revise versão nova, sem sobrescrever. Valem alterações sobre o arquivo mais recente, nunca cópia antiga. Nenhuma pausa infinita: trabalho independente de revisão segue, e informe bloqueio real se necessário.

Critérios: preservar conceito cidade/metrô e dados/editabilidade; melhorar leitura/hierarquia/contraste/ritmo e erro concreto observado, sem inventar nova estética. Meça 1440/390 claro/escuro, animação/paradas/seguir, detalhe/editor, início e fim. Crítica existente mede 34 controles antes do mapa, dots14x24, narração ~2s para19-26 palavras e balão ~0,96s; verificar comportamento atual. Cada correção precisa antes→depois verificável. Referências e modelo de mapa são conteúdo existente: não precisa pesquisa de tendências nem imagem gerada. Não declarar compreensão/aprovação humana.

Gate: antes de editar fontes, confira nos/n1/resultado.md (revisão GLM do plano). Se ainda não existe, faça revisão somente leitura/prints/backups e espere em intervalos curtos. Em AJUSTAR material, corrija os achados pertinentes. Antes de gerar HTML confira o cursor/decisões canônicos atuais, pois o worker interface os atualiza; gerar no fim para integrar os controles novos. Não copiar arquivos do outro worker.

Pronto: achados GPT com prints, correções de problemas reais no gerador/CSS/JS/dados, teste de motor apropriado, HTML regenerado, prints desktop/mobile inspecionados com controle sem overflow e funções principais verificadas. Opcional atualizar topo da própria entrada com resultado recente conciso, sem painel novo. Não reiniciar app; n0 integra e apresenta no app real. Não alterar relatório do app. Registre resultado.md do nó e evidence/.../mapa-revisao-gpt/resultado.json com arquivos, hashes, verificações, limitação e reversão. Revisor final GLM pelo n0; você não aprova seu próprio trabalho.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e/nos/n4/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.
