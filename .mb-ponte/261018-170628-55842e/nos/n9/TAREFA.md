# Nó n9 · Revisar recibos entre perfis e integração final

Papel: **revisor** · aberto por n0 (planejador, GPT) · profundidade 1.
Projeto: `<MEGABRAIN_ROOT>` · ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e` (pedido original em pedido.json).

## Tarefa
# Revisão independente do delta de recibos entre perfis

Você é GLM/ZCode, revisor de leitura. GPT/Codex 1 produziu este delta. Não edite produto, não publique, não execute modelos nem comentários na base real. Releia o estado final no disco; backup e provas históricas estão em evidence/261018_ponte-orquestradores/.

Problema confirmado na prova de dois perfis: segundo perfil restaura nota já recebida do rascunho servidor, mas não possui SentMap local. sendDecision reenviava a nota e o resumo textual junto da decisão. Prova do bug: integration-repeat-analysis.json e integration_repeat_profiles.py.

Revise este delta: central_note_receipts.py, central_server.py (GET note-receipts e whitelist resumo_texto_original), central_reports.py (resumo_respostas), web/src/ReportFrame.tsx, web/src/report-notes.ts, motor/modelos/interacoes/261010_decisoes-respondiveis/decisoes-respondiveis.js e seus novos testes. Compare com backups before-note-receipts e before-original-summary e os backups do agente em evidence. O nome exato da fonte decisões pode ser conferido pelo rg.

Confira também a integração final n0 em central_workflows.py (image_paths do workspace isolado passados a run_model; revisão só ganha contexto completo depois de recibo de transporte dos hashes, nunca percepção visual). Novos 4 testes em tests/test_central_attachment_transport.py; model_clients.py já teve revisão n7. Nenhuma chamada real de IA necessária.

Critérios: autenticação e isolamento por projeto/relatório/hash; recibos de notas resolvidas continuam válidos; nota só imagem preservada; edição de texto/imagem gera novo envio; versão diferente não bloqueia; erro na busca mantém decisão pendente; decisão não repete nota nem no resumo operacional; resumo original preservado como evidência, sem virar instrução duplicada na ponte; guards de concorrência preservados; 20/min e remoção explícita continuam presentes. A leitura/endpoint não altera histórico original. Revisor pode rodar testes sintéticos dirigidos (unittest e testes JS, sem rebuild/restart) e registrar comandos reais. Não afirme percepção de print nem hardware físico.

Grave parecer em evidence/261018_ponte-orquestradores/revisao-delta-recibos-glm.md e resultado em seu nos/n*/resultado.md, com APROVADO/AJUSTAR, achados falsificáveis, testes e hashes. Aguarde se FINAL-RECIBOS.json ainda não existir; depois confirme hashes desse marcador antes e após revisar. Não esperar indefinidamente: se ausência persistir, relate bloqueio.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e/nos/n9/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.
