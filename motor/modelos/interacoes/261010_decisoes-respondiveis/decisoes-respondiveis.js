/* decisoes-respondiveis v1.1 · 261013 · MEGABRAIN
   v1.1: barra no fluxo do documento em viewport de até 480 px de altura, sem cobrir alternativas.
   Fonte única: MEGA B R A I  N/motor/modelos/interacoes/261010_decisoes-respondiveis/decisoes-respondiveis.js
   Primeira aplicação: Portfólio · Decisões do Portfólio (10/10/2026), aprovada pelo Usuário ("adorei").
   O que faz: transforma um relatório em formulário de decisão. Cada pergunta vira uma caixa com
   alternativas (recomendação já marcada) ou resposta escrita (com sugestões), barra de progresso e
   UM botão Finalizar. No claude.ai: comentário "Send to Claude" (acorda a sessão) + respostas.json.
   Fora do claude.ai: Copiar respostas e Baixar respostas (.json), para qualquer agente ler.
   Uso: DecisoesRespondiveis.iniciar({ chave, titulo, secoes:[{id, titulo, perguntas:[...]}] })
   Marcação: <div data-dr-sec="ID"></div> onde as caixas entram; opcionais <span data-dr-status="ID">
   e <span data-dr-dot="ID">. Liga CursorFerramentas sozinho se o script dele estiver na página. */
