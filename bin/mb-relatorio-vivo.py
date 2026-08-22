#!/usr/bin/env python3
"""
mb-relatorio-vivo.py — RELATORIO-VIVO.html: retrato ao vivo do projeto pro
usuário deixar aberto no navegador enquanto os agentes trabalham (v6).

A página se recarrega sozinha (JS, a cada 15s, preservando o scroll).
Limite declarado: em file:// o navegador não consegue detectar mudança do
arquivo sem um servidor local, então o "ao vivo" é reload em intervalo fixo
— o usuário não aperta F5, mas há até 15s de atraso.

Fontes: PROGRESSO.json (etapas + notas, atualizado via --marcar/--nota),
ESTADO.md, HANDOFF.md (trava + seção "PARA VOCÊ"), DECISOES.md (últimos
títulos), .mb-log/ do dia, VERSAO.txt, git de _github-repo-local/ e os
VERSAO.txt das cópias MEGABRAIN/ dos projetos irmãos.

v6.1 (260821) — bloco de VERSÃO no topo:
  · versão atual do megabrain (VERSAO.txt) + commit git local (HEAD de
    _github-repo-local), remoto conhecido (origin/main) e quantos commits
    locais ainda não subiram;
  · versão ANTERIOR (a que estava no ar na última troca de versão/commit);
  · tabela dos projetos: qual versão cada MEGABRAIN/ puxou vs a atual.
  Toda vez que a versão ou o commit muda, o HTML anterior é guardado em
  .mb-backup/relatorio-vivo/ (YYMMDD_HHMM_RELATORIO-VIVO_<commit>.html) e o
  par atual/anterior fica em .mb-backup/relatorio-vivo/versao-atual.json.
  Regeneração sem troca de versão NÃO gera snapshot (senão acumula a cada 15s
  de --nota).

Uso:
    python bin/mb-relatorio-vivo.py                        # só regenera
    python bin/mb-relatorio-vivo.py --marcar f2.1 feito "detalhe"
    python bin/mb-relatorio-vivo.py --marcar f2.2 fazendo
    python bin/mb-relatorio-vivo.py --nota "comecei a fase 2"
    python bin/mb-relatorio-vivo.py --snapshot    # força guardar o HTML atual

Status válidos: pendente | fazendo | feito | bloqueado
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import sys
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import mb_utils as u

try:
    import mb_visual as vis
except Exception:  # biblioteca visual ausente: relatório degrada, não quebra
    vis = None

u.utf8_console()


# CSS do conteúdo agregado (.md) e dos slots fixos. Fica aqui, e não em
# modelos/visuais/, porque descreve a PÁGINA — as mecânicas descrevem peças.
CSS_CONTEUDO = """
.faixa { margin:2.4rem 0 .2rem; padding:.35rem 0; border-top:2px solid var(--ink);
  border-bottom:1px solid var(--line); font:800 .7rem/1.3 var(--mono);
  text-transform:uppercase; letter-spacing:.14em; }
.faixa small { font-weight:400; letter-spacing:.04em; color:var(--ink-faint); text-transform:none; }
.slot { margin:1.1rem 0; }
.slot__tit { font-size:.8rem; font-weight:800; margin:0 0 .4rem; letter-spacing:.01em; }
.slot__vazio { font-size:.78rem; color:var(--ink-faint); border:1px dashed var(--line-strong);
  border-radius:2px; padding:.6rem .8rem; margin:0; background:var(--paper-high); }
.indice { display:flex; flex-wrap:wrap; gap:.3rem .7rem; font-size:.74rem; padding:.5rem 0 0; }
.indice a { color:var(--info); text-decoration:none; border-bottom:1px solid var(--line); }
.indice a:hover { border-bottom-color:var(--info); }
.doc section { border-top:1px solid var(--line); padding:1.4rem 0 .4rem; }
.doc section h2 { font-size:1rem; margin:0 0 .2rem; }
.doc .section-file { font:400 .68rem/1.3 var(--mono); color:var(--ink-faint); margin-bottom:.6rem; }
.doc h3 { font-size:.86rem; margin:1.1rem 0 .3rem; }
.doc h4 { font-size:.78rem; margin:.9rem 0 .25rem; color:var(--ink-soft); }
.doc p { font-size:.84rem; line-height:1.6; margin:.5rem 0; }
.doc ul, .doc ol { font-size:.84rem; line-height:1.6; padding-left:1.2rem; margin:.5rem 0; }
.doc li { margin:.15rem 0; }
.doc code { font-family:var(--mono); font-size:.78em; background:var(--paper-sunk);
  border:1px solid var(--line); border-radius:2px; padding:0 .2em; }
