# Laboratório de processos · proposta para o MegaBrain

Data: 2026-10-20 · Autor: worker n5 (Claude), ordem 261020-211812-fe0b10 · Estado: **proposta, não instalada**.
Base: `evidence/261020_eventos-bolhas/metodo-academico.json` (17 métodos, 46 referências, 41 conferidas no Crossref).

## 1. Objetivo

1. Testar dinâmicas de trabalho (como gerar, filtrar, revisar, distribuir entre IAs) como experimentos, em vez de adotá-las por opinião.
2. Melhorar o MegaBrain e os projetos em dois níveis:
   1. **macro**: a esteira inteira (pedido → plano → produção → revisão → entrega);
   2. **micro**: uma etapa (ex.: como filtrar 150 itens até 50).
3. Promover para a central só o que venceu a comparação com o caso anterior; o resto é revertido e o negativo fica registrado.

Enquadramento acadêmico: *research through design* (Frayling 1993; Zimmerman, Forlizzi & Evenson 2007). O processo é o artefato que produz conhecimento, e por isso precisa ser documentado para ser repetível.

## 2. Formato de um experimento

Cada experimento é um arquivo `lab/EXP-NNN.json` (área técnica da central, fora de `00_PARA-VOCE`) com estes campos:

| Campo | O que contém |
|---|---|
| `hipotese` | 1 frase falseável: "Se fizermos X, a métrica M melhora em pelo menos Y frente ao caso C." |
| `dinamica_testada` | o passo-a-passo exato, congelado por versão (`v1`, `v2`...) |
| `nivel` | `macro` ou `micro` |
| `caso_base` | execução anterior comparável (projeto, data, arquivos) ou "linha de base nova" |
| `metricas` | nome, como medir, fonte do dado; ausente = `NAO_MEDIDO` |
| `custo` | tempo de relógio, chamadas por vendor, % de cota antes/depois (snapshot, não saldo) |
| `resultado` | valores medidos + prints/arquivos de prova |
| `revisor` | quem conferiu sem ter produzido o resultado |
| `decisao` | `promover`, `ajustar` (nova versão) ou `reverter`, com motivo e alternativa descartada |
| `humano` | o que o <USUARIO> aprovou ou rejeitou (literal), separado da opinião do agente |

Regras:
1. Uma dinâmica muda por vez; se duas mudarem, o experimento não isola a causa e vira só "observação".
2. Comparar janelas equivalentes (mesmo tipo de tarefa, tamanho parecido). Uma rodada é um indício, não uma prova; promover exige 2 rodadas na mesma direção ou 1 rodada + aprovação explícita do <USUARIO>.
3. Reversão sempre escrita antes de rodar.
4. A decisão vai para `DECISOES.md` do projeto e, se promovida, para uma referência portátil da central (padrão sanitizado, sem dado de cliente).

## 3. Experimento nº 1 · "Superproduzir e filtrar aprendendo"

Origem: pedido do <USUARIO> em 21/10 (50 eventos que evocam bolhas, coletar mais e filtrar aprendendo por que X é melhor que Y). Nome sugerido: **garimpo analógico com seleção comparativa**.

### 3.1 Hipótese

H1: Coletar 2–3× o alvo com cotas de diversidade e filtrar por rubrica + comparação em pares gera um conjunto final **mais variado e mais original**, sem perder fidelidade de fonte, do que coletar só o alvo e escolher por impressão.

### 3.2 Dinâmica testada (v1)

Os 11 passos de `protocolo_refinado` no JSON, resumidos:
enquadrar facetas relacionais → cotas de diversidade → superproduzir (≥2×) → extrair dinâmica → misturar (caixa morfológica) → pré-filtro de integridade → rubrica com 2+ avaliadores independentes → pares na fronteira do corte → selecionar 50 com cotas → triangular futuros (≥2 sinais) → registrar aprendizado.

### 3.3 Caso base

