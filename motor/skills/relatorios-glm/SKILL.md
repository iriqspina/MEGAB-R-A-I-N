---
name: relatorios-glm
description: Produzir e corrigir relatórios MegaBrain com GLM principal MAX, revisão independente por Codex ou Claude e aprendizado por exemplos verificados. Use ao criar, regenerar ou corrigir relatório humano; não ativa para conversa simples nem obriga migrar relatórios antigos.
---

# Relatórios com GLM · produção e correção verificáveis

GLM principal em MAX é o compositor obrigatório de cada relatório novo ou regenerado. Codex e Claude coordenam, revisam, observam imagens e podem criar modelos/mockups finalizados. GLM adapta os modelos e aplica a última correção substantiva. Gravação e injeção mecânica de componentes não trocam autoria. Nunca medir autoria por bytes.

## Entrada e fontes

1. Resolver a central via `.mb-origem.json`, `MEGABRAIN.md` e `bin/`. Ler identidade e `/amadurecer`; preservar tarefa, entrada, decisões e exclusões humanas.
2. Ler `motor/skills/antierro-ia/ias/zcode-glm/limites.jsonl` e os exemplos pertinentes. O GLM textual atual não inspeciona pixels: Codex/Claude precisa ver imagens reais. Enviar ao GLM defeito observado, seletor, posição, dimensões, referência e correção esperada.
3. Preparar pacote mínimo: pergunta/decisão, fatos com fontes e datas, fontes visuais finalizadas com origem e aprovação, modelo mestre POP versionado, padrão de interações, exemplos pertinentes e negativos. Referência candidata não é exemplar aprovado; preferências não se promovem a regras universais.

## Rota executável

Usar `/orquestracao1` para plano e revisão, congelando o despacho. O motor V6 genérico não comprova provider GLM. Produção textual usa `python bin/mb-produzir-relatorio-glm.py --project RAIZ --prompt evidence/TAREFA/pedido.txt --run-dir evidence/TAREFA/producao-N --output evidence/TAREFA/fragment-N.html`. Esse adaptador reaproveita o runtime oficial certificado e os helpers de `apps/megabrain-dashboard/model_clients.py`, com perfil local `build`, ferramentas negadas e MAX comprovado no tráfego nativo. Não altera a configuração global nem usa API extra. A saída é candidata; nunca pronta por código de saída.

O adaptador inclui este contrato e o mestre POP explicitamente, porque skills/memória/ferramentas ficam desligadas. O solicitante inclui fatos e exemplos pertinentes no arquivo do pedido; ele compõe HTML e o coordenador monta mecanicamente. JSON nativo pode ser formatado, não JSONL. Não usar `--settings` nessa instalação: flag foi recusada pelo runtime real; a configuração isolada é lida pelo cwd. O wrapper genérico em modo `plan` produziu saída degenerada neste ensaio, portanto não é a rota de composição. Revalidar estes limites ao trocar runtime; não prometer que instalar uma skill muda sessão já aberta.

## Ciclo de entrega

1. GLM compõe o candidato usando o modelo mestre. Codex/Claude testa DOM, fontes, links e controles e inspeciona prints 1440 e 390 px (dois tamanhos, não prova em telefone físico). Legibilidade, ordem, hierarquia e ação clara são critérios; presença de imagem não prova entendimento.
2. Cada achado registra hash da versão, autoria real, classe de erro, evidência, consequência e teste de aceite. Separar fala humana, observação e inferência. Revisor não inventa números, identidade ou resultado; sua opinião pode ser refutada pela fonte.
3. Devolver achados ao GLM; GLM corrige e explica o que mudou. Renderizar novamente. Alteração substantiva invalida revisão e prints anteriores. Usar o gate `bin/mb-relatorios-glm.py` conforme [contrato-cli.md](references/contrato-cli.md).
4. Após duas correções sem melhora, abrir nova sessão GLM com pacote congelado de fontes, melhor candidato, achados e exemplos; não carregar a conversa inteira. Limite de três correções por execução é [HEURÍSTICA] para conter gasto, não autorização para outro fornecedor finalizar. Persistindo bloqueio, registrar pendência e preservar o melhor candidato.
5. Entregar somente após gate da versão final; abrir pela central nativa (`bin/mb-abrir-entrega.py`). Separar arquivo encontrado, indexado, apresentado e interação observada. Nenhum desses estados equivale à aprovação humana.

