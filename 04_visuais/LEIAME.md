# 09_visuais — a biblioteca visual do megabrain

**Criada em 260822.** Esta pasta é do **humano**: você entra, olha, arrasta.
A implementação (tokens e mecânicas que o código usa) mora em `modelos/visuais/`
e é do **código**. Uma alimenta a outra, nunca se misturam.

## Por que existe separada do relatório

Referência visual não é do relatório — é sua, de designer. O relatório é só
**um consumidor** dela. Se a biblioteca morasse dentro de `04_relatorios/`,
toda peça futura (proposta de cliente, deck, portfólio, capa de projeto) teria
que ir buscar num lugar que não é dela. Aqui é o acervo; quem precisa, puxa.

```
09_visuais/            ← acervo (humano)  ─┐
                                            ├─→ modelos/visuais/temas/  (código)
modelos/visuais/       ← implementação    ─┘        └─→ 04_relatorios/RELATORIO.html
```

## As pastas, e o que cada uma quer de você

| pasta | o que é | o que você faz |
|---|---|---|
| `00_entrada/` | referência recém-buscada, **você ainda não olhou** | triar: arrastar pra `01_sim/` ou `02_nao/` |
| `01_sim/` | aprovado. Subdividido por **eixo**, não por projeto | arrastar pro eixo certo (ou deixar na raiz que eu classifico) |
| `02_nao/` | recusado — **e é a pasta mais valiosa** | arrastar e, se der, escrever o motivo num `.txt` de mesmo nome |
| `03_temas/` | o que virou tema de verdade, com as refs que o geraram | nada; eu mantenho |
| `_fontes/` | o rastro da busca (URL, data, query, o que falhou) | nada; é auditoria |

**Por que `02_nao/` importa mais que `01_sim/`:** "sim" me diz o que serve
hoje; "não" me ensina seu gosto e encolhe a próxima busca. Um `nao/` com motivo
vale por dez briefings.

## Os eixos de `01_sim/`

Referência não é "bonita" — ela resolve **uma** coisa. Por isso o corte é por
eixo e não por projeto ou por site:

- `cor/` — paleta, relação entre acento e neutro, comportamento claro/escuro
- `tipografia/` — pares, escala, tracking, mono, variable fonts
- `layout/` — densidade, grid, hierarquia, o que fica em cima
- `movimento/` — transição, scroll-driven, feedback de estado (não decoração)
- `textura/` — grão, dither, halftone, malha, material
- `componentes/` — KPI, timeline, grafo, semáforo, tabela, barra de execuções

Uma referência pode aparecer em dois eixos. Duplicar o arquivo é barato;
procurar num eixo errado, não.

## Como eu busco (o método)

Está em `_fontes/260822_metodo-de-busca.md`. Resumo: eu traduzo o que você fala
em **eixos e negativos** antes de buscar, varro em paralelo por territórios
diferentes, verifico cada URL, e declaro o que falhou em vez de inventar.

## Regra de ouro

Nada aqui é lido por script do megabrain. Você pode renomear, mover e apagar à
vontade — **não quebra nada**. O único acoplamento é `03_temas/`, que cita de
onde cada tema veio; se você mover uma referência citada, o tema continua
funcionando, só perde a nota de proveniência.
