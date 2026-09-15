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
import os
import re
import shutil
import sys
from pathlib import Path

import mb_utils as u
import mb_pop_tema

u.utf8_console()

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
    path = u.achar(central, "VERSAO.txt")
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
    # v7.1: achar() resolve pasta de máquina em motor/ (central nova) e plana
    # (cópia de projeto / central antiga).
    path = u.achar(central, nome)
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
     "desc": "Checa presença, escopo e trava por arquivo; lê ESTADO/HANDOFF/DECISOES/LICOES.",
     "detalhe": "mb-sync.py declara presença/escopo no HANDOFF. mb_trava.py é checado pelos escritores e protege cada arquivo compartilhado separadamente."},
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
    {"id": "g5", "label": "5 · Verificar", "grupo": "gate", "x": 780, "y": 180,
     "desc": "Arquivo abre? Números batem? Links existem?",
     "detalhe": "Teste o caminho, não confie na citação. Se o alvo é protocolo ou script versionado, compare hash e data da cópia que rodou com a fonte. Depois amarre as pontas: no máximo 5 perguntas, cada uma com evidência, impacto e recomendação. Alto risco: delegue a um subagente ou outro modelo, sem histórico."},

    # Ferramentas/métodos conectados
    {"id": "aspirador", "label": "Aspirador", "grupo": "ferramenta", "x": 120, "y": 340,
     "desc": "Revisão pós-implementação: limpa código mecanicamente.",
     "detalhe": "Default dry-run. Detecta trailing whitespace, linhas em branco, tabs misturados, imports não usados. Só aplica correções mecânicas seguras com backup."},
    {"id": "sync", "label": "mb-sync + mb_trava", "grupo": "ferramenta", "x": 260, "y": 340,
     "desc": "Presença de sessão + trava por arquivo compartilhado.",
     "detalhe": "mb-sync escreve TRAVADO_POR/ATÉ/ESCOPO no HANDOFF. mb_trava usa .mb-lock por arquivo, prazo/dono e recusa IDs duplicados em DECISOES."},
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
    {"id": "g6", "label": "6 · Passar o Bastão", "grupo": "gate", "x": 320, "y": 500,
     "desc": "Reescreve ESTADO.md, HANDOFF.md, anexa DECISOES.md.",
     "detalhe": "Handoff com verbo e objeto. Próximo agente não começa do zero."},
    {"id": "g7", "label": "7 · Aprender", "grupo": "gate", "x": 680, "y": 500,
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
]


