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

1. **Leitura de situação:** `python <CENTRAL>/bin/mb-leitura-uso.py`
   — lê `dados/orcamento_ia.json` (medição viva do widget Cotas IA + motor),
   mostra por conta/janela: uso %, horas pra renovar, veredito
   (folga/apertado/esgotado/não medido) e avisa se há **janela descrepante**
   (uma conta ≥70% enquanto outra com folga ≥30 pontos abaixo).
2. **Peso do pedido:** leve = edição local pequena, resposta única (fica na
   sessão) · médio = leitura de muitos arquivos, varredura, prova, build
   (considerar worker) · pesado = revisão, geração, pesquisa, plano
   (despachar pra conta com folga: worker `claude -p`, `codex exec` no
   CODEX_HOME livre, ou run V6 — o motor mede cota sozinho).
3. **Rota:** pesado vai pra conta com FOLGA medida; a sessão atual comanda e
   consolida. Sessão já apertada + pedido médio/pesado = despachar ou pedir
   pra abrir sessão na conta folgada. Nenhuma conta saudável = dizer e
   esperar janela (renovação de 5h geralmente resolve), sem queimar a última.
4. **Projeto que pega mais processamento:** antes de aceitar "é pesado",
   checar o histórico: `memoria/cerebro/wiki/` (tópicos de uso) e
   `dados/telemetria-orquestracao.json` (240 eventos recentes por
   provider/modelo). Projeto repetidamente caro = candidato a fase menor,
   worker barato ou fatia.
5. **Registrar:** decisão de rota não-óbvia ou discrepância vista → 1 tópico
   curto em `memoria/cerebro/wiki/YYMMDD_<tema>.md` (reindexa com
   `bin/mb-indice-cerebro.py`) e, se virou regra de trabalho, lição via
   `/registrar-licao`.

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

## Janela descrepante (definição prática)

Uma conta ≥70% de uso enquanto outra ≥30 pontos abaixo de folga = erro de
roteamento, não azar. Quem decide o canal é a leitura, não o hábito
("sempre abro no Z"/"sempre no Claude" é o bug).
