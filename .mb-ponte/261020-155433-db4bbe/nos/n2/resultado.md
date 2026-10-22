# Parecer independente — nó n2

Veredito: **APROVAR COM AJUSTES**. Codex e Claude correspondem às fontes locais consultadas. Há informação incorreta sobre modelos do ZCode e uma lacuna na proteção automatizada do relatório. Nenhum arquivo de implementação foi editado.

## Destino

A tarefa contém referência interna a n1, mas a instrução direta do <USUARIO> e seu fechamento determinam n2/resultado.md. Este é o único parecer gravado; n1 foi preservado.

## Achados

1. **Médio — ZCode suporta seleção de modelo pela CLI, contrariando o catálogo.** `apps/megabrain-dashboard/central_dispatch.py:32`, `:50`, `:51`, `:112`; `motor/modelos/interacoes/261010_decisoes-respondiveis/decisoes-respondiveis.js:30`; `00_PARA-VOCE/261020_cotas-mapa-bapp/261020_RELATORIO.html:107`. Meu `zcode --help` (0.16.9) mostra no final `--model <provider/model>` para execução `--prompt`, sem alterar o padrão salvo. O catálogo oferece somente padrão e a montagem ignora modelo. Corrigir a distinção: modelo tem flag; effort não teve flag encontrada. Permitir seleção de modelo e testar o argumento efetivo, verificando separadamente quais identificadores estão disponíveis/autorizados.

2. **Médio — o teste não protege o HTML entregue contra divergência futura.** `apps/megabrain-dashboard/tests/test_dispatch_catalogo_consistente.py:18`, `:45`, `:48`; relatório `:108`. Os testes comparam Python com JS do motor; não leem o HTML. Minha comparação independente confirma os blocos `var IAS` idênticos hoje. Porém atualizar catálogo e motor sem regenerar o HTML continuará passando nos 9 testes. Incluir a cópia inline no teste ou restringir a promessa de proteção. Os testes verificam listas e strings CLI, não execução real em cada modelo nem atualização automática de capacidades.

3. **Baixo — data Kimi não corresponde à fonte localizada.** `apps/megabrain-dashboard/central_dispatch.py:35`, `:119`; relatório `:107`. O texto declara 16/10, mas a decisão humana localizada está em `memoria/estado/DECISOES.md:2620-2622`, seção `260916e` (16/09). Essa decisão sustenta retirar Kimi do roteamento: a remoção não foi considerada regressão. Corrigir a data ou indicar outra evidência para 16/10.

## Verificação própria

1. `python -m unittest tests.test_dispatch_catalogo_consistente -v`, no dashboard: **9 testes passaram**. Cobrem listas espelhadas, Kimi ausente, ultra/max, rejeição de minimal e strings CLI.
2. `rg -n enabled-reasoning-efforts <USER_HOME>/.codex/config.toml`: linha 180 contém low, medium, high, xhigh, ultra, max. `codex --version`: 0.163.0. Metadados de gpt-6.1-sol em `models_cache.json` também anunciam esses seis níveis. Isso corrobora a configuração; não equivale a chamada executada agora em cada nível/modelo livre.
3. `claude --version`: 2.1.302. `claude --help`: low, medium, high, xhigh, max; exemplos de aliases fable, opus, sonnet. Haiku não aparece nos exemplos consultados e não foi certificado por essa ajuda; exemplos não são lista exclusiva.
4. `zcode --help`: 0.16.9, flag --model presente no final. Nenhuma flag de effort encontrada.
5. `node --check motor/modelos/interacoes/261010_decisoes-respondiveis/decisoes-respondiveis.js`: saída 0.
6. Comparação literal dos blocos `var IAS` com Python: iguais. Extração dos quatro scripts inline e `node --check` via stdin UTF-8: todos saída 0. A primeira tentativa falhou por cp1252 no subprocesso; repetida com bytes UTF-8 e limite de tempo, passou. Era falha do procedimento de revisão, não do artefato.
7. Caminho relativo da imagem popup-zai-detalhes.png resolve para arquivo existente. Não fiz inspeção visual ou interação no aplicativo. Sintaxe e existência não provam layout em 1440/390, conteúdo do print ou controles funcionais.
8. Consultei AGENTS.md, estado/handoff/decisões/lições em memoria/estado e memoria/nucleo; equivalentes na raiz não existem. Git status mostra extenso trabalho concorrente; consultei travas no handoff e datas dos arquivos. Nenhuma alteração alheia foi sobrescrita.

## Limites e pendências

- Corrigir os achados 1 e 2 antes de declarar todas as informações conferidas e a divergência futura impedida. Ajustar a procedência da data Kimi.
- Não certifiquei login Gemini, reinícios de 17:14, redução de instâncias nem a suíte de 638 testes do widget. Extrator Z.ai da sessão paralela ficou fora desta revisão.
- Não abri navegador: o destino de relatórios locais é MegaBrain. Validação visual no aplicativo permanece pendente.
- A suíte ampla `python -m unittest discover -s tests -q` não retornou resumo durante a janela desta revisão e foi interrompida pelo próprio revisor (saída 1). Única saída observada: aviso de depreciação Starlette/httpx. Resultado amplo INCONCLUSIVO; não alego 377 testes aprovados nem atribuo o atraso à alteração. Os 9 testes específicos concluíram normalmente.

## Lição técnica registrada no parecer

GATILHO: catálogo local de capacidades anunciado como conferido com a CLI.
LIÇÃO: espelhos idênticos podem repetir informação errada; --model do ZCode aparece no final da ajuda e escapou do catálogo.
ATALHO: ler a ajuda completa, conferir cada capacidade separadamente e testar também a cópia entregue no HTML.

## Arquivos alterados

Somente este `nos/n2/resultado.md`, resumo técnico solicitado. Nenhuma correção de implementação aplicada: papel de revisor independente. A referência interna a n1 não autorizou sobrescrever o parecer de outro nó.