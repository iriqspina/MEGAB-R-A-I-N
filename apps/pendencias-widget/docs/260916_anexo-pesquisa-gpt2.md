# Anexo — segunda opinião da conta gpt2 (astra/high, 260916)

Despacho com o prompt verbatim do dono + contexto inline medido. Incorporado na pesquisa principal em 4 pontos: sugestões nunca viram item sozinhas, validação antes de gravar, --json no CLI, cópia válida de recuperação.

---

# Pesquisa de planejamento — widget `/pendencias`

**TL;DR + /leigolanguage — Recomendo a fonte híbrida: a IA encontra possíveis pendências nos arquivos dos projetos, mas só o registro central aprovado alimenta o widget · o widget vira um painel confiável, não um “chutador” de texto · recolhido mostra apenas quantidade e urgência; expandido organiza ações por projeto · tudo é reversível: pausar oculta, retomar devolve e remover arquiva.**

## 1. Interpretação do pedido

1. O produto final é um widget discreto no desktop virtual **I.A.**, com as pendências relevantes dos projetos que o usuário escolheu acompanhar.
2. A pasta observada é configurável; para <USUARIO>, começa em `C:/Projetos`, hoje com 29 pastas [fonte: contexto medido].
3. Projeto parado não pode continuar poluindo a lista: o usuário precisa pausar e retomar projetos ou pendências individualmente.
4. Qualquer IA deve conseguir adicionar, concluir, remover, pausar ou retomar itens por meio da skill `/pendencias`.
5. Os arquivos `ESTADO.md` e `HANDOFF.md` ajudam a descobrir trabalho, mas não são confiáveis o bastante para controlar diretamente o que aparece na tela.

## 2. UX

### 2.1 Princípio do produto

O widget responde a uma pergunta: **“O que merece minha atenção agora?”**

Ele não deve virar:

- gerenciador completo de tarefas;
- espelho integral dos `ESTADO.md`;
- lista automática de frases que talvez sejam pendências;
- arquivo que o <USUARIO> precise editar manualmente.

A unidade principal é a pendência. O projeto serve como agrupamento, filtro e controle de pausa.

### 2.2 Jornada da manhã: ver o que está pendente

1. O usuário entra no desktop **I.A.**
2. O widget aparece recolhido na posição salva.
3. A forma recolhida mostra:
   - ícone discreto;
   - quantidade de pendências ativas;
   - sinal de atenção somente quando houver item prioritário ou bloqueado.
4. Ao clicar, abre a lista expandida sem trocar de janela nem deslocar o foco para outro aplicativo.
5. A lista começa por:
   1. prioridade;
   2. itens desbloqueados;
   3. atualização mais recente;
   4. nome do projeto.
6. O cabeçalho informa, por exemplo: **“7 pendências em 4 projetos”**.
7. Projetos pausados não entram nessa contagem.

A lista deve permitir entender o dia em aproximadamente 5 segundos [ESTIMATIVA], sem exigir leitura dos documentos dos projetos.

### 2.3 Jornada: agir numa pendência

Ao selecionar uma pendência, a linha revela ações curtas:

1. **Abrir projeto** — abre a pasta do projeto.
2. **Ver contexto** — abre o arquivo de origem na linha registrada, quando existir.
3. **Copiar para a IA** — copia um texto pronto, por exemplo:

   > No projeto Portfolio, continue esta pendência: <USUARIO> escolher a base visual do comparativo. Leia ESTADO.md e HANDOFF.md antes de agir.

4. **Concluir** — retira o item da lista ativa e registra `concluida`.
5. **Pausar** — oculta temporariamente apenas aquela pendência.
6. Menu `⋯`:
   - editar título;
   - mudar prioridade;
   - remover;
   - pausar o projeto inteiro.

O clique simples seleciona. Abertura de pasta ou arquivo exige ação explícita, evitando janelas acidentais.

### 2.4 Jornada: pausar um projeto parado

1. No cabeçalho do grupo, o usuário abre `⋯`.
2. Escolhe **Pausar projeto**.
3. O grupo recolhe e some da lista principal.
4. Surge uma confirmação curta: **“Pets pausado. 4 pendências ocultadas.”**
5. A área **Pausados** permite retomar o projeto.
6. Retomar devolve as pendências que estavam ativas antes da pausa; itens concluídos ou removidos continuam fora.

