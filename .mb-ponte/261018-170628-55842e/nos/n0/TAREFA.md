# Ordem da ponte MegaBrain · 261018-170628-55842e

Você é o **planejador** (nó n0) e o orquestrador-raiz. IA escolhida pelo <USUARIO>: **GPT** (Codex · conta principal (Codex 1)).
Projeto: `<MEGABRAIN_ROOT>` · pasta da ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e`

## O que o <USUARIO> pediu (literal, pelo botão "Enviar ao projeto")
### Comentário 1 · 2026-10-18T19:28:52+00:00
- Relatório: `<MEGABRAIN_ROOT>/00_PARA-VOCE/261011_harnesses/261017_MAPA-DO-HARNESS.html`
- Nota no relatório, cravada em: "Mapa do harness: a cidade em volta das IAs Mapa em forma de cidade com metrô: 10 bairros," (âncora #mh-mapa)
> precisa ser aperfeiçoado, revisado e corrigido por outro vendor

### Comentário 2 · 2026-10-18T19:31:15+00:00
- Relatório: `<MEGABRAIN_ROOT>/00_PARA-VOCE/261011_harnesses/261017_MAPA-DO-HARNESS.html` (enviado sobre uma versão anterior)
- Texto literal do <USUARIO>:
> leia o comentário e faça

### Comentário 3 · 2026-10-18T19:32:27+00:00
- Relatório: `<MEGABRAIN_ROOT>/00_PARA-VOCE/261011_harnesses/261017_MAPA-DO-HARNESS.html`
- Texto literal do <USUARIO>:
> quero poder adicionar prints com o crl v e escolhendo arquivo em todos os campos de input aqui do megabrain que são coesos de ter essa funcionalidade. e arrume os comentários, usando codex 1

## Coordenação
Nota da sessão Claude que criou a ponte (18/10/2026 17:06, Brasília):
1. "arrume os comentários, usando codex 1" pede que esta correção seja feita pelo Codex 1 (GPT, conta principal) — você. A nota "precisa ser aperfeiçoado, revisado e corrigido por outro vendor" está cravada no Mapa da cidade (00_PARA-VOCE/261011_harnesses/261017_MAPA-DO-HARNESS.html, âncora #mh-mapa), feito pelo Claude: revisão e correção do mapa ficam com outro fornecedor (GPT e/ou GLM), nunca Claude.
2. Coordenação: a sessão Claude "Megabrain bugs e visualização do harness" está ativa e fez uma crítica de direção de arte do mapa (evidence/261017_cursor-harness/mapa/critica-r2/, últimos arquivos 16:48). Leia essa crítica e aproveite os achados. Arquivos do mapa: bin/mb-harness-mapa.py, dados/harness-mapa.json, motor/modelos/harness-mapa/*, 00_PARA-VOCE/261011_harnesses/261017_MAPA-DO-HARNESS.html. Só edite esses arquivos se nenhum deles mudou nos últimos 20 minutos; antes disso, faça a revisão independente (achados com print em evidence/261018_ponte-orquestradores/mapa-revisao-gpt/) e volte a conferir. O HTML sai do gerador (bin/mb-harness-mapa.py), nunca à mão. Faça backup antes de alterar.
3. "Adicionar prints com Ctrl+V e escolhendo arquivo em todos os campos de input do MegaBrain que são coesos": campos de texto do app (apps/megabrain-dashboard/web/src — caixa "Peça uma alteração neste relatório" em ReportFrame.tsx, comentário de módulo, Novo pedido, decisões com texto) e as notas do cursor dentro dos relatórios (motor/modelos/interacoes/261010_cursor-ferramentas/, com cópias em web/public e web/dist). Hoje o servidor não recebe anexos: crie uma rota que guarde a imagem dentro do projeto (fora de 00_PARA-VOCE, ex.: .mb-anexos/) com limite de tamanho e tipo, e ligue o caminho ao comentário (o pedido da ponte já lê o campo "anexos" do comentário). Campos onde imagem não faz sentido (senha, busca, nomes) ficam fora.
4. App fora do Git: backup em evidence/261018_ponte-orquestradores/ antes de editar; prove com python -m unittest discover -s tests (em apps/megabrain-dashboard), npm run build e npm run test:ui (em web/). Para o servidor novo valer, reinicie o MegaBrain do jeito simples (fechar a janela; abrir apps/megabrain-dashboard/bootstrap/MegaBrain.exe; conferir http://127.0.0.1:8766/api/health) — autorizado pelo <USUARIO>.
5. "Arrume os comentários" — leitura conservadora: tratar estes comentários de ponta a ponta e registrar o resultado pela ponte (concluir). Se achar defeito no próprio sistema de comentários durante o trabalho, corrija e registre; dúvida de interpretação vira pendência.

## Seu trabalho
1. Leia ESTADO.md → HANDOFF.md → fim de DECISOES.md → LICOES.md do projeto (procure também em memoria/estado/) e confira a trava. Meça o estado real antes de descrever.
2. Abra o relatório citado e o ponto exato de cada nota. Se um termo tiver duas leituras que mudam o resultado, escolha a mais conservadora e registre a dúvida como pendência.
3. Grave o plano em `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e/plano.json`: {"objetivo", "criterios" (verificáveis), "tarefas": [{"id", "titulo", "papel", "vendor", "arquivos", "depende_de", "revisor_vendor"}]}.
4. Execute: faça você mesmo o que for pequeno; abra orquestradores/workers para o que for separável (instruções abaixo).
5. Verifique de verdade: testes, build, prints quando for visual. Confira no disco o que cada nó disse que fez.
6. Antes de concluir, leia `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e/complementos.jsonl` se existir: são comentários que chegaram depois e entram nesta mesma ordem.
7. Conclua (isso atualiza o comentário no app MegaBrain):
```bash
python "<MEGABRAIN_ROOT>/bin/mb-ponte.py" concluir --ordem "<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e" --status corrigido --resumo "o que foi feito em 1–3 frases" --prova "comando/arquivo que prova" --pendencia "o que ficou para o <USUARIO>"
```
   Use `--status parcial` se ficou algo por fazer e `--status falhou` se não deu para corrigir.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e/nos/n0/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.

## Como abrir outras IAs (orquestradores e workers)
IAs ativas neste MegaBrain: claude, gpt, glm. Use a que fizer sentido para cada tarefa.
Tarefa separável e grande → abra um nó. Tarefa pequena → faça você mesmo.
```bash
python "<MEGABRAIN_ROOT>/bin/mb-ponte.py" despachar --ordem "<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e" --pai n0 --papel worker --vendor gpt --titulo "título curto" --tarefa-arquivo caminho/da/tarefa.md
python "<MEGABRAIN_ROOT>/bin/mb-ponte.py" aguardar --ordem "<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e" --nos n1,n2
python "<MEGABRAIN_ROOT>/bin/mb-ponte.py" estado --ordem "<MEGABRAIN_ROOT>/.mb-ponte/261018-170628-55842e"
```
- Papéis: `orquestrador` (pode abrir outros nós), `worker` (executa), `revisor` (revisa). Profundidade máxima 3; até 16 nós na ordem.
- Cada tarefa enviada diz objetivo, arquivos que pode mexer, critério de pronto e como provar. Nós simultâneos não mexem nos mesmos arquivos.
- Revisão independente: quem revisa é de fornecedor diferente de quem produziu.
- `despachar` volta na hora (o nó roda em segundo plano); use `aguardar` antes de depender do resultado. `--esperar` faz o despacho bloquear até o fim.
