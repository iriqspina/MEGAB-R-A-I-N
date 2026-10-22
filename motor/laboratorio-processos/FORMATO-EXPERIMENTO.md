# Formato de experimento do Laboratório de processos

Um experimento = um arquivo `experimentos/EXP-NNN_<slug>.json`, preenchido antes de rodar e completado depois.

| Campo | Conteúdo |
|---|---|
| `id`, `titulo`, `nivel` | `EXP-NNN`; nome curto; `macro` ou `micro` |
| `origem` | pedido humano literal (caminho do raw) ou lição que motivou |
| `hipotese` | 1 frase falseável: "Se fizermos X, a métrica M melhora pelo menos Y frente ao caso C" |
| `dinamica` | passo a passo congelado, com `versao` (v1, v2…) |
| `caso_base` | execução comparável anterior (projeto, data, arquivos) ou `linha de base nova` |
| `metricas` | lista {id, nome, como_medir, fonte, meta (com [ESTIMATIVA] se sem base)} |
| `rodadas` | lista {data, projeto, ordem, valores medidos, provas (caminhos), custo (minutos, chamadas por fornecedor, cota antes/depois como snapshot)} |
| `revisor` | quem conferiu sem ter produzido |
| `decisao` | `promover` / `ajustar` / `reverter` / `pendente`, com motivo e alternativa descartada |
| `aprendizados` | o que o filtro/execução ensinou (critério que mais decidiu, critério novo proposto, critério inútil) |
| `humano` | aprovação/rejeição literal do <USUARIO>, separada da opinião do agente |
| `reversao` | como desfazer, escrito antes de rodar |

Regras: uma dinâmica muda por vez; janelas equivalentes; sem dado = `NAO_MEDIDO`; promover = 2 rodadas na mesma direção ou 1 + aprovação do <USUARIO>; negativo fica registrado.