def css() -> str:
    # Marca POP v1.2 (motor/modelos/relatorios/PADRAO.md): fundo escuro com
    # auroras fixas, glow no topo, vidro raio 10px, paleta Duolingo nos estados
    # (sempre com glifo além da cor), display pesado no h1, números tabulares.
    return """
    :root {
      --fundo: #0B0B16;
      --fundo2: #12121F;
      --vidro: rgba(31,31,48,.58);
      --vidro-forte: rgba(25,25,39,.82);
      --linha: rgba(255,255,255,.11);
      --tinta: #FFFFFF;
      --corpo: #C9C7E0;
      --fraco: #9A98B6;
      --coral: #FF6B6B;   /* signal · #FF4B4B clareado p/ texto no escuro */
      --verde: #6BDB1A;   /* ok     · #58CC02 */
      --azul: #3DBDF8;    /* info   · #1CB0F6 */
      --amarelo: #FFC800; /* warn */
      --roxo: #CE82FF;
      --radius: 10px;
      --mono: ui-monospace, "Cascadia Mono", Consolas, monospace;
      --sombra: 0 14px 38px rgba(0,0,0,.45);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      font: 16px/1.55 "Segoe UI", system-ui, sans-serif;
      font-variant-numeric: tabular-nums;
      background: var(--fundo);
      color: var(--corpo);
      overflow-x: hidden;
    }
    body::before {
      content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
      background:
        radial-gradient(60rem 30rem at 50% -14%, rgba(124,58,237,.62) 0%, transparent 64%),
        radial-gradient(36rem 22rem at 86% 8%, rgba(28,176,246,.30) 0%, transparent 62%),
        radial-gradient(32rem 20rem at 8% 18%, rgba(124,58,237,.30) 0%, transparent 60%),
        radial-gradient(40rem 26rem at 70% 105%, rgba(28,176,246,.16) 0%, transparent 62%),
        linear-gradient(180deg, var(--fundo2) 0%, var(--fundo) 45%);
    }
    a { color: var(--azul); text-decoration: none; }
    a:hover { text-decoration: underline; }
    strong, b { color: var(--tinta); }
    header {
      padding: 3rem 1.5rem 2rem;
      text-align: center;
    }
    header h1 {
      margin: 0; font-size: clamp(3rem, 6.5vw, 4.6rem); font-weight: 900;
      letter-spacing: -.05em; line-height: 1; color: #fff;
      background: linear-gradient(180deg, #fff 35%, #C4B5FD 90%);
      -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
      filter: drop-shadow(0 8px 34px rgba(124,58,237,.55));
    }
    header p { margin: .7rem 0 0; color: var(--corpo); font: 500 .9rem var(--mono); }
    .badge {
      display: inline-flex; align-items: center; gap: .45rem;
      padding: .32rem .85rem; margin-top: .9rem;
      border-radius: 99px; font: 700 .74rem var(--mono); letter-spacing: .06em;
      text-transform: uppercase;
      background: rgba(206,130,255,.16); color: var(--roxo);
      border: 1px solid rgba(206,130,255,.45);
    }
    .badge::before { content: "◆"; color: var(--verde); }
    nav {
      position: sticky; top: 0; z-index: 50;
      display: flex; gap: .5rem; flex-wrap: wrap; justify-content: center;
      padding: .7rem 1.5rem;
      background: rgba(11,11,22,.72);
      backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
      border-bottom: 1px solid var(--linha);
    }
    nav button {
      font: 700 .85rem "Segoe UI", system-ui, sans-serif;
      padding: .55rem 1rem; border-radius: var(--radius); cursor: pointer;
      background: var(--vidro); color: var(--tinta);
      border: 1px solid var(--linha);
      transition: transform .12s ease, border-color .12s ease;
    }
    nav button:hover { transform: translateY(-2px); border-color: var(--roxo); }
    nav button.active {
      background: color-mix(in oklab, var(--roxo) 22%, var(--vidro-forte));
      border-color: var(--roxo);
    }
    nav button.active::before { content: "▸ "; color: var(--roxo); }
    main { max-width: 1180px; margin: 0 auto; padding: 1.8rem 1.5rem; }
    section { display: none; }
    section.active { display: block; }
    /* animação só na troca de aba: a carga inicial já nasce no estado final */
    section.active.trocou { animation: surge .28s ease both; }
    @keyframes surge { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
    h2 {
      margin-top: 0; padding-bottom: .55rem;
      color: var(--tinta); font-size: 1.6rem; font-weight: 800; letter-spacing: -.02em;
      border-bottom: 1px solid var(--linha);
    }
    h3 { color: var(--azul); font-size: 1.08rem; font-weight: 800; margin-top: 1.6rem; }
    .hint { color: var(--fraco); }
    .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; margin: 1.5rem 0; }
    .card, .detail-panel, details, .ai-box {
      background: var(--vidro);
      backdrop-filter: blur(16px) saturate(140%); -webkit-backdrop-filter: blur(16px) saturate(140%);
      border: 1px solid var(--linha);
      border-radius: var(--radius);
      box-shadow: var(--sombra);
    }
    .card { padding: 1rem 1.05rem; border-top: 3px solid var(--roxo); }
    .card h4 { margin: 0 0 .4rem; color: var(--tinta); font-size: 1rem; }
    .card h4::before { content: "■ "; color: var(--roxo); font-size: .8em; }
    .card p { margin: 0; color: var(--corpo); font-size: .92rem; }

    /* Árvore de desenvolvimento */
    .leg { font-weight: 700; white-space: nowrap; }
    .leg-gate { color: var(--azul); }
    .leg-ferramenta { color: var(--verde); }
    .leg-metodo { color: var(--coral); }
    .tree-wrap {
      position: relative; overflow-x: auto; padding: 1rem 0;
      background: rgba(11,11,22,.35); border: 1px solid var(--linha); border-radius: var(--radius);
    }
    .tree { position: relative; width: 1110px; height: 600px; margin: 0 auto; user-select: none; }
    .tree svg { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
    .tree svg line { stroke: rgba(206,130,255,.38); stroke-width: 2; stroke-linecap: round; }
    .node {
      position: absolute; transform: translate(-50%, -50%); z-index: 10;
      padding: .55rem .9rem; border-radius: var(--radius);
      border: 2px solid var(--c, var(--linha));
      background: color-mix(in oklab, var(--c, #fff) 14%, var(--vidro-forte));
      backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
      color: var(--c, var(--tinta));
      font-size: .82rem; font-weight: 700; white-space: nowrap; cursor: pointer;
      box-shadow: 0 4px 0 color-mix(in oklab, var(--c, #fff) 38%, #000), 0 10px 24px rgba(0,0,0,.4);
      transition: transform .12s ease, box-shadow .12s ease;
    }
    .node::before { margin-right: .4rem; }
    .node:hover { transform: translate(-50%, -54%); }
    .node:active { transform: translate(-50%, -46%); box-shadow: 0 1px 0 color-mix(in oklab, var(--c, #fff) 38%, #000); }
    .node:focus-visible { outline: 3px solid var(--roxo); outline-offset: 3px; }
    .node.raiz {
      --c: var(--roxo); color: #fff; font-size: 1.05rem; font-weight: 900; letter-spacing: -.01em;
      padding: .7rem 1.2rem;
      background: linear-gradient(135deg, rgba(124,58,237,.75), rgba(28,176,246,.45));
      box-shadow: 0 4px 0 #4C1D95, 0 0 34px rgba(124,58,237,.6);
    }
    .node.raiz::before { content: "✦"; color: var(--amarelo); }
    .node.gate { --c: var(--azul); }
    .node.gate::before { content: "◆"; }
    .node.ferramenta { --c: var(--verde); }
    .node.ferramenta::before { content: "■"; }
    .node.metodo { --c: var(--coral); }
    .node.metodo::before { content: "●"; }
    .node.selected {
      border-color: var(--amarelo);
      box-shadow: 0 4px 0 #8A6D00, 0 0 0 3px rgba(255,200,0,.35), 0 0 26px rgba(255,200,0,.35);
    }
    .node.selected::after {
      content: "★"; position: absolute; top: -.7rem; right: -.55rem;
      width: 1.25rem; height: 1.25rem; border-radius: 50%; display: grid; place-items: center;
      background: var(--amarelo); color: #0B0B16; font-size: .72rem;
    }

    .detail-panel { padding: 1.25rem 1.35rem; margin-top: 1.5rem; min-height: 120px; border-left: 4px solid var(--amarelo); }
    .detail-panel h3 { margin: 0 0 .5rem; color: var(--tinta); }
    .detail-panel h3::before { content: "★ "; color: var(--amarelo); }
    .detail-panel p { margin: .4rem 0; }
    .detail-panel .hint { font-size: .9rem; }

    details { margin: 1rem 0; }
    summary { padding: .9rem 1.1rem; cursor: pointer; font-weight: 700; color: var(--azul); list-style: none; }
    summary::-webkit-details-marker { display: none; }
    summary::before { content: "▸ "; }
    details[open] summary::before { content: "▾ "; }
    summary:focus-visible { outline: 3px solid var(--roxo); outline-offset: 2px; border-radius: var(--radius); }
    details > div { padding: 0 1.1rem 1rem; }
    code, pre { font-family: var(--mono); font-size: .9em; }
    code { color: #E4D4FF; }
    pre {
      position: relative; margin: .6rem 0;
      background: rgba(11,11,22,.78); border: 1px solid var(--linha);
      padding: .8rem .9rem; border-radius: var(--radius); overflow-x: auto;
    }
    pre[data-copia] { cursor: copy; padding-right: 6.5rem; transition: border-color .12s ease; }
    pre[data-copia]:hover { border-color: var(--verde); }
    pre[data-copia]:focus-visible { outline: 3px solid var(--roxo); outline-offset: 2px; }
    pre[data-copia]::after {
      content: "⧉ copiar"; position: absolute; top: .55rem; right: .6rem;
      font: 800 .68rem var(--mono); color: #0B0B16; background: var(--verde);
      padding: .15rem .5rem; border-radius: 6px; box-shadow: 0 2px 0 #2F6B00;
    }
    .ai-box { padding: 1rem 1.25rem; border-left: 4px solid var(--azul); }
    .ai-box > p:first-child::before { content: "ⓘ "; color: var(--azul); font-weight: 800; }
    footer {
      text-align: center; color: var(--fraco); font-size: .85rem;
      padding: 2rem 1rem; border-top: 1px solid var(--linha); margin-top: 2rem;
    }

    #toasts {
      position: fixed; bottom: 1.1rem; left: 50%; transform: translateX(-50%); z-index: 100;
      display: flex; flex-direction: column; gap: .45rem; align-items: center;
      pointer-events: none; max-width: min(92vw, 34rem);
    }
    .toast {
      display: flex; align-items: center; gap: .55rem; padding: .62rem 1rem; border-radius: var(--radius);
      background: var(--vidro-forte); border: 2px solid var(--verde); color: var(--tinta);
      font-weight: 600; font-size: .85rem; box-shadow: 0 12px 34px rgba(0,0,0,.55);
      animation: surge .22s ease both;
    }
    .toast.err { border-color: var(--coral); }
    .toast .t-ico { color: var(--verde); flex: 0 0 auto; }
    .toast.err .t-ico { color: var(--coral); }
    .toast small { display: block; color: var(--fraco); font-weight: 500; word-break: break-all; }
    .toast.saindo { transition: opacity .25s ease, transform .25s ease; opacity: 0; transform: translateY(8px); }

    @media (max-width: 760px) {
      .tree { width: 100%; height: auto; min-height: 620px; }
      .node { font-size: .72rem; padding: .4rem .6rem; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { animation: none !important; transition: none !important; }
      html { scroll-behavior: auto; }
    }
    @media print {
      *, *::before, *::after { animation: none !important; transition: none !important; }
      nav, #toasts { display: none; }
      section { display: block !important; }
    }
    """


