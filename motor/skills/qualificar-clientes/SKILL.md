---
name: qualificar-clientes
description: Pesquisa empresas e cruza necessidades com serviços comprovados do <USUARIO>, mantém comparação e histórico comercial e prepara revisão visual em lotes de cinco. Use ao qualificar prospectos, retomar um lote ou atualizar fichas; não envia campanhas.
---

# Qualificar clientes

Fonte canônica deste procedimento no Mega Brain. Projeto inicial: `<PROJETOS_ROOT>/Marketeiro`.

## Retomar sem perder trabalho

Leia estado, handoff, decisões recentes e trava. A base de identidade é `dados/empresas.json`; pesquisa e serviços são coleções vinculadas por ID. Consulte `dados/260915_contrato-clientes.json` e a última entrega em `00_PARA-VOCE/260915_clientes/`. Não confunda cadastro, candidato histórico, pesquisa parcial, pesquisa revisada e aprovação humana.

Preserve os 60 cadastros do inventário inicial e descubra mudanças no disco; o número não é limite. Não some seleção e universo. Empreendimento, filial, grupo e contratante podem ser entidades diferentes: registre relação antes de unir ou criar duplicata.

## Ciclo de cinco

1. **Pesquisar.** Releia fontes do cérebro. Verifique nome, endereço, domínio, CNPJ empresarial e canais. Abra a home e as páginas citadas; um artigo ruim não descreve todo o site. Para análise visual, capture tela renderizada, URL, data e viewport. Instagram bloqueado ou CNPJ inacessível é limitação, não ausência.
2. **Definir.** Para cada necessidade, separe observação, impacto presumido e pergunta de validação. Redija um problema testável: público + tarefa + obstáculo observado + como verificar. Site feio não prova perda de venda, solvência nem interesse em contratar.
3. **Explorar.** Cruze necessidades com o catálogo: capacidade comprovada no escopo, declarada, experimental ou dependente de parceiro. Escolha uma oferta de entrada e uma alternativa; deixe outras condicionais. Software não é produto. Apps simples/médios/complexos exigem fronteira de integrações, dados, suporte e criticidade. Felipe e Lucas são parceiros potenciais até confirmação.
4. **Revisar.** Entregue ficha, comparação e prints no Figma, com texto editável e espaço para leitura do <USUARIO>. Pare na revisão do lote antes de avançar a pesquisa de outros cinco; cadastro da fila pode ser automatizado. Preço, canal de campanha e mensagens são etapa posterior.

Registre `lote_revisado` com a crítica recebida e os ajustes aplicados. Um pedido explícito do <USUARIO> para avançar também libera o próximo lote e entra como evento `avanco_solicitado`; não transforma as ofertas anteriores em aprovadas. Silêncio não libera lote.

Elegibilidade da oferta: comprovada no escopo → candidata principal/alternativa; declarada → diagnóstico ou amostra delimitada, nunca promessa de entrega completa; experimental → piloto com critério de saída; parceiro potencial → proposta condicionada à confirmação do parceiro. App de alta complexidade sem case não vira oferta principal: primeiro definir risco, equipe e prova de conceito. “Comprovada” por relato profissional deve manter esse nível de prova visível.

## Evidência e relacionamento

- Cada afirmação: ID, empresa, fonte, data da fonte, acesso, tipo, limite e fato/hipótese/ausência. Fonte primária preferida. Consulta hoje a agregador antigo não torna dado atual.
- Sócios: nome e função empresarial pública quando inequívocos. Não coletar CPF, dívida pessoal, antecedentes ou outros dados privados sensíveis. Riscos pesquisados dizem respeito à pessoa jurídica e ao trabalho contratado.
- Reclamação é relato atribuído; processo é procedimento com estado, não condenação. Homônimo ou razão social sem vinculação suficiente fica não atribuível. Ausência de resultado não é atestado de segurança.
- Separe reviews de consumidor, trabalhador e experiência do <USUARIO>. Fonte própria é testemunho selecionado, não amostra independente. Registre volume, período, temas, resposta da empresa e limites; não publicar identificadores de avaliadores.
- Evento de relação é append-only com data, tipo, resumo, evidência, próximo passo e estado. Pesquisa não é contato. Sem registro recuperado não significa nunca houve relação. Proposta, aceite, entrega, pagamento e recusa são eventos distintos.

