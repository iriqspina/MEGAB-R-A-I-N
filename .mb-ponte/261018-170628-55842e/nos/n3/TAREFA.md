# Nó n3 · Colar e escolher prints nos campos

Papel: **worker** · aberto por n0 (planejador, GPT) · profundidade 1.
Projeto: `<MEGABRAIN_ROOT>` · ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e` (pedido original em pedido.json).

## Tarefa
Você é worker GPT/Codex 1 desta ordem. Objetivo: colar prints com Ctrl+V e escolher arquivo em todos os campos textuais coerentes do MegaBrain, preservando rascunhos e associação ao pedido. Fontes plano.json e nos/n0/TAREFA.md. N0 já leu estado/startup/trava. Não concluir a ordem. Faça backup dos arquivos antes de alterar em evidence/261018_ponte-orquestradores/interface/backup (fora da pasta humana), com hashes. Confira mtimes/travas para não sobrescrever trabalho recente.

Arquivos EXCLUSIVOS: apps/megabrain-dashboard/web/src/*, web/public/* de cursor/decisões, scripts de teste JS novos; apps/megabrain-dashboard/central_reports.py (bootstrap JS transporte), motor/modelos/interacoes/261010_cursor-ferramentas/* e decisões respondíveis pertinentes. Não tocar central_server.py, central_store.py, central_bridge.py, mapa, estado global, package.json, dist (build final é do n0). Cursor foi corrigido ontem e outra sessão estava nele: antes de alterar compare hashes e preserve correções. Só trabalhar se não há modificação concorrente: em conflito, reportar por arquivo e continuar outra frente.

Contrato backend congelado: POST /api/projects/{pid}/attachments JSON {name,mime,data}, data base64 sem prefixo; resposta {attachment:{id,path,name,mime,size,url}}. GET url autenticada. Até 8 MiB por PNG/JPEG/GIF/WebP, até 6 por envio; sem SVG. Payload dos comentários/feedback/pedido usa `anexos: [attachment]`. Backend resolve para caminhos strings canônicos para ponte. Não converter imagem inteira em comentário/SQLite/localStorage: guardar referência após upload, com prévia via url ou blob curto enquanto envia.

Cobertura obrigatória: textarea "Peça uma alteração neste relatório" (ReportFrame), comentário de módulo (App), Novo pedido (GoalWizard), decisões textuais no app; notas do cursor no app (CursorTools) e nos HTML canônicos, decisões respondíveis com texto. Busca/senha/nome ficam fora. Reusar componente AttachmentInput e helper se fizer sentido. Mostrar botão escolher print, prévias removíveis, estado enviando e erro; preservar texto normal/Ctrl+V texto, não impedir envio acidental perdendo rascunho em falha/limite. Não enviar enquanto upload pendente. Sem texto mas com imagem deve funcionar. Remover anexo não precisa apagar físico.

Riscos já encontrados: report-notes.ts SentMap/markSent/unsentNotes e CursorTools recibos comparam somente texto; fingerprint precisa considerar anexos, senão alteração só de imagem fica perdida. Cursor canônico `vazia` apaga nota só com imagem, e `notas()`/central_reports.BOOTSTRAP.notes filtram anexos; corrigir. PostMessage precisa validar token/origem/fid e ACK com anexos sem serializar objetos File indevidos. Não alterar envio original/âncora/recibo/source_hash; fora do app, erro claro caso upload indisponível e rascunho preservado. Copies canônicas/public devem bater; não atualizar HTML gerado à mão.

Novo pedido atual fica em AnalysisForm.tsx (não confundir só GoalWizard). Cursor do relatório tem CSP connect-src none: NÃO relaxar esse isolamento; canal dedicado com postMessage/File ou buffers limitados e validação token/fid/janela. BOOTSTRAP/wrapper têm teto160k em mensagens antigas, não inflar limite indiscriminadamente. Preview de referência no relatório pode receber data URL limitada do pai, sem gravar base64 no rascunho.

Gate: antes de editar fontes, confira nos/n1/resultado.md (revisão GLM do plano). Se ainda não existe, faça inventário/leitura/backups e espere em intervalos curtos; não produza antes do parecer. Se houver AJUSTAR material, resolva achados pertinentes sem mudar contrato compartilhado. Grave registro do parecer usado.

Pronto: todos os campos coerentes inventariados com implementado/exclusão motivada; testes comportamentais de colar/arquivo/prévia/remoção/falha/rascunho/imagem sem texto e transporte; npm run check passa. Não rodar build global nem reiniciar app. Use browser/Qt isolado para provas, sem comentários de teste em produção. Registre resultado.md no nó com arquivos e comandos, e evidence/.../interface/resultado.json. Se o escopo de decisões exigir outra pasta canônica, pode incluí-la, registrando-a antes de editar. Nenhum HTML humano concorrente.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e/nos/n3/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.