A pausa deve guardar um motivo opcional. Quando a IA detectar expressões como “não retomar automaticamente”, pode sugerir a pausa, mas não alterar o registro silenciosamente.

### 2.5 Jornada: adicionar ou remover conversando com qualquer IA

Exemplos que a skill deve entender:

- `/pendencias adicione no Portfolio: escolher a base visual do comparativo`
- `/pendencias conclua “escolher a base visual”`
- `/pendencias pause o projeto Pets até eu pedir`
- `/pendencias retome Pets`
- `/pendencias tire Rato de Olho da minha tela`
- `/pendencias o que está ativo?`
- `/pendencias procure possíveis pendências nos projetos`

A skill traduz o pedido para `bin/mb-pendencias.py`. Se houver mais de uma correspondência, ela mostra as opções antes de alterar.

“Tire da tela” deve usar:

- `pausada`, quando o texto indicar adiamento;
- `removida`, quando o usuário rejeitar a pendência;
- `concluida`, somente quando ele disser que terminou.

Remoção vira estado arquivado em vez de apagar o registro. Isso permite desfazer erros sem manter o item visível.

### 2.6 Jornada: instalar em outra pasta de projetos

1. O usuário executa `INSTALAR-E-ABRIR.cmd`.
2. Na primeira abertura, o widget pede a pasta que contém os projetos.
3. O caminho fica no `settings.json` local.
4. O sistema procura `ESTADO.md` e `HANDOFF.md` somente um nível abaixo da pasta escolhida por padrão.
5. A primeira leitura mostra **sugestões encontradas**, separadas da lista oficial.
6. O usuário pode:
   - aceitar;
   - editar e aceitar;
   - ignorar;
   - pausar o projeto inteiro.
7. Depois da configuração, o widget abre normalmente pelo `launch.vbs`.

A instalação deve funcionar mesmo quando alguns projetos não usam Git ou não têm os dois documentos.

### 2.7 Conteúdo mínimo de uma pendência

Na tela:

- título acionável;
- projeto;
- estado;
- prioridade;
- bloqueio, quando existir;
- origem, quando existir.

No registro:

- identificador estável;
- título;
- identificador e nome do projeto;
- estado;
- prioridade;
- datas de criação e atualização;
- origem;
- autoria da entrada;
- motivo de pausa ou remoção, quando houver.

Descrição longa, prazo e etiquetas são opcionais. A v1 não deve exigir nenhum deles.

### 2.8 Estados de tela

#### 2.8.1 Sem pendências

Mensagem:

> **Nada ativo agora**  
> Os projetos pausados continuam guardados.  
> `Buscar nos projetos` · `Adicionar pendência`

Não usar linguagem comemorativa: vazio também pode significar que o registro ainda não foi alimentado.

#### 2.8.2 Tudo pausado

Mensagem:

> **Todas as pendências estão pausadas**  
> 12 itens em 3 projetos [ESTIMATIVA].  
> `Ver pausados` · `Retomar projeto`

O ícone recolhido usa aparência neutra e contagem `0`, com um pequeno símbolo de pausa.

#### 2.8.3 Mais de 20 itens

A partir de 21 itens, a tela:

- mostra primeiro **Foco**, com até 7 itens [ESTIMATIVA];
- mantém os demais em **Outras pendências**;
- oferece busca por texto;
- oferece filtro por projeto, estado e prioridade;
- mantém grupos recolhíveis;
- preserva a posição da rolagem enquanto estiver aberto.

A contagem continua real; o produto não deve fingir que existem somente os itens em foco.

#### 2.8.4 Erro de leitura

Mensagem:

> **Não consegui atualizar a lista**  
> A última versão válida continua visível.  
> `Tentar novamente` · `Abrir diagnóstico`

O widget nunca deve substituir uma lista válida por uma tela vazia após JSON incompleto ou leitura interrompida.

### 2.9 O que significa “sutil”

