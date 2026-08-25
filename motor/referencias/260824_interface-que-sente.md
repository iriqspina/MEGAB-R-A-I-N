# Interface que sente — detalhe que vira critério verificável

Origem: `make-interfaces-feel-better` do ECC (github.com/affaan-m/ECC, MIT,
© Affaan Mustafa; lá creditado a um PR da comunidade de `linus707`). Traduzido
e adaptado ao megabrain em 260824 — cortado o que era específico de Tailwind/
macOS, somadas as regras da casa (tema, token de estado, Pico).

**Pra que serve:** no Gate 1, "ficar bonito" não é critério. Isto aqui vira os
**3 critérios verificáveis** de qualquer peça de interface. No Gate 4/5, vira
checklist de auditoria. Abra quando o passo pedir — não leia por hábito.

---

## 1. Raio concêntrico

Superfícies arredondadas aninhadas e próximas:

```
raio externo = raio interno + respiro (padding)
```

Card com `padding: 16px` e botão interno de `radius: 8px` → o card quer
`radius: 24px`. Se o respiro é grande demais, trate as camadas como superfícies
separadas em vez de forçar a conta. O alvo é **coerência óptica**, não devoção
à fórmula.

**Sinal de slop:** o mesmo `border-radius` em pai e filho.

## 2. Alinhamento óptico

Centro geométrico ≠ centro visual. Ícone de play, seta, estrela, qualquer
forma assimétrica pede deslocamento de 1–2px. Corrija no SVG quando der;
senão, `padding`/`margin` no elemento.

## 3. Borda × sombra — cada uma pro seu motivo

- **Borda**: separar superfícies e marcar foco (anel de foco).
- **Sombra em camadas**: dar profundidade a card, botão, dropdown, popover.

Sombra tem que ser transparente e discreta o bastante pra funcionar em fundo
claro e escuro. Uma sombra só, densa, é sombra de template.

**Sinal de slop:** `box-shadow: 0 4px 6px rgba(0,0,0,.1)` — é o default do
Bootstrap/Tailwind, aparece em metade da internet.

## 4. Quebra de texto e número

- `text-wrap: balance` em título e rótulo curto.
- `text-wrap: pretty` em corpo curto/médio, legenda, item de lista.
- Nenhum dos dois em prosa longa, código e `<pre>`.
- `font-variant-numeric: tabular-nums` em contador, cronômetro, preço, tabela
  e qualquer número que **atualiza** — sem isso o número dança na tela a cada
  dígito.

## 5. Contorno em imagem

Imagem sem contorno derrete na superfície quando as bordas têm luminância
parecida.

```css
img { outline: 1px solid rgba(0,0,0,.1); outline-offset: -1px; }
@media (prefers-color-scheme: dark){ img { outline-color: rgba(255,255,255,.1) } }
```

Contorno neutro (preto ou branco com alfa). **Nunca tinja o contorno com a cor
da marca** — vira moldura, não acabamento.

## 6. Movimento

- **Transição CSS** pra mudança de estado: ela consegue mudar de alvo no meio
  se o usuário mudar de ideia. **Keyframes** só pra entrada encenada ou loop de
  carregamento.
- **Entrada**: opacidade + `translateY` pequeno, às vezes blur.
- **Saída**: mais curta e mais quieta que a entrada — ~150ms.
- **Toque**: `scale(.96)` pra botão tátil, com jeito de desligar quando
  distrai.
- **Troca de ícone**: cross-fade com opacidade + escala + blur, nunca
  `visibility` piscando.

## 7. Escopo de transição

Nunca `transition: all` — ela anima propriedade que você não pediu e mata o
desempenho em `layout`/`paint`.

```css
.botao{
  transition-property: transform, background-color, box-shadow;
  transition-duration: 150ms;
  transition-timing-function: ease-out;
}
```

`will-change` só pra tremida de primeiro quadro, e só em `transform`,
`opacity`, `filter`. Nunca `will-change: all`.

## 8. Área de toque

Controle interativo: mínimo **40×40px**, ideal **44×44px**. Ícone menor que
isso → expanda com pseudo-elemento, sem deixar as áreas expandidas se
sobreporem.

## 9. Estados que quase sempre faltam

`hover` · `focus-visible` (anel visível, nunca `outline:none` órfão) ·
`active` · **carregando** · **vazio** · **erro**. Peça sem estado vazio é peça
que não foi testada com dado real.

---

## Regras da casa (não são do ECC — são do megabrain)

- **Cor sai do TEMA**, não da mecânica. `#hex` solto dentro de mecânica visual
  é bug, não escolha (`modelos/visuais/temas/`, cascata `:not()` padrão Pico).
- **Nunca `!important`.**
- **Token de estado ≠ hierarquia.** `--ok/--warn/--signal` marcam estado.
  Rótulo e eyebrow são `--ink-faint`. Trocar um pelo outro faz a peça mentir.
- **Rótulo tem que ler como título**: linha própria, corpo maior que o texto,
  separador e respiro embaixo. Rótulo inline colado no texto é lido como
  ênfase do começo da frase.
- **Planta do relatório é fixa** (D/W/E/C/R). Slot vazio não some.

---

## Como isso vira critério no Gate 1

Não escreva "vai ficar polido". Escreva 3 linhas testáveis, tiradas daqui.
Exemplo pra um card de painel:

1. Raio do card = raio do botão interno + o respiro (medir, não olhar).
2. Nenhum `transition: all` e nenhum `!important` no arquivo final.
3. Número que atualiza usa `tabular-nums`; card tem estado vazio desenhado.

## Como isso vira auditoria no Gate 4/5

`python bin\mb-slop-visual.py <arquivo>` pega a parte mecânica (transição
solta, sombra de template, gradiente de estoque, grade uniforme, tudo
centralizado, CTA genérico, `!important`, hex solto). O resto — alinhamento
óptico, raio concêntrico, estado vazio — é olho, e é você.

**Formato do relato**, quando você audita uma peça: linha por princípio, antes
e depois, com caminho de arquivo. Omita o que checou e não mudou.

| Princípio | Antes | Depois |
|---|---|---|
| Raio concêntrico | pai e filho com 8px | pai 24px = 8 + 16 de respiro |
| Número tabular | contador dança | `tabular-nums` no `.valor` |
| Escopo de transição | `transition: all` | `transform, background-color` |
