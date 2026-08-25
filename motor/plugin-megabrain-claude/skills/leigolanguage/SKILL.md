---
name: leigolanguage
description: Explica uma decisão técnica para quem não é programador poder decidir — dá a referência que falta usando o mundo que a pessoa já domina, mostra a consequência concreta de cada caminho e diz o que dói se der errado. Use quando o usuário digitar /leigolanguage, disser "não entendi", "explica melhor", "explica como se eu fosse leigo", "fala em português", "tô perdido", "e daí?", "isso é bom ou ruim?"; e automaticamente sempre que você for pedir uma decisão que depende de um conceito que ele não usou primeiro.
---

# leigolanguage — explicar pra pessoa poder decidir

**v1.0 · 260825.** Nasceu de um pedido do <USUARIO>: *"como sou leigo, tá
chegando num ponto que você manja mais, e pra eu decidir você tem que me
explicar muito bem explicado."*

## A regra que sustenta tudo (leia antes de qualquer técnica)

**Explicar bem não é falar como se a pessoa fosse burra.**

Ele pediu de brincadeira "como se eu fosse um idiota de 5 anos". Não faça
isso. Quem pede isso está dizendo *"eu não tenho o vocabulário, me dá ele"* —
não *"me trate como criança"*. A diferença importa por dois motivos:

1. **Infantilizar tira informação.** "O git é tipo um baú mágico" não deixa
   ninguém decidir nada. Ele precisa decidir, não se distrair.
2. **Ele não é leigo em pensar.** É designer: raciocina em sistema, hierarquia,
   versão, arquivo linkado, camada, herança. Falta o *nome* das coisas do
   outro domínio, não a capacidade de operar com elas.

O alvo é: **em 60 segundos ele sabe o suficiente pra escolher, e sabe o que
acontece se escolher errado.**

## O método — 5 partes, nessa ordem, sempre

### 1. O que é — traduzido pro mundo dele

Uma frase. Use algo que ele **já usa todo dia**: Illustrator, Photoshop,
Figma, WordPress, InDesign, gravar/mixar música, papel impresso.

> ❌ "`.gitignore` é um arquivo que define exclusões do controle de versão."
> ✅ "`.gitignore` é a lista do que **não** entra no backup. Igual quando você
> manda um .ai pro cliente e não manda a pasta de Links inteira junto."

**Marque que é analogia e diga onde ela vaza.** Analogia sem aviso vira modelo
mental errado, e modelo errado custa mais caro que ignorância:

> "A comparação quebra num ponto: no Illustrator o Link some se você mover a
> pasta. No git, o que ficou de fora simplesmente nunca foi guardado — não
> tem link pra quebrar, tem arquivo que não existe no histórico."

### 2. Como está hoje — medido, não suposto

Estado real, com número. Sem isso ele decide no vácuo.

> "Hoje: 418 arquivos entram no backup, 28 MB ficam de fora, e o `.env` com
> suas 4 chaves de API está entre os que ficam de fora."

### 3. Os caminhos — o que MUDA na vida dele, não no código

Duas ou três opções nomeadas. Para cada uma: **o que ele ganha e o que perde
em coisa que ele sente**, não em propriedade técnica.

> **A** — versiona seus dados pessoais: se uma IA apagar 158 lições sem
> querer, você recupera com um comando. Custa: se um dia você publicar essa
> pasta por engano, seus dados vão junto.
> **B** — não versiona: publicar por engano é inofensivo. Custa: perdeu, perdeu.

### 4. O que dói se der errado — e quanto é reversível

O eixo que ele mais usa pra decidir, e o que quase nunca aparece na explicação
técnica. Seja específico sobre **quanto tempo** e **se dá pra desfazer**.

> "Escolher A e se arrepender: 2 minutos, é editar uma linha.
> Escolher B e se arrepender: você só descobre no dia que perder alguma coisa,
> e aí não tem volta."

### 5. A recomendação — com o porquê em uma linha

Sempre. Pergunta sem palpite empurra o trabalho pra ele, que é exatamente o
que ele não consegue fazer nesse assunto.

> "➡️ **A.** O motivo de existir esse backup é não perder lição de novo. B
> deixa de fora justo o arquivo que motivou criá-lo."

## Regras de escrita

| Faça | Não faça |
|---|---|
| Use o termo técnico **e** defina na mesma frase, uma vez | Esconder o termo — ele precisa reconhecer da próxima vez |
| Uma ideia por linha | Parágrafo denso |
| Número com unidade que ele sente (MB, minutos, "quantas vezes") | "significativo", "considerável", "otimizado" |
| Nome de arquivo entre crases quando ele for procurar | Caminho longo no meio da frase |
| Dizer "não sei" quando não mediu | Preencher com plausível |

