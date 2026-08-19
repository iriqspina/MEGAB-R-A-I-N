#!/usr/bin/env python3
"""
mb-relatorio-vivo.py — RELATORIO-VIVO.html: retrato ao vivo do projeto pro
usuário deixar aberto no navegador enquanto os agentes trabalham (v6).

A página se recarrega sozinha (JS, a cada 15s, preservando o scroll).
Limite declarado: em file:// o navegador não consegue detectar mudança do
arquivo sem um servidor local, então o "ao vivo" é reload em intervalo fixo
— o usuário não aperta F5, mas há até 15s de atraso.

Fontes: PROGRESSO.json (etapas + notas, atualizado via --marcar/--nota),
ESTADO.md, HANDOFF.md (trava), DECISOES.md (últimos títulos), .mb-log/ do
dia, VERSAO.txt.

Uso:
    python bin/mb-relatorio-vivo.py                        # só regenera
    python bin/mb-relatorio-vivo.py --marcar f2.1 feito "detalhe"
    python bin/mb-relatorio-vivo.py --marcar f2.2 fazendo
    python bin/mb-relatorio-vivo.py --nota "comecei a fase 2"

Status válidos: pendente | fazendo | feito | bloqueado
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
from pathlib import Path

import mb_utils as u

u.utf8_console()

RELOAD_SEGUNDOS = 15
STATUS_VALIDOS = {"pendente", "fazendo", "feito", "bloqueado"}
ICONE = {"feito": "✓", "fazendo": "●", "pendente": "○", "bloqueado": "✕"}


def central() -> Path:
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def carregar_progresso(c: Path) -> dict:
    arq = c / "PROGRESSO.json"
    texto = u.safe_read_text(arq)
    if texto:
        try:
            return json.loads(texto)
        except (json.JSONDecodeError, ValueError):
            pass
    return {"projeto": "megabrain", "etapas": [], "notas": []}


def salvar_progresso(c: Path, dados: dict) -> bool:
    dados["atualizado"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    return u.atomic_write_text(c / "PROGRESSO.json",
                               json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def ler_trava(c: Path):
    texto = u.safe_read_text(c / "HANDOFF.md") or ""
    quem = ate = "-"
    m = re.search(r"^TRAVADO_POR:\s*(.+)$", texto, re.MULTILINE)
    # O bloco do mb-sync fica no fim do arquivo; a última ocorrência vale.
    for m in re.finditer(r"^TRAVADO_POR:\s*(.+)$", texto, re.MULTILINE):
        quem = m.group(1).strip()
    for m in re.finditer(r"^AT[EÉ]:\s*(.+)$", texto, re.MULTILINE):
        ate = m.group(1).strip()
    return quem, ate


def ultimas_decisoes(c: Path, n=3):
    texto = u.safe_read_text(c / "DECISOES.md") or ""
    titulos = re.findall(r"^## (.+)$", texto, re.MULTILINE)
    return titulos[-n:][::-1]


def eventos_hoje(c: Path, n=12):
    arq = c / ".mb-log" / f"eventos-{dt.datetime.now():%y%m%d}.jsonl"
    texto = u.safe_read_text(arq)
    if not texto:
        return []
    linhas = []
    for bruta in texto.splitlines()[-n:]:
        try:
            ev = json.loads(bruta)
        except (json.JSONDecodeError, ValueError):
            continue
        resumo = ev.get("prompt") or ev.get("arquivo") or ev.get("evento") or ""
        if isinstance(resumo, str) and len(resumo) > 90:
            resumo = resumo[:90] + "…"
        linhas.append((ev.get("ts", "")[11:19], ev.get("agente", "?"),
                       ev.get("evento", "?"), resumo))
    return linhas[::-1]


def fila_pendentes(c: Path) -> list[dict]:
    """alteracoes-pendentes/ com dono + idade (v6 fase 4: fila sem dono era
    um dos 7 problemas de lógica do diagnóstico)."""
    base = c / "alteracoes-pendentes"
    fila = []
    if not base.is_dir():
        return fila
    hoje = dt.date.today()
    for pasta in sorted(base.iterdir()):
        if not pasta.is_dir():
            continue
        dono = None
        for md in sorted(pasta.glob("*.md")):
            texto = u.safe_read_text(md) or ""
            m = re.search(r"^DONO:\s*(.+)$", texto, re.MULTILINE)
            if m:
                dono = m.group(1).strip()
                break
        m = re.match(r"(\d{6})", pasta.name)
        if m:
            try:
                d = dt.datetime.strptime(m.group(1), "%y%m%d").date()
            except ValueError:
                d = dt.date.fromtimestamp(pasta.stat().st_mtime)
        else:
            d = dt.date.fromtimestamp(pasta.stat().st_mtime)
        fila.append({"pasta": pasta.name, "dono": dono,
                     "idade": (hoje - d).days})
    fila.sort(key=lambda x: -x["idade"])
    return fila


def gerar_html(c: Path) -> bool:
    e = html.escape
    prog = carregar_progresso(c)
    etapas = prog.get("etapas", [])
    notas = prog.get("notas", [])[-30:][::-1]
    feitas = sum(1 for x in etapas if x.get("status") == "feito")
    pct = round(100 * feitas / len(etapas)) if etapas else 0
    quem, ate = ler_trava(c)
    versao = u.read_first_non_empty_line(c / "VERSAO.txt") or "?"
    estado = (u.safe_read_text(c / "ESTADO.md") or "").strip()
    tldr = ""
    m = re.search(r"TL;DR:(.*?)(?:\n\n|\Z)", estado, re.DOTALL)
    if m:
        tldr = " ".join(m.group(1).split())
    agora = dt.datetime.now()

    linhas_etapas = []
    for et in etapas:
        st = et.get("status", "pendente")
        detalhe = et.get("detalhe") or ""
        ts = (et.get("ts") or "")[11:16]
        linhas_etapas.append(
            f'<li class="etapa etapa--{e(st)}"><span class="ic">{ICONE.get(st, "○")}</span>'
            f'<div><strong>{e(et.get("titulo", et.get("id", "?")))}</strong>'
            f'{f" <span class=ts>{e(ts)}</span>" if ts and st == "feito" else ""}'
            f'{f"<br><span class=det>{e(detalhe)}</span>" if detalhe else ""}</div></li>'
        )

    linhas_notas = "".join(
        f'<li><span class="ts">{e((n.get("ts") or "")[11:19])}</span> {e(n.get("texto", ""))}</li>'
        for n in notas
    ) or "<li class=det>sem notas ainda</li>"

    linhas_ev = "".join(
        f"<tr><td>{e(h)}</td><td>{e(ag)}</td><td>{e(ev)}</td><td>{e(res)}</td></tr>"
        for h, ag, ev, res in eventos_hoje(c)
    ) or '<tr><td colspan="4" class="det">nenhum evento hoje</td></tr>'

    linhas_dec = "".join(f"<li>{e(t)}</li>" for t in ultimas_decisoes(c)) or "<li class=det>—</li>"

    fila = fila_pendentes(c)
    linhas_fila = "".join(
        f'<tr{" style=background:var(--signal-soft)" if item["idade"] >= 7 or not item["dono"] else ""}>'
        f'<td>{e(item["pasta"])}</td>'
        f'<td>{e(item["dono"] or "SEM DONO")}</td>'
        f'<td>{item["idade"]}d</td></tr>'
        for item in fila
    ) or '<tr><td colspan="3" class="det">fila vazia</td></tr>'

    pagina = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MEGABRAIN — relatório vivo</title>
<style>
:root {{
  --paper:#f2efe7; --paper-high:#fffdf8; --ink:#171716; --ink-soft:#55544f;
  --ink-faint:#68665f; --line:#cec9bc; --signal:#a63025; --signal-soft:#f1d8d1;
  --ok:#23613e; --ok-soft:#dce9df; --info:#245d7c; --info-soft:#dce9ef;
  --mono:ui-monospace,"SFMono-Regular",Consolas,"Liberation Mono",monospace;
  --sans:Arial,Helvetica,sans-serif;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink); font:16px/1.5 var(--sans); }}
.wrap {{ max-width:64rem; margin-inline:auto; padding:clamp(1.25rem,4vw,2.5rem); }}
header {{ border-bottom:2px solid var(--ink); padding-bottom:1rem; margin-bottom:1.5rem; }}
h1 {{ margin:.3rem 0 .2rem; font-size:clamp(1.8rem,5vw,2.8rem); line-height:.95; letter-spacing:-.05em; }}
h2 {{ margin:2rem 0 .6rem; font-size:1.15rem; letter-spacing:-.03em; }}
.eyebrow,.label {{ color:var(--signal); font:800 .66rem/1.3 var(--mono); letter-spacing:.1em; text-transform:uppercase; }}
.meta {{ color:var(--ink-faint); font:.68rem/1.5 var(--mono); }}
.pulse {{ display:inline-flex; align-items:center; gap:.4rem; }}
.pulse::before {{ content:""; width:.5rem; height:.5rem; border-radius:50%; background:#2e8c57; box-shadow:0 0 0 .22rem rgb(46 140 87 / 18%); }}
.barra {{ height:.7rem; border:1px solid var(--ink); background:var(--paper-high); margin:.6rem 0 .2rem; }}
.barra > div {{ height:100%; background:var(--ok); width:{pct}%; }}
.etapas {{ margin:0; padding:0; list-style:none; border:1px solid var(--line); background:var(--paper-high); }}
.etapa {{ display:flex; gap:.7rem; padding:.55rem .8rem; border-bottom:1px solid var(--line); }}
.etapa:last-child {{ border-bottom:0; }}
.ic {{ font:800 1rem/1.4 var(--mono); width:1.2rem; text-align:center; }}
.etapa--feito .ic {{ color:var(--ok); }}
.etapa--feito strong {{ color:var(--ink-soft); font-weight:600; }}
.etapa--fazendo {{ background:var(--info-soft); }}
.etapa--fazendo .ic {{ color:var(--info); animation:pisca 1.2s infinite; }}
.etapa--bloqueado {{ background:var(--signal-soft); }}
.etapa--bloqueado .ic {{ color:var(--signal); }}
.etapa--pendente .ic {{ color:var(--ink-faint); }}
@keyframes pisca {{ 50% {{ opacity:.25; }} }}
.det {{ color:var(--ink-soft); font-size:.82rem; }}
.ts {{ color:var(--ink-faint); font:.66rem/1.4 var(--mono); }}
.notas {{ margin:0; padding:0; list-style:none; border:1px solid var(--line); background:var(--paper-high); max-height:18rem; overflow:auto; }}
.notas li {{ padding:.45rem .8rem; border-bottom:1px solid var(--line); font-size:.88rem; }}
.notas li:last-child {{ border-bottom:0; }}
table {{ width:100%; border-collapse:collapse; background:var(--paper-high); border:1px solid var(--line); }}
th,td {{ padding:.4rem .6rem; border-bottom:1px solid var(--line); text-align:left; font-size:.8rem; }}
th {{ font:800 .62rem/1.3 var(--mono); text-transform:uppercase; letter-spacing:.08em; color:var(--signal); }}
.duo {{ display:grid; grid-template-columns:1fr 1fr; gap:1.25rem; }}
.cartao {{ border:1px solid var(--line); background:var(--paper-high); padding: .9rem 1rem; }}
ul.simples {{ margin:.3rem 0 0; padding-left:1.1rem; font-size:.85rem; color:var(--ink-soft); }}
@media (max-width:44rem) {{ .duo {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <span class="eyebrow">megabrain · retrato ao vivo</span>
    <h1>{e(prog.get("projeto", "megabrain"))}</h1>
    <p class="meta pulse">gerado {agora:%H:%M:%S} · recarrega sozinho a cada {RELOAD_SEGUNDOS}s · versão: {e(versao[:60])}</p>
    {f'<p class="det">{e(tldr)}</p>' if tldr else ""}
  </header>

  <span class="label">progresso — {feitas}/{len(etapas)} etapas ({pct}%)</span>
  <div class="barra"><div></div></div>

  <h2>Etapas</h2>
  <ul class="etapas">{"".join(linhas_etapas)}</ul>

  <h2>Notas da execução</h2>
  <ul class="notas">{linhas_notas}</ul>

  <div class="duo">
    <div>
      <h2>Trava</h2>
      <div class="cartao"><strong>{e(quem)}</strong><br><span class="det">até {e(ate)}</span></div>
      <h2>Últimas decisões</h2>
      <div class="cartao"><ul class="simples">{linhas_dec}</ul></div>
    </div>
    <div>
      <h2>Eventos de hoje (central)</h2>
      <table><thead><tr><th>hora</th><th>agente</th><th>evento</th><th>resumo</th></tr></thead>
      <tbody>{linhas_ev}</tbody></table>
      <h2>Fila alteracoes-pendentes</h2>
      <table><thead><tr><th>nota</th><th>dono</th><th>idade</th></tr></thead>
      <tbody>{linhas_fila}</tbody></table>
      <p class="det">destaque = 7+ dias parada ou sem dono. Nota nova leva linha <code>DONO:</code>.</p>
    </div>
  </div>

  <p class="meta" style="margin-top:2rem">fonte: PROGRESSO.json · ESTADO.md · HANDOFF.md · .mb-log/ · arquivo local, não sobe pro GitHub.<br>
  sem servidor local o navegador não detecta mudança de arquivo — por isso o reload em intervalo fixo, preservando o scroll.</p>
</div>
<script>
(function () {{
  var KEY = "mb-vivo-scroll";
  var s = sessionStorage.getItem(KEY);
  if (s !== null) {{
    window.scrollTo(0, parseInt(s, 10) || 0);
    sessionStorage.removeItem(KEY);
  }}
  setInterval(function () {{
    sessionStorage.setItem(KEY, String(window.scrollY || document.documentElement.scrollTop || 0));
    location.reload();
  }}, {RELOAD_SEGUNDOS * 1000});
}})();
</script>
</body>
</html>
"""
    return u.atomic_write_text(c / "RELATORIO-VIVO.html", pagina)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--marcar", nargs="+", default=None,
                   metavar=("ID STATUS", "DETALHE"),
                   help='ex.: --marcar f2.1 feito "template criado"')
    p.add_argument("--nota", default=None)
    args = p.parse_args()

    c = central()
    prog = carregar_progresso(c)
    agora = dt.datetime.now().astimezone().isoformat(timespec="seconds")

    if args.marcar:
        if len(args.marcar) < 2 or args.marcar[1] not in STATUS_VALIDOS:
            print(f"ERRO: uso --marcar <id> <{'|'.join(sorted(STATUS_VALIDOS))}> [detalhe]")
            return 1
        alvo, status = args.marcar[0], args.marcar[1]
        detalhe = " ".join(args.marcar[2:]) if len(args.marcar) > 2 else None
        achou = False
        for et in prog.get("etapas", []):
            if et.get("id") == alvo:
                et["status"] = status
                et["ts"] = agora
                if detalhe:
                    et["detalhe"] = detalhe
                achou = True
        if not achou:
            print(f"ERRO: etapa '{alvo}' não existe no PROGRESSO.json")
            return 1
        salvar_progresso(c, prog)

    if args.nota:
        prog.setdefault("notas", []).append({"ts": agora, "texto": args.nota})
        salvar_progresso(c, prog)

    if not gerar_html(c):
        return 1
    print(f"relatório vivo: {c / 'RELATORIO-VIVO.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
