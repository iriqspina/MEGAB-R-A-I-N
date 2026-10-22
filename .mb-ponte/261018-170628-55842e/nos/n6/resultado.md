# Resultado do nó n6 — revisão de armazenamento e segurança dos prints

TL;DR — **APROVADO.** Revisão independente GLM/ZCode do backend n2 não encontrou defeito explorável no escopo congelado; 101 testes reproduzidos com 0 falhas/0 erros/0 pulados; hashes do n2 conferidos 6/6; 4 observações informativas de gravidade baixa registradas sem bloquear a integração do n0. Parecer completo: `evidence/261018_ponte-orquestradores/revisao-backend-glm.md`.

## 1. O que fiz (somente leitura + provas; nada implementado)

1. Li `nos/n2/resultado.md`, `backend/resultado.json`, `backend/testes-direcionados.json`, `backend/verificar.py` e os backups do n2.
2. Recalculei SHA-256 dos 6 arquivos do escopo congelado (`central_attachments.py`, `central_server.py`, `central_execution.py`, `tests/test_central_attachments.py`, `tests/test_central_attachment_execution.py`; `central_workflows.py` excluído por contrato) — todos idênticos ao registrado pelo n2, incluindo após a suíte.
3. Li integralmente as fontes e os 2 módulos de teste; fiz diff contra os backups para isolar o delta real do n2 (aditivo, restrito a anexos).
4. Rodei a suíte dos 6 módulos com runner próprio (`MB_ISOLATED=1 MB_PONTE=0`, fixtures, sem sobrescrever evidências do n2): **101 testes, 0 falhas, 0 erros, 0 pulados, OK em 25,4 s**.
5. Analisei linha a linha os itens pedidos: auth/CSRF/origem, limites (8 MiB/arquivo, 6 imagens únicas somando notas/respostas, teto de upload 11.193.004 B só na rota de upload, 350.000 B nas demais com contagem real sem Content-Length), raster (verify + decode por quadro, 40 M pixels somados, 200 quadros, bomba de decompressão recusada), referência entre projetos, traversal/symlink/junction/hardlink, TOCTOU (mitigado por hash SHA-256 pós-leitura e leitura limitada), corrupção de bytes/manifesto, idempotência por conteúdo e por chave, feedback de nota/resposta sem texto, ponte recebendo strings (`central_bridge.py:327,792`), bytes reais no workspace da execução, anexos nunca virando artefatos e mutação de entrada detectada.
6. Probe independente: `normalize_feedback` com lista lança `TypeError` só em chamada direta — impossível via HTTP (`central_server.py:317` valida dict antes); registrado como observação de robustez, não defeito.

## 2. Veredito e observações

- **APROVADO** para o escopo congelado do n2. Nenhum achado de gravidade média/alta.
- Observações informativas (gravidade baixa, não bloqueiam): (1) re-decode completo da imagem a cada GET — custo de CPU, defesa em profundidade legítima; (2) anexos órfãos sem coleta; (3) `normalize_feedback` sem validação de tipo para chamadas fora do endpoint; (4) `anchor` sem validação estrutural — pré-existente ao n2 (confirmado no diff). Correções mínimas sugeridas no parecer.

## 3. Arquivos escritos por este nó

1. `<MEGABRAIN_ROOT>/evidence/261018_ponte-orquestradores/revisao-backend-glm.md` (parecer técnico completo com hashes, método e observações).
2. Este `resultado.md`. Nenhuma fonte, teste ou evidência de outro nó foi modificada.

## 4. Pendências (fora do meu alcance)

1. Integração do transporte nativo em `central_workflows.py`/`model_clients.py` — n0/n5; exigirá nova revisão do delta.
2. Prova no app real (Ctrl+V, prévias, remoção, erro) — n0/n3.
3. Observações 1 e 2 podem vir refinamento pós-ordem; não são pré-requisito.
4. Nada exige ação do <USUARIO>.
