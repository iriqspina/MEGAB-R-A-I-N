# Resultado n9 · Revisar recibos entre perfis e integração final

**Veredito: APROVADO** · revisor GLM/ZCode · 2026-10-18 ~18:05 (Brasília)
Parecer completo: `<MEGABRAIN_ROOT>/evidence/261018_ponte-orquestradores/revisao-delta-recibos-glm.md`

## O que foi revisado (leitura, sem editar produto)

1. **Delta de recibos** (GPT/Codex 1): `central_note_receipts.py` (novo), `central_server.py` (GET `/api/reports/{fid}/note-receipts?hash=` reusando `report_opened_version` + whitelist `resumo_texto_original`), `central_reports.py` (bootstrap com `resumo_respostas`), `web/src/report-notes.ts` (`readNoteReceipts`, `unreceivedDecisionNotes`, `decisionFeedback`), `web/src/ReportFrame.tsx` (`receivedNotes`, consultas em `flushNotes`/`sendDecision`), `motor/modelos/interacoes/261010_decisoes-respondiveis/decisoes-respondiveis.js` (`textoRespostas` = base sem notas). Diffs conferidos contra `backup-n0/central_server.before-note-receipts.py` e `before-original-summary.py`: delta cumulativo, sem mudança fora do descrito.
2. **Integração final n0**: `central_workflows.py` passa `image_paths` do workspace isolado (`.mb-anexos` do job) ao `run_model`; cobertura da revisão só fica `complete` após recibo de transporte com SHA-256 dos staging e bytes preservados; `visual_inspection_observed=False` sempre (recibo de transporte nunca vira percepção). `model_clients.py` não re-revisado (escopo n7).

## Critérios — todos OK

Autenticação/isolamento (projeto/relatório/hash) · recibos de resolvidas válidos · nota só imagem preservada · edição gera novo envio · versão diferente não bloqueia · erro na busca mantém decisão pendente · decisão não repete nota nem no resumo operacional · resumo original preservado como evidência sem duplicar instrução na ponte (`resumo_respostas` descartado no frontend E na whitelist — dupla barreira) · guards de concorrência (assinatura da decisão, flushing/decisionSending, mutationKey+dedupe) · 20/min e remoção explícita · leitura não altera histórico.

## Como verificou (comandos reais, sem rebuild/restart)

1. `python -X utf8 -m unittest discover -s tests -p "test_central_note_receipts.py" -v` → 4/4 OK.
2. `python -X utf8 -m unittest tests.test_central_reports tests.test_central_attachment_transport -v` → 24 OK, 1 skipped (probe Chromium nativo, pré-existente); os 4 testes de transporte passam.
3. `node --test scripts/test-report-notes.cjs` → 13/13 OK (inclui os novos casos de recibo/resumo).
4. Teste dirigido do revisor: `evidence/261018_ponte-orquestradores/revisao-n9/teste-dirigido-n9.py` → 17/17 OK (leitura não altera `comments`; recibo serve perfil sem SentMap e decisão não repete nota; isolamento entre projeto/alvo/hash).
5. Prova de dois perfis pós-fix (`integration-repeat-profiles.json`) conferida por leitura: `all_pass=true, repeated=false, sources_unchanged=true`.

## FINAL-RECIBOS.json (hashes antes → depois)

`4a6a0b2ff541de3912c116d7bc959793f8c65459e8e229f3eb909138ed1c01bb` → **idêntico** após a revisão; os 7 hashes de fontes do marcador conferem byte a byte com o disco (`central_note_receipts 8a3d4edc…`, `central_server b2b5a564…`, `central_reports 14c09c1e…`, `central_workflows b832f8b8…`, `ReportFrame.tsx 2cc99109…`, `report-notes.ts b6e26b8f…`, `decisoes-respondiveis.js 51fee84c…`). Produto congelado durante toda a revisão.

## Achados menores (não bloqueiam)

O1 varredura sem índice em `comments` (custo só com volume grande, [ESTIMATIVA]); O2 import de topo exige `discover -s tests`; O3 nota com versão nunca servida devolve 409 e mantém pendência (mitigado por `remember_report_version`); O4 `web/dist` atual já contém a lógica de recibos (leitura; sem rebuild meu).

## Pendências

1. Reinício real do app + health + receipt no app real (checklist do n0) — fora do escopo do revisor.
2. Prova Qt de dois perfis é registro do produtor; reexecutar só se o n0 julgar necessário.
3. Nenhuma correção de produto solicitada por esta revisão. Nada foi commitado, publicado ou reiniciado.
