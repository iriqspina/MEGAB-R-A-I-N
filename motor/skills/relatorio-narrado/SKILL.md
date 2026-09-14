---
name: relatorio-narrado
description: Transforma qualquer relatório, relação ou estado de projeto em uma apresentação HTML narrada (voz + legenda + animações) que o <USUARIO> assiste como PowerPoint comentado. Use quando ele pedir "apresentação", "vídeo comentado", "explica visualmente", "com animações", "com voz", "pra entender melhor visualmente", "templatiza esse visual de relatório" — ou quando a entrega for um retrato de estado com 6+ fatos que ele precisa fixar. Modelo pronto em motor/modelos/relatorios/260914_narrado/.
---

# relatorio-narrado — relatório que se assiste

**v1.0 · 260914.** Nasceu do pedido do <USUARIO> após a entrega
`Portfolio/00_PARA-VOCE/260914_RELACAO-GERAL-APRESENTACAO/`: *"queria que tivesse
uma voz que segue enquanto a animação rola... penso mais num feedback como vídeo
ou como powerpoint comentado do que só palavras, ajuda a fixar"* — e depois
*"templatiza isso, coloca no megabrain"*.

## Por que existe

<USUARIO> tem TDAH e decide melhor com áudio+visual juntos. Um relatório em .md
pede leitura linear; o deck narrado dá o TL;DR falado com legenda sincronizada,
animação de entrada por elemento e ritmo controlado por ele (tocar tudo, tocar
tela, ou navegar mudo). A primeira aplicação teve parecer de revisão aprovado
nos fatos ("aprovar com ajustes" — Fable médio, 260914) e os bugs de modelo já
foram corrigidos NA FONTE daqui.

## Quando NÃO usar

1. Papo rápido, resposta N0/N1 — texto no chat basta.
2. Documento canônico do projeto (ESTADO/HANDOFF/DECISOES) — esses são fonte
   de verdade em texto; o deck é DERIVADO de leitura, nunca substitui.
3. Peça visual de identidade (o Figma manda no visual do produto; o deck é
   artefato interno de entendimento).
4. Algo que precise ser editável por terceiros — gere o .md normal junto.

## Os 7 passos

0. **Escolha a variante ANTES de começar** (regra 260914, pedido do <USUARIO>:
   "template pra baratear"):
   - **LEVE (padrão do dia adia)** — `MODELO-relatorio-narrado-LEVE.html`:
     1 arquivo único, narração pela voz do PRÓPRIO navegador (Web Speech,
     grátis, offline), sem mp3, sem TTS cloud, sem cota de modelo. Se o
     navegador não tiver voz pt-BR, vira leitura cronometrada (legenda +
     avanço automático). Custo: zero. Use por padrão, inclusive em rascunhos
     pra ele julgar visual.
   - **PREMIUM (exceção)** — `MODELO-relatorio-narrado.html` + mp3 TTS cloud:
     voz de qualidade gravada. Só quando: a entrega é decisão importante que
     ele vai rever mais de uma vez, vai pra terceiros, ou a voz do sistema
     decepcionou na audição. Nesse caso anote o custo (9 telas ≈ 225 s de
     TTS + eventuais runs de revisão).
