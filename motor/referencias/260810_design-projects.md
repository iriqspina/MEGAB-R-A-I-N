# Projetos de design: Duplo Diamante + craft de superfície

Base: Double Diamond, do UK Design Council.

> ⚠️ O Duplo Diamante **não é prescritivo**. O que não muda é a ordem:
> entender antes de resolver.

## Nomenclatura — os dois vocabulários

| Design Council (oficial) | Prático (UX) | Modo |
|---|---|---|
| **Discover** | Pesquisa | divergir |
| **Define** | Análise | convergir |
| **Develop** | Ideação | divergir |
| **Deliver** | Design | convergir |

Use o vocabulário do cliente. Se ele fala Discover/Define, não traduza.

---

## O princípio operacional

Dois losangos, quatro estágios, alternando modo de pensamento:

```
        DIAMANTE 1 (problema)          DIAMANTE 2 (solução)
    ◇ Pesquisa → Análise ◇        ◇ Ideação → Design ◇
    divergir      convergir        divergir    convergir
```

**Divergir** = gerar amplo, sem julgamento, sem fronteira.
**Convergir** = estreitar, avaliar, escolher 1–2 e descartar o resto.

O erro clássico não é pular estágio — é **misturar os modos**. Julgar durante
a divergência mata as ideias boas; divergir durante a convergência impede a
decisão. Antes de qualquer sessão, declare em qual modo você está.

---

## Os 4 estágios — atividades, outputs e engajamento

### Estágio 1 — PESQUISA (divergente)
> Entender o problema em vez de assumir.

**Atividades:** entrevistas (usuários, clientes, SMEs) · personas · mapa de
empatia · desk research · análise competitiva · coleta de dados

**Outputs:** necessidades do cliente · achados brutos · transcrições

**Stakeholder:** nenhum ainda. Não apresente pesquisa crua.

**Armadilha:** tarefa-lista. Não rode todas as atividades — escolha pelo
tempo, recurso e resultado necessários.

---

### Estágio 2 — ANÁLISE (convergente)
> Os insights redefinem o desafio.

**Atividades:** customer journey map · pain points · jobs to be done · causa
raiz · insights & temas · perguntas "How might we"

**Outputs:** problema definido · declarações "How might we" · oportunidades

**Stakeholder:** 🚪 **primeiro stage gate** — apresentação aos patrocinadores.

**Técnicas de convergência:**
- **Affinity diagramming** — agrupe os achados em temas até o padrão aparecer
- **5 porquês** — cave abaixo do sintoma até a causa raiz
- **"How might we"** — reformule o insight em pergunta aberta

**A frase de problema.** É o output que importa. Formato: *quem* precisa de
*o quê*, **porque** *evidência da pesquisa*.

O objetivo do Define não é listar todos os problemas — é enunciar **o único
que mais importa**, para o usuário e para o negócio.

**Armadilha:** pular de "achados" para "solução" sem o problema escrito numa
frase falseável. Desconfie de Define que só confirma o que o time já achava —
isso indica Discover curto demais.

---

### Estágio 3 — IDEAÇÃO (divergente)
> Gerar amplo, traduzir em protótipo barato.

**Atividades:** workshops · sketches / protótipos rápidos · user flows ·
wireframes / conceitos · teste de conceito

**Outputs:** ideias · mapas de fluxo · conceitos · baixa fidelidade

**Stakeholder:** sense check informal.

**Time-boxing é obrigatório aqui.** Divergência sem limite vira paralisia por
análise. Crazy 8s (8 ideias em 8 minutos) existe para forçar o salto além das
2 ou 3 primeiras ideias óbvias. Defina o prazo de decisão *antes* de abrir a
sessão.

**Regra de saída:** saia com 2–4 conceitos distintos e testáveis, não com um
vencedor. Conceito único não é convergência, é falta de exploração.

**Armadilha:** alta fidelidade cedo. Fidelidade alta compra comprometimento
emocional e mata a divergência.

---

### Estágio 4 — DESIGN (convergente)
> Testar em pequena escala, rejeitar o que não funciona, iterar até fechar.

**Atividades:** alta fidelidade · design reviews · testes de usabilidade

**Outputs:** designs finais · solução · protótipos funcionais

**Stakeholder:** 🚪 **segundo stage gate** — apresentação final.

**Métricas de teste de usabilidade** — substituem "achei que ficou bom":

