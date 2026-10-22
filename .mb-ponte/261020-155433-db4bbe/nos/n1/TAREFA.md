# Revisão independente · ordem 261020-155433-db4bbe · nó n1 (revisor GPT)

Você é o **revisor independente** (vendor GPT) do trabalho produzido pelo planejador GLM (nó n0) na ordem da ponte `.mb-ponte/261020-155433-db4bbe`. Não edite nenhum arquivo; só leia, verifique e escreva seu parecer em `.mb-ponte/261020-155433-db4bbe/nos/n1/resultado.md`.

## Contexto
Comentários do <USUARIO> no relatório `00_PARA-VOCE/261020_cotas-mapa-bapp/261020_RELATORIO.html`:
1. "resolva e deixe automatizado" e "sem custo de i.a. nem leitura via i.a. se possível" — Z.ai sem detalhes / "Resets —" no widget de cotas.
2. Complemento (âncora #dr-term): "precisa ser batido as informações pq faltam efforts disponíveis do codex e imagino que nao estão todos corretos e adaptados 100% com a linguagem que cada vendor usa".

IMPORTANTE: o item 1 (extrator `zai_details` no widget) foi implementado por UMA SESSÃO PARALELA (ordem 261020-170554, planejamento bapp) — o n0 conferiu no disco (suíte 638 testes verde + leitura real com details). Você pode revisá-lo também se quiser, mas o alvo principal é o recorte abaixo, produzido pelo n0.

## O que o n0 produziu (recorte a revisar)
1. `apps/megabrain-dashboard/central_dispatch.py` — CATALOG batido com fontes LOCAIS (sem custo de IA): codex efforts = padrão,low,medium,high,xhigh,ultra,max (ultra/max novos, minimal removido — fonte `enabled-reasoning-efforts` do `~/.codex/config.toml`, Codex 0.163); claude efforts = padrão,low,medium,high,xhigh,max e modelos +fable (fonte `claude --help` 2.1.302); kimi removido (conta cancelada 16/10); gemini com nota login pendente; fallback do `_linha_cli` agora levanta ValueError em vez de montar linha do kimi.
2. `motor/modelos/interacoes/261010_decisoes-respondiveis/decisoes-respondiveis.js` — `var IAS` espelhado (v1.3), Kimi fora, notas.
3. `apps/megabrain-dashboard/tests/test_dispatch_catalogo_consistente.py` — NOVO: compara CATALOG (Python) ↔ var IAS (JS) por IA/modelos/efforts; kimi ausente; ultra/max presentes, minimal ausente; validar() aceita ultra e rejeita minimal; linhas de comando com `--effort xhigh` (claude) e `model_reasoning_effort="ultra"` (codex).
4. `00_PARA-VOCE/261020_cotas-mapa-bapp/261020_RELATORIO.html` — `var IAS` inline substituído (mesmas listas) + nova seção "Efforts por vendor batidos" com print do popup Z.ai (evidence/261020_cotas-mapa-bapp/prints/popup-zai-detalhes.png) e fatos; CRLF preservado.
5. Operação: widget reiniciado (2 instâncias → 1) e app MegaBrain reiniciado (2 → 1) para carregar CATALOG novo; provas em `evidence/261020_zai-detalhes-efforts/` (probe.json, prints, scripts .ps1).

## Como verificar (faça você mesmo)
- Rodar: `python -m unittest tests.test_dispatch_catalogo_consistente -v` dentro de `apps/megabrain-dashboard` (9 testes).
- Conferir as fontes locais: `grep -n "enabled-reasoning-efforts" ~/.codex/config.toml`; `claude --help | grep -A2 effort`; `zcode --help` (sem flag de modelo/effort).
- Rodar `node --check motor/modelos/interacoes/261010_decisoes-respondiveis/decisoes-respondiveis.js`.
- No relatório: confirmar que o `var IAS` inline é idêntico ao do JS do motor e que a nova seção não quebrou o HTML (abrindo no navegador, se possível).
- Suíte maior se achar necessário: `python -m unittest discover -s tests -q` em apps/megabrain-dashboard (377 OK com 3 skips na última rodada do n0).

## Critérios do parecer
- Erros graves (lógica errada, fonte mentirosa, HTML quebrado, teste que não testa) × médios × cosméticos.
- As listas de efforts/modelos correspondem às fontes locais declaradas?
- Alguma mudação de comportamento indesejada (ex.: rota que usava kimi)?
- Escreva o parecer em `nos/n1/resultado.md` com: veredito (aprovar / aprovar com ajustes / reprovar), o que verificou com comando próprio, e lista de achados com arquivo:linha. NÃO edite arquivos do projeto.