def js() -> str:
    return """
    const fila = document.getElementById('toasts');
    function toast(msg, sub, err) {
      const t = document.createElement('div');
      t.className = 'toast' + (err ? ' err' : '');
      const ico = document.createElement('span'); ico.className = 't-ico'; ico.textContent = err ? '⚠' : '✓';
      const box = document.createElement('span'); box.textContent = msg;
      if (sub) { const s = document.createElement('small'); s.textContent = sub; box.appendChild(s); }
      t.appendChild(ico); t.appendChild(box);
      fila.appendChild(t);
      while (fila.children.length > 3) fila.removeChild(fila.firstChild);
      setTimeout(() => { t.classList.add('saindo'); setTimeout(() => t.remove(), 280); }, 3400);
    }
    function fallback(txt) {
      const ta = document.createElement('textarea');
      ta.value = txt; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      let ok = false; try { ok = document.execCommand('copy'); } catch (e) {}
      ta.remove(); return ok;
    }
    function copia(txt, diz) {
      const origem = document.activeElement;
      const feito = ok => {
        toast(ok ? (diz || 'Copiado') : 'Não deu pra copiar', ok ? txt : 'copia na mão: ' + txt, !ok);
        if (origem && origem.focus) { try { origem.focus({preventScroll: true}); } catch (e) {} }
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(() => feito(true), () => feito(fallback(txt)));
      } else { feito(fallback(txt)); }
    }

    const nodes = document.querySelectorAll('.node');
    const panelTitle = document.getElementById('detail-title');
    const panelDesc = document.getElementById('detail-desc');
    const panelDetalhe = document.getElementById('detail-detalhe');

    nodes.forEach(n => {
      n.addEventListener('click', () => {
        nodes.forEach(x => { x.classList.remove('selected'); x.setAttribute('aria-pressed', 'false'); });
        n.classList.add('selected');
        n.setAttribute('aria-pressed', 'true');
        panelTitle.textContent = n.dataset.label;
        panelDesc.textContent = n.dataset.desc || '';
        panelDetalhe.textContent = n.dataset.detalhe || '';
      });
    });

    const navButtons = document.querySelectorAll('nav button');
    const sections = document.querySelectorAll('main section');
    navButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        navButtons.forEach(b => { b.classList.remove('active'); b.setAttribute('aria-pressed', 'false'); });
        btn.classList.add('active');
        btn.setAttribute('aria-pressed', 'true');
        sections.forEach(s => s.classList.remove('active', 'trocou'));
        document.getElementById(btn.dataset.target).classList.add('active', 'trocou');
      });
    });

    /* delegação única: clique e teclado (Enter/Espaço) em quem não é botão nativo */
    document.addEventListener('click', e => {
      const c = e.target.closest('[data-copia]');
      if (c) { e.preventDefault(); copia(c.getAttribute('data-copia'), c.getAttribute('data-diz')); return; }
      const d = e.target.closest('[data-diz]');
      if (d) toast(d.getAttribute('data-diz'));
    });
    document.addEventListener('keydown', e => {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      const t = e.target.closest ? e.target.closest('[role="button"]') : null;
      if (t && t.tagName !== 'BUTTON' && t.tagName !== 'A' && t.tagName !== 'SUMMARY') {
        e.preventDefault();
        t.click();
      }
    });
    document.querySelectorAll('details').forEach(det => det.addEventListener('toggle', () => {
      toast((det.open ? 'Aberto: ' : 'Fechado: ') + det.querySelector('summary').textContent.trim());
    }));
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


def gerar_html(central: Path, versao: str, data_iso: str, tema: str | None = None) -> str:
    resumo_megabrain = ler_resumo_arquivo(central, "MEGABRAIN.md")
    resumo_skill = ler_resumo_arquivo(central, "skills/megabrain/SKILL.md")

    # Posição de tela: espalha x (rótulos POP são mais pesados) e alterna a
    # altura dos nós da mesma linha quando o vizinho fica perto demais.
    pos = {no["id"]: [round(no["x"] * 1.1) - 20, no["y"] + 20] for no in NOS}
    linhas_y: dict[int, list[dict]] = {}
    for no in NOS:
        linhas_y.setdefault(no["y"], []).append(no)
    for linha in linhas_y.values():
        if len(linha) >= 7:
            for i, no in enumerate(sorted(linha, key=lambda n: n["x"])):
                pos[no["id"]][1] += -26 if i % 2 == 0 else 26

    # Gera nós
    nos_html = []
    for no in NOS:
        cls = f"node {no['grupo']}"
        x, y = pos[no["id"]]
        nos_html.append(
            f'<div class="{cls}" style="left:{x}px;top:{y}px" '
            f'role="button" tabindex="0" aria-pressed="false" '
            f'data-id="{html.escape(no["id"])}" data-label="{html.escape(no["label"])}" '
            f'data-desc="{html.escape(no["desc"])}" data-detalhe="{html.escape(no["detalhe"])}">'
            f'{html.escape(no["label"])}</div>'
        )

    # Gera linhas SVG
    linhas = []
    for origem_id, destino_id in CONEXOES:
        (ox, oy), (dx, dy) = pos[origem_id], pos[destino_id]
        linhas.append(f'<line x1="{ox}" y1="{oy}" x2="{dx}" y2="{dy}" />')

    json_ld = u.safe_json_dumps(gerar_json_ld(versao, data_iso), ensure_ascii=False, indent=2)
    meta_componentes = ", ".join(n["label"] for n in NOS)

    def comando(texto: str) -> str:
        """Bloco de comando que copia no clique (todo clique responde — PADRAO.md)."""
        return (
            f'<pre data-copia="{html.escape(texto)}" data-diz="Comando copiado" '
            f'role="button" tabindex="0" title="Clique para copiar"><code>{html.escape(texto)}</code></pre>'
        )

    cmd_instalar = comando('python MEGABRAIN/bin/mb-check-version.py --projeto "./meu-projeto"')
    cmd_git = comando('python MEGABRAIN/bin/mb-check-version.py --projeto "./meu-projeto" --verificar-git')
    cmd_aspirador = comando(
        'python MEGABRAIN/bin/mb-aspirador.py --dir "./meu-projeto"\n'
        'python MEGABRAIN/bin/mb-aspirador.py --dir "./meu-projeto" --aplicar'
    )
    cmd_dna = comando('python bin/mb-relatorio-dna.py --central "./MEGABRAIN" --saida "./MEGABRAIN/dna/RELATORIO-DNA.html"')
    cmd_projeto = comando('python bin/mb-relatorio-projeto.py --projeto "./meu-projeto" --titulo "Meu Projeto" --plano "ESTADO.md ou PLANO.md"')

    html_attr = ' data-tema="claro"' if tema == "claro" else ""
    return f"""<!DOCTYPE html>
