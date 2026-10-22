# Nó n5 · Levar prints aos clientes de IA

Papel: **worker** · aberto por n0 (planejador, GPT) · profundidade 1.
Projeto: `<MEGABRAIN_ROOT>` · ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e` (pedido original em pedido.json).

## Tarefa
Você é worker GPT/Codex1 nesta ordem. Contexto: plano.json, nos/n0/TAREFA.md. N2 implementa backend/anexos e preparação em central_execution.py/central_workflows.py; n3 interface. Achado de integração n0 em17:20: central_workflows.attachment_context_payload admite somente metadados para etapas textual/research e faz coverage.complete=False para qualquer imagem. Isso impede tratar corretamente um Novo pedido com print e deixa a revisão sempre incompleta. Implementação de imagens precisa chegar ao cliente de modelo, sem afirmar que o modelo viu pixels só porque um arquivo existe.

Seu escopo EXCLUSIVO agora: apps/megabrain-dashboard/model_clients.py, testes associados do adapter (test_model_clients.py ou teste novo apropriado), evidence/261018_ponte-orquestradores/transporte-imagens/*. Não tocar central_workflows.py, central_execution.py, central_server.py nem frontend/cursor/mapa; n0 liga a sua API ao workflow depois que n2 acabar. Não abrir outros nós, não reiniciar app, não rodar modelo nem rede de inferência como teste; toda prova com subprocessos simulados/CLI --help. Não alterar conta/globalconfig/providers/assinatura nem APIpaga. Antes de editar confira mtimes/travas, backup+hash em seu evidence. Preserve segurança e isolamento de capacidades atuais.

Objetivo: estender run_model com parâmetro keyword opcional `image_paths` (lista de paths absolutos de imagens previamente preparadas no workspace do próprio job), enviando pixels por mecanismo nativo dos clientes de assinatura quando a capacidade documentada existir, mantendo ferramentas desabilitadas onde já estavam. Codex CLI suporta --image no exec (verifique help local); ZCode `--attach` (verifique o executável realmente usado pelo adapter, não outra versão); Claude Code input stream-json user message multimodal (verifique ajuda/docs primárias oficiais se necessário). Evitar qualquer segredo em logs; metadados registram ids/mime/size/hash/transporte e ausência de prova de percepção, nunca base64.

Contrato desejado para n0: `run_model(..., image_paths=[str(path),...])`; retornar metadata `image_inputs`/`image_transport` com `transported` ou equivalente por arquivo e `visual_inspection_observed=False` (sem inferir entendimento). Valide até6 arquivos/8MiB cada e total48MiB, tipos PNG/JPEG/GIF/WebP, paths canônicos sem links/hardlinks e confinados a `<job_directory>/workspace/.mb-anexos` correspondente ao logdir de etapa. Nunca receber arbitrarypath diretamente do navegador nem ampliar selected_paths/capacidades. Validações de bytes podem reutilizar central_attachments apenas de forma sem ciclo. Se uma CLI real não suportar inputvisual nessa configuração, retorne falha explícita antes da chamada e registre limitação; não mandar só metadata como sucesso nem trocar modelo silenciosamente.

Prove com testes significativos por cliente: argumentos/mensagem reais construídos, stdin de imagem chega ao mockprocess, limites e pathsnegativos, nenhumahabilitação de tools/conta/escalation, logs sem base64, tarefa semimagens mantémcomportamento existente. Não instalar nem executar inferência paga/assinatura como smoke. Registre resultado.md do nó e evidence/.../transporte-imagens/resultado.json: APIfinal, arquivos, testes, fatos e limites. N0 integra e GLM revisa o conjunto final.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e/nos/n5/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.
