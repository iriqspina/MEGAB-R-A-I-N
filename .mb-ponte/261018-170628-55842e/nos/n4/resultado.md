# Resultado do nó n4 — mapa do harness

TL;DR — Mapa revisto e corrigido por GPT/Codex1, HTML regenerado na entrada original. **20 testes do motor e 43 verificações da interface passaram.** Resultado aguarda revisão GLM e integração/apresentação do n0.

## Mudanças

1. Topo: **34 → 15 controles visíveis**. Os14 botões de14 × 24 px viraram um seletor de176 × 44 px; preferências/Reiniciar/velocidade usam o menu ⋯ existente.
2. Narração: tempo acompanha o texto. A mesma fala de26 palavras ficou aproximadamente **2.11s → 9.42s** na captura, incluindo o deslocamento seguinte. O ritmo usa heurística, sem alegar compreensão humana. Barra reserva espaço: topo antes 182.30→192.08px; depois 180.30→180.30px, estável também ao selecionar todas as paradas.
3. Origem/destino: placas e texto seguem as8 linhas. Posição busca área sem cobrir estações/legendas; conectores passam atrás dos títulos dos bairros. No celular, orientação cima→baixo.
4. Pausa vertical: defeito antigo reproduzido **1/14→3/14**; correção chega em **2/14, cliente**. Movimento reduzido durante transição não conserva timer residual.
5. Editor: instrução na barra, sem dica temporária sobre os trilhos. Renomeação, exportação do remendo e Desfazer testados em perfil isolado. Narração inicial conta12 estações, em vez de chamar11 trechos de paradas.
6. HTML: **247,099bytes**, abaixo do limite250 KB. Compacta só a cópia embutida do cursor; canônico intacto, com guarda para futuras strings multilinha. JSON,52 estações,8 linhas e dados/editabilidade preservados.

## Arquivos alterados

- `<MEGABRAIN_ROOT>\motor\modelos\harness-mapa\mapa.js` — SHA256 `e071e0e384d24d7f38d5a1d1506fbf28c7162fb87da9e5d25bcbb828eddb0afd`
- `<MEGABRAIN_ROOT>\motor\modelos\harness-mapa\mapa.css` — SHA256 `17a969b9df6d8aaaad0518ee4e22b85d394cd36d3b613069eb8166e895b6cdc6`
- `<MEGABRAIN_ROOT>\bin\mb-harness-mapa.py` — SHA256 `506f2fbc523d5aa958ddefe3738a2682c3698808164815b5c1bfad50404b812a`
- `<MEGABRAIN_ROOT>\motor\modelos\harness-mapa\LEIAME.md` — SHA256 `bb49bb4d61981982d248c84e9388a785c08f25db4a848605d35ee55cd1c0e20f`
- `<MEGABRAIN_ROOT>\motor\tests\test_mb_harness_mapa.py` — SHA256 `6fe6ec958f4211069daf868b92740066f6dc10fb2a2be1a7c45b8970e9e6bff3`
- `<MEGABRAIN_ROOT>\00_PARA-VOCE\261011_harnesses\261017_MAPA-DO-HARNESS.html` — SHA256 `2d2e05fbbc0067d023247a00b9a1166e8b78ddcedaee012b009ba87b32f5a17c`

`dados/harness-mapa.json` ficou idêntico ao backup. Nenhum cursor/decisão canônico, frontend, backend ou estado global foi editado pelo n4.

## Prova e reprodução

- Evidência detalhada: `<MEGABRAIN_ROOT>\evidence\261018_ponte-orquestradores\mapa-revisao-gpt\resultado.json`; inventário e hashes antes em `inventario-antes.json`, rastreio de escrita em `edicao.json`, canônicos lidos na geração em `geracao-final.json`.
- Testes: `python -B -X utf8 -m unittest discover -s motor/tests -p test_mb_harness_mapa.py -v`; log UTF-8 `testes-motor-final.log`.
- Interface: `apps/ia-quota-widget/.venv/Scripts/python.exe -X utf8 evidence/261018_ponte-orquestradores/mapa-revisao-gpt/fluxo.py fluxo-entrega`; **43/43**, zero erro JS, HTML exato `2d2e05fbbc0067d023247a00b9a1166e8b78ddcedaee012b009ba87b32f5a17c`. JSON `fluxo-entrega/fluxo.json`.
- Prints próprios 1440/390 claro/escuro em `antes/` e `depois/`; todos os processos e menus em `fluxo-entrega/`; bug antigo e placas em `antes-casos/`; tempo completo em `ritmo-final/`. Capturas essenciais foram abertas/inspecionadas. Medidor antigo da crítica contava palavras incorretamente; usamos `split`/`\S+` sobre o texto efetivo.
- CUA não expôs navegador/app nesta sessão. Renderização foi QtWebEngine6.11.2 isolada, sem tocar no perfil ou na mesa reais. Não equivale a prova de apresentação no app.
- Gate: revisão n1 AJUSTAR lida, correções A1–A4 incorporadas por n0 no plano antes da produção. Todos os alvos tinham mais de20 min sem alteração no primeiro inventário; hashes novamente conferidos imediatamente antes das gravações. Complemento de coordenação confirmou interrupção da rodada Claude antes de tocar o mapa.

## Limites e próximo passo do coordenador

1. **n0:** revisão final GLM, integração com n3 e apresentação da mesma entrada no app. Se cursor/decisões mudarem depois dos hashes de `geracao-final.json`, regenerar antes da prova final. Canônicos alterados desde geração neste fechamento: `[]`.
2. Nenhuma ação do <USUARIO> exigida neste nó. Sem aprovação visual/humana presumida, Pixel7 físico, leitura por acessibilidade, clique/teclado físicos ou apresentação nativa alegados. Sem reinício do app, Git/publicação ou painel concorrente.
3. Capturas de leitura completa/ritmo precedem só a troca textual11 paradas→12 estações; o fluxo43 verificações foi repetido no HTML final.

## Reversão

Backup: `<MEGABRAIN_ROOT>\evidence\261018_ponte-orquestradores\mapa-revisao-gpt\backup`. Conferir hashes antes de repor qualquer arquivo; restaurar somente os arquivos deste nó ainda iguais ao resultado registrado. Preservar mudanças posteriores. Regenerar o HTML pela fonte, nunca editar à mão. Não executei restauração.

## Lição técnica registrada para o n0

GATILHO: pausar animação CSS com índice lógico já na próxima estação.
LIÇÃO: cancelar timer e retomar pelo agendador pula a chegada; reproduzido1/14→3/14.
ATALHO: conservar tempo/callback restantes, congelar transform e retomar a mesma chegada; testar movimento reduzido/timer residual. Registro restrito à evidência do nó; estado global reservado ao n0.