1. **Roteiro primeiro.** Uma fala por tela, 15–35 s cada (uma frase de tese +
   2–4 fatos + o que decide). Linguagem leiga: termo técnico traduzido NA HORA
   ("deploy (publicação)"). Números por extenso na fala ("cento e oitenta e
   nove", "H zero um") para o TTS não engolir. Total recomendado: 2–5 min.
2. **(Só PREMIUM) TTS.** `speech_synthesize` do video-agent-kit (provider
   cloud_tts), `language: pt-BR`, `output_format: mp3`, um arquivo por tela:
   `narr_01.mp3...narr_NN.mp3` na MESMA pasta do HTML. Registrar durações.
   Na LEVE, este passo não existe — o texto vive só no array `NARR`.
3. **Montar do modelo.** Copiar o MODELO da variante escolhida e preencher os
   blocos `═══ EDITE`. O array `NARR` recebe EXATAMENTE o texto da fala
   (é a legenda; na PREMIUM, o mesmo texto dos mp3).
4. **3 temas de cor** editáveis nos tokens do `:root` (se o projeto tiver
   modos/tokens próprios, usar os reais — ex.: Portfolio usa claro/roxo/escuro
   de `260822_modos-cor_tokens.md`).
5. **Conferência técnica mínima** (checklist das lições abaixo) e abrir no
   navegador por `cmd //c start` na sessão.
6. **Entrega:** PREMIUM = pasta inteira (HTML + mp3 + LEIA-PRIMEIRO); LEVE =
   o HTML único já basta (LEIA-PRIMEIRO de 3 linhas). Tudo em `00_PARA-VOCE/`
   do projeto.
7. **Registro:** entrada no ESTADO.md com variante usada, hash do HTML,
   duração total (PREMIUM) e o fato de ser leitura-only.

## Regras de qualidade (herdadas da revisão aprovada)

1. **Autocontido e offline:** sem CDN, sem fonte externa, sem rede. Abre por
   duplo clique em `file://`.
2. **Autoplay só por clique:** o "TOCAR TUDO" e o botão 🔊 são os únicos
   disparadores de áudio (política de autoplay dos navegadores).
3. **Dois controles distintos:** `G`/TOCAR TUDO = modo guiado (narra e avança
   sozinho); `N`/🔊 = narra só a tela atual — e DURANTE o guiado, `N` devolve
   o controle manual (para tudo, desliga guiado). Nunca deixe o usuário preso.
4. **Legenda sincronizada** com o texto idêntico ao áudio; a voz reserva do
   navegador (fallback Web Speech, pt-BR) também mostra legenda e usa o índice
   da tela CERTA (não o índice "atual" — lição T2).
5. **`prefers-reduced-motion`** respeitado (animações viram corte seco).
6. **TL;DR na capa** e toda tela responde "o que muda / onde decidir".
7. **Nomes de classe únicos** — conferir colisão antes de fechar (lição T1:
   duas `.legenda` no mesmo arquivo esconderam os números do gráfico).

## Lições pagas (não repita)

1. **Classe CSS duplicada** (T1): a legenda fixa da narração e a legenda do
   gráfico usavam `.legenda`; a regra `position:fixed` engolia o bloco do
   gráfico. No modelo, gráfico usa `.leg-donut`.
2. **Fallback de voz chamado 2×/tela errada** (T2/T3): o evento `error` do
   `<audio>` + o `.catch()` do `play()` disparavam juntos. No modelo há só o
   `.catch()` com guarda `if(!fallbackAtivo)` e o índice `i` capturado.
3. **Revisão por agente com fonte grande:** o motor V6 só entrega o pacote
   congelado; HTML >20 KB não entra como `--source` e o revisor NÃO lê disco.
   Para revisar um deck, EMBUTA o HTML integral no `context` do brief desde a
   primeira run (custou 2 runs queimadas em 260914).
4. **Cota:** antes de despachar revisão, medir `dados/orcamento_ia.json`;
   semana Claude em `desacelerar` = no máximo uma tentativa cirúrgica.

## Variações úteis do modelo

- **LEVE sem voz:** se nem a voz do navegador existir, o modo guiado vira
  leitura cronometrada sozinho (legenda + avanço) — já embutido no modelo.
- **Dashboard vivo:** os contadores (`data-count`) e as barras (`data-bar`)
  aceitam números reais medidos na hora; refeche o HTML por script na entrega.
- **Vídeo de verdade:** se ele pedir MP4, renderizar as telas + mp3 por
  ffmpeg depois — o roteiro e os assets são os mesmos (comece da PREMIUM).