| Métrica | Mede |
|---|---|
| Task completion rate | O fluxo funciona no cenário real? |
| Time on task | Eficiência — crítico em ferramenta de trabalho |
| Error rate | Aponta a tela exata que confunde |
| SUS | Nota comparável entre versões |

Escolha 2. Medir as 4 em teste de 5 pessoas gera número sem significância.

---

## Armadilhas por fase

| Armadilha | Fase | Correção |
|---|---|---|
| **Correr a pesquisa** | Discover | Plano de pesquisa escrito antes: objetivo, perguntas, quantas pessoas |
| **Construir sobre premissa** | Discover/Define | Entrevista direta obrigatória antes da frase de problema |
| **Stakeholder desalinhado** | Todas | Cadência fixa de review curto. Faça o stakeholder *ver* a pesquisa |
| **Ideação infinita** | Develop | Time-boxing + prazo de decisão definido antes |
| **Fidelidade alta cedo** | Develop | Baixa fidelidade até ter dado de teste |
| **Convergir sem dado** | Deliver | Métrica declarada antes do teste |

A mais cara é a primeira. Cortar Discover parece economizar tempo, mas
transfere o custo para a engenharia — onde ele é multiplicado.

---

## Regras de qualidade específicas de design

Complementam o anti-slop (`260810_anti-slop.md`, camada visual).

1. **Trave a restrição antes de compor.** Grade, escala tipográfica (máx. 5
   passos), paleta (máx. 3 famílias + neutros), sistema de espaçamento.
2. **Referência antes de descrição.** Direção visual definida por referência
   concreta bate adjetivo em qualquer projeto — como montar e usar a
   biblioteca: `260810_galerias-referencia.md`.
3. **Teste do print sem logo.** Cubra a marca. Dá pra dizer de quem é?
4. **Contraste é legibilidade.** WCAG AA: 4.5:1 texto normal, 3:1 texto grande.
5. **Fidelidade proporcional à certeza.** Baixa certeza = baixa fidelidade.
6. **Toda decisão visual tem motivo declarável.** Se você não consegue dizer
   por que o radius é 12px, ele deveria ser 0.

---

## Quando a entrega vira código (DOM)

Peça estática, deck, print, 3D e motion sem DOM ficam inteiramente neste
arquivo + Gate 4.5. Landing, dashboard, app UI, form — que **viram código**
— saem daqui: roteiro completo, modos de superfície e piso de craft em
`260810_impeccable-routing.md`. O Duplo Diamante continua governando a
*fase* do projeto; o craft de código é uma camada extra sobre ela.

---

## Encaixe com Agile / Scrum

- **Duplo Diamante** responde *o quê* construir e *por quê*
- **Agile / Scrum** responde *como* construir bem

Arranjo padrão: design roda **1–2 sprints à frente** do desenvolvimento.
Falha comum: design vira "fábrica de tela" e o primeiro diamante desaparece.
Se a pesquisa não tem sprint própria, ela não acontece.

---

## Papéis mínimos

| Papel | Dono de |
|---|---|
| Produto | O "porquê" — alinhamento com objetivo de negócio |
| Pesquisa (UX) | Discover — extrair o insight |
| Designer de produto | Traduzir insight em protótipo e peça final |
| Engenharia (lead) | Checagem de viabilidade **durante**, não no fim |

Trabalhando solo, você acumula os quatro. O risco específico do solo é pular a
checagem de viabilidade e o desalinhamento — os dois papéis que existem para
te contradizer. Compense marcando conversa explícita com dev e cliente ao fim
das fases 2 e 4.

---

## Duração

Não há número certo. O critério não é calendário — é se a fase entregou o
output dela. Discover terminou quando parou de aparecer surpresa nas
entrevistas. Define terminou quando existe a frase de problema.

**Custo declarado:** o Duplo Diamante atrasa o primeiro pixel. Em projeto com
escopo travado e problema validado, ele é overhead. Use quando há incerteza
real sobre *qual* é o problema.

---

## Quando NÃO usar o Duplo Diamante

- Escopo travado e problema já validado → vá direto ao Estágio 3/4
- Peça pontual (um post, um banner) → Gates 1, 4 e 6 bastam
- Prazo menor que 48h com briefing sólido → design sprint condensado
- Cliente que já decidiu a solução e quer execução → declare o risco por
  escrito uma vez, depois execute
