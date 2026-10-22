# Laboratório de processos · MegaBrain

Aberto em 2026-10-21 a pedido do <USUARIO> (literal em `memoria/cerebro/raw/261021_pedido-laboratorio-processos.md`):
> "abra uma parte do megabrain para laboratório de processos, com fim de melhorar o megabrain e os projetos, testar dinâmicas para deixarmos a pipeline ideal no macro e no micro. lembre disso no megabrain, é importante."

## Para que serve

1. Testar dinâmicas de trabalho (gerar, filtrar, revisar, distribuir entre IAs, entregar) como **experimentos com métrica**, não por opinião.
2. Dois níveis:
   1. **macro**: a esteira inteira (pedido → plano → produção → revisão → entrega);
   2. **micro**: uma etapa (ex.: filtrar 200 itens até 50).
3. Só vira regra/referência da central o que venceu a comparação com o caso anterior. O que perdeu fica registrado como negativo (não se apaga).

Enquadramento: research through design (Frayling 1993; Zimmerman, Forlizzi & Evenson 2007, DOI 10.1145/1240624.1240704) — o processo é o artefato que produz conhecimento, por isso precisa ser documentado e repetível.

## Como rodar um experimento

1. Copiar `experimentos/_modelo.json` para `experimentos/EXP-NNN_<slug>.json` e preencher **antes** de rodar: hipótese falseável, dinâmica congelada (versão), caso base, métricas, reversão.
2. Mudar uma dinâmica por vez. Se mudarem duas, registrar como "observação", não como experimento.
3. Medir com dados do disco (JSON, prints, logs). Dado ausente = `NAO_MEDIDO`. Meta sem base = `[ESTIMATIVA]`.
4. Revisor que não produziu o resultado confere as métricas.
5. Decidir: `promover` (referência da central + linha no DECISOES da central), `ajustar` (nova versão, nova rodada) ou `reverter`.
6. Promover exige 2 rodadas na mesma direção, ou 1 rodada + aprovação explícita do <USUARIO>. Gosto humano é registrado à parte (campo `humano`) e nunca substituído pela nota técnica.

## Índice de experimentos (recente primeiro)

| ID | Nível | Dinâmica | Estado |
|---|---|---|---|
| EXP-001 | micro | Garimpo analógico com seleção comparativa (superproduzir ≥2× e filtrar aprendendo por que X > Y) | rodada 1 executada no Bubble, 21/10 — ver `experimentos/EXP-001_garimpo-analogico.json` |

Fila (sem compromisso): EXP-002 revisão visual por print com 2 fornecedores × 1; EXP-003 rotas prontas antes do plano × plano direto; EXP-004 eco de termo (mal-entendidos capturados × ruído). Detalhe em `261021_proposta-original-n5.md` §4.

## Arquivos

- `FORMATO-EXPERIMENTO.md` — campos e regras.
- `experimentos/_modelo.json` — molde vazio.
- `experimentos/EXP-001_garimpo-analogico.json` — primeiro experimento.
- `metodos/261021_garimpo-analogico.md` — o método (protocolo de 11 passos, rubrica, como registrar o aprendizado do filtro, base acadêmica).
- `261021_proposta-original-n5.md` — proposta original do worker que pesquisou o método (preservada).