- Recolhido na maior parte do tempo.
- Sem janela na barra de tarefas.
- Sem roubar o foco do aplicativo atual.
- Sem som.
- Sem animação contínua.
- Sem notificações recorrentes.
- Opacidade e superfície compatíveis com o Cotas IA.
- Expansão somente por clique.
- Atualização silenciosa quando o arquivo muda.
- Sinal vermelho reservado a erro de leitura ou bloqueio explícito; quantidade alta, sozinha, não é erro.

O widget precisa continuar localizável: a forma recolhida mantém texto ou contagem, área de clique confortável e contraste legível.

## 3. UI

### 3.1 Forma recolhida

Recomendação: **pill horizontal**, uma cápsula curta.

Conteúdo:

```text
●  Pendências  7
```

Variações:

```text
○  Em dia
Ⅱ  Tudo pausado
!  2 bloqueadas
```

Dimensões iniciais:

- altura: 34 px [ESTIMATIVA];
- largura adaptável entre 108 e 156 px [ESTIMATIVA];
- raio: aproximadamente 14 px, herdado do Cotas IA [fonte: contexto medido];
- opacidade padrão: 76%, herdada do Cotas IA [fonte: contexto medido].

A cápsula inteira pode ser arrastada. Depois de um pequeno deslocamento, o gesto passa a mover o widget em vez de abri-lo.

### 3.2 Forma expandida

Painel vertical ancorado à cápsula:

```text
┌ Pendências                         7 ┐
│ 4 projetos                 Buscar  ⋯ │
├ Foco ────────────────────────────────┤
│ PORTFOLIO                         ⋯  │
│ ● Escolher base visual do comparativo│
│   Próximo passo · alta               │
│                                      │
│ RATO DE OLHO                      ⋯  │
│ ○ Calibrar 9 pontos                  │
│   bloqueada · abrir contexto          │
├ Outras pendências · 5 ──────────────┤
│ ...                                  │
└ Atualizado agora             + Adicionar┘
```

Dimensões iniciais:

- largura: 360 px [ESTIMATIVA];
- altura máxima: 70% da área útil da tela [ESTIMATIVA];
- até 7 itens visíveis antes da rolagem [ESTIMATIVA].

O painel abre para o lado com mais espaço disponível.

### 3.3 Agrupamento e hierarquia

Ordem visual:

1. cabeçalho geral;
2. área **Foco**;
3. grupos por projeto;
4. itens;
5. área recolhida **Pausados**;
6. rodapé de atualização.

Cada item usa:

1. marcador de estado;
2. título em até 2 linhas [ESTIMATIVA];
3. metadados em uma linha;
4. ações somente ao selecionar ou passar o cursor.

O nome do projeto aparece uma vez no cabeçalho do grupo. Repeti-lo em todas as pendências desperdiçaria espaço.

### 3.4 Cores e tipografia

Reusar integralmente os sete presets do Cotas IA:

- carvão;
- meia_noite;
- ameixa;
- musgo;
- telha;
- nevoa;
- papel.

Estados herdados:

- verde `#7cc48f`: ativo e livre para agir;
- âmbar `#e0b46a`: atenção, pausa temporária ou prazo próximo;
- vermelho `#e89a9a`: bloqueio explícito ou falha de leitura.

Estados adicionais devem usar a paleta da superfície:

- concluída: texto secundário;
- removida: não aparece na lista normal;
- sugestão automática: contorno tracejado ou rótulo **Sugestão**, sem cor de urgência.

Tipografia:

- Segoe UI, herdada dos widgets existentes;
- título do item: 13 px [ESTIMATIVA], peso semibold;
- metadados: 11 px [ESTIMATIVA];
- cabeçalho: 12 px [ESTIMATIVA], peso semibold;
- contagem da cápsula: 12 px [ESTIMATIVA].

### 3.5 Densidade

Cada item fechado ocupa entre 44 e 56 px [ESTIMATIVA]. Descrição longa não aparece na lista: fica no detalhe ou no arquivo de origem.

Metadados usam linguagem direta:

```text
alta · bloqueada por escolha do <USUARIO>
normal · adicionada pela IA
pausada até pedido
```

Datas relativas aparecem somente quando ajudam:

```text
atualizada hoje
sem revisão há 18 dias
```

“Antiga” não significa automaticamente urgente.

