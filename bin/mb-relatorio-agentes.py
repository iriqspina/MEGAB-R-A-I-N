#!/usr/bin/env python3
"""
mb-relatorio-agentes.py — agrega os `.mb-log/` de todos os projetos e gera
RELATORIO-AGENTES.html na raiz da central (v6, fase 1).

Por agente/modelo: prompts, sessões, projetos tocados, tokens e custo (quando
o CLI expõe — hoje só o GerenteNeuron), erros e retrabalho (mesmo arquivo
editado 2+ vezes em 24h). "Lições disparadas" chega na fase 3 (índice).

Uso:
    python bin/mb-relatorio-agentes.py [--dias 30] [--saida PATH]

Sem --dias, considera tudo (retenção é sem limite; poda manual).
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
from collections import defaultdict
from pathlib import Path

import mb_utils as u

u.utf8_console()


def central() -> Path:
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def projetos_root() -> Path:
    env = os.environ.get("MEGABRAIN_PROJETOS_ROOT")
    if env:
        return Path(env).resolve()
    return central().parent


def coletar_logs(raiz: Path, c: Path):
    """Yields (nome_projeto, Path do jsonl)."""
    vistos = set()
    try:
        candidatos = sorted(raiz.iterdir())
    except OSError:
        candidatos = []
    for pasta in candidatos:
        log_dir = pasta / ".mb-log"
        if log_dir.is_dir():
            for arq in sorted(log_dir.glob("eventos-*.jsonl")):
                vistos.add(arq.resolve())
                yield pasta.name, arq
    # Subpastas da central que têm .mb-log próprio (ex.: gerenteneuron)
    # e o balde fora-de-projeto.
    for arq in sorted((c / ".mb-log").rglob("eventos-*.jsonl")) if (c / ".mb-log").is_dir() else []:
        if arq.resolve() not in vistos:
            yield "(fora de projeto)", arq
    for sub in sorted(c.iterdir()) if c.is_dir() else []:
        log_dir = sub / ".mb-log"
        if sub.is_dir() and log_dir.is_dir():
            for arq in sorted(log_dir.glob("eventos-*.jsonl")):
                if arq.resolve() not in vistos:
                    yield sub.name, arq


def parse_ts(ts: str):
    try:
        return dt.datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dias", type=int, default=None,
                   help="considera só os últimos N dias (default: tudo)")
    p.add_argument("--saida", default=None)
    args = p.parse_args()

    c = central()
    raiz = projetos_root()
    corte = None
    if args.dias:
        corte = dt.datetime.now().astimezone() - dt.timedelta(days=args.dias)

    agentes = defaultdict(lambda: {
        "prompts": 0, "eventos": 0, "sessoes": set(), "projetos": set(),
        "modelos": defaultdict(int), "tokens_in": 0, "tokens_out": 0,
        "custo": 0.0, "erros": [],
    })
    edicao_arquivo = defaultdict(list)  # (agente, arquivo) -> [ts]
    por_projeto = defaultdict(lambda: defaultdict(int))
    total_linhas = 0
    invalidas = 0

    for projeto, arq in coletar_logs(raiz, c):
        texto = u.safe_read_text(arq)
        if texto is None:
            continue
        for linha in texto.splitlines():
            if not linha.strip():
                continue
            try:
                ev = json.loads(linha)
            except (json.JSONDecodeError, ValueError):
                invalidas += 1
                continue
            ts = parse_ts(ev.get("ts") or "")
            if corte and ts:
                ts_cmp = ts if ts.tzinfo else ts.replace(tzinfo=dt.timezone.utc)
                if ts_cmp < corte:
                    continue
            total_linhas += 1
            nome = ev.get("agente") or "desconhecido"
            a = agentes[nome]
            a["eventos"] += 1
            if ev.get("evento") == "prompt":
                a["prompts"] += 1
            if ev.get("session_id"):
                a["sessoes"].add(ev["session_id"])
            a["projetos"].add(projeto)
            if ev.get("modelo"):
                a["modelos"][ev["modelo"]] += 1
            extra = ev.get("extra") or {}
            a["tokens_in"] += extra.get("tokens_entrada") or 0
            a["tokens_out"] += extra.get("tokens_saida") or 0
            a["custo"] += extra.get("custo_estimado_usd") or 0.0
            if extra.get("erro"):
                a["erros"].append(str(extra["erro"])[:200])
            if ev.get("evento") == "arquivo" and ev.get("arquivo") and ts:
                edicao_arquivo[(nome, ev["arquivo"])].append(ts)
            por_projeto[projeto][nome] += 1

    # Retrabalho: mesmo arquivo editado 2+ vezes num intervalo de 24h.
    retrabalho = defaultdict(set)
    for (nome, arquivo), tss in edicao_arquivo.items():
        tss.sort()
        for i in range(1, len(tss)):
            if (tss[i] - tss[i - 1]) <= dt.timedelta(hours=24):
                retrabalho[nome].add(arquivo)
                break

    agora = dt.datetime.now()
    periodo = f"últimos {args.dias} dias" if args.dias else "todo o histórico"
    e = html.escape

    # v6 fase 2: últimos vereditos de meta-check por projeto.
    vereditos = {}
    for projeto, arq in coletar_logs(raiz, c):
        texto = u.safe_read_text(arq)
        if not texto:
            continue
        for linha in texto.splitlines():
            try:
                ev = json.loads(linha)
            except (json.JSONDecodeError, ValueError):
                continue
            if ev.get("evento") == "meta-check":
                extra = ev.get("extra") or {}
                vereditos[extra.get("projeto") or projeto] = (
                    extra.get("veredito", "?"), extra.get("motivo", ""), ev.get("ts", ""))
    linhas_meta = "".join(
        f"<tr><td>{e(p)}</td><td>{e(v)}</td><td>{e(m[:120])}</td><td>{e(ts[:16])}</td></tr>"
        for p, (v, m, ts) in sorted(vereditos.items())
    )

    # v6 fase 3: candidatas a regra (recorrência 3×+).
    candidatas = []
    rec_txt = u.safe_read_text(c / "dna" / "licoes-recorrencia.json")
    if rec_txt:
        try:
            rec = json.loads(rec_txt)
            candidatas = [cl for cl in rec.get("clusters", []) if cl.get("candidata_a_regra")]
        except (json.JSONDecodeError, ValueError):
            pass
    linhas_cand = "".join(
        f'<li><strong>{cl["n"]}×</strong> — {e(" · ".join(cl["titulos"][:3]))}'
        f'{" …" if len(cl["titulos"]) > 3 else ""}</li>'
        for cl in candidatas
    )

    cards = []
    for nome in sorted(agentes, key=lambda n: -agentes[n]["eventos"]):
        a = agentes[nome]
        modelos = ", ".join(f"{e(m)} ({n}×)" for m, n in
                            sorted(a["modelos"].items(), key=lambda kv: -kv[1])) or "n/d"
        custo = f"US$ {a['custo']:.4f}" if a["custo"] else "n/d"
        tokens = (f"{a['tokens_in']:,} in / {a['tokens_out']:,} out".replace(",", ".")
                  if (a["tokens_in"] or a["tokens_out"]) else "n/d")
        n_retrab = len(retrabalho.get(nome, ()))
        erros_html = ""
        if a["erros"]:
            itens = "".join(f"<li><code>{e(x)}</code></li>" for x in a["erros"][:10])
            mais = f"<li>… +{len(a['erros']) - 10} erro(s)</li>" if len(a["erros"]) > 10 else ""
            erros_html = f'<div class="erros"><span class="label">erros ({len(a["erros"])})</span><ul>{itens}{mais}</ul></div>'
        cards.append(f"""
    <article class="agente">
      <h2>{e(nome)}</h2>
      <div class="grid">
        <div class="metric"><span class="label">prompts</span><span class="valor">{a['prompts']}</span></div>
        <div class="metric"><span class="label">sessões</span><span class="valor">{len(a['sessoes']) or 'n/d'}</span></div>
        <div class="metric"><span class="label">eventos</span><span class="valor">{a['eventos']}</span></div>
        <div class="metric"><span class="label">projetos</span><span class="valor">{len(a['projetos'])}</span></div>
        <div class="metric"><span class="label">tokens</span><span class="valor valor--s">{e(tokens)}</span></div>
        <div class="metric"><span class="label">custo</span><span class="valor valor--s">{e(custo)}</span></div>
        <div class="metric{' metric--alerta' if n_retrab else ''}"><span class="label">retrabalho 24h</span><span class="valor">{n_retrab}</span></div>
        <div class="metric"><span class="label">lições disparadas</span><span class="valor valor--s">n/d (fase 3)</span></div>
      </div>
      <p class="modelos"><span class="label">modelos</span> {modelos}</p>
      {erros_html}
    </article>""")

    linhas_proj = "".join(
        f"<tr><td>{e(proj)}</td>" +
        "".join(f"<td>{cont.get(ag, 0) or '·'}</td>" for ag in sorted(agentes)) + "</tr>"
        for proj, cont in sorted(por_projeto.items(), key=lambda kv: -sum(kv[1].values()))
    )
    cab_proj = "".join(f"<th>{e(ag)}</th>" for ag in sorted(agentes))

    corpo_vazio = ""
    if not agentes:
        corpo_vazio = ('<p class="vazio">Nenhum evento em <code>.mb-log/</code> ainda. '
                       'Os hooks gravam a partir da primeira sessão com o megabrain v6 ativo.</p>')

    pagina = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MEGABRAIN — relatório de agentes</title>
<style>
:root {{
  --paper: #f2efe7; --paper-high: #fffdf8; --ink: #171716; --ink-soft: #55544f;
  --ink-faint: #68665f; --line: #cec9bc; --signal: #a63025; --signal-soft: #f1d8d1;
  --mono: ui-monospace, "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  --sans: Arial, Helvetica, sans-serif;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--paper); color: var(--ink); font: 16px/1.5 var(--sans); }}
.wrap {{ max-width: 72rem; margin-inline: auto; padding: clamp(1.25rem, 4vw, 3rem); }}
header {{ border-bottom: 2px solid var(--ink); padding-bottom: 1rem; margin-bottom: 2rem; }}
h1 {{ margin: .4rem 0 .2rem; font-size: clamp(2rem, 5vw, 3.4rem); line-height: .95; letter-spacing: -.06em; }}
.eyebrow, .label {{ color: var(--signal); font: 800 .66rem/1.3 var(--mono); letter-spacing: .1em; text-transform: uppercase; }}
.meta {{ color: var(--ink-faint); font: .7rem/1.4 var(--mono); }}
.agente {{ border: 1px solid var(--line); background: var(--paper-high); padding: 1.25rem; margin-bottom: 1.5rem; }}
.agente h2 {{ margin: 0 0 1rem; font-size: 1.6rem; letter-spacing: -.04em; }}
.grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; border: 1px solid var(--line); background: var(--line); }}
.metric {{ padding: .9rem; background: var(--paper-high); }}
.metric--alerta {{ background: var(--signal-soft); }}
.valor {{ display: block; margin-top: .4rem; font-size: 1.6rem; letter-spacing: -.04em; }}
.valor--s {{ font-size: .95rem; }}
.modelos {{ color: var(--ink-soft); font-size: .88rem; }}
.erros ul {{ margin: .4rem 0 0; padding-left: 1.2rem; color: var(--ink-soft); font-size: .82rem; }}
table {{ width: 100%; border-collapse: collapse; background: var(--paper-high); border: 1px solid var(--line); }}
th, td {{ padding: .55rem .7rem; border-bottom: 1px solid var(--line); text-align: left; font-size: .88rem; }}
th {{ font: 800 .66rem/1.3 var(--mono); text-transform: uppercase; letter-spacing: .08em; color: var(--signal); }}
.vazio {{ padding: 2rem; border: 1px dashed var(--line); color: var(--ink-soft); }}
code {{ font-family: var(--mono); font-size: .85em; overflow-wrap: anywhere; }}
@media (max-width: 48rem) {{ .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <span class="eyebrow">megabrain · observabilidade · v6 fase 1</span>
    <h1>Relatório de agentes</h1>
    <p class="meta">gerado {agora:%Y-%m-%d %H:%M} · período: {e(periodo)} · {total_linhas} evento(s) válido(s){f" · {invalidas} linha(s) inválida(s) ignorada(s)" if invalidas else ""}</p>
  </header>
  {corpo_vazio}
  {"".join(cards)}
  {f'<h2 style="letter-spacing:-.04em">Atividade por projeto</h2><table><thead><tr><th>projeto</th>{cab_proj}</tr></thead><tbody>{linhas_proj}</tbody></table>' if por_projeto else ""}
  {f'<h2 style="letter-spacing:-.04em">Aderência à meta (mb-checar-meta)</h2><table><thead><tr><th>projeto</th><th>veredito</th><th>motivo</th><th>quando</th></tr></thead><tbody>{linhas_meta}</tbody></table>' if linhas_meta else ""}
  {f'<h2 style="letter-spacing:-.04em">Candidatas a regra (lição 3×+ — recorrência automática)</h2><ul>{linhas_cand}</ul>' if linhas_cand else ""}
  <p class="meta" style="margin-top:2rem">fonte: <code>&lt;projeto&gt;/.mb-log/eventos-*.jsonl</code> · dados locais, nunca sobem pro GitHub (EXCLUIR_TOPO) · retenção sem limite, poda manual (decisão 260819)</p>
</div>
</body>
</html>
"""

    saida = Path(args.saida) if args.saida else c / "RELATORIO-AGENTES.html"
    if not u.atomic_write_text(saida, pagina):
        return 1
    print(f"relatório gerado: {saida}")
    print(f"  agentes: {', '.join(sorted(agentes)) or 'nenhum'} · eventos: {total_linhas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