## Aprendizado fechado

Registrar caso → erro → correção GLM → prova antes/depois → teste reproduzível. Guardar ocorrências na skill antierro (IA `zcode-glm`) e o ciclo versionado em `evidence/` do projeto. Só promover modelo/componente para biblioteca central depois da revisão independente e verificação visual, preservando origem, hashes, revisor e formatos vistos. Reprovação humana revoga o exemplar ativo sem apagar histórico.

Biblioteca: `motor/modelos/relatorios/glm/` (índice, candidatos, promovidos e testes). Recuperar apenas `promoted` ativos do índice, nunca revogações ou pastas encontradas por nome; `promote` registra aprovação técnica, e `revoke --reason ... --evidence ...` retira o hash ativo sem apagar o histórico. Mudar composição funcional (comparação, esteira, cronologia, decisão), preservando tokens/estilo POP e acessibilidade. Não variar layout por decoração. Modelo novo permanece candidato até aprovação técnica; gosto/negócio sem default segue decisão humana.

Uma nova versão do processo é candidata: comparar com o caso que motivou a mudança e ao menos um caso anterior pertinente; promover somente se o critério novo passa e o anterior continua passando. Reverter a referência ativa quando houver piora comprovada. Guardar métricas separadas: primeira passagem, erros por classe, recorrência, rodadas e exceções por relatório; sem amostra = NAO_MEDIDO. Não somar percentuais de assinatura nem chamar cópia de treinamento dos pesos. A melhoria é de processo, referências e verificadores; zero erro não é garantia.

## Exceção estreita e economia

Só crédito GLM extremo comprovado e sem reset útil ao prazo permite compositor substituto. Registrar conta, fonte recente, janelas aplicáveis, prazo, reset e motivo. Limiar até 5% restante é [HEURÍSTICA] conservadora para análise, não permissão automática; reset desconhecido, indisponibilidade, dificuldade visual ou demora não justificam exceção. Sem comprovação, aguardar GLM e registrar bloqueio; nunca trocar silenciosamente.

Claude evita MAX e ultracode por determinação humana de 20/10/2026; usar Codex para revisão quando suficiente. Resets, compra e APIs extras não estão autorizados. Ao novo reset, medir novamente; preferência por economia permanece até orientação nova. Corrigir erros sem gastar apenas para igualar cotas.

## Fechamento e propagação

Revisar conformidade do próprio relatório e registrar produtor/revisores reais. Distribuição em disco não comprova leitura nem execução. Atualização central `261020-relatorios-glm-max` deve continuar pendente no projeto até execução ali verificada. Projetos pausados recebem apenas a regra; não retomar modelos, automações ou tarefas. Não alterar pipeline congelada de ordem em andamento.

Fiscalização mecânica: startup e `bin/mb-auditar-relatorios-glm.py --root RAIZ_PROJETOS` revalidam hashes e mantêm fila só quando os dados mudam, sem chamar modelos. O comando de apresentação bloqueia novo/alterado sem manifesto entregue, preserva legado idêntico ao baseline como não auditado e permite `--preview` explicitamente candidato. Abertura direta pelo app ainda fica fora desse bloqueio: a varredura detecta a lacuna, não equivale a controle universal. Acompanhamento de 6h desta conversa só atua em mudanças relevantes de tarefas autorizadas, sem reescrever legado em lote. Nunca confundir fila com correção executada.
