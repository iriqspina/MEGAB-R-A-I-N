#!/usr/bin/env python3
"""mb_workspace.py — camada de workspace do relatório vivo (v7.0, 260824).

O relatório vira um painel com ABAS que o leitor monta como quer (estilo
workspace do Illustrator): cada aba pode ser fixada (＋) pra abrir lado a
lado; o layout, o tamanho de fonte, a densidade e o rascunho de feedback
persistem por navegador (localStorage com namespace por arquivo — lição
260822: Chrome compartilha uma origem entre arquivos locais).

Regras da casa respeitadas:
- Cor NUNCA sai daqui: só tokens do tema (var(--ink), var(--ok)...).
- Rótulo é hierarquia (--ink-faint); --signal/--ok/--warn são estado.
- Página degrada sem JS: primeira aba visível, resto empilhado? Não —
  sem JS todas as abas ficam visíveis em sequência (noscript-friendly).
Spec: 03_docs/260824_spec-fase2.md §1–§3.
"""
from __future__ import annotations

import html as _html
import re
from pathlib import Path

import mb_utils as u

ABAS = [
    ("painel", "Painel"),
    ("esquema", "Esquema"),
    ("acoes", "Ações"),
    ("skills", "Skills"),
    ("docs", "Documentos"),
    ("historico", "Histórico"),
]

