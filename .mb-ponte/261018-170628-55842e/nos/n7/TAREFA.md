# Nó n7 · Revisar campos, cursor e transporte de imagens

Papel: **revisor** · aberto por n0 (planejador, GPT) · profundidade 1.
Projeto: `<MEGABRAIN_ROOT>` · ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e` (pedido original em pedido.json).

## Tarefa
Você é revisor independente GLM/ZCode. Só leitura de fontes e testes; escrever apenas seu resultado.md e evidence/261018_ponte-orquestradores/revisao-interface-glm.md. Não implementar, não concluir ordem nem abrir outro nó, não executar modelos/jobs reais.

Revisão final de interface e transporte, produção GPT n3/n5 e integração n0. Fontes: apps/megabrain-dashboard/web/src/{AttachmentInput.tsx,attachments.ts,AnalysisForm.tsx,App.tsx,CursorTools.tsx,ReportFrame.tsx,report-notes.ts,report-attachment-guard.ts,Modal.tsx}; central_reports.py; cursor/decisões canônicos motor/modelos/interacoes e cópias públicas; model_clients.py e central_workflows.py apenas delta visual. Leia relatórios nos/n3/resultado.md e nos/n5/resultado.md quando existirem. N3 está terminando testes/espelhos, portanto pode começar revisão agora, mas NÃO aprove a versão final antes de resultado.md do n3 existir e revalidar hashes. N5 terminou22testes, n0 integrou image_paths e4testes de workflow; GLM5.3 é sótexto no adapter e dá erro antes da própria inferência, sem fallback silencioso. Transporte nativeCLI não é prova de percepção/provider.

Critérios: CtrlV de imagem e texto/arquivo nos campos coerentes, prévia/remoção/retry/limites, imagem sem texto, rascunho preservado em upload/enviofalho/fechamento, troca só de anexo gera novo envio, notas não duplicadas em decisões, seleção de imagem por resposta, proteção contra fechar editor com File pendente. Iframe opaco segue CSP connect-srcnone; postMessage valida janela/token/fid e limites, sem caminho arbitrário ou base64 em draft. Não criar comentário de teste no servidor real. Testes UI direcionados se úteis, usando fixtures próprias. Não rodar build global (n0 faz final).

Preservar correções da sessão Claude conforme complementos.jsonl: autosend só notas do cursor, flushNotes(manual), teto20/min autoTimes, noteKey(fid,n,hash), ready reenvia pendente dehashantigo, decisão não duplica notas; textos App0,4s/retornonovo eCursorToolsNotaenviada✓; cursor rotuloSalvar/enviaProjeto/salvarTexto.

Achado do coordenador para verificar sem aceitar no automático: cursor canônico atual define ehToque() sem parâmetro (~275, usa ultimoTipo/coarse) e ehToque(tipo) (~334) no mesmo closure. JS hoisting pode fazer a segunda substituir a primeira; rotuloSalvar e toast chamam sem argumento, então toque semprefalse. Prove ou refute, sugira patch mínimo sem quebrar lógica ponteiro. N0 corrige quando n3 liberar fonte.

Veredito APROVADO ou AJUSTAR com gravidade, arquivo:linha, cenário reproduzível e correção mínima. Registre arquivos/hashes lidos e limites reais; não transformar leitura ou mock em percepção de imagens ou uso físico. Revisão backend n6 cobre armazenamento/rotas, mapa tem outro revisor. Sem novo relatório humano, sem apprestart.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e/nos/n7/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.