<html lang="pt-BR"{html_attr}>
<head>
{mb_pop_tema.JS_TEMA_HEAD}
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MEGABRAIN — Relatório DNA</title>
<meta name="generator" content="mb-relatorio-dna.py">
<meta name="megabrain:versao" content="{html.escape(versao)}">
<meta name="megabrain:timestamp" content="{html.escape(data_iso)}">
<meta name="megabrain:componentes" content="{html.escape(meta_componentes)}">
<meta name="description" content="DNA completo do protocolo megabrain. Frontend humano, metadados para IA.">
<script type="application/ld+json">{json_ld}</script>
<style>{css()}{mb_pop_tema.CSS_TEMA}</style>
</head>
<body>
<header>
  <div class="tema-linha">{mb_pop_tema.HTML_TEMA_CONTROLE}</div>
  <h1>MEGABRAIN</h1>
  <p>Relatório DNA · {html.escape(versao)} · gerado em {html.escape(data_iso[:10])}</p>
  <span class="badge">Protocolo multi-agente + anti-slop</span>
</header>

<nav>
  <button type="button" data-target="arvore" class="active" aria-pressed="true">Árvore de desenvolvimento</button>
  <button type="button" data-target="sobre" aria-pressed="false">Sobre</button>
  <button type="button" data-target="componentes" aria-pressed="false">Componentes</button>
  <button type="button" data-target="uso" aria-pressed="false">Como usar</button>
  <button type="button" data-target="ia" aria-pressed="false">Para a IA</button>
