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
    ("cerebro", "Cérebro"),
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
    base = u.pasta(c, "skills")   # v7.1: motor/skills na central nova
    if not base.is_dir():
        return itens
    try:
        rel_base = base.relative_to(c).as_posix().replace("/", "\\")
    except ValueError:
        rel_base = "skills"
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
        itens.append({"nome": d.name, "desc": desc[:220],
                      "rel": f"{rel_base}\\{d.name}\\SKILL.md"})
    return itens


def html_skills(itens: list[dict]) -> str:
    if not itens:
        return '<p class="slot__vazio">nenhuma skill encontrada em skills/</p>'
    cards = "".join(
        f'<div class="skillcard"><b>/{_e(i["nome"])}</b>'
        f'<span class="desc">{_e(i["desc"] or "—")}</span>'
        f'<span class="cam">{_e(i["rel"])}</span></div>'
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
    <div class="esq-tile alerta"><b>o pessoal</b><small>identidade, cérebro, pessoas, motor\\dna\\usuario\\ — morre na máquina de cada um</small></div>
  </div>
  <div class="esq-row">
    <div class="esq-tile"><b>memoria\\</b><small>o que a IA lê pra lembrar: nucleo (regras e lições) · estado (onde paramos) · identidade · cerebro (raw → wiki) · pendencias</small></div>
    <div class="esq-tile"><b>02_entrada\\</b><small>jogue fontes aqui (PDF, print, briefing) → /ingerir destila pro cérebro</small></div>
    <div class="esq-tile"><b>motor\\</b><small>a máquina numa caixa só: skills, referencias, modelos, dna, tests, dist, plugins, gerenteneuron — você nunca precisa abrir. Só <code>bin\\</code> ficou na raiz (hook externo aponta pra ela)</small></div>
    <div class="esq-tile"><b>motor\\dna\\usuario\\</b><small>backup imaculado local das suas infos pessoais — intocável, fora do git</small></div>
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


# ═══════════════════════════════════════════════════════════════════
# v7.1 (260824) — componente pergunta (.ask) + aba Cérebro
# spec 03_docs/260824_spec-fase2.md §1 (componente pergunta) e §5 (cérebro).
# Lição 260824 do <USUARIO>: rótulo tem que LER como título — linha própria,
# separador embaixo, espaçamento. Nunca inline no meio do texto.
# ═══════════════════════════════════════════════════════════════════

CSS += """
/* ── componente pergunta (.ask): mostra a pergunta que a seção responde ── */
.ask { border-left:3px solid var(--info); background:var(--paper-high);
  padding:.6rem .9rem .7rem; margin:0 0 1.1rem; max-width:60rem;
  color:var(--ink-soft); font-style:italic; font-size:.9rem; line-height:1.5; }
.ask > b:first-child { display:block; font-style:normal; color:var(--info);
  font:800 .78rem/1.4 var(--mono); text-transform:uppercase; letter-spacing:.12em;
  margin:0 0 .45rem; padding-bottom:.35rem; border-bottom:1px solid var(--line); }

/* ── aba Cérebro ──────────────────────────────────────────────── */
.cer-tiles { display:grid; gap:.6rem; grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));
  margin:0 0 1rem; }
.cer-tile { border:1px solid var(--line); background:var(--paper-high); padding:.6rem .75rem; }
.cer-tile .n { display:block; font:800 1.6rem/1.1 var(--mono); }
.cer-tile .r { display:block; font:800 .66rem/1.4 var(--mono); color:var(--ink-faint);
  text-transform:uppercase; letter-spacing:.1em; margin-top:.15rem; }
.cer-tile.alerta { border-color:var(--signal); } .cer-tile.alerta .n { color:var(--signal); }
.cer-tile.ok .n { color:var(--ok); }
.val { font:700 .68rem/1.3 var(--mono); text-transform:uppercase; letter-spacing:.06em;
  border:1px solid var(--line); padding:.1rem .4rem; white-space:nowrap; }
.val--permanente { color:var(--ink-faint); }
.val--vence { color:var(--info); border-color:var(--info); }
.val--vencida { color:var(--signal); border-color:var(--signal); font-weight:800; }
.cer-vault { border:1px solid var(--line); border-left:3px solid var(--ok);
  background:var(--paper-high); padding:.7rem .9rem; margin:1rem 0 0; }
.cer-vault b { display:block; font:800 .78rem/1.4 var(--mono); text-transform:uppercase;
  letter-spacing:.1em; margin-bottom:.35rem; padding-bottom:.3rem; border-bottom:1px solid var(--line); }
"""


def html_ask(pergunta: str, rotulo: str = "você perguntou") -> str:
    """Caixa que mostra a PERGUNTA que a seção abaixo responde (padrão .ask,
    validado por ele em 260824: "isso me ajudou mt")."""
    return f'<div class="ask"><b>{_e(rotulo)}</b>{_e(pergunta)}</div>'


def _validade(texto: str):
    """VALIDADE: YYMMDD | YYYY-MM | YYYY-MM-DD no front-matter → date|None.
    Mesma convenção do bin/mb-manutencao-cerebro.py (spec §5)."""
    import datetime as _dt
    m = re.search(r"^VALIDADE:\s*([0-9]{2,4}[-/]?[0-9]{2}[-/]?[0-9]{0,2})\s*$",
                  texto[:2000], re.I | re.M)
    if not m:
        return None
    s = m.group(1).strip().replace("/", "-")
    try:
        if re.fullmatch(r"[0-9]{6}", s):
            return _dt.date(2000 + int(s[:2]), int(s[2:4]), int(s[4:6]))
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", s):
            return _dt.date.fromisoformat(s)
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}", s):
            a, mes = int(s[:4]), int(s[5:7])
            prox = _dt.date(a + (mes == 12), (mes % 12) + 1, 1)
            return prox - _dt.timedelta(days=1)
    except ValueError:
        return None
    return None


