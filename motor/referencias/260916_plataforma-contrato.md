# Organização e evolução do MEGABRAIN · 260916

Fonte: pedido direto de <USUARIO>. Objetivo: encontrar a entrega certa, entender a ação da IA e preservar capacidades. Provas em `evidence/260916_plataforma/`; conforto e tempo real de uso ainda dependem de observação humana.

## Endereços fixos

| Função | Destino | Regra |
|---|---|---|
| Entrada humana | `00_PARA-VOCE/INICIO.html` | Um catálogo por projeto; não duplicar dados dos widgets. |
| Entrega de tarefa | Pasta estável sob `00_PARA-VOCE`, dentro do assunto vigente | Reusar a mesma pasta e entrada em todas as revisões; data identifica a abertura. Projeto, tarefa, estado e próxima ação explícitos. |
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

## Pasta estável por tarefa · 261002

Pedido direto de <USUARIO>: organizar todas as entregas numa organização fixa e manter isso em toda resposta e no pipeline MEGABRAIN.

1. Antes de produzir, resolver a tarefa existente, seu assunto, pasta e entrada principal. Reusar esses endereços nas revisões; não criar outra pasta, painel ou índice por rodada. Respeitar a organização humana de cada projeto.
2. Quando aplicável, resultado atual, candidatos e histórico ficam em categorias claras (`resultado/`, `candidatos/`, `historico/`) dentro da tarefa. Criar só o necessário; plano/rota/logs/provas/backups ficam na área técnica.
3. Respostas sobre a entrega apontam à mesma entrada absoluta testada. A entrada existente do projeto continua sendo o catálogo; atualização de uma tarefa não cria um catálogo paralelo.
4. Validar o conteúdo físico e os links/recursos antes e depois de consolidar. Preservar edições humanas, consumidores e reversão; não declarar organização somente porque o HTML mudou.
5. Persistir correções e exclusões em fonte/manifesto consumido pelos geradores. Em acervos de pessoas, candidato e confirmado são estados distintos: nome, caminho, origem e autoria/metadado não identificam a pessoa fotografada. Registrar a base de qualquer confirmação.

O princípio é global; a estrutura física exata depende do projeto. Este pedido não autoriza migrar em lote outros projetos nem reabrir aprovações estéticas. A V6 mantém novos rascunhos técnicos em `.automations/runs/ID/entrega-rascunho/`; o coordenador consolida a entrega humana no endereço da tarefa. Execuções antigas preservam seus caminhos congelados.

## Mesma esteira, etapas proporcionais

Todo pedido é avaliado por contexto, intenção, artefato, risco, evidência, ambiguidade e autorização. `bin/mb_triagem.py` recomenda etapas com motivo. É uma heurística por regras: pode omitir sinais ou produzir falsos positivos. A IA confere a conversa inteira; palavra ou “sim” isolado não concede autorização.

1. Conversa: resposta curta, sem criar plano ou relatório por obrigação.
2. Pergunta: responder e verificar o que afirma; dados atuais ou incertos exigem fonte.
3. Entrega: critério, produção, revisão, prova e destino verificável.
4. Ação sensível: acumular exigências pertinentes e respeitar autorização já concedida.

Sensibilidade enxuta/equilibrada/criteriosa muda só revisões opcionais. Mantém o piso de qualidade e não altera modelo, gasto ou permissão. Preferência do projeto vence a central. Configuração inválida gera aviso, não flexibilização.

`mb-contexto.py` injeta a recomendação se o cliente invocar o hook. Nos demais clientes, o contrato comum orienta a IA. Fonte escrita, cópia instalada e uso em sessão nova são provas diferentes. Não anunciar integração universal sem teste por cliente.

## Resposta e interface

**Leitura humana em HTML (261002):** documentos para <USUARIO> ler ou decidir usam o padrão visual vigente, com resultado/sumário e ações claros, detalhes recolhidos e links funcionais. Ser conciso e visual; uma conversão de Markdown em paredão de texto não atende. Reusar a pasta e a entrada da tarefa. Não entregar `.md` nem pedir sua abertura: Markdown é fonte/estado/evidência técnica entre agentes, fora da pasta humana. Outro formato cabe por pedido explícito ou necessidade específica, como editável nativo; imagens, vídeos e peças solicitadas mantêm o próprio formato, com HTML apenas como acesso quando útil.

Conversa fica curta. Entrega informa resultado e estado, projeto/tarefa quando há sessões paralelas, link com caminho absoluto testado e pasta completa em bloco de código. Esse bloco permite copiar nos clientes que oferecem o controle; não inventar botão no chat.

