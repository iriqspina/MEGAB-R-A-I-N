---
name: reacao-genuina
description: Analisa layout, overlay, controle e fluxo pela ótica da reação genuína — o que o humano sente nos primeiros instantes, antes de racionalizar. Minimiza leitura obrigatória, maximiza percepção direta (forma, cor, movimento, área de clique, hover) e converte estado em imagem. Aprende por casos registrados (ciclo RSI plugado ao laboratório de processos). Irmã da filtro-percepcao (que cuida do que o app diz por texto).
---

# reacao-genuina — desenhar para o instante antes do pensamento

**v1 · 261022**. Nasceu de um pedido do <USUARIO> (Bubble): tornar o card do modo
assistir clicável por inteiro, tirar o botão "Voltar pra sala", dar hover na área
livre e desenhar bolhas de participantes — tudo justificado por uma ótica dele:
**o humano vê, sente (sem controle), só depois racionaliza, triangula com o que
acredita e então reage.** O design que acerta é o que informa e guia dentro dessa
janela pré-racional, sem cobrar leitura. Fonte literal:
`memoria/cerebro/raw/261022_pedido-skill-reacao-genuina.md`.

## O modelo que sustenta tudo

**Cadeia da reação:** ver → sentir (involuntário) → racionalizar → triangular
com crenças → reagir racionalizado. A janela entre *ver* e *racionalizar* é
curta e é aí que o layout age: estímulo percebido direto (forma, cor, movimento,
área) informa sem custo; texto cobra racionalização e atrasa a reação.

Traduções para o vocabulário da área (para triangular com pesquisa, não para
substituir a ótica do <USUARIO>): Sistema 1 × Sistema 2 (Kahneman); design
visceral → comportamental → reflexivo e affordance (Norman); carga cognitiva
extrínseca (Sweller); percepção pré-atentiva de cor/forma/movimento (Healey);
lei de Fitts (alvo maior e mais perto = clique mais fácil). TDAH e ansiedade
encurtam a paciência de varredura: se precisa ler frase para entender, parte do
público já perdeu o estímulo.

## Quando usar (e quando não)

- **Usar:** desenhar ou revisar layout, overlay, card, controle, navegação, peça
  interativa — qualquer coisa em que o objetivo é o usuário final entender e agir
  rápido. Aperfeiçoar proposta visual antes de codar (barato mudar no papel).
- **Não usar:** documento, relatório, texto de estado/erro/telemetria (isso é a
  `filtro-percepcao`), decisão de negócio, conteúdo cujo objetivo É a leitura
  (artigo, contrato, brief). Pedido explícito de densidade informacional também
  dispensa. *Não é para usar sempre e em tudo* (pedido literal do <USUARIO>).

## Os 9 princípios (v1 — derivados do caso semente, sujeitos ao ciclo de casos)

1. **Premissa do leigo.** Desenhar para quem não sabe nada. Se o layout precisa
   de explicação para funcionar, o layout ainda não acabou.
2. **Percepção antes de leitura.** Informação essencial deve ser capturada sem
   frase. Texto é fallback para quem quer confirmar — nunca o veículo primário.
3. **O contêiner é o alvo.** Maximizar área de clique: a superfície inteira vira
   botão, com zona central livre para clicar sem mirar (Fitts). Controles ficam
   fora dessa zona e continuam 100% funcionais.
4. **Feedback vivo ensina.** Hover, cursor, elevação, brilho: o elemento conta
   que é clicável no momento em que o ponteiro chega — descoberta pelo corpo,
   não pela leitura.
5. **Estado vira imagem.** Pessoa = avatar; câmera ligada = vídeo visível; tela
   compartilhada = janela própria; nada = foto de perfil. Nunca descrever por
   rótulo o que uma imagem já mostra.
6. **Presença retraível.** Informação social rica não rouba o fundo da página:
   expande sob demanda, colapsa sozinha, e o estado retraído continua claro.
7. **Variação com propósito.** Controle novo pode ter estilo diferente do padrão
   existente para manter curiosidade — desde que percebido sem texto e coerente
   com a família visual do produto.
