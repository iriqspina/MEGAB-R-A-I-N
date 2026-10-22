# Resultado do nó n2 — transporte e persistência de prints no backend

TL;DR — Backend implementado e verificado com **101 testes direcionados aprovados, zero falhas, erros ou testes pulados**. Rotas autenticadas persistem e recuperam PNG/JPEG/GIF/WebP no projeto; comentários, feedback, decisões e Novo pedido aceitam referências, inclusive sem texto humano. Integração visual, transporte multimodal dos clientes, revisão GLM final e reinício ficam com n0, conforme divisão da ordem.

## 1. Arquivos alterados/criados

1. `apps/megabrain-dashboard/central_attachments.py` (novo): valida base64 e bytes raster com Pillow já instalado; armazenamento `.mb-anexos/<sha256>.<extensão-real>` com manifesto por imagem, deduplicação por conteúdo, resolução confinada por projeto, leitura limitada e bloqueio de symlink/junction/hardlink. Metadados recebidos não são autoridade de leitura.
2. `apps/megabrain-dashboard/central_server.py`: POST/GET de anexos, teto maior somente no POST de upload, idempotência por conteúdo e por chave de tentativa; comentários/feedback/jobs resolvem anexos de seu próprio projeto antes de persistir. Pedido/comentário só com imagem mantém `prompt=''`/`text=''`; `Pedido com imagem` é título do sistema. Feedback agrega caminhos únicos e preserva vínculos em cada nota/resposta, hash da fonte, versão anterior e estado recebido.
3. `apps/megabrain-dashboard/central_execution.py`: argumento independente `attachments=` prepara cópias binárias em `workspace/.mb-anexos` com manifesto e hash próprios. `selected_paths` permanece restrito a texto/código. Imagens intactas não viram artefatos; alteração, remoção, link ou arquivo extra causam pendência verificável.
4. `apps/megabrain-dashboard/central_workflows.py`: entrega os caminhos reais das cópias à etapa de código e registra o contexto disponível. Etapas sem transporte visual recebem somente metadados; não há alegação de inspeção visual. Esse limite fica explícito na cobertura da revisão.
5. `apps/megabrain-dashboard/tests/test_central_attachments.py` (novo): 14 testes HTTP/armazenamento e de associação.
6. `apps/megabrain-dashboard/tests/test_central_attachment_execution.py` (novo): 16 testes de preparação, confinamento, inventário e execução simulada com imagem e pedido vazio.

Não editei `central_store.py`, `central_reports.py`, `central_bridge.py`, frontend, cursor, mapa, estado global ou dist. Não reiniciei app nem rodei build global. A assistência na implementação do executor e a auditoria interna foram subagentes da mesma conta; não representam Codex 2 nem substituem revisão GLM.

## 2. Gate, backup e concorrência

- Parecer GLM n1 **AJUSTAR**, lido antes da produção e preservado em `evidence/261018_ponte-orquestradores/backend/parecer-usado.md`. A1: teto próprio por rota; A2: persistência de caminhos STRING; A3: fontes exclusivas; A4: render sem rede e upload pelo host, responsabilidade n3. A recomendação de caminho relativo foi conciliada com o contrato congelado: caminhos finais são **strings canônicas absolutas**, para a ponte localizar o arquivo.
- O plano revisado pelo n0 no disco incorpora esses quatro ajustes. Backups das três fontes existentes estão em `evidence/261018_ponte-orquestradores/backend/backup/`; hashes/mtimes anteriores em `antes.json`.
- Trava consultada: vencida e fora deste escopo. Mtimes/hashes foram conferidos antes das edições; patches preservaram o conteúdo existente. Os seis arquivos de produção/testes ficaram com hashes e mtimes estáveis durante a suíte final: `sources_unchanged_during_tests: true`. Nenhum conflito externo detectado no recorte n2.
- Complementos de coordenação até 17:20 foram lidos; tratam de arquivos da interface/mapa e não ampliaram as fontes deste nó.

## 3. Contrato efetivo

