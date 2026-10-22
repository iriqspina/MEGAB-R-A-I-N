# Resultado · nó n1 · Revisão do plano (GLM/ZCode)

**Veredito: AJUSTAR** — plano aprovado em escopo e critérios, mas com 4 achados materiais a corrigir no plano antes da produção. Revisão completa em `evidence/261018_ponte-orquestradores/revisao-plano-glm.md`.

## O que mudou (arquivos)
- Criado: `<MEGABRAIN_ROOT>/evidence/261018_ponte-orquestradores/revisao-plano-glm.md` (revisão com evidências por linha).
- Criado: este `resultado.md`.
- Nenhuma fonte editada; nenhum outro nó aberto; nenhuma chamada de rede externa.

## Achados curtos
1. **Bloqueante (A1):** o middleware corta todo corpo de POST em 350 KB (`central_server.py:73-84`); o contrato de anexos (base64 em JSON, 8 MiB/imagem ≈ 10,9 MB em base64) nunca passaria — precisa exceção por rota com cap próprio e streaming, ou o critério "8 MiB" é inalcançável.
2. **A2:** a ponte imprime `anexos` com `_posix(a)` esperando string-caminho (`central_bridge.py:327/760/89`); o plano prevê objetos "attachment" → sairia lixo na tarefa do worker. Fixar: `anexos` guarda caminho relativo como string; `central_bridge.py` (fora da lista de arquivos dos nós) não é tocado.
3. **A3:** backend e interface são simultâneos, mas comentários, feedback de relatório e "Novo pedido" (jobs) vivem em `central_server.py` — só o backend pode tocar rotas; a interface fica no front, ou `interface` passa a depender de `backend`. Confirmado por mtime que esses arquivos mudaram hoje 17:04–17:13 (sessão Claude paralela ativa; trava de HANDOFF sobre `cursor-ferramentas.js` vencida em data, sessão viva) — conferir mtimes imediatamente antes de cada edição e refazer backup.
4. **A4:** notas do cursor com print: o relatório renderizado não tem rede (CSP `connect-src 'none'`, `central_reports.py:31`) e o rascunho limita valores a 50.000 chars — colagem exige canal postMessage render→wrapper→host com upload pelo host e referência curta na nota; bytes nunca no rascunho.
5. Menores: idempotência no upload (retry sem duplicar), anexo atrelado ao pid na leitura, não reusar `confined_file` para `.mb-anexos` (ele recusa caminhos ocultos, `central_reports.py:62`), validar magic bytes além do mime declarado.

## Como verifiquei
Leitura integral de `central_server.py`, `central_reports.py`, `ReportFrame.tsx` e `api.ts`; trechos de `central_bridge.py` (`_posix`, anexos, `comentario_para_ordem`); localização do "Novo pedido" (`create_job`) e comentários de módulo (rota `/comments`); grep de colagem no cursor canônico (não existe hoje); conferência de mtimes e da trava em `memoria/estado/HANDOFF.md`.

## Pendente
- Para o n0 (GPT): incorporar A1–A4 no `plano.json` antes de despachar os workers; a recomendação 1–5 da evidência é opcional.
- Para os workers: com o plano ajustado, nada me bloqueia; revisão de cada entrega continua comigo (revisor_vendor glm) quando os nós produzirem.
- Nada exige o <USUARIO> nesta etapa.