def cerebro_dados(c: Path) -> dict:
    """Retrato do cérebro: páginas do wiki (com validade), cards de pessoas,
    fontes raw, o que está parado em 02_entrada e a última manutenção."""
    import datetime as _dt
    import json as _json
    hoje = _dt.date.today()
    cer = u.pasta(c, "cerebro")
    d = {"wiki": [], "pessoas": 0, "raw": 0, "entrada": [], "vencidas": 0,
         "a_vencer": 0, "ultima_manutencao": "—", "caminho": str(cer)}
    if cer.is_dir():
        w = cer / "wiki"
        if w.is_dir():
            for f in sorted(w.rglob("*.md")):
                texto = u.safe_read_text(f) or ""
                val = _validade(texto)
                if val is None:
                    estado, rotulo = "permanente", "permanente"
                elif val < hoje:
                    estado, rotulo = "vencida", f"vencida em {val.isoformat()}"
                    d["vencidas"] += 1
                else:
                    dias = (val - hoje).days
                    estado, rotulo = "vence", f"vence em {dias}d"
                    if dias <= 14:
                        d["a_vencer"] += 1
                titulo = ""
                for linha in texto.splitlines():
                    if linha.startswith("# "):
                        titulo = linha[2:].strip()
                        break
                d["wiki"].append({"arq": f.name, "titulo": titulo or f.stem,
                                  "estado": estado, "rotulo": rotulo})
        d["pessoas"] = len(list((cer / "pessoas").glob("*.md"))) if (cer / "pessoas").is_dir() else 0
        d["raw"] = len(list((cer / "raw").glob("*.md"))) if (cer / "raw").is_dir() else 0
    entrada = c / "02_entrada"
    if entrada.is_dir():
        for f in sorted(entrada.iterdir()):
            if f.is_file() and f.name.lower() != "leiame.md":
                idade = (hoje - _dt.date.fromtimestamp(f.stat().st_mtime)).days
                d["entrada"].append({"nome": f.name, "idade": idade})
    stamp = c / ".mb-log" / "manutencao-cerebro.json"
    if stamp.is_file():
        try:
            d["ultima_manutencao"] = _json.loads(stamp.read_text(encoding="utf-8")).get("ultima", "—")
        except (OSError, ValueError):
            pass
    return d


