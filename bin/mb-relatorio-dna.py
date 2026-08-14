#!/usr/bin/env python3
"""
mb-relatorio-dna.py — gera o relatório DNA do megabrain.

O relatório DNA é um HTML autocontido, interativo e visualmente rico que
funciona como "DNA" do megabrain: quem tiver esse arquivo tem a descrição
completa do protocolo, componentes, gates, ferramentas e instruções para
replicar/adaptar o sistema.

Frontend voltado para humano (árvore de desenvolvimento tipo skill tree,
seções navegáveis, cards). Backend para IA (JSON-LD, <meta> tags e seção
"Para a IA").

Desde 260814, a saída vive numa PASTA (`dna/`), não mais num arquivo solto na
raiz da central — o relatório continua sendo o artefato principal
(`dna/RELATORIO-DNA.html`), mas a pasta também guarda um `dna/dna.json`
(mesmos dados em JSON puro, pra script/IA consumir sem parsear HTML) e um
`dna/README.md` (índice de uma linha). Isso deixa o DNA com o mesmo formato
de "pasta com propósito único" que o resto do projeto usa (`referencias/`,
`skills/`, `bin/`).

Uso:
    python bin/mb-relatorio-dna.py [--central PATH] [--saida PATH]

Sem argumentos, detecta a central a partir do diretório do script e salva
`dna/RELATORIO-DNA.html` dentro dela. Antes de sobrescrever, copia o arquivo
anterior para `dna/.dna-backup/`. Se existir o arquivo legado
`MEGABRAIN-RELATORIO-DNA.html` solto na raiz da central (versões < 260814),
ele é migrado para `dna/.dna-backup/` na primeira execução.
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

DNA_DIR_NAME = "dna"
BACKUP_DIR_NAME = ".dna-backup"
DEFAULT_OUT_FILENAME = "RELATORIO-DNA.html"
LEGACY_FLAT_NAME = "MEGABRAIN-RELATORIO-DNA.html"  # nome antigo, solto na raiz (< 260814)


def detectar_central() -> Path:
    """Retorna a pasta central do megabrain baseada no script ou env var."""
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return Path(env).resolve()
    # Diretório pai de bin/
    return Path(__file__).resolve().parent.parent


def ler_versao(central: Path) -> str:
    path = central / "VERSAO.txt"
    if not path.exists():
        return "desconhecida"
    for linha in path.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha:
            m = re.match(r"(\d{4}-\d{2}-\d{2})\s*·\s*v([\d.]+)", linha)
            if m:
                return f"v{m.group(2)} · {m.group(1)}"
            return linha
    return "desconhecida"


def ler_resumo_arquivo(central: Path, nome: str) -> str:
    path = central / nome
    if not path.exists():
        return ""
    texto = path.read_text(encoding="utf-8")
    # Pega as primeiras linhas até um limite
    linhas = texto.splitlines()
    paragrafos = []
    for linha in linhas:
        if linha.strip():
            paragrafos.append(linha.strip())
        if len(paragrafos) >= 3:
            break
    return " ".join(paragrafos)[:300]


# Dados da árvore de desenvolvimento visual (skill tree).
# Cada nó: id, label, grupo, descrição curta, detalhe.
NOS = [
    {"id": "raiz", "label": "MEGABRAIN", "grupo": "raiz", "x": 500, "y": 40,
     "desc": "Protocolo de execução multi-agente e anti-slop.",
     "detalhe": "O megabrain é um protocolo operacional para agentes de IA trabalharem juntos sem pisar um no outro e para evitar entregas genéricas."},

    # Gates
    {"id": "g0", "label": "0 · Assumir", "grupo": "gate", "x": 80, "y": 180,
     "desc": "Checa trava, lê ESTADO/HANDOFF/DECISOES/LICOES.",
     "detalhe": "Gate 0 garante que apenas um agente escreva por vez. Usa HANDOFF.md e o script mb-sync.py para travar/liberar o projeto."},
    {"id": "g1", "label": "1 · Enquadrar", "grupo": "gate", "x": 220, "y": 180,
     "desc": "Define artefato, leitor, critérios e restrições.",
     "detalhe": "Antes de gerar qualquer output, responde: artefato, leitor, 3 critérios verificáveis, restrição dura e a versão genérica a evitar."},
    {"id": "g2", "label": "2 · Orçar Contexto", "grupo": "gate", "x": 360, "y": 180,
     "desc": "Contexto é orçamento compartilhado.",
     "detalhe": "Leia sob demanda (Glob → Grep → Read), checkpoint em arquivo e delegue varredura a subagentes. Acima de ~85%, handoff e recomece."},
    {"id": "g3", "label": "3 · Gerar", "grupo": "gate", "x": 500, "y": 180,
     "desc": "Estrutura antes de prosa; uma afirmação por parágrafo.",
     "detalhe": "Fatos sobre o mundo atual são buscados antes; números têm fonte ou rótulo [ESTIMATIVA]."},
    {"id": "g4", "label": "4 · Auditar", "grupo": "gate", "x": 640, "y": 180,
     "desc": "Anti-slop: léxico, estrutura, substância, compressão.",
     "detalhe": "Releia e reescreva. Corte léxico banido, teste 'e daí?', declare trade-offs e comprima 30% sem perda."},
    {"id": "g5", "label": "5 · Reparar", "grupo": "gate", "x": 780, "y": 180,
     "desc": "Uma rodada só de autocrítica.",
     "detalhe": "Loop infinito de autocrítica homogeneiza o texto. Se uma rodada não resolver, volte ao enquadramento."},
    {"id": "g6", "label": "6 · Verificar", "grupo": "gate", "x": 920, "y": 180,
     "desc": "Arquivo abre? Números batem? Links funcionam?",
     "detalhe": "Alto risco: delegue a um subagente ou outro modelo sem histórico."},

    # Ferramentas/métodos conectados
    {"id": "aspirador", "label": "Aspirador", "grupo": "ferramenta", "x": 120, "y": 340,
     "desc": "Revisão pós-implementação: limpa código mecanicamente.",
     "detalhe": "Default dry-run. Detecta trailing whitespace, linhas em branco, tabs misturados, imports não usados. Só aplica correções mecânicas seguras com backup."},
    {"id": "sync", "label": "mb-sync.py", "grupo": "ferramenta", "x": 260, "y": 340,
     "desc": "Trava de handoff multi-agente.",
     "detalhe": "Escreve TRAVADO_POR/ATÉ/ESCOPO em HANDOFF.md. status/lock/release. Garantia executável para que dois agentes não escrevam ao mesmo tempo."},
    {"id": "version", "label": "mb-check-version.py", "grupo": "ferramenta", "x": 400, "y": 340,
     "desc": "Sincroniza megabrain dos projetos com a central.",
     "detalhe": "Compara VERSAO.txt. Central mais nova → sync. Projeto mais novo → avisa. Modo --verificar-git consulta o repositório público."},
    {"id": "relatorio", "label": "Relatório DNA", "grupo": "ferramenta", "x": 540, "y": 340,
     "desc": "Este HTML: DNA completo do megabrain, em dna/.",
     "detalhe": "Gera dna/RELATORIO-DNA.html (+ dna/dna.json), autocontido e interativo, com árvore de desenvolvimento visual, para humano e IA replicarem o protocolo."},
    {"id": "relatorio_projeto", "label": "Relatório de projeto", "grupo": "ferramenta", "x": 680, "y": 340,
     "desc": "Irmão do DNA: concentra a instância de UM projeto.",
     "detalhe": "mb-relatorio-projeto.py gera RELATORIO.html na raiz de um projeto: contexto específico + geral, estado/handoff, situação viva, próximas ações e pendências — tudo num arquivo só, pra humano e IA."},
    {"id": "memoria", "label": "mb-sync-memoria.py", "grupo": "ferramenta", "x": 820, "y": 340,
     "desc": "Sincroniza identidade entre agentes.",
     "detalhe": "Copia perfil pessoal para CLAUDE.md/GEMINI.md/AGENTS.md de forma idempotente."},
    {"id": "duplo", "label": "Duplo Diamante", "grupo": "metodo", "x": 960, "y": 340,
     "desc": "Pesquisa → Análise → Ideação → Design.",
     "detalhe": "Para projetos de design. Não misture modos divergente/convergente. Trave grade, tipografia, paleta e espaçamento antes de compor."},

    # Bastão e aprender ficam abaixo dos gates
    {"id": "g7", "label": "7 · Passar o Bastão", "grupo": "gate", "x": 320, "y": 500,
     "desc": "Reescreve ESTADO.md, HANDOFF.md, anexa DECISOES.md.",
     "detalhe": "Handoff com verbo e objeto. Próximo agente não começa do zero."},
    {"id": "g8", "label": "8 · Aprender", "grupo": "gate", "x": 680, "y": 500,
     "desc": "Registra lição no formato GATILHO/LIÇÃO/ATALHO.",
     "detalhe": "Lição 3× vira regra em MEGABRAIN.md ou skill própria."},
]

CONEXOES = [
    ("raiz", "g0"), ("raiz", "g1"), ("raiz", "g2"), ("raiz", "g3"),
    ("raiz", "g4"), ("raiz", "g5"), ("raiz", "g6"),
    ("g0", "sync"),
    ("g2", "version"),
    ("g4", "aspirador"),
    ("g6", "relatorio"),
    ("relatorio", "relatorio_projeto"),
    ("g0", "memoria"),
    ("g1", "duplo"),
    ("g3", "relatorio"),
    ("g6", "g7"),
    ("g7", "g8"),
]


def css() -> str:
    return """
    :root {
      --bg: #0b0f14;
      --surface: #111820;
      --panel: #161f2a;
      --border: #253244;
      --text: #dbe1e8;
      --muted: #8b9aae;
      --accent: #7dd3fc;
      --accent-2: #c084fc;
      --ok: #4ade80;
      --warn: #facc15;
      --danger: #f87171;
      --radius: 10px;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.55;
    }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    header {
      background: linear-gradient(90deg, rgba(125,211,252,.08), rgba(192,132,252,.08));
      border-bottom: 1px solid var(--border);
      padding: 2rem 1.5rem;
      text-align: center;
    }
    header h1 { margin: 0; font-size: 2.2rem; letter-spacing: -0.02em; }
    header p { margin: .5rem 0 0; color: var(--muted); }
    .badge {
      display: inline-block;
      padding: .25rem .7rem;
      border-radius: 999px;
      font-size: .75rem;
      font-weight: 700;
      text-transform: uppercase;
      background: rgba(125,211,252,.12);
      color: var(--accent);
      border: 1px solid rgba(125,211,252,.25);
      margin-top: .8rem;
    }
    nav {
      position: sticky;
      top: 0;
      background: rgba(11,15,20,.92);
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--border);
      display: flex;
      gap: .5rem;
      padding: .75rem 1.5rem;
      flex-wrap: wrap;
      z-index: 50;
    }
    nav button {
      background: var(--surface);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: .45rem .9rem;
      cursor: pointer;
      font-size: .85rem;
    }
    nav button:hover, nav button.active { border-color: var(--accent); color: var(--accent); }
    main { max-width: 1100px; margin: 0 auto; padding: 1.5rem; }
    section { display: none; animation: fade .25s ease; }
    section.active { display: block; }
    @keyframes fade { from { opacity: 0; transform: translateY(6px);} to { opacity: 1; transform: translateY(0);} }
    h2 { font-size: 1.35rem; border-bottom: 1px solid var(--border); padding-bottom: .5rem; margin-top: 0; }
    h3 { color: var(--accent); font-size: 1.05rem; margin-top: 1.5rem; }
    .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; margin: 1.5rem 0; }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1rem;
    }
    .card h4 { margin: 0 0 .4rem; color: var(--accent-2); }
    .card p { margin: 0; color: var(--muted); font-size: .92rem; }

    /* Árvore de desenvolvimento */
    .tree-wrap { position: relative; overflow-x: auto; padding: 1rem 0; }
    .tree {
      position: relative;
      width: 1080px;
      height: 620px;
      margin: 0 auto;
      user-select: none;
    }
    .tree svg {
      position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none;
    }
    .tree svg line {
      stroke: #334155; stroke-width: 2; stroke-linecap: round;
    }
    .node {
      position: absolute;
      transform: translate(-50%, -50%);
      padding: .55rem .9rem;
      border-radius: var(--radius);
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text);
      font-size: .82rem;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      box-shadow: 0 4px 12px rgba(0,0,0,.25);
      transition: transform .15s, box-shadow .15s, border-color .15s;
      z-index: 10;
    }
    .node:hover { transform: translate(-50%, -52%); box-shadow: 0 8px 22px rgba(0,0,0,.35); }
    .node.raiz { background: linear-gradient(135deg, rgba(125,211,252,.18), rgba(192,132,252,.18)); border-color: var(--accent); color: #fff; font-size: 1rem; }
    .node.gate { border-color: rgba(125,211,252,.45); color: var(--accent); }
    .node.ferramenta { border-color: rgba(74,222,128,.45); color: var(--ok); }
    .node.metodo { border-color: rgba(192,132,252,.45); color: var(--accent-2); }
    .node.selected { box-shadow: 0 0 0 2px var(--warn); border-color: var(--warn); }

    .detail-panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.25rem;
      margin-top: 1.5rem;
      min-height: 120px;
    }
    .detail-panel h3 { margin: 0 0 .5rem; color: var(--accent); }
    .detail-panel p { margin: .4rem 0; }
    .detail-panel .hint { color: var(--muted); font-size: .9rem; }

    details { background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); margin: 1rem 0; }
    summary { padding: .9rem 1.1rem; cursor: pointer; font-weight: 600; }
    details > div { padding: 0 1.1rem 1rem; }
    code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .9em; }
    pre { background: var(--bg); padding: .75rem; border-radius: 6px; overflow-x: auto; }
    .ai-box { background: rgba(125,211,252,.08); border-left: 4px solid var(--accent); padding: 1rem 1.25rem; border-radius: 0 var(--radius) var(--radius) 0; }
    footer { text-align: center; color: var(--muted); font-size: .85rem; padding: 2rem 1rem; border-top: 1px solid var(--border); margin-top: 2rem; }
    @media (max-width: 760px) {
      .tree { width: 100%; height: auto; min-height: 620px; }
      .node { font-size: .72rem; padding: .4rem .6rem; }
    }
    """


def js() -> str:
    return """
    const nodes = document.querySelectorAll('.node');
    const panelTitle = document.getElementById('detail-title');
    const panelDesc = document.getElementById('detail-desc');
    const panelDetalhe = document.getElementById('detail-detalhe');

    nodes.forEach(n => {
      n.addEventListener('click', () => {
        nodes.forEach(x => x.classList.remove('selected'));
        n.classList.add('selected');
        panelTitle.textContent = n.dataset.label;
        panelDesc.textContent = n.dataset.desc || '';
        panelDetalhe.textContent = n.dataset.detalhe || '';
      });
    });

    const navButtons = document.querySelectorAll('nav button');
    const sections = document.querySelectorAll('main section');
    navButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        navButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        sections.forEach(s => s.classList.remove('active'));
        document.getElementById(btn.dataset.target).classList.add('active');
      });
    });
    """


def gerar_json_ld(versao: str, data_iso: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "name": "MEGABRAIN — Relatório DNA",
        "version": versao,
        "dateCreated": data_iso,
        "description": "DNA completo do protocolo megabrain: gates, ferramentas, métodos e instruções para replicação.",
        "about": {
            "@type": "SoftwareApplication",
            "name": "megabrain",
            "featureList": [n["label"] for n in NOS],
        },
        "hasPart": [
            {"@type": "Thing", "name": n["label"], "description": n["desc"]}
            for n in NOS
        ],
    }


def gerar_html(central: Path, versao: str, data_iso: str) -> str:
    resumo_megabrain = ler_resumo_arquivo(central, "MEGABRAIN.md")
    resumo_skill = ler_resumo_arquivo(central, "skills/megabrain/SKILL.md")

    # Gera nós
    nos_html = []
    for no in NOS:
        cls = f"node {no['grupo']}"
        nos_html.append(
            f'<div class="{cls}" style="left:{no["x"]}px;top:{no["y"]}px" '
            f'data-id="{html.escape(no["id"])}" data-label="{html.escape(no["label"])}" '
            f'data-desc="{html.escape(no["desc"])}" data-detalhe="{html.escape(no["detalhe"])}">'
            f'{html.escape(no["label"])}</div>'
        )

    # Gera linhas SVG
    mapa = {no["id"]: no for no in NOS}
    linhas = []
    for origem_id, destino_id in CONEXOES:
        o = mapa[origem_id]
        d = mapa[destino_id]
        linhas.append(f'<line x1="{o["x"]}" y1="{o["y"]}" x2="{d["x"]}" y2="{d["y"]}" />')

    json_ld = json.dumps(gerar_json_ld(versao, data_iso), ensure_ascii=False, indent=2)
    meta_componentes = ", ".join(n["label"] for n in NOS)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MEGABRAIN — Relatório DNA</title>
<meta name="generator" content="mb-relatorio-dna.py">
<meta name="megabrain:versao" content="{html.escape(versao)}">
<meta name="megabrain:timestamp" content="{html.escape(data_iso)}">
<meta name="megabrain:componentes" content="{html.escape(meta_componentes)}">
<meta name="description" content="DNA completo do protocolo megabrain. Frontend humano, metadados para IA.">
<script type="application/ld+json">{json_ld}</script>
<style>{css()}</style>
</head>
<body>
<header>
  <h1>MEGABRAIN</h1>
  <p>Relatório DNA · {html.escape(versao)} · gerado em {html.escape(data_iso[:10])}</p>
  <span class="badge">Protocolo multi-agente + anti-slop</span>
</header>

<nav>
  <button data-target="arvore" class="active">Árvore de desenvolvimento</button>
  <button data-target="sobre">Sobre</button>
  <button data-target="componentes">Componentes</button>
  <button data-target="uso">Como usar</button>
  <button data-target="ia">Para a IA</button>
</nav>

<main>
  <section id="arvore" class="active">
    <h2>Árvore de desenvolvimento</h2>
    <p class="hint">Clique nos nós para ver detalhes. Cores: <span style="color:var(--accent)">gates</span>, <span style="color:var(--ok)">ferramentas</span>, <span style="color:var(--accent-2)">métodos</span>.</p>
    <div class="tree-wrap">
      <div class="tree">
        <svg>{''.join(linhas)}</svg>
        {''.join(nos_html)}
      </div>
    </div>
    <div class="detail-panel">
      <h3 id="detail-title">Selecione um nó</h3>
      <p id="detail-desc" class="hint">Clique em qualquer nó da árvore para ver a descrição completa.</p>
      <p id="detail-detalhe"></p>
    </div>
  </section>

  <section id="sobre">
    <h2>Sobre o megabrain</h2>
    <div class="ai-box">
      <p><strong>TL;DR:</strong> protocolo operacional para agentes de IA trabalharem no mesmo projeto sem pisar um no outro e para evitar entregas genéricas.</p>
    </div>
    <p>{html.escape(resumo_megabrain)}</p>
    <p>{html.escape(resumo_skill)}</p>

    <h3>O que é o Relatório DNA</h3>
    <p>Este arquivo é o <strong>DNA</strong> do megabrain: tendo ele, uma pessoa ou IA pode entender o protocolo completo, replicar a estrutura e adaptá-la a outros projetos. Ele substitui a necessidade de vasculhar vários arquivos <code>.md</code> separados. Desde 260814 ele vive em <code>dna/</code> (pasta), não mais solto na raiz — a pasta também guarda <code>dna/dna.json</code> (dados estruturados) e <code>dna/.dna-backup/</code> (histórico de versões).</p>

    <h3>Relatório DNA vs Relatório de Projeto</h3>
    <div class="card-grid">
      <div class="card">
        <h4>Relatório DNA</h4>
        <p>Canônico, genérico, vem do template do megabrain. Descreve o protocolo, gates, ferramentas e métodos. Gerado por <code>bin/mb-relatorio-dna.py</code>, vive em <code>dna/</code>.</p>
      </div>
      <div class="card">
        <h4>Relatório de Projeto</h4>
        <p>Instância aplicada a um projeto específico (ex.: Financeiro da Silva, TLOU). Concentra contexto específico e geral, estado/handoff, situação viva e pendências — pra não precisar abrir vários .md soltos. Gerado por <code>bin/mb-relatorio-projeto.py</code>, vive na raiz do projeto (<code>RELATORIO.html</code>).</p>
      </div>
    </div>
  </section>

  <section id="componentes">
    <h2>Componentes</h2>
    <div class="card-grid">
      <div class="card">
        <h4>Gates de entrega</h4>
        <p>Assumir → Enquadrar → Orçar → Gerar → Auditar → Reparar → Verificar → Passar o Bastão → Aprender.</p>
      </div>
      <div class="card">
        <h4>mb-aspirador.py</h4>
        <p>Revisão pós-implementação: limpa código mecanicamente sem alterar lógica. Dry-run, backup, correções seguras.</p>
      </div>
      <div class="card">
        <h4>mb-sync.py</h4>
        <p>Trava multi-agente em HANDOFF.md. Garante que só um agente escreva por vez.</p>
      </div>
      <div class="card">
        <h4>mb-check-version.py</h4>
        <p>Sincroniza a cópia do megabrain dentro de cada projeto com a central (inclui a pasta <code>dna/</code> e <code>bin/</code> inteiro). Pode consultar o git remote.</p>
      </div>
      <div class="card">
        <h4>mb-relatorio-dna.py</h4>
        <p>Gera este HTML dentro de <code>dna/</code>. Backup automático em <code>dna/.dna-backup/</code>.</p>
      </div>
      <div class="card">
        <h4>mb-relatorio-projeto.py</h4>
        <p>Irmão deste gerador: monta o relatório de UM projeto (contexto, estado/handoff, situação, pendências) num HTML só, na raiz do projeto.</p>
      </div>
      <div class="card">
        <h4>mb-sync-memoria.py</h4>
        <p>Sincroniza identidade do usuário entre CLAUDE.md, GEMINI.md e AGENTS.md.</p>
      </div>
    </div>

    <details>
      <summary>Referências sob demanda</summary>
      <div>
        <p>Todas em <code>referencias/</code>:</p>
        <ul>
          <li><code>260810_anti-slop.md</code> — léxico e estrutura banidos</li>
          <li><code>260810_context-engineering.md</code> — orçamento de contexto</li>
          <li><code>260810_design-projects.md</code> — Duplo Diamante</li>
          <li><code>260810_evaluation-gates.md</code> — rubricas</li>
          <li><code>260810_galerias-referencia.md</code> — direção visual</li>
          <li><code>260810_impeccable-routing.md</code> — design vira código</li>
          <li><code>260810_metaprompt-patterns.md</code> — padrões de prompt</li>
          <li><code>260810_metaprompt-templates.md</code> — templates T1–T8</li>
          <li><code>260810_PROMPT-PORTATIL.md</code> — colar em qualquer IA</li>
          <li><code>260810_sync-memoria.md</code> — sincronização de identidade</li>
          <li><code>260810_workflow-architecture.md</code> — skill vs subagente vs hook</li>
        </ul>
      </div>
    </details>
  </section>

  <section id="uso">
    <h2>Como usar</h2>
    <h3>1. Instalar o megabrain num projeto</h3>
    <pre><code>python MEGABRAIN/bin/mb-check-version.py --projeto "./meu-projeto"</code></pre>
    <p>Isso cria a pasta <code>MEGABRAIN/</code> dentro do projeto com o protocolo, referências, <code>bin/</code> inteiro e a pasta <code>dna/</code>.</p>

    <h3>2. Verificar se há atualização</h3>
    <pre><code>python MEGABRAIN/bin/mb-check-version.py --projeto "./meu-projeto" --verificar-git</code></pre>
    <p>Consulta o repositório público e avisa se existe versão mais recente.</p>

    <h3>3. Rodar o aspirador</h3>
    <pre><code>python MEGABRAIN/bin/mb-aspirador.py --dir "./meu-projeto"
python MEGABRAIN/bin/mb-aspirador.py --dir "./meu-projeto" --aplicar</code></pre>

    <h3>4. Gerar/atualizar este relatório DNA</h3>
    <pre><code>python bin/mb-relatorio-dna.py --central "./MEGABRAIN" --saida "./MEGABRAIN/dna/RELATORIO-DNA.html"</code></pre>

    <h3>5. Gerar o relatório de UM projeto (irmão do DNA)</h3>
    <pre><code>python bin/mb-relatorio-projeto.py --projeto "./meu-projeto" --titulo "Meu Projeto" --plano "ESTADO.md ou PLANO.md"</code></pre>
    <p>Ver seção "Relatório de projeto" em <code>MEGABRAIN.md</code> para o guia completo de argumentos.</p>
  </section>

  <section id="ia">
    <h2>Para a IA</h2>
    <div class="ai-box">
      <p>Este HTML é o <strong>DNA canônico</strong> do megabrain. Se você está lendo isso como IA, use as informações abaixo para replicar ou adaptar o protocolo:</p>
      <ul>
        <li><strong>Versão:</strong> {html.escape(versao)}</li>
        <li><strong>Gerado em:</strong> {html.escape(data_iso)}</li>
        <li><strong>Componentes principais:</strong> {html.escape(meta_componentes)}</li>
        <li><strong>Regra de ouro:</strong> garantia real é script, não markdown. Use <code>mb-sync.py</code> para travar, <code>mb-check-version.py</code> para sincronizar.</li>
        <li><strong>Se procura o relatório de UM projeto</strong> (não o protocolo), é outro artefato: <code>RELATORIO.html</code> na raiz do projeto, gerado por <code>mb-relatorio-projeto.py</code> — não confundir os dois.</li>
      </ul>
      <p>Para replicar: copie a estrutura de <code>MEGABRAIN.md</code>, <code>SKILL.md</code>, <code>referencias/</code> e <code>bin/</code>. Mantenha <code>ESTADO.md</code>, <code>HANDOFF.md</code>, <code>DECISOES.md</code> e <code>LICOES.md</code> por projeto.</p>
    </div>
    <h3>Metadados estruturados</h3>
    <pre><code>{html.escape(json_ld)}</code></pre>
    <p class="hint">Os mesmos dados, em JSON puro, também ficam em <code>dna/dna.json</code>.</p>
  </section>
</main>

<footer>
  <p>MEGABRAIN · Relatório DNA · gerado por <code>mb-relatorio-dna.py</code> · vive em <code>dna/</code></p>
  <p>Backup automático em <code>dna/.dna-backup/</code></p>
</footer>

<script>{js()}</script>
</body>
</html>
"""