8. **Legibilidade ganha de estilo.** Transparência, blur e efeito que degradam
   a leitura do conteúdo caem. Ver o amigo > estética translúcida.
9. **Um golpe de olho.** Hierarquia sobrevive a varredura curta: o dado que
   importa é o maior/percebido primeiro; detalhe vem recolhido.

## Checklist de análise (a ordem é a ordem do olhar)

1. **Primeiro instante** (~meio segundo, sem ler): o que o humano sente? Qual
   forma/cor/movimento salta?
2. **Custo de leitura:** quantas frases ele precisa ler para saber o que fazer?
   Como chegar a zero?
3. **Alvo:** onde o clique vai cair? A área pode ser o contêiner inteiro com
   centro livre? Controles preservados e funcionais?
4. **Descoberta:** como ele percebe que é clicável sem ler? (hover, cursor,
   elevação)
5. **Estado por imagem:** que informação hoje escrita pode virar forma/foto/
   vídeo? (regra de estado das bolhas: câmera→vídeo; tela→perfil+tela; ambos→
   os dois; nada→perfil)
6. **Retração:** o que não pode roubar o fundo? Como expande/colapsa? O estado
   retraído ainda informa?
7. **Varredura curta:** TDAH/ansiedade passam? Hierarquia de um golpe de olho?
8. **Legibilidade:** algum efeito (transparência, blur) está custando a leitura?
9. **Nada quebrou:** ao mover/remover elementos, tudo continua funcionando?
   Tamanho do contêiner preservado quando o pedido pediu estabilidade?

## Ciclo de aprendizado contínuo (RSI, v1 — estado `ajustar`)

Objetivo do <USUARIO>: "aprender continuamente e ir se otimizando, até ficar
estável e com qualidade satisfatória". Mecânica:

1. **Toda aplicação registra um caso** em `motor/skills/reacao-genuina/casos/`
   (`caso-NNN-<slug>-<YYMMDD>.md`): contexto, o que foi proposto, **previsão de
   percepção** (o que deveria melhorar), reação humana **literal** (quando
   houver — gosto é registrado à parte, nunca inferido), resultado
   (aprovado/ajustado/rejeitado/pendente) e lição.
2. **Métricas por caso** (contáveis do próprio design, sem laboratório):
   frases-obrigatórias antes→depois; área de alvo relativa (% do contêiner);
   feedback pré-clique (tem/não); estados visuais convertidos em imagem; defeitos
   apontados por revisão independente.
3. **Lição vira princípio:** confirmação → reforça; contradição → ajusta ou cria
   princípio novo (versionado: "v2 · 26MMDD · motivo"). Negativo fica registrado,
   não é apagado.
4. **Promoção/reversão** segue o laboratório de processos (EXP-002): 2 rodadas
   na mesma direção, ou 1 + aprovação explícita do <USUARIO>.
5. **Estabilidade:** 3 casos consecutivos sem mudança de princípio e com reação
   positiva → skill marca estado `estável`; casos continuam sendo registrados,
   revisão passa a ser amostral.
6. **Elos:** lição transversal vira `registrar-licao`; problema de frase/estado
   vira `filtro-percepcao`; experimento-mestre é
   `motor/laboratorio-processos/experimentos/EXP-002_reacao-genuina-rsi.json`.

## Caso fundador (Bubble, 261022)

Card do modo assistir (overlay flutuante): botão "Voltar pra sala" ocupava o
centro; mic e câmera ficavam à esquerda, separados do botão de sair. Proposta:
remover o botão texto, tornar o corpo do card clicável (mesmo comprimento no
eixo X, centro livre), mover mic+câmera para a direita alinhados ao botão de
desconexão, hover na área livre; bolhas de participantes retráteis com regra de
estado por imagem e sem transparência. Detalhe em
`casos/caso-001-bubble-overlay-261022.md` e no relatório da tarefa
(`Bubble/00_PARA-VOCE/10_Design-thinking/261022_REACAO-GENUINA-OVERLAY.html`).