def html_cerebro(d: dict) -> str:
    esquecidas = [x for x in d["entrada"] if x["idade"] > 14]
    tiles = (
        f'<div class="cer-tile"><span class="n">{len(d["wiki"])}</span><span class="r">páginas no wiki</span></div>'
        f'<div class="cer-tile"><span class="n">{d["pessoas"]}</span><span class="r">cards de pessoas</span></div>'
        f'<div class="cer-tile"><span class="n">{d["raw"]}</span><span class="r">fontes guardadas (raw)</span></div>'
        f'<div class="cer-tile{" alerta" if d["entrada"] else ""}"><span class="n">{len(d["entrada"])}</span>'
        f'<span class="r">esperando na entrada</span></div>'
        f'<div class="cer-tile{" alerta" if d["vencidas"] else " ok"}"><span class="n">{d["vencidas"]}</span>'
        f'<span class="r">páginas vencidas</span></div>'
    )
    linhas = "".join(
        f'<tr><td><code>{_e(x["arq"])}</code></td><td>{_e(x["titulo"])}</td>'
        f'<td><span class="val val--{x["estado"]}">{_e(x["rotulo"])}</span></td></tr>'
        for x in d["wiki"]) or '<tr><td colspan="3" class="det">wiki vazio — jogue uma fonte em 02_entrada e rode /ingerir</td></tr>'
    linhas_ent = "".join(
        f'<tr{" style=background:var(--signal-soft)" if x["idade"] > 14 else ""}>'
        f'<td><code>{_e(x["nome"])}</code></td><td>{x["idade"]}d parada</td></tr>'
        for x in d["entrada"]) or '<tr><td colspan="2" class="det">nada parado na entrada</td></tr>'
    return (
        html_ask("o que a IA já sabe dos meus assuntos — e o que está vencendo?") +
        f'<div class="cer-tiles">{tiles}</div>'
        '<h3 class="slot__tit">Páginas do wiki — permanente × temporário</h3>'
        f'<table><thead><tr><th>arquivo</th><th>tópico</th><th>validade</th></tr></thead><tbody>{linhas}</tbody></table>'
        '<p class="det">Página sem <code>VALIDADE:</code> é permanente. Com data, ela avisa antes de virar '
        'informação velha — quem arquiva é você, rodando <code>bin\\mb-manutencao-cerebro.py --arquivar</code>. '
        'Nunca apaga: vai pra <code>90_arquivo\\cerebro-vencido\\</code>.</p>'
        '<h3 class="slot__tit" style="margin-top:1.2rem">Fila de entrada — fontes esperando /ingerir</h3>'
        f'<table><thead><tr><th>arquivo</th><th>parado há</th></tr></thead><tbody>{linhas_ent}</tbody></table>'
        f'<p class="det">{len(esquecidas)} fonte(s) esquecida(s) (mais de 14 dias). '
        f'Última manutenção do cérebro: <b>{_e(d["ultima_manutencao"])}</b>.</p>'
        '<div class="cer-vault"><b>abrir o cérebro no Obsidian</b>'
        f'<span class="det">O vault já está apontado pra <code>{_e(d["caminho"])}</code>. '
        'No Obsidian: <i>Open folder as vault</i> → escolha essa pasta (ou 2 cliques em '
        '<code>01_acoes\\03_abrir-cerebro-obsidian.cmd</code>). '
        'A configuração do vault fica local e não sobe pro GitHub.</span></div>')


# ═══════════════════════════════════════════════════════════════════
# v7.1 (260824) — agregador de telemetria no painel (spec §4/§6)
# Lê .mb-log/ pelo bin/mb_telemetria.py. Dado é LOCAL: o painel só mostra.
# ═══════════════════════════════════════════════════════════════════

CSS += """
/* ── telemetria: barras de frequência ─────────────────────────── */
.tel-barras { display:grid; gap:.35rem; margin:.2rem 0 .9rem; }
.tel-linha { display:grid; grid-template-columns:11rem 1fr 3.2rem; align-items:center; gap:.5rem; }
.tel-linha .k { font:700 .74rem/1.3 var(--mono); overflow:hidden; text-overflow:ellipsis;
  white-space:nowrap; }
.tel-linha .b { height:.7rem; background:var(--line); position:relative; }
.tel-linha .b i { display:block; height:100%; background:var(--ink); }
.tel-linha .v { font:.7rem/1.3 var(--mono); color:var(--ink-faint); text-align:right; }
.tel-cols { display:grid; gap:1.1rem; grid-template-columns:repeat(auto-fit,minmax(17rem,1fr)); }
.tel-cols h4 { margin:0 0 .35rem; font:800 .7rem/1.4 var(--mono); text-transform:uppercase;
  letter-spacing:.1em; color:var(--ink-faint); border-bottom:1px solid var(--line);
  padding-bottom:.25rem; }
"""


def telemetria_dados(c: Path) -> dict | None:
    """Agregado de .mb-log/ — None se o módulo não existir nesta instância."""
    try:
        import mb_telemetria as tel
    except ImportError:
        return None
    try:
        d = tel.resumo(c, dias=90)
    except Exception:
        return None
    d["padroes"] = padroes_dados(c)
    return d