## Comparação

Use pesos e régua explicitamente versionados. Falta de dado fica vazia, não zero. Benefício comercial, confiança, risco empresarial e relação ficam separados. Só ranquear diretamente fichas com as mesmas dimensões avaliadas; cobertura mínima padrão integral. Remover nota reduz elegibilidade, não promove empresa. Notas estéticas históricas nunca viram benefício por simples inversão.

A cobertura integral se refere às quatro dimensões comerciais, não a todos os campos cadastrais. CNPJ ausente mantém `identidade_juridica_pendente`: a pesquisa e hipótese de oferta continuam, mas situação oficial não pode ser declarada e identificação contratual precisa ser resolvida antes de contrato/faturamento. CNPJ ausente sozinho não recebe nota comercial zero.

Quantidade de produtos é descritiva: não premiar cardápio inflado. Capacidade de pagar não se deduz de bairro, capital social ou fachada. Ao haver relação, medir prazo de resposta, cumprimento de acordo, retrabalho fora do combinado, pagamento, esforço/margem realizada e satisfação do <USUARIO> com evidência.

## Orquestração e preservação

Use `/orquestracao1` para trabalho novo decomponível. Antes de despachar: modelo realmente disponível, cota de cada janela, horário de renovação e idade da leitura. Cota desconhecida não é saudável; Sol somente abaixo do teto de 90% pedido pelo <USUARIO>. Não fixar Astra para todo planejamento. Modelos e computer-use são escolhidos por teste da tarefa, não por reputação presumida. GLM web longo continua condicionado a teste solo com escrita incremental; não repetir 429/1302.

Planilha e Figma são editáveis, sem sincronização automática prometida. Antes de atualizar: capturar arquivo/textos/posição atuais, comparar com a última exportação e a base atual, preservar alterações humanas. Conflito no mesmo campo interrompe só a substituição daquele campo. Nunca regenerar por cima de uma planilha alterada. Guarde hash, IDs e baseline; use o builder para versão nova e concilie mudanças.

Verifique fórmulas mudando/restaurando peso e nota, links, contagem, arquivos abertos e telas do Figma; leia de volta textos. Revise uma vez com agente independente. Atualize estado/handoff e registre lição específica quando houver aprendizado real. Envio, publicação, gastos e Git não são autorizados por esta skill.
## Modelos de produto e prévias · pedido 260915

Depois de triangular empresa, necessidade e capacidade, siga [templates por necessidade](../../referencias/260915_templates-por-necessidade.md) quando houver oportunidade de reutilização. Compare estrutura, fluxo, conteúdo existente e características de marca; registre família candidata e exceções antes de desenhar. Sites: explorar duas alternativas e até três famílias se justificadas; teto de três por produto, não por cliente. Não construir versão final agora.

Aprofunde com <USUARIO> etapa por etapa: perguntas em lista, relato falado → decisões/hipóteses/pendências. A análise dos grupos e a escolha visual são etapas diferentes. Entrega desta extensão: dados/260915_mapa-templates.json e 00_PARA-VOCE/260915_clientes/260915_templates-produtos.md. Mapa inicial usa somente os cinco pesquisados; não define quantidade elegível nos demais 55.

Prévia pequena pode ter acabamento alto: preservar o núcleo reutilizável e personalizar problema, conteúdo, identidade e provas. App pede recorte de conceito/fluxo, sem app completo; mockup apoia a demonstração. Escolher e testar mecanismo de acesso antes de prometer expiração. Preço, publicação e envio continuam etapas posteriores.
