# Widget de cotas IA

Faixa translúcida, sempre no topo, arrastável entre monitores, mostrando a cota de
Codex, Claude, Z.ai (GLM Coding Plan), Gemini CLI, Antigravity e Gemini (app) — cada
fonte separada, nunca uma média entre janelas de cota ou entre provedores. Codex,
Claude e Z.ai aparecem por padrão; os outros três ligam pelo menu quando quiser.
Fonte e armadilhas do Z.ai (endpoint não documentado, chave DPAPI) em `PROVIDERS.md`.

## Visual (260913)

Uma linha por provedor: nome · % usado da pior janela · barra · "Semana · renova em 5 d ·
agora". Expandido, o detalhe fica embaixo, na largura inteira, com colunas alinhadas
(janela · % · renovação · ritmo "dá ~N%/dia"). Plano e fonte técnica ficam na dica do
nome. **Spark** é linha própria só na tela: vem da mesma consulta do Codex (janelas
`codex_bengalfox:*`), sem chamada extra, e `providers.py`/`dados/orcamento_ia.json`
continuam com o snapshot inteiro. Decisões e como reverter:
`00_PARA-VOCE/260913_cotas-ia-z/260913_GRELHA-RESPONDIDA.md`.

Para iterar no visual, use `--demo`: captura com dado real consulta as APIs de novo e
já levou o Claude a HTTP 429.

## Tamanho e Configurações (260913)

- **Redimensionar:** arraste bordas e cantos (faixa invisível de 7 px fora do contorno,
  como no Windows 11). O tamanho fica salvo; conteúdo maior rola. Duplo clique no
  cabeçalho, `Ctrl+0` ou Opções → "Ajustar tamanho ao conteúdo" volta ao automático.
- **Configurações** (`Ctrl+,` ou Opções → Configurações…): tudo aplica na hora e salva,
  com prévia ao vivo (o mesmo componente do widget, dado de exemplo).
  - Texto: fonte (a lista mostra cada fonte nela mesma, mais 12 exemplos clicáveis),
    tamanhos de nome, número, status e detalhes, escala.
  - Aparência: cor, opacidade 20–100 %, layout, detalhes, ritmo, rodapé, ao passar o
    mouse (nada, fundo sólido, transparente).
  - Números: % usado ou que sobra, renovação relativa ou dia e hora, atualizar a cada
    2–30 min, aviso na bandeja a 75/90 %.
  - Janela: sempre acima, travar posição e tamanho, grudar nas bordas, atravessar
    cliques (para desligar: ícone na bandeja → Atravessar cliques).
  - Provedores: marcar e reordenar.
  - "Desfazer alterações" volta ao estado de quando a janela abriu.
- Captura das Configurações sem consultar API:
  `widget.py --demo --skip-singleton-guard --settings-screenshot out.png --settings-tab 0`.

## Rodar

Duplo clique em `launch.vbs` — nenhuma janela de console, nem na abertura nem
nos refreshes. O `launcher.cmd` faz a mesma coisa, mas pisca a janela do `cmd`
por uma fração de segundo antes de sair; use ele só pra depurar.
Ambos chamam `.venv\Scripts\pythonw.exe widget.py`.

Manual, dentro da pasta:

```
.venv\Scripts\python.exe widget.py          # dados reais
.venv\Scripts\python.exe widget.py --demo   # dados ficticios rotulados, sem consultar nada
```

Primeira vez, criar o ambiente:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Ou rodar `scripts\instalar.ps1` uma vez, na pasta de destino final — ele cria o
`.venv`, instala as dependências travadas, roda a suite de testes (falha alto se
não passar) e cria o atalho da Área de Trabalho. Ver "Instalação no destino final"
abaixo.

## Fechar

Botão `×` no cabeçalho, ou "Sair" no menu (botão `Opções`). Os dois encerram o
processo depois de salvar posição e configurações.

## Providers visíveis

