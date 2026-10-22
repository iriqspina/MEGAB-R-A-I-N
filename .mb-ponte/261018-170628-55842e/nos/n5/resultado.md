# Resultado do nó n5 — transporte de imagens aos clientes

TL;DR — Concluído no escopo do n5 e pronto para integração pelo n0. `run_model` aceita `image_paths` como keyword opcional; Codex recebe imagens pelo `exec --image` e Claude pelo stdin multimodal `stream-json`. GLM-5.3 devolve limitação explícita antes da inferência, pois o catálogo do executável oficial verificado declara entrada somente de texto. **22 testes aprovados, sem inferência real.**

1. **Arquivos alterados e API final.**
   - `<MEGABRAIN_ROOT>/apps/megabrain-dashboard/model_clients.py`
   - `<MEGABRAIN_ROOT>/apps/megabrain-dashboard/tests/test_model_clients.py` — arquivo novo.
   - API: `run_model(..., image_paths=[str(path), ...])`. `None` e lista vazia preservam o transporte textual; os metadados são aditivos.
   - O `logdir` deve ser o diretório da etapa: `<job_directory>/<etapa>`. Imagens aceitas somente em `<job_directory>/workspace/.mb-anexos`, com caminhos absolutos canônicos. Não passar originais de `.mb-anexos` do projeto nem caminhos do navegador.

2. **Validação e isolamento preservados.**
   - Até 6 imagens, 8 MiB cada e 48 MiB no conjunto; PNG/JPEG/GIF/WebP validados por decodificação de bytes via `central_attachments.validate_image`, importação local sem ciclo observado.
   - Rejeita caminhos relativos, traversal, outro job, arquivos externos, diretórios, ausentes, repetidos, links/reparse e hardlinks. Compara identidade/tamanho/mtime na leitura; Codex revalida bytes antes de entregar os caminhos ao processo.
   - Mantém a conta Codex selecionada apenas no ambiente filho, ferramentas desabilitadas em textual, research restrito às duas ferramentas web e sandbox/permissões anteriores em code. Não altera providers, assinatura ou configuração global.
   - A entrada multimodal do Claude fica apenas no stdin. Base64 dos arquivos entra na redação dos logs/resultados para suprimir um eventual eco do cliente. Teste de eco acidental confirma ausência do payload codificado nos arquivos do adapter.

3. **Metadados distinguem transporte de percepção.**
   - `image_inputs`: `id`, `path`, `mime`, `size`, `sha256`, `transport`, `state`, `transported` e `visual_inspection_observed=False` por imagem.
   - `image_transport`: mecanismo, estado e evidência/limitação; `provider_visual_ack_observed=False`. `transported=True` só após término aceito do cliente, com escopo explícito `native_cli_input_only`. Não comprova envio ao provedor nem interpretação dos pixels.
   - Falta de suporte visual retorna `status='image_transport_unavailable'`, `model_called=False`, `transported=False`, estado `unsupported` e motivo. Não há fallback silencioso.

4. **Fatos sobre os clientes instalados.**
   - Ajuda local do Codex confirma `exec --image`; argumentos usam `--` antes do prompt `-` para ele não ser consumido pela opção de imagens.
   - Ajuda local do Claude confirma os formatos stream-json. Mensagem `user` contém blocos `text` e `image` com `source.type='base64'`, MIME e bytes. Esquema conferido na [documentação oficial de streaming input](https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode) e flags na [referência oficial de CLI](https://code.claude.com/docs/en/cli-reference).
   - O executável ZCode realmente usado pelo adapter (`AppData/Local/Programs/ZCode/resources/glm/zcode.cjs`) tem o SHA-256 fixado `e9f1868c0fdb863537ed910ee3828b9be96b8c2fd805473f63b439e1113266b8`. Seu `--help` confirma `--attach`, mas o catálogo embutido de `glm-5.3` declara `attachment:false` e modalidades de entrada `text`. Por isso a rota main/max tool-free é recusada com imagem, antes de ler credenciais/configurar o cliente. Não foi habilitado outro modelo, MCP ou ferramenta visual.

5. **Provas gravadas.**
   - Pasta: `<MEGABRAIN_ROOT>/evidence/261018_ponte-orquestradores/transporte-imagens/`.
   - `resultado.json`: API final, hashes e mtimes finais, contrato, testes, fatos, limites e pendências para integração.
   - `testes.txt`: 22 testes, 0 falhas, 0 erros, 0 pulos. Comando equivalente, executado no dashboard: `python -X utf8 -m unittest discover -s tests -p test_model_clients.py -v`.
   - Cobertura: bytes/argumentos no mock Codex; bytes no stdin multimodal Claude nos quatro formatos; GLM recusado sem inferência; configuração/conta/ferramentas; limites exatos 6 arquivos/48 MiB; excessos e caminhos negativos; hardlink real e reparse simulado; troca de bytes antes do envio; logs sem base64; cancelamento/erro/resultado ausente; comportamento sem imagens nos três clientes.
   - `preflight.json` e `model_clients.before.py`: backup anterior com hash conferido; `model_clients.diff`: revisão das mudanças. `cli-help.json`, três arquivos `*-help.txt`, `glm-image-limitation.txt` e `fontes.json`: evidência local/documental. Sintaxe dos dois arquivos compilada sem erro.
   - A primeira execução dos testes revelou diferença de `st_ctime_ns` entre `stat` e `fstat` no Windows/Python local. A comparação passou a usar identidade, tamanho, mtime e contagem de links, preservando a detecção de troca. O teste de mudança de bytes continua passando.

6. **Pendências do coordenador; nenhuma ação do <USUARIO> requerida por este nó.**
   - N0 liga `image_paths` aos caminhos das cópias preparadas por n2 no workspace, trata explicitamente a indisponibilidade visual GLM, providencia revisão independente e prova de integração/app.
   - Os testes demonstram construção/transporte até processos simulados. Não houve modelo real, recebimento pelo provedor, percepção de pixels, teste de app ou reinício. Não abriram-se outros nós nem houve mutação Git.
   - Codex reabre caminhos no processo nativo; a revalidação anterior reduz a janela de troca, mas não constitui bloqueio imutável do sistema operacional.

## Lição preparada para o n0 — /registrar-licao

GATILHO: transportar prints por um CLI de assinatura sem ampliar ferramentas nem trocar o modelo contratado.
LIÇÃO: a presença de `--attach` no ZCode não prova entrada visual no GLM-5.3; o catálogo do executável fixado declara somente texto. No Windows local, `stat` e `fstat` também expõem `ctime` diferente no mesmo arquivo.
ATALHO: conferir ajuda e catálogo do executável efetivamente usado; recusar a rota visual incompatível antes da inferência; provar bytes/flags com processos simulados; comparar identidade, tamanho, mtime, links e hash, separando transporte de percepção. O registro no canônico fica para o coordenador, pois o escopo exclusivo do n5 não autoriza alterar lições compartilhadas.
