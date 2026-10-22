# Ferramentas do cursor · v1.5 · 261017

Gesto vigente: **segurar 0,4 s parado** (detalhes em "Gesto vigente", abaixo). As menções a 2 s e 0,7 s neste arquivo são histórico.

Ideia do <USUARIO> (Portfólio, 10/10/2026): segurar o botão esquerdo abre um menu em leque em volta do ponteiro;
ali o cursor troca de ferramenta (Interagir ↔ Comentar).
Pedido literal (261010): "salva essa ideia pq eu quero usar ela em outros casos, então seria bom ter um artefato só dela".
Pedido literal (261011): "Quero uma alteração também nessa funcionalidade do mouse, para que eu possa segurar e ainda mover o mouse, e que tenha que durar 0,7 segundos. Também quero uma funcionalidade onde eu possa utilizar meu microfone para poder falar o comentário que eu quero."

- `cursor-ferramentas.js` — fonte única. Sem dependências, injeta o próprio CSS, expõe `window.CursorFerramentas.iniciar(opções)`.
- `demo-fonte.html` + `build.py` → `demo.html` (autocontida). Publicada como artefato: https://claude.ai/artifact/FC9hWt3J2PJffLiRyAUd5d
  (o artefato publicado continua na v1.0 até ser republicado; para o microfone funcionar lá, republicar com a capability de microfone).
- `antes_v1.0/` — cópia da v1.0 (js, demo, LEIAME, build) tirada antes da troca.
- Comentar: `modo:'auto'` usa `comments.openComposer` quando a página roda no claude.ai com a capability `comments`;
  fora dele cria nota local (pino numerado + editor), guardada em localStorage (`chave`) e lida por `notas()`.
- Para artefato do claude.ai: colar o JS inline (CSP bloqueia arquivo externo fora das CDNs permitidas) e declarar
  `capabilities: {comments: {}}` (ou `{"composer_only": true}` se só abrir o composer). Para ditar a nota local, declarar também a capability de microfone.
- Consumidores: Portfólio · Decisões do Portfólio (`Portfolio/evidence/261010_decisoes/tools/build.py`), geradores POP (`bin/mb_pop_tema.html_interacoes`), `bin/mb-interacoes.py`, modelo `../261010_decisoes-respondiveis/`.

## Gesto vigente (v1.5, 261017)

- **Segurar 0,4 s parado** abre o leque (`segurarMs: 400`, `cancelarAoMover: true`). Pedido registrado em `memoria/estado/DECISOES.md` (13/10): "400 ms exclusivamente parado". A folga de poucos px abaixo é a leitura da v1.5 para a tremida da mão; ainda não foi confirmada pelo <USUARIO>.
- "Parado" tem uma folga pequena para a tremida natural da mão: `tolerancia` 3 px no mouse e `toleranciaToque` 8 px no dedo ou caneta (escolhida por `pointerType`). Mexer mais que isso cancela até o próximo clique.
- Com `cancelarAoMover: false`, arrastar para a direita continua sendo seleção de texto.
- Mouse: segurar, deslizar até a opção e soltar escolhe; soltar sem deslizar fecha o leque. Dedo: soltar sem deslizar deixa o leque aberto e um toque na opção escolhe; tocar fora fecha.
- O segurar funciona em qualquer ferramenta (Interagir, Comentar, Desenhar, Aprovar). Esc volta a Interagir.
- As menções a **2 s** (v1.0) e **0,7 s** (v1.1) mais abaixo são histórico.

## O que mudou na v1.5 (261017)

- Com Comentar ou Aprovar ativos, segurar voltou a abrir o leque (o bug de 15/10 transformava o segurar em nota ou aprovação sem querer). O clique curto continua comentando ou aprovando.
- Fechar o leque tocando fora não cria nota. Com uma nota aberta, o 1º clique fora fecha a nota (o rascunho fica salvo) e o próximo comenta.
- Folga do "parado" separada por tipo de ponteiro (`tolerancia` mouse 3 px, `toleranciaToque` 8 px).
- Toque: soltar sem deslizar mantém o leque aberto; dedo sobre o leque não rola a página.
- Nota perto do rodapé abre acima do ponto; o chip não some em relatório baixo (a regra de 480 px vale só para tela de toque).
- Depois de escolher no leque, o foco do teclado volta para onde estava (ou para o chip, se o leque abriu por ele).
- Nota sem texto e sem rascunho não é gravada nem sincronizada e some ao fechar. Sem mudança real, as notas não são gravadas de novo.
- Sair da janela (blur) devolve a ferramenta a Interagir: uma ferramenta ativa por vez entre a mesa do app e o relatório.
- API nova para barras externas: `ferramentas()` (id, nome, ativa) e `dicaSegurar()` ("segure 0,4 s"). `CursorFerramentas.versao` = `'1.5'`.
- Teste de regressão: `evidence/261017_cursor-harness/teste-cursor/` (ver `LEIA.txt`): Edge headless pela mesa e pelo relatório reais (B1 a B16) e o motor Qt do app (`qt261013/261013_testar-cursor-v15.py` e `qt_alvo_controles.py`).

## O que mudou na v1.1 (261011) · histórico (o tempo vigente é 0,4 s parado, ver acima)

