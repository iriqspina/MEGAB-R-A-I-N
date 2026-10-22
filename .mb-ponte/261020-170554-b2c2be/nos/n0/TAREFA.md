# Ordem da ponte MegaBrain · 261020-170554-b2c2be

Você é o **planejador** (nó n0) e o orquestrador-raiz. IA escolhida pelo <USUARIO>: **GPT** (Codex · conta principal (Codex 1)).
Projeto: `<MEGABRAIN_ROOT>` · pasta da ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261020-170554-b2c2be`

## O que o <USUARIO> pediu (literal, pelo botão "Enviar ao projeto")
### Comentário 1 · 2026-10-20T20:02:47+00:00
- Relatório: `<MEGABRAIN_ROOT>/00_PARA-VOCE/261020_bapp-planejamento/PLANEJAMENTO-BAPP.html`
- Nota no relatório, cravada em: "MEGABRAIN · planejamento do aplicativo (bapp) · 20/10/2026 · plano final v1 · codex + glm" (âncora body)
> crie uma função no cursor inteligente que uso para editar e comentar no bapp de pausa, pois se depois de x tempo o projeto roda sozinho, eu devo poder pedir para aguardar retorno e pausar projeto (melhor entao adicionar 2 novas funcoes mas com as bolinhas meio mescladas, porque são atividades parecidas, ajuda a compreender e reduz espaço de uso no layout, aprenda isso para design e crie tmb uma skill que utilize essa forma de analise para designs nas nocoes do megabrain, não é obrigatório e sim uma ferramenta de ajuda. preciso tomar banho agora então quero que aguarde por retornos

## Seu trabalho
1. Leia ESTADO.md → HANDOFF.md → fim de DECISOES.md → LICOES.md do projeto (procure também em memoria/estado/) e confira a trava. Meça o estado real antes de descrever.
2. Abra o relatório citado e o ponto exato de cada nota. Se um termo tiver duas leituras que mudam o resultado, escolha a mais conservadora e registre a dúvida como pendência.
3. Grave o plano em `<MEGABRAIN_ROOT>/.mb-ponte/261020-170554-b2c2be/plano.json`: {"objetivo", "criterios" (verificáveis), "tarefas": [{"id", "titulo", "papel", "vendor", "arquivos", "depende_de", "revisor_vendor"}]}.
4. Execute: faça você mesmo o que for pequeno; abra orquestradores/workers para o que for separável (instruções abaixo).
5. Verifique de verdade: testes, build, prints quando for visual. Confira no disco o que cada nó disse que fez.
6. Antes de concluir, leia `<MEGABRAIN_ROOT>/.mb-ponte/261020-170554-b2c2be/complementos.jsonl` se existir: são comentários que chegaram depois e entram nesta mesma ordem.
7. Conclua (isso atualiza o comentário no app MegaBrain):
```bash
python "<MEGABRAIN_ROOT>/bin/mb-ponte.py" concluir --ordem "<MEGABRAIN_ROOT>/.mb-ponte/261020-170554-b2c2be" --status corrigido --resumo "o que foi feito em 1–3 frases" --prova "comando/arquivo que prova" --pendencia "o que ficou para o <USUARIO>"
```
   Use `--status parcial` se ficou algo por fazer e `--status falhou` se não deu para corrigir.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261020-170554-b2c2be/nos/n0/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.

## Como abrir outras IAs (orquestradores e workers)
IAs ativas neste MegaBrain: claude, gpt, glm. Use a que fizer sentido para cada tarefa.
Tarefa separável e grande → abra um nó. Tarefa pequena → faça você mesmo.
```bash
python "<MEGABRAIN_ROOT>/bin/mb-ponte.py" despachar --ordem "<MEGABRAIN_ROOT>/.mb-ponte/261020-170554-b2c2be" --pai n0 --papel worker --titulo "título curto" --tarefa-arquivo caminho/da/tarefa.md
python "<MEGABRAIN_ROOT>/bin/mb-ponte.py" aguardar --ordem "<MEGABRAIN_ROOT>/.mb-ponte/261020-170554-b2c2be" --nos n1,n2
python "<MEGABRAIN_ROOT>/bin/mb-ponte.py" estado --ordem "<MEGABRAIN_ROOT>/.mb-ponte/261020-170554-b2c2be"
```
- Papéis: `orquestrador` (pode abrir outros nós), `worker` (executa), `revisor` (revisa). Profundidade máxima 3; até 16 nós na ordem.
- Cada tarefa enviada diz objetivo, arquivos que pode mexer, critério de pronto e como provar. Nós simultâneos não mexem nos mesmos arquivos.
- A pipeline congelada em pedido.json escolhe fornecedor, modelo e esforço por papel. Não a substitua por preferência própria; override explícito exige justificativa registrada e valores válidos.
- Revisão independente: quem revisa não produziu o resultado; outro fornecedor pode reduzir viés, sem prometer superioridade.
- `despachar` volta na hora (o nó roda em segundo plano); use `aguardar` antes de depender do resultado. `--esperar` faz o despacho bloquear até o fim.
