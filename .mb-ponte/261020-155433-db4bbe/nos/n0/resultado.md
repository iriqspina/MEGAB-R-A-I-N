# Resultado · n0 (planejador GLM) · ordem 261020-155433-db4bbe

## O que foi pedido e o estado de cada item

1. **"resolva e deixe automatizado"** (Z.ai sem detalhes / "Resets —" no widget de cotas) — **RESOLVIDO**. `zai_details()` em `apps/ia-quota-widget/quota_details_data.py` + ligação em `_fetch_zai` (providers.py): plano, % livre por janela e nota de créditos da própria API de cota. Renovação de cada janela segue nos cartões (resets_at). Zero chamada nova de rede, zero leitura por modelo — mesma consulta `api/monitor/usage/quota/limit` que o widget já fazia a cada refresh (automático para sempre).
2. **"sem custo de i.a. nem leitura via i.a."** — **ATENDIDO**: só JSON da API de cota + arquivos locais (config.toml, provider_config.json, `--help`). Nenhum modelo foi usado para extrair nada.
3. **Nota #dr-term** ("faltam efforts do codex… linguagem que cada vendor usa") — **RESOLVIDO** (frente B, abaixo).
4. **Complementos posteriores** (ver "Coordenação com sessões paralelas"): debounce 3 min + edição-ao-mesmo-agente já estavam em produção na ponte (espera_segundos=180); "modo janela?" respondido no 261018_PONTE regenerado; sweep de comentários em andamento pela frente de auditoria; **pendência real: escolha de IA/modelo/effort no próprio comentário do relatório** (base pronta — ver Pendências).

## Frente A — Z.ai com detalhes no widget (implementada por sessão paralela, conferida aqui)

- **Autoria**: enquanto eu media o estado, uma sessão paralela (ordem 261020-170554-b2c2be / frente bapp) implementou o extrator no widget. Não reescrevi; **conferi no disco**: suíte do widget 638 testes + 34 subtestes verdes (`.venv/Scripts/python.exe -m pytest tests/ -q`), e leitura real `fetch_provider('zai')` devolvendo `details` com plano/janelas/notas (probe em `evidence/261020_zai-detalhes-efforts/probe.json`).
- "Resets" fica honestamente `—` para Z.ai: a API não expõe estoque de resets (Codex/Claude expõem); cada janela renova sozinha no `nextResetTime` — agora explicado nas notas do popup.
- Widget real reiniciado: 2 instâncias brigando → 1 (pid 50448), carregando a versão nova.

## Frente B — esforços/modelos batidos por vendor (implementada por este n0)

Arquivos: `apps/megabrain-dashboard/central_dispatch.py` (CATALOG + `_linha_cli`), `motor/modelos/interacoes/261010_decisoes-respondiveis/decisoes-respondiveis.js` (v1.3, var IAS + MODELO_LIVRE), `00_PARA-VOCE/261020_cotas-mapa-bapp/261020_RELATORIO.html` (IAS inline + seção nova "Efforts por vendor batidos" com print do popup Z.ai), `apps/megabrain-dashboard/tests/test_dispatch_catalogo_consistente.py` (novo).

- **Codex** (fonte local `~/.codex/config.toml` `enabled-reasoning-efforts`, codex-cli 0.163.0): low, medium, high, xhigh, **ultra**, **max** entraram; **minimal** saiu (não existe no seletor).
- **Claude Code** (fonte `claude --help` 2.1.302): efforts ganham **xhigh** e **max**; modelos ganham **fable** (alias oficial).
- **ZCode** (fonte `zcode --help` completo + `~/.zcode/v2/provider_config.json`, ajuste da revisão): `--model provider/model` passa a ser usado (`zai/GLM-5.3`, `zai/GLM-5.3-Flash`); esforço (low/high/max) sem flag — fica na sessão. Teste efetivo executado: `zcode --model zai/GLM-5.3-Flash -p ...` respondeu OK (1 request mínimo consumido).
- **Kimi** saiu do catálogo (conta cancelada 16/09/2026, decisão 260916e — data corrigida pela revisão).
- **Gemini**: mantido sem effort, com nota "login pendente desde 261014".
- **Automação anti-deriva**: teste novo (13 casos, verdes) compara CATALOG (Python) ↔ `var IAS` (JS do motor) ↔ `var IAS` inline do relatório entregue; valida ultra/minimal/fable/zai-GLM e as linhas de comando geradas.
- App MegaBrain reiniciado para o CATALOG novo valer nos despachos (o central_dispatch é importado no start).

## Como verifiquei

- Widget: suíte 638 ✓ (antes da outra sessão terminar havia 5 falhas do trabalho dela em andamento; ela fechou tudo — re-executado e verde), leitura real com `details` ✓, probe de render com dados reais (`popup-zai.png`, `celula-zai.png`, `probe.json`) ✓.
- Dashboard: suíte completa 377 testes OK / 3 skips (1ª rodada teve 3 erros transitórios de concorrência com a outra sessão editando o app ao vivo; re-execução com o mesmo código 100% verde).
- Dispatch: teste dedicado 13/13 ✓; `node --check` no JS do motor e no inline do HTML ✓; teste efetivo do `--model` do ZCode ✓.
- Reinícios: widget 2→1 ✓; app central com CATALOG novo ✓ (nasceu às 17:26+, após a edição final de 17:25).

## Revisão independente

Revisor GPT (nó n2, parecer em `nos/n2/resultado.md`): **aprovar com ajustes**. Os 3 achados foram aplicados por mim: (1) ZCode `--model` (médio) — corrigido com fonte e teste efetivo; (2) teste não cobria o HTML entregue (médio) — agora compara as três cópias; (3) data do Kimi 16/10→16/09 (baixo) — corrigida nos três pontos.

## Coordenação com sessões paralelas

- Ordem 261020-170554 (GPT, bapp/cursor) implementou o extrator Z.ai no widget e segue viva em outro escopo; nada dela foi sobrescrito.
- Frente de auditoria (evidence/261020_auditoria-comentarios) já colocou o debounce de 3 min (espera_segundos=180) e a regra edição-de-nota→mesmo-responsável na ponte; regenerou o 261018_PONTE com a seção "O que é modo janela?" (resposta à pergunta do <USUARIO>) e a auditoria dos 53 comentários (sweep em andamento).
- Suíte do widget rodou 2× por causa da edição concorrente; nenhum arquivo alheio foi tocado por mim.

## Pendências (para o <USUARIO> / próxima ordem)

1. **Escolher IA/modelo/effort no próprio comentário do relatório** (nota 19:18 UTC): a ponte já despacha com modelo/effort (dr-term + perfil do vendor) e o catálogo agora está batido e testado; falta a UI da nota oferecer essas escolhas. Base pronta em `central_dispatch.CATALOG` — qualquer frente do app pode consumir.
2. Validação visual humana do popup Z.ai e do seletor novo no app (feita por probe estrutural e dados reais; print anexado).
3. Gemini segue sem login (desde 261014) — nota mantida no catálogo até nova sessão.
4. Reinício do app central nasce com 2 instâncias (comportamento do lançador, preexistente; fora deste escopo).

## Provas

`evidence/261020_zai-detalhes-efforts/` (probe.json, popup-zai.png, celula-zai.png, scripts de reinício), `apps/megabrain-dashboard/tests/test_dispatch_catalogo_consistente.py` (13/13), `.mb-ponte/261020-155433-db4bbe/nos/n2/resultado.md` (parecer), suítes: widget 638 ✓ / dashboard 377 ✓.