def migrar_arquivo_legado(central: Path, pasta_dna: Path) -> None:
    """Se existir o HTML antigo solto na raiz (< 260814), move para o backup
    dentro da nova pasta dna/ em vez de deixá-lo perdido ou sobrescrevê-lo."""
    legado = central / LEGACY_FLAT_NAME
    if not legado.exists():
        return
    backup_dir = pasta_dna / BACKUP_DIR_NAME
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = backup_dir / f"{LEGACY_FLAT_NAME.replace('.html', '')}-legado-{timestamp}.html"
    shutil.move(str(legado), str(destino))
    print(f"Arquivo legado migrado: {legado} -> {destino}")


def main():
    ap = argparse.ArgumentParser(description="Gerador do relatório DNA do megabrain")
    ap.add_argument("--central", default=None, help="pasta central do megabrain (default: detecta)")
    ap.add_argument("--saida", default=None, help="caminho do HTML de saída (default: dna/RELATORIO-DNA.html na central)")
    args = ap.parse_args()

    central = Path(args.central).resolve() if args.central else detectar_central()
    if not central.is_dir():
        print(f"ERRO: central não encontrada: {central}")
        sys.exit(1)

    pasta_dna = central / DNA_DIR_NAME
    pasta_dna.mkdir(parents=True, exist_ok=True)

    migrar_arquivo_legado(central, pasta_dna)

    saida = Path(args.saida).resolve() if args.saida else pasta_dna / DEFAULT_OUT_FILENAME

    versao = ler_versao(central)
    data_iso = dt.datetime.now().isoformat()

    html_out = gerar_html(central, versao, data_iso)

    # Garante que o diretório pai exista
    saida.parent.mkdir(parents=True, exist_ok=True)

    # Backup do relatório anterior
    if saida.exists():
        backup_base = pasta_dna / BACKUP_DIR_NAME
        backup_base.mkdir(parents=True, exist_ok=True)
        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = backup_base / f"RELATORIO-DNA-{timestamp}.html"
        shutil.copy2(saida, backup_path)
        print(f"Backup do DNA anterior: {backup_path}")

    saida.write_text(html_out, encoding="utf-8")
    print(f"Relatório DNA gerado: {saida}")

    # JSON estruturado (mesmos dados do JSON-LD embutido), sidecar pra script/IA
    json_path = pasta_dna / "dna.json"
    json_path.write_text(
        json.dumps(gerar_json_ld(versao, data_iso), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"DNA estruturado gerado: {json_path}")

    # README de uma linha pra quem abrir a pasta sem contexto
    readme_path = pasta_dna / "README.md"
    readme_path.write_text(
        "# dna/\n\n"
        f"`{DEFAULT_OUT_FILENAME}` — relatório DNA do megabrain (protocolo, genérico). "
        f"`dna.json` — os mesmos dados em JSON puro. `.dna-backup/` — versões anteriores.\n\n"
        "Gerado por `bin/mb-relatorio-dna.py` — nunca editar os arquivos desta pasta na mão; "
        "edite a fonte (`MEGABRAIN.md`, `SKILL.md`) e rode o script de novo.\n\n"
        "Procurando o relatório de UM projeto (não o protocolo)? É outro artefato: "
        "`RELATORIO.html` na raiz do projeto, gerado por `bin/mb-relatorio-projeto.py`.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