CSS = """
/* ── workspace: barra de controles ─────────────────────────────── */
.wsbar { display:flex; flex-wrap:wrap; align-items:center; gap:.6rem 1rem;
  border:1px solid var(--line); background:var(--paper-high);
  padding:.5rem .8rem; margin:0 0 1rem; }
.wsbar .label { margin-right:.2rem; }
.chip-modo { display:inline-flex; align-items:center; gap:.4rem;
  border:2px solid var(--info); color:var(--info);
  font:800 .72rem/1.4 var(--mono); text-transform:uppercase;
  letter-spacing:.08em; padding:.15rem .6rem; }
.chip-modo::before { content:""; width:.45rem; height:.45rem;
  border-radius:50%; background:var(--info); }
.wsbtn { font:700 .72rem/1.4 var(--mono); border:1px solid var(--line-strong,var(--line));
  background:var(--paper); color:var(--ink); padding:.15rem .55rem;
  cursor:pointer; }
.wsbtn:hover { border-color:var(--ink); }
.wsbtn[aria-pressed="true"] { background:var(--ink); color:var(--paper); }
.ws-grupo { display:inline-flex; align-items:center; gap:.25rem; }
.ws-salvo { color:var(--ink-faint); font:.66rem/1.4 var(--mono); }

/* ── abas ──────────────────────────────────────────────────────── */
.mbtabs { display:flex; flex-wrap:wrap; gap:.35rem; margin:0 0 1.1rem;
  border-bottom:2px solid var(--ink); padding-bottom:.45rem; }
.mbtabs .tab { display:inline-flex; align-items:center; gap:.45rem;
  border:1px solid var(--line); background:var(--paper-high);
  padding:.3rem .7rem; cursor:pointer;
  font:700 .78rem/1.3 var(--mono); text-transform:uppercase; letter-spacing:.05em; }
.mbtabs .tab:hover { border-color:var(--ink); }
.mbtabs .tab.on { background:var(--ink); color:var(--paper); border-color:var(--ink); }
.mbtabs .tab .pin { font-weight:400; opacity:.55; padding:0 .1rem; }
.mbtabs .tab .pin:hover { opacity:1; }
.mbtabs .tab.fixa .pin { opacity:1; color:var(--ok); }
.mbtabs .tab.on .pin { color:inherit; }

.panes { display:grid; grid-template-columns:1fr; gap:1.4rem; align-items:start; }
.panes[data-n="2"] { grid-template-columns:1fr 1fr; }
.panes[data-n="3"] { grid-template-columns:1fr 1fr 1fr; }
.pane { min-width:0; }
.pane > .pane-tit { display:none; }
.js .pane { display:none; }
.js .pane.on { display:block; }
.panes[data-n="2"] .pane.on, .panes[data-n="3"] .pane.on {
  border:1px solid var(--line); padding:0 1rem 1rem; background:var(--paper); overflow:auto; }
.panes[data-n="2"] .pane.on > .pane-tit, .panes[data-n="3"] .pane.on > .pane-tit {
  display:block; margin:.8rem 0 .4rem; }
@media (max-width:900px) { .panes[data-n="2"], .panes[data-n="3"] { grid-template-columns:1fr; } }

/* ── densidade (controle da barra; clamp garante nada vazando) ── */
html[data-dens="compacta"] .wrap { max-width:56rem; }
html[data-dens="ampla"] .wrap { max-width:78rem; }
html[data-dens="compacta"] .slot { margin:.7rem 0; }

/* ── ações e skills ────────────────────────────────────────────── */
.acoes-lista, .skills-lista { display:grid; gap:.6rem;
  grid-template-columns:repeat(auto-fill,minmax(19rem,1fr)); }
.acao, .skillcard { border:1px solid var(--line); background:var(--paper-high);
  padding:.7rem .8rem; display:flex; flex-direction:column; gap:.3rem; }
.acao b { font-size:.9rem; }
.acao .cam, .skillcard .cam { font:.66rem/1.4 var(--mono); color:var(--ink-faint);
  word-break:break-all; }
.acao .desc, .skillcard .desc { font-size:.78rem; color:var(--ink-soft); line-height:1.45; }
.acao .linha-botao { display:flex; gap:.4rem; align-items:center; margin-top:.2rem; }
.skillcard b { font:700 .82rem/1.3 var(--mono); }

/* ── esquema (os desenhos do doc, na linguagem do tema) ────────── */
.esq { display:flex; flex-direction:column; gap:.9rem; }
.esq-row { display:flex; align-items:stretch; gap:.5rem; flex-wrap:wrap; }
.esq-tile { border:1px solid var(--line); background:var(--paper-high);
  padding:.55rem .7rem; min-width:10rem; flex:1 1 10rem; max-width:16rem; }
.esq-tile b { display:block; font:800 .72rem/1.4 var(--mono);
  text-transform:uppercase; letter-spacing:.06em; margin-bottom:.15rem; }
.esq-tile.forte { border:2px solid var(--ink); }
.esq-tile.ok { border-color:var(--ok); } .esq-tile.ok b { color:var(--ok); }
.esq-tile.alerta { border-color:var(--signal); } .esq-tile.alerta b { color:var(--signal); }
.esq-tile small { font-size:.72rem; color:var(--ink-soft); line-height:1.4; display:block; }
.esq-seta { align-self:center; color:var(--ink-faint); font:800 1rem/1 var(--mono); }
.esq-rotulo { font:800 .66rem/1.3 var(--mono); color:var(--ink-faint);
  text-transform:uppercase; letter-spacing:.1em; align-self:center; min-width:5.2rem; }

/* ── feedback rail ─────────────────────────────────────────────── */
.rail { position:fixed; right:0; top:16vh; width:16rem; z-index:40;
  border:1px solid var(--line-strong,var(--line)); border-right:0;
  background:var(--paper-high); padding:.8rem .9rem;
  box-shadow:-2px 2px 0 var(--line); transition:transform .18s ease; }
.rail.fechado { transform:translateX(calc(100% - 2rem)); }
.rail-alca { position:absolute; left:0; top:0; bottom:0; width:2rem;
  writing-mode:vertical-rl; display:flex; align-items:center; justify-content:center;
  font:800 .62rem/1 var(--mono); text-transform:uppercase; letter-spacing:.14em;
  color:var(--ink-faint); cursor:pointer; border-right:1px solid var(--line);
  background:var(--paper); }
.rail-corpo { margin-left:1.6rem; display:flex; flex-direction:column; gap:.55rem; }
.rail textarea { width:100%; min-height:5.5rem; resize:vertical;
  border:1px solid var(--line); background:var(--paper); color:var(--ink);
  font:.78rem/1.5 var(--sans); padding:.4rem .5rem; box-sizing:border-box; }
.rail .aviso { font-size:.66rem; line-height:1.45; color:var(--ink-faint); }
.rail .aviso s { opacity:.7; }
.rail .curtir { display:flex; align-items:center; gap:.5rem; }
@media (max-width:1180px) { .rail { top:auto; bottom:0; } }
@media print { .rail, .wsbar, .mbtabs { display:none; } }
"""


def _e(s: str) -> str:
    return _html.escape(str(s), quote=True)