Não existe rodada anterior medida com o mesmo pedido. Duas opções, em ordem de preferência:
1. **Controle barato**: um worker separado produz só 50 itens, sem cotas, e escolhe por impressão (mesmo prazo, mesma fonte de busca). Compara-se o conjunto dele com o conjunto final do protocolo.
2. **Linha de base nova**: sem controle; a rodada 1 vira referência para a rodada 2 (próxima pesquisa do mesmo tipo). Mais fraca: só permite comparar consigo mesma.

### 3.4 Métricas (todas mensuráveis a partir dos JSON)

| # | Métrica | Como medir | Meta v1 [ESTIMATIVA] |
|---|---|---|---|
| M1 | Taxa de superprodução | itens coletados ÷ 50 | ≥ 2,0 |
| M2 | Variedade | células distintas preenchidas (escala × domínio × região) ÷ células da matriz (Shah et al. 2003) | ≥ controle + 20% |
| M3 | Originalidade média dos 50 | média do critério "Originalidade no conjunto" (1–5) | ≥ controle + 0,5 |
| M4 | Taxa de clichê | % dos 50 com `risco` marcando clichê/literal | ≤ 10% |
| M5 | Fidelidade | % dos 50 com `confianca: verificado` e URL aberta | ≥ 90% |
| M6 | Concordância entre avaliadores | diferença média absoluta das notas por critério | ≤ 1,0 ponto |
| M7 | Aprendizado capturado | nº de comparações X×Y com motivo; nº de motivos "novo: ..." que viraram proposta de critério | ≥ 30 comparações; ≥ 1 proposta |
| M8 | Tendência triangulada | % dos itens com tendência que têm ≥2 fontes independentes | 100% |
| M9 | Aprovação humana | dos 50, quantos o <USUARIO> marca "aproveitar" na decisão respondível | registrar; sem meta |
| M10 | Custo | minutos de relógio + chamadas por vendor + % de cota antes/depois | registrar; comparar com controle |

Metas são [ESTIMATIVA] de partida, não norma; a rodada 1 calibra.

### 3.5 Critério de decisão

1. **Promover** a dinâmica como referência da central se: M2 e M3 superam o controle, M5 ≥ 90%, e M9 não fica abaixo do controle.
2. **Ajustar (v2)** se a variedade melhorar mas a fidelidade cair, ou se M6 > 1,0 (rubrica mal definida: reescrever o critério com mais discordância).
3. **Reverter** se o custo M10 for maior que 2× o controle sem ganho em M2/M3/M9.

### 3.6 Riscos específicos do experimento

1. Avaliador do mesmo modelo que gerou: usar outro vendor (Codex ou GLM) ou o <USUARIO> como 2º avaliador.
2. Fixação nos primeiros itens: avaliar em ordem aleatória.
3. Viés contra originalidade (Rietzschel et al. 2010; Mueller et al. 2011): manter a cota de ≥10 itens com originalidade 5.
4. Gosto humano ≠ nota técnica: M9 é registrado à parte e nunca substituído pela rubrica.

### 3.7 Reversão

Nada é instalado na central nesta etapa. Reverter = não promover; os arquivos do experimento ficam como histórico negativo.

## 4. Próximos candidatos (fila, sem compromisso)

1. EXP-002 (micro): revisão visual por print com 2 vendors vs. 1 vendor — mede defeitos encontrados depois da entrega.
2. EXP-003 (macro): planejamento com rotas prontas antes do plano vs. plano direto — mede retrabalho.
3. EXP-004 (micro): eco de termo (ECO-TERMO) — mede mal-entendidos capturados vs. ruído.

## 5. O que falta para instalar

1. Decisão do <USUARIO>: criar a pasta `lab/` na central e aceitar o formato acima.
2. Um verificador simples que leia `EXP-NNN.json` e calcule M1–M8 a partir dos JSON do worker (sem chamada a modelo).
3. Ligação com o app MegaBrain: mostrar experimentos abertos/decididos na central, recente primeiro.