- `POST /api/projects/{pid}/attachments`, JSON `{name,mime,data}` com base64 sem prefixo; retorno `{attachment:{id,path,name,mime,size,url}}`. `id` é SHA-256 de 64 caracteres. Repetir conteúdo retorna o mesmo anexo; repetir chave com outro corpo retorna 409.
- `GET /api/projects/{pid}/attachments/{id}` autenticado, resposta com bytes e MIME reais, `nosniff` e `no-store`; projeto desconhecido é recusado e ID de outro projeto não concede leitura.
- PNG/JPEG/GIF/WebP, **8 MiB por arquivo**, até **6 imagens por envio**, contando a união de notas/respostas. O POST de upload tem teto de corpo base64 calculado (`11.193.004 bytes`); todas as demais mutações mantêm `350.000 bytes`, inclusive quando não há Content-Length. Origem e CSRF seguem a segurança atual.
- Defesa adicional contra expansão de raster: até **40.000.000 pixels somados pelos tamanhos reais dos quadros**, até **200 quadros**. SVG/HTML, arquivo truncado, MIME falso e conteúdo não raster são recusados. Nome é só apresentação; não escolhe caminho nem extensão do armazenamento.
- API recebe objetos de upload ou referências canônicas já persistidas. `anexos` finais são **caminhos STRING absolutos**, compatíveis com `central_bridge._texto_comentarios`; `attachment_details` contém metadados reconstruídos. Atributos forjados, caminho arbitrário, outro projeto e referências fora de `.mb-anexos` são rejeitados. Associação por nota/resposta é mantida, com união única no comentário principal.

## 4. Verificação executada

Antes: 9 testes existentes de API de relatório + 23 de segurança passaram.

Conferência final reproduzível, da raiz do projeto:

```powershell
python -X utf8 evidence/261018_ponte-orquestradores/backend/verificar.py
```

Usa Python com `apps/megabrain-dashboard/runtime-packages`, `MB_ISOLATED=1`, `MB_PONTE=0`, fixtures temporárias, `Ponte.lancar=False` e executores simulados. Carrega seis módulos: anexos, executor com anexos, segurança, API de relatório, execução e workflows. Resultado em **12,620 s: 101 testes, 0 falhas, 0 erros, 0 pulados**. Os 30 testes novos estão incluídos nesse total; não são somados novamente.

Cobertura observada: autenticação/CSRF/origem, leitura após reabertura, quatro formatos, 8 MiB exatos e excesso, contagem real de corpo sem Content-Length, limite exclusivo por rota, projeto permitido, referência forjada/cruzada, link/hardlink, corrupção de bytes/manifesto, repetição de envio, seis imagens, associação de notas/decisões, versão anterior/hash, ponte recebendo strings e pedido/comentário só com imagem. O stub de execução leu os bytes reais dentro do `execution_dir`; nenhuma inferência real foi usada como teste.

Evidências: `backend/testes-direcionados.log`, `backend/testes-direcionados.json` e `backend/resultado.json`. Auditoria suplementar em `backend/revisao-interna.md`: encontrou expansão de canvas em GIF entre quadros, corrigida e coberta por regressão com GIF real. Nenhum outro achado material no recorte final. Histórico da preparação do executor em `backend/revisao-execucao.md`.

## 5. Pendências para integração n0

1. O código atual disponibiliza bytes à etapa de código; etapas textual/research e revisão recebem só metadados. Sem transporte visual demonstrado, a cobertura fica incompleta e o job pode terminar `partial` por `review_context_incomplete`. N0 já acrescentou `transporte-imagens` ao plano; deve integrar o retorno n5 em `central_workflows.py` **após este nó terminar**, preservando seus hashes/backup. Acesso aos bytes não comprova percepção visual pelo modelo.
2. N0/n3 verificam upload do host pelo canal postMessage, Ctrl+V/arquivo, prévias, remoção, erro e rascunhos no app real. N0 faz revisão GLM final, testes integrados/build/reinício e conclusão da ordem. Este nó não concluiu a ordem nem marcou comentário como `CORRIGIDO_VERIFICADO`.
3. Nada exige ação do <USUARIO> neste recorte. Lição do GIF registrada apenas na evidência local `backend/LICOES.md`, sem editar lições/estado globais.
