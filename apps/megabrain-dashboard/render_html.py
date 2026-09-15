"""Offline presentation of collect(); no measurements are inferred here."""
from __future__ import annotations

import base64
from html import escape
from pathlib import Path
import re

from dashboard_data import display_time

APP = Path(__file__).resolve().parent


def _text(value) -> str:
    return escape(str(value))


def _source(path, label: str) -> str:
    if path and path != "Não encontrado":
        candidate = Path(path)
        if candidate.is_absolute() and candidate.is_file():
            return f'<a href="{_text(candidate.as_uri())}">{_text(label)} <span aria-hidden="true">↗</span></a>'
    return f'<span class="unavailable">{_text(label)} · não encontrado</span>'


def _metric(value) -> str:
    return '<span class="unknown">Não medido</span>' if value is None else f'<span class="num">{_text(value)}</span>'


def render(data: dict, *, native: bool = False) -> str:
    css = (APP / "assets" / "dashboard.css").read_text(encoding="utf-8")
    icon = APP / "assets" / "megabrain-cerebro-rosa.png"
    brand = ''
    if icon.is_file():
        brand = '<img class="brain" alt="" width="44" height="44" src="data:image/png;base64,' + base64.b64encode(icon.read_bytes()).decode("ascii") + '">'
    blocker = str(data["blocker"])
    unknown = blocker.strip().casefold() in {"não medido", "não medida", ""}
    clear = blocker.strip().casefold().rstrip(".") in {"nenhum", "nenhuma", "sem bloqueio"}
    tone = "neutral" if unknown or clear else "blocked"
    status = "Bloqueio não medido" if unknown else "Sem bloqueio informado" if clear else "Pede atenção"
    next_step = str(data["next_step"])
    duplicate = blocker.strip().casefold() == next_step.strip().casefold()
    priority = '' if duplicate else f'<div class="priority"><span class="label">Prioridade registrada</span><p>{_text(blocker)}</p></div>'
    if unknown or clear:
        priority = ''
    action = _text(next_step)
    if next_step == "Não medido":
        action = 'Próximo passo: Não medido'
    decisions = []
    for entry in data["recent_decisions"]:
        raw = str(entry)
        match = re.match(r"^(\d{6}[a-z]*)\s*[—·–-]\s*(.*)$", raw, re.DOTALL)
        stamp, title = (match.group(1), match.group(2)) if match else ("Registro", raw)
        decisions.append(f'<li><span class="stamp">{_text(stamp)}</span><p>{_text(title)}</p></li>')
    news = ''.join(decisions) or '<li class="empty">Nenhuma decisão encontrada nas fontes locais.</li>'
    projects = ''.join(f'<li><span>{_text(item.get("projeto", "Projeto"))}</span><span class="project-version">{_text(item.get("versao") or "Versão não medida")}</span></li>' for item in data["stale_projects"])
    if not projects:
        projects = '<li class="empty">Nenhum atraso listado nesta leitura.</li>' if data["projects_total"] is not None else '<li class="empty">Sincronização: Não medido.</li>'
    lock = str(data["lock"])
    lock_class = 'ok' if lock.strip().casefold() == 'livre' else 'neutral' if lock == 'Não medido' else 'waiting'
    controls = '' if native else '<button type="button" onclick="location.reload()">Recarregar prévia <span aria-hidden="true">↻</span></button>'
    snapshot = _source(data.get('snapshot_path'), 'Dados desta leitura')
    sources = ''.join(_source(data.get(key), label) for key, label in [('state_path', 'Estado'), ('handoff_path', 'Handoff'), ('decisions_path', 'Decisões')])
    preview_note = '' if native else '<p class="preview-note">Prévia local. Para reler os arquivos e escolher projeto, use a janela do dashboard. Recarregar esta página apenas reabre o HTML gerado.</p>'
    source_note = 'Fotografia dos dados locais; atualizar relê os arquivos, sem recalcular as medições.' if data.get('source_ok') else 'Leitura dos documentos locais. Medições ausentes permanecem como Não medido.'
    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>MEGABRAIN · visão pessoal</title><style>{css}</style></head>
<body><a class="skip" href="#agora">Ir para o próximo passo</a><main>
<header class="top"><div class="brand">{brand}<div><p class="eyebrow">MEGABRAIN <span>· visão pessoal</span></p><h1>{_text(data['name'])}</h1><p class="context">Acompanhando {'a central' if data['is_central'] else 'este projeto'}</p></div></div>{controls}</header>
<section class="now glass" id="agora" tabindex="-1" aria-labelledby="now-title">
<div class="section-head"><h2 id="now-title">Agora</h2><span class="status {tone}"><i aria-hidden="true"></i>{status}</span></div>
<div class="next"><p class="eyebrow accent">Seu próximo passo</p><p class="action">{action}</p></div>
{priority}<div class="now-foot"><span>Uma ação por vez, a partir do que está registrado.</span>{_source(data.get('state_path'), 'Consultar estado')}</div>
</section>
<section class="signals" aria-label="Sinais desta leitura"><div><h2>Versão</h2><p>{_text(data['version'])}</p><span>Registrada na fonte</span></div><div><h2>Trava</h2><p class="{lock_class}">{_text(lock)}</p><span>Ocupação informada pelo projeto</span></div><div><h2>Arquivos pendentes</h2><p>{_metric(data['git_dirty'])}</p><span>Alterações locais registradas</span></div><div><h2>Atualização da fonte</h2><p class="time">{_text(display_time(data['updated_at']))}</p><span>Data dos dados, não deste clique</span></div></section>
<div class="lower"><section class="news" aria-labelledby="news-title"><div class="section-head"><div><p class="eyebrow">Micro · registros recentes</p><h2 id="news-title">O que mudou</h2></div>{_source(data.get('decisions_path'), 'Ver decisões')}</div><ol class="timeline">{news}</ol></section>
<aside class="context-column"><section class="overview glass" aria-labelledby="overview-title"><p class="eyebrow">Macro · projeto inteiro</p><h2 id="overview-title">Onde estamos</h2><p class="overview-copy">{_text(data['tldr'])}</p></section>
<section class="sync" aria-labelledby="sync-title"><h2 id="sync-title">Projetos e sincronização</h2><p class="sync-count">{_metric(data['projects_current'])} <span>em dia de</span> {_metric(data['projects_total'])}</p><p class="caption">Atrasos listados na fonte · até seis projetos</p><ul class="projects">{projects}</ul></section></aside></div>
<footer><div class="source-line"><span class="label">Fontes locais</span><nav aria-label="Fontes do projeto">{sources}{snapshot}</nav></div><p>{source_note}</p><p class="path">{_text(data['root'])}</p>{preview_note}</footer>
</main></body></html>'''


def write_html(data: dict, target: str | Path, *, native: bool = False) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(data, native=native), encoding="utf-8")
    return target