def html_topbar(modo: str) -> str:
    return f"""
  <div class="wsbar" id="wsbar">
    <span class="chip-modo" title="decisão 260824: um modo só — o melhor resultado sem gasto à toa (troca futura: linha MODO: no META.md)">modo: {_e(modo)}</span>
    <span class="ws-grupo"><span class="label">fonte</span>
      <button class="wsbtn" data-ws="fonte-" type="button" title="diminuir fonte">A−</button>
      <button class="wsbtn" data-ws="fonte+" type="button" title="aumentar fonte">A+</button></span>
    <span class="ws-grupo"><span class="label">densidade</span>
      <button class="wsbtn" data-ws="dens" data-v="compacta" type="button">compacta</button>
      <button class="wsbtn" data-ws="dens" data-v="normal" type="button">normal</button>
      <button class="wsbtn" data-ws="dens" data-v="ampla" type="button">ampla</button></span>
    <span class="ws-salvo" id="ws-salvo" title="abas fixadas, aba ativa, fonte e densidade ficam salvas neste navegador">workspace salvo automaticamente</span>
  </div>"""


def tabs_nav() -> str:
    botoes = "".join(
        f'<span class="tab" role="button" tabindex="0" data-tab="{i}">{r}'
        f'<span class="pin" data-pin="{i}" title="fixar: abre lado a lado com a aba ativa">＋</span></span>'
        for i, r in ABAS)
    return f'<nav class="mbtabs" id="mbtabs">{botoes}</nav>'


def pane_abre(ident: str) -> str:
    rotulo = dict(ABAS).get(ident, ident)
    return (f'<section class="pane" data-pane="{ident}" id="pane-{ident}">'
            f'<h2 class="pane-tit faixa">{rotulo}</h2>')


def pane_fecha() -> str:
    return "</section>"


def modo_atual(c: Path) -> str:
    texto = u.safe_read_text(u.achar(c, "META.md")) or ""
    m = re.search(r"^MODO:\s*(\w+)", texto, re.MULTILINE | re.IGNORECASE)
    return (m.group(1).lower() if m else "otimizado")


def acoes_lista(c: Path) -> list[dict]:
    """Os .cmd de 01_acoes com a 1ª linha de comentário como descrição."""
    base = u.pasta(c, "scripts")
    itens = []
    if not base.is_dir():
        return itens
    for f in sorted(base.glob("*.cmd")):
        desc = ""
        texto = u.safe_read_text(f) or ""
        for linha in texto.splitlines():
            s = linha.strip()
            if s.lower().startswith("rem ") and len(s) > 8 and "=====" not in s:
                desc = s[4:].strip()
                break
        itens.append({"nome": f.name, "rel": f"{base.name}\\{f.name}", "desc": desc})
    return itens


def html_acoes(itens: list[dict]) -> str:
    if not itens:
        return '<p class="slot__vazio">nenhum .cmd encontrado em 01_acoes/</p>'
    cards = "".join(
        f'<div class="acao"><b>{_e(i["nome"].replace("260824_", "").replace(".cmd", "").replace("-", " "))}</b>'
        f'<span class="cam">{_e(i["rel"])}</span>'
        f'<span class="desc">{_e(i["desc"] or "—")}</span>'
        f'<span class="linha-botao"><button class="wsbtn" data-copiar="{_e(i["rel"])}" type="button">copiar caminho</button>'
        f'<span class="det">2 cliques no arquivo executam</span></span></div>'
        for i in itens)
    return (f'<div class="acoes-lista">{cards}</div>'
            '<p class="det" style="margin-top:.8rem">Página de navegador não pode executar programa no seu PC '
            '(proteção do sistema). O botão copia o caminho; o clique-que-executa chega com a integração do '
            'Neuron (spec §6). Ordem do envio pro GitHub: <b>publicar e fotografar</b> → <b>enviar pro github</b>.</p>')


def skills_lista(c: Path) -> list[dict]:
    itens = []
    base = c / "skills"
    if not base.is_dir():
        return itens
    for d in sorted(base.iterdir()):
        sk = d / "SKILL.md"
        if not sk.is_file():
            continue
        texto = u.safe_read_text(sk) or ""
        m = re.search(r"^description:\s*(.+)$", texto, re.MULTILINE)
        desc = (m.group(1).strip() if m else "")
        ponto = desc.find(". ")
        if ponto > 40:
            desc = desc[:ponto + 1]
        itens.append({"nome": d.name, "desc": desc[:220]})
    return itens


def html_skills(itens: list[dict]) -> str:
    if not itens:
        return '<p class="slot__vazio">nenhuma skill encontrada em skills/</p>'
    cards = "".join(
        f'<div class="skillcard"><b>/{_e(i["nome"])}</b>'
        f'<span class="desc">{_e(i["desc"] or "—")}</span>'
        f'<span class="cam">skills\\{_e(i["nome"])}\\SKILL.md</span></div>'
        for i in itens)
    return (f'<div class="skills-lista">{cards}</div>'
            '<p class="det" style="margin-top:.8rem">Os poderes do megabrain: digite o comando no chat '
            '(ex.: <code>/megabrain</code>, <code>/ingerir</code>, <code>/registrar-licao</code>) '
            'ou descreva a tarefa — a skill certa acorda sozinha.</p>')