Menu `Opções` → "Provedores": um item marcável por provedor (Codex, Claude, Gemini CLI,
Antigravity, Gemini app), mostrando o estado conhecido (`— 42% ok`, `— reautenticar`,
`— indisponível`...) quando já houve alguma leitura, ou só o nome se nunca foi
consultado. Provedor desligado não é consultado no ciclo de 120s — economiza rede e
processo, e não fica batendo num provedor que você desligou de propósito (ex.:
Gemini CLI com token vencido). Ao ligar, dispara uma consulta imediata; até ela
voltar, o segmento mostra "consultando…", nunca um número antigo sem aviso.

A janela encolhe e cresce de verdade com o número de providers visíveis — não é
largura fixa com espaço reservado escondido. Cresce a partir do canto
superior-esquerdo e nunca sai da tela (mesma trava de `screen_geometry` usada pra
posição).

## Cor de fundo

Menu `Opções` → "Cor de fundo": 7 presets translúcidos (Carvão é o padrão, mais Meia-noite,
Ameixa, Musgo, Telha, Névoa e Papel — os dois últimos claros). Sem seletor de cor
livre. Cada preset foi medido, não só olhado: `tests/test_contrast.py` compõe a cor
do painel sobre branco puro e sobre preto puro (os dois extremos possíveis de área
de trabalho por trás de um fundo translúcido) e trava o texto principal em
≥4,5:1 de contraste WCAG nos dois casos — preset que não passasse teria que mudar de
valor, não entrar quieto. Cor de identidade do provedor (o pontinho) e cor de estado
da barra (verde/âmbar/vermelho) **não mudam** com o preset — só a superfície muda, o
significado da cor continua igual. Nos presets claros a paleta de status usa
variantes mais escuras (a pastel pensada pro carvão quase sumia num painel claro,
medido: ~1,8:1 de contraste, bem abaixo do necessário).

## Contrato de dados

`providers.py`, na raiz desta pasta, expõe `PROVIDER_IDS` e `fetch_provider(id)`.
Esse arquivo é de responsabilidade de outro agente (Opus) — o widget nunca escreve
nele. Se `providers.py` ainda não existir, cada provedor aparece como
"indisponível" com uma mensagem explicando o motivo; nada é inventado.

Cada leitura tem um `status` (`ok`, `unavailable`, `auth_required`, `error`,
`rate_limited`). O widget guarda o último dado bom por provedor: uma falha
pontual não apaga o número — ele continua visível com a idade da leitura, e só
muda de cor depois de `STALE_GRACE_SECONDS` (900s, ~7 ciclos de poll) sem sucesso,
pra falha transitória de rede/CLI não piscar a cor toda hora
(`widget_app/theme.py::stale_aware_track_color`).

No modo compacto, cada provedor mostra a PIOR janela de cota da própria fonte
(nunca uma média, nunca fundida com outro provedor), com o rótulo do período.
O modo expandido (menu `Opções` → Expandir detalhes) lista todas as janelas, mais a
fonte técnica de cada leitura no tooltip de “Fonte técnica ⓘ”. O endereço completo
também fica no nome acessível, sem quebrar em várias linhas na faixa.

## Configuração e posição

`app/data/settings.json`: posição, opacidade do fundo, cor de fundo, escala,
layout (horizontal/vertical), always-on-top, expandido, providers visíveis. Local
ao app, não em `%AppData%`. Recalculada e travada dentro da área visível dos
monitores atuais a cada abertura e sempre que um monitor conecta/desconecta.

## Ícone e atalho

`assets/cotas-ia.ico` (16 a 256px, gerado por `scripts/generate_icon.py`: quadrado
carvão com barras verticais nas cores de identidade dos providers — 2 barras abaixo
de 32px, pra não virar borrão no tamanho pequeno) e `assets/cotas-ia.png` (256px).