(function (global) {
  'use strict';
  if (global.DecisoesRespondiveis) return;

  var CSS = [
    ':root{--dr-card:var(--card,#191927);--dr-card2:var(--card2,#23233A);--dr-ink:var(--ink,var(--tinta,#FFFFFF));--dr-body:var(--body,var(--corpo,#C9C7E0));--dr-muted:var(--muted,var(--fraco,#8F8DAA));--dr-line:var(--line,var(--linha,rgba(255,255,255,.11)));--dr-accent:var(--accent,var(--magenta,#EC0F7C));--dr-ok:var(--ok,var(--verde,#58CC02));--dr-info:var(--info,var(--azul,#1CB0F6));--dr-bad:var(--bad,var(--coral,#FF4B4B));--dr-bg:var(--bg,var(--fundo,#0B0B16))}',
    '.dr-perguntas{display:grid;gap:14px;margin-top:18px}',
    '.dr-pergunta{margin:0;border:1px solid var(--dr-line);border-radius:12px;background:var(--dr-card);padding:16px;min-width:0;color:var(--dr-body);font-family:inherit;font-size:16px;line-height:1.5}',
    '.dr-pergunta.dr-mexeu{border-color:color-mix(in srgb,var(--dr-ok) 45%,var(--dr-line))}',
    '.dr-pergunta legend{padding:0;float:left;width:100%;color:var(--dr-ink);font-weight:700;font-size:17px;line-height:1.3;display:flex;gap:10px;align-items:baseline}',
    '.dr-pergunta legend+*{clear:both}',
    '.dr-pn{font:500 12px/1 ui-monospace,Consolas,monospace;color:var(--dr-accent);background:color-mix(in srgb,var(--dr-accent) 12%,transparent);padding:5px 7px;border-radius:6px;flex:none}',
    '.dr-flag{margin-left:auto;font:500 11px/1 ui-monospace,Consolas,monospace;text-transform:uppercase;letter-spacing:.05em;color:var(--dr-muted);white-space:nowrap}',
    '.dr-mexeu .dr-flag{color:var(--dr-ok)}',
    '.dr-porque{color:var(--dr-muted);font-size:14px;margin:8px 0 0}',
    '.dr-img{margin:12px 0 0}.dr-img img{display:block;width:100%;border-radius:10px;border:1px solid var(--dr-line)}',
    '.dr-opcoes{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin-top:12px}',
    '.dr-opcao{position:relative;display:block;cursor:pointer}',
    '.dr-opcao>input{position:absolute;opacity:0;width:1px;height:1px}',
    '.dr-card{display:flex;flex-direction:column;gap:8px;height:100%;box-sizing:border-box;border:1.5px solid var(--dr-line);border-radius:10px;padding:12px;background:var(--dr-card2);transition:border-color .15s,background .15s}',
    '.dr-opcao:hover .dr-card{border-color:color-mix(in srgb,var(--dr-accent) 55%,var(--dr-line))}',
    '.dr-opcao>input:checked+.dr-card{border-color:var(--dr-accent);background:color-mix(in srgb,var(--dr-accent) 10%,var(--dr-card2))}',
    '.dr-opcao>input:focus-visible+.dr-card{outline:2px solid var(--dr-info);outline-offset:2px}',
    '.dr-rec{align-self:flex-start;font:500 11px/1 ui-monospace,Consolas,monospace;letter-spacing:.05em;text-transform:uppercase;color:var(--dr-accent);background:color-mix(in srgb,var(--dr-accent) 14%,transparent);padding:5px 7px;border-radius:6px}',
    '.dr-topo{display:flex;gap:8px;align-items:flex-start}.dr-topo b{color:var(--dr-ink);font-size:15px;line-height:1.3;flex:1}',
    '.dr-radio{width:18px;height:18px;border-radius:50%;border:2px solid var(--dr-muted);flex:none;margin-top:1px;display:grid;place-items:center;box-sizing:border-box}',
    '.dr-opcao>input:checked+.dr-card .dr-radio{border-color:var(--dr-accent);background:var(--dr-accent)}',
    '.dr-opcao>input:checked+.dr-card .dr-radio::after{content:"";width:6px;height:6px;border-radius:50%;background:var(--dr-card)}',
    '.dr-desc{font-size:14px}',
    '.dr-meta{display:flex;flex-wrap:wrap;gap:6px}.dr-meta span{font-size:12px;color:var(--dr-muted);border:1px solid var(--dr-line);border-radius:6px;padding:3px 6px}',
    '.dr-vis{border-radius:8px;overflow:hidden;background:var(--dr-card)}.dr-vis svg,.dr-vis img{display:block;width:100%;height:auto}',
    '.dr-extra{display:block;width:100%;box-sizing:border-box;font-family:inherit;font-size:15px;color:var(--dr-ink);background:var(--dr-card);border:1px dashed var(--dr-muted);border-radius:8px;padding:8px 10px}',
    '.dr-resp{display:block;width:100%;box-sizing:border-box;margin-top:12px;font-family:inherit;font-size:16px;line-height:1.5;color:var(--dr-ink);background:var(--dr-card2);border:1.5px dashed var(--dr-muted);border-radius:10px;padding:12px;resize:vertical}',
    '.dr-resp:focus,.dr-extra:focus{outline:2px solid var(--dr-info);outline-offset:1px;border-style:solid}',
    '.dr-sug{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.dr-sug button{font-family:inherit;font-size:14px;color:var(--dr-ink);background:transparent;border:1px solid var(--dr-line);border-radius:999px;padding:6px 10px;cursor:pointer}.dr-sug button:hover{border-color:var(--dr-accent)}',
    '.dr-revisar{margin-top:34px;background:var(--dr-card);border:2px solid var(--dr-accent);border-radius:16px;padding:20px;color:var(--dr-body)}',
    '.dr-revisar h2{color:var(--dr-ink);margin:0 0 8px}',
    '.dr-resumo{display:grid;gap:12px;margin-top:14px}.dr-resumo section{border:1px solid var(--dr-line);border-radius:10px;padding:10px 12px}.dr-resumo h3{color:var(--dr-ink);font-size:15px;margin:0 0 6px}',
    '.dr-resumo ul{margin:0;padding:0;list-style:none;display:grid;gap:6px;font-size:14px}.dr-resumo li{display:flex;gap:8px;flex-wrap:wrap;align-items:baseline}',
    '.dr-resumo .q{color:var(--dr-muted)}.dr-resumo .v{color:var(--dr-ink);font-weight:600}',
    '.dr-origem{font:500 11px/1 ui-monospace,Consolas,monospace;text-transform:uppercase;padding:4px 6px;border-radius:5px}.dr-origem.sua{color:var(--dr-ok);background:color-mix(in srgb,var(--dr-ok) 14%,transparent)}.dr-origem.rec{color:var(--dr-muted);background:color-mix(in srgb,var(--dr-muted) 16%,transparent)}',
    '.dr-acoes{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}',
    '.dr-btn{font-family:inherit;font-weight:700;font-size:15px;border-radius:999px;padding:12px 18px;border:1.5px solid var(--dr-line);background:var(--dr-card2);color:var(--dr-ink);cursor:pointer}',
    '.dr-btn:hover{border-color:var(--dr-accent)}.dr-btn.prim{background:var(--dr-accent);border-color:var(--dr-accent);color:#fff}.dr-btn:disabled{opacity:.6;cursor:progress}',
    '.dr-btn:focus-visible{outline:2px solid var(--dr-info);outline-offset:2px}',
    '.dr-aviso{margin-top:12px;border-radius:10px;padding:12px 14px;font-size:15px;color:var(--dr-ink);background:var(--dr-card2);border:1px solid var(--dr-line)}',
    '.dr-aviso.ok{border-color:color-mix(in srgb,var(--dr-ok) 50%,transparent)}.dr-aviso.erro{border-color:color-mix(in srgb,var(--dr-bad) 50%,transparent)}',
    '.dr-saida{width:100%;box-sizing:border-box;min-height:140px;margin-top:12px;font:13px/1.5 ui-monospace,Consolas,monospace;color:var(--dr-ink);background:var(--dr-card2);border:1px solid var(--dr-line);border-radius:10px;padding:10px}',
    '.dr-barra{position:sticky;bottom:0;margin-top:28px;padding:12px 16px calc(12px + env(safe-area-inset-bottom,0px));background:color-mix(in srgb,var(--dr-bg) 92%,transparent);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);border-top:1px solid var(--dr-line);display:flex;flex-wrap:wrap;gap:12px;align-items:center;z-index:5}',
    '.dr-prog{flex:1;min-width:200px}.dr-prog p{margin:0;font-size:14px;color:var(--dr-ink);font-weight:600}.dr-prog small{display:block;font-size:12px;color:var(--dr-muted)}',
    '.dr-trilho{height:6px;border-radius:999px;background:var(--dr-card2);margin-top:6px;overflow:hidden}.dr-trilho i{display:block;height:100%;width:0;background:var(--dr-ok);border-radius:999px;transition:width .25s}',
    '.dr-dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--dr-muted)}.dr-dot.parcial{background:#FFC800}.dr-dot.feito{background:var(--dr-ok)}',
    '[data-dr-status].feito{color:var(--dr-ok)}',
    '.dr-banner{margin:16px 0;border-radius:12px;padding:12px 16px;color:var(--dr-ink);background:color-mix(in srgb,var(--dr-ok) 14%,var(--dr-card));border:1px solid color-mix(in srgb,var(--dr-ok) 45%,transparent)}',
    '@media (max-height:480px){.dr-barra{position:static;bottom:auto;z-index:auto}.dr-prog{flex-basis:100%;min-width:0}.dr-barra .dr-btn{max-width:100%;white-space:normal}#dr-cf-lugar{max-width:100%}}',
    '@media (prefers-reduced-motion:reduce){.dr-card,.dr-trilho i{transition:none}}'
  ].join('\n');

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function iniciar(o) {
    o = o || {};
    var doc = document, KEY = o.chave || ('dr:' + location.pathname), TIT = o.titulo || doc.title || 'Decisões';
    if (!doc.getElementById('dr-estilo')) { var st = doc.createElement('style'); st.id = 'dr-estilo'; st.textContent = CSS; (doc.head || doc.documentElement).insertBefore(st, (doc.head || doc.documentElement).firstChild); }
    var SEC = o.secoes || [], TOTAL = 0, R = {}, IDX = {};
    SEC.forEach(function (s) { s.perguntas.forEach(function (q) { TOTAL++; IDX[q.id] = q; R[q.id] = { valor: q.tipo === 'texto' ? (q.valor || '') : q.rec, extra: '', mexeu: false }; }); });

    var CF = null;
    function notas() { return CF ? CF.notas() : []; }

    function htmlPergunta(q) {
      var h = '<fieldset class="dr-pergunta" id="dr_f_' + q.id + '"><legend><span class="dr-pn">' + esc(q.n || '') + '</span><span>' + esc(q.titulo) + '</span><span class="dr-flag" data-cf-sem-rotulo id="dr_flag_' + q.id + '"></span></legend>';
      if (q.porque) h += '<p class="dr-porque">' + esc(q.porque) + '</p>';
      if (q.img) h += '<figure class="dr-img"><img src="' + q.img + '" alt="' + esc(q.imgAlt || q.titulo) + '"></figure>';
      if (q.tipo === 'escolha') {
        h += '<div class="dr-opcoes" role="radiogroup">';
        q.opcoes.forEach(function (op) {
          var id = 'dr_' + q.id + '__' + op.v;
          h += '<label class="dr-opcao" for="' + id + '"><input type="radio" id="' + id + '" name="dr_' + q.id + '" value="' + esc(op.v) + '" data-dr-q="' + q.id + '"><span class="dr-card">';
          if (op.vis) h += '<span class="dr-vis">' + op.vis + '</span>';
          if (op.v === q.rec) h += '<span class="dr-rec">Recomendado</span>';
          h += '<span class="dr-topo"><span class="dr-radio"></span><b>' + esc(op.t) + '</b></span>';
          if (op.d) h += '<span class="dr-desc">' + esc(op.d) + '</span>';
          if (op.meta) h += '<span class="dr-meta">' + op.meta.map(function (m) { return '<span>' + esc(m) + '</span>'; }).join('') + '</span>';
          if (op.extra) h += '<input class="dr-extra" type="' + (op.extra === 'data' ? 'date' : 'text') + '" id="' + id + '__extra" data-dr-extra="' + q.id + '" hidden aria-label="Complemento"' + (op.extra === 'data' ? '' : ' placeholder="' + esc(op.extra) + '"') + '>';
          h += '</span></label>';
        });
        h += '</div>';
      } else {
        h += q.linha ? '<input class="dr-resp" type="text" id="dr_' + q.id + '" data-dr-texto="' + q.id + '" aria-label="' + esc(q.titulo) + '" placeholder="' + esc(q.ph || '') + '">'
                     : '<textarea class="dr-resp" rows="3" id="dr_' + q.id + '" data-dr-texto="' + q.id + '" aria-label="' + esc(q.titulo) + '" placeholder="' + esc(q.ph || '') + '"></textarea>';
        if (q.sug) h += '<div class="dr-sug">' + q.sug.map(function (s) { return '<button type="button" data-dr-sug="' + q.id + '">' + esc(s) + '</button>'; }).join('') + '</div>';
      }
      return h + '</fieldset>';
    }
    SEC.forEach(function (s) { var box = doc.querySelector('[data-dr-sec="' + s.id + '"]'); if (box) { box.classList.add('dr-perguntas'); box.innerHTML = s.perguntas.map(htmlPergunta).join(''); } });

    /* painel de revisão + barra */
    var todas = doc.querySelectorAll('[data-dr-sec]'), ancora = todas[todas.length - 1];
    var raiz = o.raiz || (ancora && (ancora.closest('main') || ancora.closest('#pagina'))) || doc.body;
    var banner = doc.createElement('div'); banner.className = 'dr-banner'; banner.hidden = true; banner.setAttribute('role', 'status');
    var primeiro = doc.querySelector('[data-dr-sec]'); if (o.bannerEm) o.bannerEm.appendChild(banner); else if (primeiro && primeiro.parentNode) (primeiro.closest('section') || primeiro).insertAdjacentElement('beforebegin', banner);
    var rev = doc.createElement('section'); rev.className = 'dr-revisar'; rev.hidden = true; rev.id = 'dr-revisar';
    rev.innerHTML = '<h2 id="dr-revisar-titulo">Revise e envie</h2><p>“Sua escolha” = você mexeu. “Recomendação” = ficou o que vinha marcado.</p><p class="dr-aviso" id="dr-aviso-claude">Conferindo se o Claude pode ser avisado daqui…</p><div class="dr-resumo" id="dr-resumo"></div>' +
      '<div class="dr-acoes"><button class="dr-btn prim" type="button" id="dr-enviar">Enviar</button><button class="dr-btn" type="button" id="dr-voltar">Voltar e ajustar</button><button class="dr-btn" type="button" id="dr-copiar">Copiar respostas</button><button class="dr-btn" type="button" id="dr-baixar" hidden>Baixar respostas</button></div><div id="dr-retorno"></div><textarea class="dr-saida" id="dr-saida" readonly hidden aria-label="Respostas em texto"></textarea>';
    var barra = doc.createElement('div'); barra.className = 'dr-barra';
    barra.innerHTML = '<div class="dr-prog"><p id="dr-prog-txt"></p><small>O que você não mexer vai com a recomendação.</small><div class="dr-trilho"><i id="dr-prog-bar"></i></div></div><span id="dr-cf-lugar"></span><button class="dr-btn prim" type="button" id="dr-finalizar">Finalizar respostas</button>';
    raiz.appendChild(rev); if (o.barra !== false) raiz.appendChild(barra);
    if (o.cursor !== false) {
      if (o.cursor && typeof o.cursor.notas === 'function') CF = o.cursor;
      else if (global.CursorFerramentas) try { CF = global.CursorFerramentas.iniciar({ modo: 'auto', chave: KEY + '-notas', chip: o.chipEm || doc.getElementById('dr-cf-lugar') || true }); } catch (e) { CF = null; }
    }

    function aplicar(src) { if (!src) return; Object.keys(src).forEach(function (k) { if (R[k] && src[k]) R[k] = { valor: src[k].valor, extra: src[k].extra || '', mexeu: !!src[k].mexeu }; }); }
    var FINAL = null;
    try { var ls = JSON.parse(global.localStorage.getItem(KEY) || 'null'); if (ls && ls.respostas) aplicar(ls.respostas); } catch (e) {}
    function salvar() { try { global.localStorage.setItem(KEY, JSON.stringify({ salvo_em: new Date().toISOString(), respostas: R })); } catch (e) {} }
    function preencher() {
      Object.keys(IDX).forEach(function (id) {
        var q = IDX[id], r = R[id];
        if (q.tipo === 'escolha') {
          var el = doc.getElementById('dr_' + id + '__' + r.valor); if (el) el.checked = true;
          q.opcoes.forEach(function (op) { if (op.extra) { var x = doc.getElementById('dr_' + id + '__' + op.v + '__extra'); if (x) { x.hidden = r.valor !== op.v; if (r.valor === op.v) x.value = r.extra || ''; } } });
        } else { var t = doc.getElementById('dr_' + id); if (t) t.value = r.valor || ''; }
      });
      atualizar();
    }
    function atualizar() {
      var mex = 0;
      SEC.forEach(function (s) {
        var n = 0;
        s.perguntas.forEach(function (q) {
          var m = R[q.id].mexeu; if (m) { n++; mex++; }
          var f = doc.getElementById('dr_f_' + q.id); if (f) f.classList.toggle('dr-mexeu', m);
          var fl = doc.getElementById('dr_flag_' + q.id); if (fl) fl.textContent = m ? 'sua escolha' : (q.tipo === 'texto' && !R[q.id].valor ? 'opcional' : 'recomendação');
        });
        var st = doc.querySelector('[data-dr-status="' + s.id + '"]'), dot = doc.querySelector('[data-dr-dot="' + s.id + '"]'), tot = s.perguntas.length;
        if (st) { st.textContent = n + ' de ' + tot + ' mexida' + (tot > 1 ? 's' : ''); st.classList.toggle('feito', n === tot); }
        if (dot) dot.className = 'dr-dot' + (n === tot ? ' feito' : n > 0 ? ' parcial' : '');
      });
      var pt = doc.getElementById('dr-prog-txt'); if (pt) pt.textContent = 'Você mexeu em ' + mex + ' de ' + TOTAL;
      var pb = doc.getElementById('dr-prog-bar'); if (pb) pb.style.width = Math.round(mex / Math.max(1, TOTAL) * 100) + '%';
    }
    doc.addEventListener('change', function (e) {
      var t = e.target, id = t.dataset && t.dataset.drQ; if (!id || t.type !== 'radio') return;
      R[id].valor = t.value; R[id].mexeu = true; R[id].extra = '';
      IDX[id].opcoes.forEach(function (op) { if (op.extra) { var x = doc.getElementById('dr_' + id + '__' + op.v + '__extra'); if (x) { x.hidden = op.v !== t.value; if (op.v === t.value) { x.value = ''; setTimeout(function () { x.focus(); }, 0); } } } });
      salvar(); atualizar();
    });
    doc.addEventListener('input', function (e) {
      var t = e.target, d = t.dataset || {};
      if (d.drExtra && R[d.drExtra]) { R[d.drExtra].extra = t.value; R[d.drExtra].mexeu = true; }
      else if (d.drTexto && R[d.drTexto]) { R[d.drTexto].valor = t.value; R[d.drTexto].mexeu = true; }
      else return;
      salvar(); atualizar();
    });
    doc.addEventListener('click', function (e) {
      var b = e.target.closest && e.target.closest('[data-dr-sug]'); if (!b) return;
      var id = b.dataset.drSug, t = doc.getElementById('dr_' + id); if (!t) return;
      t.value = t.value ? (t.value.replace(/\s+$/, '') + '; ' + b.textContent) : b.textContent; R[id].valor = t.value; R[id].mexeu = true; salvar(); atualizar(); t.focus();
    });

    function rotulo(q) { var r = R[q.id]; if (q.tipo === 'texto') return r.valor || '(vazio)'; var op = q.opcoes.filter(function (x) { return x.v === r.valor; })[0]; return (op ? op.t : r.valor) + (r.extra ? ' · ' + r.extra : ''); }
    function textoResumo() {
      var L = ['RESPOSTAS · ' + TIT + ' · ' + new Date().toLocaleString('pt-BR')];
      SEC.forEach(function (s) { L.push(''); L.push(s.titulo || s.id); s.perguntas.forEach(function (q) { L.push((q.n ? q.n + ' ' : '') + q.titulo + ' → ' + rotulo(q) + (R[q.id].mexeu ? '' : ' [recomendação]')); }); });
      var ns = notas(); if (ns.length) { L.push(''); L.push('NOTAS NA PÁGINA'); ns.forEach(function (n) { L.push(n.n + '. ' + n.texto + ' (perto de: ' + n.onde + ')'); }); }
      return L.join('\n');
    }
    function textoCurto(p) {
      var n = 0; Object.keys(R).forEach(function (k) { if (R[k].mexeu) n++; });
      var L = ['Usuário finalizou "' + TIT + '" em ' + new Date(p.enviado_em).toLocaleString('pt-BR') + '. Mexeu em ' + n + ' de ' + TOTAL + ' (* = escolha dele).'];
      Object.keys(IDX).forEach(function (id) { var q = IDX[id], r = R[id]; L.push((q.n ? q.n + ' ' : '') + id + ' = ' + (q.tipo === 'texto' ? (r.valor || '-') : r.valor + (r.extra ? ' (' + r.extra + ')' : '')) + (r.mexeu ? ' *' : '')); });
      var ns = notas(); if (ns.length) { L.push('Notas (' + ns.length + '):'); ns.forEach(function (x) { L.push(x.n + '. ' + String(x.texto).slice(0, 160) + ' [perto de: ' + String(x.onde).slice(0, 60) + ']'); }); }
      L.push('Versão completa: respostas.json desta página.');
      var s = L.join('\n'), enc = new TextEncoder(); while (enc.encode(s).length > 3900) s = s.slice(0, -40);
      return s;
    }
    function payload() { return { versao: 1, titulo: TIT, chave: KEY, finalizado: true, enviado_em: new Date().toISOString(), total: TOTAL, respostas: R, notas: notas(), resumo_texto: textoResumo() }; }
    function retorno(tipo, html) { doc.getElementById('dr-retorno').innerHTML = '<div class="dr-aviso ' + tipo + '">' + html + '</div>'; }
    function mostrarCopia() { var s = doc.getElementById('dr-saida'); s.value = textoResumo(); s.hidden = false; }
    function montarResumo() {
      var ns = notas();
      doc.getElementById('dr-resumo').innerHTML = (ns.length ? '<section><h3>Notas na página</h3><ul>' + ns.map(function (n) { return '<li><span class="q">' + n.n + '. perto de: ' + esc(n.onde) + '</span><span class="v">' + esc(n.texto) + '</span></li>'; }).join('') + '</ul></section>' : '') +
        SEC.map(function (s) { return '<section><h3>' + esc(s.titulo || s.id) + '</h3><ul>' + s.perguntas.map(function (q) { var m = R[q.id].mexeu; return '<li><span class="q">' + esc((q.n ? q.n + ' ' : '') + q.titulo) + '</span><span class="v">' + esc(rotulo(q)) + '</span><span class="dr-origem ' + (m ? 'sua' : 'rec') + '">' + (m ? 'sua escolha' : 'recomendação') + '</span></li>'; }).join('') + '</ul></section>'; }).join('');
    }
    var temClaude = !!(global.claude && typeof global.claude.use === 'function');
    var artP = temClaude ? global.claude.use('artifact').catch(function () { return null; }) : Promise.resolve(null);
    var comP = temClaude ? global.claude.use('comments').catch(function () { return null; }) : Promise.resolve(null);
    var pode = 'off';
    if (!temClaude) doc.getElementById('dr-baixar').hidden = false;
    function checar() {
      return comP.then(function (c) { if (!c || typeof c.canSendToClaude !== 'function') return 'off'; return c.canSendToClaude().catch(function () { return 'off'; }); }).then(function (v) {
        pode = v; var el = doc.getElementById('dr-aviso-claude');
        if (v === 'available') { el.className = 'dr-aviso ok'; el.textContent = 'Ao enviar, o Claude é avisado na hora por um comentário nesta página. Na primeira vez o claude.ai pode pedir permissão.'; }
        else if (temClaude) { el.className = 'dr-aviso'; el.textContent = 'O aviso automático não está disponível agora. As respostas ficam salvas na página: depois de enviar, escreva "respondi" no chat.'; }
        else { el.className = 'dr-aviso'; el.textContent = 'Página aberta fora do claude.ai: use Copiar respostas (cole no chat de qualquer agente) ou Baixar respostas (arquivo .json em Downloads).'; }
      });
    }
    function bannerFinal(p) { var d = p && p.enviado_em ? new Date(p.enviado_em) : null; banner.textContent = 'Respostas enviadas' + (d ? ' em ' + d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '') + '. Se quiser mudar algo, ajuste e finalize de novo.'; banner.hidden = false; }
    function copiar(txt) {
      mostrarCopia();
      function alt() { doc.getElementById('dr-saida').select(); retorno('', 'Selecionei o texto abaixo. Use Ctrl+C e cole no chat.'); }
      try { navigator.clipboard.writeText(txt).then(function () { retorno('ok', 'Respostas copiadas. Cole no chat do agente.'); }, alt); } catch (e) { alt(); }
    }
    doc.getElementById('dr-finalizar').addEventListener('click', function () { checar(); montarResumo(); rev.hidden = false; doc.getElementById('dr-retorno').innerHTML = ''; rev.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
    doc.getElementById('dr-voltar').addEventListener('click', function () { rev.hidden = true; });
    doc.getElementById('dr-copiar').addEventListener('click', function () { copiar(textoResumo()); });
    doc.getElementById('dr-baixar').addEventListener('click', function () {
      var p = payload(), d = new Date(), nome = KEY.replace(/[^a-z0-9_-]+/gi, '-') + '-respostas-' + String(d.getFullYear()).slice(2) + String(d.getMonth() + 1).padStart(2, '0') + String(d.getDate()).padStart(2, '0') + '.json';
      try { var url = URL.createObjectURL(new Blob([JSON.stringify(p, null, 2)], { type: 'application/json' })), a = doc.createElement('a'); a.href = url; a.download = nome; doc.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(url); }, 4000); retorno('ok', 'Arquivo ' + esc(nome) + ' salvo em Downloads. Avise o agente que ele está lá.'); }
      catch (e) { copiar(textoResumo()); }
    });
    doc.getElementById('dr-enviar').addEventListener('click', function () {
      var btn = this, p = payload(); btn.disabled = true; retorno('', 'Enviando…');
      var avisoP = comP.then(function (c) {
        if (!c || pode !== 'available' || typeof c.sendToClaude !== 'function') return 'sem';
        return c.anchorFor(doc.getElementById('dr-revisar-titulo')).then(function (a) { return c.sendToClaude({ anchor: a, text: textoCurto(p) }); }).then(function () { return 'ok'; }, function (e) { return (e && e.code) || 'erro'; });
      });
      avisoP.then(function (aviso) {
        return artP.then(function (art) {
          if (!art) return 'sem';
          return art.publish({ 'respostas.json': { content: JSON.stringify(p, null, 2), contentType: 'application/json' } }).then(function () { return 'ok'; }, function (e) { return (e && e.code) || 'erro'; });
        }).then(function (salvo) {
          btn.disabled = false;
          if (salvo === 'ok') { FINAL = p; bannerFinal(p); }
          if (typeof o.aoEnviar === 'function') try { o.aoEnviar(p, { aviso: aviso, salvo: salvo }); } catch (e) {}
          if (aviso === 'ok' && salvo === 'ok') retorno('ok', 'Pronto: o Claude foi avisado e as respostas ficaram salvas nesta página. Pode fechar.');
          else if (aviso === 'ok') retorno('ok', 'O Claude foi avisado com o resumo. A cópia completa não salvou (' + esc(salvo) + ').');
          else if (salvo === 'ok') retorno('', 'Respostas salvas nesta página. O aviso automático não saiu: escreva "respondi" no chat.');
          else if (aviso === 'sem' && salvo === 'sem') { mostrarCopia(); retorno('', 'Página aberta fora do claude.ai: use Copiar respostas ou Baixar respostas.'); }
          else { mostrarCopia(); retorno('erro', 'Não consegui salvar nem avisar. Use Copiar respostas e cole no chat.'); }
        });
      });
    });
    preencher();
    try { fetch('respostas.json', { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) { if (d && d.finalizado) { FINAL = d; bannerFinal(d); } }).catch(function () {}); } catch (e) {}

    return { respostas: function () { return JSON.parse(JSON.stringify(R)); }, resumoTexto: textoResumo, abrirRevisao: function () { doc.getElementById('dr-finalizar').click(); }, cursor: CF };
  }

  global.DecisoesRespondiveis = { iniciar: iniciar, versao: '1.1' };
})(window);
