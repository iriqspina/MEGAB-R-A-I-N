# Quando a entrega vira código: roteamento pra fora do Duplo Diamante

Peça estática — deck, print, imagem, 3D, motion sem DOM — fica inteira em
`260810_design-projects.md` + Gate 4 (anti-slop visual). Este arquivo cobre
o caso em que a entrega **vira código que roda num navegador ou app**:
landing page, dashboard, app UI, formulário, componente.

## Por que sai do protocolo de design puro

Peça estática se avalia por captura de tela. Interface em código se avalia
em execução: estado, breakpoint, foco de teclado, erro de rede — nenhum
desses aparece num PNG. Aplicar só o Gate 4 (anti-slop visual) nessa entrega
audita a composição e ignora o comportamento, que é metade do produto.

## Os 4 modos de superfície

Define o que "bom" significa **antes de qualquer pixel** — o modo é da
superfície, não do produto (a landing de uma ferramenta é Persuade; a
documentação de uma marca é Read):

| Modo | Objetivo | Exemplo |
|---|---|---|
| **Persuade** | O visitante decide e age | Landing page, página de marketing |
| **Operate** | Completa uma tarefa | Dashboard, ferramenta interna, admin |
| **Read** | Entende algo | Documentação, conteúdo editorial |
| **Experience** | Está dentro da obra | Site autoral, portfólio |

## Piso de craft (número, não adjetivo)

- Medida de linha: 65–75ch no corpo de texto.
- Display: no máximo 6rem.
- Tracking: não abaixo de -0.04em.
- Line-height: 1.5–1.7 no corpo.
- Contraste: 4.5:1 (texto normal) e 3:1 (texto grande) — WCAG AA.
- Espaço acima do heading maior que o espaço abaixo dele.
- Sombra com offset e blur — halo colorido de offset zero é decoração, não
  profundidade.

## Checagem determinística antes da inspeção no olho

Rode primeiro o que roda como script — lint de UI, detector de contraste,
de heading pulado, de linha longa — **sem** deixar a crítica subjetiva ver o
resultado antes. O número ancora o julgamento; se a crítica vier primeiro,
ela racionaliza o que já decidiu gostar.

## Roteamento prático

1. A entrega tem estado, interação ou responde a breakpoint? → Este arquivo
   governa o craft; `260810_design-projects.md` ainda governa a fase (em
   qual estágio do Duplo Diamante o projeto está).
2. Pixel e papel sem DOM → fica só em `260810_design-projects.md`.
3. Se o ambiente tiver uma skill dedicada a design responsivo/UI de app
   (ex.: uma skill de "frontend design"), use-a para a implementação —
   este arquivo define o que medir, não como codificar.

## Como isso costuma dar errado

1. **Avaliar interface em código pela screenshot.** Meça em execução:
   teclado, erro, estado vazio, loading.
2. **Rodar craft num problema ainda não enunciado numa frase falseável.**
   Produz superfície bem-executada resolvendo a coisa errada — Gate 1
   (enquadrar) vem antes de qualquer pixel.
3. **Confundir o modo do produto com o modo da superfície.** Um SaaS
   Operate pode ter uma landing Persuade — craft muda por página, não por
   produto inteiro.
