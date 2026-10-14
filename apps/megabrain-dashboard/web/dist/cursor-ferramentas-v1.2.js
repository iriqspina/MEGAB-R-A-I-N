/* cursor-ferramentas v1.4 · 261013 · MEGABRAIN
   v1.4: no app Qt, voz usa ditado do Windows por clique explícito, sem SpeechRecognition;
   rascunho salvo a cada entrada de texto, inclusive ditado. O Windows controla ouvir/parar.
   v1.3: 0,4 s exclusivamente parado; mover cancela até o próximo clique.
   Soltar fecha o menu; arrastar até uma opção e soltar escolhe.
   Fonte única: MEGA B R A I  N/motor/modelos/interacoes/261010_cursor-ferramentas/cursor-ferramentas.js
   Ideia do Usuário (261010): segurar o botão principal abre um menu em leque em volta do ponteiro;
   ali o cursor vira uma ferramenta (ex.: comentar).
   v1.1 (261011): segurar 0,7 s (segurarMs: 700) e o ponteiro pode andar enquanto segura; o menu abre onde
   o ponteiro estiver quando o tempo fecha (cancelarAoMover: true volta ao jeito da v1.0, com tolerancia).
   A nota local ganhou ditado por voz: botão de microfone ao lado de Salvar e Ctrl+Espaço com o editor aberto
   (opções microfone, idiomaVoz). Sem suporte ou sem permissão, avisa e sugere Win + H.
   v1.2 (261011):
   · arrastar para a direita durante o segurar é seleção de texto: cancela o segurar e a seleção nativa fica.
     Esquerda/cima/baixo continuam segurando. user-select:none só entra quando o menu abre.
   · segurar → deslizar até a opção → soltar escolhe (sem clique extra); clique, setas/Enter e Esc continuam.
     O leque se encaixa na janela contando rótulos e contorno de foco (390 px a 1440 px).
   · microfone no menu: "ditar ao comentar" (opt-in, salvo em chavePrefs, padrão desligado).
   · Desenhar: pincel, marcador, borracha (apaga traços inteiros), cor, espessura, desfazer, limpar.
     Camada no documento (rola com a página), salva em chaveDesenhos, separada das notas.
   · Aprovar (polegar) por âncora: [data-cf-ancora] quando houver, senão o caminho do elemento;
     salva em chaveAprovacoes; API confirmar/confirmado/desconfirmar/aprovacoes e opção confirmados.
   Uso: CursorFerramentas.iniciar({ ...opções }) → controle { usar, atual, abrirMenu, fecharMenu,
   notas, limparNotas, configurar, destruir, ditarAoComentar, desenhos, pincel, desfazer, limparDesenhos,
   confirmar, desconfirmar, confirmado, aprovacoes }. Sem dependências; injeta o próprio CSS. */
