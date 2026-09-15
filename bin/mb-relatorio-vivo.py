#!/usr/bin/env python3
"""
mb-relatorio-vivo.py — RELATORIO.html: retrato ao vivo do projeto pro
usuário deixar aberto no navegador enquanto os agentes trabalham (v6).

A página se recarrega sozinha (JS, a cada 15s, preservando scroll, painel
aberto e <details> abertos; não recarrega enquanto ele está mexendo).
Limite declarado: em file:// o navegador não consegue detectar mudança do
arquivo sem um servidor local, então o "ao vivo" é reload em intervalo fixo
— o usuário não aperta F5, mas há até 15s de atraso.

Fontes: PROGRESSO.json (etapas + notas, atualizado via --marcar/--nota),
ESTADO.md, HANDOFF.md (trava + seção "PARA VOCÊ"), DECISOES.md (últimos
títulos), .mb-log/ do dia, VERSAO.txt, git da central e os VERSAO.txt das
cópias MEGABRAIN/ dos projetos irmãos.

v6.1 (260821) — bloco de VERSÃO no topo:
  · versão atual do megabrain (VERSAO.txt) + commit git local, remoto
    conhecido (origin/main) e quantos commits locais ainda não subiram;
  · versão ANTERIOR (a que estava no ar na última troca de versão/commit);
  · tabela dos projetos: qual versão cada MEGABRAIN/ puxou vs a atual.
  Toda vez que a versão ou o commit muda, o HTML anterior é guardado em
  90_arquivo/relatorios-antigos/ (YYMMDD_HHMM_RELATORIO_<commit>.html) e o
  par atual/anterior fica em versao-atual.json na mesma pasta.
  Regeneração sem troca de versão NÃO gera snapshot (senão acumula a cada 15s
  de --nota).

v7.17 (260915) — pele e esqueleto do template POP v1.2
(motor/modelos/relatorios/260914_pop/, contrato em PADRAO.md):
  · ORQUESTRAÇÕES é o setor protagonista: pipeline da última run formal V6,
    runs recentes de .automations/runs/ (central, subpastas e irmãos), cotas
    de dados/orcamento_ia.json + dados/telemetria-orquestracao.json com a
    DATA de cada leitura, e papéis por modelo lidos do manifest da run;
  · a coleta de antes (frescor, versão, projetos, PROGRESSO, HANDOFF) alimenta
    os slots do POP; ações/skills/cérebro/documentos/histórico viram painéis
    no mesmo design;
  · contrato de clique: data-diz (toast), data-copia (clipboard com fallback)
    ou <a> real; o JS só usa textContent — dado do gerador nunca vira HTML.

Uso:
    python bin/mb-relatorio-vivo.py                        # só regenera
    python bin/mb-relatorio-vivo.py --marcar f2.1 feito "detalhe"
    python bin/mb-relatorio-vivo.py --marcar f2.2 fazendo
    python bin/mb-relatorio-vivo.py --nota "comecei a fase 2"
    python bin/mb-relatorio-vivo.py --snapshot    # força guardar o HTML atual
    python bin/mb-relatorio-vivo.py --saida %TEMP%\\teste.html  # prova sem tocar no vivo

Status válidos: pendente | fazendo | feito | bloqueado
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

import mb_utils as u
import mb_trava as trava
import mb_frescor as frescor
import mb_pop_tema

try:
    import mb_workspace as ws  # cérebro e telemetria: só os DADOS, a pele é a do POP
except Exception:  # sem o módulo: os painéis degradam para estado vazio
    ws = None

u.utf8_console()


RELOAD_SEGUNDOS = 15
STATUS_VALIDOS = {"pendente", "fazendo", "feito", "bloqueado"}
ICONE = {"feito": "✓", "fazendo": "●", "pendente": "○", "bloqueado": "✕"}
SNAPSHOTS_MAX = 30  # HTMLs anteriores guardados em 90_arquivo/relatorios-antigos/
RUNS_MAX = 4  # cards de run no setor ORQUESTRAÇÕES


def central() -> Path:
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# v6.1 — versão: VERSAO.txt + git + projetos + anterior
# ---------------------------------------------------------------------------

def _git(repo: Path, *args: str) -> str | None:
    try:
        # --no-optional-locks: leitura não cria index.lock (relatório roda a
        # cada 15s e em ambientes que não conseguem apagar o lock depois)
        r = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args],
                           capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def repo_git(c: Path) -> Path | None:
    """Onde está o git do megabrain: a central (se for repo) ou _github/repo-local/."""
    for cand in (c, c / "_github/repo-local"):
        if (cand / ".git").exists():
            return cand
    return None


def info_git(c: Path) -> dict:
    """HEAD local, origin/main conhecido, commits sem push, árvore suja.
    Nunca consulta a rede — é o que o git local sabe."""
    repo = repo_git(c)
    info = {"repo": str(repo) if repo else None, "head": None, "head_curto": "—",
            "assunto": "", "data": "", "origin": None, "origin_curto": "—",
            "sem_push": None, "suja": None}
    if not repo:
        return info
    head = _git(repo, "rev-parse", "HEAD")
    if head:
        info["head"] = head
        info["head_curto"] = head[:7]
        info["assunto"] = _git(repo, "log", "-1", "--format=%s") or ""
        info["data"] = _git(repo, "log", "-1", "--format=%cd", "--date=format:%Y-%m-%d %H:%M") or ""
    origin = _git(repo, "rev-parse", "origin/main")
    if origin:
        info["origin"] = origin
        info["origin_curto"] = origin[:7]
        n = _git(repo, "rev-list", "--count", "origin/main..HEAD")
        info["sem_push"] = int(n) if n and n.isdigit() else None
    st = _git(repo, "status", "--porcelain")
    info["suja"] = bool(st) if st is not None else None
    return info


def versao_resumida(linha: str | None) -> str:
    """'2026-08-19 · v6.0 — texto longo...' → 'v6.0 (2026-08-19)'."""
    if not linha:
        return "?"
    m = re.match(r"(\d{4}-\d{2}-\d{2})\s*·\s*v([\d.]+)", linha.strip())
    if m:
        return f"v{m.group(2)} ({m.group(1)})"
    return linha.strip()[:40]


def raiz_projetos(c: Path) -> Path:
    env = os.environ.get("MEGABRAIN_PROJETOS")
    return Path(env).resolve() if env else c.parent


def projetos_versao(c: Path, atual_linha: str | None) -> list[dict]:
    """Cada projeto irmão com MEGABRAIN/: versão que puxou vs a atual da central."""
    raiz = raiz_projetos(c)
    saida = []
    try:
        pastas = sorted(p for p in raiz.iterdir() if p.is_dir())
    except OSError:
        return saida
    for p in pastas:
        if p.resolve() == c.resolve():
            continue
        mb = p / "MEGABRAIN"
        if not mb.is_dir():
            continue
        puxada = u.read_first_non_empty_line(u.achar(mb, "VERSAO.txt"))
        origem = {}
        txt = u.safe_read_text(mb / ".mb-origem.json")
        if txt:
            try:
                origem = json.loads(txt)
            except (json.JSONDecodeError, ValueError):
                origem = {}
        if puxada and atual_linha and puxada.strip() == atual_linha.strip():
            estado = "atual"
        elif puxada:
            estado = "desatualizado"
        else:
            estado = "sem VERSAO.txt"
        saida.append({"projeto": p.name, "puxada": versao_resumida(puxada),
                      "commit": (origem.get("commit_central") or "")[:7],
                      "quando": (origem.get("sincronizado_em") or "")[:16].replace("T", " "),
                      "estado": estado})
    return saida


def pasta_arquivo(c: Path) -> Path:
    """Onde moram os relatórios que ficaram velhos.

    Saiu de .mb-backup/ (escondido, nome de backup) para 90_arquivo/ na v6.6:
    relatório vencido é histórico consultável, não lixo de sistema. A migração
    dos antigos acontece na primeira execução e não apaga nada.
    """
    try:
        base = u.pasta(c, "90_arquivo")
    except Exception:
        base = c / "90_arquivo"
    if not base.exists():
        base = c / "90_arquivo"
    destino = base / "relatorios-antigos"
    velha = c / ".mb-backup" / "relatorio-vivo"
    if velha.is_dir() and not destino.exists():
        try:
            destino.mkdir(parents=True, exist_ok=True)
            for item in velha.iterdir():
                if item.is_file() and not (destino / item.name).exists():
                    shutil.copy2(item, destino / item.name)
        except OSError:
            pass
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def indexar_arquivo(pasta: Path) -> None:
    """INDICE.md navegável — sem isso a pasta vira cemitério sem lápide."""
    arquivos = sorted((x for x in pasta.glob("*_RELATORIO*.html")), reverse=True)
    linhas = ["# Relatórios antigos", "",
              "Cada arquivo aqui é o relatório como ele estava ANTES de uma troca de",
              "versão ou de commit. O relatório vivo (`00_painel/RELATORIO.html`) é",
              "sempre o atual; estes são o histórico. Guardados automaticamente pelo",
              "`bin/mb-relatorio-vivo.py`; os mais velhos são podados após "
              f"{SNAPSHOTS_MAX}.", "",
              "| quando | commit | arquivo |", "|---|---|---|"]
    for a in arquivos:
        partes = a.stem.split("_")
        quando = f"{partes[0]} {partes[1][:2]}:{partes[1][2:]}" if len(partes) > 1 else partes[0]
        commit = partes[-1] if len(partes) > 2 else "—"
        linhas.append(f"| {quando} | `{commit}` | [{a.name}](./{a.name}) |")
    linhas.append("")
    try:
        # newline explícito: Path.write_text usa CRLF no Windows e fazia
        # git diff --check acusar whitespace em cada linha da tabela.
        u.atomic_write_text(pasta / "INDICE.md", "\n".join(linhas))
    except OSError:
        pass


def estado_versao(c: Path, atual: dict, forcar_snapshot: bool = False) -> dict:
    """Guarda o par atual/anterior e o snapshot do HTML quando a versão ou o
    commit muda. Retorna {'atual':..., 'anterior':..., 'snapshot': path|None}."""
    pasta = pasta_arquivo(c)
    arq = pasta / "versao-atual.json"
    dados = {}
    txt = u.safe_read_text(arq)
    if txt:
        try:
            dados = json.loads(txt)
        except (json.JSONDecodeError, ValueError):
            dados = {}
    anterior = dados.get("anterior") or {}
    guardado = dados.get("atual") or {}
    chave = ("versao", "commit")
    mudou = any(guardado.get(k) != atual.get(k) for k in chave)
    snapshot = None
    html_atual = u.achar(c, "RELATORIO.html")
    if (mudou and guardado) or forcar_snapshot:
        if html_atual.is_file():
            try:
                pasta.mkdir(parents=True, exist_ok=True)
                rotulo = (guardado.get("commit") or atual.get("commit") or "semgit")[:7]
                nome = f"{dt.datetime.now():%y%m%d_%H%M}_RELATORIO_{rotulo}.html"
                snapshot = pasta / nome
                shutil.copy2(html_atual, snapshot)
                # poda: mantém os SNAPSHOTS_MAX mais recentes
                antigos = sorted(x for x in pasta.glob("*_RELATORIO*.html"))
                for velho in antigos[:-SNAPSHOTS_MAX]:
                    try:
                        velho.unlink()
                    except OSError:
                        pass
            except OSError:
                snapshot = None
        indexar_arquivo(pasta)
    if mudou:
        if guardado:
            anterior = dict(guardado)
            anterior["saiu_em"] = dt.datetime.now().astimezone().isoformat(timespec="minutes")
        dados = {"atual": atual, "anterior": anterior,
                "atualizado": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
        u.atomic_write_text(arq, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")
    return {"atual": atual, "anterior": anterior, "snapshot": snapshot}


def secao_para_voce(c: Path) -> list[str]:
    """Linhas da seção '## PARA VOCÊ' (ou 'PARA O <nome>') do HANDOFF.md —
    o que o humano precisa fazer agora, separado do que é pro próximo agente."""
    texto = u.safe_read_text(u.achar(c, "HANDOFF.md")) or ""
    m = re.search(r"^##+\s*PARA (?:VOC[EÊ]|O USU[AÁ]RIO|O \w+)\b[^\n]*\n(.*?)(?=^##|\Z)",
                  texto, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    linhas: list[str] = []
    for bruta in m.group(1).splitlines():
        s = bruta.strip()
        if not s or s.startswith("<!--"):
            continue
        eh_item = re.match(r"^(\d+[.)]|[-*•])\s+", s)
        s = re.sub(r"^(\d+[.)]|[-*•])\s*", "", s)
        if eh_item or not linhas:
            linhas.append(s)
        else:
            linhas[-1] += " " + s  # continuação do item anterior
    return linhas


def carregar_progresso(c: Path) -> dict:
    arq = u.achar(c, "PROGRESSO.json")
    texto = u.safe_read_text(arq)
    if texto:
        try:
            return json.loads(texto)
        except (json.JSONDecodeError, ValueError):
            pass
    return {"projeto": "megabrain", "etapas": [], "notas": []}


def salvar_progresso(c: Path, dados: dict) -> bool:
    dados["atualizado"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    return u.atomic_write_text(u.achar(c, "PROGRESSO.json"),
                               json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def ler_trava(c: Path):
    texto = u.safe_read_text(u.achar(c, "HANDOFF.md")) or ""
    quem = ate = "-"
    m = re.search(r"^TRAVADO_POR:\s*(.+)$", texto, re.MULTILINE)
    # O bloco do mb-sync fica no fim do arquivo; a última ocorrência vale.
    for m in re.finditer(r"^TRAVADO_POR:\s*(.+)$", texto, re.MULTILINE):
        quem = m.group(1).strip()
    for m in re.finditer(r"^AT[EÉ]:\s*(.+)$", texto, re.MULTILINE):
        ate = m.group(1).strip()
    return quem, ate


def ultimas_decisoes(c: Path, n=3):
    texto = u.safe_read_text(u.achar(c, "DECISOES.md")) or ""
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
        # v7.5: "arquivo" chega como lista em evento de escrita múltipla — o
        # html.escape() quebrava o relatório inteiro. Campo de log é dado de
        # fora: normaliza pra texto antes de confiar no tipo.
        if isinstance(resumo, (list, tuple)):
            resumo = ", ".join(str(x) for x in resumo)
        elif not isinstance(resumo, str):
            resumo = str(resumo)
        if len(resumo) > 90:
            resumo = resumo[:90] + "…"
        linhas.append((ev.get("ts", "")[11:19], ev.get("agente", "?"),
                       ev.get("evento", "?"), resumo))
    return linhas[::-1]


def fila_pendentes(c: Path) -> list[dict]:
    """alteracoes-pendentes/ com dono + idade (v6 fase 4: fila sem dono era
    um dos 7 problemas de lógica do diagnóstico)."""
    base = u.pasta(c, "alteracoes-pendentes")
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


e = html.escape  # escape de modulo: `e` local so existe dentro de gerar_html  # escape de módulo: todo dado do gerador passa por aqui antes do HTML


def _estado_json(c: Path) -> dict:
    """O relatório passa a RENDERIZAR dados/estado.json em vez de recalcular.

    260825 (decisão 260825t): uma fonte, duas renderizações. O mesmo JSON que
    alimenta este HTML é o que qualquer IA lê — Claude, Kimi, GPT, Gemini,
    Codex — sem parsear markdown de prosa. Foi o que permitiu o relatório de
    agentes e o de padrões morrerem: eles não tinham dado próprio, tinham
    leitura própria do mesmo dado.
    """
    import json
    arq = c / "dados" / "estado.json"
    txt = u.safe_read_text(arq)
    if not txt:
        return {}
    try:
        return json.loads(txt)
    except (json.JSONDecodeError, ValueError):
        return {}


def _timeline_versao(c: Path, n: int = 6) -> list[dict]:
    """Histórico lido do VERSAO.txt — a fonte já existe, não invente outra."""
    txt = u.safe_read_text(u.achar(c, "VERSAO.txt")) or ""
    itens = []
    for m in re.finditer(r"^(\d{4})-(\d{2})-(\d{2})\s*·\s*(v[\d.]+)\s*—\s*(.+)$",
                         txt, re.MULTILINE):
        aaaa, mm, dd, ver, resto = m.groups()
        cabeca, _, cauda = resto.partition(":")
        itens.append({
            "data": f"{aaaa[2:]}{mm}{dd}",
            "titulo": f"{ver} — {cabeca.strip()}",
            "det": " ".join(cauda.split())[:150],
            "status": "ativo" if not itens else "ok",
        })
        if len(itens) >= n:
            break
    return itens


# CSS do template POP v1.2, copiado sem alteração de
# motor/modelos/relatorios/260914_pop/relatorio-pop.html (bloco <style>).
# O template é a fonte: mudou lá, copie de novo aqui; o que é só do gerador
# fica em CSS_POP_EXTRA, que vem depois e sobrescreve.
CSS_POP = """
  :root{
    --fundo:#0B0B16; --fundo2:#12121F; --card:#191927; --card2:#1F1F30;
    --tinta:#FFFFFF; --corpo:#C9C7E0; --fraco:#8B89A6;
    --linha:rgba(255,255,255,.10);
    --coral:#FF4B4B; --verde:#58CC02; --azul:#1CB0F6; --amarelo:#FFC800; --roxo:#CE82FF; --rosa:#FF82C4;
    --sombra-card:0 14px 38px rgba(0,0,0,.45);
    --mono:ui-monospace,"Cascadia Mono",Consolas,monospace;
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{margin:0;background:var(--fundo);color:var(--tinta);
    font:16px/1.45 "Segoe UI",system-ui,sans-serif;overflow-x:hidden}
  body::before{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;
    background:
      radial-gradient(58rem 30rem at 50% -12%, rgba(124,58,237,.55) 0%, transparent 65%),
      radial-gradient(34rem 20rem at 82% 6%, rgba(236,72,153,.30) 0%, transparent 60%),
      radial-gradient(30rem 18rem at 8% 12%, rgba(28,176,246,.20) 0%, transparent 60%),
      linear-gradient(180deg, var(--fundo2) 0%, var(--fundo) 40%);}
  .wrap{max-width:62rem;margin-inline:auto;padding:0 1.1rem 3rem}

  @supports (animation-timeline: scroll()){
    body::after{content:"";position:fixed;top:0;left:0;right:0;height:4px;z-index:99;
      background:linear-gradient(90deg,var(--roxo),var(--verde),var(--amarelo),var(--coral));
      transform-origin:0 50%;animation:ler linear both;animation-timeline:scroll(root block)}
    @keyframes ler{from{transform:scaleX(0)}to{transform:scaleX(1)}}
  }

  /* ═══ HERO compacto ═══ */
  .hero{display:grid;grid-template-columns:auto 1fr;gap:1.1rem;align-items:center;
    padding:2.4rem 0 1.6rem}
  .mascote{width:92px;height:auto;display:block;cursor:pointer;
    animation:flutua 4.5s ease-in-out infinite;transition:transform .18s ease}
  .mascote:active{transform:scale(.94)}
  .mascote.vibra{animation:vibra .5s ease}
  @keyframes flutua{50%{transform:translateY(-7px)}}
  @keyframes vibra{25%{transform:rotate(-7deg)}75%{transform:rotate(7deg)}}
  .pill{display:inline-flex;align-items:center;gap:.45rem;padding:.32rem .85rem;border-radius:99px;
    background:rgba(206,130,255,.16);border:1px solid rgba(206,130,255,.45);color:var(--roxo);
    font:700 .74rem var(--mono);letter-spacing:.06em}
  .pill i{width:.5rem;height:.5rem;border-radius:50%;background:var(--verde);box-shadow:0 0 10px var(--verde)}
  .hero h1{margin:.45rem 0 .15rem;font-size:clamp(2.4rem,7vw,3.8rem);font-weight:800;letter-spacing:-.045em;line-height:1;
    background:linear-gradient(180deg,#fff 30%,#C4B5FD 85%);-webkit-background-clip:text;background-clip:text;color:transparent;
    filter:drop-shadow(0 8px 34px rgba(124,58,237,.45))}
  .hero .sub{color:var(--corpo);font:500 .85rem var(--mono)}
  .hero .sub b{color:var(--verde)}
  .hero .frescor{margin:.35rem 0 0;color:var(--fraco);font-size:.72rem}

  /* ═══ SETOR ═══ */
  .setor{margin:1.5rem 0;border-radius:20px;background:var(--card);
    border:3px solid var(--c,var(--linha));box-shadow:var(--sombra-card);overflow:hidden}
  .setor > header{display:flex;align-items:center;gap:.8rem;padding:.85rem 1.1rem;
    background:linear-gradient(90deg, color-mix(in oklab, var(--c) 22%, transparent), transparent 70%)}
  .setor .ico{width:44px;height:44px;border-radius:13px;background:var(--c);display:grid;place-items:center;flex:0 0 auto;
    box-shadow:0 5px 15px color-mix(in oklab, var(--c) 55%, transparent)}
  .setor .ico svg{width:24px;height:24px}
  .setor h2{margin:0;font-size:1.18rem;font-weight:800;letter-spacing:-.02em}
  .setor .desc{margin:1px 0 0;color:var(--corpo);font-size:.8rem}
  .setor .corpo{padding:.95rem 1.1rem 1.05rem}

  /* ═══ ORQUESTRAÇÕES ═══ */
  .gates{display:grid;grid-template-columns:repeat(8,1fr);gap:4px;margin:0 0 .8rem}
  @media(max-width:48rem){.gates{grid-template-columns:repeat(4,1fr)}}
  .gate{border-radius:10px;padding:.45rem .5rem .4rem;background:var(--card2);border-top:4px solid var(--line,rgba(255,255,255,.2));cursor:pointer;position:relative}
  .gate b{display:block;font:800 .8rem var(--mono)}
  .gate span{font-size:.58rem;color:var(--fraco);line-height:1.25;display:block}
  .gate--ok{border-top-color:var(--verde)} .gate--ok b{color:var(--verde)}
  .gate--trava{border-top-color:var(--amarelo);background:color-mix(in oklab,var(--amarelo) 12%,var(--card2))}
  .gate--trava b{color:var(--amarelo)}
  .gate--espera{border-top-color:rgba(255,255,255,.18)}
  .gates-leg{margin:.1rem 0 .55rem;font:600 .68rem var(--mono);color:var(--fraco)}
  .gates-leg b{color:var(--amarelo)}
  .orc-grid{display:grid;gap:.7rem}
  @media(min-width:52rem){.orc-grid{grid-template-columns:1.1fr .9fr}}
  .runs{display:flex;flex-direction:column;gap:.5rem}
  .run{display:grid;grid-template-columns:auto 1fr auto;gap:.6rem;align-items:center;
    background:var(--card2);border-radius:12px;padding:.55rem .75rem;cursor:pointer}
  .run .st{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;font-size:1rem}
  .run--ok .st{background:color-mix(in oklab,var(--verde) 20%,transparent)}
  .run--warn .st{background:color-mix(in oklab,var(--amarelo) 20%,transparent)}
  .run b{font-size:.84rem;display:block}
  .run small{color:var(--fraco);font-size:.68rem}
  .run .q{font:700 .68rem var(--mono);color:var(--fraco)}
  .run--ok .q{color:var(--verde)} .run--warn .q{color:var(--amarelo)}
  .cotas{display:flex;flex-direction:column;gap:.45rem}
  .cota{display:grid;grid-template-columns:auto 1fr auto;gap:.6rem;align-items:center;
    background:var(--card2);border-radius:12px;padding:.5rem .7rem}
  .cota .dot{width:11px;height:11px;border-radius:50%}
  .cota--ok .dot{background:var(--verde);box-shadow:0 0 10px var(--verde)}
  .cota--warn .dot{background:var(--amarelo);box-shadow:0 0 10px var(--amarelo)}
  .cota b{font-size:.82rem}
  .cota small{display:block;color:var(--fraco);font-size:.66rem}
  .cota .ritmo{font:800 .64rem var(--mono);padding:.15rem .5rem;border-radius:8px}
  .cota--ok .ritmo{color:var(--verde);background:color-mix(in oklab,var(--verde) 16%,transparent)}
  .cota--warn .ritmo{color:var(--amarelo);background:color-mix(in oklab,var(--amarelo) 16%,transparent)}
  .papeis{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.7rem}
  .papel{font:700 .7rem var(--mono);padding:.28rem .6rem;border-radius:9px;background:var(--card2);
    border:1px solid color-mix(in oklab,var(--roxo) 40%,transparent);cursor:pointer}
  .papel b{color:var(--roxo)}

  /* ═══ cards de ação + botões ═══ */
  .acoes-voce{display:grid;gap:.7rem}
  @media(min-width:56rem){.acoes-voce{grid-template-columns:repeat(3,1fr)}}
  .acao{background:var(--card2);border:2px solid color-mix(in oklab, var(--c) 55%, transparent);
    border-radius:16px;padding:.8rem .85rem;display:flex;flex-direction:column;gap:.45rem}
  .acao .n{font:800 .68rem var(--mono);color:var(--c);letter-spacing:.12em}
  .acao h3{margin:0;font-size:.95rem;line-height:1.3}
  .acao p{margin:0;color:var(--corpo);font-size:.8rem;flex:1}
  .acao .rodape-btn{display:flex;gap:.5rem;flex-wrap:wrap}
  .btn{display:inline-block;text-align:center;padding:.58rem .95rem;border-radius:12px;border:0;cursor:pointer;
    background:var(--c,var(--roxo));color:#0B0B16;font-weight:800;font-size:.85rem;text-decoration:none;
    box-shadow:0 4px 0 color-mix(in oklab, var(--c,#CE82FF) 60%, #000);
    transition:transform .08s ease, box-shadow .08s ease, filter .12s ease}
  .btn:hover{filter:brightness(1.06)}
  .btn:active{transform:translateY(3px);box-shadow:0 1px 0 color-mix(in oklab, var(--c,#CE82FF) 60%, #000)}
  .btn:focus-visible{outline:3px solid var(--roxo);outline-offset:2px}
  .btn--sec{background:transparent;color:var(--tinta);border:2px solid color-mix(in oklab, var(--c) 55%, transparent);
    box-shadow:0 3px 0 color-mix(in oklab, var(--c) 35%, #000)}
  .btn--sec:active{box-shadow:0 1px 0 color-mix(in oklab, var(--c) 35%, #000)}

  .saude{display:grid;grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));gap:.6rem}
  .s-chip{background:var(--card2);border-radius:14px;padding:.7rem .8rem;display:flex;gap:.6rem;align-items:center;
    border:2px solid transparent;cursor:pointer;transition:transform .12s ease}
  .s-chip:hover{transform:translateY(-2px)}
  .s-chip .si{width:36px;height:36px;border-radius:10px;display:grid;place-items:center;flex:0 0 auto}
  .s-chip .si svg{width:20px;height:20px}
  .s-chip b{display:block;font-size:.9rem}
  .s-chip span{color:var(--fraco);font-size:.68rem}
  .ok   {border-color:color-mix(in oklab,var(--verde) 55%,transparent)} .ok .si{background:color-mix(in oklab,var(--verde) 22%,transparent)} .ok .si svg{color:var(--verde)}
  .info {border-color:color-mix(in oklab,var(--azul) 55%,transparent)} .info .si{background:color-mix(in oklab,var(--azul) 22%,transparent)} .info .si svg{color:var(--azul)}

  .fig{background:var(--card2);border:1px solid var(--linha);border-radius:14px;padding:.8rem .9rem .6rem;margin:0 0 .7rem}
  .fig figcaption b{font:700 .74rem var(--mono);color:var(--azul)}
  .fig .cap{margin:.4rem 0 0;color:var(--fraco);font:.66rem/1.4 var(--mono)}
  .figs{display:grid;gap:.8rem}
  @media(min-width:52rem){.figs{grid-template-columns:1.2fr .8fr}}
  .share{display:flex;height:2.1rem;border-radius:11px;overflow:hidden;border:2px solid var(--linha)}
  .share i{display:flex;align-items:center;justify-content:center;font:800 .74rem var(--mono);color:#0B0B16}
  .legenda{display:flex;flex-wrap:wrap;gap:.8rem;margin-top:.5rem;font-size:.74rem;color:var(--corpo)}
  .legenda b{color:var(--tinta)}
  .pt{display:inline-block;width:.65rem;height:.65rem;border-radius:3px;margin-right:.3rem;vertical-align:-1px}
  .spark{display:flex;align-items:flex-end;gap:.45rem;height:5.6rem;padding:.2rem .1rem 0}
  .spark .col{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:.25rem;height:100%}
  .spark .bar{width:100%;max-width:2.1rem;border-radius:5px 5px 0 0;background:var(--azul);height:calc(var(--h)*.78%);min-height:3px;
    box-shadow:0 0 14px rgba(28,176,246,.28)}
  .spark .col:hover .bar{filter:brightness(1.25)}
  .spark .v{font:700 .58rem var(--mono);color:var(--corpo)}
  .spark .r{font:.56rem var(--mono);color:var(--fraco);white-space:nowrap}

  .resumo-1linha{display:flex;align-items:center;gap:.9rem;flex-wrap:wrap}
  .anelzinho{position:relative;width:78px;height:78px;cursor:pointer}
  .anelzinho .t{position:absolute;inset:0;display:grid;place-items:center;font:800 .95rem var(--mono)}
  details.variancia{margin-top:.8rem}
  details.variancia summary{cursor:pointer;font-weight:700;color:var(--azul);list-style:none;user-select:none}
  details.variancia summary::-webkit-details-marker{display:none}
  details.variancia summary:focus-visible{outline:3px solid var(--roxo);outline-offset:3px}
  details.variancia summary::before{content:"▸ "}
  details[open].variancia summary::before{content:"▾ "}
  .tabela-wrap{max-height:14rem;overflow:auto;border:1px solid var(--linha);border-radius:11px;margin-top:.6rem}
  table{width:100%;border-collapse:collapse;font-size:.76rem}
  th{position:sticky;top:0;background:var(--card);text-align:left;font:700 .62rem var(--mono);text-transform:uppercase;
    letter-spacing:.08em;color:var(--fraco);padding:.45rem .65rem;border-bottom:1px solid var(--linha)}
  td{padding:.38rem .65rem;border-bottom:1px solid var(--linha);color:var(--corpo)}
  td b{color:var(--tinta)}

  /* ═══ PANES (abas no MESMO design) ═══ */
  .panes-nav{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center;margin:1.8rem 0 0}
  .pn{display:inline-flex;align-items:center;gap:.45rem;padding:.6rem 1rem;border-radius:14px;cursor:pointer;
    background:var(--card);border:1px solid var(--linha);color:var(--tinta);font-weight:700;font-size:.84rem;
    transition:transform .12s ease,border-color .12s ease}
  .pn:hover{transform:translateY(-2px);border-color:var(--roxo)}
  .pn[aria-pressed="true"]{background:color-mix(in oklab,var(--roxo) 18%,var(--card));border-color:var(--roxo)}
  .pn:focus-visible{outline:3px solid var(--roxo);outline-offset:2px}
  .pn svg{width:17px;height:17px;color:var(--roxo)}
  .pane-pop{margin:1rem 0 0;border:2px solid color-mix(in oklab, var(--c,var(--roxo)) 45%,transparent)}
  .pane-pop[hidden]{display:none}
  .pane-pop > header{padding:.6rem .95rem}
  .pane-pop > header .ico{width:36px;height:36px;border-radius:10px}
  .pane-pop > header .ico svg{width:19px;height:19px}
  .pane-pop > header h2{font-size:1rem}
  .lista-acoes{display:grid;gap:.45rem}
  @media(min-width:52rem){.lista-acoes{grid-template-columns:1fr 1fr}}
  .it{display:grid;grid-template-columns:auto 1fr auto;gap:.6rem;align-items:center;
    background:var(--card2);border-radius:11px;padding:.5rem .7rem;cursor:pointer}
  .it .num{font:800 .85rem var(--mono);color:var(--roxo);width:1.6rem}
  .it b{font-size:.82rem;display:block}
  .it small{color:var(--fraco);font-size:.68rem;display:block}
  .it .go{font:800 .7rem var(--mono);color:var(--fraco)}
  .it:hover .go{color:var(--roxo)}
  .skills-grid{display:grid;gap:.45rem}
  @media(min-width:52rem){.skills-grid{grid-template-columns:1fr 1fr}}
  .sk{display:grid;grid-template-columns:1fr auto;gap:.5rem;align-items:center;
    background:var(--card2);border-radius:11px;padding:.5rem .7rem;cursor:pointer}
  .sk b{font:700 .8rem var(--mono);color:var(--azul)}
  .sk small{color:var(--fraco);font-size:.68rem;display:block;margin-top:1px}
  .sk .go{color:var(--fraco)}
  .cerebro-3{display:grid;gap:.6rem}
  @media(min-width:52rem){.cerebro-3{grid-template-columns:repeat(3,1fr)}}
  .cb{background:var(--card2);border-radius:13px;padding:.7rem .8rem}
  .cb-tit{font-size:.88rem;cursor:pointer}
  .cb-tit:focus-visible{outline:3px solid var(--roxo);outline-offset:2px}
  .cb small{color:var(--fraco);font-size:.7rem;display:block;margin:.25rem 0 .5rem}
  .docs-lista{display:grid;gap:.4rem}
  .doc{display:grid;grid-template-columns:auto 1fr auto;gap:.55rem;align-items:center;
    background:var(--card2);border-radius:10px;padding:.45rem .65rem;cursor:pointer}
  .doc .ic{font-size:.9rem}
  .doc b{font-size:.78rem}
  .doc small{color:var(--fraco);font-size:.66rem;display:block}
  .doc .go{font:700 .66rem var(--mono);color:var(--fraco)}

  /* foco visível em tudo que é clicável */
  .chip:focus-visible,.s-chip:focus-visible,.anelzinho:focus-visible,.mascote:focus-visible,
  .gate:focus-visible,.run:focus-visible,.papel:focus-visible,.it:focus-visible,.sk:focus-visible,.doc:focus-visible,
  .cota:focus-visible{
    outline:3px solid var(--roxo);outline-offset:2px}

  /* ═══ TOAST ═══ */
  #toasts{position:fixed;bottom:1.1rem;left:50%;transform:translateX(-50%);z-index:100;
    display:flex;flex-direction:column;gap:.45rem;align-items:center;pointer-events:none;max-width:min(92vw,34rem)}
  .toast{display:flex;align-items:center;gap:.55rem;padding:.62rem 1rem;border-radius:13px;
    background:var(--card2);border:2px solid var(--verde);color:var(--tinta);font-weight:600;font-size:.85rem;
    box-shadow:0 12px 34px rgba(0,0,0,.55);animation:surge-toast .22s ease both}
  .toast.err{border-color:var(--coral)}
  .toast .t-ico{color:var(--verde);flex:0 0 auto}
  .toast.err .t-ico{color:var(--coral)}
  .toast small{display:block;color:var(--fraco);font-weight:500}
  @keyframes surge-toast{from{opacity:0;transform:translateY(10px) scale(.96)}to{opacity:1;transform:none}}
  .toast.saindo{transition:opacity .25s ease, transform .25s ease;opacity:0;transform:translateY(8px)}

  /* sem animação de carga: a página nasce no estado final (print headless e leitores sem JS veem tudo) */
  @media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}html{scroll-behavior:auto}}
  .nota{margin-top:1.8rem;color:var(--fraco);font-size:.7rem;text-align:center}
"""


# ---------------------------------------------------------------------------
# v7.17 — ORQUESTRAÇÕES: runs V6, cotas e papéis (fotografia com fonte e data)
# ---------------------------------------------------------------------------

def _ler_json(arq: Path):
    txt = u.safe_read_text(arq)
    if not txt:
        return None
    try:
        return json.loads(txt)
    except (json.JSONDecodeError, ValueError):
        return None


def _quando(iso) -> str:
    """ISO (UTC ou com fuso) → 'dd/mm HH:MM' no fuso local; '—' se não há data."""
    if not iso:
        return "—"
    try:
        d = dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return str(iso)[:16]
    if d.tzinfo is not None:
        d = d.astimezone()
    return f"{d:%d/%m %H:%M}"


def pastas_runs(c: Path) -> list[tuple[str, Path]]:
    """(projeto, pasta) de toda .automations/runs/<run>/ conhecida, da mais nova
    pra mais velha. Procura na central, nas subpastas dela (pets/ roda a V6
    dentro da central) e nos projetos irmãos. O nome da pasta começa com
    AAMMDD_HHMMSS, então ordenar pelo nome é ordenar pelo tempo."""
    bases: list[tuple[str, Path]] = [("megabrain", c)]
    try:
        bases += [(p.name, p) for p in sorted(c.iterdir())
                  if p.is_dir() and not p.name.startswith((".", "_", "9"))]
    except OSError:
        pass
    try:
        bases += [(p.name, p) for p in sorted(raiz_projetos(c).iterdir())
                  if p.is_dir() and p.resolve() != c.resolve()]
    except OSError:
        pass
    achadas = []
    for nome, base in bases:
        runs = base / ".automations" / "runs"
        if not runs.is_dir():
            continue
        try:
            achadas += [(nome, r) for r in runs.iterdir()
                        if r.is_dir() and re.match(r"\d{6}_\d{6}_", r.name)]
        except OSError:
            continue
    achadas.sort(key=lambda x: x[1].name, reverse=True)
    return achadas


def resumo_run(projeto: str, pasta: Path) -> dict:
    """O que a run gravou no disco — state, result, manifest, route e o
    status.json de cada estágio. Campo ausente fica None, nunca inventado."""
    state = _ler_json(pasta / "state.json") or {}
    result = _ler_json(pasta / "result.json") or {}
    manifest = _ler_json(pasta / "manifest.json") or {}
    route = _ler_json(pasta / "route.json") or {}
    estagios = []
    base = pasta / "stages"
    if base.is_dir():
        for s in base.iterdir():
            st = _ler_json(s / "status.json") or {}
            estagios.append({"id": s.name, "status": st.get("status") or "sem status",
                             "provider": st.get("provider") or "?",
                             "inicio": st.get("started_at"), "fim": st.get("finished_at"),
                             "erro": st.get("error")})
    estagios.sort(key=lambda x: (x["inicio"] or "", x["id"]))
    aplicacao = None
    m = re.search(r"^Aplica[çc][ãa]o ao projeto:\s*(.+)$",
                  u.safe_read_text(pasta / "HANDOFF.md") or "", re.MULTILINE)
    if m:
        aplicacao = m.group(1).strip()
    job = manifest.get("job") or {}
    return {"projeto": projeto, "pasta": pasta, "nome": pasta.name,
            "modo": manifest.get("mode") or "?",
            "status": state.get("status") or result.get("status") or "sem state.json",
            "em": state.get("at") or manifest.get("created_at"),
            "erro": state.get("error"),
            "objetivo": " ".join(str(job.get("objective") or "").split()),
            "perfil": route.get("effective_profile"),
            "result": result, "estagios": estagios, "aplicacao": aplicacao,
            "config": manifest.get("config") or {}}


ROTULO_RUN = {
    "verified": ("ok", "✅", "VERIFICADA"),
    "review_approved": ("ok", "✅", "REVISÃO APROVADA"),
    "needs_attention": ("warn", "⚠️", "PRECISA DE ATENÇÃO"),
}

FASES_V6 = [("plan", "Plano", "plano"),
            ("plan-review", "Rev. plano", "revisão do plano"),
            ("candidate", "Candidato", "candidato"),
            ("review", "Rev. final", "revisão final")]


def rotulo_run(status: str) -> tuple[str, str, str]:
    return ROTULO_RUN.get(status, ("warn", "⚠️", status.replace("_", " ").upper()))


def gates_run(run: dict) -> list[dict]:
    """Trilha da pipeline V6 da run: cada fase só fica verde se o status.json
    do estágio diz 'succeeded' (e, nas revisões, o result.json diz aprovado).
    A fase onde a run parou fica amarela; o que vem depois fica 'não rodou'."""
    res = run["result"]
    gates: list[dict] = []
    parou = False
    for chave, curto, longo in FASES_V6:
        est = [x for x in run["estagios"] if re.fullmatch(rf"{chave}-\d+", x["id"])]
        if parou or not est:
            gates.append({"curto": curto, "estado": "espera",
                          "diz": f"{longo}: não rodou nesta run"
                                 + (" — a pipeline parou antes." if parou else ".")})
            continue
        ultimo = est[-1]
        quem = ", ".join(sorted({x["provider"] for x in est}))
        if ultimo["status"] != "succeeded":
            parou = True
            gates.append({"curto": curto, "estado": "trava",
                          "diz": f"{longo}: ONDE A RUN PAROU — estágio {ultimo['id']} "
                                 f"{ultimo['status']}"
                                 + (f" ({ultimo['erro']})" if ultimo["erro"] else "")
                                 + f" · {quem} · {_quando(ultimo['fim'])}."})
            continue
        aprovado = {"plan-review": res.get("plan_review_approved"),
                    "review": res.get("review_approved")}.get(chave)
        if aprovado is False:
            parou = True
            gates.append({"curto": curto, "estado": "trava",
                          "diz": f"{longo}: rodou ({len(est)} rodada(s), {quem}) mas NÃO aprovou."})
            continue
        gates.append({"curto": curto, "estado": "ok",
                      "diz": f"{longo}: {len(est)} rodada(s) · {quem} · concluído "
                             f"{_quando(ultimo['fim'])}"
                             + (" · aprovado no result.json." if aprovado else ".")})
    # run que terminou mal sem estágio falho (ex.: revisor não cobriu critério):
    # a última fase que rodou é onde ela parou.
    if rotulo_run(run["status"])[0] != "ok" and not any(g["estado"] == "trava" for g in gates):
        feitos = [g for g in gates if g["estado"] == "ok"]
        if feitos:
            feitos[-1]["estado"] = "trava"
            feitos[-1]["diz"] += (f" A run terminou em {run['status']}"
                                  + (f": {run['erro']}" if run["erro"] else "") + ".")
    checks = res.get("automated_checks")
    if not res:
        gates.append({"curto": "Checagem", "estado": "espera",
                      "diz": "checagem automática: sem result.json nesta run."})
    elif checks:
        ok = res.get("automated_checks_passed") is True
        gates.append({"curto": "Checagem", "estado": "ok" if ok else "trava",
                      "diz": f"checagem automática: {len(checks)} item(ns) · "
                             + ("passou." if ok else "NÃO passou.")})
    else:
        gates.append({"curto": "Checagem", "estado": "espera",
                      "diz": "checagem automática: nenhuma rodou nesta run "
                             f"(código executado: {res.get('code_executed')})."})
    gates.append({"curto": "Aplicação", "estado": "espera",
                  "diz": "aplicação ao projeto: " + (run["aplicacao"] or "não informada no HANDOFF da run")
                         + " — a V6 não aplica sozinha; quem confere e aplica é o orquestrador."})
    return gates


PAPEIS_V6 = [("plan", "plano", "produz o plano"),
             ("plan_review", "rev. plano", "revisa o plano antes de executar"),
             ("candidate", "produz", "produz a entrega candidata"),
             ("final_review", "final", "faz a revisão final")]


def papeis_run(run: dict) -> list[dict]:
    """Quem fez o quê na run, lido do manifest (perfil efetivo do route.json)."""
    cfg = run["config"]
    perfil = run["perfil"] or ""
    papeis = ((cfg.get("workflow") or {}).get("profiles") or {}).get(perfil) or {}
    provs = cfg.get("providers") or {}
    saida = []
    for chave, curto, longo in PAPEIS_V6:
        p = papeis.get(chave) or {}
        if not p.get("provider"):
            continue
        modelo = (provs.get(p["provider"]) or {}).get("model") or "modelo não declarado"
        saida.append({"curto": curto, "quem": f"{p['provider']} {p.get('effort') or ''}".strip(),
                      "diz": f"{longo}: {p['provider']} ({modelo}), esforço {p.get('effort') or '?'} — "
                             f"perfil {perfil} da run {run['nome']} ({run['projeto']}). "
                             "Fonte: manifest.json + route.json da run."})
    return saida


ORDEM_COTAS = ["claude", "codex", "spark", "zai"]


def _rotulo_janela(ident: str) -> str:
    if ident == "session":
        return "sessão"
    if ident == "weekly_all":
        return "semana"
    if ident.startswith("weekly_scoped:"):
        return "semana " + ident.split(":", 1)[1]
    return ident


def cotas(c: Path) -> dict:
    """Cotas por provedor. Duas fontes, cada uma com a data dela:
    dados/orcamento_ia.json (ritmo por janela, updated_at por provedor) e o
    último registro de cada provedor em dados/telemetria-orquestracao.json
    (o que a última run viu). Nada aqui é 'ao vivo' — é a última fotografia."""
    orc = _ler_json(c / "dados" / "orcamento_ia.json") or {}
    tel = _ler_json(c / "dados" / "telemetria-orquestracao.json") or {}
    recentes = tel.get("recent") or []
    ultima_tel: dict[str, dict] = {}
    for ev in recentes:
        for prov, d in (ev.get("providers") or {}).items():
            ultima_tel[prov] = {"at": ev.get("at"), "moment": ev.get("moment"),
                                "status": d.get("status"), "pacing": d.get("pacing")}
    provs = [p for p in ORDEM_COTAS if p in orc or p in ultima_tel]
    provs += sorted(p for p in set(orc) | set(ultima_tel) if p not in provs)
    itens = []
    for prov in provs:
        o = orc.get(prov) or {}
        pacing = o.get("pacing") or {}
        janelas = pacing.get("windows") or {}
        partes = [f"{_rotulo_janela(k)} {float(v.get('used_percent')):.0f}%"
                  for k, v in janelas.items() if isinstance(v, dict)
                  and isinstance(v.get("used_percent"), (int, float))]
        t = ultima_tel.get(prov)
        status = pacing.get("status")
        if status:
            fonte = f"dados/orcamento_ia.json, leitura {_quando(o.get('updated_at'))}"
        elif t:
            status = t.get("pacing") or t.get("status")
            fonte = f"telemetria-orquestracao.json, leitura {_quando(t.get('at'))}"
        diz = (f"{prov}: ritmo {status or 'sem leitura'} ({fonte})."
               + (f" Janelas usadas: {', '.join(partes)}." if partes else ""))
        if t:
            diz += (f" Na última run registrada ({_quando(t.get('at'))}, {t.get('moment')}) "
                    f"o estado era {t.get('status')} e o ritmo {t.get('pacing')}.")
        itens.append({"prov": prov, "status": status or "sem leitura",
                      "ok": status == "ok", "janelas": " · ".join(partes[:3]),
                      "lido": _quando(o.get("updated_at") or (t or {}).get("at")),
                      "diz": diz})
    datas = [o.get("updated_at") for o in orc.values() if isinstance(o, dict) and o.get("updated_at")]
    return {"itens": itens, "orc_lido": _quando(max(datas)) if datas else None,
            "tel_lido": _quando(tel.get("updated_at")) if tel.get("updated_at") else None,
            "tel_n": len(recentes)}


def orquestracoes(c: Path) -> dict:
    todas = pastas_runs(c)
    runs = [resumo_run(p, d) for p, d in todas[:RUNS_MAX]]
    formal = next((r for r in runs if r["modo"] == "run"), None)
    if formal is None:
        for p, d in todas[RUNS_MAX:]:
            if (_ler_json(d / "manifest.json") or {}).get("mode") == "run":
                formal = resumo_run(p, d)
                break
    return {"runs": runs, "total": len(todas), "formal": formal,
            "gates": gates_run(formal) if formal else [],
            "papeis": papeis_run(formal) if formal else [],
            "cotas": cotas(c)}


# ---------------------------------------------------------------------------
# v7.17 — pele POP v1.2 (CSS/JS embutidos: a saída é arquivo único e offline)
# ---------------------------------------------------------------------------

CSS_POP_EXTRA = """
  /* ═══ v7.17 · peças do gerador sobre o esqueleto POP ═══ */
  .gates{grid-template-columns:repeat(var(--n,8),1fr)}
  @media(max-width:48rem){.gates{grid-template-columns:repeat(3,1fr)}}
  .hero .tldr{margin:.4rem 0 0;color:var(--corpo);font-size:.78rem;max-width:70ch}
  .hero .frescor b{color:var(--verde)} .hero .frescor b.alerta{color:var(--coral)}
  code{font-family:var(--mono);font-size:.85em;background:rgba(255,255,255,.08);border-radius:5px;padding:0 .3em}
  .vazio{margin:0;padding:.65rem .85rem;border:1px dashed rgba(255,255,255,.22);border-radius:12px;color:var(--fraco);font-size:.8rem}
  .sub-tit{margin:1rem 0 .4rem;font:800 .66rem var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--fraco)}
  .versao{display:grid;grid-template-columns:repeat(auto-fit,minmax(14rem,1fr));gap:.6rem;margin:0 0 .8rem}
  .versao > div{background:var(--card2);border-radius:14px;padding:.7rem .85rem}
  .versao .label{display:block;font:700 .62rem var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--fraco)}
  .versao .big{display:block;margin:.2rem 0;font:800 1.75rem/1.1 var(--mono);letter-spacing:-.03em;color:var(--amarelo);font-variant-numeric:tabular-nums}
  .versao .anterior .big{color:var(--fraco);text-decoration:line-through;text-decoration-thickness:2px}
  .versao small{display:block;color:var(--corpo);font-size:.72rem;line-height:1.4}
  .versao .alerta{color:var(--coral);font-weight:700} .versao .certo{color:var(--verde);font-weight:700}
  .warn{border-color:color-mix(in oklab,var(--amarelo) 55%,transparent)} .warn .si{background:color-mix(in oklab,var(--amarelo) 22%,transparent)} .warn .si svg{color:var(--amarelo)}
  .bad{border-color:color-mix(in oklab,var(--coral) 55%,transparent)} .bad .si{background:color-mix(in oklab,var(--coral) 22%,transparent)} .bad .si svg{color:var(--coral)}
  td.st-atual{color:var(--verde)} td.st-desatualizado{color:var(--coral)} td.st-sem{color:var(--fraco)}
  .acao .aviso{color:var(--amarelo);font-size:.72rem}
  .acao p code{white-space:normal}
  .barra{height:.6rem;border-radius:99px;background:rgba(255,255,255,.1);overflow:hidden;margin:.55rem 0}
  .barra i{display:block;height:100%;background:linear-gradient(90deg,var(--verde),var(--amarelo))}
  .etapas{list-style:none;margin:.3rem 0 0;padding:0;display:grid;gap:.35rem}
  .etapa{display:grid;grid-template-columns:1.5rem 1fr;gap:.5rem;align-items:start;background:var(--card2);border-radius:10px;padding:.45rem .65rem;font-size:.8rem}
  .etapa .ic{font:800 .9rem var(--mono);text-align:center}
  .etapa--feito .ic{color:var(--verde)} .etapa--fazendo .ic{color:var(--azul)} .etapa--bloqueado .ic{color:var(--coral)} .etapa--pendente .ic{color:var(--fraco)}
  .etapa small{display:block;color:var(--fraco);font-size:.7rem}
  .notas,.simples{list-style:none;margin:.3rem 0 0;padding:0;max-height:14rem;overflow:auto;border:1px solid var(--linha);border-radius:11px}
  .notas li,.simples li{padding:.38rem .65rem;border-bottom:1px solid var(--linha);font-size:.78rem;color:var(--corpo)}
  .ts{font:600 .64rem var(--mono);color:var(--fraco);margin-right:.4rem}
  .duo{display:grid;gap:.8rem} @media(min-width:52rem){.duo{grid-template-columns:1fr 1fr}}
  tr.velha td{background:color-mix(in oklab,var(--coral) 12%,transparent)}
  .hist{list-style:none;margin:0;padding:0;display:grid;gap:.4rem}
  .hist li{background:var(--card2);border-radius:11px;padding:.5rem .75rem;font-size:.8rem;color:var(--corpo)}
  .hist b{font-family:var(--mono);color:var(--amarelo)} .hist small{display:block;color:var(--fraco);font-size:.7rem}
  a.doc,a.it{color:inherit;text-decoration:none}
  a.doc:hover .go,a.it:hover .go{color:var(--roxo)}
  .cb .n{display:block;font:800 1.6rem/1 var(--mono);color:var(--verde);margin:.3rem 0 .1rem}
  .rodape{margin-top:1.6rem;color:var(--fraco);font:.68rem/1.55 var(--mono);text-align:center}
  .rodape .btn{margin-top:.5rem}
"""

# Mesma delegação do template POP v1.2: um listener de clique e um de teclado
# para a página inteira. Toast monta nó com textContent — o conteúdo que o
# gerador escreveu em data-diz/data-copia nunca é interpretado como HTML.
JS_POP = """
(function(){
  var dados = {};
  try { dados = JSON.parse(document.getElementById('mb-pop-dados').textContent); } catch(e){}
  var fila = document.getElementById('toasts');
  function toast(msg, sub, err){
    var t = document.createElement('div');
    t.className = 'toast' + (err ? ' err' : '');
    var ico = document.createElement('span'); ico.className = 't-ico'; ico.textContent = err ? '⚠' : '✓';
    var box = document.createElement('span'); box.textContent = msg;
    if (sub){ var s = document.createElement('small'); s.textContent = sub; box.appendChild(s); }
    t.appendChild(ico); t.appendChild(box);
    fila.appendChild(t);
    while (fila.children.length > 3) fila.removeChild(fila.firstChild);
    setTimeout(function(){ t.classList.add('saindo'); setTimeout(function(){ t.remove(); }, 280); }, 3400);
  }
  function fallback(txt){
    var ta = document.createElement('textarea');
    ta.value = txt; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    var ok = false; try { ok = document.execCommand('copy'); } catch(e){}
    ta.remove(); return ok;
  }
  function copia(txt, diz){
    var origem = document.activeElement;
    var feito = function(ok){
      toast(ok ? (diz || 'Copiado') : 'Não deu pra copiar', ok ? txt : 'copia na mão: ' + txt, !ok);
      if (origem && origem.focus) { try { origem.focus({preventScroll:true}); } catch(e){} }
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(txt).then(function(){ feito(true); }, function(){ feito(fallback(txt)); });
    } else { feito(fallback(txt)); }
  }
  /* mascote: o listener do próprio elemento roda ANTES da delegação no
     documento — troca a fala em data-diz e a delegação mostra */
  var falas = dados.falas || [];
  var mi = 0;
  var m = document.getElementById('mascote');
  if (m) m.addEventListener('click', function(){
    m.classList.remove('vibra'); void m.offsetWidth; m.classList.add('vibra');
    if (falas.length){ m.setAttribute('data-diz', '🧠 ' + falas[mi % falas.length]); mi++; }
  });
  /* panes: um aberto por vez, no MESMO design (o toast vem do data-diz) */
  var pnBtns = document.querySelectorAll('.pn');
  function abrePane(b, alvo){
    document.querySelectorAll('.pane-pop').forEach(function(p){ p.hidden = true; });
    pnBtns.forEach(function(x){ x.setAttribute('aria-pressed', 'false'); });
    if (alvo){ alvo.hidden = false; b.setAttribute('aria-pressed', 'true'); }
  }
  pnBtns.forEach(function(b){
    b.addEventListener('click', function(){
      var alvo = document.getElementById(b.dataset.pane);
      if (!alvo) return;
      var aberto = !alvo.hidden;
      abrePane(b, aberto ? null : alvo);
      if (!aberto){
        var suave = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        alvo.scrollIntoView({block:'nearest', behavior: suave ? 'smooth' : 'auto'});
      }
    });
  });
  /* delegação única: clique */
  document.addEventListener('click', function(e){
    var c = e.target.closest('[data-copia]');
    if (c){ e.preventDefault(); copia(c.getAttribute('data-copia'), c.getAttribute('data-diz')); return; }
    var d = e.target.closest('[data-diz]');
    if (d){
      /* controle nativo com ação própria DENTRO de um container data-diz:
         o pai não fala por ele */
      var proprio = e.target.closest('a,button,summary');
      if (!proprio || proprio === d){ toast(d.getAttribute('data-diz')); }
    }
  });
  /* delegação única: teclado */
  document.addEventListener('keydown', function(e){
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var t = e.target.closest ? e.target.closest('[data-diz],[data-copia]') : null;
    if (t && t.tagName !== 'A' && t.tagName !== 'BUTTON' && t.tagName !== 'SUMMARY'){
      e.preventDefault();
      t.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true}));
    }
  });
  /* reload em intervalo fixo (file:// não avisa quando o arquivo muda).
     Guarda scroll, painel aberto e <details> abertos; não recarrega com toast
     na tela nem enquanto ele mexe na página. */
  var K = 'mb-pop-vivo';
  try {
    var s = JSON.parse(sessionStorage.getItem(K) || 'null');
    if (s){
      sessionStorage.removeItem(K);
      (s.abertos || []).forEach(function(id){ var d = document.getElementById(id); if (d && d.tagName === 'DETAILS') d.open = true; });
      if (s.pane){
        var b = document.querySelector('.pn[data-pane="' + s.pane + '"]');
        if (b) abrePane(b, document.getElementById(s.pane));
      }
      window.scrollTo(0, s.y || 0);
    }
  } catch(e){}
  var seg = dados.reload || 0;
  if (seg > 0){
    var mexeu = Date.now();
    ['click', 'keydown', 'scroll', 'pointermove', 'wheel', 'touchstart'].forEach(function(ev){
      document.addEventListener(ev, function(){ mexeu = Date.now(); }, {passive:true});
    });
    setInterval(function(){
      if (Date.now() - mexeu < 10000 || fila.children.length) return;
      var abertos = [].map.call(document.querySelectorAll('details[open][id]'), function(d){ return d.id; });
      var pane = document.querySelector('.pane-pop:not([hidden])');
      try { sessionStorage.setItem(K, JSON.stringify({y: window.scrollY || 0, abertos: abertos, pane: pane ? pane.id : null})); } catch(e){}
      location.reload();
    }, seg * 1000);
  }
})();
"""

SVG_ORQ = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><path d="M9 6h6a3 3 0 0 1 3 3v6M15 18H9a3 3 0 0 1-3-3V9"/></svg>'
SVG_MAO = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11.5V5a1.5 1.5 0 0 1 3 0v6"/><path d="M12 11V4a1.5 1.5 0 0 1 3 0v7"/><path d="M15 11.5V6a1.5 1.5 0 0 1 3 0v8c0 4-2.5 7-6.5 7S5 18 5 14v-3a1.5 1.5 0 0 1 3 0"/></svg>'
SVG_ESTADO = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12l-8 8-4-4-6 6"/><path d="M3 14v5a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-8"/></svg>'
SVG_RAIO = '<svg viewBox="0 0 24 24" fill="none" stroke="{cor}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 3 14h7l-1 8 10-12h-7z"/></svg>'
SVG_ESTRELA = '<svg viewBox="0 0 24 24" fill="none" stroke="{cor}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l2 4 4 .6-3 3 .7 4.4L12 12l-3.7 2 .7-4.4-3-3L10 6z"/></svg>'
SVG_REDE = '<svg viewBox="0 0 24 24" fill="none" stroke="{cor}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><circle cx="5" cy="5" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><path d="M6.5 6.5 10 10m4 0 3.5-3.5M6.5 17.5 10 14m4 0 3.5 3.5"/></svg>'
SVG_LIVRO = '<svg viewBox="0 0 24 24" fill="none" stroke="{cor}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19V5a2 2 0 0 1 2-2h13v18H6a2 2 0 0 1-2-2zM19 7H7"/></svg>'
SVG_RELOGIO = '<svg viewBox="0 0 24 24" fill="none" stroke="{cor}" stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>'
SVG_CHIP = {
    "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M20 6 9 17l-5-5"/></svg>',
    "terminal": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M4 17l6-6-6-6M12 19h8"/></svg>',
    "relogio": SVG_RELOGIO.format(cor="currentColor"),
    "coracao": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 6.5c-1.5-2-5-2-6.5.5-1.4 2.3.5 5 2 6.5L12 18l4.5-4.5c1.5-1.5 3.4-4.2 2-6.5-1.5-2.5-5-2.5-6.5-.5z"/></svg>',
    "copias": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/><path d="M10 6.5h7V14"/></svg>',
}
MASCOTE = """<svg class="mascote" id="mascote" viewBox="0 0 120 110" aria-label="mascote cérebro do megabrain — clica pra ele falar" role="button" tabindex="0" data-diz="{diz}">
        <path d="M60 8c-20 0-34 10-38 24-9 3-14 11-14 20 0 12 9 21 20 23 4 9 14 15 26 15 8 0 16-3 22-8 5 4 12 6 19 4 11-3 18-13 18-24 0-4-1-8-3-11 4-15-8-43-50-43z"
          fill="#CE82FF" stroke="#8B5CF6" stroke-width="4"/>
        <path d="M52 30c-8 6-10 16-6 24M74 26c4 10 2 22-6 28M40 52c8 4 18 4 26 0" fill="none" stroke="#8B5CF6" stroke-width="3.5" stroke-linecap="round"/>
        <circle cx="47" cy="58" r="9" fill="#fff"/><circle cx="75" cy="56" r="9" fill="#fff"/>
        <circle cx="49" cy="59" r="4" fill="#1B1B2A"/><circle cx="73" cy="57" r="4" fill="#1B1B2A"/>
        <circle cx="51" cy="56" r="1.4" fill="#fff"/><circle cx="75" cy="54" r="1.4" fill="#fff"/>
        <path d="M52 74q10 8 20 0" fill="none" stroke="#1B1B2A" stroke-width="3.5" stroke-linecap="round"/>
        <ellipse cx="36" cy="68" rx="5" ry="3.4" fill="#FF82C4" opacity=".8"/>
        <ellipse cx="86" cy="66" rx="5" ry="3.4" fill="#FF82C4" opacity=".8"/>
      </svg>"""


def _href(saida: Path, alvo: Path, pasta: bool = False) -> str:
    """Link que funciona de onde o HTML está: relativo quando dá (o vivo em
    00_painel/ continua abrindo se a central mudar de disco), file:// absoluto
    quando não dá (saída de teste em outro drive). Resolve a dívida dos hrefs
    file:/// fixos do template."""
    try:
        rel = os.path.relpath(alvo, saida.parent)
        href = quote(Path(rel).as_posix(), safe="/._-~")
    except ValueError:
        href = alvo.resolve().as_uri()
    if pasta and not href.endswith("/"):
        href += "/"
    return href


def _md_inline(texto: str) -> str:
    """Markdown mínimo do HANDOFF (negrito e `código`) DEPOIS do escape."""
    s = e(texto)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def _sem_md(texto: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*|`([^`]+)`", lambda m: m.group(1) or m.group(2), texto)


def _setor(ident: str, cor: str, svg: str, titulo: str, desc: str, corpo: str,
           slot: str = "", classe_corpo: str = "") -> str:
    ds = f' data-slot="{slot}"' if slot else ""
    return (f'<section class="setor" style="--c:var(--{cor})" id="{ident}"{ds}>\n'
            f'    <header><span class="ico">{svg}</span><div><h2>{e(titulo)}</h2>'
            f'<p class="desc">{e(desc)}</p></div></header>\n'
            f'    <div class="corpo {classe_corpo}">{corpo}</div>\n  </section>')


def _pane(ident: str, cor: str, svg: str, titulo: str, desc: str, corpo: str) -> str:
    return (f'<section class="setor pane-pop" id="{ident}" data-slot="{ident}" hidden style="--c:var(--{cor})">\n'
            f'    <header><span class="ico">{svg.format(cor="#fff")}</span><div><h2>{e(titulo)}</h2>'
            f'<p class="desc">{e(desc)}</p></div></header>\n'
            f'    <div class="corpo">{corpo}</div>\n  </section>')


def _vazio(texto: str) -> str:
    return f'<p class="vazio">{e(texto)}</p>'


def _chip(estado: str, icone: str, titulo: str, sub: str, diz: str) -> str:
    return (f'<div class="s-chip {estado}" role="button" tabindex="0" data-diz="{e(diz)}">'
            f'<span class="si">{SVG_CHIP[icone]}</span><div><b>{e(titulo)}</b>'
            f'<span>{e(sub)}</span></div></div>')


def html_orquestracoes(orq: dict) -> tuple[str, str]:
    """(legenda + gates + runs + cotas + papéis, texto curto pro hero)."""
    formal = orq["formal"]
    if formal:
        _cls, _ico, rot = rotulo_run(formal["status"])
        trava_g = next((g for g in orq["gates"] if g["estado"] == "trava"), None)
        onde = f" — parou em {trava_g['curto'].lower()}" if trava_g else ""
        leg = (f'<p class="gates-leg">pipeline V6 da última run formal · <b>{e(formal["projeto"])} · '
               f'{e(_quando(formal["em"]))} — {e(rot)}{e(onde)}</b> · '
               f'{e(formal["nome"])}</p>')
        gates = "".join(
            f'<div class="gate gate--{g["estado"]}" role="button" tabindex="0" '
            f'data-diz="{e(g["diz"])}"><b>{i}</b><span>{e(g["curto"])}</span></div>'
            for i, g in enumerate(orq["gates"], 1))
        bloco_gates = (f'{leg}<div class="gates" data-slot="orc-gates" role="list" '
                       f'style="--n:{len(orq["gates"])}" aria-label="pipeline V6 da run {e(formal["nome"])}">'
                       f'{gates}</div>')
    else:
        bloco_gates = ('<div class="gates" data-slot="orc-gates">'
                       + _vazio("sem run formal registrada em .automations/runs/ — os gates aparecem "
                                "quando a primeira /orquestracao1 terminar") + '</div>')

    cards = []
    for r in orq["runs"]:
        cls, ico, rot = rotulo_run(r["status"])
        titulo = (r["objetivo"][:58] + "…") if len(r["objetivo"]) > 58 else r["objetivo"]
        if not titulo:
            titulo = "probe de rota" if r["modo"] == "probe" else f"run {r['modo']}"
        det = [_quando(r["em"]), r["modo"]]
        if r["perfil"]:
            det.append(f"perfil {r['perfil']}")
        det.append(f"{len(r['estagios'])} estágio(s)")
        diz = (f"{r['projeto']} · {r['nome']} — estado {r['status']}"
               + (f" ({r['erro'][:160]})" if r["erro"] else "")
               + (f". {len(r['result'].get('limitations') or [])} limitação(ões) declarada(s) no result.json"
                  if r["result"].get("limitations") else "")
               + ". Caminho das evidências copiado.")
        cards.append(
            f'<div class="run run--{cls}" role="button" tabindex="0" data-copia="{e(str(r["pasta"]))}" '
            f'data-diz="{e(diz)}"><span class="st">{ico}</span><span><b>{e(r["projeto"])} · {e(titulo)}</b>'
            f'<small>{e(" · ".join(det))}</small></span><span class="q">{e(rot)}</span></div>')
    runs_html = ("".join(cards) if cards else
                 _vazio("sem run registrada — nenhuma .automations/runs/ na central, nas subpastas ou nos projetos irmãos"))
    if orq["total"] > len(orq["runs"]):
        runs_html += (f'<p class="gates-leg" style="margin:.2rem 0 0">{len(orq["runs"])} mais recentes de '
                      f'{orq["total"]} runs no disco</p>')

    co = orq["cotas"]
    fontes = []
    if co["orc_lido"]:
        fontes.append(f'orçamento <b>{e(co["orc_lido"])}</b>')
    if co["tel_lido"]:
        fontes.append(f'telemetria <b>{e(co["tel_lido"])}</b> ({co["tel_n"]} leituras)')
    cota_cards = "".join(
        f'<div class="cota cota--{"ok" if x["ok"] else "warn"}" role="button" tabindex="0" '
        f'data-diz="{e(x["diz"])}"><span class="dot"></span><span><b>{e(x["prov"])}</b>'
        f'<small>{e(x["janelas"] or "sem janela medida")} · {e(x["lido"])}</small></span>'
        f'<span class="ritmo">{e(x["status"])}</span></div>' for x in co["itens"])
    cotas_html = (
        f'<p class="gates-leg" style="margin:0 0 .3rem">cotas · fotografia, não ao vivo · '
        f'{" · ".join(fontes) if fontes else "sem data de leitura"}</p>'
        + (cota_cards or _vazio("sem leitura de cota registrada (dados/orcamento_ia.json e "
                                "dados/telemetria-orquestracao.json vazios ou ausentes)")))

    papeis = "".join(
        f'<span class="papel" role="button" tabindex="0" data-diz="{e(p["diz"])}">'
        f'<b>{e(p["curto"])}</b> {e(p["quem"])}</span>' for p in orq["papeis"])
    corpo = (f'{bloco_gates}<div class="orc-grid"><div class="runs" data-slot="orc-runs">{runs_html}</div>'
             f'<div class="cotas" data-slot="orc-cotas">{cotas_html}</div></div>'
             + (f'<div class="papeis">{papeis}</div>' if papeis else ""))
    return corpo, (f"cotas: leitura {co['orc_lido']}" if co["orc_lido"] else "cotas: sem leitura")


def html_para_voce(itens: list[str], saida: Path, c: Path) -> str:
    handoff = _href(saida, u.achar(c, "HANDOFF.md"))
    if not itens:
        return _vazio("nada pendente do seu lado — a seção PARA VOCÊ do HANDOFF.md está vazia ou não existe")
    cards = []
    for n, item in enumerate(itens, 1):
        m = re.match(r"\*\*(.+?)\*\*\s*(.*)", item)
        titulo, corpo = (m.group(1), m.group(2)) if m else (_sem_md(item)[:70], item)
        botoes = []
        aviso = ""
        for cod in re.findall(r"`([^`]+)`", item):
            cmd = cod.strip()
            if cmd.startswith("!"):
                cmd = cmd[1:].strip()
            # nome + extensão ("01_acoes\11_x.cmd"), não a extensão solta (".cmd")
            if not re.search(r"\w[\w.-]*\.(cmd|py|ps1|bat)\b|^python\b", cmd):
                continue
            if any(ord(ch) < 32 for ch in cmd):
                aviso = ('<span class="aviso">o comando no HANDOFF tem caractere de controle '
                         '(provável barra invertida engolida) — corrija na fonte antes de copiar</span>')
                continue
            botoes.append(f'<button type="button" class="btn" data-copia="{e(cmd)}" '
                          f'data-diz="Comando do passo {n} copiado — cola no terminal da central.">copiar comando</button>')
            break
        botoes.append(f'<a class="btn btn--sec" href="{e(handoff)}" target="_blank" rel="noopener" '
                      f'data-diz="Abrindo o HANDOFF.md numa aba nova — seção PARA VOCÊ, item {n}.">abrir HANDOFF</a>')
        cards.append(f'<div class="acao"><span class="n">PASSO {n}</span><h3>{_md_inline(titulo)}</h3>'
                     f'<p>{_md_inline(corpo) if corpo else ""}</p>{aviso}'
                     f'<div class="rodape-btn">{"".join(botoes)}</div></div>')
    return "".join(cards)


def html_figuras(estado_dados: dict, tel: dict | None) -> str:
    ag = estado_dados.get("agentes") or {}
    figs = []
    por_agente = list((ag.get("por_agente") or {}).items())
    total = sum(v for _, v in por_agente)
    if total:
        cores = ["azul", "verde", "amarelo"]
        top = por_agente[:2]
        resto = total - sum(v for _, v in top)
        fatias = top + ([("outros", resto)] if resto else [])
        barras = "".join(
            f'<i style="width:{max(1, round(100 * v / total))}%;background:var(--{cores[i]})">'
            f'{round(100 * v / total)}%</i>' if round(100 * v / total) >= 8 else
            f'<i style="width:{max(1, round(100 * v / total))}%;background:var(--{cores[i]})"></i>'
            for i, (k, v) in enumerate(fatias))
        leg = "".join(f'<span><i class="pt" style="background:var(--{cores[i]})"></i><b>{e(str(k))}</b> {v}</span>'
                      for i, (k, v) in enumerate(fatias))
        figs.append(f'<figure class="fig" data-slot="fig-share"><figcaption><b>fig. 1 — quem trabalhou</b></figcaption>'
                    f'<div class="share" style="margin-top:.5rem">{barras}</div><div class="legenda">{leg}</div>'
                    f'<p class="cap">{total} eventos em {e(str(ag.get("dias_com_registro", "?")))} dia(s) · '
                    f'{e(str(ag.get("_fonte", "")))}</p></figure>')
    por_evento = list((ag.get("por_evento") or {}).items())[:6]
    if por_evento:
        topo = max(v for _, v in por_evento) or 1
        cols = "".join(
            f'<div class="col" title="{e(str(k))}: {v}"><span class="v">{v}</span>'
            f'<i class="bar" style="--h:{max(2, round(100 * v / topo))}"></i><span class="r">{e(str(k)[:10])}</span></div>'
            for k, v in por_evento)
        figs.append(f'<figure class="fig" data-slot="fig-spark"><figcaption><b>fig. 2 — o que a central fez</b></figcaption>'
                    f'<div class="spark">{cols}</div><p class="cap">eventos por tipo · fonte dados/estado.json '
                    f'(gerado {e(str(estado_dados.get("gerado_em", "?"))[:16].replace("T", " "))})</p></figure>')
    if tel and tel.get("eventos") and (tel.get("por") or {}).get("skill"):
        skills = list(tel["por"]["skill"].items())[:6]
        topo = max(v for _, v in skills) or 1
        cols = "".join(
            f'<div class="col" title="{e(str(k))}: {v}"><span class="v">{v}</span>'
            f'<i class="bar" style="--h:{max(2, round(100 * v / topo))};background:var(--roxo)"></i>'
            f'<span class="r">{e(str(k)[:10])}</span></div>' for k, v in skills)
        figs.append(f'<figure class="fig"><figcaption><b>fig. 3 — skills mais usadas</b></figcaption>'
                    f'<div class="spark">{cols}</div><p class="cap">janela 90 dias · .mb-log/telemetria-*.jsonl · '
                    f'último registro {e(str(tel.get("ultimo") or "—"))}</p></figure>')
    if not figs:
        return _vazio("sem telemetria nesta instância (dados/estado.json sem bloco agentes)")
    return "".join(figs)


def html_pane_acoes(c: Path) -> str:
    try:
        import mb_registro as reg
    except ImportError:
        return _vazio("registro de ações ausente (bin/mb_registro.py)")
    pasta = c / "01_acoes"
    itens = []
    for n, apelido, faz, quando in reg.ACOES:
        arq = pasta / f"{n:02d}_{apelido}.cmd"
        falta = "" if arq.is_file() else " · arquivo não encontrado"
        itens.append(f'<div class="it" role="button" tabindex="0" data-copia="{e(str(arq))}" '
                     f'data-diz="Ação {n} copiada — {e(quando)}"><span class="num">{n}</span>'
                     f'<span><b>{e(apelido.replace("-", " "))}</b><small>{e(faz)}{e(falta)}</small></span>'
                     f'<span class="go">copiar ▸</span></div>')
    rotina = "".join(
        f'<div class="it" role="button" tabindex="0" data-copia="{e(cmd)}" data-diz="Comando copiado — quando: {e(quando)}">'
        f'<span class="num">·</span><span><b>{e(cmd)}</b><small>{e(faz)}</small></span><span class="go">copiar ▸</span></div>'
        for cmd, faz, quando in reg.ROTINA)
    agente = "".join(
        f'<div class="it" role="button" tabindex="0" data-copia="{e(cmd)}" '
        f'data-diz="Não é pra você rodar — {e(gate)}: {e(faz)} Se não rodar: {e(quebra)}">'
        f'<span class="num">IA</span><span><b>{e(cmd)}</b><small>{e(gate)} — {e(faz)}</small></span>'
        f'<span class="go">copiar ▸</span></div>'
        for cmd, gate, faz, quebra in (getattr(reg, "AGENTE", None) or []))
    return (f'<div class="lista-acoes">{"".join(itens)}</div>'
            + (f'<p class="sub-tit">manutenção — sem número, você chama quando precisa</p>'
               f'<div class="lista-acoes">{rotina}</div>' if rotina else "")
            + (f'<p class="sub-tit">o que a IA roda nos gates — não é pra você clicar</p>'
               f'<div class="lista-acoes">{agente}</div>' if agente else ""))


def html_pane_skills() -> str:
    try:
        import mb_registro as reg
    except ImportError:
        return _vazio("sem skills declaradas (bin/mb_registro.py ausente)")
    por_origem: dict[str, list] = {}
    for nome, origem, faz, gatilho in reg.SKILLS_DELE:
        por_origem.setdefault(origem, []).append((nome, faz, gatilho))
    ordem = ["central", "plugin", "projeto", "Matt Pocock (MIT)"]
    rotulo = {"central": "do protocolo (fonte em motor/skills/)", "plugin": "do plugin",
              "projeto": "dos seus projetos", "Matt Pocock (MIT)": "de fora — Matt Pocock, licença MIT"}
    partes = []
    for origem in ordem + [o for o in por_origem if o not in ordem]:
        if origem not in por_origem:
            continue
        cards = "".join(
            f'<div class="sk" role="button" tabindex="0" data-diz="/{e(nome)} — {e(faz)} Chama assim: {e(gatilho)}">'
            f'<span><b>/{e(nome)}</b><small>{e(faz[:90])}{"…" if len(faz) > 90 else ""}</small></span>'
            f'<span class="go">▸</span></div>' for nome, faz, gatilho in por_origem[origem])
        partes.append(f'<p class="sub-tit">{e(rotulo.get(origem, origem))}</p><div class="skills-grid">{cards}</div>')
    return "".join(partes) or _vazio("sem skills declaradas")


def html_pane_cerebro(c: Path, saida: Path) -> str:
    if ws is None:
        return _vazio("cérebro indisponível nesta instância (falta bin/mb_workspace.py)")
    try:
        d = ws.cerebro_dados(c)
    except Exception:
        return _vazio("não deu pra ler o cérebro nesta geração")
    cer = Path(d["caminho"])
    vence = f' · {d["vencidas"]} vencida(s)' if d["vencidas"] else ""
    blocos = [("raw", "📁 raw/", d["raw"], "fontes cruas guardadas",
               "raw/ — as fontes cruas que entraram (artigo, PDF, transcrição, briefing). Nada morre no chat."),
              ("wiki", "🧠 wiki/", len(d["wiki"]), f"páginas destiladas{vence}",
               f"wiki/ — um tópico por página. {d['vencidas']} vencida(s), {d['a_vencer']} vencendo em 14 dias."),
              ("pessoas", "👤 pessoas/", d["pessoas"], "cards de contato",
               "pessoas/ — um card por contato: quem é, como trabalha, histórico.")]
    cards = "".join(
        f'<div class="cb"><b class="cb-tit" role="button" tabindex="0" data-diz="{e(diz)}">{tit}</b>'
        f'<span class="n">{n}</span><small>{e(sub)}</small>'
        f'<a class="btn btn--sec" style="--c:var(--verde)" href="{e(_href(saida, cer / sub_p, pasta=True))}" '
        f'target="_blank" rel="noopener" data-diz="Abrindo a pasta {sub_p}/ numa aba nova…">abrir</a></div>'
        for sub_p, tit, n, sub, diz in blocos)
    entrada = d["entrada"]
    return (f'<div class="cerebro-3">{cards}</div>'
            f'<p class="gates-leg" style="margin:.7rem 0 0">{len(entrada)} fonte(s) esperando /ingerir em 02_entrada · '
            f'última manutenção do cérebro: <b>{e(str(d["ultima_manutencao"]))}</b></p>')


def _titulo_doc(d: dict) -> str:
    """Título do índice; se ele carrega URL (comentário de modelo de terceiro
    virando '# título'), mostra o nome do arquivo — o painel é offline e não
    escreve endereço remoto nem como texto."""
    titulo = str(d.get("titulo") or "")
    if not titulo or re.search(r"https?://", titulo, re.IGNORECASE):
        return Path(d["caminho"]).name
    return titulo


def html_pane_docs(c: Path, saida: Path, estado_dados: dict) -> str:
    principais = [("📍", "ESTADO.md", u.achar(c, "ESTADO.md"), "onde estamos · bloqueio · próximo passo"),
                  ("🤝", "HANDOFF.md", u.achar(c, "HANDOFF.md"), "o bastão entre sessões"),
                  ("⚖️", "DECISOES.md", u.achar(c, "DECISOES.md"), "decisão + alternativa + verificação"),
                  ("🎓", "licoes-megabrain.md", c / "memoria" / "nucleo" / "licoes-megabrain.md", "lições lidas pelo hook"),
                  ("🧾", "dados/estado.json", c / "dados" / "estado.json", "a mesma informação, pra IA ler"),
                  ("🗂️", "relatórios antigos", pasta_arquivo(c) / "INDICE.md", "o painel antes de cada troca de versão")]
    linhas = "".join(
        f'<a class="doc" href="{e(_href(saida, arq))}" target="_blank" rel="noopener" '
        f'data-diz="Abrindo {e(nome)} numa aba nova…"><span class="ic">{ic}</span>'
        f'<span><b>{e(nome)}</b><small>{e(sub)}</small></span><span class="go">abrir ▸</span></a>'
        for ic, nome, arq, sub in principais if arq.is_file())
    docs = (estado_dados.get("documentos") or {}).get("itens") or []
    grupos: dict[str, list] = {}
    for d in docs:
        raiz = d["caminho"].split("/")[0] if "/" in d["caminho"] else "raiz"
        grupos.setdefault(raiz, []).append(d)
    detalhes = []
    for raiz in sorted(grupos):
        ident = "docs-" + (re.sub(r"[^a-z0-9]+", "-", raiz.casefold()).strip("-") or "raiz")
        itens = "".join(
            f'<a class="doc" href="{e(_href(saida, c / d["caminho"]))}" target="_blank" rel="noopener" '
            f'data-diz="Abrindo {e(d["caminho"])} numa aba nova…"><span class="ic">📄</span>'
            f'<span><b>{e(_titulo_doc(d))}</b><small>{e(d["caminho"])} · mudou {e(str(d.get("modificado") or "—"))}</small></span>'
            f'<span class="go">abrir ▸</span></a>'
            for d in sorted(grupos[raiz], key=lambda x: x["caminho"]))
        detalhes.append(f'<details class="variancia" id="{e(ident)}"><summary data-diz="Pasta {e(raiz)}: '
                        f'{len(grupos[raiz])} documento(s).">{e(raiz)} · {len(grupos[raiz])}</summary>'
                        f'<div class="docs-lista" style="margin-top:.5rem">{itens}</div></details>')
    indice = ("".join(detalhes) if detalhes else
              _vazio("índice de documentos ausente — rode python bin/mb-estado.py"))
    return (f'<div class="docs-lista">{linhas}</div><p class="sub-tit">todos os documentos · '
            f'{len(docs)} no índice de dados/estado.json</p>{indice}')


def html_pane_historico(c: Path, saida: Path, anterior: dict, snapshot) -> str:
    linha = _timeline_versao(c)
    itens = "".join(f'<li><b>{e(x["titulo"])}</b> <span class="ts">{e(x["data"])}</span>'
                    f'<small>{e(x["det"])}</small></li>' for x in linha)
    ant = (f'versão anterior: <b>{e(anterior.get("versao", "?"))}</b> · commit {e(anterior.get("commit", "—"))}'
           + (f' · saiu {e(anterior.get("saiu_em", "")[:16].replace("T", " "))}' if anterior.get("saiu_em") else "")
           if anterior else "versão anterior: — (primeira versão registrada)")
    snap = (f"HTML anterior guardado agora: {snapshot.name}" if snapshot else
            "o HTML anterior só é guardado quando versão ou commit muda")
    indice = pasta_arquivo(c) / "INDICE.md"
    return (f'<p class="gates-leg" style="margin:0 0 .5rem">{ant} · {e(snap)}</p>'
            + (f'<ul class="hist">{itens}</ul>' if itens else
               _vazio("VERSAO.txt sem linhas no formato 'AAAA-MM-DD · vX.Y — título'"))
            + f'<div class="rodape-btn" style="margin-top:.7rem"><a class="btn btn--sec" href="{e(_href(saida, indice))}" '
              'target="_blank" rel="noopener" data-diz="Abrindo o índice de relatórios antigos numa aba nova…">'
              'relatórios antigos</a></div>')


def gerar_html(c: Path, forcar_snapshot: bool = False, saida: Path | None = None,
               tema: str | None = None) -> bool:
    """Monta o RELATORIO.html no esqueleto POP v1.2.

    `saida` diferente do vivo = geração de prova: grava só o HTML pedido e NÃO
    mexe em 90_arquivo/relatorios-antigos/ (nem snapshot, nem versao-atual.json).
    """
    vivo = u.achar(c, "RELATORIO.html")
    saida = Path(saida) if saida else vivo
    registrar = saida.resolve() == vivo.resolve()
    estado_dados = _estado_json(c)
    proveniencia = estado_dados.get("gerado_de") or {}
    fp = proveniencia.get("fingerprint") or {}
    if (fp.get("algoritmo") != frescor.ALGORITMO or not fp.get("valor") or
            list(proveniencia.get("fontes") or []) != frescor.fontes_relativas(c)):
        print("ERRO: dados/estado.json sem fingerprint atual — rode `python bin/mb-estado.py`")
        return False
    frescor_html = frescor.bloco_html(proveniencia)
    agora_fp = frescor.calcular(c).get("valor")
    frescor_ok = agora_fp == fp.get("valor")
    prog = carregar_progresso(c)
    etapas = prog.get("etapas", [])
    notas = prog.get("notas", [])[-30:][::-1]
    feitas = sum(1 for x in etapas if x.get("status") == "feito")
    pct = round(100 * feitas / len(etapas)) if etapas else 0
    quem, ate = ler_trava(c)
    versao = u.read_first_non_empty_line(u.achar(c, "VERSAO.txt")) or "?"
    estado = (u.safe_read_text(u.achar(c, "ESTADO.md")) or "").strip()
    tldr = ""
    m = re.search(r"TL;DR:(.*?)(?:\n\n|\Z)", estado, re.DOTALL)
    if m:
        tldr = " ".join(m.group(1).split())
    agora = dt.datetime.now()

    # --- v6.1: versão atual × anterior × git × projetos ---
    git = info_git(c)
    atual = {"versao": versao_resumida(versao), "versao_linha": versao,
             "commit": git["head_curto"], "assunto": git["assunto"], "data_commit": git["data"],
             "visto_em": agora.astimezone().isoformat(timespec="minutes")}
    if registrar:
        ver = estado_versao(c, atual, forcar_snapshot)
    else:
        guardado = _ler_json(pasta_arquivo(c) / "versao-atual.json") or {}
        mesmo = all((guardado.get("atual") or {}).get(k) == atual.get(k) for k in ("versao", "commit"))
        ver = {"atual": atual, "snapshot": None,
               "anterior": (guardado.get("anterior") or {}) if mesmo else (guardado.get("atual") or {})}
    anterior = ver["anterior"]
    # v7.5: nome vem do PROGRESSO (sem o sufixo de versão), número vem do VERSAO.txt.
    nome_projeto = re.sub(r"\s+v\d+(\.\d+)*\b.*$", "",
                          str(prog.get("projeto", "megabrain"))).strip() or "megabrain"
    if git["sem_push"] is None:
        push_txt = "remoto desconhecido (git sem origin/main)" if git["repo"] else "sem repositório git"
        push_cls = ""
    elif git["sem_push"] == 0:
        push_txt, push_cls = f"origin/main = {git['origin_curto']} · nada pendente de push", "certo"
    else:
        push_txt = (f"origin/main conhecido = {git['origin_curto']} · {git['sem_push']} "
                    f"commit(s) local(is) SEM PUSH")
        push_cls = "alerta"

    projetos = projetos_versao(c, versao)
    n_atual = sum(1 for p in projetos if p["estado"] == "atual")
    desatualizados = sum(1 for p in projetos if p["estado"] == "desatualizado")
    para_voce = secao_para_voce(c)
    orq = orquestracoes(c)
    orq_html, cotas_txt = html_orquestracoes(orq)
    tel = ws.telemetria_dados(c) if ws is not None else None
    memo = estado_dados.get("memoria") or {}
    suite = estado_dados.get("suite") or {}

    # --- hero ---
    mascote_falas = []
    if orq["formal"]:
        trava_g = next((g for g in orq["gates"] if g["estado"] == "trava"), None)
        mascote_falas.append(f"V6: última run formal ({orq['formal']['projeto']}, {_quando(orq['formal']['em'])}) "
                             f"terminou em {rotulo_run(orq['formal']['status'])[2]}"
                             + (f" — parou em {trava_g['curto'].lower()}." if trava_g else "."))
    else:
        mascote_falas.append("Nenhuma run formal da V6 no disco ainda.")
    if orq["cotas"]["itens"]:
        mascote_falas.append("Cotas (última fotografia): " + ", ".join(
            f"{x['prov']} {x['status']}" for x in orq["cotas"]["itens"]) + ".")
    if projetos:
        mascote_falas.append(f"{n_atual} de {len(projetos)} cópias de projeto na versão atual.")
    mascote_falas.append(f"{len(para_voce)} passo(s) dependem de você no HANDOFF." if para_voce
                         else "Nada pendente do seu lado no HANDOFF.")
    mascote_falas.append("Regra da casa: nenhum clique seu pode nascer mudo.")
    frescor_txt = (f'<b>frescor confere</b> · {e(fp["algoritmo"])}:{e(fp["valor"][:12])} · '
                   f'{len(proveniencia.get("fontes") or [])} fontes' if frescor_ok else
                   f'<b class="alerta">frescor diverge</b> · estado.json tem {e(fp["valor"][:12])}, as fontes hoje '
                   f'dão {e(str(agora_fp)[:12])} — rode <code>python bin/mb-estado.py</code>')
    hero = f"""<header class="hero" data-slot="hero-status">
    <div>
      {MASCOTE.format(diz=e("🧠 " + mascote_falas[0]))}
    </div>
    <div>
      {mb_pop_tema.HTML_TEMA_CONTROLE}
      <span class="pill"><i></i>GERAÇÃO {agora:%d/%m %H:%M} · trava {e(quem)}{f" até {e(ate)}" if ate not in ("-", "—") else ""}</span>
      <h1>{e(nome_projeto.upper())}</h1>
      <p class="sub">{e(versao_resumida(versao))} · {e(git["head_curto"])} · relatório vivo · {e(cotas_txt)} · recarrega a cada {RELOAD_SEGUNDOS}s · tudo local</p>
      <p class="frescor">{frescor_txt} · estado.json gerado {e(str(estado_dados.get("gerado_em", "?"))[:16].replace("T", " "))}</p>
      {f'<p class="tldr" title="{e(tldr)}">{e(tldr[:260])}{"…" if len(tldr) > 260 else ""}</p>' if tldr else ""}
    </div>
  </header>"""

    # --- ESTADO DA CENTRAL ---
    versao_bloco = f"""<div class="versao">
        <div><span class="label">versão atual</span><span class="big">{e(versao_resumida(versao).split(" ")[0])}</span>
          <small title="{e(versao)}">{e(versao[:120])}{"…" if len(versao) > 120 else ""}</small></div>
        <div><span class="label">base de geração</span><span class="big">{e(git["head_curto"])}</span>
          <small>{e(git["assunto"][:80])}{" · " + e(git["data"]) if git["data"] else ""}</small>
          <small class="{push_cls}">{e(push_txt)}{" · árvore com mudanças não commitadas" if git["suja"] else ""}</small></div>
        <div class="anterior"><span class="label">versão anterior</span><span class="big">{e(str(anterior.get("versao", "—")).split(" ")[0]) if anterior else "—"}</span>
          <small>commit {e(anterior.get("commit", "—")) if anterior else "—"}{" · saiu " + e(anterior.get("saiu_em", "")[:16].replace("T", " ")) if anterior and anterior.get("saiu_em") else ""}</small></div>
      </div>"""
    chips = [
        _chip("ok" if git["sem_push"] == 0 else "warn", "terminal", f"git {git['head_curto']}",
              "nada pendente" if git["sem_push"] == 0 else ("sem remoto conhecido" if git["sem_push"] is None else f"{git['sem_push']} sem push"),
              f"git: HEAD {git['head_curto']} — {git['assunto']}. {push_txt}."),
        _chip("warn" if git["suja"] else "ok", "check", "árvore " + ("com mudanças" if git["suja"] else "limpa"),
              "mudanças não commitadas" if git["suja"] else "nada a commitar",
              "git status --porcelain " + ("tem mudanças não commitadas." if git["suja"] else "vazio.")),
        _chip("ok" if projetos and not desatualizados else "warn", "copias",
              f"{n_atual}/{len(projetos)} cópias" if projetos else "sem cópias",
              f"{desatualizados} desatualizada(s)" if desatualizados else "todas na atual",
              f"{n_atual} de {len(projetos)} projetos com MEGABRAIN/ na versão atual; desatualizado = rode a ação 5."),
        _chip("ok" if quem in ("livre", "-") else "warn", "relogio", f"trava {quem}",
              f"até {ate}" if ate not in ("-", "—") else "HANDOFF.md",
              f"TRAVADO_POR: {quem} · ATÉ: {ate} (última ocorrência no HANDOFF.md)."),
        _chip("ok" if frescor_ok else "bad", "check", "frescor " + ("confere" if frescor_ok else "diverge"),
              fp["algoritmo"], "fingerprint de dados/estado.json " + ("igual ao das fontes agora." if frescor_ok else
              "diferente do calculado agora — rode python bin/mb-estado.py.")),
    ]
    if memo.get("licoes_no_arquivo") is not None:
        chips.append(_chip("info", "coracao", f"{memo['licoes_no_arquivo']} lições",
                           "índice em dia" if memo.get("indice_em_dia") else "índice atrasado",
                           f"{memo['licoes_no_arquivo']} lições no arquivo, {memo.get('licoes_indexadas')} indexadas "
                           f"(dados/estado.json, {str(estado_dados.get('gerado_em', '?'))[:10]})."))
    chips.append(_chip("ok" if suite.get("verde") else "info", "check",
                       f"{suite['testes']} testes" if suite.get("testes") is not None else "testes sem medição",
                       "suíte verde" if suite.get("verde") else "rode python bin/mb-testar.py",
                       f"Suíte: {suite.get('_fonte') or 'sem registro em dados/estado.json'} — número nulo fica nulo, nunca zero."))

    def estado_cls(p):
        return "st-" + p["estado"].split()[0]
    linhas_proj = "".join(
        f'<tr><td><b>{e(p["projeto"])}</b></td><td>{e(p["puxada"])}</td><td>{e(p["commit"] or "—")}</td>'
        f'<td>{e(p["quando"] or "—")}</td><td class="{estado_cls(p)}">{"✓ " if p["estado"] == "atual" else "✕ "}{e(p["estado"])}</td></tr>'
        for p in projetos)
    circ = 219.9
    offset = circ * (1 - (n_atual / len(projetos))) if projetos else circ
    acao5 = c / "01_acoes" / "05_sincronizar-projetos.cmd"
    projetos_html = (f"""<details class="variancia" id="det-projetos">
        <summary data-diz="{e(f'{len(projetos)} projetos com MEGABRAIN/: {n_atual} na versão atual, {desatualizados} desatualizados. Fonte: VERSAO.txt + .mb-origem.json de cada cópia.')}">ver cópias por projeto ({desatualizados} desatualizada(s) · {n_atual} em dia)</summary>
        <div class="resumo-1linha" style="margin-top:.6rem" data-slot="anel-projetos">
          <span class="anelzinho" role="button" tabindex="0" data-diz="{e(f'{n_atual} de {len(projetos)} cópias na versão atual ({versao_resumida(versao)}).')}">
            <svg width="78" height="78" viewBox="0 0 86 86" aria-hidden="true"><circle cx="43" cy="43" r="35" fill="none" stroke="rgba(255,255,255,.12)" stroke-width="9"/><circle cx="43" cy="43" r="35" fill="none" stroke="{"#58CC02" if not desatualizados else "#FFC800"}" stroke-width="9" stroke-linecap="round" stroke-dasharray="{circ}" stroke-dashoffset="{offset:.1f}" transform="rotate(-90 43 43)"/></svg>
            <span class="t">{n_atual}/{len(projetos)}</span>
          </span>
          <p style="margin:0;color:var(--corpo);font-size:.85rem;max-width:34ch">{f'<b style="color:var(--tinta)">{desatualizados} desatualizada(s).</b> Um comando resolve todas: <b style="color:var(--amarelo)">ação 5</b>.' if desatualizados else '<b style="color:var(--tinta)">Todas na versão atual.</b> Nada a sincronizar.'}</p>
          <div class="rodape-btn">
            <button type="button" class="btn" style="--c:var(--verde)" data-copia="{e(str(acao5))}" data-diz="Ação 5 copiada — cole no terminal da central pra sincronizar as cópias.">copiar ação 5</button>
            <a class="btn btn--sec" style="--c:var(--verde)" href="{e(_href(saida, c / "01_acoes", pasta=True))}" target="_blank" rel="noopener" data-diz="Abrindo a pasta 01_acoes numa aba nova…">abrir pasta</a>
          </div>
        </div>
        <div class="tabela-wrap" data-slot="tabela-projetos">
          <table><thead><tr><th>projeto</th><th>puxou</th><th>commit</th><th>quando</th><th>estado</th></tr></thead>
          <tbody>{linhas_proj}</tbody></table>
        </div>
      </details>""" if projetos else
                     f'<div data-slot="anel-projetos"></div><div data-slot="tabela-projetos">'
                     f'{_vazio("nenhum projeto irmão com MEGABRAIN/ encontrado em " + str(raiz_projetos(c)))}</div>')

    ag = estado_dados.get("agentes") or {}
    tele_html = f"""<details class="variancia" id="det-telemetria">
        <summary data-diz="Telemetria local: {e(str(ag.get('eventos', 0)))} eventos. Tudo fica no seu PC.">telemetria geral · {e(str(ag.get("eventos", "—")))} eventos em {e(str(ag.get("dias_com_registro", "—")))} dias</summary>
        <div class="figs" data-slot="telemetria-geral" style="margin-top:.7rem">{html_figuras(estado_dados, tel)}</div>
      </details>"""

    linhas_etapas = "".join(
        f'<li class="etapa etapa--{e(et.get("status", "pendente"))}"><span class="ic">{ICONE.get(et.get("status", "pendente"), "○")}</span>'
        f'<div><b>{e(et.get("titulo", et.get("id", "?")))}</b>'
        f'{" <span class=ts>" + e((et.get("ts") or "")[11:16]) + "</span>" if et.get("ts") and et.get("status") == "feito" else ""}'
        f'{"<small>" + e(et.get("detalhe")) + "</small>" if et.get("detalhe") else ""}</div></li>'
        for et in etapas)
    linhas_notas = "".join(
        f'<li><span class="ts">{e((n.get("ts") or "")[:16].replace("T", " "))}</span>{e(n.get("texto", ""))}</li>'
        for n in notas) or '<li>sem notas ainda</li>'
    linhas_dec = "".join(f"<li>{e(t)}</li>" for t in ultimas_decisoes(c)) or "<li>—</li>"
    linhas_ev = "".join(
        f"<tr><td>{e(h)}</td><td>{e(ag_)}</td><td>{e(ev)}</td><td>{e(res)}</td></tr>"
        for h, ag_, ev, res in eventos_hoje(c)) or '<tr><td colspan="4">nenhum evento hoje</td></tr>'
    fila = fila_pendentes(c)
    linhas_fila = "".join(
        f'<tr{" class=velha" if item["idade"] >= 7 or not item["dono"] else ""}><td>{e(item["pasta"])}</td>'
        f'<td>{e(item["dono"] or "SEM DONO")}</td><td>{item["idade"]}d</td></tr>'
        for item in fila) or '<tr><td colspan="3">fila vazia</td></tr>'
    execucao_html = f"""<details class="variancia" id="det-execucao">
        <summary data-diz="{e(f'Execução: {feitas} de {len(etapas)} etapas feitas no PROGRESSO.json, {len(notas)} nota(s), eventos de hoje e fila de pendências.')}">execução · {feitas}/{len(etapas)} etapas ({pct}%) · notas · decisões · eventos</summary>
        <div style="margin-top:.6rem">
          <p class="sub-tit" style="margin-top:0">progresso — {e(str(prog.get("projeto", "")))}</p>
          <div class="barra"><i style="width:{pct}%"></i></div>
          {f'<ul class="etapas">{linhas_etapas}</ul>' if linhas_etapas else _vazio("sem etapas no PROGRESSO.json")}
          <div class="duo">
            <div><p class="sub-tit">notas da execução</p><ul class="notas">{linhas_notas}</ul></div>
            <div><p class="sub-tit">últimas decisões</p><ul class="simples">{linhas_dec}</ul></div>
          </div>
          <p class="sub-tit">eventos de hoje</p>
          <div class="tabela-wrap"><table><thead><tr><th>hora</th><th>agente</th><th>evento</th><th>resumo</th></tr></thead><tbody>{linhas_ev}</tbody></table></div>
          <p class="sub-tit">fila de pendências · destaque = 7+ dias ou sem dono</p>
          <div class="tabela-wrap"><table><thead><tr><th>nota</th><th>dono</th><th>idade</th></tr></thead><tbody>{linhas_fila}</tbody></table></div>
        </div>
      </details>"""

    estado_corpo = (f'{versao_bloco}<div class="saude" data-slot="saude-chips">{"".join(chips)}</div>'
                    f'{projetos_html}{tele_html}{execucao_html}')

    setor_orq = _setor("orquestracoes", "roxo", SVG_ORQ, "ORQUESTRAÇÕES",
                       "o motor V6 trabalhando — pipeline, runs, cotas e quem faz o quê · clique em tudo", orq_html)
    setor_voce = _setor("pra-voce", "coral", SVG_MAO, "PRA VOCÊ AGORA",
                        (f"o que depende de você — {len(para_voce)} passo(s) · fonte: HANDOFF.md, seção PARA VOCÊ"
                         if para_voce else "nada pendente do seu lado"),
                        html_para_voce(para_voce, saida, c), slot="acoes-voce",
                        classe_corpo="acoes-voce" if para_voce else "")
    setor_estado = _setor("estado-central", "verde", SVG_ESTADO, "ESTADO DA CENTRAL",
                          "versão, saúde e cópias — resumo aberto, detalhe a um clique", estado_corpo)

    try:
        import mb_registro as _mbreg
        n_acoes = len(_mbreg.ACOES)
    except ImportError:
        n_acoes = 0
    panes_def = [
        ("pane-acoes", "roxo", SVG_RAIO, "ações", "AÇÕES DA CENTRAL",
         f"os {n_acoes} comandos numerados de 01_acoes\\ — clique copia o caminho", html_pane_acoes(c)),
        ("pane-skills", "azul", SVG_ESTRELA, "skills", "SUAS SKILLS",
         "as suas, com gatilho — clique pra ver o que cada uma faz", html_pane_skills()),
        ("pane-cerebro", "verde", SVG_REDE, "cérebro", "CÉREBRO",
         "o que você sabe: raw · wiki · pessoas", html_pane_cerebro(c, saida)),
        ("pane-docs", "amarelo", SVG_LIVRO, "documentos", "DOCUMENTOS",
         "onde a máquina lê o estado — e você decide", html_pane_docs(c, saida, estado_dados)),
        ("pane-historico", "rosa", SVG_RELOGIO, "histórico", "HISTÓRICO",
         "linha do tempo de versões e relatórios antigos", html_pane_historico(c, saida, anterior, ver["snapshot"])),
    ]
    nav = "".join(
        f'<button type="button" class="pn" data-pane="{ident}" aria-pressed="false" '
        f'data-diz="{e(f"Seção {rotulo}: {desc}")}">{svg.format(cor="currentColor")}{e(rotulo)}</button>'
        for ident, _cor, svg, rotulo, _tit, desc, _corpo in panes_def)
    panes = "\n  ".join(_pane(ident, cor, svg, tit, desc, corpo)
                        for ident, cor, svg, _rot, tit, desc, corpo in panes_def)

    dados_js = json.dumps({"falas": mascote_falas, "reload": RELOAD_SEGUNDOS},
                          ensure_ascii=False).replace("</", "<\\/")
    pagina = f"""<!doctype html>
<html lang="pt-BR"{" data-tema=\"claro\"" if tema == "claro" else ""}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="{"dark light" if tema == "claro" else "dark"}">
{mb_pop_tema.JS_TEMA_HEAD}
{frescor_html}
<title>MEGABRAIN — relatório vivo · {e(versao_resumida(versao))}</title>
<!-- ═══ esqueleto e pele: template POP v1.2 (motor/modelos/relatorios/260914_pop/) ═══
     gerado por bin/mb-relatorio-vivo.py — edite o gerador, não este arquivo. -->
<style>
{CSS_POP}
{CSS_POP_EXTRA}
{mb_pop_tema.CSS_TEMA}
</style>
</head>
<body>
<div class="wrap">

  {hero}

  {setor_orq}

  {setor_voce}

  {setor_estado}

  <nav class="panes-nav" aria-label="mais conteúdo">{nav}</nav>

  {panes}

  <div class="rodape">
    fonte: PROGRESSO.json · ESTADO.md · HANDOFF.md · DECISOES.md · VERSAO.txt · git · .mb-log/ · .automations/runs/ · dados/orcamento_ia.json · dados/telemetria-orquestracao.json<br>
    frescor: {e(fp["algoritmo"])}:{e(fp["valor"][:12])} · {len(proveniencia.get("fontes") or [])} fontes · HEAD e horário são estado operacional<br>
    sem servidor local o navegador não detecta mudança de arquivo — por isso o reload a cada {RELOAD_SEGUNDOS}s, que espera você parar de mexer<br>
    este HTML é a leitura humana; a IA lê dados/estado.json (schema {e(str(estado_dados.get("schema", "?")))}) · template POP v1.2 · arquivo local, nada remoto<br>
    <button type="button" class="btn btn--sec" style="--c:var(--roxo)" data-copia="python bin/mb-estado.py --stdout" data-diz="Comando que gera o JSON da IA copiado.">copiar comando do JSON</button>
  </div>
</div>

<div id="toasts" role="status" aria-live="polite"></div>
<script id="mb-pop-dados" type="application/json">{dados_js}</script>
<script>{JS_POP}</script>
</body>
</html>
"""
    pagina = "\n".join(linha.rstrip() for linha in pagina.splitlines()) + "\n"
    saida.parent.mkdir(parents=True, exist_ok=True)
    return u.atomic_write_text(saida, pagina)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--marcar", nargs="+", default=None,
                   metavar=("ID STATUS", "DETALHE"),
                   help='ex.: --marcar f2.1 feito "template criado"')
    p.add_argument("--nota", default=None)
    p.add_argument("--snapshot", action="store_true",
                   help="guarda o HTML atual em 90_arquivo/relatorios-antigos/ mesmo sem troca de versão")
    p.add_argument("--tema", default=None, choices=["claro", "escuro"],
                   help="tema inicial do HTML gerado (default: escuro — o navegador do leitor pode lembrar a preferência)")
    p.add_argument("--saida", default=None,
                   help="grava em outro caminho (prova); não mexe no vivo nem em 90_arquivo/relatorios-antigos/")
    args = p.parse_args()

    c = central()
    agente_arquivo = trava.agente_script("mb-relatorio-vivo")

    if args.marcar and (len(args.marcar) < 2 or
                        args.marcar[1] not in STATUS_VALIDOS):
        print(f"ERRO: uso --marcar <id> <{'|'.join(sorted(STATUS_VALIDOS))}> [detalhe]")
        return 1

    try:
        if args.marcar or args.nota:
            progresso_path = u.achar(c, "PROGRESSO.json")
            # Protege o ciclo inteiro. Duas notas simultâneas não podem ler o
            # mesmo JSON e a última apagar a primeira.
            with trava.travado(progresso_path, agente_arquivo,
                               "atualiza progresso do relatório"):
                prog = carregar_progresso(c)
                agora = dt.datetime.now().astimezone().isoformat(timespec="seconds")
                if args.marcar:
                    alvo, status = args.marcar[0], args.marcar[1]
                    detalhe = (" ".join(args.marcar[2:])
                               if len(args.marcar) > 2 else None)
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
                if args.nota:
                    prog.setdefault("notas", []).append(
                        {"ts": agora, "texto": args.nota})
                salvar_progresso(c, prog)

        relatorio_path = Path(args.saida).resolve() if args.saida else u.achar(c, "RELATORIO.html")
        with trava.travado(relatorio_path, agente_arquivo,
                           "regenera relatório e snapshots"):
            if not gerar_html(c, forcar_snapshot=args.snapshot, saida=relatorio_path,
                              tema=args.tema):
                return 1
    except trava.TravaOcupada as e:
        print(f"ERRO: {e}")
        return 1
    print(f"relatório: {relatorio_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
