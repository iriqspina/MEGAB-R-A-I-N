# Nó n6 · Revisar armazenamento e segurança dos prints

Papel: **revisor** · aberto por n0 (planejador, GPT) · profundidade 1.
Projeto: `<MEGABRAIN_ROOT>` · ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e` (pedido original em pedido.json).

## Tarefa
Você é revisor independente GLM/ZCode. Somente leitura de fontes e testes; pode escrever apenas seu resultado.md e evidence/261018_ponte-orquestradores/revisao-backend-glm.md. Não implementar, não concluir a ordem, não abrir nós nem iniciar modelos/jobs reais.

Escopo CONGELADO n2 concluído: central_attachments.py, central_server.py (rotas/middleware de anexos e campos comments/feedback/jobs), central_execution.py (staging/inventário de anexos), testes/test_central_attachments.py e test_central_attachment_execution.py. Diretório base apps/megabrain-dashboard. Leia nos/n2/resultado.md e evidence/.../backend/resultado.json/testes-direcionados.json para autoria/backup/hash/prova. Não aprovar central_workflows.py nem model_clients.py nesta revisão: n0/n5 ainda integram transporte nativo de pixels nesses arquivos.

Pedido: procure defeito concreto de limite/tipo/auth/CSRF/origem, referência entre projetos, links/hardlinks/TOCTOU quando material ao caso, corrupção, idempotência, feedback de nota/resposta sem texto, ponte recebendo strings, preparação dos bytes, artefatos sem vazar anexo e mutação de entrada detectada. Verifique testes independentes direcionados se útil, sem editar source e usando fixture. A revisão deve apontar arquivo/linha/cenário reproduzível, gravidade e correção mínima; não inventar achados sem evidência. Declare APROVADO ou AJUSTAR e quais arquivos/hashes foram lidos. Compare fontes com os backups do n2 se necessário.

Contexto: n1 revisou plano AJUSTAR e n0 incorporou A1-A4 antes da produção; contrato plano.json. Até6 imagens PNG/JPEG/GIF/WebP,8MiB cada; arquivos no projeto .mb-anexos, metadataAPI e pathsstrings na persistência/ponte. Upload deve seguir BLOQUEADO no scripts/isolated_server padrão pois escreve raízes reais; n0 atualizou o teste test_isolated_server.py para classificar nova rota bloqueada, sem liberar guard. Prova real usa servidor próprio em evidence/.../integration_server.py com raízesfixture. Cotas GLM lidas antes do despacho; startupn0 jáexecutado. Não precisa HTML humano ou abrir app para este parecer técnico.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e/nos/n6/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.