### 3.6 Microinterações

- Abrir e recolher: animação entre 120 e 180 ms [ESTIMATIVA].
- Concluir: a linha fica marcada por 2 segundos [ESTIMATIVA], com opção **Desfazer**, antes de sair.
- Pausar: o item reduz opacidade e vai para **Pausados**.
- Nova entrada: destaque discreto durante uma abertura do painel.
- Atualização externa: a lista muda sem piscar e mostra **Atualizado agora**.
- Arrastar: cursor muda para indicar movimento.
- Erro: ícone estático; sem pulsação.
- `Esc`: recolhe o painel.
- Clique fora: recolhe, desde que nenhuma edição esteja aberta.

### 3.7 Comportamento no desktop I.A.

Reusar do Agentes IA:

- `QGraphicsView` frameless;
- fundo transparente;
- máscara de clique limitada à cápsula e ao painel aberto;
- nascimento no desktop virtual **I.A.**;
- `stderr` sempre redirecionado;
- nenhuma área transparente intercepta o mouse.

Quando recolhido, somente a cápsula recebe cliques. Quando expandido, a máscara cresce até os limites do painel e volta ao tamanho anterior ao fechar.

## 4. Fonte de dados

### 4.1 Recomendação

Recomendo **C: modelo híbrido**, dividido em duas camadas:

1. `ESTADO.md` e `HANDOFF.md` produzem **sugestões**.
2. `dados/pendencias.json` contém a lista **oficial e curada**.
3. O widget lê somente a lista oficial.
4. A skill e o script controlam todas as alterações.
5. Sugestões nunca entram silenciosamente na contagem principal.

### 4.2 Justificativa

A alternativa A falha porque os documentos medidos usam estruturas diferentes:

- “Próximo passo” inline;
- “Gate seguinte”;
- “PAUSADO”;
- instruções negativas como “Não iniciar campanha”;
- listas de retomada;
- pendências apenas implícitas.

Uma heurística pode confundir contexto, bloqueio e tarefa. Isso faria o widget exibir ruído e perder confiança.

A alternativa B oferece uma fonte segura, mas depende de alimentação manual desde o início. Pendências já existentes nos projetos ficariam invisíveis até alguém registrá-las.

O híbrido preserva as duas vantagens:

- descoberta automática do trabalho espalhado;
- decisão humana ou explícita da IA antes de colocar algo na tela.

### 4.3 Contrato do arquivo

Local:

```text
<MEGABRAIN>/dados/pendencias.json
```

Exemplo:

```json
{
  "schema_version": 1,
  "workspace": {
    "id": "ws-megabrain-<USUARIO>",
    "name": "Projetos <USUARIO>",
    "projects_root": "C:/Projetos",
    "updated_at": "2026-09-16T10:30:00-03:00"
  },
  "projects": [
    {
      "id": "portfolio",
      "name": "Portfolio",
      "path": "C:/Projetos\\Portfolio",
      "status": "ativo",
      "pause_reason": null,
      "paused_at": null
    },
    {
      "id": "pets",
      "name": "Pets",
      "path": "C:/Projetos\\Pets",
      "status": "pausado",
      "pause_reason": "Logout do <USUARIO>; não retomar automaticamente.",
      "paused_at": "2026-09-15T18:20:00-03:00"
    }
  ],
  "items": [
    {
      "id": "pnd_01J7PORTFOLIO",
      "project_id": "portfolio",
      "title": "Escolher a base visual do comparativo",
      "detail": null,
      "status": "ativa",
      "priority": "alta",
      "blocked": true,
      "blocked_reason": "Depende de escolha visual do <USUARIO>.",
      "source": {
        "kind": "estado",
        "path": "C:/Projetos\\Portfolio\\ESTADO.md",
        "line": 18,
        "fingerprint": "sha256:exemplo"
      },
      "created_by": {
        "kind": "assistant",
        "label": "Codex"
      },
      "created_at": "2026-09-16T09:40:00-03:00",
      "updated_at": "2026-09-16T09:40:00-03:00",
      "paused_at": null,
      "pause_reason": null,
      "completed_at": null,
      "removed_at": null,
      "removal_reason": null
    }
  ],
  "suggestions": [
    {
      "id": "sug_01J7RATO",
      "project_id": "rato-de-olho",
      "title": "Executar calibração de 9 pontos",
      "status": "proposta",
      "confidence": "alta",
      "source": {
        "kind": "estado",
        "path": "C:/Projetos\\Rato de Olho\\ESTADO.md",
        "line": 27,
        "excerpt": "Gate seguinte: calibração de 9 pontos..."
      },
      "detected_at": "2026-09-16T10:25:00-03:00"
    }
  ]
}
```