- **Segurar 0,7 s e poder mexer o mouse.** `segurarMs` padrão 700 (era 2000). Enquanto segura, o ponteiro anda à vontade; o anel acompanha e o menu abre onde o ponteiro estiver quando completa o tempo (não onde começou). Rolar a página continua cancelando. Ao abrir, a seleção de texto criada pelo arraste é limpa e o clique seguinte continua engolido. Chip: "segure 0,7 s".
- **`cancelarAoMover`** (padrão `false`). `true` volta ao jeito da v1.0: mexer mais que `tolerancia` (10 px) cancela.
- Segurar em cima de link, imagem ou texto já selecionado não dispara mais o arraste nativo do navegador (que cancelava o segurar). Elementos com `draggable="true"` da própria página continuam mandando: ali o segurar é cancelado e o arraste da página funciona.
- **Microfone na nota local.** Botão de microfone ao lado de Salvar; com o editor aberto, `Ctrl+Espaço` liga e desliga. Usa `SpeechRecognition`/`webkitSpeechRecognition` com `continuous` e `interimResults`, idioma `idiomaVoz` (padrão `pt-BR`). O texto final entra no textarea na posição do cursor; o provisório aparece em cinza/itálico embaixo do campo e só vira texto quando fica final. Estados: parado / ouvindo (pulso) / erro.
  - Para ao Salvar, ao fechar (Esc) e ao Excluir. Ao Salvar, o que ainda estava em cinza entra na nota; ao fechar ou excluir, é descartado. Se o navegador encerrar a escuta sozinho com texto em cinza na tela, esse texto entra no campo.
  - Sem suporte ou sem permissão (`not-allowed`, `service-not-allowed`, `audio-capture`, `network`, erro no `start`): o editor mostra "Microfone indisponível aqui. No Windows, use Win + H para ditar." e devolve o foco ao campo, para o Win + H digitar ali. Nada quebra. `no-speech` só avisa "Não ouvi nada."
  - `microfone: false` esconde o botão e desliga o atalho.
- **Acessibilidade.** Botões com `aria-label`; microfone com `aria-pressed` e `aria-describedby` apontando para o aviso (`role="status"`); foco visível em todos; `prefers-reduced-motion` troca o pulso por um anel fixo.
- **Eventos.** Novo `aoEvento('microfone', {estado, mensagem, erro})`. `segurou` agora manda a posição onde o menu abriu (`x`, `y`) e onde começou (`inicioX`, `inicioY`).
- **Bugs da v1.0 corrigidos.** (1) Redesenhar os pinos (resize da janela, página mudando de altura) apagava o editor de nota aberto. (2) `Esc` com o foco dentro do menu gerava `TypeError` no console. (3) `destruir()` não removia os listeners de scroll e resize.

## Onde o microfone funciona

| Onde | Resultado |
|---|---|
| Chrome ou Edge em `https://` ou `http://localhost` | Funciona. Na 1ª vez o navegador pede permissão do microfone. O reconhecimento roda online (serviço de voz do navegador). |
| `file://` (abrir o `demo.html` direto do disco) | Depende do navegador e da versão; se negar, aparece o aviso e o Win + H resolve. |
| Artefato do claude.ai | Só com a capability de microfone declarada no publish. Sem ela o iframe bloqueia (`not-allowed`) e aparece o aviso. |
| Firefox | Não tem a API: aviso + Win + H. |
| Mac | `Ctrl+Espaço` costuma trocar o idioma do teclado no sistema; usar o botão. |

## Testes

261017 (v1.5), teste de regressão em `evidence/261017_cursor-harness/teste-cursor/` (`LEIA.txt`): Edge headless com a mesa e o relatório reais (`central_reports.render_report`), 29 verificações herdadas mais B12 a B16 (foco depois da escolha, tremida de 2 px no mouse não cancela e 6 px cancela, tremida de 5 px no dedo não cancela, dedo solto mantém o leque, nota vazia não gravada); harness 261013 no motor Qt do app e `qt_alvo_controles.py` com mouse nativo.

261010 (v1.0): segurar/cancelar ao mover, clique engolido após abrir o menu, troca de ferramenta, nota local criada/editada/excluída, celular 390 px por emulação.

261011 (v1.1), Playwright + Chromium headless, `demo.html` servida em http://127.0.0.1: segurar e mover 60 px em 5 passos durante 0,6 s abre o menu aos 0,75 s no ponto final, com o anel seguindo o ponteiro e sem texto selecionado; soltar em 0,5 s não abre; rolar durante o segurar cancela; segurar sobre texto selecionado e mover abre o menu; `cancelarAoMover:true` repete a v1.0; Comentar abre o editor com microfone; reconhecedor falso (provisório "teste de" → final "teste de voz") preenche o campo na posição do cursor; Ctrl+Espaço liga/desliga; Salvar e Esc param o microfone; sem a API aparece o aviso; reduced-motion tira o pulso; editor sobrevive a resize; zero erros de console.

Não testado: voz real (microfone físico, prompt de permissão, qualidade do reconhecimento em pt-BR, Edge), openComposer real (depende do clique humano no claude.ai).
