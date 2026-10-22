/* GraficoPilula · v1 · 261022 · origem: Bubble (gráfico de rede ao lado de Ajustes)
   Gráfico vivo desenhado num <canvas> dentro de uma máscara invisível em formato de pílula.
   Três estilos: "onda" (aplicado no Bubble), "espelho" e "liquido" (guardados como inspiração).

   Uso:
     <span class="gpilula" style="width:84px;height:30px"></span>
     var g = GraficoPilula.montar(el, { tipo: "onda" });   // "onda" | "espelho" | "liquido"
     g.amostra({ a: 1800, b: 320, saude: "boa", teto: 5000 });  // chamar a cada medição (ex.: 2 s)
     g.limpar(); g.destruir();
   Campos da amostra: a = série principal (onda soma a+b; espelho desenha a embaixo e b em cima),
   saude = "boa" | "instavel" | "ruim" (cor do ponto/barras/líquido), teto = valor de "cheio" no líquido.
   Sem dependências. Respeita prefers-reduced-motion (desenha só a cada amostra). */
(function (raiz) {
  "use strict";
  var CSS = ".gpilula{display:block;position:relative;flex:none;border-radius:99px;overflow:hidden}.gpilula canvas{display:block;width:100%;height:100%}";
  var SAUDE = { boa: "#1FA855", instavel: "#E89A0C", ruim: "#D11F32" };
  var IRID = ["#8B7BFF", "#46C7FF", "#FF7BC8", "#FFC861"];
  var reduz = raiz.matchMedia ? raiz.matchMedia("(prefers-reduced-motion: reduce)") : null;

  function estilo() {
    if (document.getElementById("gpilula-css")) return;
    var s = document.createElement("style"); s.id = "gpilula-css"; s.textContent = CSS; document.head.appendChild(s);
  }
  function rgba(hex, a) { var n = parseInt(hex.slice(1), 16); return "rgba(" + (n >> 16 & 255) + "," + (n >> 8 & 255) + "," + (n & 255) + "," + a + ")"; }
  function fadeEsquerda(c, H, larg) {
    c.save(); c.globalCompositeOperation = "destination-out";
    var g = c.createLinearGradient(0, 0, larg, 0); g.addColorStop(0, "rgba(0,0,0,1)"); g.addColorStop(1, "rgba(0,0,0,0)");
    c.fillStyle = g; c.fillRect(0, 0, larg, H); c.restore();
  }

  function montar(el, op) {
    op = op || {}; estilo();
    el.classList.add("gpilula");
    var cv = document.createElement("canvas"); cv.setAttribute("aria-hidden", "true"); el.appendChild(cv);
    var g = { tipo: op.tipo || "onda", janela: op.janela || 60000, janelaMin: op.janelaMin || 16000, hist: [], max: 2000, nivel: 0, fase: Math.random() * 6, raf: 0, vivo: true,
      corUp: op.corUp || "#7C5CFF", corDown: op.corDown || "#2FB4F0" };

    function v(s, k) { return k === "tot" ? s.a + s.b : s[k]; }
    function agoraDe(s, now, k) {   // a última medição desliza da anterior até ela em 0,7 s
      var h = g.hist, b = h[h.length - 1], a = h[h.length - 2] || b, t = Math.min(1, Math.max(0, (now - b.t) / 700));
      t = 1 - Math.pow(1 - t, 3); return v(a, k) + (v(b, k) - v(a, k)) * t;
    }

    function onda(c, W, H, u, now) {
      var h = g.hist, m = 600; h.forEach(function (s) { m = Math.max(m, v(s, "tot")); });
      g.max += (m * 1.15 - g.max) * .06;
      var pad = 4 * u, y = function (x) { return H - pad - x / g.max * (H - pad * 2); }, ult = h[h.length - 1];
      var jan = Math.max(g.janelaMin, Math.min(g.janela, now - h[0].t)), vA = agoraDe(ult, now, "tot");
      var pts = h.map(function (s, i) { return [W - (now - s.t) / jan * W, y(i === h.length - 1 ? vA : v(s, "tot"))]; });
      pts.push([W + 2, pts[pts.length - 1][1]]);
      function curva() { c.beginPath(); c.moveTo(pts[0][0], pts[0][1]); for (var i = 1; i < pts.length - 1; i++) c.quadraticCurveTo(pts[i][0], pts[i][1], (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2); }
      var area = c.createLinearGradient(0, 0, 0, H); area.addColorStop(0, "rgba(124,92,255,.32)"); area.addColorStop(1, "rgba(70,199,255,0)");
      curva(); c.lineTo(W + 2, H); c.lineTo(pts[0][0], H); c.closePath(); c.fillStyle = area; c.fill();
      var ln = c.createLinearGradient(0, 0, W, 0); ln.addColorStop(0, IRID[0]); ln.addColorStop(.4, IRID[1]); ln.addColorStop(.75, IRID[2]); ln.addColorStop(1, IRID[3]);
      curva(); c.strokeStyle = ln; c.lineWidth = 1.8 * u; c.lineJoin = c.lineCap = "round"; c.stroke();
      var cor = ult.saude && ult.saude !== "boa" ? SAUDE[ult.saude] : IRID[3];
      c.beginPath(); c.arc(W - 5 * u, y(vA), 2.4 * u, 0, 6.3); c.fillStyle = cor; c.shadowColor = cor; c.shadowBlur = 6 * u; c.fill(); c.shadowBlur = 0;
      fadeEsquerda(c, H, 18 * u);
    }

    function espelho(c, W, H, u, now) {   // b (ex.: envio) em cima, a (ex.: recebimento) embaixo, escala única
      var h = g.hist, m = 600, meio = H / 2, gap = 1.2 * u, passo = h.length > 1 ? h[h.length - 1].t - h[h.length - 2].t : 2000;
      h.forEach(function (s) { m = Math.max(m, s.a, s.b); });
      g.max += (m * 1.1 - g.max) * .06;
      var jan = Math.max(g.janelaMin, Math.min(g.janela * .8, now - h[0].t)), bw = Math.max(1.6 * u, W / (g.janela * .8 / passo) - 1.6 * u);
      c.lineCap = "round"; c.lineWidth = bw;
      h.forEach(function (s, i) {
        var x = W - 4 * u - (now - s.t) / jan * W; if (x < -bw) return;
        var ult = i === h.length - 1, vb = ult ? agoraDe(s, now, "b") : s.b, va = ult ? agoraDe(s, now, "a") : s.a;
        var alt = function (x) { return Math.max(.6 * u, x / g.max * (meio - gap - 2.5 * u)); };
        var alerta = s.saude && s.saude !== "boa";
        c.globalAlpha = ult ? 1 : .82;
        c.strokeStyle = alerta ? SAUDE[s.saude] : g.corUp; c.beginPath(); c.moveTo(x, meio - gap); c.lineTo(x, meio - gap - alt(vb)); c.stroke();
        c.strokeStyle = alerta ? rgba(SAUDE[s.saude], .7) : g.corDown; c.beginPath(); c.moveTo(x, meio + gap); c.lineTo(x, meio + gap + alt(va)); c.stroke();
      });
      c.globalAlpha = 1; fadeEsquerda(c, H, 16 * u);
    }

    function liquido(c, W, H, u, now) {   // nível = (a+b) ÷ teto; número dentro; cor = saúde
      var ult = g.hist[g.hist.length - 1], tot = agoraDe(ult, now, "tot"), t = now / 1000;
      g.nivel += (Math.min(1, tot / (ult.teto || 5000)) - g.nivel) * .05;
      var ny = H - (.12 + g.nivel * .8) * H, gr = c.createLinearGradient(0, 0, W, 0);
      if (!ult.saude || ult.saude === "boa") { gr.addColorStop(0, "#46C7FF"); gr.addColorStop(1, "#8B7BFF"); }
      else { gr.addColorStop(0, SAUDE[ult.saude]); gr.addColorStop(1, rgba(SAUDE[ult.saude], .75)); }
      function onda2(amp, comp, vel, fase, alpha) {
        c.beginPath(); c.moveTo(0, H); for (var x = 0; x <= W; x += 2) c.lineTo(x, ny + Math.sin(x / comp + t * vel + fase) * amp);
        c.lineTo(W, H); c.closePath(); c.globalAlpha = alpha; c.fillStyle = gr; c.fill(); c.globalAlpha = 1;
      }
      onda2(2.2 * u, 7 * u, 1.6, g.fase + 2, .35); onda2(1.6 * u, 9 * u, -2.1, g.fase, .9);
      c.font = "700 " + (10.5 * u) + "px Inter, Segoe UI, system-ui, sans-serif"; c.textAlign = "center"; c.textBaseline = "middle";
      c.fillStyle = op.corTexto || "rgba(13,17,23,.88)";
      c.fillText((tot / 1000).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + (op.unidade || " Mb/s"), W / 2, H / 2 + .5 * u);
    }

    function quadro(now) {
      g.raf = 0; if (!g.vivo) return;
      var calmo = !!reduz && reduz.matches, h = g.hist;
      if (calmo && h.length) now = h[h.length - 1].t + 700;
      var dpr = Math.min(3, raiz.devicePixelRatio || 1), W = el.clientWidth, H = el.clientHeight;
      if (!W || !H || document.hidden) return;   // volta na próxima amostra
      if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); }
      var c = cv.getContext("2d"); c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, W, H);
      if (h.length) (g.tipo === "espelho" ? espelho : g.tipo === "liquido" ? liquido : onda)(c, W, H, H / 30, now);
      if (!calmo) g.raf = raiz.requestAnimationFrame(quadro);
    }
    function acordar() { if (!g.raf && g.vivo) g.raf = raiz.requestAnimationFrame(quadro); }

    return {
      amostra: function (s) {
        g.hist.push({ t: performance.now(), a: Math.max(0, +s.a || 0), b: Math.max(0, +s.b || 0), saude: s.saude, teto: s.teto });
        while (g.hist.length > (op.maxAmostras || 45)) g.hist.shift();
        acordar();
      },
      limpar: function () { g.hist = []; var c = cv.getContext("2d"); c.clearRect(0, 0, cv.width, cv.height); },
      tipo: function (t) { g.tipo = t; acordar(); },
      destruir: function () { g.vivo = false; if (g.raf) raiz.cancelAnimationFrame(g.raf); cv.remove(); el.classList.remove("gpilula"); }
    };
  }
  raiz.GraficoPilula = { montar: montar, versao: "1.0.0" };
})(typeof window !== "undefined" ? window : this);