### 4.4 Valores permitidos

```text
project.status:
- ativo
- pausado
- arquivado

item.status:
- ativa
- pausada
- concluida
- removida

item.priority:
- alta
- normal
- baixa

suggestion.status:
- proposta
- aceita
- ignorada
- obsoleta
```

`blocked` é separado de `status`: uma pendência pode estar ativa e bloqueada, porque continua exigindo atenção.

### 4.5 Regras de integridade

- IDs não mudam quando título ou prioridade mudam.
- Caminhos ficam absolutos no JSON da máquina.
- Datas usam ISO 8601 com fuso.
- Escrita usa arquivo temporário e substituição completa para evitar JSON pela metade.
- Antes de escrever, o script valida a versão e o formato.
- Escritas concorrentes usam bloqueio de arquivo.
- O último JSON válido fica como cópia de recuperação.
- O widget não escreve no arquivo.
- Campo desconhecido é preservado sempre que possível.
- Versão incompatível gera erro visível, sem tentar “consertar” automaticamente.
- Uma sugestão com o mesmo `fingerprint` não reaparece depois de ignorada, salvo quando a frase de origem mudar.

## 5. Arquitetura

### 5.1 Árvore proposta

```text
MEGA B R A I  N/
├─ apps/
│  └─ pendencias-widget/
│     ├─ README.md
│     ├─ INSTALAR-E-ABRIR.cmd
│     ├─ launch.vbs
│     ├─ requirements.txt
│     ├─ settings.example.json
│     ├─ src/
│     │  └─ pendencias_widget/
│     │     ├─ __init__.py
│     │     ├─ __main__.py
│     │     ├─ app.py
│     │     ├─ window.py
│     │     ├─ collapsed_view.py
│     │     ├─ expanded_view.py
│     │     ├─ item_view.py
│     │     ├─ theme.py
│     │     ├─ data_reader.py
│     │     ├─ file_watcher.py
│     │     ├─ settings.py
│     │     ├─ desktop_target.py
│     │     ├─ singleton.py
│     │     ├─ diagnostics.py
│     │     └─ resources/
│     ├─ tests/
│     │  ├─ fixtures/
│     │  ├─ test_data_reader.py
│     │  ├─ test_sorting.py
│     │  ├─ test_filters.py
│     │  ├─ test_states.py
│     │  ├─ test_file_watcher.py
│     │  ├─ test_click_mask.py
│     │  ├─ test_settings.py
│     │  └─ test_screenshot_mode.py
│     └─ tools/
│        └─ capture_states.py
├─ bin/
│  ├─ mb-pendencias.py
│  └─ mb-pendencias-scan.py
├─ dados/
│  ├─ pendencias.json
│  ├─ pendencias.schema.json
│  └─ backups/
├─ motor/
│  └─ skills/
│     └─ pendencias/
│        └─ SKILL.md
└─ memoria/
   └─ estado/
      └─ pendencias-widget.md
```

### 5.2 Responsabilidades

#### `apps/pendencias-widget/`

- apresenta a lista;
- observa mudanças no JSON;
- salva posição, tema e pasta configurada;
- abre pasta ou arquivo de origem;
- copia contexto para a área de transferência;
- nunca interpreta markdown;
- nunca decide o estado das pendências.

#### `bin/mb-pendencias.py`

Comandos previstos:

```text
list
add
edit
complete
remove
pause
resume
pause-project
resume-project
projects
suggestions
accept-suggestion
ignore-suggestion
validate
```

Exemplos:

