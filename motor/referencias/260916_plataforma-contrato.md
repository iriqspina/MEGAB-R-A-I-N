# Organização e evolução do MEGABRAIN · 260916

Fonte: pedido direto de <USUARIO>. Objetivo: encontrar a entrega certa, entender a ação da IA e preservar capacidades. Provas em `evidence/260916_plataforma/`; conforto e tempo real de uso ainda dependem de observação humana.

## Endereços fixos

| Função | Destino | Regra |
|---|---|---|
| Entrada humana | `00_PARA-VOCE/INICIO.html` | Um catálogo por projeto; não duplicar dados dos widgets. |
| Entrega de tarefa | `00_PARA-VOCE/YYMMDD_tarefa/` | Um arquivo principal e recursos. Projeto, tarefa, sessão, estado e próxima ação explícitos. |
| Arquivo humano | `00_PARA-VOCE/_arquivo/AAAA-MM/` | Só mover após mapear consumidores. Pode arquivar no registro sem mover. |
| Registro | `dados/entregas.json` | Metadados explícitos; pronto exige prova do conteúdo atual. |
| Estado | `memoria/estado/` | Bloco vigente identificado; histórico não vira pendência automaticamente. |
| Conhecimento | `memoria/cerebro/` | raw para fontes, wiki para conhecimento destilado. |
| Comportamento | `memoria/identidade/` + `motor/skills/` | Fonte única, sincronização oficial, verificação dos destinos. |
| Programa | `bin/`, `motor/`, `apps/` | Um dono por função; consumidores mapeados antes de mover. |
| Provas e backup | `evidence/YYMMDD_tarefa/` | Testes e capturas fora da pasta humana. |
| Execuções de IA | `.automations/runs/ID/` | Revisão textual não é prova de aplicação. |
| Legado | Caminhos existentes | Preservados por compatibilidade; recolhidos no catálogo. |

Não criar outra pasta de entrega por conveniência. Regra para novas escritas; migração física do acervo requer conferir links e sessões ativas. `00_painel/RELATORIO.html` mantém o endereço usado pelos programas.

## Mesma esteira, etapas proporcionais

Todo pedido é avaliado por contexto, intenção, artefato, risco, evidência, ambiguidade e autorização. `bin/mb_triagem.py` recomenda etapas com motivo. É uma heurística por regras: pode omitir sinais ou produzir falsos positivos. A IA confere a conversa inteira; palavra ou “sim” isolado não concede autorização.

1. Conversa: resposta curta, sem criar plano ou relatório por obrigação.
2. Pergunta: responder e verificar o que afirma; dados atuais ou incertos exigem fonte.
3. Entrega: critério, produção, revisão, prova e destino verificável.
4. Ação sensível: acumular exigências pertinentes e respeitar autorização já concedida.

Sensibilidade enxuta/equilibrada/criteriosa muda só revisões opcionais. Mantém o piso de qualidade e não altera modelo, gasto ou permissão. Preferência do projeto vence a central. Configuração inválida gera aviso, não flexibilização.

`mb-contexto.py` injeta a recomendação se o cliente invocar o hook. Nos demais clientes, o contrato comum orienta a IA. Fonte escrita, cópia instalada e uso em sessão nova são provas diferentes. Não anunciar integração universal sem teste por cliente.

## Resposta e interface

Conversa fica curta. Entrega informa resultado e estado, projeto/tarefa quando há sessões paralelas, link com caminho absoluto testado e pasta completa em bloco de código. Esse bloco permite copiar nos clientes que oferecem o controle; não inventar botão no chat.

HTML/aplicativo oferecem Abrir entrega, Abrir pasta e Copiar caminho. Falha de cópia mantém campo selecionável. No navegador, pasta pode abrir como listagem; no aplicativo, abre no gerenciador de arquivos. O agente abre só a entrada essencial ao entregar.

O registro aceita `pedido_inicial`, `pedido_atual` e `etapa`: resumos explícitos da sessão, exibidos como Começou/Agora/Etapa e incluídos na busca. Não copiar o histórico integral, não inferir progresso por tempo e não exigir campos em entregas antigas. Modelo em `motor/modelos/260916_ENTREGA.json`; bloco de estado vigente em `motor/modelos/260916_ESTADO-ATUAL.md`.

Ocultar pasta no Windows pode retirar arquivos das buscas de algumas ferramentas. O piloto do plano UX do Claude depende de demonstrar recuperação dos mesmos arquivos nos clientes afetados, manifesto dos atributos anteriores e reversão. Preservar endereços, sozinho, não prova ausência de piora.

## Evolução sem piora

Toda mudança declara problema observado, evidência, hipótese, benefício e custo. Registrar situação inicial, consumidores, testes e reversão. Distinguir teste automático, revisão de IA e aceite humano. Se o arquivo mudar, a prova anterior perde validade.

Backlog único em `dados/plataforma-backlog.json`: dono, fonte, critério e dependências. Não gerar relatório por observação. Templates fixam estrutura de entrega/estado/revisão; conteúdo, evidência e solução continuam específicos. Nova superfície precisa declarar qual tarefa atende ou qual superfície substitui.