`scripts/criar-atalho.ps1 [-InstallDir <pasta>] [-DesktopDir <pasta>]` cria (ou
atualiza, idempotente) um atalho apontando pro `launch.vbs` da pasta, com o ícone e
o `WorkingDirectory` certos. Não mexe em Startup, registro nem `%APPDATA%`. Por
padrão aponta pra própria pasta e pra Área de Trabalho real — passe `-DesktopDir`
pra testar num destino temporário sem tocar na Área de Trabalho de verdade.

## Instalação no destino final

Este app foi desenvolvido dentro de um worktree do Traycer (descartável). O destino
combinado é a central do MEGA BRAIN (`apps/ia-quota-widget` dentro do checkout de
`master`) — chega lá sozinho quando este branch for integrado, sem cópia manual.

Depois que os arquivos chegarem no destino final, rodar uma vez:

```
scripts\instalar.ps1
```

Isso recria o `.venv` do zero ali (não copia — venv do Windows grava caminho
absoluto em `pyvenv.cfg` e nos `.exe` de `Scripts\`, então um `.venv` copiado de
outra pasta quebra o `pip`), instala `PySide6==6.11.2` travado, roda
`pytest tests/ -q` e para com erro se não passar, e cria o atalho "Cotas IA" na
Área de Trabalho de verdade.

Nenhum módulo do app usa caminho absoluto do worktree — `widget_app/paths.py` e os
dois launchers resolvem tudo relativo à própria pasta (`Path(__file__)`/`%~dp0`/
`GetParentFolderName`), então mover a pasta não quebra nada além do `.venv`.

## Estrutura

```
widget.py                  ponto de entrada (CLI: --demo, --screenshot, --move-to, --theme, --expanded)
widget_app/
  main_window.py            janela frameless, grade alinhada, providers/tema/menu, bandeja
  ui_provider_segment.py    widgets de um provedor (compacto + detalhe expandido)
  providers_bridge.py       ponte com providers.py: fallback, normalização, poll em thread pool
  snapshot_store.py         guarda último-bom por provedor, decide a pior janela
  theme.py                  presets de cor, paleta de status por tema, regra de carência de dado velho
  contrast.py               composição alpha + contraste WCAG (usado pelo teste dos presets)
  persistence.py            settings.json
  screen_geometry.py        clamp multi-monitor, inclusive coordenada negativa
  single_instance.py        trava de instância única (QLocalServer)
  formatting.py             idade/renovação/percentual em texto
  demo_data.py               dados ficticios do --demo
scripts/
  generate_icon.py          gera assets/cotas-ia.ico + .png
  criar-atalho.ps1           cria/atualiza o atalho da Área de Trabalho
  instalar.ps1                setup completo no destino final
tests/                      pytest, rodar com .venv\Scripts\python.exe -m pytest tests/ -q
```

## Testado nesta máquina (evidência em `evidence/`, fora do git)

- Always-on-top real sobre outra janela (WhatsApp Web), nos 3 monitores desta
  máquina, incluindo o monitor retrato em coordenada negativa `(-1080,-480)`.
- Transparência real do fundo contra o desktop, texto opaco, nos dois extremos
  claro/escuro por trás (é o que o teste de contraste também mede).
- Posição persistida entre reinícios (matada a força e reaberta, voltou no
  mesmo lugar).
- Consumo em repouso medido: processo Qt ~131 MB working set / ~61 MB privado,
  0,00s de CPU ao longo de 3s parado.
- `launch.vbs` abre sem console visível; `launcher.cmd` pisca o `cmd` uma vez.
- Nenhum refresh abre console: todo processo filho (codex app-server, `netstat`,
  `tasklist`) nasce com `CREATE_NO_WINDOW`. Sob `pythonw` o pai não tem console,
  então sem essa flag o Windows alocaria um novo pra cada filho.
- Trava de instância única funcional.
- Grade alinhada (título/número/barra/período na mesma altura entre colunas) e
  janela encolhendo/crescendo ao ligar/desligar provider, com dado real.
- 3 presets de cor testados com dado real, incluindo um claro (Névoa) e um
  escuro alternativo (Meia-noite), além do Carvão padrão.
- `criar-atalho.ps1` testado contra pasta temporária: cria, roda de novo sem
  duplicar, `TargetPath`/`WorkingDirectory`/`IconLocation` conferidos.
- Nenhum caminho absoluto do worktree encontrado no código (`grep` no `.py`).

## Não testado / limitações conhecidas

- DPI por monitor: os 3 monitores desta máquina não têm escalas diferentes
  configuradas agora, então o comportamento com DPI misto (ex.: 100%/150%)
  não foi validado visualmente, só por código (Qt6 faz scaling automático).
- Arraste com mouse real não foi feito por um humano nesta sessão — o
  mecanismo de drag (`DragHeader`) segue a API padrão do Qt
  (`globalPosition()` + `move()`), mas a sensação em uso real fica para
  validação do <USUARIO>.
- Empacotamento em `.exe` (PyInstaller ou similar): pendência consciente, não
  esquecimento — empacotar agora congelaria um app cujo layout ainda estava
  mudando nesta mesma entrega.
- `scripts/instalar.ps1` não foi executado de verdade contra o destino final
  (a central ainda não recebeu a integração deste branch) — só revisado e
  com cada peça dele (venv, pytest, ícone, atalho) testada separadamente.


## Controles e feedback de consulta (260908)

O cabeçalho mostra **Opções**, uma seta para expandir/recolher detalhes e o estado
marcável de **Sempre acima** (◆ ligado, ◇ desligado; tooltip e nome acessível).
O rodapé informa **Consultando…**, **Tentativa agora**, **Tentativa há 1 min** ou
**Consulta pausada**, com data e horário exatos no tooltip.
Tentativa não significa leitura bem-sucedida: o estado e a idade de cada provedor
continuam indicando a qualidade do dado. Com todos desligados, **Escolher
provedores…** abre a lista para religar uma fonte.

Com o widget em foco: **F5** atualiza, **Ctrl+D** alterna detalhes, **Ctrl+,** abre
Opções e **Ctrl+T** alterna Sempre acima. Tab percorre os botões com contorno de
foco visível. A atualização manual respeita a consulta pendente e o intervalo
mínimo já existente. As mensagens truncadas têm tooltip com o texto completo.
Todos esses comandos também estão no menu Opções; os atalhos dependem de foco.

Validação final: `167 passed, 28 subtests passed`. Capturas do produto
real (`Qt.Tool`, `widget.py`) em `evidence/260908_ux_after_product_*.png`.
Interação nativa de Ctrl+D, Ctrl+, e F5 foi exercitada em um proxy `Qt.Window`:
**foco/ativação dos atalhos em Qt.Tool ainda precisa de validação humana**.
Relatório: [260908_UX.md](260908_UX.md).

## Correções de idade, captura e recuo (260908)

Leitura `ok` também envelhece: após 15 minutos, a barra degrada mesmo sem falha
de rede. A idade e as cores são reavaliadas localmente a cada 30 segundos; o menu
de provedores inclui a idade do número. Reconstruir o layout preserva consultas
pendentes.

Uma resposta `rate_limited` impõe pausa somente naquela fonte: 4 minutos,
8 minutos e depois 15 minutos, mantendo esse teto até uma leitura bem-sucedida.
Atualização manual e desligar/religar não pulam essa pausa. O recuo é da sessão;
reiniciar o processo perde seu histórico.

Usar `--theme`, `--expanded` ou `--screenshot` torna as configurações daquela
execução temporárias, inclusive ajustes pelo menu. A sessão normal continua
salvando as preferências.

Evidência e limites: [260908_CORRECOES_FINAIS.md](260908_CORRECOES_FINAIS.md).

