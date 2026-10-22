# Nó n2 · Receber e vincular prints no servidor

Papel: **worker** · aberto por n0 (planejador, GPT) · profundidade 1.
Projeto: `<MEGABRAIN_ROOT>` · ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e` (pedido original em pedido.json).

## Tarefa
Você é worker GPT/Codex 1 desta ordem. Objetivo: implementar transporte e persistência de prints, exclusivamente no backend. Fontes: plano.json e nos/n0/TAREFA.md desta ordem. Coordenação n0 já leu estado/trava/startup; não repetir startup nem concluir a ordem. Antes de editar, confira mtimes/travas, faça backup dos seus arquivos em evidence/261018_ponte-orquestradores/backend/backup, registre hashes. Se arquivo mudar externamente durante o trabalho, releia e preserve a mudança.

Arquivos exclusivos: apps/megabrain-dashboard/central_server.py, novo central_attachments.py, tests/test_central_attachments.py, testes backend existentes estritamente afetados. Pode modificar central_store.py SOMENTE se indispensável a Novo pedido/persistência e registre. Não tocar central_reports.py, central_bridge.py, frontend, cursor, mapa, estado global ou dist; outros workers cuidam deles. N0 cuida de scripts/isolated_server.py e integração final.

Contrato congelado com o worker de interface:
- POST /api/projects/{pid}/attachments; JSON {name,mime,data}; data = base64 sem prefixo. Resposta {attachment:{id,path,name,mime,size,url}}. GET /api/projects/{pid}/attachments/{id}, autenticado.
- Tipos PNG/JPEG/GIF/WebP (sem SVG/HTML), até 8 MiB por arquivo, até 6 anexos por envio. Validar bytes reais (não confiar MIME/nome), tamanho, diretório confinado e projeto permitido; storage .mb-anexos na raiz real do projeto. Não usar caminho recebido para ler arquivo arbitrário. Permitir body maior APENAS na rota upload e manter teto para demais rotas. Auth/CSRF/origem iguais às rotas atuais; erro visível sem detalhe sensível. Nenhuma dependência nova por necessidade aparente.
- Comments, report feedback e Novo pedido/decisões: aceitar anexos: [attachment], resolver sempre referências do próprio projeto. Comentários finais e ponte guardam `anexos` como caminhos canônicos STRING para compatibilidade com central_bridge._texto_comentarios. Manter metadados adicionais se útil em attachment_details. Aceitar comentário só com imagem sem inventar texto humano. Feedback `notas` pode conter anexos por nota e decisões por resposta; agregar caminhos únicos sem perder associação. Rejeitar anexos de outro projeto, forjados ou fora de .mb-anexos.
- Preservar idempotência e vínculo source_hash/versão anterior; nenhum retorno RECEBIDO vira CORRIGIDO_VERIFICADO. Não disparar IAs em testes (Ponte lancar=False, MB_ISOLATED/MB_PONTE=0); não criar comentários de teste no banco real.

Novo pedido exige `central_workflows.py`/`central_execution.py` para acesso real no executor. Esses dois arquivos também ficam exclusivos seus se necessários, incluindo testes. Nomes selecionados em selected_paths continuam protegidos: anexos externos têm fluxo próprio, não ampliar código por implicação.

Gate: antes de editar fontes, confira nos/n1/resultado.md (revisão GLM do plano). Se ainda não existe, faça leitura/revisão/backups e espere em intervalos curtos; não produza antes do parecer. Se houver AJUSTAR material, aplique os achados pertinentes preservando contrato publicado. Grave registro do parecer usado.

Pronto: rota autenticada persiste e lê imagem, testes cobrem permissão/CSRF/limites/tipo/caminhos/projeto/idempotência/feedback e pedido sem texto com imagem. Rode testes direcionados no Python com runtime-packages. Não reinicie o app nem rode build global. Registre comandos, arquivos e contrato efetivo em resultado.md do seu nó e evidence/.../backend/resultado.json; confirme ausência de conflito. Se encontrar contrato impraticável, comunique por arquivo evidence/.../backend/CONTRATO.md antes de mudar.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e/nos/n2/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.
