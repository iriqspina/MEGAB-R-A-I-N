# Anti-slop: detecção e reparo

## O que é slop

Texto (ou imagem) que passa numa leitura rápida e não sobrevive a uma segunda.
Sintomas: repetitivo, previsível, genérico, reconhecível como saída de máquina.
Não é erro factual — é ausência de escolha.

**Causa raiz técnica**: modelos de linguagem colapsam para os padrões de maior
probabilidade. Slop é o modo default. Evitá-lo exige restrição explícita, não
boa vontade.

**Regra de eficácia**: prompt sozinho resolve ~80% dos casos. Os 20% restantes
exigem uma passada de validação separada com reparo limitado. Por isso o Gate 4
(Auditar) é etapa própria, não adjetivo no prompt inicial.

---

## Camada 1 — Léxico

### Inglês (marcadores fortes)
```
delve, tapestry, testament to, in the ever-evolving landscape, navigate the
complexities, unlock, harness, leverage, robust, seamless, game-changer,
at its core, furthermore, moreover, in conclusion, let's dive in,
the world of, boasts, crucial, pivotal, underscores, beacon, realm,
myriad, plethora, meticulous, elevate, empower, cutting-edge, revolutionize,
paradigm shift, holistic, synergy, curated, bespoke, streamline,
transformative, unparalleled, seamlessly integrate, foster, spearhead
```

### Português (marcadores fortes)
```
no mundo de hoje, no cenário atual, cada vez mais, de forma eficaz,
é importante ressaltar, vale destacar, cabe ressaltar, em suma,
nesse sentido, dessa forma, por fim, dito isso, revolucionar,
potencializar, alavancar, robusto, impactante, entregar valor,
jornada (sem trajeto real), ecossistema (sem sistema real),
curadoria (sem critério declarado), de forma holística, sinergia,
assertivo (usado como "certeiro"), imersivo, disruptivo, escalável (vazio),
solução completa, ponta a ponta, fazer a diferença, nível de excelência
```

### Como reparar
**Não troque por sinônimo.** `alavancar` → `usar` continua slop porque a frase
inteira era vazia. Reescreva a frase respondendo: *o que exatamente acontece
aqui?*

- ❌ "Vamos alavancar o design system para potencializar a entrega."
- ⚠️ "Vamos usar o design system para melhorar a entrega." (menos feio, ainda vazio)
- ✅ "O design system corta ~3 dias de handoff porque o dev não precisa medir espaçamento."

---

## Camada 2 — Estrutura

| Padrão | Por que é slop | Reparo |
|---|---|---|
| "Não é apenas X — é Y" | Antítese que finge profundidade sem afirmar nada | Afirme Y direto |
| Regra de três compulsiva ("rápido, simples e poderoso") | Ritmo decorativo; o 3º item quase sempre é enchimento | Corte para 1 ou 2 reais |
| Travessão em todo parágrafo | Muleta rítmica que apaga a variação de frase | Máx. 1 a cada 3 parágrafos |
| Parágrafo-resumo no fim | Redundância; o leitor acabou de ler | Corte |
| `**Rótulo:** frase` em toda bullet | Formata em vez de argumentar | Vire prosa ou tabela real |
| Abertura reafirmando a pergunta | Zero informação nova | Comece pela resposta |
| "Espero que ajude!" / "Me avise se..." | Preenchimento social | Corte |
| Hedge empilhado ("pode potencialmente às vezes") | Medo de errar disfarçado de nuance | Escolha o grau de certeza e assuma |
| Parágrafos de comprimento idêntico | Cadência de máquina | Varie: 1 linha, depois 5, depois 2 |
| Bullets onde a relação entre itens importa | Bullet apaga causalidade | Prosa com conectivos reais |
| "Em conclusão / Em resumo" | Anuncia o fim em vez de terminar | Termine |

### Marcador estrutural mais difícil de ver
**Parágrafos que abrem com o conectivo errado.** "Além disso", "Ademais",
"Por outro lado" usados como cola em vez de relação lógica real. Teste: remova
o conectivo. Se o sentido não muda, ele estava mentindo sobre a relação entre
os parágrafos.