**Ensine o termo, não o esconda.** Escrever "o `.gitignore` (a lista do que
não entra no backup)" faz ele sair sabendo a palavra. Escrever só "a lista do
que não entra" mantém ele dependente de tradução pra sempre. Esconder
vocabulário é a versão educada de infantilizar.

## Quando roda

| Situação | Roda? |
|---|---|
| Você vai **pedir uma decisão** que depende de um conceito que ele não usou primeiro | **Sim, automático.** Não espere ele pedir |
| Ele digita `/leigolanguage`, diz "não entendi", "e daí?", "isso é bom ou ruim?" | **Sim**, sobre a última coisa que você disse |
| Ele já usou o termo corretamente numa mensagem anterior | **Não.** Já tem a referência; repetir é que é condescendente |
| Ele pediu a resposta curta, ou é papo | **Não** |

Um jeito rápido de checar: **se a pergunta que você ia fazer só faz sentido
pra quem já sabe a resposta, ela precisa desta skill antes.**

## Formato de saída

```
🟢 O QUE É — <uma frase, no mundo dele> (isso é uma comparação; ela
   quebra em: <onde vaza>)

📍 COMO ESTÁ HOJE — <estado medido, com número>

🔀 OS CAMINHOS
   A — <o que muda pra ele> · custa: <o que perde>
   B — <o que muda pra ele> · custa: <o que perde>

💥 SE DER ERRADO — A: <dor + é reversível?> · B: <dor + é reversível?>

➡️ RECOMENDO <A ou B> — <o porquê em uma linha>
```

Sem os emojis se o ambiente não os renderizar: os rótulos em CAIXA já separam.

## Para agentes que não são o Claude

Esta skill não depende de ferramenta nenhuma. Se você é Kimi, GPT, Gemini,
Codex, Qwen local ou qualquer outro:

1. **Não** procure ferramenta com nome específico. Use o que você tem pra ler
   arquivo e medir estado — o nome muda por agente, o passo não.
2. A parte 2 (COMO ESTÁ HOJE) **exige medir**. Se você não consegue ler o
   disco nesta sessão, escreva `[NÃO MEDIDO]` no lugar do número em vez de
   estimar. Número inventado numa explicação pra leigo é pior que ausência:
   ele não tem como conferir.
3. A analogia sai do mundo **dele** (design gráfico e digital, Adobe, Figma,
   WordPress, impressão, música), não do seu exemplo favorito de programação.

## Como isso dá errado

- **Virar baby talk.** "Pensa no git como um robozinho amigo." Ele para de te
  levar a sério e a decisão continua não tomada.
- **Analogia sem vazamento declarado.** Ele constrói o modelo errado e decide
  certo hoje, errado no mês que vem.
- **Explicar e não perguntar.** A skill existe pra ele DECIDIR. Termine com a
  pergunta, não com a aula.
- **Explicar o que ele já sabe.** Ele é designer sênior: hierarquia, versão,
  fonte × cópia, herança e template são o dia dele. Traduzir *isso* ofende.
- **Explicação longa.** TDAH: passou de uma tela, ele perdeu. Se não coube,
  o problema é que você está explicando três decisões de uma vez — separe.

## Exemplo completo, real (260825)

> 🟢 **O QUE É** — "trava por escopo" é um bilhete de "estou mexendo neste
> arquivo" que as IAs deixam uma pra outra. Igual quando você e um freela
> mexem no mesmo Figma e um avisa "tô na página 3, não encosta".
> *A comparação quebra em: no Figma você VÊ o cursor do outro. Aqui ninguém vê
> nada — se o bilhete não for lido, o segundo simplesmente escreve por cima.*
>
> 📍 **COMO ESTÁ HOJE** — o bilhete existe (`HANDOFF.md`, campo `TRAVADO_POR`),
> mas **só 1 script lê ele** e 10 scripts escrevem sem olhar. Hoje de manhã um
> agente escreveu com o bilhete marcando "livre".
>
> 🔀 **OS CAMINHOS**
> **A** — um bilhete por arquivo, e os scripts passam a ler antes de escrever.
> Custa: mexer em 10 scripts.
> **B** — cada IA escreve num arquivo só dela e um script junta depois. Custa:
> é obra maior, e você passa a ter arquivos soltos até o script rodar.
>
> 💥 **SE DER ERRADO** — A: uma trava esquecida trava você mesmo; conserto em
> segundos, é apagar uma linha. B: se o script de juntar falhar, a decisão fica
> num arquivo que ninguém lê — some da mesma forma, só que mais devagar.
>
> ➡️ **Recomendo A.** Agora que existe git, decisão perdida dá pra recuperar —
> então você não precisa da solução cara. A resolve 90% por 10% do trabalho.
