---
name: amadurecer
description: Amadurecer um pedido antes de executar — leitura de situação de créditos/uso (contas, janelas, discrepâncias), noção de qual projeto pesa no processamento, e só então escolher a rota. Use SEMPRE que o usuário der ordem de criação/execução não-trivial (crie, faça, refaça, revise, gera), ao abrir trabalho em conta medida, ou quando notar uso desequilibrado entre contas.
---

# amadurecer — leitura de situação antes da ordem

**Regra de ouro (pedido do dono, 260916, 2ª correção):** ordem de criar/fazer
NÃO é instrução pra executar cego na sessão atual. É: ler a situação de
créditos e usos → estimar o peso do pedido → escolher a rota que não espreme
uma conta enquanto outra folga → executar → registrar padrão no cérebro.

## Passo a passo (rodar antes de executar)

1. **Leitura real por conta:** `python <CENTRAL>/bin/mb-leitura-uso.py --json`.
   O startup `mb-inicio-sessao.py` já inclui esse snapshot. Ele não atualiza rede:
   medir cotas nos leitores oficiais antes de cada despacho; guardar fonte,
   horário, conta/home, duração e reset de cada janela. Snapshot acima de 300 s
   [HEURÍSTICA] ou inválido = `NAO_MEDIDO`, nunca saldo zero ou folga.
2. **Comparabilidade:** comparar pressão apenas entre janelas de igual duração,
   com todas as restrições da conta consideradas. Menor janela isolada não escolhe
   rota; `base_model_inference` não representa saldo geral Codex. `primary` não
   significa sempre 5 horas. Duração inferida fica separada de medição explícita.
   Ritmo `used_percent / (100 * elapsed_fraction)` só com denominador positivo;
   início da janela é `NAO_MEDIDO`. Percentuais de vendors não equivalem a tokens,
   dinheiro, capacidade ou produtividade.
3. **Plano antes de ferramentas:** listar tarefas úteis, dependências, acesso
   necessário, responsável real, prova esperada e revisor independente. Codex 1
   e Codex 2 são homes/contas distintos; ZCode é o cliente GLM oficial. Verificar
   ferramenta e capacidade junto com a cota. Quem detém Figma pode executar essa
   parte enquanto outro cliente pesquisa, organiza candidatos ou revisa artefatos.
4. **Rota e economia:** distribuir trabalho independente para a conta capaz com
   menor pressão comparável, reservando margem do limite mais restritivo. Separar
   custo observado de [ESTIMATIVA]. Usar contexto mínimo e uma chamada útil por
   papel; não fazer pergunta ao modelo só para descobrir a versão se houver
   metadado/configuração. Cache lido não é token novo, nem prova de consumo de cota.
   Não gastar para equalizar percentuais, duplicar pesquisa sem propósito ou
   atribuir todo delta da conta a esta tarefa quando existem sessões paralelas.
5. **Reavaliar:** repetir medição imediatamente antes do despacho, após erro/429,
   mudança de escopo/capacidade e no fechamento. Não repetir após 429; escolher
   alternativa capaz já autorizada ou registrar bloqueio. Toda rota guarda
   fonte/idade, critérios, trabalho delegado, resultado e motivo de exceção.
6. **Fechar:** comparar o previsto e o realmente executado, registrar desperdício
   evitável e limites de atribuição. A melhoria é distribuição de trabalho útil,
   não garantia de fechar um gap numérico. Atualizar lição/estado sem transformar
   preferência em compra, troca global de conta ou reconfiguração de provider.

## Quando NÃO rodar (não virar burocracia)

- Papo/N0, pergunta rápida, correção local óbvia de 1 arquivo.
- Trabalho já roteado por run V6 aberta (o motor mede cota em cada despacho).
- Emergência de produção — resolver primeiro, amadurecer no post-mortem.

## Automações que sustentam esta skill

- `bin/mb-leitura-uso.py` — a leitura em 1 comando (fonte: orcamento_ia.json).
- Widget Cotas IA — regrava o pacing continuamente (medição viva).
- `bin/mb-codex-quota.py <chave> <home>` — cota de conta codex específica.
- `bin/mb-compreensor.py` — contexto injetado da sessão (fuga de orçamento).
- Cérebro `memoria/cerebro/wiki/` — padrão medido por projeto/conta.

## Pressão desigual: sinal, não diagnóstico automático

Uma diferença de pelo menos 30 pontos percentuais com uma conta acima de 70%
[HEURÍSTICA] chama atenção somente em janelas equivalentes e amostras atuais.
Não comprova erro de rota: ferramenta exclusiva, qualidade exigida, limites de
modelo, dependências ou custo adicional de handoff podem justificar a diferença.
Registrar o motivo; reavaliar tarefas independentes antes do próximo despacho.

## Relatórios: GLM compõe, Codex/Claude revisam (261020)

Ao criar, regenerar ou corrigir relatório humano, aplicar `/relatorios-glm` (fonte central `motor/skills/relatorios-glm/SKILL.md`). GLM principal MAX é compositor obrigatório; Codex/Claude revisam fontes, imagens e controles e podem fornecer modelos finalizados. Última correção substantiva volta ao GLM. Exceção apenas crédito extremo comprovado sem reset útil; falha técnica não troca produtor. Esta regra específica prevalece sobre papéis genéricos anteriores somente para relatórios. Evitar Claude MAX e ultracode. Gate `bin/mb-relatorios-glm.py`, evidência e exemplo promovido por prova; nunca prometer erro zero ou recarga de chats abertos.
