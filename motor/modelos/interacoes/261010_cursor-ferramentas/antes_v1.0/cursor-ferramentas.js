/* cursor-ferramentas v1.0 · 261010 · MEGABRAIN
   Fonte única: MEGA B R A I  N/motor/modelos/interacoes/261010_cursor-ferramentas/cursor-ferramentas.js
   Ideia do Usuário (261010): segurar o botão principal por 2 s, sem arrastar, abre um menu
   em leque em volta do ponteiro; ali o cursor vira uma ferramenta (ex.: comentar).
   Uso: CursorFerramentas.iniciar({ ...opções }) → controle { usar, atual, abrirMenu, fecharMenu,
   notas, limparNotas, configurar, destruir }. Sem dependências; injeta o próprio CSS. */
(function (global) {
  'use strict';
  if (global.CursorFerramentas) return;

  var ICONES = {
    interagir: '<path d="M5 3l13 7.5-6 1.6L9.4 18z"/>',
    comentar: '<path d="M4 5h16v11H9l-5 4V5z"/><path d="M12 8v5M9.5 10.5h5"/>',
    fechar: '<path d="M7 7l10 10M17 7 7 17"/>'
  };
  function svg(p) { return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' + p + '</svg>'; }
  var CURSOR_COMENTAR = 'url("data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">' +
    '<path d="M3 3h25v17H12l-9 8z" fill="#EC0F7C" stroke="#fff" stroke-width="2" stroke-linejoin="round"/>' +
    '<path d="M15.5 7.5v8M11.5 11.5h8" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/></svg>') +
    '") 3 28, crosshair';

  var CSS = [
    ':root{--cf-acento:#EC0F7C;--cf-fundo:#1C1C2B;--cf-tinta:#FFFFFF;--cf-borda:rgba(255,255,255,.16);--cf-sombra:0 14px 36px rgba(0,0,0,.42);--cf-foco:#1CB0F6;--cf-chip-bottom:16px;--cf-chip-left:16px}',
    'html.cf-segurando,html.cf-segurando *{user-select:none!important;-webkit-user-select:none!important;-webkit-touch-callout:none!important}',
    '.cf-anel{position:fixed;left:0;top:0;width:60px;height:60px;margin:-30px 0 0 -30px;pointer-events:none;z-index:2147483600;opacity:0;transition:opacity .15s}',
    '.cf-anel.on{opacity:1}',
    '.cf-anel circle{fill:none;stroke-width:4}',
    '.cf-anel .cf-trilho{stroke:rgba(128,128,128,.35)}',
    '.cf-anel .cf-prog{stroke:var(--cf-acento);stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%}',
    '.cf-menu{position:fixed;inset:0;z-index:2147483601}',
    '.cf-veu{position:absolute;inset:0;background:rgba(0,0,0,.08)}',
    '.cf-botao{position:absolute;width:54px;height:54px;margin:-27px 0 0 -27px;border-radius:50%;border:0;padding:0;background:var(--cf-fundo);color:var(--cf-tinta);box-shadow:var(--cf-sombra),0 0 0 1px var(--cf-borda);display:grid;place-items:center;cursor:pointer;opacity:0;transform:translate(0,0) scale(.25);transition:transform .24s cubic-bezier(.2,.9,.3,1.25),opacity .18s,background .15s;font:inherit}',
    '.cf-menu.aberto .cf-botao{opacity:1;transform:translate(var(--dx),var(--dy)) scale(1)}',
    '.cf-botao svg{width:23px;height:23px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}',
    '.cf-botao:hover{background:color-mix(in srgb,var(--cf-acento) 30%,var(--cf-fundo))}',
    '.cf-botao.ativo{background:var(--cf-acento);color:#fff}',
    '.cf-botao:focus-visible{outline:3px solid var(--cf-foco);outline-offset:3px}',
    '.cf-centro{width:40px;height:40px;margin:-20px 0 0 -20px}',
    '.cf-centro svg{width:18px;height:18px}',
    '.cf-rot{position:absolute;left:50%;transform:translateX(-50%);white-space:nowrap;font:600 12px/1 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--cf-fundo);color:var(--cf-tinta);padding:6px 8px;border-radius:7px;box-shadow:0 0 0 1px var(--cf-borda);pointer-events:none}',
    '.cf-rot.cima{bottom:calc(100% + 7px)}.cf-rot.baixo{top:calc(100% + 7px)}',
    '.cf-alvo{position:fixed;pointer-events:none;z-index:2147483590;border:2px dashed var(--cf-acento);border-radius:8px;background:color-mix(in srgb,var(--cf-acento) 7%,transparent);transition:all .08s}',
    'html.cf-ferr-comentar,html.cf-ferr-comentar *{cursor:' + CURSOR_COMENTAR + '!important}',
    'html.cf-ferr-comentar .cf-ui,html.cf-ferr-comentar .cf-ui *{cursor:pointer!important}',
    'html.cf-ferr-comentar .cf-editor textarea{cursor:text!important}',
    '.cf-chip{position:fixed;left:var(--cf-chip-left);bottom:calc(var(--cf-chip-bottom) + env(safe-area-inset-bottom,0px));z-index:2147483500}',
    '.cf-chip-btn{display:inline-flex;align-items:center;gap:8px;border:0;border-radius:999px;padding:9px 13px 9px 10px;background:var(--cf-fundo);color:var(--cf-tinta);box-shadow:var(--cf-sombra),0 0 0 1px var(--cf-borda);font:600 13px/1.1 system-ui,-apple-system,"Segoe UI",sans-serif;cursor:pointer}',
    '.cf-chip-btn svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}',
    '.cf-chip-btn small{font-weight:500;opacity:.72}',
    '.cf-chip-btn.ativo{background:var(--cf-acento);color:#fff}',
    '.cf-chip-btn:focus-visible{outline:3px solid var(--cf-foco);outline-offset:2px}',
    '.cf-pinos{position:absolute;left:0;top:0;width:0;height:0;z-index:2147483400}',
    '.cf-pino{position:absolute;width:28px;height:28px;margin:-28px 0 0 -2px;border:2px solid #fff;border-radius:14px 14px 14px 3px;background:var(--cf-acento);color:#fff;font:700 13px/24px system-ui,sans-serif;text-align:center;box-shadow:0 6px 16px rgba(0,0,0,.35);cursor:pointer;padding:0}',
    '.cf-pino:focus-visible{outline:3px solid var(--cf-foco);outline-offset:2px}',
    '.cf-editor{position:absolute;width:260px;max-width:calc(100vw - 32px);background:var(--cf-fundo);color:var(--cf-tinta);border-radius:12px;box-shadow:var(--cf-sombra),0 0 0 1px var(--cf-borda);padding:10px;display:grid;gap:8px;font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;z-index:2147483450}',
    '.cf-editor .cf-ed-onde{font-size:12px;opacity:.72;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
    '.cf-editor textarea{width:100%;box-sizing:border-box;min-height:74px;resize:vertical;border-radius:8px;border:1px solid var(--cf-borda);background:rgba(127,127,127,.12);color:inherit;font:inherit;padding:8px}',
    '.cf-editor textarea:focus{outline:2px solid var(--cf-foco);outline-offset:1px}',
    '.cf-ed-acoes{display:flex;gap:6px;justify-content:flex-end}',
    '.cf-ed-acoes button{border:0;border-radius:999px;padding:7px 12px;font:600 13px system-ui,sans-serif;cursor:pointer;background:rgba(127,127,127,.2);color:inherit}',
    '.cf-ed-acoes .cf-salvar{background:var(--cf-acento);color:#fff}',
    '.cf-ed-acoes button:focus-visible{outline:2px solid var(--cf-foco);outline-offset:2px}',
    '.cf-toast{position:fixed;left:50%;top:16px;transform:translateX(-50%);z-index:2147483602;background:var(--cf-fundo);color:var(--cf-tinta);box-shadow:var(--cf-sombra),0 0 0 1px var(--cf-borda);border-radius:999px;padding:9px 15px;font:600 13px/1.3 system-ui,sans-serif;max-width:calc(100vw - 32px);text-align:center}',
    '@media (prefers-reduced-motion:reduce){.cf-botao,.cf-anel,.cf-alvo{transition:none!important}}'
  ].join('\n');

  function iniciar(opcoes) {
    var o = {
      segurarMs: 2000,
      atrasoVisualMs: 250,
      tolerancia: 10,
      raio: 82,
      ignorar: 'input,textarea,select,[contenteditable=""],[contenteditable="true"],[data-cf-ignorar]',
      modo: 'auto',
      chip: true,
      chave: 'cf-notas:' + location.pathname,
      ferramentas: null,
      aoMudar: null,
      aoMudarNotas: null,
      aoEvento: null
    };
    for (var k in (opcoes || {})) o[k] = opcoes[k];

    var doc = document, html = doc.documentElement;
    if (!doc.getElementById('cf-estilo')) {
      var st = doc.createElement('style'); st.id = 'cf-estilo'; st.textContent = CSS; (doc.head || html).appendChild(st);
    }

    var FERR = o.ferramentas || [
      { id: 'interagir', nome: 'Interagir', icone: ICONES.interagir },
      { id: 'comentar', nome: 'Comentar', icone: ICONES.comentar, cursorClasse: 'cf-ferr-comentar', destacar: true, aoClicar: comentar }
    ];
    var atual = FERR[0];
    var segurando = null, engolir = false, menu = null, menuAbertoEm = 0, focoAntes = null;
    var caixaAlvo = null, chip = null, chipBtn = null, toastEl = null, toastT = 0;
    var shell = null, pinos = null, editor = null;
    var notas = carregar();

    function evento(tipo, dados) { if (typeof o.aoEvento === 'function') try { o.aoEvento(tipo, dados || {}); } catch (e) {} }
    function ehUI(el) { return !!(el && el.closest && el.closest('.cf-ui')); }

    /* ---------- segurar ---------- */
    var anel = doc.createElement('div'); anel.className = 'cf-anel cf-ui'; anel.setAttribute('aria-hidden', 'true');
    anel.innerHTML = '<svg viewBox="0 0 60 60"><circle class="cf-trilho" cx="30" cy="30" r="24"/><circle class="cf-prog" cx="30" cy="30" r="24" stroke-dasharray="150.8" stroke-dashoffset="150.8"/></svg>';
    doc.body.appendChild(anel);
    var prog = anel.querySelector('.cf-prog');

    function cancelar() {
      if (!segurando) return;
      clearTimeout(segurando.tv); clearTimeout(segurando.ta); segurando = null;
      html.classList.remove('cf-segurando'); anel.classList.remove('on');
      prog.style.transition = 'none'; prog.style.strokeDashoffset = '150.8';
    }
    function aoBaixar(e) {
      if (e.button !== 0 || e.isPrimary === false) return;
      engolir = false;
      if (menu || ehUI(e.target)) return;
      if (o.ignorar && e.target.closest && e.target.closest(o.ignorar)) return;
      cancelar();
      var s = segurando = { x: e.clientX, y: e.clientY, tipo: e.pointerType };
      s.tv = setTimeout(function () {
        if (segurando !== s) return;
        html.classList.add('cf-segurando');
        anel.style.left = s.x + 'px'; anel.style.top = s.y + 'px'; anel.classList.add('on');
        prog.style.transition = 'none'; prog.style.strokeDashoffset = '150.8';
        void prog.getBoundingClientRect();
        prog.style.transition = 'stroke-dashoffset ' + Math.max(0, o.segurarMs - o.atrasoVisualMs) + 'ms linear';
        prog.style.strokeDashoffset = '0';
      }, o.atrasoVisualMs);
      s.ta = setTimeout(function () {
        if (segurando !== s) return;
        cancelar(); engolir = true;
        try { var sel = global.getSelection && global.getSelection(); if (sel) sel.removeAllRanges(); } catch (er) {}
        abrirMenu(s.x, s.y);
        evento('segurou', { x: s.x, y: s.y });
      }, o.segurarMs);
    }
    function aoMover(e) {
      if (segurando && Math.hypot(e.clientX - segurando.x, e.clientY - segurando.y) > o.tolerancia) cancelar();
      if (!segurando && !menu && atual.destacar) destacar(e.clientX, e.clientY);
    }
    function aoSoltar() { cancelar(); if (engolir) setTimeout(function () { engolir = false; }, 700); }
    function aoClicar(e) {
      if (engolir && !ehUI(e.target)) { e.preventDefault(); e.stopPropagation(); engolir = false; return; }
      if (atual.aoClicar && !menu && !ehUI(e.target)) {
        e.preventDefault(); e.stopPropagation();
        var alvo = e.target;
        atual.aoClicar({ alvo: alvo, x: e.clientX, y: e.clientY, evento: e }, api);
      }
    }
    function aoMousedown(e) {
      if (atual.aoClicar && !menu && !ehUI(e.target) && e.button === 0) e.preventDefault();
    }
    function aoContexto(e) { if (segurando) e.preventDefault(); }
    function aoSelecionar(e) { if (segurando && html.classList.contains('cf-segurando')) e.preventDefault(); }
    function aoTecla(e) {
      if (e.key !== 'Escape') return;
      if (menu) { fecharMenu(); e.preventDefault(); return; }
      if (editor) { fecharEditor(); e.preventDefault(); return; }
      if (atual !== FERR[0]) { usar(FERR[0].id); e.preventDefault(); }
    }

    /* ---------- menu em leque ---------- */
    function abrirMenu(x, y) {
      if (menu) return;
      var n = FERR.length, R = o.raio;
      var w = global.innerWidth, h = global.innerHeight;
      var cx = Math.min(Math.max(x, R + 44), w - R - 44), cy = Math.min(Math.max(y, R + 54), h - R - 44);
      if (w < 2 * R + 88) cx = w / 2;
      focoAntes = doc.activeElement;
      menu = doc.createElement('div'); menu.className = 'cf-menu cf-ui'; menu.setAttribute('role', 'menu'); menu.setAttribute('aria-label', 'Ferramentas do cursor');
      var veu = doc.createElement('div'); veu.className = 'cf-veu'; menu.appendChild(veu);
      veu.addEventListener('pointerdown', function (ev) { ev.preventDefault(); fecharMenu(); });
      var passo = n <= 5 ? 62 : 360 / n;
      FERR.forEach(function (f, i) {
        var ang = (n <= 5 ? (-90 + (i - (n - 1) / 2) * passo) : (-90 + i * passo)) * Math.PI / 180;
        var dx = Math.round(Math.cos(ang) * R), dy = Math.round(Math.sin(ang) * R);
        var b = doc.createElement('button'); b.type = 'button'; b.className = 'cf-botao' + (f === atual ? ' ativo' : '');
        b.setAttribute('role', 'menuitemradio'); b.setAttribute('aria-checked', String(f === atual)); b.setAttribute('aria-label', f.nome);
        b.style.left = cx + 'px'; b.style.top = cy + 'px'; b.style.setProperty('--dx', dx + 'px'); b.style.setProperty('--dy', dy + 'px');
        b.style.transitionDelay = (i * 35) + 'ms';
        b.innerHTML = svg(f.icone) + '<span class="cf-rot ' + (dy < -10 ? 'cima' : 'baixo') + '">' + f.nome + '</span>';
        b.addEventListener('click', function () { if (Date.now() - menuAbertoEm < 250) return; usar(f.id); fecharMenu(true); });
        menu.appendChild(b);
      });
      var c = doc.createElement('button'); c.type = 'button'; c.className = 'cf-botao cf-centro'; c.setAttribute('aria-label', 'Fechar menu');
      c.style.left = cx + 'px'; c.style.top = cy + 'px'; c.style.setProperty('--dx', '0px'); c.style.setProperty('--dy', '0px');
      c.innerHTML = svg(ICONES.fechar);
      c.addEventListener('click', function () { if (Date.now() - menuAbertoEm < 250) return; fecharMenu(); });
      menu.appendChild(c);
      menu.addEventListener('keydown', function (ev) {
        var bs = Array.prototype.slice.call(menu.querySelectorAll('.cf-botao'));
        var i = bs.indexOf(doc.activeElement);
        if (ev.key === 'ArrowRight' || ev.key === 'ArrowDown' || (ev.key === 'Tab' && !ev.shiftKey)) { ev.preventDefault(); bs[(i + 1) % bs.length].focus(); }
        else if (ev.key === 'ArrowLeft' || ev.key === 'ArrowUp' || (ev.key === 'Tab' && ev.shiftKey)) { ev.preventDefault(); bs[(i - 1 + bs.length) % bs.length].focus(); }
      });
      doc.body.appendChild(menu);
      menuAbertoEm = Date.now();
      esconderAlvo();
      requestAnimationFrame(function () { requestAnimationFrame(function () {
        if (!menu) return; menu.classList.add('aberto');
        var at = menu.querySelector('.cf-botao.ativo') || menu.querySelector('.cf-botao'); if (at) at.focus({ preventScroll: true });
      }); });
      evento('menu', { aberto: true });
    }
    function fecharMenu(escolheu) {
      if (!menu) return;
      var m = menu; menu = null; m.classList.remove('aberto');
      setTimeout(function () { if (m.parentNode) m.parentNode.removeChild(m); }, 260);
      if (!escolheu && focoAntes && focoAntes.focus) try { focoAntes.focus({ preventScroll: true }); } catch (e) {}
      evento('menu', { aberto: false });
    }

    /* ---------- ferramenta atual ---------- */
    function usar(id) {
      var f = FERR.filter(function (x) { return x.id === id; })[0]; if (!f) return;
      FERR.forEach(function (x) { if (x.cursorClasse) html.classList.remove(x.cursorClasse); });
      atual = f; if (f.cursorClasse) html.classList.add(f.cursorClasse);
      if (!f.destacar) esconderAlvo();
      atualizarChip();
      toast(f.id === FERR[0].id ? 'Ferramenta: ' + f.nome + '. Cliques voltam ao normal.' : 'Ferramenta: ' + f.nome + '. Clique onde quiser. Esc volta ao normal.');
      if (typeof o.aoMudar === 'function') try { o.aoMudar(f.id, f); } catch (e) {}
      evento('ferramenta', { id: f.id });
    }
    function destacar(x, y) {
      var el = doc.elementFromPoint(x, y);
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
        if (n.id && !ehUI(n)) { partes.unshift('#' + n.id); return { base: partes.shift(), idx: idxs(n, el) }; }
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
      var cam = camadaPinos(); cam.innerHTML = '';
      notas.forEach(function (nota, i) {
        var p = posicao(nota), b = doc.createElement('button');
        b.type = 'button'; b.className = 'cf-pino'; b.textContent = String(i + 1);
        b.style.left = p.x + 'px'; b.style.top = p.y + 'px';
        b.setAttribute('aria-label', 'Nota ' + (i + 1) + (nota.texto ? ': ' + nota.texto.slice(0, 60) : ''));
        b.addEventListener('click', function (ev) { ev.stopPropagation(); abrirEditor(nota, false); });
        cam.appendChild(b);
      });
      if (editor && editor.nota) posicionarEditor(editor.nota);
      atualizarChip();
    }
    function abrirEditor(nota, nova) {
      fecharEditor(true);
      var ed = doc.createElement('div'); ed.className = 'cf-editor cf-ui'; ed.setAttribute('role', 'dialog'); ed.setAttribute('aria-label', 'Nota');
      var idx = notas.indexOf(nota) + 1;
      ed.innerHTML = '<div class="cf-ed-onde">Nota ' + idx + ' · perto de: <span></span></div><textarea aria-label="Texto da nota" placeholder="Escreva o comentário…"></textarea><div class="cf-ed-acoes"><button type="button" class="cf-excluir">Excluir</button><button type="button" class="cf-salvar">Salvar</button></div>';
      ed.querySelector('.cf-ed-onde span').textContent = nota.onde || '—';
      var ta = ed.querySelector('textarea'); ta.value = nota.texto || '';
      ed.querySelector('.cf-salvar').addEventListener('click', function () { nota.texto = ta.value.trim(); if (!nota.texto) remover(nota); else { guardar(); toast('Nota ' + idx + ' salva.'); } fecharEditor(true); desenharPinos(); });
      ed.querySelector('.cf-excluir').addEventListener('click', function () { remover(nota); fecharEditor(true); desenharPinos(); toast('Nota excluída.'); });
      ta.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey)) ed.querySelector('.cf-salvar').click(); });
      camadaPinos().appendChild(ed);
      editor = { el: ed, nota: nota, nova: nova };
      posicionarEditor(nota);
      setTimeout(function () { ta.focus({ preventScroll: true }); }, 0);
    }
    function posicionarEditor(nota) {
      if (!editor) return;
      var p = posicao(nota), cam = camadaPinos().getBoundingClientRect();
      var maxX = global.innerWidth - cam.left - 276 + 0, x = Math.max(16 - cam.left, Math.min(p.x + 14, maxX));
      editor.el.style.left = x + 'px'; editor.el.style.top = (p.y + 8) + 'px';
    }
    function fecharEditor(silencioso) {
      if (!editor) return;
      var e = editor; editor = null;
      if (e.nova && !e.nota.texto) remover(e.nota);
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

    /* ---------- ligar ---------- */
    var ro = null;
    global.addEventListener('pointerdown', aoBaixar, true);
    global.addEventListener('pointermove', aoMover, true);
    global.addEventListener('pointerup', aoSoltar, true);
    global.addEventListener('pointercancel', cancelar, true);
    global.addEventListener('click', aoClicar, true);
    global.addEventListener('mousedown', aoMousedown, true);
    global.addEventListener('contextmenu', aoContexto, true);
    doc.addEventListener('selectstart', aoSelecionar, true);
    global.addEventListener('keydown', aoTecla, true);
    global.addEventListener('scroll', function () { cancelar(); esconderAlvo(); }, true);
    global.addEventListener('resize', desenharPinos);
    if (global.ResizeObserver) { ro = new ResizeObserver(function () { if (notas.length) desenharPinos(); }); ro.observe(doc.body); }
    montarChip();
    if (notas.length) desenharPinos();

    var api = {
      usar: usar,
      atual: function () { return atual.id; },
      abrirMenu: abrirMenu,
      fecharMenu: function () { fecharMenu(); },
      notas: function () { return notas.map(function (n, i) { return { n: i + 1, texto: n.texto, onde: n.onde, criado_em: n.criado_em }; }); },
      limparNotas: function () { notas = []; guardar(); fecharEditor(true); desenharPinos(); },
      configurar: function (mudas) { for (var k in mudas) o[k] = mudas[k]; atualizarChip(); },
      destruir: function () {
        cancelar(); fecharMenu(); fecharEditor(true);
        global.removeEventListener('pointerdown', aoBaixar, true); global.removeEventListener('pointermove', aoMover, true);
        global.removeEventListener('pointerup', aoSoltar, true); global.removeEventListener('pointercancel', cancelar, true);
        global.removeEventListener('click', aoClicar, true); global.removeEventListener('mousedown', aoMousedown, true);
        global.removeEventListener('contextmenu', aoContexto, true); doc.removeEventListener('selectstart', aoSelecionar, true);
        global.removeEventListener('keydown', aoTecla, true); if (ro) ro.disconnect();
        [anel, chip, chipBtn, pinos, caixaAlvo, toastEl].forEach(function (x) { if (x && x.parentNode) x.parentNode.removeChild(x); });
        FERR.forEach(function (x) { if (x.cursorClasse) html.classList.remove(x.cursorClasse); });
      }
    };
    return api;
  }

  global.CursorFerramentas = { iniciar: iniciar, versao: '1.0', icones: ICONES };
})(window);