def html_esquema() -> str:
    """Central → GitHub → usuário → projetos, na linguagem visual do tema.
    A versão didática completa (43 boards) é 03_docs/260824_megabrain-do-zero.html."""
    return """
<div class="esq">
  <div class="esq-row">
    <div class="esq-tile forte"><b>sua central</b><small>MEGA B R A I N — a matriz do mundo: a única onde o megabrain é editado</small></div>
    <span class="esq-seta">→</span>
    <div class="esq-tile"><b>GitHub</b><small>a versão pública + todas as fotos antigas (sem nada pessoal)</small></div>
    <span class="esq-seta">→</span>
    <div class="esq-tile"><b>central do usuário</b><small>clone no PC de cada pessoa; identidade e cérebro dela nascem vazios e são só dela</small></div>
    <span class="esq-seta">→</span>
    <div class="esq-tile"><b>megabrain do projeto</b><small>a pasta MEGABRAIN\\ dentro de cada projeto: trava a versão, roda sozinho, se atualiza. Não é backup nem lugar de editar</small></div>
  </div>
  <div class="esq-row">
    <span class="esq-rotulo">desce</span>
    <div class="esq-tile ok"><b>automático</b><small>regras, skill, scripts, referências — matriz → GitHub → centrais → projetos, no sync</small></div>
    <span class="esq-rotulo">sobe</span>
    <div class="esq-tile ok"><b>peneirado</b><small>lição generalizada, SEM dados pessoais, como proposta que o dono aprova (opt-in)</small></div>
    <span class="esq-rotulo">nunca sobe</span>
    <div class="esq-tile alerta"><b>o pessoal</b><small>identidade, cérebro, pessoas, dna\\usuario\\ — morre na máquina de cada um</small></div>
  </div>
  <div class="esq-row">
    <div class="esq-tile"><b>memoria\\</b><small>o que a IA lê pra lembrar: nucleo (regras e lições) · estado (onde paramos) · identidade · cerebro (raw → wiki) · pendencias</small></div>
    <div class="esq-tile"><b>02_entrada\\</b><small>jogue fontes aqui (PDF, print, briefing) → /ingerir destila pro cérebro</small></div>
    <div class="esq-tile"><b>máquina</b><small>bin, dna, skills, referencias, modelos, tests, plugins — você nunca precisa abrir</small></div>
    <div class="esq-tile"><b>dna\\usuario\\</b><small>backup imaculado local das suas infos pessoais — intocável, fora do git</small></div>
  </div>
  <p class="det">A explicação completa, board por board: <code>03_docs\\260824_megabrain-do-zero.html</code> (43 boards, setas ↑↓).</p>
</div>"""


def html_rail() -> str:
    return """
  <aside class="rail fechado" id="rail" aria-label="feedback">
    <span class="rail-alca" id="rail-alca" role="button" tabindex="0">feedback</span>
    <div class="rail-corpo">
      <span class="label">feedback rápido</span>
      <span class="curtir"><button class="wsbtn" id="btn-curtir" type="button" title="registra um 👍 local">👍 curtir</button><span class="det" id="curtidas">0</span></span>
      <textarea id="fb-texto" placeholder="anota aqui o que incomodou ou brilhou — o rascunho fica salvo sozinho"></textarea>
      <button class="wsbtn" id="fb-copiar" type="button">copiar pra mandar no chat</button>
      <p class="aviso">Nada daqui sai com seus dados: lições e feedback só sobem depois de uma limpeza que
      remove nomes, caminhos e qualquer coisa pessoal — e só se você ativar o envio.
      A gente valoriza demais usuário que <s>mete o pau</s> critica construtivamente:
      este é um projeto independente e solo, e a experiência de quem usa é o que faz ele melhorar.</p>
    </div>
  </aside>"""


