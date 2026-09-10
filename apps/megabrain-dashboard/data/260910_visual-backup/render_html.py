"""HTML renderer. The dashboard remains useful outside the native shell."""
from __future__ import annotations

from html import escape
from pathlib import Path

from dashboard_data import display_time


PINK = "#EF3D8F"


def _item(text: str, kind: str = "") -> str:
    return f'<li class="{kind}">{escape(str(text))}</li>'


def render(data: dict) -> str:
    stale = data["stale_projects"]
    projects = "".join(_item(f'{item.get("projeto", "Projeto")} · {item.get("versao", "sem versão")}') for item in stale) or _item("Nenhum projeto atrasado medido.")
    decisions = "".join(_item(item) for item in data["recent_decisions"]) or _item("Nenhuma decisão encontrada.")
    dirty = "Não medido" if data["git_dirty"] is None else str(data["git_dirty"])
    current = "Não medido" if data["projects_current"] is None else str(data["projects_current"])
    total = "Não medido" if data["projects_total"] is None else str(data["projects_total"])
    attention = data["blocker"] if data["blocker"] != "Não medido" else "Sem bloqueio medido. Veja o próximo passo antes de abrir outra frente."
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MEGABRAIN · visão pessoal</title><style>
:root{{--pink:{PINK};--pink-soft:#FFE5F0;--ink:#231B20;--muted:#756A72;--line:#F0DCE6;--paper:#FFF;--wash:#FFF7FB;--ok:#16856A;}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font:15px/1.45 "Segoe UI",Arial,sans-serif}}
main{{max-width:1120px;margin:auto;padding:30px 28px 48px}}.top{{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;margin-bottom:24px}}h1{{font-size:26px;letter-spacing:-.04em;margin:0}}.eyebrow{{color:var(--pink);font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;margin:0 0 5px}}.fresh{{font-size:12px;color:var(--muted);text-align:right}}button{{border:1px solid var(--pink);border-radius:999px;background:#fff;color:var(--pink);font:700 12px inherit;padding:9px 13px;cursor:pointer}}button:hover{{background:var(--pink-soft)}}.hero{{border:1px solid var(--line);background:var(--paper);border-radius:20px;padding:24px;margin-bottom:16px;box-shadow:0 12px 35px #ef3d8f0d}}.hero h2{{font-size:21px;line-height:1.2;letter-spacing:-.03em;margin:0 0 10px}}.hero p{{color:var(--muted);margin:0}}.grid{{display:grid;grid-template-columns:1.25fr .75fr;gap:16px}}.card{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px}}.card h3{{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:0 0 10px}}.focus{{border-left:4px solid var(--pink)}}.focus p{{margin:0;font-size:16px;font-weight:650;line-height:1.35}}.mini{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}.stat{{background:var(--pink-soft);border-radius:11px;padding:12px}}.stat b{{display:block;font-size:20px}}.stat span{{font-size:11px;color:var(--muted)}}ul{{margin:0;padding-left:19px}}li{{margin:0 0 8px;color:#423941}}.wide{{margin-top:16px}}.path{{font:11px ui-monospace,Consolas,monospace;color:var(--muted);overflow-wrap:anywhere}}@media(max-width:700px){{main{{padding:20px 14px}}.top,.grid{{display:block}}.fresh{{text-align:left;margin-top:10px}}.grid>.card{{margin-bottom:12px}}.mini{{margin-top:12px}}}}
</style></head><body><main>
<header class="top"><div><p class="eyebrow">MEGABRAIN · visão pessoal</p><h1>{escape(data['name'])}</h1></div><div class="fresh">Atualizado: {escape(display_time(data['updated_at']))}<br><button onclick="location.reload()">Atualizar agora</button></div></header>
<section class="hero"><p class="eyebrow">Macro · projeto inteiro</p><h2>{escape(data['tldr'])}</h2><p class="path">Fonte acompanhada: {escape(data['root'])}</p></section>
<section class="grid"><div><article class="card focus"><h3>Prioridade · o que precisa de você</h3><p>{escape(attention)}</p></article><article class="card focus wide"><h3>Próximo passo · uma ação por vez</h3><p>{escape(data['next_step'])}</p><p class="path">Estado: {escape(data['state_path'])}</p></article><article class="card wide"><h3>Micro · novidades e decisões recentes</h3><ul>{decisions}</ul><p class="path">Decisões: {escape(data['decisions_path'])}</p></article></div>
<aside><article class="card"><h3>Visão rápida</h3><div class="mini"><div class="stat"><b>{escape(data['version'])}</b><span>versão</span></div><div class="stat"><b>{escape(str(data['lock']))}</b><span>trava</span></div><div class="stat"><b>{dirty}</b><span>arquivos pendentes</span></div></div></article><article class="card wide"><h3>Macro · projetos e sincronização</h3><div class="mini"><div class="stat"><b>{current}/{total}</b><span>em dia</span></div><div class="stat"><b>{len(stale)}</b><span>atrasados visíveis</span></div><div class="stat"><b>{'central' if data['is_central'] else 'projeto'}</b><span>contexto aberto</span></div></div><ul style="margin-top:14px">{projects}</ul><p class="path">Handoff: {escape(data['handoff_path'])}</p></article></aside></section>
</main></body></html>"""


def write_html(data: dict, target: str | Path) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(data), encoding="utf-8")
    return target
