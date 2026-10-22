# Resultado do nó n3 — prints nos campos coerentes

TL;DR — Interface implementada e verificada em isolamento: **55 testes JavaScript passaram, 38 verificações do cursor/decisões no Chromium passaram, 11 verificações do componente no Qt passaram e `npm run check` passou**. As fontes estão liberadas para integração. **Não concluí a ordem, não rodei build global e não reiniciei o aplicativo.**

1. **Gate e concorrência preservados.** Li o parecer GLM n1 (`AJUSTAR`, SHA-256 `2315122174f66d3b498789c257d00f719f92b05cd29db836b6bfe6f6597ec3e7`) antes das fontes; o plano n0 incorporou A1–A4 às 17:15. Backups com hashes em `evidence/261018_ponte-orquestradores/interface/backup/`. Detectei mudanças concorrentes de hoje em App, ReportFrame, CursorTools e report-notes; preservei as versões novas e A1–A6, refiz os preflights e não sobrescrevi os textos/correções recentes. Fontes finais ficaram estáveis durante os testes.

2. **Campos implementados.** ReportFrame (“Peça uma alteração neste relatório”), comentário/decisão textual de módulo no App, Novo pedido real em AnalysisForm, notas do CursorTools, cursor canônico e decisões textuais/complementos explicativos. Decisões legadas recebem adaptador pelo BOOTSTRAP, sem atualizar HTML gerado à mão. GoalWizard não existe em src. Busca/senha/nome/título/URL/filtro ficam fora; RoutingEditor configura esteiras e simula classificação textual, não é a entrada do pedido persistido. Inventário campo a campo e motivos em `interface/resultado.json` → `coverage`.

3. **Comportamento e preservação.** Ctrl+V de imagem, seletor de arquivo, prévias removíveis, progresso, erro, retry e envio só com imagem. Texto e colagem textual/mista são preservados. Referências curtas ficam nos rascunhos; File, buffers e prévias em base64 ficam transitórios. Limites de 8 MiB e 6 por envio. Junção de versões com mais de seis conserva todas as referências e envia em lotes, mantendo a sobra. Falha não limpa o rascunho. Upload/erro bloqueiam envio, troca de versão, Escape, fechar resposta/painel e retirar fixado; recolher sem desmontar continua possível.

4. **Transporte e comentários.** Canal dedicado `mb-attachment-request/result` e `mb-attachment-preview-request/result`, com janela, origem, token, fid, hash, requestId e limites. Upload no host; o relatório conserva CSP `connect-src none` e o teto legado de 160.000 caracteres. POST mantém contrato congelado `anexos:[attachment]`; backend n2 resolve caminhos da ponte. Fingerprints/chaves/recibos incluem anexos, permitindo editar só a imagem; ACK leva snapshot de texto e referências. Âncoras, versão e origem da nota foram preservadas.

5. **Arquivos de produto alterados ou novos.**
   - `apps/megabrain-dashboard/web/src/`: `AttachmentInput.tsx`, `attachments.ts`, `attachments.css`, `attachment-transport.ts`, `report-attachment-guard.ts`, `ReportFrame.tsx`, `App.tsx`, `AnalysisForm.tsx`, `CursorTools.tsx`, `report-notes.ts`.
   - `apps/megabrain-dashboard/central_reports.py`.
   - `motor/modelos/interacoes/261010_cursor-ferramentas/cursor-ferramentas.js` e cópia `apps/megabrain-dashboard/web/public/cursor-ferramentas-v1.2.js`.
   - `motor/modelos/interacoes/261010_decisoes-respondiveis/decisoes-respondiveis.js`.
   - Scripts JS novos em `web/scripts/test-attachments.cjs`, `test-app-attachments.cjs`, `test-cursor-attachments.cjs`, `test-report-note-attachments.cjs`, `test-reportframe-attachments.cjs`, `test-modal-attachment-close.cjs`, `test-attachments-canonical.mjs` e fixtures isoladas `serve-attachments-probe.mjs`/`attachments-probe-entry.js`.
   - Nenhuma alteração em `central_server.py`, store, bridge, mapa, package.json, dist ou estado global por este nó. Manifesto exato: `interface/verificacao-final.json`.

6. **Comandos e provas.** Em `apps/megabrain-dashboard/web`:

```text
node --test scripts/test-attachments.cjs scripts/test-report-note-attachments.cjs scripts/test-cursor-attachments.cjs scripts/test-app-attachments.cjs scripts/test-reportframe-attachments.cjs scripts/test-modal-attachment-close.cjs
node scripts/test-attachments-canonical.mjs
npm run check
```

   - JS: **55/55**, `interface/testes-js-final.log`.
   - Chromium canônico: **38/38**, `interface/canonical-tests/resultado.json`; screenshots desktop/mobile com PNG sintético visível e prévias carregadas. Não são capturas de produção.
   - Qt/componente: **11/11**, `interface/browser-probe.json`, `prints-1440.png`, `prints-390.png`; abri e inspecionei ambos. Fixture local sem API real. Servidor de teste encerrado após a prova.
   - Tipos: **exit 0**; executei o comando literal `npm run check` também na conferência final.
   - Cursor canônico e public idênticos: SHA-256 `9e6f4181667e7a4dcef0dea6bad806bd03416b11bb491ce798c75f01e8740f49`.
   - Revisão de outro worker Codex: R1–R4 corrigidos e conferidos; `interface/revisao-integracao.md`. Não substitui revisão GLM final.

7. **Falhas antigas e limites explícitos.** `test-report-notes.cjs` tem 8/9: C8 legado espera apagar por ausência e conflita com A2 concorrente (remoção explícita). `test_central_reports.py` tem 18 aprovações, 1 skip e 1 falha antiga de rótulo “protótipo” versus “relatório”, já presente no backup. Não alterei esses testes fora do escopo de scripts novos nem declarei suíte global aprovada. Não certifiquei clipboard físico no aplicativo de produção, Pixel físico ou recuperação de File ainda não enviado após encerrar o processo.

8. **Próximo responsável: n0.** Integrar backend n2 e transporte multimodal pertinente; revisão GLM final, build global, dist, reinício e prova no app real. A ordem continua aberta para o coordenador. Nada exige ação do <USUARIO> neste nó. Lição registrada via `/registrar-licao` somente em `interface/LICOES.md`, sem mudar memória/estado global.

Evidência consolidada: `<MEGABRAIN_ROOT>\evidence\261018_ponte-orquestradores\interface`.