(function (global) {
  'use strict';
  if (global.CursorFerramentas) return;

  var ICONES = {
    interagir: '<path d="M5 3l13 7.5-6 1.6L9.4 18z"/>',
    comentar: '<path d="M4 5h16v11H9l-5 4V5z"/><path d="M12 8v5M9.5 10.5h5"/>',
    desenhar: '<path d="M4 20l1.2-4.8L16 4.4l3.6 3.6L8.8 18.8z"/><path d="M13.8 6.6l3.6 3.6"/>',
    polegar: '<path d="M7 10.5V20H4v-9.5z"/><path d="M7 10.5 11 4c1.6 0 2.6 1.1 2.3 2.7L12.7 10H19a2 2 0 0 1 2 2.3l-1.1 5.9A2.2 2.2 0 0 1 17.7 20H7"/>',
    fechar: '<path d="M7 7l10 10M17 7 7 17"/>',
    microfone: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M8.5 21h7"/>',
    semMicrofone: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M8.5 21h7M4 4l16 16"/>'
  };
  function svg(p) { return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' + p + '</svg>'; }
  var CURSOR_COMENTAR = 'url("data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">' +
    '<path d="M3 3h25v17H12l-9 8z" fill="#EC0F7C" stroke="#fff" stroke-width="2" stroke-linejoin="round"/>' +
    '<path d="M15.5 7.5v8M11.5 11.5h8" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/></svg>') +
    '") 3 28, crosshair';
  var MSG_SEM_MIC = 'Microfone indisponível aqui. No Windows, use Win + H para ditar.';
  var MSG_MIC = {
    'sem-suporte': 'Este navegador não tem ditado por voz. No Windows, use Win + H.',
    'not-allowed': 'Microfone bloqueado: permissão negada. No Windows, use Win + H.',
    'service-not-allowed': 'Microfone bloqueado: permissão negada. No Windows, use Win + H.',
    'audio-capture': 'Nenhum microfone encontrado. No Windows, use Win + H.',
    'network': 'O ditado do navegador precisa de rede e falhou. No Windows, use Win + H.'
  };
  var NS = 'http://www.w3.org/2000/svg';

  var CSS = [
    ':root{--cf-acento:#EC0F7C;--cf-fundo:#1C1C2B;--cf-tinta:#FFFFFF;--cf-borda:rgba(255,255,255,.16);--cf-sombra:0 14px 36px rgba(0,0,0,.42);--cf-foco:#1CB0F6;--cf-chip-bottom:16px;--cf-chip-left:16px}',
    'html.cf-segurando,html.cf-segurando *{user-select:none!important;-webkit-user-select:none!important;-webkit-touch-callout:none!important}',
    '.cf-anel{position:fixed;left:0;top:0;width:60px;height:60px;margin:-30px 0 0 -30px;pointer-events:none;z-index:2147483600;opacity:0;transition:opacity .15s}',
    '.cf-anel.on{opacity:1}',
    '.cf-anel circle{fill:none;stroke-width:4}',
    '.cf-anel .cf-trilho{stroke:rgba(128,128,128,.35)}',
    '.cf-anel .cf-prog{stroke:var(--cf-acento);stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%}',
    '.cf-menu:not(.aberto),.cf-menu:not(.aberto) *{pointer-events:none!important}',
    '.cf-menu{position:fixed;inset:0;z-index:2147483601}',
    '.cf-veu{position:absolute;inset:0;background:rgba(0,0,0,.08)}',
    '.cf-botao{position:absolute;width:54px;height:54px;margin:-27px 0 0 -27px;border-radius:50%;border:0;padding:0;background:var(--cf-fundo);color:var(--cf-tinta);box-shadow:var(--cf-sombra),0 0 0 1px var(--cf-borda);display:grid;place-items:center;cursor:pointer;opacity:0;transform:translate(0,0) scale(.25);transition:transform .24s cubic-bezier(.2,.9,.3,1.25),opacity .18s,background .15s;font:inherit}',
    '.cf-menu.aberto .cf-botao{opacity:1;transform:translate(var(--dx),var(--dy)) scale(1)}',
    '.cf-botao svg{width:23px;height:23px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}',
    '.cf-botao:hover,.cf-botao.mirando{background:color-mix(in srgb,var(--cf-acento) 30%,var(--cf-fundo))}',
    '.cf-botao.ativo{background:var(--cf-acento);color:#fff}',
    '.cf-botao.mirando{box-shadow:var(--cf-sombra),0 0 0 3px var(--cf-tinta)}',
    '.cf-botao:focus-visible{outline:3px solid var(--cf-foco);outline-offset:3px}',
    '.cf-centro{width:40px;height:40px;margin:-20px 0 0 -20px}',
    '.cf-centro svg{width:18px;height:18px}',
    '.cf-rot{position:absolute;left:50%;transform:translateX(-50%);white-space:nowrap;font:600 12px/1 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--cf-fundo);color:var(--cf-tinta);padding:6px 8px;border-radius:7px;box-shadow:0 0 0 1px var(--cf-borda);pointer-events:none}',
    '.cf-rot.cima{bottom:calc(100% + 7px)}.cf-rot.baixo{top:calc(100% + 7px)}',
    '.cf-alvo{position:fixed;pointer-events:none;z-index:2147483590;border:2px dashed var(--cf-acento);border-radius:8px;background:color-mix(in srgb,var(--cf-acento) 7%,transparent);transition:all .08s}',
    'html.cf-ferr-comentar,html.cf-ferr-comentar *{cursor:' + CURSOR_COMENTAR + '!important}',
    'html.cf-ferr-aprovar,html.cf-ferr-aprovar *{cursor:pointer!important}',
    'html.cf-ferr-desenhar,html.cf-ferr-desenhar *{cursor:crosshair!important;user-select:none!important;-webkit-user-select:none!important;touch-action:none!important}',
    'html.cf-ferr-comentar .cf-ui,html.cf-ferr-comentar .cf-ui *,html.cf-ferr-desenhar .cf-ui,html.cf-ferr-desenhar .cf-ui *{cursor:pointer!important;touch-action:manipulation!important}',
    'html.cf-ferr-comentar .cf-editor textarea{cursor:text!important}',
    '.cf-chip{position:fixed;left:var(--cf-chip-left);bottom:calc(var(--cf-chip-bottom) + env(safe-area-inset-bottom,0px));z-index:2147483500}',
    '.cf-chip-btn{display:inline-flex;align-items:center;gap:8px;border:0;border-radius:999px;padding:9px 13px 9px 10px;background:var(--cf-fundo);color:var(--cf-tinta);box-shadow:var(--cf-sombra),0 0 0 1px var(--cf-borda);font:600 13px/1.1 system-ui,-apple-system,"Segoe UI",sans-serif;cursor:pointer}',
    '.cf-chip-btn svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}',
    '.cf-chip-btn small{font-weight:500;opacity:.72}',
    '.cf-chip-btn.ativo{background:var(--cf-acento);color:#fff}',
    '.cf-chip-btn:focus-visible{outline:3px solid var(--cf-foco);outline-offset:2px}',
    '.cf-pinos{position:absolute;left:0;top:0;width:0;height:0;z-index:2147483400}',
    '.cf-pino{position:absolute;width:28px;height:28px;margin:-28px 0 0 -2px;border:2px solid #fff;border-radius:14px 14px 14px 3px;background:var(--cf-acento);color:#fff;font:700 13px/24px system-ui,sans-serif;text-align:center;box-shadow:0 6px 16px rgba(0,0,0,.35);cursor:pointer;padding:0}',
    '.cf-polegar{position:absolute;width:30px;height:30px;margin:-15px 0 0 -15px;border:2px solid #fff;border-radius:50%;background:#2E9E00;color:#fff;display:grid;place-items:center;box-shadow:0 6px 16px rgba(0,0,0,.35);cursor:pointer;padding:0}',
    '.cf-polegar svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}',
    '.cf-pino:focus-visible,.cf-polegar:focus-visible{outline:3px solid var(--cf-foco);outline-offset:2px}',
    'html.cf-ferr-desenhar input,html.cf-ferr-desenhar textarea,html.cf-ferr-desenhar [contenteditable]{user-select:text!important;-webkit-user-select:text!important;touch-action:auto!important;cursor:text!important}',
    '.cf-desenho,.cf-desenho *{pointer-events:none}',
    '.cf-desenho{position:absolute;left:0;top:0;width:1px;height:1px;overflow:visible;z-index:2147483300}',
    '.cf-desenho path{fill:none;stroke-linecap:round;stroke-linejoin:round}',
    '.cf-barra{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(var(--cf-chip-bottom) + 56px + env(safe-area-inset-bottom,0px));z-index:2147483550;box-sizing:border-box;width:max-content;max-width:calc(100vw - 16px);display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;justify-content:center;padding:8px;border-radius:14px;background:var(--cf-fundo);color:var(--cf-tinta);box-shadow:var(--cf-sombra),0 0 0 1px var(--cf-borda);font:600 13px/1.1 system-ui,-apple-system,"Segoe UI",sans-serif}',
    '.cf-barra[hidden]{display:none}',
    '.cf-grupo{display:inline-flex;gap:4px;align-items:center}',
    '.cf-barra button{border:0;border-radius:999px;padding:7px 10px;background:rgba(127,127,127,.2);color:inherit;font:inherit;cursor:pointer}',
    '.cf-barra button[aria-checked="true"]{background:var(--cf-acento);color:#fff}',
    '.cf-barra button:disabled{opacity:.45;cursor:default}',
    '.cf-barra .cf-cor{width:26px;height:26px;padding:0;box-shadow:inset 0 0 0 2px rgba(255,255,255,.45)}',
    '.cf-barra .cf-cor[aria-checked="true"]{box-shadow:0 0 0 2px var(--cf-fundo),0 0 0 4px var(--cf-tinta)}',
    '.cf-barra label{display:inline-flex;align-items:center;gap:6px}',
    '.cf-barra input{width:84px;margin:0}',
    '.cf-barra button:focus-visible,.cf-barra input:focus-visible{outline:2px solid var(--cf-foco);outline-offset:2px}',
    '.cf-editor{position:absolute;width:260px;max-width:calc(100vw - 32px);background:var(--cf-fundo);color:var(--cf-tinta);border-radius:12px;box-shadow:var(--cf-sombra),0 0 0 1px var(--cf-borda);padding:10px;display:grid;gap:8px;font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;z-index:2147483450}',
    '.cf-editor .cf-ed-onde{font-size:12px;opacity:.72;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
    '.cf-editor textarea{width:100%;box-sizing:border-box;min-height:74px;resize:vertical;border-radius:8px;border:1px solid var(--cf-borda);background:rgba(127,127,127,.12);color:inherit;font:inherit;padding:8px}',
    '.cf-editor textarea:focus{outline:2px solid var(--cf-foco);outline-offset:1px}',
    '.cf-editor .cf-provisorio{font-style:italic;font-size:13px;line-height:1.35;opacity:.62;overflow-wrap:anywhere}',
    '.cf-editor .cf-mic-aviso{font-size:12px;line-height:1.35;opacity:.85}',
    '.cf-editor .cf-provisorio:empty,.cf-editor .cf-mic-aviso:empty{display:none}',
    '.cf-ed-acoes{display:flex;gap:6px;justify-content:flex-end;align-items:center}',
    '.cf-ed-acoes button{border:0;border-radius:999px;padding:7px 12px;font:600 13px system-ui,sans-serif;cursor:pointer;background:rgba(127,127,127,.2);color:inherit}',
    '.cf-ed-acoes .cf-salvar{background:var(--cf-acento);color:#fff}',
    '.cf-ed-acoes .cf-mic{width:32px;height:32px;padding:0;display:grid;place-items:center;flex:none}',
    '.cf-ed-acoes .cf-mic svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}',
    '.cf-ed-acoes .cf-mic[aria-pressed="true"]{background:var(--cf-acento);color:#fff;animation:cf-pulso 1.3s ease-out infinite}',
    '.cf-ed-acoes .cf-mic.erro{background:transparent;box-shadow:inset 0 0 0 1.5px currentColor;opacity:.8}',
    '@keyframes cf-pulso{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--cf-acento) 65%,transparent)}70%{box-shadow:0 0 0 9px transparent}100%{box-shadow:0 0 0 0 transparent}}',
    '.cf-ed-acoes button:focus-visible{outline:2px solid var(--cf-foco);outline-offset:2px}',
    '.cf-toast{position:fixed;left:50%;top:16px;transform:translateX(-50%);z-index:2147483602;background:var(--cf-fundo);color:var(--cf-tinta);box-shadow:var(--cf-sombra),0 0 0 1px var(--cf-borda);border-radius:999px;padding:9px 15px;font:600 13px/1.3 system-ui,sans-serif;max-width:calc(100vw - 32px);text-align:center;pointer-events:none}',
    '@media (max-height:480px){.dr-barra{position:static!important;bottom:auto!important;z-index:auto!important}.cf-chip{position:static;left:auto;bottom:auto;max-width:100%;margin:12px 16px;box-sizing:border-box}.cf-chip-btn{max-width:100%;white-space:normal;flex-wrap:wrap;overflow-wrap:anywhere;justify-content:center}}',
    '@media (prefers-reduced-motion:reduce){.cf-botao,.cf-anel,.cf-alvo{transition:none!important}.cf-ed-acoes .cf-mic[aria-pressed="true"]{animation:none!important;box-shadow:0 0 0 3px color-mix(in srgb,var(--cf-acento) 45%,transparent)}}'
  ].join('\n');

  var instanciaAtiva = null;
  function iniciar(opcoes) {
    if (instanciaAtiva) instanciaAtiva.destruir();
    var o = {
      segurarMs: 400,
      cancelarAoMover: true,
      atrasoVisualMs: 80,
      tolerancia: 0,
      raio: 82,
      ignorar: 'input,textarea,select,[contenteditable=""],[contenteditable="true"],[data-cf-ignorar]',
      modo: 'auto',
      chip: true,
      chave: 'cf-notas:' + location.pathname,
      chaveDesenhos: 'cf-desenhos:' + location.pathname,
      chaveAprovacoes: 'cf-aprovacoes:' + location.pathname,
      chavePrefs: 'cf-prefs',
      microfone: true,
      ditarAoComentar: false,
      idiomaVoz: 'pt-BR',
      cores: ['#EC0F7C', '#1CB0F6', '#2E9E00', '#FFC800', '#1C1C2B'],
      confirmados: null,
      ferramentas: null,
      aoMudar: null,
      aoMudarNotas: null,
      aoSalvarNota: null,
      aoMudarDesenhos: null,
      aoAprovar: null,
      aoEvento: null
    };
    for (var k in (opcoes || {})) o[k] = opcoes[k];

    var doc = document, html = doc.documentElement;
    if (!doc.getElementById('cf-estilo')) {
      var st = doc.createElement('style'); st.id = 'cf-estilo'; st.textContent = CSS; (doc.head || html).appendChild(st);
    }

    var FERR = o.ferramentas || [
      { id: 'interagir', nome: 'Interagir', icone: ICONES.interagir },
      { id: 'comentar', nome: 'Comentar', icone: ICONES.comentar, cursorClasse: 'cf-ferr-comentar', destacar: true, aoClicar: comentar },
      { id: 'desenhar', nome: 'Desenhar', icone: ICONES.desenhar, cursorClasse: 'cf-ferr-desenhar', desenho: true, aoClicar: function () {} },
      { id: 'aprovar', nome: 'Aprovar', icone: ICONES.polegar, cursorClasse: 'cf-ferr-aprovar', destacar: true, ancora: true, aoClicar: aprovarClique }
    ];
    var atual = FERR[0], destruida = false;
    var segurando = null, engolir = false, engolirT = 0, menu = null, menuAbertoEm = 0, focoAntes = null, pontos = [], deslize = null;
    var caixaAlvo = null, chip = null, chipBtn = null, toastEl = null, toastT = 0;
    var shell = null, pinos = null, editor = null, voz = null, camadaD = null, barra = null, traco = null, historico = [], micHotkey = null;
    var notas = carregar();
    var prefs = ler(o.chavePrefs, {}); if (!prefs || typeof prefs !== 'object') prefs = {};
    var ditar = typeof prefs.ditarAoComentar === 'boolean' ? prefs.ditarAoComentar : o.ditarAoComentar === true;
    var pincel = { modo: 'pincel', cor: o.cores[0], espessura: 4 };
    if (prefs.pincel) for (var kp in pincel) if (prefs.pincel[kp] != null) pincel[kp] = prefs.pincel[kp];
    if (pincel.modo === 'borracha') pincel.modo = 'pincel'; // ao recarregar, o primeiro gesto desenha em vez de apagar
    var tracos = lerTracos();
    var aprovs = ler(o.chaveAprovacoes, []); if (!Array.isArray(aprovs)) aprovs = [];

    function evento(tipo, dados) { if (typeof o.aoEvento === 'function') try { o.aoEvento(tipo, dados || {}); } catch (e) {} }
    function ehUI(el) { return !!(el && el.closest && el.closest('.cf-ui')); }
    function ignorado(el) { return !!(o.ignorar && el && el.closest && el.closest(o.ignorar)); }
    function ler(chave, padrao) { try { var v = JSON.parse(global.localStorage.getItem(chave)); return v == null ? padrao : v; } catch (e) { return padrao; } }
    function gravar(chave, v) { try { global.localStorage.setItem(chave, JSON.stringify(v)); } catch (e) {} }

    /* ---------- segurar ---------- */
    var anel = doc.createElement('div'); anel.className = 'cf-anel cf-ui'; anel.setAttribute('aria-hidden', 'true');
    anel.innerHTML = '<svg viewBox="0 0 60 60"><circle class="cf-trilho" cx="30" cy="30" r="24"/><circle class="cf-prog" cx="30" cy="30" r="24" stroke-dasharray="150.8" stroke-dashoffset="150.8"/></svg>';
    doc.body.appendChild(anel);
    var prog = anel.querySelector('.cf-prog');

    function posAnel(x, y) { anel.style.left = x + 'px'; anel.style.top = y + 'px'; }
    function limparSelecao(sempre) {
      try {
        var sel = global.getSelection && global.getSelection();
        if (sel && (sempre || (sel.rangeCount && !sel.isCollapsed))) sel.removeAllRanges();
      } catch (er) {}
    }
    function cancelar() {
      if (!segurando) return;
      clearTimeout(segurando.tv); clearTimeout(segurando.ta); segurando = null;
      html.classList.remove('cf-segurando'); anel.classList.remove('on');
      prog.style.transition = 'none'; prog.style.strokeDashoffset = '150.8';
    }
    function aoBaixar(e) {
      if (e.button !== 0 || e.isPrimary === false) return;
      clearTimeout(engolirT); engolir = false;
      if (menu || ehUI(e.target)) return;
      if (ignorado(e.target)) return;
      cancelar();
      // x/y: onde começou; cx/cy: onde o ponteiro está agora (o menu abre aqui)
      var s = segurando = { x: e.clientX, y: e.clientY, cx: e.clientX, cy: e.clientY, id: e.pointerId, tipo: e.pointerType };
      if (atual.desenho) { e.preventDefault(); comecarTraco(e); }
      posAnel(s.x, s.y);
      s.tv = setTimeout(function () {
        if (segurando !== s) return;
        // só o anel: ainda pode virar seleção de texto à direita, então nada de user-select:none aqui
        posAnel(s.cx, s.cy); anel.classList.add('on');
        prog.style.transition = 'none'; prog.style.strokeDashoffset = '150.8';
        void prog.getBoundingClientRect();
        prog.style.transition = 'stroke-dashoffset ' + Math.max(0, o.segurarMs - o.atrasoVisualMs) + 'ms linear';
        prog.style.strokeDashoffset = '0';
      }, o.atrasoVisualMs);
      s.ta = setTimeout(function () {
        if (segurando !== s) return;
        cancelar(); engolir = true;
        descartarTraco(); // o segurar virou menu: o ponto inicial não era desenho
        html.classList.add('cf-segurando'); // agora é segurar de verdade: sem seleção de texto até soltar
        limparSelecao(true);
        abrirMenu(s.cx, s.cy, s.id == null ? 0 : s.id);
        evento('segurou', { x: s.cx, y: s.cy, inicioX: s.x, inicioY: s.y });
      }, o.segurarMs);
    }
    function aoMover(e) {
      var s = segurando;
      if (s && (s.id == null || e.pointerId === s.id)) {
        var dx = e.clientX - s.x, dy = e.clientY - s.y;
        if (o.cancelarAoMover || traco) { if (Math.hypot(dx, dy) > o.tolerancia) cancelar(); } // desenhando: mexeu = traço
        else if (dx > o.tolerancia && dx >= Math.abs(dy)) { cancelar(); evento('segurar', { cancelado: 'selecao' }); } // à direita = selecionar texto
        else { s.cx = e.clientX; s.cy = e.clientY; posAnel(s.cx, s.cy); }
      }
      if (traco && e.pointerId === traco.id) estenderTraco(e);
      if (menu && deslize && e.pointerId === deslize.id) {
        if (Math.hypot(e.clientX - deslize.x, e.clientY - deslize.y) > 6) deslize.mexeu = true;
        mirar(itemEm(e.clientX, e.clientY));
      }
      if (engolir && (e.buttons & 1)) limparSelecao();
      if (!segurando && !menu && atual.destacar) destacar(e.clientX, e.clientY);
    }
    function aoSoltar(e) {
      if (segurando && e && e.pointerId !== segurando.id) return;
      if (deslize && e && e.pointerId !== deslize.id) return;
      cancelar(); html.classList.remove('cf-segurando');
      if (traco && (!e || e.pointerId === traco.id)) terminarTraco();
      if (menu && deslize) { // segurou, deslizou e soltou: escolhe sem clique extra
        var d = deslize; deslize = null; mirar(null);
        if (e && e.type === 'pointerup' && d.mexeu) soltarNoMenu(itemEm(e.clientX, e.clientY));
        else fecharMenu();
      }
      if (engolir) { clearTimeout(engolirT); engolirT = setTimeout(function () { engolir = false; }, 700); }
    }
    // arrastar link/imagem/texto selecionado dispararia o arraste nativo (e pointercancel) no meio do segurar
    function aoArrastar(e) {
      if (!segurando || o.cancelarAoMover) return;
      var t = e.target; if (t && t.nodeType === 3) t = t.parentElement;
      if (t && t.closest && t.closest('[draggable="true"]')) { cancelar(); return; } // arraste da própria página: ela manda
      e.preventDefault();
    }
    function aoRolar() { cancelar(); esconderAlvo(); }
    function aoClicar(e) {
      if (engolir) { e.preventDefault(); e.stopPropagation(); engolir = false; return; }
      if (ignorado(e.target)) return;
      if (atual.aoClicar && !menu && !ehUI(e.target)) {
        e.preventDefault(); e.stopPropagation();
        var alvo = e.target;
        atual.aoClicar({ alvo: alvo, x: e.clientX, y: e.clientY, evento: e }, api);
      }
    }
    function aoMousedown(e) {
      if (ignorado(e.target)) return;
      if (atual.aoClicar && !menu && !ehUI(e.target) && e.button === 0) e.preventDefault();
    }
    function aoContexto(e) { if (segurando) e.preventDefault(); }
    function aoSelecionar(e) { if ((segurando || engolir) && html.classList.contains('cf-segurando')) e.preventDefault(); }
    function aoTecla(e) {
      if (editor && editor.mic && e.ctrlKey && !e.altKey && !e.metaKey && (e.code === 'Space' || e.key === ' ')) {
        e.preventDefault(); if (!e.repeat) { if (vozNativa()) micHotkey = editor; else alternarMic(); } return;
      }
      if (!ignorado(e.target) && atual.desenho && !menu && (e.ctrlKey || e.metaKey) && !e.shiftKey && (e.key === 'z' || e.key === 'Z')) { e.preventDefault(); desfazer(); return; }
      if (e.key !== 'Escape') return;
      if (menu) { fecharMenu(); e.preventDefault(); return; }
      if (editor) { fecharEditor(); e.preventDefault(); return; }
      if (ignorado(e.target)) return;
      if (atual !== FERR[0]) { usar(FERR[0].id); e.preventDefault(); }
    }
    function aoSoltarTecla(e) {
      if (micHotkey && !e.ctrlKey && (e.key === 'Control' || e.code === 'Space' || e.key === ' ')) {
        var ed = micHotkey; micHotkey = null;
        if (editor === ed) alternarMic();
      }
    }

    /* ---------- menu em leque ---------- */
    function itensMenu() {
      var its = FERR.map(function (f) { return { id: f.id, nome: f.nome, rotulo: f.nome, icone: f.icone, ativo: f === atual, papel: 'menuitemradio' }; });
      if (o.microfone !== false) {
        var tem = vozNativa() || !!Reconhecedor();
        its.push({ id: 'cf-microfone', mic: true, ativo: ditar, papel: 'menuitemcheckbox', icone: tem ? ICONES.microfone : ICONES.semMicrofone,
          nome: 'Ditado: ' + (ditar ? 'ligado' : 'desligado') + (tem ? '' : ' (sem suporte)'),
          rotulo: vozNativa() ? 'Ditado do Windows ao comentar (abertura por clique)' : 'Ativar microfone ao comentar' + (tem ? '' : ' (sem suporte neste navegador)') });
      }
      return its;
    }
    function abrirMenu(x, y, idPonteiro) {
      if (menu) return;
      var its = itensMenu(), n = its.length;
      focoAntes = doc.activeElement;
      menu = doc.createElement('div'); menu.className = 'cf-menu cf-ui'; menu.setAttribute('role', 'menu'); menu.setAttribute('aria-label', 'Ferramentas do cursor');
      var veu = doc.createElement('div'); veu.className = 'cf-veu'; menu.appendChild(veu);
      veu.addEventListener('pointerdown', function (ev) { ev.preventDefault(); fecharMenu(); });
      var passo = n <= 5 ? 62 : 360 / n;
      pontos = its.map(function (it, i) {
        var ang = (n <= 5 ? (-90 + (i - (n - 1) / 2) * passo) : (-90 + i * passo)) * Math.PI / 180;
        var cima = Math.sin(ang) < -0.12;
        var b = doc.createElement('button'); b.type = 'button'; b.className = 'cf-botao' + (it.ativo ? ' ativo' : '');
        b.setAttribute('role', it.papel); b.setAttribute('aria-checked', String(it.ativo)); b.setAttribute('aria-label', it.rotulo);
        b.setAttribute('data-cf-item', it.id);
        b.style.transitionDelay = (i * 35) + 'ms';
        b.innerHTML = svg(it.icone) + '<span class="cf-rot ' + (cima ? 'cima' : 'baixo') + '"></span>';
        var rot = b.querySelector('.cf-rot'); rot.textContent = it.nome;
        b.addEventListener('click', function () { if (Date.now() - menuAbertoEm < 250) return; escolher(it); });
        menu.appendChild(b);
        return { el: b, it: it, ang: ang, cima: cima, rot: rot };
      });
      var c = doc.createElement('button'); c.type = 'button'; c.className = 'cf-botao cf-centro'; c.setAttribute('aria-label', 'Fechar menu');
      c.setAttribute('data-cf-item', 'cf-fechar');
      c.innerHTML = svg(ICONES.fechar);
      c.addEventListener('click', function () { if (Date.now() - menuAbertoEm < 250) return; fecharMenu(); });
      menu.appendChild(c);
      pontos.push({ el: c, centro: true });
      var este = menu;
      menu.addEventListener('keydown', function (ev) {
        if (menu !== este) return; // Esc já fechou este menu no listener global
        var bs = Array.prototype.slice.call(este.querySelectorAll('.cf-botao'));
        var i = bs.indexOf(doc.activeElement);
        if (ev.key === 'ArrowRight' || ev.key === 'ArrowDown' || (ev.key === 'Tab' && !ev.shiftKey)) { ev.preventDefault(); bs[(i + 1) % bs.length].focus(); }
        else if (ev.key === 'ArrowLeft' || ev.key === 'ArrowUp' || (ev.key === 'Tab' && ev.shiftKey)) { ev.preventDefault(); bs[(i - 1 + bs.length) % bs.length].focus(); }
      });
      doc.body.appendChild(menu);
      encaixar(x, y);
      deslize = idPonteiro != null ? { id: idPonteiro, x: x, y: y, mexeu: false } : null;
      menuAbertoEm = Date.now();
      esconderAlvo();
      requestAnimationFrame(function () { requestAnimationFrame(function () {
        if (!menu) return; menu.classList.add('aberto');
        var at = menu.querySelector('.cf-botao.ativo') || menu.querySelector('.cf-botao'); if (at) at.focus({ preventScroll: true });
      }); });
      evento('menu', { aberto: true });
    }
    // encaixa o leque inteiro (botões, rótulos e contorno de foco) na janela; se não couber, encolhe o raio
    function encaixar(x, y) {
      var w = global.innerWidth, h = global.innerHeight, M = 8, B = 33, R = o.raio, ext;
      for (;;) {
        ext = { l: -26, r: 26, t: -26, b: 26 };
        pontos.forEach(function (p) {
          if (p.centro) return;
          p.dx = Math.round(Math.cos(p.ang) * R); p.dy = Math.round(Math.sin(p.ang) * R);
          var lw = p.rot.offsetWidth || p.rot.textContent.length * 7 + 16, lh = p.rot.offsetHeight || 24;
          var ly = p.cima ? p.dy - 34 - lh : p.dy + 34;
          ext.l = Math.min(ext.l, p.dx - B, p.dx - lw / 2 - 1); ext.r = Math.max(ext.r, p.dx + B, p.dx + lw / 2 + 1);
          ext.t = Math.min(ext.t, p.dy - B, ly - 1); ext.b = Math.max(ext.b, p.dy + B, ly + lh + 1);
        });
        if ((ext.r - ext.l <= w - 2 * M && ext.b - ext.t <= h - 2 * M) || R <= 58) break;
        R -= 6;
      }
      var cx = entre(x, M - ext.l, w - M - ext.r), cy = entre(y, M - ext.t, h - M - ext.b);
      pontos.forEach(function (p) {
        p.dx = p.dx || 0; p.dy = p.dy || 0; p.x = cx + p.dx; p.y = cy + p.dy;
        p.el.style.left = cx + 'px'; p.el.style.top = cy + 'px';
        p.el.style.setProperty('--dx', p.dx + 'px'); p.el.style.setProperty('--dy', p.dy + 'px');
      });
    }
    function entre(v, min, max) { return min > max ? (min + max) / 2 : Math.min(Math.max(v, min), max); }
    function itemEm(x, y) {
      var melhor = null, dm = Infinity;
      pontos.forEach(function (p) { var d = Math.hypot(x - p.x, y - p.y); if (d <= (p.centro ? 22 : 31) && d < dm) { dm = d; melhor = p; } });
      return melhor;
    }
    function mirar(p) { pontos.forEach(function (q) { q.el.classList.toggle('mirando', q === p); }); }
    function soltarNoMenu(p) {
      if (!p) { fecharMenu(); return; }
      if (p.centro) fecharMenu(); else escolher(p.it);
    }
    function escolher(it) {
      if (it.mic) { fecharMenu(true); alternarDitado(); return; }
      usar(it.id); fecharMenu(true);
    }
    function fecharMenu(escolheu) {
      if (!menu) return;
      var m = menu; menu = null; deslize = null; pontos = []; m.classList.remove('aberto');
      setTimeout(function () { if (m.parentNode) m.parentNode.removeChild(m); }, 260);
      if (!escolheu && focoAntes && focoAntes.focus) try { focoAntes.focus({ preventScroll: true }); } catch (e) {}
      evento('menu', { aberto: false });
    }

    /* ---------- ferramenta atual ---------- */
    function usar(id) {
      var f = FERR.filter(function (x) { return x.id === id; })[0]; if (!f) return;
      if (traco) terminarTraco();
      FERR.forEach(function (x) { if (x.cursorClasse) html.classList.remove(x.cursorClasse); });
      atual = f; if (f.cursorClasse) html.classList.add(f.cursorClasse);
      if (!f.destacar) esconderAlvo();
      mostrarBarra(!!f.desenho);
      atualizarChip();
      toast(f.id === FERR[0].id ? 'Ferramenta: ' + f.nome + '. Cliques voltam ao normal.' : 'Ferramenta: ' + f.nome + (f.desenho ? '. Arraste para desenhar.' : '. Clique onde quiser.') + ' Esc volta ao normal.');
      if (typeof o.aoMudar === 'function') try { o.aoMudar(f.id, f); } catch (e) {}
      evento('ferramenta', { id: f.id });
    }
    function destacar(x, y) {
      var el = doc.elementFromPoint(x, y);
      if (el && atual.ancora && el.closest) el = el.closest('[data-cf-ancora]') || el;
      if (!el || ehUI(el) || el === doc.body || el === html) { esconderAlvo(); return; }
      if (!caixaAlvo) { caixaAlvo = doc.createElement('div'); caixaAlvo.className = 'cf-alvo cf-ui'; doc.body.appendChild(caixaAlvo); }
      var r = el.getBoundingClientRect();
      caixaAlvo.style.display = 'block';
      caixaAlvo.style.left = (r.left - 3) + 'px'; caixaAlvo.style.top = (r.top - 3) + 'px';
      caixaAlvo.style.width = (r.width + 6) + 'px'; caixaAlvo.style.height = (r.height + 6) + 'px';
    }
    function esconderAlvo() { if (caixaAlvo) caixaAlvo.style.display = 'none'; }

    /* ---------- chip ---------- */
    function montarChip() {
      if (o.chip === false) return;
      chipBtn = doc.createElement('button'); chipBtn.type = 'button'; chipBtn.className = 'cf-chip-btn cf-ui';
      chipBtn.setAttribute('aria-haspopup', 'menu');
      chipBtn.addEventListener('click', function () {
        var r = chipBtn.getBoundingClientRect(); abrirMenu(r.left + r.width / 2, r.top - o.raio - 20);
      });
      if (o.chip && o.chip.nodeType === 1) { o.chip.appendChild(chipBtn); }
      else { chip = doc.createElement('div'); chip.className = 'cf-chip cf-ui'; chip.appendChild(chipBtn); doc.body.appendChild(chip); }
      atualizarChip();
    }
    function atualizarChip() {
      if (!chipBtn) return;
      var nn = notas.length;
      chipBtn.classList.toggle('ativo', atual !== FERR[0]);
      chipBtn.innerHTML = svg(atual.icone) + '<span>' + atual.nome + (nn ? ' · ' + nn + ' nota' + (nn > 1 ? 's' : '') : '') + '</span><small>segure ' + (o.segurarMs / 1000).toLocaleString('pt-BR') + ' s</small>';
      chipBtn.setAttribute('aria-label', 'Ferramenta atual: ' + atual.nome + '. Abrir menu de ferramentas');
    }
    function toast(t) {
      if (!toastEl) { toastEl = doc.createElement('div'); toastEl.className = 'cf-toast cf-ui'; toastEl.setAttribute('role', 'status'); doc.body.appendChild(toastEl); }
      toastEl.textContent = t; toastEl.hidden = false; clearTimeout(toastT);
      toastT = setTimeout(function () { toastEl.hidden = true; }, 2600);
    }

    /* ---------- comentar ---------- */
    if (global.claude && typeof global.claude.use === 'function') {
      global.claude.use('comments').then(function (c) { shell = c; }, function () { shell = null; });
    }
    function comentar(ctx) {
      esconderAlvo();
      if (o.modo !== 'local' && shell && typeof shell.openComposer === 'function') {
        shell.openComposer({ element: ctx.alvo }).then(function (r) {
          if (r && r.opened) { toast('Comentário aberto no painel do claude.ai.'); evento('comentario', { onde: 'claude', rotulo: rotuloDe(ctx.alvo) }); }
          else if (o.modo === 'auto') comentarLocal(ctx);
        }, function () { if (o.modo === 'auto') comentarLocal(ctx); });
        return;
      }
      comentarLocal(ctx);
    }
    function caminho(el) {
      var partes = [], n = el;
      while (n && n.nodeType === 1 && n !== doc.body) {
        if (n.id && !ehUI(n)) { partes.unshift('#' + global.CSS.escape(n.id)); return { base: partes.shift(), idx: idxs(n, el) }; }
        n = n.parentElement;
      }
      return { base: 'body', idx: idxs(doc.body, el) };
    }
    function idxs(base, el) {
      var out = [], n = el;
      while (n && n !== base) { var p = n.parentElement; if (!p) break; out.unshift(Array.prototype.indexOf.call(p.children, n)); n = p; }
      return out;
    }
    function resolver(anc) {
      try {
        var el = anc.base === 'body' ? doc.body : doc.querySelector(anc.base);
        for (var i = 0; el && i < anc.idx.length; i++) el = el.children[anc.idx[i]];
        return el || null;
      } catch (e) { return null; }
    }
    function textoDe(n) {
      var partes = [];
      (function anda(x) {
        for (var f = x.firstChild; f; f = f.nextSibling) {
          if (f.nodeType === 3) partes.push(f.nodeValue);
          else if (f.nodeType === 1 && !(f.matches && f.matches('[data-cf-sem-rotulo],.cf-ui,[aria-hidden="true"],script,style'))) anda(f);
        }
      })(n);
      return partes.join(' ');
    }
    function limpa(s) { return String(s || '').replace(/\s+/g, ' ').trim().slice(0, 90); }
    function rotuloDe(el) {
      var n = el;
      for (var i = 0; n && n !== doc.body && i < 8; i++, n = n.parentElement) {
        if (n.matches && n.matches('legend,h1,h2,h3,h4,figcaption,label,button,a')) return limpa(textoDe(n));
        var h = n.querySelector && n.querySelector(':scope > legend, :scope > h1, :scope > h2, :scope > h3, :scope > h4, :scope > figcaption');
        if (h) return limpa(textoDe(h));
        if (i > 0 && n.getAttribute && n.getAttribute('aria-label')) return limpa(n.getAttribute('aria-label'));
      }
      return limpa(textoDe(el) || (el.getAttribute && el.getAttribute('alt')) || el.tagName);
    }
    function comentarLocal(ctx) {
      var r = ctx.alvo.getBoundingClientRect();
      var nota = {
        id: 'n' + Date.now().toString(36), texto: '', criado_em: new Date().toISOString(),
        onde: rotuloDe(ctx.alvo), ancora: caminho(ctx.alvo),
        ox: r.width ? (ctx.x - r.left) / r.width : 0, oy: r.height ? (ctx.y - r.top) / r.height : 0,
        px: ctx.x + global.scrollX, py: ctx.y + global.scrollY
      };
      notas.push(nota); desenharPinos(); abrirEditor(nota, true);
    }
    function camadaPinos() {
      if (!pinos) { pinos = doc.createElement('div'); pinos.className = 'cf-pinos cf-ui'; doc.body.appendChild(pinos); }
      return pinos;
    }
    function posicao(nota) {
      var cam = camadaPinos().getBoundingClientRect(), el = resolver(nota.ancora);
      if (el && el.getBoundingClientRect) {
        var r = el.getBoundingClientRect();
        if (r.width || r.height) return { x: r.left + nota.ox * r.width - cam.left, y: r.top + nota.oy * r.height - cam.top };
      }
      return { x: nota.px - global.scrollX - cam.left, y: nota.py - global.scrollY - cam.top };
    }
    function desenharPinos() {
      // só os pinos: o editor aberto mora na mesma camada e não pode sumir quando a página muda de tamanho
      var cam = camadaPinos(), velhos = cam.querySelectorAll('.cf-pino,.cf-polegar'), antes = editor && editor.el.parentNode === cam ? editor.el : null;
      for (var j = 0; j < velhos.length; j++) cam.removeChild(velhos[j]);
      notas.forEach(function (nota, i) {
        var p = posicao(nota), b = doc.createElement('button');
        b.type = 'button'; b.className = 'cf-pino'; b.textContent = String(i + 1);
        b.style.left = p.x + 'px'; b.style.top = p.y + 'px';
        b.setAttribute('aria-label', 'Nota ' + (i + 1) + (nota.texto ? ': ' + nota.texto.slice(0, 60) : ''));
        b.addEventListener('click', function (ev) { ev.stopPropagation(); abrirEditor(nota, false); });
        cam.insertBefore(b, antes);
      });
      var cr = cam.getBoundingClientRect();
      aprovs.forEach(function (a) {
        var el = elementoDe(a.chave), r = el && el.getBoundingClientRect ? el.getBoundingClientRect() : null;
        if (!r || !(r.width || r.height) || !validoAprov(a,el)) return; // âncora ausente ou obsoleta: continua salva, só não aparece
        var b = doc.createElement('button'); b.type = 'button'; b.className = 'cf-polegar'; b.innerHTML = svg(ICONES.polegar);
        b.setAttribute('data-cf-chave', a.chave);
        b.style.left = (Math.min(r.right - 4, global.innerWidth - 18) - cr.left) + 'px'; b.style.top = (r.top + 4 - cr.top) + 'px';
        b.setAttribute('aria-label', 'Aprovado: ' + a.onde);
        b.addEventListener('click', function (ev) {
          ev.stopPropagation();
          if (atual.ancora) { desconfirmar(a.chave, 'usuario'); toast('Aprovação removida.'); } else toast('Aprovado: ' + a.onde);
        });
        cam.insertBefore(b, antes);
      });
      if (editor && editor.nota) posicionarEditor(editor.nota);
      atualizarChip();
    }
    function abrirEditor(nota, nova) {
      fecharEditor(true);
      var comMic = o.microfone !== false;
      var ed = doc.createElement('div'); ed.className = 'cf-editor cf-ui'; ed.setAttribute('role', 'dialog');
      var idx = notas.indexOf(nota) + 1, idAviso = 'cf-aviso-' + nota.id;
      ed.setAttribute('aria-label', 'Nota ' + idx);
      ed.innerHTML = '<div class="cf-ed-onde">Nota ' + idx + ' · perto de: <span></span></div>' +
        '<textarea aria-label="Texto da nota" placeholder="' + (comMic ? 'Escreva ou dite o comentário…' : 'Escreva o comentário…') + '"></textarea>' +
        (comMic ? '<div class="cf-provisorio" aria-hidden="true"></div><div class="cf-mic-aviso" role="status" id="' + idAviso + '"></div>' : '') +
        '<div class="cf-ed-acoes"><button type="button" class="cf-excluir" aria-label="Excluir nota">Excluir</button>' +
        (comMic ? '<button type="button" class="cf-mic" aria-pressed="false" aria-label="Ditar com o microfone" aria-describedby="' + idAviso + '" title="Ditar com o microfone (Ctrl+Espaço)">' + svg(ICONES.microfone) + '</button>' : '') +
        '<button type="button" class="cf-salvar" aria-label="Salvar nota" title="Salvar (Ctrl+Enter)">Salvar · Ctrl+Enter</button></div>';
      ed.querySelector('.cf-ed-onde span').textContent = nota.onde || '—';
      var ta = ed.querySelector('textarea'); ta.value = nota.rascunho != null ? nota.rascunho : (nota.texto || '');
      // Persist before any voice handoff or renderer failure. Draft is not approval/send.
      ta.addEventListener('input', function () { nota.rascunho = ta.value; guardar(); });
      var mic = ed.querySelector('.cf-mic');
      if (mic && vozNativa()) {
        mic.setAttribute('aria-label', 'Abrir ditado do Windows');
        mic.title = 'Abrir ditado do Windows (Ctrl+Espaço)';
      }
      ed.querySelector('.cf-salvar').addEventListener('click', function () {
        soltarMic(true); // o que estava em cinza entra antes de salvar
        nota.texto = ta.value.trim(); delete nota.rascunho; if (!nota.texto) remover(nota); else { guardar(); if (typeof o.aoSalvarNota === 'function') o.aoSalvarNota(JSON.parse(JSON.stringify(nota))); toast('Nota ' + idx + ' salva.'); } ta.value=nota.texto; fecharEditor(true); desenharPinos();
      });
      ed.querySelector('.cf-excluir').addEventListener('click', function () { if ((ta.value.trim() || nota.texto || nota.rascunho) && !global.confirm('Excluir esta nota e seu rascunho local?')) return; ta.value=''; delete nota.rascunho; remover(nota); editor.nova=false; fecharEditor(true); desenharPinos(); toast('Nota excluída.'); });
      ta.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey)) ed.querySelector('.cf-salvar').click(); });
      if (mic) {
        mic.addEventListener('mousedown', function (ev) { ev.preventDefault(); }); // clique de mouse não tira o foco do texto
        mic.addEventListener('click', alternarMic);
      }
      camadaPinos().appendChild(ed);
      editor = { el: ed, nota: nota, nova: nova, ta: ta, mic: mic,
        prov: ed.querySelector('.cf-provisorio'), aviso: ed.querySelector('.cf-mic-aviso') };
      posicionarEditor(nota);
      setTimeout(function () { ta.focus({ preventScroll: true }); }, 0);
      if (mic && nova && ditar) {
        if (vozNativa()) estadoMic(editor, 'parado', 'Clique no áudio para abrir o ditado do Windows. A barra do Windows controla ouvir e parar.');
        else ligarMic();
      }
    }
    function posicionarEditor(nota) {
      if (!editor) return;
      var p = posicao(nota), cam = camadaPinos().getBoundingClientRect();
      var maxX = global.innerWidth - cam.left - 276 + 0, x = Math.max(16 - cam.left, Math.min(p.x + 14, maxX));
      editor.el.style.left = x + 'px'; editor.el.style.top = (p.y + 8) + 'px';
    }
    function fecharEditor(silencioso) {
      if (!editor) return;
      if (vozNativa() && typeof global.megabrainCancelDictation === 'function') global.megabrainCancelDictation();
      soltarMic();
      var e = editor; editor = null;
      micHotkey = null;
      if (e.ta.value.trim() !== (e.nota.texto || '')) { e.nota.rascunho=e.ta.value; guardar(); toast('Rascunho preservado neste aparelho. Abra a nota e use Salvar · Ctrl+Enter para enviar.'); }
      if (e.nova && !e.nota.texto && !e.nota.rascunho) remover(e.nota);
      if (e.el.parentNode) e.el.parentNode.removeChild(e.el);
      if (!silencioso) desenharPinos();
    }
    function remover(nota) { var i = notas.indexOf(nota); if (i >= 0) notas.splice(i, 1); guardar(); }
    function carregar() { try { var v = JSON.parse(global.localStorage.getItem(o.chave) || '[]'); return Array.isArray(v) ? v : []; } catch (e) { return []; } }
    function guardar() {
      try { global.localStorage.setItem(o.chave, JSON.stringify(notas)); } catch (e) {}
      if (typeof o.aoMudarNotas === 'function') try { o.aoMudarNotas(notas.slice()); } catch (e) {}
      evento('notas', { total: notas.length });
    }

    /* ---------- ditado por voz (nota local) ---------- */
    // estados: parado · ouvindo (pulso) · erro. Só texto final vai para a nota; o provisório fica em cinza.
    function vozNativa() { return global.__MEGABRAIN_NATIVE_VOICE__ === true || /QtWebEngine\//.test(global.navigator && global.navigator.userAgent || ''); }
    function Reconhecedor() { return vozNativa() ? null : (global.SpeechRecognition || global.webkitSpeechRecognition || null); }
    function estadoMic(ed, estado, msg, erro) {
      if (!ed || !ed.mic) return;
      ed.mic.setAttribute('aria-pressed', String(estado === 'ouvindo'));
      ed.mic.classList.toggle('erro', estado === 'erro');
      ed.mic.innerHTML = svg(estado === 'erro' ? ICONES.semMicrofone : ICONES.microfone);
      ed.aviso.textContent = msg || '';
      if (estado !== 'ouvindo') ed.prov.textContent = '';
      evento('microfone', { estado: estado, mensagem: msg || '', erro: erro || '' });
    }
    function inserirNoTexto(ta, txt) {
      txt = String(txt || '').replace(/\s+/g, ' ').trim();
      if (!txt) return;
      var v = ta.value, ini = ta.selectionStart, fim = ta.selectionEnd;
      if (typeof ini !== 'number' || typeof fim !== 'number') ini = fim = v.length;
      var antes = v.slice(0, ini), depois = v.slice(fim);
      if (antes && !/\s$/.test(antes)) txt = ' ' + txt;
      if (depois && !/^[\s.,;:!?)]/.test(depois)) txt += ' ';
      ta.setRangeText(txt, ini, fim, 'end');
      ta.dispatchEvent(new Event('input', { bubbles: true }));
    }
    function ligarMic() {
      var ed = editor; if (!ed || !ed.mic) return;
      if (voz) soltarMic();
      if (vozNativa()) {
        ed.nota.rascunho = ed.ta.value; guardar();
        ed.ta.focus({ preventScroll: true });
        var handoff = global.megabrainNativeDictation;
        if (typeof handoff !== 'function') {
          estadoMic(ed, 'erro', 'Ponte de áudio indisponível. No campo da nota, use Win + H. O ditado depende do serviço online e das permissões do Windows.', 'ponte-indisponivel');
          return;
        }
        if (ed.ditadoPendente) return;
        ed.ditadoPendente = true;
        estadoMic(ed, 'parado', 'Abrindo o ditado do Windows…');
        try {
          Promise.resolve(handoff()).then(function (result) {
            ed.ditadoPendente = false;
            if (editor !== ed) return;
            estadoMic(ed, 'parado', result && result.state === 'awaiting-native-confirmation'
              ? 'Confirme em Abrir ditado do Windows, no painel do aplicativo. Ele usa o serviço online da Microsoft; a barra do Windows controla ouvir/parar. Salvar envia só o texto.'
              : 'Ditado do Windows solicitado. Use o microfone da barra do Windows para ouvir/parar. Depende do serviço online e das permissões do Windows; Salvar envia só o texto.');
          }, function (err) {
            ed.ditadoPendente = false;
            if (editor === ed) estadoMic(ed, 'erro', (err && err.message || MSG_SEM_MIC), 'ditado-windows');
          });
        } catch (err) {
          ed.ditadoPendente = false;
          estadoMic(ed, 'erro', (err && err.message || MSG_SEM_MIC), 'ditado-windows');
        }
        return;
      }
      var C = Reconhecedor(), rec = null;
      if (C) try { rec = new C(); rec.lang = o.idiomaVoz || 'pt-BR'; rec.continuous = true; rec.interimResults = true; } catch (er) { rec = null; }
      if (!rec) { estadoMic(ed, 'erro', MSG_MIC['sem-suporte'], 'sem-suporte'); ed.ta.focus({ preventScroll: true }); return; }
      var v = voz = { rec: rec, ed: ed, prov: '', parando: false };
      rec.onresult = function (ev) {
        if (voz !== v) return;
        var prov = '';
        for (var i = ev.resultIndex; i < ev.results.length; i++) {
          var r = ev.results[i], t = r && r[0] ? r[0].transcript : '';
          if (r.isFinal) inserirNoTexto(ed.ta, t); else prov += t;
        }
        v.prov = prov.replace(/\s+/g, ' ').trim();
        ed.prov.textContent = v.parando ? '' : v.prov;
      };
      rec.onerror = function (ev) {
        if (voz !== v) return;
        var c = ev && ev.error;
        if (c === 'aborted') return;
        voz = null; rec.onresult = rec.onerror = rec.onend = null;
        try { rec.abort(); } catch (er) {}
        if (c === 'no-speech') estadoMic(ed, 'parado', 'Não ouvi nada.', c);
        else estadoMic(ed, 'erro', MSG_MIC[c] || MSG_SEM_MIC, c || 'desconhecido');
      };
      rec.onend = function () {
        if (voz !== v) return;
        voz = null;
        if (v.prov) inserirNoTexto(ed.ta, v.prov); // sobrou provisório sem virar final: não perde o que foi falado
        if (!v.parando) estadoMic(ed, 'parado', ''); // o navegador encerrou sozinho (silêncio longo, limite de tempo)
      };
      try { rec.start(); } catch (er) { voz = null; estadoMic(ed, 'erro', MSG_SEM_MIC, 'start'); return; }
      estadoMic(ed, 'ouvindo', 'Ouvindo…');
    }
    function desligarMic() { // pedido do usuário: para de ouvir e espera o último resultado final
      var v = voz; if (!v || v.parando) return;
      v.parando = true;
      estadoMic(v.ed, 'parado', '');
      try { v.rec.stop(); } catch (er) { soltarMic(true); }
    }
    function soltarMic(aproveitar) { // salvar/fechar/excluir: corta na hora
      var v = voz; if (!v) return;
      voz = null;
      v.rec.onresult = v.rec.onerror = v.rec.onend = null;
      try { v.rec.abort(); } catch (er) {}
      if (aproveitar && v.prov) inserirNoTexto(v.ed.ta, v.prov);
      estadoMic(v.ed, 'parado', '');
    }
    function alternarMic() { if (!editor || !editor.mic) return; if (voz && !voz.parando) desligarMic(); else ligarMic(); }
    function alternarDitado(v) {
      ditar = v == null ? !ditar : !!v;
      prefs.ditarAoComentar = ditar; gravar(o.chavePrefs, prefs);
      var tem = vozNativa() || !!Reconhecedor();
      toast(!ditar ? 'Ditado ao comentar: desligado.' : vozNativa() ? 'No aplicativo, clique no áudio de cada nota para abrir o ditado do Windows.' : tem ? 'Ditado ao comentar: ligado. O microfone abre em cada nota nova.'
        : 'Ditado ao comentar: ligado, mas este navegador não tem ditado por voz. No Windows, use Win + H.');
      evento('ditado', { ligado: ditar, suporte: tem });
      return ditar;
    }

    /* ---------- desenhar ---------- */
    // traço salvo: { id, modo: 'pincel'|'marcador', cor, esp, pts: [x0, y0, x1, y1, …] } em px do documento
    function lerTracos() {
      var v = ler(o.chaveDesenhos, null);
      return (v && Array.isArray(v.tracos) ? v.tracos : []).filter(function (t) { return t && Array.isArray(t.pts) && t.pts.length >= 2; });
    }
    function guardarTracos() {
      gravar(o.chaveDesenhos, { v: 1, tracos: tracos });
      atualizarBarra();
      if (typeof o.aoMudarDesenhos === 'function') try { o.aoMudarDesenhos(JSON.parse(JSON.stringify(tracos))); } catch (e) {}
      evento('desenhos', { total: tracos.length });
    }
    function salvarPincel() { prefs.pincel = { modo: pincel.modo, cor: pincel.cor, espessura: pincel.espessura }; gravar(o.chavePrefs, prefs); }
    function camadaDesenho() {
      if (!camadaD) { camadaD = doc.createElementNS(NS, 'svg'); camadaD.setAttribute('class', 'cf-desenho cf-ui'); camadaD.setAttribute('aria-hidden', 'true'); doc.body.appendChild(camadaD); }
      return camadaD;
    }
    function ptDe(e) { var r = camadaDesenho().getBoundingClientRect(); return [Math.round((e.clientX - r.left) * 10) / 10, Math.round((e.clientY - r.top) * 10) / 10]; }
    function largura(t) { return t.modo === 'marcador' ? t.esp * 3 : t.esp; }
    function caminhoD(pts) {
      var d = 'M' + pts[0] + ' ' + pts[1];
      for (var i = 2; i < pts.length; i += 2) d += 'L' + pts[i] + ' ' + pts[i + 1];
      return pts.length === 2 ? d + 'L' + pts[0] + ' ' + pts[1] : d; // ponto solto vira bolinha
    }
    function pathDe(t) {
      var p = doc.createElementNS(NS, 'path');
      p.setAttribute('d', caminhoD(t.pts)); p.setAttribute('stroke', t.cor); p.setAttribute('stroke-width', largura(t));
      if (t.modo === 'marcador') p.setAttribute('stroke-opacity', '0.4');
      p.setAttribute('data-cf-traco', t.id);
      return p;
    }
    function desenharTracos() {
      var cam = camadaDesenho(); while (cam.firstChild) cam.removeChild(cam.firstChild);
      tracos.forEach(function (t) { cam.appendChild(pathDe(t)); });
      if (traco && traco.el) cam.appendChild(traco.el);
    }
    function comecarTraco(e) {
      var p = ptDe(e);
      if (pincel.modo === 'borracha') { traco = { id: e.pointerId, borracha: true, apagados: [] }; apagarEm(p); return; }
      var t = { id: 'd' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5), modo: pincel.modo, cor: pincel.cor, esp: +pincel.espessura || 4, pts: p };
      traco = { id: e.pointerId, t: t, el: pathDe(t) }; camadaDesenho().appendChild(traco.el);
    }
    function estenderTraco(e) {
      var p = ptDe(e);
      if (traco.borracha) { apagarEm(p); return; }
      var pts = traco.t.pts, n = pts.length;
      if (Math.hypot(p[0] - pts[n - 2], p[1] - pts[n - 1]) < 1.5) return;
      pts.push(p[0], p[1]); traco.el.setAttribute('d', caminhoD(pts));
    }
    function terminarTraco() {
      var tr = traco; traco = null; if (!tr) return;
      if (tr.borracha) { if (tr.apagados.length) { historico.push({ tipo: 'apagar', itens: tr.apagados }); guardarTracos(); } return; }
      tracos.push(tr.t); historico.push({ tipo: 'traco', t: tr.t }); guardarTracos();
    }
    function descartarTraco() {
      var tr = traco; traco = null; if (!tr) return;
      if (tr.borracha) desfazerOp({ tipo: 'apagar', itens: tr.apagados });
      else if (tr.el.parentNode) tr.el.parentNode.removeChild(tr.el);
    }
    function distSeg(px, py, ax, ay, bx, by) {
      var dx = bx - ax, dy = by - ay, l = dx * dx + dy * dy, k = l ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l)) : 0;
      return Math.hypot(px - ax - k * dx, py - ay - k * dy);
    }
    function toca(t, x, y, raio) {
      var pts = t.pts, lim = raio + largura(t) / 2;
      if (pts.length === 2) return Math.hypot(x - pts[0], y - pts[1]) <= lim;
      for (var i = 2; i < pts.length; i += 2) if (distSeg(x, y, pts[i - 2], pts[i - 1], pts[i], pts[i + 1]) <= lim) return true;
      return false;
    }
    function apagarEm(p) { // borracha apaga traços inteiros; cada remoção guarda o índice para o desfazer
      var raio = Math.max(6, pincel.espessura * 1.5), mudou = false;
      for (var i = tracos.length - 1; i >= 0; i--) {
        if (toca(tracos[i], p[0], p[1], raio)) { traco.apagados.push({ t: tracos[i], i: i }); tracos.splice(i, 1); mudou = true; }
      }
      if (mudou) desenharTracos();
    }
    function desfazerOp(op) {
      if (op.tipo === 'traco') { var i = tracos.indexOf(op.t); if (i >= 0) tracos.splice(i, 1); }
      else if (op.tipo === 'apagar') for (var j = op.itens.length - 1; j >= 0; j--) tracos.splice(Math.min(op.itens[j].i, tracos.length), 0, op.itens[j].t);
      else if (op.tipo === 'limpar') tracos = op.itens.concat(tracos);
      desenharTracos();
    }
    function desfazer() {
      var op = historico.pop();
      if (!op) { toast('Nada para desfazer.'); return false; }
      desfazerOp(op); guardarTracos(); return true;
    }
    function limparDesenhos() { // só por ação explícita; o desfazer traz de volta
      if (!tracos.length) return false;
      historico.push({ tipo: 'limpar', itens: tracos }); tracos = [];
      desenharTracos(); guardarTracos(); toast('Desenhos apagados. Desfazer traz de volta.');
      return true;
    }
    function mostrarBarra(sim) {
      if (!sim) { if (barra) barra.hidden = true; return; }
      if (!barra) montarBarra();
      barra.hidden = false; atualizarBarra();
    }
    function montarBarra() {
      barra = doc.createElement('div'); barra.className = 'cf-barra cf-ui'; barra.setAttribute('role', 'toolbar'); barra.setAttribute('aria-label', 'Desenho');
      barra.innerHTML = '<div class="cf-grupo" role="radiogroup" aria-label="Traço">' +
        [['pincel', 'Pincel'], ['marcador', 'Marcador'], ['borracha', 'Borracha']].map(function (m) {
          return '<button type="button" role="radio" data-modo="' + m[0] + '">' + m[1] + '</button>';
        }).join('') + '</div><div class="cf-grupo" role="radiogroup" aria-label="Cor">' +
        o.cores.map(function (c) { return '<button type="button" role="radio" class="cf-cor" data-cor="' + c + '" aria-label="Cor ' + c + '" style="background:' + c + '"></button>'; }).join('') +
        '</div><label>Espessura <input type="range" min="1" max="24" step="1"></label>' +
        '<button type="button" data-acao="desfazer">Desfazer</button><button type="button" data-acao="limpar">Limpar</button><button type="button" data-acao="pronto">Pronto</button>';
      barra.addEventListener('click', function (ev) {
        var b = ev.target.closest && ev.target.closest('button'); if (!b) return;
        var d = b.dataset;
        if (d.modo) pincel.modo = d.modo;
        else if (d.cor) { pincel.cor = d.cor; if (pincel.modo === 'borracha') pincel.modo = 'pincel'; }
        else if (d.acao === 'desfazer') desfazer();
        else if (d.acao === 'limpar') limparDesenhos();
        else if (d.acao === 'pronto') { usar(FERR[0].id); return; }
        salvarPincel(); atualizarBarra();
      });
      var rng = barra.querySelector('input');
      rng.addEventListener('input', function () { pincel.espessura = +rng.value; salvarPincel(); });
      doc.body.appendChild(barra);
    }
    function atualizarBarra() {
      if (!barra) return;
      Array.prototype.forEach.call(barra.querySelectorAll('[data-modo]'), function (b) { b.setAttribute('aria-checked', String(b.dataset.modo === pincel.modo)); });
      Array.prototype.forEach.call(barra.querySelectorAll('[data-cor]'), function (b) { b.setAttribute('aria-checked', String(b.dataset.cor === pincel.cor)); });
      barra.querySelector('input').value = pincel.espessura;
      barra.querySelector('[data-acao="desfazer"]').disabled = !historico.length;
      barra.querySelector('[data-acao="limpar"]').disabled = !tracos.length;
    }

    /* ---------- aprovar (polegar) por âncora ---------- */
    // chave: valor de [data-cf-ancora] (âncora opcional e estável) ou o caminho do elemento ("#id>0>2", "body>1")
    function chaveDe(a) {
      if (a && a.nodeType === 1) {
        var m = a.closest('[data-cf-ancora]'); if (m) return m.getAttribute('data-cf-ancora');
        var c = caminho(a); return [c.base].concat(c.idx).join('>');
      }
      return a == null ? '' : String(a);
    }
    function elementoDe(chave) {
      var el = null;
      try { el = doc.querySelector('[data-cf-ancora="' + String(chave).replace(/["\\]/g, '\\$&') + '"]'); } catch (e) {}
      if (!el && /^(body|#[^>]+)(>\d+)*$/.test(chave)) { var p = chave.split('>'); el = resolver({ base: p[0], idx: p.slice(1).map(Number) }); }
      return el;
    }
    function fingerprint(el) { var value=el.tagName+'|'+textoDe(el).replace(/\s+/g,' ').trim()+'|'+Array.prototype.map.call(el.querySelectorAll('img'),function(i){return i.getAttribute('src')||''}).join('|'), hash=2166136261; for(var i=0;i<value.length;i++){hash^=value.charCodeAt(i);hash=Math.imul(hash,16777619)} return (hash>>>0).toString(16); }
    function validoAprov(reg,el) { if(!el)return !!reg.semElemento; return !!reg.fingerprint && reg.onde===rotuloDe(el) && reg.fingerprint===fingerprint(el); }
    function idxAprov(chave) { for (var i = 0; i < aprovs.length; i++) if (aprovs[i].chave === chave) return i; return -1; }
    function mudouAprov(reg, aprovado, origem, quieto) {
      gravar(o.chaveAprovacoes, aprovs); desenharPinos();
      var m = { chave: reg.chave, aprovado: aprovado, origem: origem, onde: reg.onde };
      if (!quieto && typeof o.aoAprovar === 'function') try { o.aoAprovar(m, JSON.parse(JSON.stringify(aprovs))); } catch (e) {}
      evento('aprovacao', m);
    }
    function confirmar(a, extra, quieto) {
      var chave = chaveDe(a); if (!chave) return false;
      var existing=idxAprov(chave); if(existing>=0 && validoAprov(aprovs[existing],elementoDe(chave)))return false; if(existing>=0)aprovs.splice(existing,1); // obsoleta só é renovada por ação explícita
      var el = a && a.nodeType === 1 ? (a.closest('[data-cf-ancora]') || a) : elementoDe(chave);
      var reg = { chave: chave, onde: el ? rotuloDe(el) : chave, em: new Date().toISOString(), origem: (extra && extra.origem) || 'api' };
      reg.fingerprint=el?fingerprint(el):null; reg.semElemento=!el;
      if (extra && extra.dados !== undefined) reg.dados = extra.dados;
      aprovs.push(reg); mudouAprov(reg, true, reg.origem, quieto);
      return true;
    }
    function desconfirmar(a, origem) {
      var i = idxAprov(chaveDe(a)); if (i < 0) return false;
      mudouAprov(aprovs.splice(i, 1)[0], false, origem || 'api');
      return true;
    }
    function aprovarClique(ctx) {
      esconderAlvo();
      var chave = chaveDe(ctx.alvo);
      if (api.confirmado(chave)) { desconfirmar(chave, 'usuario'); toast('Aprovação removida.'); }
      else { confirmar(ctx.alvo, { origem: 'usuario' }); toast('Aprovado: ' + aprovs[aprovs.length - 1].onde); }
    }

    /* ---------- ligar ---------- */
    var ro = null;
    function redesenhar() { if (notas.length || aprovs.length) desenharPinos(); }
    global.addEventListener('pointerdown', aoBaixar, true);
    global.addEventListener('pointermove', aoMover, true);
    global.addEventListener('pointerup', aoSoltar, true);
    global.addEventListener('pointercancel', aoSoltar, true);
    global.addEventListener('click', aoClicar, true);
    global.addEventListener('mousedown', aoMousedown, true);
    global.addEventListener('contextmenu', aoContexto, true);
    global.addEventListener('dragstart', aoArrastar, true);
    doc.addEventListener('selectstart', aoSelecionar, true);
    global.addEventListener('keydown', aoTecla, true);
    global.addEventListener('keyup', aoSoltarTecla, true);
    global.addEventListener('scroll', aoRolar, true);
    global.addEventListener('resize', desenharPinos);
    if (global.ResizeObserver) { ro = new ResizeObserver(redesenhar); ro.observe(doc.body); }
    montarChip();
    (o.confirmados || []).forEach(function (a) { confirmar(a, { origem: 'inicial' }, true); }); // escolhas já aplicadas
    if (notas.length || aprovs.length) desenharPinos();
    if (tracos.length) desenharTracos();

    var api = {
      usar: usar,
      atual: function () { return atual.id; },
      abrirMenu: function (x, y) { abrirMenu(x, y); },
      fecharMenu: function () { fecharMenu(); },
      notas: function () { return notas.map(function (n, i) { return { n: i + 1, texto: n.texto, onde: n.onde, criado_em: n.criado_em }; }); },
      limparNotas: function () { notas = []; guardar(); fecharEditor(true); desenharPinos(); },
      configurar: function (mudas) { for (var k in mudas) o[k] = mudas[k]; atualizarChip(); },
      ditarAoComentar: function (v) { if (v != null && !!v !== ditar) alternarDitado(!!v); return ditar; },
      desenhos: function () { return JSON.parse(JSON.stringify(tracos)); },
      pincel: function (m) {
        if (m) { for (var k in m) if (k in pincel) pincel[k] = m[k]; salvarPincel(); atualizarBarra(); }
        return { modo: pincel.modo, cor: pincel.cor, espessura: pincel.espessura };
      },
      desfazer: desfazer,
      limparDesenhos: limparDesenhos,
      confirmar: function (a, extra) { return confirmar(a, extra); },
      desconfirmar: function (a) { return desconfirmar(a, 'api'); },
      confirmado: function (a) { var key=chaveDe(a),i=idxAprov(key);return i>=0 && validoAprov(aprovs[i],elementoDe(key)); },
      aprovacoes: function () { return aprovs.map(function(a){var row=JSON.parse(JSON.stringify(a));row.obsoleta=!validoAprov(a,elementoDe(a.chave));return row}); },
      destruir: function () {
        if (destruida) return; destruida=true;
        clearTimeout(engolirT);
        if (instanciaAtiva===api) instanciaAtiva=null;
        cancelar(); traco = null; fecharMenu(); fecharEditor(true); soltarMic(); html.classList.remove('cf-segurando');
        global.removeEventListener('pointerdown', aoBaixar, true); global.removeEventListener('pointermove', aoMover, true);
        global.removeEventListener('pointerup', aoSoltar, true); global.removeEventListener('pointercancel', aoSoltar, true);
        global.removeEventListener('click', aoClicar, true); global.removeEventListener('mousedown', aoMousedown, true);
        global.removeEventListener('contextmenu', aoContexto, true); global.removeEventListener('dragstart', aoArrastar, true);
        doc.removeEventListener('selectstart', aoSelecionar, true);
        global.removeEventListener('keydown', aoTecla, true); global.removeEventListener('scroll', aoRolar, true);
        global.removeEventListener('keyup', aoSoltarTecla, true);
        global.removeEventListener('resize', desenharPinos); if (ro) ro.disconnect();
        [anel, chip, chipBtn, pinos, caixaAlvo, toastEl, camadaD, barra].forEach(function (x) { if (x && x.parentNode) x.parentNode.removeChild(x); });
        FERR.forEach(function (x) { if (x.cursorClasse) html.classList.remove(x.cursorClasse); });
      }
    };
    instanciaAtiva=api;
    if (aprovs.some(function(a){return !validoAprov(a,elementoDe(a.chave))}))toast('Há aprovação local obsoleta: o conteúdo mudou ou não pode ser confirmado.');
    return api;
  }

  global.CursorFerramentas = { iniciar: iniciar, versao: '1.4', icones: ICONES };
})(window);