HTML/aplicativo oferecem Abrir entrega, Abrir pasta e Copiar caminho. Falha de cópia mantém campo selecionável. No navegador, pasta pode abrir como listagem; no aplicativo, abre no gerenciador de arquivos. O agente abre só a entrada essencial ao entregar.

O registro aceita `pedido_inicial`, `pedido_atual` e `etapa`: resumos explícitos da sessão, exibidos como Começou/Agora/Etapa e incluídos na busca. Não copiar o histórico integral, não inferir progresso por tempo e não exigir campos em entregas antigas. Modelo em `motor/modelos/260916_ENTREGA.json`; bloco de estado vigente em `motor/modelos/260916_ESTADO-ATUAL.md`.

Ocultar pasta no Windows pode retirar arquivos das buscas de algumas ferramentas. O piloto do plano UX do Claude depende de demonstrar recuperação dos mesmos arquivos nos clientes afetados, manifesto dos atributos anteriores e reversão. Preservar endereços, sozinho, não prova ausência de piora.

## Evolução sem piora

Toda mudança declara problema observado, evidência, hipótese, benefício e custo. Registrar situação inicial, consumidores, testes e reversão. Distinguir teste automático, revisão de IA e aceite humano. Se o arquivo mudar, a prova anterior perde validade.

Backlog único em `dados/plataforma-backlog.json`: dono, fonte, critério e dependências. Não gerar relatório por observação. Templates fixam estrutura de entrega/estado/revisão; conteúdo, evidência e solução continuam específicos. Nova superfície precisa declarar qual tarefa atende ou qual superfície substitui.

## Relatórios: recente primeiro (261010, pedido direto)

RELATORIO-ORDEM: recente_primeiro · 261010 · ativo globalmente.
<USUARIO>: "nos relatórios deixa as coisas e respostas mais recentes em cima, as coisas mais antigar sempre mais pra baixo e indo até o final, lembrar disso em todos os megabrains, inclusive central".

1. Toda entrada HTML de tarefa, caso ou central apresenta primeiro o resultado e a resposta mais recentes; respostas e versões anteriores descem em ordem cronológica decrescente até o fim.
2. Usar data/hora explícita quando existirem, preservar autoria, fontes e correções. Atualizar a data de revisão não atualiza a data da evidência antiga. Não inverter etapas de um procedimento sequencial nem falsificar datas ausentes para ordenar.
3. Reutilizar a mesma entrada. Histórico técnico pode manter append; o gerador da visão humana ordena pelos registros reais. Não duplicar painel, apagar história ou migrar outros projetos para aplicar a regra.
4. Cada assunto segue o padrão visual vigente: imagem com origem e função (prova ou ilustração), ícones e texto curto. Imagem decorativa, anúncio encontrado e mockup não provam vendas, demanda ou rentabilidade.

Fonte literal: memoria/cerebro/raw/261010_pedido-fable-casos-relatorios.md.

## Rotas prontas antes do plano (261010, pedido direto)

ROTAS-PRONTAS: antes_do_plano · 261010 · ativo na orquestração total.
<USUARIO>: "adicione isso à orquestração total", com print pedindo estudo de mercado e ferramental atual, processos existentes, plugins, MCPs e softwares para automatizar sem começar do zero.

1. Em monetização, automação ou escolha de processo novo, pesquisar rotas existentes antes de fechar o plano: integrações nativas, plugins, MCPs, softwares e processo operacional. Reusar pesquisa recente pertinente, conferindo o que pode ter mudado; conversa simples não dispara estudo.
2. Comparar opções úteis por adequação ao caso, acesso e país, custo atual com fonte/data, manutenção, limitações e prova disponível. Distinguir capacidade documentada, acesso disponível, conexão testada e resultado observado. Mercado exige separar oferta/preço anunciado de demanda/venda comprovada.
3. O plano declara a rota escolhida, a alternativa descartada, o custo da escolha e as lacunas. Código próprio requer explicar a lacuna que uma rota pronta não resolve; disponibilidade de ferramenta não obriga usá-la.
4. Congelar fontes e comparação na evidência do caso e incluir o resultado visual na mesma entrada HTML, recente primeiro. Cadastro, compra, publicação ou contato comercial dependem do escopo autorizado; instalar regra não prova execução futura nem recarga de sessões abertas.

Fonte: memoria/cerebro/raw/261010_conversa-rotas-prontas.md; print original preservado no Caso 1 de Monetarização automatizada.
