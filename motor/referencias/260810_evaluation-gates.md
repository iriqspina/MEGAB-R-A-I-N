# Avaliação: rubricas e gates

Princípio: **"está bom?" não é falseável. "atende ao critério 2?" é.**
Sem rubrica escrita antes da geração, autocrítica vira opinião — e opinião de
modelo converge para "ficou ótimo".

---

## Como escrever uma rubrica utilizável

Três a cinco critérios. Cada um precisa ser:
- **Verificável** — dá pra apontar a evidência no texto/arquivo
- **Independente** — não é reformulação de outro critério
- **Falseável** — existe uma versão que falharia

```
❌ "Deve ser de alta qualidade"        (não falseável)
❌ "Deve ser claro e conciso"          (dois critérios, ambos vagos)
✅ "Toda recomendação declara seu custo, citável no texto"
✅ "Nenhum parágrafo sobrevive à remoção sem perda"
✅ "Todo número tem fonte ou rótulo [ESTIMATIVA]"
```

---

## Rubricas prontas

### Texto entregável (proposta, artigo, relatório)
1. Um leitor específico toma uma decisão específica depois de ler. Qual?
2. Passa no teste da substituição de marca (troque o cliente pelo
   concorrente — quebra?)
3. Toda recomendação tem trade-off declarado
4. Zero itens do léxico banido; zero "não é apenas X, é Y"
5. Sobrevive à compressão de 30% sem perda de argumento

### Peça de design
1. Restrição travada antes da composição (grade, escala tipo, paleta,
   espaçamento)
2. Hierarquia legível em 3 segundos
3. Contraste WCAG AA (4.5:1 / 3:1)
4. Passa no teste do print sem logo
5. Toda decisão visual tem motivo declarável
6. Zero itens do léxico visual banido

### Código / script
1. Roda no ambiente-alvo real, não só na cabeça
2. Caso de erro tratado explicitamente, não engolido
3. Nenhum valor mágico sem nome
4. Testável sem mock de tudo
5. Diff mínimo — não reescreve o que não precisava mudar

### Apresentação
1. Um slide = uma ideia
2. Título do slide é a afirmação, não o rótulo ("Receita caiu 12% no Q2" >
   "Receita")
3. Todo gráfico responde a uma pergunta declarada
4. Roteiro de fala existe e cabe no tempo
5. Slide final tem a decisão pedida, não "obrigado"

---

## Protocolo de pontuação

```
Para cada critério: nota 1–5 + citação da evidência.
Sem citação → a nota não conta, refaça a avaliação.
Qualquer critério < 4 → reescreva SÓ o que falhou.
Uma rodada de reparo. Depois disso, volte ao enquadramento.
```

**Por que citar a evidência:** obriga a avaliação a olhar o artefato real em
vez de julgar a intenção. Nota sem citação é sempre 4.

---

## Verificação independente

Para trabalho de alto risco (cliente, dinheiro, prazo público), a autoavaliação
não basta — quem gerou está ancorado no próprio raciocínio.

Delegue a um agente separado com **só o artefato e a rubrica**, sem o
histórico (template pronto: T4 em `260810_metaprompt-templates.md`):

```
Você recebe um artefato e uma rubrica. Não sabe como ele foi feito
e não deve assumir boa intenção. Pontue cada critério 1–5 com
citação. Liste as 3 objeções mais fortes de quem rejeitaria isso.
```

Contexto zero é a característica útil aqui, não uma limitação. Refinamento:
rode a avaliação crítica e qualquer checagem determinística (script, lint,
detector) **sem uma ver a outra**; a síntese só depois — output determinístico
ancora o julgamento se chegar primeiro.

---

## Verificação factual

Camada separada da rubrica. Sempre que a peça afirma algo sobre o mundo:

- [ ] Números recalculados, não copiados
- [ ] Datas e prazos conferidos contra a data de hoje
- [ ] Nomes de pessoa/cargo/empresa verificados (mudam)
- [ ] Preços e planos verificados (mudam)
- [ ] Versões de software verificadas (mudam)
- [ ] Links abrem
- [ ] Nenhuma afirmação sobre o presente vinda só de memória do modelo

Regra dura: qualquer fato sobre o mundo atual → buscar antes. Confiança não
substitui verificação.

---

## Verificação de artefato

- [ ] O arquivo abre no app de destino (não só "foi gerado")
- [ ] Entrega fora do repo com prefixo `YYMMDD_`
- [ ] Fontes embutidas / imagens não quebradas
- [ ] Caminhos referenciados existem
- [ ] Tamanho razoável (arquivo de 4KB que deveria ter 40 páginas = falha
      silenciosa)

---

## Como isso costuma dar errado

1. **Rubrica escrita depois da geração.** Ela se molda ao que já existe.
   Escreva antes.
2. **Autoavaliação sem citação.** Vira 4/5 em tudo.
3. **Critério que é reformulação de outro.** Dá falsa sensação de cobertura.
4. **Reparar mais de uma vez.** Homogeneíza.
5. **Verificar o formato e não o conteúdo.** O arquivo abre e está errado.
