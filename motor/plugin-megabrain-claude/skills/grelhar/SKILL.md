---
name: grelhar
description: Entrevista em rodadas que esvazia o briefing antes de produzir — árvore de decisão, perguntas numeradas com resposta recomendada, e a regra de que fato é trabalho do agente e decisão é do usuário. Use quando o usuário digitar /grelhar, disser "grelha isso", "me grelha", "clareia isso", "me pergunta o que precisar", "antes de fazer, pergunta"; e automaticamente no Gate 1 do megabrain ao abrir/retomar projeto e ao encarar uma ENTREGA.
---

# grelhar — esvaziar o briefing antes de produzir

**v1.0 · 260824.** Substitui o teto de "máx. 2 perguntas" do Gate 1. Base:
`grilling` do Matt Pocock (github.com/mattpocock/skills, MIT), adaptada ao
megabrain — a diferença é que aqui a grelha lê ESTADO/DECISOES/cérebro antes
de abrir a boca, e o resultado dela vira registro, não só conversa.

## A ideia em uma linha

As decisões de um trabalho formam uma **árvore**: cada decisão abre as que
dependem dela. Perguntar em ordem aleatória obriga o usuário a responder no
escuro. A grelha percorre a árvore por camadas até não sobrar nada assumido
em silêncio.

## Fronteira

**Fronteira** = toda decisão cujos pré-requisitos já estão resolvidos — as
perguntas que dá pra fazer AGORA sem chutar resposta que ainda não veio.

- Pergunte a **fronteira inteira numa rodada só**. Sem teto. Se a fronteira
  tem 9 perguntas, são 9 perguntas.
- Pergunta que depende de outra ainda aberta **nesta** rodada pertence à
  rodada seguinte, não a esta. Isso não é economia, é ordem.
- Cada resposta do usuário empurra a fronteira pra fora e abre a camada
  seguinte. Recalcule e pergunte de novo.
- Acaba quando a **fronteira esvazia**: todo galho visitado, nada assumido
  em silêncio.

## Antes da primeira rodada — o que já está respondido não vira pergunta

Isto é o que separa a grelha de um interrogatório preguiçoso. Antes de
escrever a rodada 1, leia (e nunca pergunte o que estiver lá):

| Onde | O que já está decidido |
|---|---|
| `ESTADO.md` · `HANDOFF.md` | fase, próximo passo, o que já foi feito |
| `DECISOES.md` | decisão fechada + a alternativa descartada. **Reabrir decisão fechada só se o usuário mandar** |
| `LICOES.md` · `licoes-megabrain.md` | erro que já aconteceu — vira restrição, não pergunta |
| `cerebro/wiki/` · `cerebro/pessoas/` | o que já se sabe do cliente, do mercado, da ferramenta |
| `dna/usuario/` | gosto, voz, hardware, jeito de trabalhar dele |
| `MEGABRAIN.md` | fases macro e regras de ouro do projeto |

Perguntar o que está escrito num desses arquivos é erro de Gate 0, não zelo.

## A regra de ouro: fato é seu, decisão é dele

| | Quem resolve | O que fazer |
|---|---|---|
| **Fato** — o que existe, quanto custa, que fonte tem no arquivo, quem já usa esse componente, o que o concorrente faz | **Você** | Abra, procure, pesquise. Se demora, **despache um subagente e siga perguntando o resto** — busca em andamento é pré-requisito não resolvido, então só os galhos que dependem dela esperam |
| **Decisão** — formato, tom, prioridade, o que pode aparecer, prazo, quem aprova | **Ele** | Pergunte e **pare**. Não decida por ele, não "assuma o mais provável" |

Nunca peça pro usuário um dado que você mesmo pode olhar. Nunca decida no
lugar dele o que é gosto ou limite.

## Formato da rodada

```
❓ **Q1 — <título curto da decisão>**: <o que precisa ser decidido, e por que
isso muda o trabalho. Pode ter alternativas nomeadas.>

➡️ <a resposta que você recomenda, com o motivo em meia linha>

---

❓ **Q2 — <título>**: <corpo>

➡️ <recomendação>
```

Regras do formato:

