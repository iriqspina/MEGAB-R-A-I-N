# SPEC FASE 2 — decisões de 260824 (tarde) que viram implementação

Fonte: conversa <USUARIO> × Claude, 260824. Este arquivo é a ponte entre o que
ele decidiu e as sessões de implementação. Cada seção tem DONO e MOMENTO.
Boards citados = `03_docs/260824_megabrain-do-zero.html`.

## 0. Vocabulário

- **megabrain do projeto** = a pasta `MEGABRAIN\` dentro de cada projeto
  (termo oficial; substitui "cópia de projeto"). Se "cópia de projeto"
  aparecer em outro contexto e não for óbvio, perguntar.
- **DNA do usuário** = `dna/usuario/YYMMDD/` — backup imaculado LOCAL das
  infos pessoais. "Imaculado" = intocável. Nunca sobe (já no .gitignore).
- **Neuron** = apelido do Gerente Neuron. Papel: pet observador do PC, NÃO
  escolhe modelo.
- "megabrian" = typo de megabrain. Entender e seguir.

## 1. Relatório vivo → workspace com abas (dono: Claude · sessões dedicadas)

Regra mantida: UM relatório vivo por instância (megabrain e cada projeto).
Tudo abaixo acontece DENTRO dele, no gerador `bin/mb-relatorio-vivo.py`:

- **Abas**: Dashboard (default) · Esquema do megabrain · Ações (os .cmd como
  botões: copiar comando + apontar arquivo) · Skills (os poderes, 1 linha
  cada) · Cérebro · Histórico (retrátil, no fim).
- **Multi-painel**: o leitor pode abrir N abas lado a lado (grade que ele
  monta, estilo workspace do Illustrator) — todas funcionais e atualizadas.
- **Workspace salvável**: layout escolhido persiste (localStorage com
  namespace por arquivo — lição 260822: Chrome compartilha origem em file://).
- **Controles fixos**: tamanho de elementos (densidade) e tamanho de fonte,
  com clamp — nada vaza da caixa em nenhum tema/modo.
- **Dashboard**: infográficos e ícones de estado/andamento (não só texto);
  configurações manipuláveis na própria visão, sem entrar em categoria;
  modo de inteligência atual sempre visível.
- **Aba "Esquema do megabrain"**: os desenhos do doc-do-zero (central →
  GitHub → central do usuário → megabrains de projeto; funções de cada peça)
  no estilo visual dos boards. Fica abaixo/depois do dashboard em prioridade.
- **Componente pergunta**: sempre que o relatório responde algo, mostrar a
  pergunta sendo respondida (padrão .ask do doc — validado por ele).
- **Feedback rail** fixo à direita (ver §3).

## 2. Canal de ideias e anotações do usuário (dono: Claude · junto do §1)

- Durante o projeto, ideias sobre o megabrain vão para
  `MEGABRAIN/IDEIAS.md` do projeto (anotar ≠ editar o megabrain).
- Na "edição do megabrain" do usuário, essa fila vira pontos concretos de
  alteração (pipeline geral e/ou do projeto).
- Lição/ideia generalizável + validada + sem dados do usuário → candidata a
  subir pra matriz (fluxo do board 04·D). Fazer sempre que couber.

## 3. Feedback + consentimento (dono: Claude · junto do §1)

- Rail fixo à direita do dashboard: 👍 like de 1 clique · campo de texto
  livre ("escreveu, enviou") · envio de lição generalizada.
- **Opt-in explícito** na instalação/primeira geração do relatório (e em
  versão antiga que ganhar a mecânica): nada é enviado sem o usuário ligar.
  Consentimento é necessário sim (lei de dados + confiança) — e o envio é
  sempre genérico: a limpeza remove nomes, caminhos e dados pessoais.
- Texto do aviso (manter o riscado):
  "Nada aqui sai com seus dados: lições e feedback só sobem depois de uma
  limpeza que remove nomes, caminhos e qualquer coisa pessoal — e só se você
  ativar o envio. A gente valoriza demais usuário que ~~mete o pau~~ critica
  construtivamente: este é um projeto independente e solo, e a experiência de
  quem usa é o que faz ele melhorar."

## 4. Telemetria — dado bruto local (dono: Claude · base: .mb-log/)

Registrar por evento (JSONL, local-first, nunca sobe sem opt-in e agregação):
skill usada (p/ pesos de frequência) · timestamp · duração da resposta ·
modelo usado · modo de inteligência · gates rodados · cliente (Cowork / CLI /
browser / terminal) · SO · projeto (id) · resultado (ok/erro).
Formato genérico para RECEBER qualquer dado; VALORES nunca são generalizados
(ex.: "RTX 4070" registra "RTX 4070"). Uso: otimização, compreensão, evolução;
alimenta o Neuron (§6) e os "compreensores" (§7).

## 5. Cérebro: temporário × permanente (dono: Claude · skill nova)

- `wiki/` = conhecimento de longo prazo. Novo: front-matter `VALIDADE:` (ou
  subpasta `wiki/tempo/YYQn/`) pra informação útil hoje mas não daqui 1 ano,
  fragmentada por período — serve também pra medir erro de julgamento
  (quantos "temporários" foram renovados).
- Skill de manutenção roda em frequência com lógica (semanal ou a cada N
  sessões — NUNCA todo prompt): detecta vencidos, AVISA o usuário e move pra
  `90_arquivo/` (nunca apaga).

## 6. Neuron = pet do PC (dono: Claude · depois do §1)

Sem escolha de modelo (fica com o processamento normal da sessão). Papel:
visão geral do PC e dos projetos, telemetria (§4), botões do painel, índice
de "onde está cada coisa". Ideia registrada pra depois: evoluir como pet
(presença, personalidade, avisos).

## 7. Compreensores de padrões (dono: Claude · depois do §4)

Job periódico que cruza projetos × cérebro × identidade × telemetria pra
extrair padrões e templatizar/generalizar. Depende da telemetria existir.

## 8. Modelo por tarefa — máximo sem desperdício (regra imediata, toda sessão)

Inteligente ≠ gastão: tarefa mecânica/varredura roda no modelo equivalente
mais barato que dá conta (Sonnet, Kimi, local COMPROVADO); julgamento,
decisão, auditoria e entrega final ficam no topo. Local ruim gerando resposta
continua proibido.

## 9. Fila de aprovações já dadas (260824)

1. Tirar peso (skill 556→curta + HANDOFF dieta) — AUTORIZADO ("vai lá e
   faça") · próxima sessão, item único, com teste + rebuild do plugin.
2. Dashboard/workspace (§1–3) — AUTORIZADO · sessões dedicadas na sequência.
3. Neuron sem faixas + telemetria (§4/§6) — AUTORIZADO.
4. Reorg de pastas (board 15·B) — APROVADA com condição "não quebrar nada" →
   sessão dedicada: mapear → mover → reapontar → testar.
5. Obsidian: <USUARIO> instala o app; Claude aponta o vault em `memoria/cerebro`
   (.gitignore já preparado).
6. Figma: aplicar as 4 correções do board 24 no arquivo Planejamento-visual.
7. Modos: PAUSADOS no máximo; pesquisar referências/gits sobre sistemas de
   modos pra ele estudar antes de desenvolver.
8. Portfólio: registrar o megabrain como case (nota em memoria/pendencias).