def js_workspace() -> str:
    # namespace por caminho do arquivo (mesma lição do seletor de temas)
    return r"""
(function () {
  "use strict";
  document.documentElement.classList.add("js");
  var NS = "mb-ws::" + location.pathname;
  function ler() { try { return JSON.parse(localStorage.getItem(NS)) || {}; } catch (e) { return {}; } }
  function gravar(st) { try { localStorage.setItem(NS, JSON.stringify(st)); } catch (e) {} }
  var st = ler();
  st.ativa = st.ativa || "painel";
  st.fixas = Array.isArray(st.fixas) ? st.fixas : [];
  st.fonte = Math.min(20, Math.max(13, st.fonte || 16));
  st.dens = st.dens || "normal";
  st.curtidas = st.curtidas || 0;

  var tabs = document.querySelectorAll("#mbtabs .tab");
  var panes = document.querySelectorAll(".pane");
  var cont = document.getElementById("panes");

  function aplicar() {
    var visiveis = [st.ativa].concat(st.fixas.filter(function (f) { return f !== st.ativa; }));
    visiveis = visiveis.slice(0, 3);
    panes.forEach(function (p) { p.classList.toggle("on", visiveis.indexOf(p.dataset.pane) !== -1); });
    tabs.forEach(function (t) {
      t.classList.toggle("on", t.dataset.tab === st.ativa);
      t.classList.toggle("fixa", st.fixas.indexOf(t.dataset.tab) !== -1);
      var pin = t.querySelector(".pin");
      if (pin) pin.textContent = st.fixas.indexOf(t.dataset.tab) !== -1 ? "×" : "＋";
    });
    if (cont) cont.dataset.n = String(visiveis.length);
    document.documentElement.style.fontSize = st.fonte + "px";
    document.documentElement.setAttribute("data-dens", st.dens);
    document.querySelectorAll('[data-ws="dens"]').forEach(function (b) {
      b.setAttribute("aria-pressed", b.dataset.v === st.dens ? "true" : "false");
    });
    var c = document.getElementById("curtidas");
    if (c) c.textContent = String(st.curtidas);
    gravar(st);
  }

  tabs.forEach(function (t) {
    t.addEventListener("click", function (ev) {
      if (ev.target.classList.contains("pin")) return;
      st.ativa = t.dataset.tab; aplicar();
    });
    t.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); st.ativa = t.dataset.tab; aplicar(); }
    });
  });
  document.querySelectorAll(".pin").forEach(function (p) {
    p.addEventListener("click", function (ev) {
      ev.stopPropagation();
      var id = p.dataset.pin, i = st.fixas.indexOf(id);
      if (i === -1) st.fixas.push(id); else st.fixas.splice(i, 1);
      aplicar();
    });
  });
  document.querySelectorAll("[data-ws^='fonte']").forEach(function (b) {
    b.addEventListener("click", function () {
      st.fonte += (b.dataset.ws === "fonte+" ? 1 : -1);
      st.fonte = Math.min(20, Math.max(13, st.fonte)); aplicar();
    });
  });
  document.querySelectorAll('[data-ws="dens"]').forEach(function (b) {
    b.addEventListener("click", function () { st.dens = b.dataset.v; aplicar(); });
  });

  function copiar(texto, botao) {
    function feito() { if (botao) { var t = botao.textContent; botao.textContent = "copiado ✓";
      setTimeout(function () { botao.textContent = t; }, 1600); } }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(texto).then(feito, function () { feito(); });
    } else {
      var ta = document.createElement("textarea"); ta.value = texto;
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (e) {}
      document.body.removeChild(ta); feito();
    }
  }
  document.querySelectorAll("[data-copiar]").forEach(function (b) {
    b.addEventListener("click", function () { copiar(b.dataset.copiar, b); });
  });

  var rail = document.getElementById("rail"), alca = document.getElementById("rail-alca");
  if (rail && alca) {
    if (st.railAberto) rail.classList.remove("fechado");
    var alt = function () { rail.classList.toggle("fechado");
      st.railAberto = !rail.classList.contains("fechado"); gravar(st); };
    alca.addEventListener("click", alt);
    alca.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); alt(); } });
  }
  var fb = document.getElementById("fb-texto");
  if (fb) {
    fb.value = st.rascunho || "";
    fb.addEventListener("input", function () { st.rascunho = fb.value; gravar(st); });
  }
  var curtir = document.getElementById("btn-curtir");
  if (curtir) curtir.addEventListener("click", function () { st.curtidas += 1; aplicar(); });
  var fbcp = document.getElementById("fb-copiar");
  if (fbcp) fbcp.addEventListener("click", function () {
    copiar("feedback do relatório (" + new Date().toISOString().slice(0, 16) + "): " + (fb ? fb.value : ""), fbcp);
  });

  aplicar();
})();
"""