```text
python bin/mb-pendencias.py list --status ativa
python bin/mb-pendencias.py add --project portfolio --title "Escolher base visual"
python bin/mb-pendencias.py pause-project --project pets --reason "Não retomar automaticamente"
python bin/mb-pendencias.py complete --id pnd_01J7PORTFOLIO
python bin/mb-pendencias.py validate
```

Saída para outras IAs deve ter dois modos:

- texto curto para humanos;
- `--json` para automação.

#### `bin/mb-pendencias-scan.py`

- encontra projetos um nível abaixo da raiz;
- lê `ESTADO.md` e `HANDOFF.md`;
- identifica trechos candidatos;
- grava somente em `suggestions`;
- evita duplicatas por projeto, origem e impressão digital do trecho;
- nunca promove sugestão para pendência ativa.

Separar a varredura do comando principal reduz o risco de uma leitura heurística afetar operações confiáveis.

#### `motor/skills/pendencias/SKILL.md`

A skill define:

- quando usar o registro;
- como interpretar pedidos naturais;
- diferença entre pausar, concluir e remover;
- obrigação de consultar correspondências antes de agir em nomes ambíguos;
- uso exclusivo do script para alterações;
- formato de resposta curto;
- regra de nunca editar `pendencias.json` diretamente;
- regra de nunca aceitar automaticamente sugestões do scanner.

#### `memoria/estado/pendencias-widget.md`

Guarda somente o estado de desenvolvimento do produto:

- versão atual;
- última validação;
- limitações conhecidas;
- próximo passo do próprio widget.

Não duplica a lista de pendências.

### 5.3 Reuso do Cotas IA

Reutilizar:

- estrutura Python + PySide6;
- ambiente virtual compartilhado em `apps/ia-quota-widget/.venv`;
- janela frameless e arrastável;
- raio visual;
- opacidade;
- presets de superfície;
- cores de estado;
- Segoe UI;
- `QLocalServer` para instância única;
- persistência em `settings.json`;
- modo screenshot;
- padrão de testes;
- `INSTALAR-E-ABRIR.cmd`;
- `launch.vbs` com `pythonw`.

O código compartilhado deve ser extraído somente se houver compatibilidade real. A v1 pode copiar componentes pequenos com autoria registrada, evitando transformar a entrega em uma reforma dos widgets existentes.

### 5.4 Reuso do Agentes IA

Reutilizar:

- inicialização no desktop virtual **I.A.**;
- janela transparente;
- máscara dinâmica de clique;
- redirecionamento obrigatório de `stderr`;
- tratamento para aplicativos iniciados no desktop correto.

O widget deve manter singleton por usuário. Abrir novamente traz a instância existente para o estado expandido.

### 5.5 Launcher e configuração

`INSTALAR-E-ABRIR.cmd`:

1. encontra o Python do ambiente compartilhado;
2. instala somente dependências ausentes;
3. cria `settings.json` a partir do exemplo;
4. pede ou detecta a raiz dos projetos na primeira execução;
5. inicia por `launch.vbs`;
6. registra início automático apenas se essa opção estiver habilitada.

`settings.json` local:

```json
{
  "projects_root": "C:/Projetos",
  "data_file": "C:/Projetos\\MEGA B R A I  N\\dados\\pendencias.json",
  "theme": "carvao",
  "opacity": 0.76,
  "collapsed": true,
  "position": {
    "screen": "primary",
    "x": 1480,
    "y": 90
  },
  "show_paused_count": false,
  "start_with_windows": true
}
```

### 5.6 Testes necessários

1. Leitura de JSON válido, vazio, incompleto e com versão incompatível.
2. Recuperação da última versão válida após escrita interrompida.
3. Ordenação por prioridade, bloqueio, atualização e projeto.
4. Pausa de item e pausa de projeto.
5. Retomada sem ressuscitar concluídos ou removidos.
6. Mais de 20 itens, busca e filtros.
7. Todos os projetos pausados.
8. Projeto sem `ESTADO.md`, sem `HANDOFF.md` ou sem Git.
9. Caminhos com espaços e caracteres acentuados.
10. Alteração externa do JSON enquanto o painel está aberto.
11. Instância única.
12. Máscara de clique recolhida e expandida.
13. Abertura no desktop virtual **I.A.**
14. `stderr` redirecionado no lançamento sem console.
15. Capturas dos sete temas nos estados principais.
16. Script concorrente tentando gravar duas alterações.
17. Scanner evitando sugestão duplicada ou já ignorada.
18. Preservação de campos desconhecidos do contrato.