def padroes_dados(c: Path) -> dict | None:
    """Última saída de bin/mb-compreensor.py (spec §7). O painel só MOSTRA:
    quem calcula é o compreensor, e nada aqui roda script."""
    import json as _json
    arq = c / ".mb-log" / "padroes.json"
    if not arq.is_file():
        return None
    try:
        return _json.loads(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def html_padroes(p: dict | None) -> str:
    if p is None:
        return ('<h3 class="slot__tit" style="margin-top:1.4rem">Padrões — o que já se repete</h3>'
                '<p class="det">Ainda não rodou. Dois cliques em '
                '<code>01_acoes\\02_compreender-padroes.cmd</code> — ele cruza pendências, '
                'cérebro, docs e visuais e aponta o tema que merece virar modelo.</p>')
    decl, ach = p.get("declarados") or [], p.get("achados") or []
    linhas = "".join(
        f'<tr><td><code>{_e(x["caminho"])}</code></td><td>{_e(x.get("titulo") or x["assunto"])}</td>'
        f'<td>{_e(str(x.get("dias_parado") if x.get("dias_parado") is not None else "—"))}d</td>'
        f'<td><span class="val val--{"ok" if x.get("ja_existe") else "alerta"}">'
        f'{"modelo feito" if x.get("ja_existe") else "sem modelo"}</span></td></tr>' for x in decl)
    linhas += "".join(
        f'<tr><td><code>{_e(a.get("modelo_sugerido", ""))}</code></td><td>{_e(a["termo"])}</td>'
        f'<td>—</td><td><span class="val val--alerta">achado</span></td></tr>' for a in ach)
    if not linhas:
        linhas = ('<tr><td colspan="4" class="det">nada passou da régua — nenhuma pendência '
                  'pedindo template e nenhum tema repetido em tipos diferentes de lugar</td></tr>')
    resumo = p.get("resumo") or {}
    return (
        '<h3 class="slot__tit" style="margin-top:1.4rem">Padrões — o que já se repete e não virou modelo</h3>'
        '<table><thead><tr><th>modelo</th><th>tema</th><th>parado</th><th>estado</th></tr></thead>'
        f'<tbody>{linhas}</tbody></table>'
        f'<p class="det">{resumo.get("itens", 0)} itens varridos · gerado em '
        f'{_e(str(p.get("gerado_em") or "—")[:16].replace("T", " "))} por '
        '<code>bin\\mb-compreensor.py</code>. Relatório completo em '
        '<code>00_painel\\AAMMDD_padroes.md</code>.</p>')


def _barras(contagem: dict, limite: int = 6) -> str:
    itens = list(contagem.items())[:limite]
    if not itens:
        return '<p class="det">— sem registro ainda</p>'
    topo = max(v for _, v in itens) or 1
    linhas = "".join(
        f'<div class="tel-linha"><span class="k" title="{_e(k)}">{_e(k)}</span>'
        f'<span class="b"><i style="width:{max(3, round(100 * v / topo))}%"></i></span>'
        f'<span class="v">{v}</span></div>' for k, v in itens)
    return f'<div class="tel-barras">{linhas}</div>'


def html_telemetria(d: dict | None) -> str:
    if d is None:
        return ('<p class="slot__vazio">telemetria indisponível nesta instância '
                '(falta bin/mb_telemetria.py)</p>')
    if not d.get("eventos"):
        return (html_ask("o que essa central mais usa?") +
                '<p class="slot__vazio">nenhum evento registrado ainda — o caderninho '
                'começa a encher assim que as sessões registrarem '
                '(<code>bin\\mb_telemetria.py --evento sessao --skill ...</code>).</p>' + html_padroes(d.get("padroes")))
    custo = d.get("custo_total_usd") or 0
    tiles = (
        f'<div class="cer-tile"><span class="n">{d["eventos"]}</span><span class="r">eventos registrados</span></div>'
        f'<div class="cer-tile"><span class="n">{len(d.get("dias", {}))}</span><span class="r">dias com registro</span></div>'
        f'<div class="cer-tile"><span class="n">{len(d["por"].get("skill", {}))}</span><span class="r">skills usadas</span></div>'
        f'<div class="cer-tile"><span class="n">{len(d["por"].get("modelo", {}))}</span><span class="r">modelos vistos</span></div>'
        f'<div class="cer-tile"><span class="n">{("US$ " + str(custo)) if custo else "—"}</span>'
        f'<span class="r">custo somado (local)</span></div>')
    cols = "".join(
        f'<div><h4>{rot}</h4>{_barras(d["por"].get(ch, {}))}</div>'
        for ch, rot in (("skill", "skills mais usadas"), ("agente", "quem trabalhou"),
                        ("cliente", "por onde"), ("evento", "tipo de evento")))
    dur = (f' · duração média {d["duracao_media_s"]}s' if d.get("duracao_media_s") else "")
    return (
        html_ask("o que essa central mais usa, quem trabalhou e quanto custou?") +
        f'<div class="cer-tiles">{tiles}</div>'
        f'<div class="tel-cols">{cols}</div>'
        f'<p class="det">Janela: 90 dias · último registro {_e(str(d.get("ultimo") or "—"))}{dur}. '
        'Fonte: <code>.mb-log\\telemetria-*.jsonl</code> + <code>neuron.jsonl</code> + '
        '<code>eventos-*.jsonl</code>. <b>Fica tudo no seu PC</b> — nenhum número sai daqui sem '
        'você ligar o envio, e o que sobe é sempre agregado e sem nome, caminho ou dado pessoal.</p>'
        + html_padroes(d.get("padroes")))