</nav>

<main>
  <section id="arvore" class="active">
    <h2>Árvore de desenvolvimento</h2>
    <p class="hint">Clique nos nós para ver detalhes. Cores: <span class="leg leg-gate">◆ gates</span>, <span class="leg leg-ferramenta">■ ferramentas</span>, <span class="leg leg-metodo">● métodos</span>.</p>
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
        <p>0 Assumir → 1 Enquadrar → 2 Orçar contexto → 3 Gerar → 4 Auditar (+1 reparo) → 5 Verificar e amarrar pontas → 6 Passar o bastão → 7 Registrar.</p>
      </div>
      <div class="card">
        <h4>mb-aspirador.py</h4>
        <p>Revisão pós-implementação: limpa código mecanicamente sem alterar lógica. Dry-run, backup, correções seguras.</p>
      </div>
      <div class="card">
        <h4>mb-sync.py + mb_trava.py</h4>
        <p>O HANDOFF declara presença e escopo; os escritores checam uma trava por arquivo antes do read-modify-write.</p>
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
    {cmd_instalar}
    <p>Isso cria a pasta <code>MEGABRAIN/</code> dentro do projeto com o protocolo, referências, <code>bin/</code> inteiro e a pasta <code>dna/</code>.</p>

    <h3>2. Verificar se há atualização</h3>
    {cmd_git}
    <p>Consulta o repositório público e avisa se existe versão mais recente.</p>

    <h3>3. Rodar o aspirador</h3>
    {cmd_aspirador}

    <h3>4. Gerar/atualizar este relatório DNA</h3>
    {cmd_dna}

    <h3>5. Gerar o relatório de UM projeto (irmão do DNA)</h3>
    {cmd_projeto}
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
        <li><strong>Regra de ouro:</strong> garantia real é script, não markdown. Use <code>mb-sync.py</code> para presença/escopo, <code>mb_trava.py</code> por arquivo e <code>mb-check-version.py</code> para sincronizar.</li>
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
<div id="toasts" aria-live="polite"></div>

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
    ap.add_argument("--tema", default=None, choices=["claro", "escuro"],
                    help="tema inicial do HTML gerado (default: escuro — o navegador do leitor pode lembrar a preferência)")
    args = ap.parse_args()

    central_default = detectar_central()
    central = Path(args.central).resolve() if args.central else central_default
    if not central.is_dir():
        u.die(f"central não encontrada: {central}")

    # A central deve ser a central default ou um subcaminho dela.
    try:
        u.resolve_within(central, central_default)
    except ValueError as e:
        u.die(f"--central fora da central conhecida: {e}")

    pasta_dna = u.pasta(central, DNA_DIR_NAME)
    pasta_dna.mkdir(parents=True, exist_ok=True)

    migrar_arquivo_legado(central, pasta_dna)

    saida = Path(args.saida).resolve() if args.saida else pasta_dna / DEFAULT_OUT_FILENAME
    try:
        u.resolve_within(saida.parent, central)
    except ValueError as e:
        u.die(f"--saida fora da central: {e}")

    versao = ler_versao(central)
    data_iso = dt.datetime.now().isoformat()

    html_out = gerar_html(central, versao, data_iso, tema=args.tema)

    # Backup do relatório anterior
    if saida.exists():
        backup_base = pasta_dna / BACKUP_DIR_NAME
        backup_base.mkdir(parents=True, exist_ok=True)
        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = backup_base / f"RELATORIO-DNA-{timestamp}.html"
        try:
            shutil.copy2(saida, backup_path)
            print(f"Backup do DNA anterior: {backup_path}")
        except OSError as e:
            print(f"AVISO: falha no backup do DNA: {e}")

    if not u.atomic_write_text(saida, html_out):
        sys.exit(1)
    print(f"Relatório DNA gerado: {saida}")

    # JSON estruturado (mesmos dados do JSON-LD embutido), sidecar pra script/IA
    json_path = pasta_dna / "dna.json"
    if not u.atomic_write_text(
        json_path,
        u.safe_json_dumps(gerar_json_ld(versao, data_iso), ensure_ascii=False, indent=2),
    ):
        sys.exit(1)
    print(f"DNA estruturado gerado: {json_path}")

    # README de uma linha pra quem abrir a pasta sem contexto
    readme_path = pasta_dna / "README.md"
    if not u.atomic_write_text(
        readme_path,
        "# dna/\n\n"
        f"`{DEFAULT_OUT_FILENAME}` — relatório DNA do megabrain (protocolo, genérico). "
        f"`dna.json` — os mesmos dados em JSON puro. `.dna-backup/` — versões anteriores.\n\n"
        "Gerado por `bin/mb-relatorio-dna.py` — nunca editar os arquivos desta pasta na mão; "
        "edite a fonte (`MEGABRAIN.md`, `SKILL.md`) e rode o script de novo.\n\n"
        "Procurando o relatório de UM projeto (não o protocolo)? É outro artefato: "
        "`RELATORIO.html` na raiz do projeto, gerado por `bin/mb-relatorio-projeto.py`.\n",
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