## 6. Critérios verificáveis de estado final da v1

1. O widget inicia sem console e aparece no desktop virtual **I.A.**
2. Uma segunda abertura não cria outra instância.
3. A cápsula recolhida mostra a quantidade correta de pendências ativas em projetos ativos.
4. Pendências e projetos pausados não entram na contagem ativa.
5. O painel expandido agrupa os itens pelo projeto correto.
6. Itens prioritários e bloqueados seguem a ordenação definida.
7. O widget aceita uma raiz de projetos diferente de `C:/Projetos`.
8. Projetos sem Git ou sem os dois arquivos de contexto não quebram a leitura.
9. Alterações feitas por `mb-pendencias.py` aparecem no widget sem reiniciá-lo.
10. O widget continua mostrando a última lista válida quando o arquivo atual está inválido.
11. Concluir, remover, pausar e retomar preservam histórico e datas.
12. Pausar um projeto oculta seus itens; retomar devolve somente os que permanecem ativos.
13. O scanner grava achados como sugestões e nenhum achado aparece automaticamente na lista principal.
14. Uma sugestão aceita gera uma pendência com ligação para a origem.
15. Uma sugestão ignorada não reaparece enquanto o trecho de origem continuar igual.
16. Qualquer IA com a skill instalada consegue listar e alterar pendências sem editar JSON manualmente.
17. O painel permite abrir a pasta do projeto, abrir a origem disponível e copiar contexto para outra IA.
18. Com mais de 20 itens, busca, filtros, grupos e rolagem permanecem utilizáveis.
19. As áreas transparentes do widget não bloqueiam cliques no desktop.
20. Posição, tema, opacidade e estado recolhido sobrevivem ao reinício.
21. Os sete temas mantêm texto, estados e controles legíveis nas capturas de prova.
22. O contrato é validado por `pendencias.schema.json` antes de cada gravação.
23. Duas gravações simultâneas não corrompem nem descartam silenciosamente uma alteração.
24. `INSTALAR-E-ABRIR.cmd` prepara e inicia o widget em uma instalação nova compatível.
25. Testes automatizados, captura dos estados principais e validação do JSON terminam sem erro.

## 7. Riscos principais

### 7.1 Sugestões automáticas virarem ruído

**Risco:** frases como “não iniciar campanha” podem ser interpretadas como tarefas, embora representem uma trava.

**Mitigação:** scanner grava apenas em `suggestions`; cada sugestão mostra trecho e origem; aceitação é explícita; itens ignorados usam impressão digital para não reaparecer.

### 7.2 Registro ficar desatualizado em relação aos projetos

**Risco:** uma IA atualiza `ESTADO.md`, mas esquece de atualizar a pendência correspondente.

**Mitigação:** a skill inclui atualização do registro no fechamento de trabalho; o scanner marca sugestões relacionadas a fontes alteradas; o widget mostra “origem mudou” sem editar o item automaticamente.

### 7.3 Escritas concorrentes perderem alterações

**Risco:** duas IAs podem chamar o script quase ao mesmo tempo.

**Mitigação:** bloqueio de arquivo, leitura da versão mais recente antes da mudança, escrita temporária, substituição atômica e cópia da última versão válida.

### 7.4 Widget sutil ficar invisível ou difícil de clicar

**Risco:** excesso de transparência e tamanho pequeno fazem o produto desaparecer na tela.

**Mitigação:** cápsula com contagem textual, contraste por tema, altura inicial de 34 px [ESTIMATIVA], opacidade configurável e captura de prova sobre fundos claros e escuros.

### 7.5 Widget roubar clique, foco ou desktop

**Risco:** a janela transparente pode interceptar áreas maiores que o conteúdo ou nascer no desktop errado.

**Mitigação:** máscara dinâmica herdada do Agentes IA, testes de clique fora dos elementos, abertura no desktop virtual **I.A.**, ausência na barra de tarefas e recolhimento por `Esc` ou clique externo.