---

## Camada 3 — Substância

Quatro perguntas por peça. Falhou em uma, reescreva.

1. **Teste do "e daí?"** — remova qualquer parágrafo. A peça perdeu algo? Se
   não, ele nunca esteve lá.
2. **Teste da substituição de marca** — troque o nome do produto/cliente por um
   concorrente. Ainda faz sentido? Então não é sobre o cliente — é sobre a
   categoria. Especifique.
3. **Teste do trade-off** — toda recomendação declara o que ela custa?
   Recomendação sem custo é folheto de vendas, não conselho.
4. **Teste da fonte** — todo número, data, preço, nome de cargo, versão de
   software é verificado ou explicitamente marcado como estimativa?

### Extra para conteúdo técnico
5. **Teste do falseamento** — a afirmação poderia ser falsa? Se nenhuma
   evidência a contradiria, ela não afirma nada.

---

## Camada 4 — Compressão

Reescreva 30% menor. Se nada essencial se perdeu, entregue a versão menor.

Isso não é sobre ser breve — é um **detector**. Slop comprime sem perda porque
é enchimento. Argumento denso resiste à compressão.

Se você comprimiu 30% e a peça ficou *melhor*, comprima mais 20% e teste de novo.

---

## Slop visual (design)

Aplicável a qualquer entrega gráfica, incluindo o que outra IA gerar.

### Léxico visual banido por default
- Gradiente roxo→azul (o "gradiente de IA")
- Fundo mesh gradient sem motivo
- Glassmorphism não motivado (blur sem camada real por trás)
- Inter / Poppins / Montserrat como escolha default sem justificativa
- Border-radius 8px em tudo, sem hierarquia
- Drop shadow em todo elemento
- Foto de banco de imagem: pessoas apontando pra laptop, aperto de mão,
  equipe rindo em reunião
- Ícone linear + headline + 3 linhas de body, em grid de 3 cards
- "Dashboard fake" com gráficos genéricos
- Tudo centralizado
- Ilustração isométrica genérica
- Mockup de iPhone flutuando em ângulo 3/4

### Testes estruturais de design
1. **Teste do print sem logo** — cubra a marca. Dá pra dizer de que empresa é?
2. **Teste da grade** — os alinhamentos são intencionais ou acidentais?
3. **Teste da hierarquia em 3 segundos** — mostre por 3s. A pessoa lembra o
   que era mais importante?
4. **Teste da escala tipográfica** — mais de 5 tamanhos na mesma peça =
   decisão não tomada.
5. **Teste do contraste** — WCAG AA (4.5:1 texto normal, 3:1 texto grande).
   Não é acessibilidade opcional, é legibilidade.
6. **Teste da restrição** — a paleta e a escala foram travadas *antes* do
   layout? Se não, o resultado vai divergir.

### Reparo visual
Slop visual quase sempre é **ausência de restrição, não excesso de opção**.
Trave antes de compor: grade, escala tipográfica (máx. 5 passos), paleta
(máx. 3 famílias + neutros), sistema de espaçamento. A restrição gera a forma.

---

## Validador rápido (checklist de 60s)

```
[ ] Zero palavras da lista de léxico
[ ] Zero "não é apenas X — é Y"
[ ] Menos de 1 travessão a cada 3 parágrafos
[ ] Sem parágrafo-resumo final
[ ] Sem "espero que ajude" / "me avise"
[ ] Comprimentos de parágrafo variados
[ ] Passa no teste da substituição de marca
[ ] Toda recomendação tem trade-off declarado
[ ] Todo número tem fonte ou marca de estimativa
[ ] Sobreviveu à compressão de 30%
```

---

## Limite

Uma rodada de reparo. Ciclos de autocrítica sem limite fazem o texto convergir
para uma média homogênea — corrige slop léxico e introduz slop estrutural.
Se após 1 reparo ainda não está bom, o problema é o **enquadramento**, não a
redação.