.doc pre { overflow-x:auto; background:var(--paper-sunk); border:1px solid var(--line);
  padding:.7rem; font-family:var(--mono); font-size:.72rem; line-height:1.5; }
.doc blockquote { margin:.6rem 0; padding:.3rem 0 .3rem .9rem; border-left:3px solid var(--line-strong);
  color:var(--ink-soft); font-size:.82rem; }
.doc .tbl-wrap { overflow-x:auto; margin:.7rem 0; }
.doc .chk { font-family:var(--mono); font-size:.8em; color:var(--ink-faint); }
.doc hr { border:0; border-top:1px solid var(--line); margin:1.2rem 0; }
.doc a { color:var(--info); }
@media (max-width: 720px) { .duo { grid-template-columns:1fr; } }
"""

RELOAD_SEGUNDOS = 15
STATUS_VALIDOS = {"pendente", "fazendo", "feito", "bloqueado"}
ICONE = {"feito": "✓", "fazendo": "●", "pendente": "○", "bloqueado": "✕"}
SNAPSHOTS_MAX = 30  # HTMLs anteriores guardados em .mb-backup/relatorio-vivo/


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
    """Onde está o git do megabrain: a central (se for repo) ou _github-repo-local/."""
    for cand in (c, c / "_github-repo-local"):
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
              "versão ou de commit. O relatório vivo (`04_relatorios/RELATORIO.html`) é",
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
        (pasta / "INDICE.md").write_text("\n".join(linhas), encoding="utf-8")
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
        if isinstance(resumo, str) and len(resumo) > 90:
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



# ---------------------------------------------------------------------------
# v6.6 — fusão: o relatório vivo absorveu o agregador de .md
# ---------------------------------------------------------------------------

# Pastas da central que NÃO entram no conteúdo do relatório: são código,
# derivado ou arquivo morto. Sem esta lista o rglob puxa referencias/,
# github-export/ e repo-local/ e o HTML passa de 2 MB.
IGNORAR_CENTRAL = {
    "90_arquivo", "99_to_delete", "_github-repo-local", "260810_github-export",
    "04_relatorios", "06_dist", "referencias", "modelos", "skills", "tests",
    "bin", "dna", "plugin-megabrain", "plugin-megabrain-claude",
    "relatorio-megabrain", "gerenteneuron", ".claude", ".mb-backup", ".mb-log",
    ".mb-aspirador", "__pycache__", ".git", "megabrain",
}


def _motor_md():
    """Carrega mb-relatorio-projeto.py como módulo.

    O hífen no nome impede o import normal — daí o importlib. Fundir por
    composição e não copiando 400 linhas: o conversor de markdown continua
    tendo UM dono, e corrigir um bug lá conserta os dois escopos.
    """
    arq = Path(__file__).resolve().parent / "mb-relatorio-projeto.py"
    if not arq.is_file():
        return None
    spec = importlib.util.spec_from_file_location("mb_rel_projeto", arq)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mb_rel_projeto"] = mod
    spec.loader.exec_module(mod)
    return mod


def _titulo_md(relativo: str, texto: str) -> str:
    for linha in texto.splitlines():
        if linha.startswith("# "):
            return linha[2:].strip()
    return Path(relativo).stem.replace("_", " ").replace("-", " ")


def conteudo_md(inst: Path, na_central: bool) -> tuple[list[tuple[str, str]], str]:
    """Todo o .md informacional da instância vira seção navegável.

    É a metade que vinha do RELATORIO.html antigo. Retorna (índice, html).
    """
    mod = _motor_md()
    if not mod:
        return [], ""
    if na_central:
        achados = []
        ignorar = {x.casefold() for x in IGNORAR_CENTRAL}
        for caminho in sorted(inst.rglob("*.md"), key=lambda p: str(p).casefold()):
            rel = caminho.relative_to(inst)
            if {p.casefold() for p in rel.parts[:-1]} & ignorar:
                continue
            texto = mod.ler(caminho)
            if texto:
                achados.append((rel.as_posix(), texto))
    else:
        achados = mod.descobrir_markdowns(inst, set())

    pendencias: list = []
    navs, secoes = [], []
    for relativo, texto in achados:
        ident = mod.id_extra(relativo)
        titulo = _titulo_md(relativo, texto)
        corpo = mod.markdown_para_html(texto, pendencias, relativo)
        secoes.append(mod.secao(ident, titulo, corpo, relativo))
        navs.append((ident, titulo))
    return navs, "".join(secoes)


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


def pecas_visuais(c: Path, git: dict, versao: str, projetos: list,
                  prog: dict, na_central: bool, saude_extra: list | None = None) -> dict:
    """Uma peça visual por SLOT do dashboard.

    Devolve dict — nunca uma string única — porque o layout do relatório é
    FIXO: cada peça tem um lugar reservado na página e é montada lá. Peça
    ausente vira estado vazio, não buraco que empurra o resto pra cima.

    Metade dos dados é viva (git, projetos, versão, PROGRESSO); a outra
    metade é a descrição canônica do workflow em modelos/visuais/exemplos.json
    — a mesma fonte do catálogo, para não existirem duas verdades.
    """
    vazio = {k: "" for k in ("kpi", "distribuicao", "saude", "gates", "trilha", "camadas", "historico")}
    if vis is None:
        return vazio
    try:
        dados = vis.exemplos()
    except Exception:
        dados = {}
    p = dict(vazio)

    atrasados = [x for x in projetos if x.get("estado") == "desatualizado"]
    etapas = prog.get("etapas", [])
    feitas = sum(1 for x in etapas if x.get("status") == "feito")

    kpi = [
        {"valor": versao_resumida(versao), "rotulo": "versão", "status": "ok",
         "det": (git.get("assunto") or "")[:46]},
        {"valor": git.get("head_curto") or "—", "rotulo": "commit",
         "status": "ok" if git.get("sem_push") == 0 else "espera",
         "det": "= origin/main" if git.get("sem_push") == 0
                else f"{git.get('sem_push') or '?'} commit sem push"},
        {"valor": (f"{len(projetos) - len(atrasados)}/{len(projetos)}" if projetos else "—"),
         "rotulo": "projetos na atual",
         "status": "ok" if projetos and not atrasados else "espera",
         "det": "sincronizar-pipeline.cmd" if atrasados else ("nada a fazer" if projetos else "sem projetos irmãos")},
        {"valor": (f"{feitas}/{len(etapas)}" if etapas else "—"), "rotulo": "etapas",
         "status": "ok" if etapas and feitas == len(etapas) else "ativo",
         "det": "PROGRESSO.json"},
    ]
    try:
        kpi.append({"valor": str(len(vis.ids())), "rotulo": "mecânicas visuais",
                    "status": "ok", "det": "modelos/visuais/"})
    except Exception:
        pass
    p["kpi"] = vis.render("kpi-linha", {"itens": kpi})

    if projetos:
        por_versao: dict[str, int] = {}
        for x in projetos:
            chave = x.get("puxada") or "?"
            por_versao[chave] = por_versao.get(chave, 0) + 1
        atual = versao_resumida(versao)
        segs = [{"rotulo": v, "n": n, "status": "ok" if v == atual else "espera"}
                for v, n in sorted(por_versao.items(), key=lambda kv: -kv[1])]
        p["distribuicao"] = vis.render("barra-segmentos", {
            "titulo": f"Os {len(projetos)} projetos por versão do megabrain", "segmentos": segs})

    saude = [
        {"rotulo": "git", "estado": "ok" if git.get("sem_push") == 0 else "espera",
         "det": f"{git.get('head_curto') or '—'} · " +
                ("nada pendente" if git.get("sem_push") == 0 else "commit local sem push")},
        {"rotulo": "árvore", "estado": "espera" if git.get("suja") else "ok",
         "det": "mudanças não commitadas" if git.get("suja") else "limpa"},
        {"rotulo": "projetos", "estado": "espera" if atrasados else "ok",
         "det": f"{len(atrasados)} desatualizado(s)" if atrasados else "todos na versão atual"},
        {"rotulo": "biblioteca visual", "estado": "ok" if vis.ids() else "trava",
         "det": f"{len(vis.ids())} mecânicas em modelos/visuais/"},
    ]
    for extra in (saude_extra or []):
        saude.append(extra)
    p["saude"] = vis.render("semaforo", {"titulo": "Saúde do sistema", "itens": saude})

    for chave, ident in (("gates", "fluxo-etapas"), ("trilha", "trilha-dupla"), ("camadas", "mapa-camadas")):
        if ident in dados:
            p[chave] = vis.render(ident, dados[ident])

    linha = _timeline_versao(c)
    if linha:
        p["historico"] = vis.render("timeline", {"titulo": "Histórico de versão", "itens": linha})
    return p


def gerar_html(c: Path, forcar_snapshot: bool = False) -> bool:
    e = html.escape
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
    ver = estado_versao(c, atual, forcar_snapshot)
    anterior = ver["anterior"]
    if git["sem_push"] is None:
        push_txt = "remoto desconhecido (git sem origin/main)" if git["repo"] else "sem repositório git"
        push_cls = "det"
    elif git["sem_push"] == 0:
        push_txt = f"origin/main = {git['origin_curto']} · nada pendente de push"
        push_cls = "ok"
    else:
        push_txt = (f"origin/main conhecido = {git['origin_curto']} · "
                    f"{git['sem_push']} commit{'s' if git['sem_push'] != 1 else ''} local"
                    f"{'is' if git['sem_push'] != 1 else ''} SEM PUSH — rode git push")
        push_cls = "alerta"
    suja_txt = " · árvore com mudanças não commitadas" if git["suja"] else ""
    anterior_txt = (f"{e(anterior.get('versao', '?'))} · commit {e(anterior.get('commit', '—'))}"
                    f"{' · saiu ' + e(anterior.get('saiu_em', '')[:16].replace('T', ' ')) if anterior.get('saiu_em') else ''}"
                    if anterior else "— (primeira versão registrada)")
    snapshot_txt = (f"HTML anterior guardado: {e(ver['snapshot'].name)}" if ver["snapshot"]
                    else "guardado só quando versão/commit muda (90_arquivo/relatorios-antigos/)")

    projetos = projetos_versao(c, versao)
    linhas_proj = "".join(
        f'<tr class="proj--{e(p["estado"].split()[0])}"><td>{e(p["projeto"])}</td>'
        f'<td>{e(p["puxada"])}</td><td>{e(p["commit"] or "—")}</td>'
        f'<td>{e(p["quando"] or "—")}</td><td><span class="pill pill--{e(p["estado"].split()[0])}">{e(p["estado"])}</span></td></tr>'
        for p in projetos
    ) or '<tr><td colspan="5" class="det">nenhum projeto irmão com MEGABRAIN/ encontrado em ' \
         f'{e(str(raiz_projetos(c)))}</td></tr>'
    desatualizados = sum(1 for p in projetos if p["estado"] == "desatualizado")

    para_voce = secao_para_voce(c)
    bloco_para_voce = ""
    if para_voce:
        itens = "".join(
            "<li>" + re.sub(r"`([^`]+)`", r"<code>\1</code>", e(x)) + "</li>" for x in para_voce)
        bloco_para_voce = (f'<section class="voce"><span class="label">👉 para você — o que fazer agora '
                           f'({len(para_voce)})</span><ol>{itens}</ol>'
                           f'<p class="det">fonte: seção "PARA VOCÊ" do HANDOFF.md — edite lá, não aqui.</p></section>')

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

    # --- v6.6: peças visuais, conteúdo .md e CSS da biblioteca ---
    na_central = u.e_central(c) if hasattr(u, "e_central") else True
    pecas = pecas_visuais(c, git, versao, projetos, prog, na_central)
    navs_md, secoes_md = conteudo_md(c, na_central)
    css_extra = ""
    if vis is not None:
        try:
            css_extra = vis.css()
        except Exception:
            css_extra = ""
    css_extra += CSS_CONTEUDO
    bloco_indice = ("".join(f'<a href="#{e(i)}">{e(tt)}</a>' for i, tt in navs_md)
                    if navs_md else '<span class="det">nenhum .md informacional encontrado</span>')

    def slot(ident: str, titulo: str, corpo: str, vazio: str = "sem dado nesta instância") -> str:
        """Slot de posição fixa: existe sempre, mesmo vazio. É o que garante
        que o relatório de um projeto e o da central tenham a MESMA planta."""
        interno = corpo if corpo and corpo.strip() else f'<p class="slot__vazio">{e(vazio)}</p>'
        cab = f'<h3 class="slot__tit">{e(titulo)}</h3>' if titulo else ""
        return f'<section class="slot" id="{e(ident)}">{cab}{interno}</section>'

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
.versao {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(14rem,1fr)); gap:0; border:2px solid var(--ink); background:var(--paper-high); margin:1rem 0 1.25rem; }}
.versao > div {{ padding:.7rem .9rem; border-right:1px solid var(--line); }}
.versao > div:last-child {{ border-right:0; }}
.versao .label {{ display:block; margin-bottom:.2rem; }}
.versao .big {{ font:800 1.35rem/1.1 var(--mono); letter-spacing:-.03em; }}
.versao .anterior .big {{ color:var(--ink-faint); text-decoration:line-through; text-decoration-thickness:2px; }}
.ok {{ color:var(--ok); font-weight:700; }}
.alerta {{ color:var(--signal); font-weight:700; }}
.voce {{ border:2px solid var(--signal); background:var(--signal-soft); padding:.8rem 1rem 0.6rem; margin:0 0 1.5rem; }}
.voce ol {{ margin:.4rem 0 .4rem; padding-left:1.4rem; }}
.voce li {{ margin:.25rem 0; font-size:.95rem; }}
.pill {{ display:inline-block; padding:.05rem .45rem; border:1px solid currentColor; font:700 .62rem/1.5 var(--mono); text-transform:uppercase; letter-spacing:.06em; }}
.pill--atual {{ color:var(--ok); }}
.pill--desatualizado {{ color:var(--signal); }}
.pill--sem {{ color:var(--ink-faint); }}
tr.proj--desatualizado td {{ background:var(--signal-soft); }}
@media (max-width:44rem) {{ .duo {{ grid-template-columns:1fr; }} .versao > div {{ border-right:0; border-bottom:1px solid var(--line); }} }}
{css_extra}
</style>
</head>
<body>
<div class="wrap">

  <!-- ═══ D · DASHBOARD — planta fixa: D1→D5 nesta ordem, sempre ═══ -->
  <header id="d1-identidade">
    <span class="eyebrow">megabrain · relatório</span>
    <h1>{e(prog.get("projeto", "megabrain"))}</h1>
    <p class="meta pulse">gerado {agora:%d/%m %H:%M:%S} · recarrega sozinho a cada {RELOAD_SEGUNDOS}s · trava: {e(quem)} (até {e(ate)})</p>
    {f'<p class="det">{e(tldr)}</p>' if tldr else ""}
  </header>

  <div class="versao">
    <div>
      <span class="label">versão ATUAL</span>
      <span class="big">{e(versao_resumida(versao))}</span><br>
      <span class="det" title="{e(versao)}">{e(versao[:110])}{"…" if len(versao) > 110 else ""}</span>
    </div>
    <div>
      <span class="label">git (local)</span>
      <span class="big">{e(git["head_curto"])}</span><br>
      <span class="det">{e(git["assunto"][:80])}{" · " + e(git["data"]) if git["data"] else ""}</span><br>
      <span class="{push_cls}">{e(push_txt)}</span><span class="det">{e(suja_txt)}</span>
    </div>
    <div class="anterior">
      <span class="label">versão ANTERIOR</span>
      <span class="big">{e(anterior.get("versao", "—")) if anterior else "—"}</span><br>
      <span class="det">{anterior_txt}</span><br>
      <span class="det">{snapshot_txt}</span>
    </div>
  </div>

  {slot("d2-kpi", "", pecas["kpi"], "biblioteca visual ausente — rode python bin/mb_visual.py")}
  {slot("d3-acao", "Para você — o que fazer agora", bloco_para_voce, "nada pendente do seu lado (seção PARA VOCÊ do HANDOFF.md está vazia)")}
  {slot("d4-saude", "", pecas["saude"])}
  {slot("d5-distribuicao", "", pecas["distribuicao"] + f'<table><thead><tr><th>projeto</th><th>puxou</th><th>commit</th><th>quando</th><th>estado</th></tr></thead><tbody>{linhas_proj}</tbody></table><p class="det">fonte: <code>&lt;projeto&gt;/MEGABRAIN/VERSAO.txt</code> + <code>.mb-origem.json</code>. Desatualizado = rode <code>sincronizar-pipeline.cmd</code>.</p>' if projetos else pecas["distribuicao"], "nenhum projeto irmão com MEGABRAIN/ encontrado")}

  <!-- ═══ W · WORKFLOW — o desenho do sistema ═══ -->
  <h2 class="faixa">Workflow <small>— dados em modelos/visuais/exemplos.json; mecânicas em modelos/visuais/mecanicas/</small></h2>
  {slot("w1-gates", "", pecas["gates"])}
  {slot("w2-trilha", "", pecas["trilha"])}
  {slot("w3-camadas", "", pecas["camadas"])}
  {slot("w4-historico", "", pecas["historico"], "VERSAO.txt sem linhas no formato 'AAAA-MM-DD · vX.Y — título'")}

  <!-- ═══ E · ESTADO DA EXECUÇÃO ═══ -->
  <h2 class="faixa">Estado da execução <small>— PROGRESSO.json · HANDOFF.md · DECISOES.md · .mb-log/</small></h2>
  <section class="slot" id="e1-progresso">
    <span class="label">progresso — {feitas}/{len(etapas)} etapas ({pct}%)</span>
    <div class="barra"><div></div></div>
    <ul class="etapas">{"".join(linhas_etapas) or '<li class="det">sem etapas no PROGRESSO.json</li>'}</ul>
  </section>
  {slot("e2-notas", "Notas da execução", f'<ul class="notas">{linhas_notas}</ul>')}
  <div class="duo">
    <div>
      <section class="slot" id="e3-decisoes">
        <h3 class="slot__tit">Últimas decisões</h3>
        <div class="cartao"><ul class="simples">{linhas_dec}</ul></div>
      </section>
    </div>
    <div>
      <section class="slot" id="e4-eventos">
        <h3 class="slot__tit">Eventos de hoje</h3>
        <table><thead><tr><th>hora</th><th>agente</th><th>evento</th><th>resumo</th></tr></thead>
        <tbody>{linhas_ev}</tbody></table>
        <h3 class="slot__tit" style="margin-top:1rem">Fila 08_alteracoes-pendentes</h3>
        <table><thead><tr><th>nota</th><th>dono</th><th>idade</th></tr></thead>
        <tbody>{linhas_fila}</tbody></table>
        <p class="det">destaque = 7+ dias parada ou sem dono.</p>
      </section>
    </div>
  </div>

  <!-- ═══ C · CONTEÚDO — os .md da instância, agregados (era o RELATORIO.html antigo) ═══ -->
  <h2 class="faixa">Documentos <small>— {len(navs_md)} arquivo(s) .md desta instância, na íntegra</small></h2>
  <nav class="indice">{bloco_indice}</nav>
  <div class="doc">{secoes_md}</div>

  <!-- ═══ R · RODAPÉ ═══ -->
  <p class="meta" style="margin-top:2.5rem">fonte: PROGRESSO.json · ESTADO.md · HANDOFF.md · DECISOES.md · VERSAO.txt · git de {e(git["repo"] or "—")} · .mb-log/ · os .md acima. Arquivo local, não sobe pro GitHub.<br>
  sem servidor local o navegador não detecta mudança de arquivo — por isso o reload em intervalo fixo, preservando o scroll.<br>
  planta fixa D1–D5 · W1–W4 · E1–E4 · C: cada bloco tem lugar reservado e aparece vazio quando não há dado, para o relatório de qualquer projeto ter a mesma leitura.</p>
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
    return u.atomic_write_text(u.achar(c, "RELATORIO.html"), pagina)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--marcar", nargs="+", default=None,
                   metavar=("ID STATUS", "DETALHE"),
                   help='ex.: --marcar f2.1 feito "template criado"')
    p.add_argument("--nota", default=None)
    p.add_argument("--snapshot", action="store_true",
                   help="guarda o HTML atual em 90_arquivo/relatorios-antigos/ mesmo sem troca de versão")
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

    if not gerar_html(c, forcar_snapshot=args.snapshot):
        return 1
    print(f"relatório: {u.achar(c, 'RELATORIO.html')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
