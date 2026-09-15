#!/usr/bin/env python3
"""
mb-relatorio-reskin.py — veste a pele POP em relatórios de esqueleto antigo.
v1 (260915)

Por que existe: o PADRAO.md (seção "Pele sobre esqueleto antigo") manda que
arquivados e páginas que não valem reconstruir ganhem a pele POP SEM reescrever
o conteúdo histórico. Refazer à mão 30 HTMLs de ~150–300 KB é onde se apaga
uma linha sem perceber; aqui a única coisa escrita é um bloco
<style id="mb-pop-skin"> antes de </head>, e a integridade é PROVADA a cada
arquivo: o HTML sem o bloco tem que ser byte a byte igual ao original sem o
bloco. Se não for, o arquivo não é gravado.

Dois esqueletos conhecidos, detectados por assinatura de classe:
  vivo-antigo  relatório vivo 260825→260915 (.wrap/.versao/.etapas/.mbv-*,
               tokens --paper/--ink e temas data-tema/data-modo)
  glass        caderno 260909 (.report/.evidence-card/.view-toggle)

Modo claro/escuro (vivo-antigo): POP é escuro por padrão e segue o próprio
seletor do esqueleto — "sistema" respeita prefers-color-scheme, "claro" e
"escuro" explícitos (data-modo) mandam. O claro é uma pele POP clara, não o
papel bege antigo.

Idempotente: bloco existente é substituído, nunca duplicado; rodar duas vezes
não muda nada na segunda.

Uso:
    python bin/mb-relatorio-reskin.py --dry-run          # só conta e confere
    python bin/mb-relatorio-reskin.py                    # aplica no padrão
    python bin/mb-relatorio-reskin.py --arquivo X.html [--skin glass]
    python bin/mb-relatorio-reskin.py --contraste        # testa a paleta (WCAG)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mb_utils as u  # noqa: E402

u.utf8_console()

RAIZ = Path(__file__).resolve().parent.parent
PASTA_ARQUIVO = RAIZ / "90_arquivo" / "relatorios-antigos"
GLASS_PADRAO = RAIZ / "00_PARA-VOCE" / "260909_orquestracoes" / "260909_relatorio.html"
# Backup sagrado do vivo antes da POP: nunca tocar, nem com --arquivo.
SAGRADOS = {"260915_0410_RELATORIO_pre-POP.html"}
VERSAO_PELE = "1"

BLOCO_RE = re.compile(r'<style id="mb-pop-skin"[^>]*>.*?</style>\n?', re.S)

# ── paleta (fonte única: o CSS e o teste de contraste leem daqui) ──────────
FUNDO_ESCURO = "#0B0B16"
FUNDO_CLARO = "#F3F1FA"

ESCURO = {
    "--paper": "rgba(11,11,22,.55)",
    "--paper-high": "rgba(28,27,46,.60)",
    "--paper-sunk": "rgba(255,255,255,.05)",
    "--ink": "#F5F4FF", "--ink-soft": "#C9C7E0", "--ink-faint": "#B1AFCB",
    "--line": "rgba(255,255,255,.11)", "--line-strong": "rgba(255,255,255,.24)",
    "--ok": "#3DDC97", "--ok-soft": "rgba(61,220,151,.14)",
    "--info": "#5CC8FF", "--info-soft": "rgba(92,200,255,.14)",
    "--warn": "#FFC53D", "--warn-soft": "rgba(255,197,61,.13)",
    "--signal": "#FF8A7D", "--signal-soft": "rgba(255,122,107,.14)",
    "--ok-dim": "#2FA776", "--bar-bg": FUNDO_ESCURO, "--bar-ink": "#C9C7E0",
    "--bar-line": "rgba(255,255,255,.12)",
    "--brilho-vivo": "0 0 0 1px rgba(92,200,255,.40), 0 0 22px rgba(92,200,255,.25)",
    "--pop-fundo": FUNDO_ESCURO,
    "--pop-sobre-estado": FUNDO_ESCURO,
    "--pop-acento": "#D6A0FF",
    "--pop-brilho-topo": "rgba(206,130,255,.10)",
    "--pop-sombra": "0 14px 38px rgba(0,0,0,.38)",
    "--pop-aurora-1": "rgba(124,58,237,.48)",
    "--pop-aurora-2": "rgba(28,120,246,.36)",
    "--pop-glow": "rgba(190,120,255,.50)",
    "--pop-h1-a": "#FFFFFF", "--pop-h1-b": "#C4B5FD",
    "--pop-halo": "rgba(124,58,237,.50)",
}

CLARO = {
    "--paper": "rgba(255,255,255,.50)",
    "--paper-high": "rgba(255,255,255,.68)",
    "--paper-sunk": "rgba(40,24,110,.05)",
    "--ink": "#15132B", "--ink-soft": "#434160", "--ink-faint": "#514F6C",
    "--line": "rgba(21,19,43,.13)", "--line-strong": "rgba(21,19,43,.28)",
    "--ok": "#05663F", "--ok-soft": "rgba(6,122,79,.08)",
    "--info": "#095A8E", "--info-soft": "rgba(11,107,168,.08)",
    "--warn": "#744A00", "--warn-soft": "rgba(200,140,0,.12)",
    "--signal": "#A52D22", "--signal-soft": "rgba(194,58,46,.08)",
    "--ok-dim": "#3E8F6B", "--bar-bg": "#15132B", "--bar-ink": "#F3F1FA",
    "--bar-line": "rgba(255,255,255,.18)",
    "--brilho-vivo": "0 0 0 1px rgba(11,107,168,.30), 0 0 18px rgba(11,107,168,.18)",
    "--pop-fundo": FUNDO_CLARO,
    "--pop-sobre-estado": "#FFFFFF",
    "--pop-acento": "#5B21B6",
    "--pop-brilho-topo": "rgba(124,58,237,.07)",
    "--pop-sombra": "0 12px 30px rgba(40,24,110,.12)",
    "--pop-aurora-1": "rgba(124,58,237,.18)",
    "--pop-aurora-2": "rgba(28,140,246,.15)",
    "--pop-glow": "rgba(170,110,255,.30)",
    "--pop-h1-a": "#15132B", "--pop-h1-b": "#5B3FD6",
    "--pop-halo": "rgba(124,58,237,.18)",
}

GLASS = {
    "--ink": "#F5F4FF", "--muted": "#B9B7D6", "--accent": "#CE82FF",
    "--pop-menta": "#3DDC97", "--pop-azul": "#5CC8FF",
    "--pop-card": "rgba(25,25,39,.58)",
}


def _tokens(d: dict) -> str:
    return "".join(f"{k}:{v};" for k, v in d.items())


# ── CSS: vivo-antigo ───────────────────────────────────────────────────────
# Especificidade: os temas do esqueleto chegam a (0,2,0)/(0,3,0);
# :root:root:root é (0,3,0) e vem depois na fonte, :root×3[data-modo] é (0,4,0).
CSS_VIVO = """@media screen{
:root:root:root{/*ESCURO*/--r:10px;--sans:"Segoe UI Variable Text","Segoe UI",system-ui,sans-serif;--mono:"Cascadia Mono",ui-monospace,Consolas,monospace;color-scheme:dark;background:var(--pop-fundo)}
@media (prefers-color-scheme: light){:root:root:root:not([data-modo="escuro"]){/*CLARO*/color-scheme:light}}
:root:root:root[data-modo="claro"]{/*CLARO*/color-scheme:light}
:root:root:root[data-modo="escuro"]{/*ESCURO*/color-scheme:dark}
body{background:transparent;color:var(--ink);font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
body::before{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;background:
 radial-gradient(40rem 9rem at 50% -3rem,var(--pop-glow),transparent 72%),
 radial-gradient(62rem 36rem at 12% -8%,var(--pop-aurora-1),transparent 62%),
 radial-gradient(54rem 34rem at 94% 16%,var(--pop-aurora-2),transparent 62%),
 var(--pop-fundo)}
/* vidro */
.etapas,.notas,table,.cartao,.versao,.wsbar,.mbv-kpi,.mbv-sem__grade,.mbv-fluxo__trilho,.mbv-mtz__rolo,
.esq-section,.esq-core,.esq-tile,.cer-tile,.cer-vault,.acao,.skillcard,.ask,.voce,.slot__vazio,.rail,
.panes[data-n="2"] .pane.on,.panes[data-n="3"] .pane.on{border-radius:10px;border-color:var(--line);
 background-image:linear-gradient(180deg,var(--pop-brilho-topo),transparent 3.2rem);
 -webkit-backdrop-filter:blur(14px) saturate(140%);backdrop-filter:blur(14px) saturate(140%);
 box-shadow:var(--pop-sombra),inset 0 1px 0 rgba(255,255,255,.06)}
.mbv-camada,.mbv-raia{-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px)}
.mbv-camada:first-of-type,.mbv-raia:first-of-type{border-radius:10px 10px 0 0}
.mbv-camada:last-of-type,.mbv-raia:last-of-type{border-radius:0 0 10px 10px}
table{border-collapse:separate;border-spacing:0;overflow:hidden}
tbody tr:last-child td{border-bottom:0}
.mbv-mtz__rolo table{box-shadow:none;border-radius:0;backdrop-filter:none;-webkit-backdrop-filter:none}
.mbv-sem__grade,.mbv-kpi,.mbv-fluxo__trilho,.versao,.etapas{overflow:hidden}
.versao{border:1px solid var(--line-strong)}
.versao .big{font-weight:800;color:var(--ink)}
.voce{border:1px solid color-mix(in srgb,var(--signal) 60%,transparent);border-left:4px solid var(--signal)}
.acao{border-left:3px solid var(--pop-acento)}
.acao[open]{border-left-color:var(--signal)}
.esq-core{border:1px solid var(--line-strong)}
.esq-era,.esq-channel,.esq-step,.esq-route,.mbv-item,.esq-proof{border-radius:8px}
.rail{border-radius:10px 0 0 10px}
/* cabeçalho, display pesado com halo */
header{border-bottom:1px solid transparent;border-image:linear-gradient(90deg,var(--pop-acento),var(--info) 45%,transparent) 1}
h1{font-family:"Segoe UI Variable Display","Segoe UI",system-ui,sans-serif;font-weight:800;letter-spacing:-.045em;line-height:1.05;padding-bottom:.12em;margin-bottom:0;
 background:linear-gradient(180deg,var(--pop-h1-a) 30%,var(--pop-h1-b) 92%);-webkit-background-clip:text;background-clip:text;
 color:transparent;-webkit-text-fill-color:transparent;filter:drop-shadow(0 6px 26px var(--pop-halo))}
.eyebrow{color:var(--pop-acento)}
.pulse::before{background:var(--ok);box-shadow:0 0 10px var(--ok)}
.faixa{border-top:1px solid var(--line-strong);color:var(--ink)}
/* controles */
.mbtabs{border-bottom:1px solid var(--line-strong)}
.mbtabs .tab,.wsbtn,.copiar,.sel__b{border-radius:8px}
.mbtabs .tab.on,.wsbtn[aria-pressed="true"]{background:linear-gradient(135deg,#7C3AED,#3B82F6);color:#FFFFFF;border-color:transparent;box-shadow:0 4px 16px rgba(124,58,237,.35)}
.copiar:hover{background:var(--pop-acento);color:var(--pop-sobre-estado);border-color:var(--pop-acento)}
.chip-modo,.pill,.val{border-radius:99px}
.chip-modo{box-shadow:0 0 14px color-mix(in srgb,var(--info) 30%,transparent)}
.barra,.mbv-barra__trilho{border-radius:10px;overflow:hidden}
.mbv-barra__seg{color:var(--pop-sobre-estado)}
.barra>div{background:linear-gradient(90deg,var(--ok),var(--info))}
.tel-linha .b{border-radius:99px;overflow:hidden}
.tel-linha .b i{background:linear-gradient(90deg,#7C3AED,var(--info))}
.mbv-kpi__v,.cer-tile .n,.acao__n,.esq-metric strong{font-weight:800}
[data-tema] .mbv-sem__i--espera{border-style:solid;border-color:var(--line);border-width:0 1px 1px 0}
.etapa--fazendo,.mbv-etapa--ativo{box-shadow:inset 3px 0 0 var(--info)}
a{text-underline-offset:3px}
}"""

# ── CSS: glass (caderno 260909) ────────────────────────────────────────────
CSS_GLASS = """@media screen{
:root:root{/*GLASS*/color-scheme:dark;background:#0B0B16}
body[data-view]{background:transparent;background-image:none;color:var(--ink);font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
body[data-view]::before{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;background:
 radial-gradient(40rem 9rem at 50% -3rem,rgba(190,120,255,.50),transparent 72%),
 radial-gradient(62rem 36rem at 12% -8%,rgba(124,58,237,.55),transparent 62%),
 radial-gradient(54rem 34rem at 94% 16%,rgba(28,120,246,.36),transparent 62%),
 #0B0B16}
body[data-view] .report{border-radius:10px;border:1px solid rgba(255,255,255,.12);
 background:linear-gradient(180deg,rgba(206,130,255,.12),transparent 9rem),var(--pop-card);
 -webkit-backdrop-filter:blur(22px) saturate(140%);backdrop-filter:blur(22px) saturate(140%);
 box-shadow:0 24px 70px rgba(0,0,0,.45),inset 0 1px 0 rgba(255,255,255,.08)}
body[data-view] .header{border-bottom:1px solid transparent;border-image:linear-gradient(90deg,var(--accent),var(--pop-azul) 45%,transparent) 1}
body[data-view] h1{font-weight:800;letter-spacing:-.045em;padding-bottom:.1em;
 background:linear-gradient(180deg,#FFFFFF 30%,#C4B5FD 92%);-webkit-background-clip:text;background-clip:text;
 color:transparent;-webkit-text-fill-color:transparent;filter:drop-shadow(0 6px 26px rgba(124,58,237,.50))}
body[data-view="executive"] h1{font-family:"Segoe UI Variable Display","Segoe UI",system-ui,sans-serif}
body[data-view] .kicker{color:var(--accent)}
body[data-view] .badge{border-radius:99px;border-color:rgba(61,220,151,.45);color:var(--pop-menta);background:rgba(61,220,151,.10)}
body[data-view] .view-toggle{border-radius:10px;background:rgba(11,11,22,.55);border-color:rgba(255,255,255,.12)}
body[data-view] .btn{border-radius:8px}
body[data-view] .btn[aria-pressed="true"]{background:linear-gradient(135deg,#7C3AED,#3B82F6);color:#FFFFFF;box-shadow:0 4px 16px rgba(124,58,237,.35)}
body[data-view] .verdict-text{color:var(--ink)}
body[data-view] .meta{border-left-color:rgba(255,255,255,.12)}
body[data-view] .base-list b{color:var(--pop-menta);font-weight:800}
body[data-view] .prioridades li{border-top-color:rgba(255,255,255,.10)}
body[data-view] .prioridades li:before{color:var(--accent);font-weight:800}
body[data-view] .flow-line li:not(:last-child):after{color:var(--pop-azul)}
body[data-view] .evidences{border-radius:10px;border:1px solid rgba(255,255,255,.11);padding:20px;
 background:linear-gradient(180deg,rgba(92,200,255,.08),transparent 5rem),rgba(255,255,255,.035)}
body[data-view] .evidence-card{border-top-color:rgba(255,255,255,.10)}
body[data-view] .panel-footer{border-top-color:rgba(255,255,255,.12)}
body[data-view] a:focus-visible,body[data-view] button:focus-visible{outline-color:var(--accent)}
}"""


def css_para(skin: str) -> str:
    if skin == "vivo-antigo":
        return (CSS_VIVO.replace("/*ESCURO*/", _tokens(ESCURO))
                        .replace("/*CLARO*/", _tokens(CLARO)))
    if skin == "glass":
        return CSS_GLASS.replace("/*GLASS*/", _tokens(GLASS))
    raise ValueError(f"skin desconhecido: {skin}")


def bloco_para(skin: str) -> str:
    return (f'<style id="mb-pop-skin" data-skin="{skin}" data-versao="{VERSAO_PELE}">'
            f"\n/* pele POP — bin/mb-relatorio-reskin.py; conteúdo histórico intocado */\n"
            f"{css_para(skin)}\n</style>\n")


# ── núcleo ─────────────────────────────────────────────────────────────────
HTML_TAG_RE = re.compile(r'<html\b[^>]*>')

def sem_tema(html: str) -> str:
    """Remove data-tema do <html> — a flag --tema muda o atributo FORA do
    bloco de pele, então a integridade combinada compara sem os dois."""
    m = HTML_TAG_RE.search(html)
    if not m:
        return html
    return html[:m.start()] + re.sub(r'\s+data-tema="[^"]*"', "", m.group(0)) + html[m.end():]

def sem_pele(html: str) -> str:
    return BLOCO_RE.sub("", html)

def aplicar_tema(html: str, tema: str) -> str:
    """Grava data-tema="claro" no <html> (tema claro) ou remove (escuro)."""
    m = HTML_TAG_RE.search(html)
    if not m:
        raise ValueError("sem <html>")
    limpo = re.sub(r'\s+data-tema="[^"]*"', "", m.group(0))
    novo_tag = limpo[:-1] + ' data-tema="claro">' if tema == "claro" else limpo
    return html[:m.start()] + novo_tag + html[m.end():]


def detectar(html: str) -> str | None:
    h = sem_pele(html)
    if 'class="report"' in h and ("evidence-card" in h or "view-toggle" in h):
        return "glass"
    if 'class="wrap"' in h and ('class="versao"' in h or 'class="etapas"' in h or 'class="mbv-' in h):
        return "vivo-antigo"
    return None


def aplicar(html: str, skin: str) -> str:
    """Devolve o HTML com o bloco da pele antes do </head> do documento."""
    base = sem_pele(html)
    corpo = re.search(r"<body\b", base, re.I)
    limite = corpo.start() if corpo else len(base)
    fechos = [m.start() for m in re.finditer(r"</head\s*>", base[:limite], re.I)]
    if not fechos:
        raise ValueError("sem </head> antes do <body>")
    pos = fechos[-1]
    return base[:pos] + bloco_para(skin) + base[pos:]


def integro(original: str, novo: str, tema_mudou: bool = False) -> bool:
    base = (lambda h: sem_tema(sem_pele(h))) if tema_mudou else sem_pele
    return base(original) == base(novo) and novo.count('id="mb-pop-skin"') == 1


def alvos_padrao() -> list[Path]:
    arqs = sorted(p for p in PASTA_ARQUIVO.glob("*.html") if p.name not in SAGRADOS)
    if GLASS_PADRAO.is_file():
        arqs.append(GLASS_PADRAO)
    return arqs


def processar(caminho: Path, skin_forcado: str | None, seco: bool,
              tema: str | None = None) -> tuple[str, str]:
    """Retorna (skin|'-', estado). Estados: novo, substituido, igual, pulado:<motivo>."""
    if caminho.name in SAGRADOS:
        return "-", "pulado:backup sagrado"
    bruto = caminho.read_bytes()
    try:
        html = bruto.decode("utf-8")
    except UnicodeDecodeError:
        return "-", "pulado:não é UTF-8"
    skin = skin_forcado or detectar(html)
    if not skin:
        return "-", "pulado:esqueleto não reconhecido"
    try:
        novo = aplicar(html, skin)
        if tema is not None:
            novo = aplicar_tema(novo, tema)
    except ValueError as e:
        return skin, f"pulado:{e}"
    if not integro(html, novo, tema_mudou=tema is not None):
        return skin, "pulado:FALHA DE INTEGRIDADE"
    if novo == html:
        return skin, "igual"
    estado = "substituido" if 'id="mb-pop-skin"' in html else "novo"
    if tema is not None:
        estado += f" · data-tema {'gravado' if tema == 'claro' else 'removido'}"
    if not seco:
        caminho.write_bytes(novo.encode("utf-8"))
        if not integro(html, caminho.read_bytes().decode("utf-8")):
            caminho.write_bytes(bruto)
            return skin, "pulado:FALHA DE INTEGRIDADE pós-gravação (original restaurado)"
    return skin, estado


# ── contraste WCAG sobre a paleta real (com vidro composto) ────────────────
def _rgba(c: str) -> tuple[float, float, float, float]:
    c = c.strip()
    if c.startswith("#"):
        h = c[1:]
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0
    r, g, b, a = (float(x) for x in re.findall(r"[\d.]+", c))
    return r, g, b, a


def _sobre(topo: str, fundo: tuple) -> tuple:
    r, g, b, a = _rgba(topo)
    return tuple(a * x + (1 - a) * y for x, y in zip((r, g, b), fundo[:3])) + (1.0,)


def _lum(c: tuple) -> float:
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def razao(texto: str, fundo: tuple) -> float:
    l1, l2 = sorted((_lum(_sobre(texto, fundo)), _lum(fundo)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def checar_contraste(minimo: float = 4.5) -> list[tuple[str, str, str, float]]:
    """Pior caso: texto sobre vidro/estado-suave composto sobre o pico da aurora."""
    linhas = []
    for nome, p in (("escuro", ESCURO), ("claro", CLARO)):
        base = _rgba(p["--pop-fundo"])
        pico = _sobre(p["--pop-aurora-1"], base)
        fundos = {"página": base, "aurora": pico,
                  "cartão@aurora": _sobre(p["--paper-high"], pico)}
        for est in ("signal", "warn", "info", "ok"):
            fundos[f"{est}-soft@cartão"] = _sobre(p[f"--{est}-soft"], fundos["cartão@aurora"])
        for tk in ("--ink", "--ink-soft", "--ink-faint", "--ok", "--info", "--warn", "--signal", "--pop-acento"):
            for fn, fc in fundos.items():
                if fn.endswith("-soft@cartão") and tk not in ("--ink", "--ink-soft", "--" + fn.split("-soft")[0]):
                    continue
                linhas.append((nome, tk, fn, razao(p[tk], fc)))
        for est in ("--ok", "--info", "--warn", "--signal"):
            linhas.append((nome, "--pop-sobre-estado", f"barra {est}", razao(p["--pop-sobre-estado"], _rgba(p[est]))))
    base = _rgba("#0B0B16")
    card = _sobre(GLASS["--pop-card"], _sobre("rgba(124,58,237,.55)", base))
    for tk in ("--ink", "--muted", "--accent", "--pop-menta", "--pop-azul"):
        linhas.append(("glass", tk, "report@aurora", razao(GLASS[tk], card)))
    return [(*l[:3], round(l[3], 2)) for l in linhas]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Injeta a pele POP em relatórios de esqueleto antigo.")
    ap.add_argument("--dry-run", action="store_true", help="não grava; mostra o que faria")
    ap.add_argument("--arquivo", action="append", type=Path, help="processa só este(s) arquivo(s)")
    ap.add_argument("--skin", choices=("vivo-antigo", "glass"), help="força o skin (sem detecção)")
    ap.add_argument("--tema", choices=("claro", "escuro"), default=None,
                    help="além da pele, grava/remove data-tema=\"claro\" no <html> do alvo (default: nada muda)")
    ap.add_argument("--contraste", action="store_true", help="testa a paleta e sai")
    a = ap.parse_args(argv)

    if a.contraste:
        ruins = 0
        for modo, tk, fundo, r in checar_contraste():
            marca = "ok " if r >= 4.5 else "RUIM"
            ruins += r < 4.5
            print(f"{marca} {modo:7} {tk:20} sobre {fundo:22} {r:5.2f}:1")
        print(f"\n{ruins} par(es) abaixo de 4.5:1")
        return 1 if ruins else 0

    alvos = [p.resolve() for p in a.arquivo] if a.arquivo else alvos_padrao()
    contagem: dict[str, int] = {}
    pulados = falhas = 0
    for p in alvos:
        if not p.is_file():
            print(f"  ✗ não existe: {p}")
            pulados += 1
            continue
        skin, estado = processar(p, a.skin, a.dry_run)
        if estado.startswith("pulado"):
            pulados += 1
            falhas += "INTEGRIDADE" in estado
            print(f"  – {p.name}: {estado}")
            continue
        contagem[skin] = contagem.get(skin, 0) + 1
        print(f"  ✓ {p.name}: {skin} · {estado}")
    total = sum(contagem.values())
    por = " · ".join(f"{k}: {v}" for k, v in sorted(contagem.items())) or "nenhum"
    print(f"\n{'[dry-run] ' if a.dry_run else ''}{total} arquivo(s) com pele ({por}) · {pulados} pulado(s)")
    return 2 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