- **Sempre** venha com a recomendação. Pergunta sem palpite empurra o
  trabalho pro usuário — ele deve poder responder "1 sim, 2 muda pra X,
  3 tanto faz" e seguir a vida.
- A recomendação sai de evidência (o que ele fez nos últimos trabalhos, o
  que está no DNA, o que a lição diz), não de educação. Sem evidência,
  escreva `➡️ sem base pra recomendar — preciso da sua`.
- Título de pergunta nomeia a **decisão**, não o assunto: "Formato do deck",
  não "Sobre o deck".
- Uma decisão por pergunta. Duas coisas na mesma pergunta viram resposta
  ambígua.
- Numere de forma contínua entre rodadas (rodada 2 começa em Q4 se a 1
  terminou em Q3) — assim ele pode responder "Q7 muda" três mensagens depois.

## Quando a grelha roda

| Situação | Grelha |
|---|---|
| **Abrir ou retomar projeto** | Completa. Rodadas até a fronteira esvaziar. É o momento de esclarecer tudo — quantidade de pergunta aqui não é atrito, é o produto |
| **ENTREGA** (arquivo, peça, código, análise que sai da conversa) | Completa, com foco no que **fecha**: critério de aceite, o que não pode faltar, quem aprova, o que trava a finalização |
| **`/grelhar` no meio do caminho** | Completa, no escopo que ele apontou. Serve pra clarear e **continuar desenvolvendo** — não precisa estar no início de nada |
| **Rascunho / exploração** | Uma rodada curta, só a fronteira de nível 1. Explorar com trava é o oposto de explorar |
| **Pergunta, papo, "o que você acha"** | **Nenhuma.** Responda. Grelhar papo é o próprio slop |

Subir de rascunho pra entrega no meio do caminho é barato: abra a grelha na
hora em que virar entrega. Descer não existe.

## Escape

Ele pode cortar a qualquer momento: "toca", "chega", "tanto faz o resto",
`/chega`. Ao ser cortado:

1. **Não insista.** Nem "só mais uma".
2. Liste em uma linha cada decisão que ficou em aberto e **o que você vai
   assumir** em cada uma.
3. Grave essas suposições no `DECISOES.md` marcadas `[ASSUMIDO — não
   confirmado]`. Suposição não registrada é a que volta como retrabalho.

## Fechamento — o que a grelha entrega

Fronteira vazia (ou corte dele) → **antes de produzir qualquer coisa**:

1. **Espelho do entendimento**, curto: o artefato, o leitor, os 3 critérios
   verificáveis, a restrição dura, o contraexemplo genérico (o slop
   esperado). É o Gate 1 preenchido — a grelha não substitui o Gate 1, ela
   é o método dele.
2. **Confirmação explícita** dele. Fronteira vazia não é autorização.
3. **Registro**: decisões novas em `DECISOES.md` (com a alternativa
   descartada); fase e próximo passo no `ESTADO.md`; fato sobre o mundo
   (cliente, mercado, ferramenta) vai pro cérebro via `/ingerir`, não pro
   corpo da conversa.

Sem o passo 3 a grelha vira conversa jogada fora: a próxima sessão pergunta
tudo de novo.

## Como isso dá errado

- **Rodada gigante com tudo misturado** — perguntar o que depende do que
  ainda não foi respondido. O usuário responde no escuro e a árvore
  desanda.
- **Pergunta sem recomendação** — vira formulário. Ele te contratou pra ter
  opinião.
- **Perguntar fato** — "qual o caminho da pasta?", "que fonte tem no
  arquivo?". Isso é você não ter aberto o arquivo.
- **Grelhar papo** — ele pergunta as horas e leva três perguntas numeradas.
  Melhor jeito de fazer ele parar de usar o megabrain.
- **Não registrar** — grelha linda, `DECISOES.md` intacto. Trabalho perdido.
- **Reabrir decisão fechada** — o `DECISOES.md` existe pra isso não
  acontecer.

## Crédito

Método derivado de `grilling` / `grill-me` de Matt Pocock
(github.com/mattpocock/skills, licença MIT). Adaptações do megabrain: leitura
prévia de ESTADO/DECISOES/LICOES/cérebro/DNA, tabela de quando roda, escape
com suposições registradas, e fechamento gravando em DECISOES/ESTADO/cérebro.
