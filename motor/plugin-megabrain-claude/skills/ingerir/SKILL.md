---
name: ingerir
description: Ingere fontes brutas (artigo, transcrição, PDF, print, briefing, e-mail) de cerebro/raw/ e destila em páginas de wiki (um tópico por arquivo) e cards de pessoas, mantendo cerebro/INDICE.md — o "LLM wiki" do megabrain. Use quando o usuário digitar /ingerir, disser "ingere isso", "joga no cérebro", "guarda essa fonte", "lê isso e anota", "o que eu sei sobre X", ou soltar um arquivo em cerebro/raw/.
---

# ingerir — fonte bruta vira conhecimento que compõe

**v1.0 · 260822.** Camada de conteúdo do megabrain. Lições e decisões guardam
*como trabalhar*; `cerebro/` guarda *o que você sabe* (clientes, mercado,
referências, hardware, pesquisa). O ciclo: `raw/` → destilar → `wiki/` +
`pessoas/` → `INDICE.md` → índice de embeddings → hook injeta no prompt.

## Onde está o cérebro

Dois cérebros, sempre os dois:

1. **Do projeto:** `<projeto>/cerebro/` — cliente, briefing, fontes deste
   trabalho. `mb-check-version.py` cria o esqueleto no Gate 0 se faltar.
2. **Da central:** `<MEGABRAIN_ROOT>/memoria/cerebro/` — conhecimento que vale em
   qualquer projeto (mercado, ferramentas, pessoas recorrentes, método).

Regra de destino: *serviria num projeto completamente diferente?* Sim →
central. Não → projeto. Na dúvida, projeto (subir depois é barato).

## Procedimento

### 1. Descobrir o que falta ingerir
- Liste `raw/` e compare com a tabela **Fontes processadas** do `INDICE.md`
  (hash sha256 curto, 16 hex). Sem hash igual = pendente. Conteúdo mudou =
  pendente de novo.
- Se o usuário mandou texto/link no chat em vez de arquivo, **salve primeiro**
  em `raw/YYMMDD_slug.md` (texto integral ou transcrição) — o raw é a prova.
  Link sem conteúdo não é fonte.

### 2. Ler a fonte inteira
- PDF/imagem: extraia o texto; print de tweet/artigo: transcreva.
- Anote: autor, data, tipo (artigo, transcrição, briefing, e-mail, print),
  o que a fonte **afirma** e o que ela **prova** (dado, exemplo, código) —
  são coisas diferentes; marketing e número sem origem ficam rotulados.

### 3. Destilar em páginas (um tópico por arquivo)
- Para cada tópico que a fonte cobre: existe página em `wiki/`? Grep por
  slug e por termo. **Existe → atualize** (append em Fatos, ajuste TL;DR,
  acrescente a fonte). **Não existe → crie** a partir de
  `modelos/cerebro/wiki/260822_MODELO-pagina.md`.
- Nome: `YYMMDD_slug.md`, lowercase, hífen, data = criação da página (não
  muda ao atualizar; o campo **Atualizado** muda).
- Um fato por linha. Número/preço/data/versão com fonte ou `[ESTIMATIVA]`.
  Contradição entre fontes: registre as duas com data — não escolha em
  silêncio.
- Pessoa/empresa citada com relevância de relação (cliente, contato,
  fornecedor) → card em `pessoas/` a partir de
  `modelos/cerebro/pessoas/260822_MODELO-card.md`. Figura pública citada de
  passagem (autor de artigo) **não** vira card — vai em Fontes.
- Linke: toda página cita as páginas vizinhas em **Relações**, nos dois
  sentidos.

### 4. Atualizar o INDICE.md
- Tabela Páginas: uma linha por página criada/atualizada.
- Tabela Pessoas: idem para cards.
- Tabela Fontes processadas: `raw/arquivo` · hash · YYMMDD · lista do que
  gerou/atualizou.
- Nunca apague linha; página aposentada ganha `(aposentada)` no tópico.

### 5. Indexar
`python "<MEGABRAIN_ROOT>/bin/mb-indice-cerebro.py" --indexar --cerebro <pasta>/cerebro`
(roda para o cérebro do projeto e o da central; sem Ollama, cai em keyword
e avisa). O hook `mb-contexto.py` passa a injetar as páginas mais próximas
do prompt.

### 6. Responder ao usuário (1 bloco, N1)
TL;DR com: fontes ingeridas (n), páginas criadas / atualizadas (paths),
cards (paths), fatos marcados `[ESTIMATIVA]` ou contraditórios, dúvidas
abertas que só ele responde (máx. 3).

## Perguntar ao cérebro ("o que eu sei sobre X")

1. `INDICE.md` dos dois cérebros → candidatas por tópico.
2. `mb-indice-cerebro.py --buscar "X"` → top-5 por proximidade.
3. Leia só as páginas candidatas. Responda **citando `path`**. Se não está
   nas páginas: **"não encontrado no cérebro"** — e ofereça ingerir a fonte.
   Não complete com memória do modelo sem rotular.

## O que não fazer
- Não editar `raw/`. Não mover raw depois de ingerido (o hash no INDICE é o
  marcador).
- Não criar `notas.md`, `geral.md`, `diversos.md`. Tópico sem nome = página
  que ninguém acha.
- Não duplicar: antes de criar, grep. Duas páginas do mesmo tópico é fork.
- Não transformar lição de processo em página de wiki (vai em
  `licoes-megabrain.md` via `/registrar-licao`) nem o contrário.
- Não subir `cerebro/` pra repositório público — está em `EXCLUIR` do
  gerador do pacote.

## Manutenção (quando o usuário pedir "arruma o cérebro")
- Páginas sem fonte, sem atualização há 90+ dias, ou com 2+ páginas
  cobrindo o mesmo tópico → relatar e propor merge. Merge preserva todas as
  fontes e aposenta a página absorvida no INDICE.

## Manutenção (rodar junto, sem custo de token extra)

No começo de uma sessão de ingestão: `python bin/mb-manutencao-cerebro.py --auto`
(silencioso se rodou há <7 dias). Fontes também podem chegar por `02_entrada/`
na central: ingerir = mover o original pra `cerebro/raw/` e destilar normalmente.
