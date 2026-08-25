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
títulos), .mb-log/ do dia, VERSAO.txt, git de _github/repo-local/ e os
VERSAO.txt das cópias MEGABRAIN/ dos projetos irmãos.

v6.1 (260821) — bloco de VERSÃO no topo:
  · versão atual do megabrain (VERSAO.txt) + commit git local (HEAD de
    _github/repo-local), remoto conhecido (origin/main) e quantos commits
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
import mb_trava as trava

try:
    import mb_visual as vis
except Exception:  # biblioteca visual ausente: relatório degrada, não quebra
    vis = None

try:
    import mb_workspace as ws  # v7.0: abas + workspace + feedback rail
except Exception:  # sem o módulo: página degrada pro fluxo único antigo
    ws = None

u.utf8_console()


# CSS do conteúdo agregado (.md) e dos slots fixos. Fica aqui, e não em
# modelos/visuais/, porque descreve a PÁGINA — as mecânicas descrevem peças.
CSS_CONTEUDO = """
html.pre-carga *, html.pre-carga *::before { transition: none !important; }

/* --- 260825: ações numeradas + skills expansíveis ------------------------
   Regra do 260804 (feedback nasce no campo visual de quem clicou): o corpo
   do <details> abre logo abaixo do próprio item, nunca em painel de rodapé.
   O número é grande e monoespaçado porque a frase que ele vai ouvir é
   "roda o 5" — o 5 tem que ser a primeira coisa que o olho acha. */
.acao { border:1px solid var(--line); border-left:3px solid var(--ink);
  background:var(--paper-high); margin:0 0 .35rem; }
.acao[open] { border-left-color:var(--signal); }
.acao > summary { display:grid; grid-template-columns:2.6rem minmax(9rem,auto) 1fr;
  gap:.6rem; align-items:baseline; padding:.55rem .7rem; cursor:pointer;
  list-style:none; }
.acao > summary::-webkit-details-marker { display:none; }
.acao > summary:hover { background:var(--signal-soft); }
.acao__n { font:800 1.25rem/1 var(--mono); color:var(--signal);
  text-align:right; font-variant-numeric:tabular-nums; }
.acao__nome { font:700 .92rem/1.3 var(--sans); }
.acao__faz { font:400 .82rem/1.45 var(--sans); color:var(--ink-soft); }
.acao__falta { font:700 .7rem var(--mono); color:var(--signal); }
.acao__corpo { padding:.2rem .7rem .7rem 3.9rem; border-top:1px solid var(--line); }
.acao__corpo p { margin:.5rem 0; font-size:.86rem; }
.acao--rotina > summary { grid-template-columns:minmax(15rem,auto) 1fr; }
.acao--rotina .acao__corpo, .acao--skill .acao__corpo { padding-left:.7rem; }
.acao--skill > summary { grid-template-columns:minmax(11rem,auto) 1fr; }
.acao--skill .acao__nome { font-family:var(--mono); color:var(--info); }
.skills__grupo { margin:1.1rem 0 .4rem; font:800 .68rem var(--mono);
  text-transform:uppercase; letter-spacing:.12em; color:var(--ink-faint); }
.copiar { font:600 .74rem var(--mono); padding:.3rem .6rem; cursor:pointer;
  border:1px solid var(--ink); background:var(--paper); color:var(--ink); }
.copiar:hover { background:var(--ink); color:var(--paper); }
.copiar[data-ok] { border-color:var(--ok); color:var(--ok); }
@media (max-width:640px) {
  .acao > summary { grid-template-columns:2.2rem 1fr; }
  .acao__faz { grid-column:1 / -1; }
  .acao__corpo { padding-left:.7rem; }
}
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

# Tema que abre por padrão. O usuário troca no seletor e a escolha persiste;
# este valor só vale na primeira visita (ou quando o storage está bloqueado).
TEMA_PADRAO = "02-wildfire"
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



# ---------------------------------------------------------------------------
# v6.6 — fusão: o relatório vivo absorveu o agregador de .md
# ---------------------------------------------------------------------------

# Pastas da central que NÃO entram no conteúdo do relatório: são código,
# derivado ou arquivo morto. Sem esta lista o rglob puxa referencias/,
# github-export/ e repo-local/ e o HTML passa de 2 MB.
#
# O casamento é por PEDAÇO de caminho (rel.parts), então entrada composta
# ("_github/export") NUNCA casa e o filtro vira no-op silencioso — foi o que
# fez cada documento aparecer 3× no HTML até 260825. A asserção abaixo mata
# a próxima tentativa na hora de importar, em vez de na conta do byte.
IGNORAR_CENTRAL = {
    "90_arquivo", "99_to_delete", "_github",
    "00_painel", "dist", "referencias", "modelos", "skills", "tests",
    "bin", "dna", "plugin-megabrain", "plugin-megabrain-claude",
    "relatorio-megabrain", "gerenteneuron", ".claude", ".mb-backup", ".mb-log",
    ".mb-aspirador", "__pycache__", ".git", "megabrain", "02_entrada",
    "motor",  # v7.1: a máquina inteira mora aqui — nada dela entra no relatório
}
assert not any("/" in x or "\\" in x for x in IGNORAR_CENTRAL), (
    "IGNORAR_CENTRAL casa por pedaço de caminho: entrada composta nunca casa")


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


e = html.escape  # escape de modulo: `e` local so existe dentro de gerar_html


def secao_acoes(c: Path) -> str:
    """As ações numeradas 1..N — a única lista do painel com número.

    260825: ele pediu pra poder ouvir "clica no script 3" em vez de decorar
    nome. O número vem de mb_registro.ACOES (declarado, estável), não da ordem
    da pasta — se viesse da pasta, um botão novo renumeraria os outros e a
    frase "clica no 3" passaria a apontar pro lugar errado na semana seguinte.
    """
    try:
        import mb_registro as reg
    except ImportError:
        return ""
    pasta = c / "01_acoes"
    linhas = []
    for n, apelido, faz, quando in reg.ACOES:
        arq = pasta / f"{n:02d}_{apelido}.cmd"
        existe = arq.is_file()
        rotulo = apelido.replace("-", " ")
        estado = "" if existe else ' <span class="acao__falta">arquivo não encontrado</span>'
        caminho = f"01_acoes\\{n:02d}_{apelido}.cmd"
        linhas.append(f"""<details class="acao">
<summary><span class="acao__n">{n}</span><span class="acao__nome">{e(rotulo)}</span>{estado}
<span class="acao__faz">{e(faz)}</span></summary>
<div class="acao__corpo">
<p><strong>Quando usar:</strong> {e(quando)}</p>
<p class="det">Está em <code>{e(caminho)}</code> — o número está no nome do arquivo,
então na pasta ele aparece nesta mesma ordem.</p>
<button class="copiar" data-copiar="{e(str(pasta / f'{n:02d}_{apelido}.cmd'))}">copiar caminho</button>
</div>
</details>""")
    cab = ('<p class="det">Clique para abrir na pasta <code>01_acoes\\</code>. '
           'O número é fixo: botão novo entra no fim e nunca renumera os outros — '
           'então "roda o 5" continua sendo o 5 daqui a três meses.</p>')
    return cab + "".join(linhas)


def secao_rotina(c: Path) -> str:
    """Comandos que rodam de vez em quando. Sem número de propósito: ele não
    procura por eles na pasta, chama quando precisa."""
    try:
        import mb_registro as reg
    except ImportError:
        return ""
    linhas = []
    for cmd, faz, quando in reg.ROTINA:
        linhas.append(f"""<details class="acao acao--rotina">
<summary><span class="acao__nome"><code>{e(cmd)}</code></span>
<span class="acao__faz">{e(faz)}</span></summary>
<div class="acao__corpo"><p><strong>Quando:</strong> {e(quando)}</p>
<button class="copiar" data-copiar="{e(cmd)}">copiar comando</button></div>
</details>""")
    return ('<p class="det">Sem número: você não procura estes na pasta, você chama '
            'quando precisa. Os de uso único já executados saíram de <code>bin/</code> '
            'e estão em <code>90_arquivo/scripts-uso-unico-260825/</code>.</p>'
            + "".join(linhas))


def secao_agente(c: Path) -> str:
    """Os comandos que a IA roda nos gates. Aparecem no painel dele NÃO pra ele
    rodar, mas porque comando que não está declarado em lugar nenhum não
    acontece: `mb-mapa-refs.py` tinha 4 citações em SKILL.md e zero execuções
    em 6 dias de log. Ver é a primeira condição de cobrar."""
    try:
        import mb_registro as reg
    except ImportError:
        return ""
    if not getattr(reg, "AGENTE", None):
        return ""
    linhas = []
    for cmd, gate, faz, quebra in reg.AGENTE:
        linhas.append(f"""<details class="acao acao--rotina">
<summary><span class="acao__nome"><code>{e(cmd)}</code></span>
<span class="acao__faz"><b>{e(gate)}</b> — {e(faz)}</span></summary>
<div class="acao__corpo"><p><strong>Se não rodar:</strong> {e(quebra)}</p>
<button class="copiar" data-copiar="{e(cmd)}">copiar comando</button></div>
</details>""")
    return ('<p class="det">Isto <b>não é pra você rodar</b> — é o que a IA deve '
            'rodar sozinha nos gates. Está aqui porque comando que não aparece em '
            'lugar nenhum é comando que não acontece: em 260825 o do Gate 3 tinha '
            '4 citações nas skills e zero execuções em 6 dias.</p>'
            + "".join(linhas))


def secao_skills(c: Path) -> str:
    """As skills DELE, expansíveis. As de plugin de terceiro ficam de fora —
    são 30+, ele não escreveu nem mantém, e listá-las é o próprio problema
    que ele descreveu ('fico olhando vários e perdido')."""
    try:
        import mb_registro as reg
    except ImportError:
        return ""
    por_origem: dict[str, list] = {}
    for nome, origem, faz, gatilho in reg.SKILLS_DELE:
        por_origem.setdefault(origem, []).append((nome, faz, gatilho))
    ordem = ["central", "plugin", "projeto", "Matt Pocock (MIT)"]
    rotulo = {"central": "Do protocolo (fonte em motor/skills/)",
              "plugin": "Do plugin", "projeto": "Dos seus projetos",
              "Matt Pocock (MIT)": "De fora — Matt Pocock, licença MIT"}
    partes = []
    for origem in ordem + [o for o in por_origem if o not in ordem]:
        if origem not in por_origem:
            continue
        partes.append(f'<h4 class="skills__grupo">{e(rotulo.get(origem, origem))}</h4>')
        for nome, faz, gatilho in por_origem[origem]:
            partes.append(f"""<details class="acao acao--skill">
<summary><span class="acao__nome">/{e(nome)}</span>
<span class="acao__faz">{e(faz)}</span></summary>
<div class="acao__corpo"><p><strong>Chama assim:</strong> {e(gatilho)}</p></div>
</details>""")
    return ('<p class="det">Só as suas. As de plugin de terceiro (cloudflare, figma, '
            'adobe, wordpress, canva) não entram aqui — você não as escreveu nem as '
            'mantém, e listar 30 a mais é o que faz você não achar as suas.</p>'
            + "".join(partes))


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


def secao_agentes(c: Path) -> str:
    """Absorve o RELATORIO-AGENTES.html (aposentado em 260825)."""
    d = _estado_json(c).get("agentes") or {}
    if not d.get("eventos"):
        return ""
    linhas = "".join(f"<tr><td>{e(k)}</td><td>{v}</td></tr>"
                     for k, v in list((d.get("por_agente") or {}).items())[:8])
    evs = "".join(f"<tr><td>{e(k)}</td><td>{v}</td></tr>"
                  for k, v in list((d.get("por_evento") or {}).items())[:8])
    return (f'<p class="det">{d["eventos"]} evento(s) em {d.get("dias_com_registro", "?")} '
            f'dia(s). Fonte: <code>{e(d.get("_fonte", ""))}</code></p>'
            f'<div class="duo"><div><table><thead><tr><th>agente</th><th>eventos</th></tr>'
            f'</thead><tbody>{linhas}</tbody></table></div>'
            f'<div><table><thead><tr><th>tipo de evento</th><th>n</th></tr></thead>'
            f'<tbody>{evs}</tbody></table></div></div>')


def secao_padroes(c: Path) -> str:
    """Absorve o AAMMDD_padroes.md (o compreensor continua rodando)."""
    d = _estado_json(c).get("padroes") or {}
    temas = d.get("temas") or []
    if not temas:
        return (f'<p class="det">Nada passou da régua — e isso é informação, não vazio. '
                f'Régua: {e(str(d.get("regua", ""))[:200])}</p>')
    itens = "".join(f"<li>{e(str(x)[:200])}</li>" for x in temas)
    return f'<ul>{itens}</ul><p class="det">Régua: {e(str(d.get("regua", ""))[:200])}</p>'


def secao_copias(c: Path) -> str:
    """Os megabrains de projeto — absorve a auditoria de cópias."""
    d = _estado_json(c).get("copias") or {}
    itens = d.get("itens") or []
    if not itens:
        return ""
    linhas = "".join(
        f'<tr><td>{e(i["projeto"])}</td><td>{e(i["versao"])}</td>'
        f'<td>{"✓" if i["em_dia"] else "✕ desatualizada"}</td>'
        f'<td>{i["licoes"]}</td><td>{e(i["layout"])}</td></tr>' for i in itens)
    return (f'<p class="det">{d.get("em_dia")}/{d.get("total")} em dia · '
            f'{d.get("com_morto")} com arquivo aposentado. '
            f'Desatualizada = rode a ação <b>5</b>.</p>'
            f'<table><thead><tr><th>projeto</th><th>versão</th><th>estado</th>'
            f'<th>lições</th><th>layout</th></tr></thead><tbody>{linhas}</tbody></table>')


def secao_para_ia(c: Path) -> str:
    """O bloco que fecha o ciclo: a IA não lê este HTML, lê o JSON."""
    d = _estado_json(c)
    if not d:
        return ""
    return (
        '<p>Este HTML é a renderização <b>humana</b>. A renderização de máquina é '
        '<code>dados/estado.json</code> — mesmo dado, mesma geração, sem prosa. '
        'Qualquer IA (Claude, Kimi, GPT, Gemini, Codex, Qwen local) lê aquele arquivo '
        'em vez de parsear cinco markdowns em cinco formatos.</p>'
        f'<p class="det">schema {d.get("schema")} · gerado {e(str(d.get("gerado_em", "")))} · '
        'cada número lá dentro carrega o <code>_fonte</code> de onde veio, e campo que '
        'não pôde ser medido vem <code>null</code> — nunca zero.</p>'
        '<button class="copiar" data-copiar="python bin/mb-estado.py --stdout">'
        'copiar comando que gera o JSON</button>')


def _titulo_md(relativo: str, texto: str) -> str:
    for linha in texto.splitlines():
        if linha.startswith("# "):
            return linha[2:].strip()
    return Path(relativo).stem.replace("_", " ").replace("-", " ")


def conteudo_md(inst: Path, na_central: bool) -> tuple[list[tuple[str, str]], str]:
    """ÍNDICE dos .md — não mais o conteúdo deles.

    260825 (decisão 260825v): esta função embutia os 31 documentos inteiros no
    HTML — 471 KB, 76% do arquivo. Ela existia porque uma IA precisava do texto
    e o único jeito era o relatório agregar. Com `dados/estado.json` carregando
    o índice (caminho, título, tamanho, quando mudou), a IA lê o arquivo de que
    precisa e o painel volta a ser painel: uma lista de links, não um despejo.

    O leitor humano ganha também — ele clicava e caía num poço de 31 seções
    sem navegação. Agora vê o que existe e abre o que quer.
    """
    import json as _json
    dados = _json.loads(u.safe_read_text(inst / "dados" / "estado.json") or "{}")
    docs = (dados.get("documentos") or {}).get("itens") or []
    if not docs:
        return [], ('<p class="slot__vazio">índice ausente — rode '
                    '<code>python bin/mb-estado.py</code></p>')
    grupos: dict[str, list] = {}
    for d in docs:
        raiz = d["caminho"].split("/")[0] if "/" in d["caminho"] else "raiz"
        grupos.setdefault(raiz, []).append(d)
    partes = [f'<p class="det">{len(docs)} documento(s). Clique pra abrir o arquivo. '
              'O texto não é embutido aqui de propósito: 76% deste relatório era '
              'despejo de markdown que existia só pra IA ler — hoje ela lê '
              '<code>dados/estado.json</code>.</p>']
    navs = []
    for raiz in sorted(grupos):
        partes.append(f'<h4 class="skills__grupo">{e(raiz)}</h4><table>'
                      '<thead><tr><th>documento</th><th>tamanho</th><th>mudou</th></tr></thead><tbody>')
        for d in sorted(grupos[raiz], key=lambda x: x["caminho"]):
            href = "../" + d["caminho"]
            kb = f'{d["bytes"] // 1024} KB' if d["bytes"] >= 1024 else f'{d["bytes"]} B'
            partes.append(f'<tr><td><a href="{e(href)}">{e(d["titulo"])}</a>'
                          f'<br><code class="det">{e(d["caminho"])}</code></td>'
                          f'<td>{e(kb)}</td><td>{e(str(d.get("modificado") or "—"))}</td></tr>')
        partes.append("</tbody></table>")
    return navs, "".join(partes)


def _conteudo_md_antigo(inst: Path, na_central: bool) -> tuple[list[tuple[str, str]], str]:
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
         "det": "05_sincronizar-projetos.cmd" if atrasados else ("nada a fazer" if projetos else "sem projetos irmãos")},
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
    try:
        import mb_registro as _mbreg
        _reg_acoes = _mbreg.ACOES
    except ImportError:
        _reg_acoes = []
    # v7.5: o h1 mostrava PROGRESSO.json["projeto"], string congelada na v6.7 —
    # a primeira coisa que ele lê pra saber "onde estou" mentia a versão.
    # Nome vem do PROGRESSO (sem o sufixo de versão), número vem do VERSAO.txt.
    nome_projeto = re.sub(r"\s+v\d+(\.\d+)*\b.*$", "",
                          str(prog.get("projeto", "megabrain"))).strip() or "megabrain"
    titulo_h1 = f"{nome_projeto} {versao_resumida(versao)}"
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
            "<li>" + re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>",
                            re.sub(r"`([^`]+)`", r"<code>\1</code>", e(x))) + "</li>"
            for x in para_voce)
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

    # --- v7.0: workspace (abas, controles, feedback rail) ---
    if ws is not None:
        modo = ws.modo_atual(c)
        topbar = ws.html_topbar(modo)
        tabnav = ws.tabs_nav()
        rail = ws.html_rail()
        js_ws = ws.js_workspace()
        esquema_html = ws.html_esquema()
        # 260825: a lista de acoes/skills sai de mb_registro (numerada,
        # declarada), nao da varredura de comentario do .cmd — uma fonte so.
        bloco_acoes = secao_acoes(c) + secao_rotina(c)
        bloco_skills = secao_skills(c)
        bloco_cerebro = ws.html_cerebro(ws.cerebro_dados(c))
        bloco_telemetria = ws.html_telemetria(ws.telemetria_dados(c))
        ask = ws.html_ask
        pa, pf = ws.pane_abre, ws.pane_fecha
    else:
        topbar = tabnav = rail = js_ws = esquema_html = ""
        bloco_acoes = bloco_skills = bloco_cerebro = bloco_telemetria = ""
        ask = (lambda _p, rotulo="": "")
        pa = (lambda _ident: "")
        pf = (lambda: "")
    css_extra = ""
    antiflash = seletor_html = seletor_js = ""
    if vis is not None:
        try:
            # ordem importa: tokens (contrato) → mecânicas → TEMAS → seletor.
            # [data-tema=...] tem a mesma especificidade que :root, então quem
            # vem depois manda. Os blocos de modo usam :not() (padrão Pico),
            # e por isso a escolha explícita ganha do sistema nos dois sentidos.
            css_extra = vis.css() + "\n" + vis.css_temas() + "\n" + vis.css_seletor()
            antiflash = vis.script_antiflash()
            seletor_html = vis.html_seletor(TEMA_PADRAO)
            seletor_js = vis.js_seletor()
        except Exception:
            css_extra = ""
    css_extra += CSS_CONTEUDO
    if ws is not None:
        css_extra += ws.CSS
    # 260825: navs_md ficou vazio de propósito — o conteúdo virou índice com
    # link pro arquivo, então não há âncora interna pra listar.
    bloco_indice = ("".join(f'<a href="#{e(i)}">{e(tt)}</a>' for i, tt in navs_md)
                    if navs_md else "")

    def slot(ident: str, titulo: str, corpo: str, vazio: str = "sem dado nesta instância") -> str:
        """Slot de posição fixa: existe sempre, mesmo vazio. É o que garante
        que o relatório de um projeto e o da central tenham a MESMA planta."""
        interno = corpo if corpo and corpo.strip() else f'<p class="slot__vazio">{e(vazio)}</p>'
        cab = f'<h3 class="slot__tit">{e(titulo)}</h3>' if titulo else ""
        return f'<section class="slot" id="{e(ident)}">{cab}{interno}</section>'

    pagina = f"""<!doctype html>
<html lang="pt-BR" data-tema="{TEMA_PADRAO}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<script>{antiflash}</script>
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
.eyebrow,.label {{ /* rótulo é hierarquia, não estado */ color:var(--ink-faint); font:800 .66rem/1.3 var(--mono); letter-spacing:.1em; text-transform:uppercase; }}
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
th {{ font:800 .62rem/1.3 var(--mono); text-transform:uppercase; letter-spacing:.08em; color:var(--ink-faint); }}
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
    <h1>{e(titulo_h1)}</h1>
    <p class="meta pulse">gerado {agora:%d/%m %H:%M:%S} · recarrega sozinho a cada {RELOAD_SEGUNDOS}s · trava: {e(quem)} (até {e(ate)})</p>
    {f'<p class="det">{e(tldr)}</p>' if tldr else ""}
  </header>

  {seletor_html}
  {topbar}
  {tabnav}
  <div class="panes" id="panes" data-n="1">
  {pa("painel")}
  {ask("em que pé está o megabrain agora — e o que depende de mim?")}

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
  {slot("d5-distribuicao", "", pecas["distribuicao"] + f'<table><thead><tr><th>projeto</th><th>puxou</th><th>commit</th><th>quando</th><th>estado</th></tr></thead><tbody>{linhas_proj}</tbody></table><p class="det">fonte: <code>&lt;projeto&gt;/MEGABRAIN/VERSAO.txt</code> + <code>.mb-origem.json</code>. Desatualizado = rode <code>05_sincronizar-projetos.cmd</code>.</p>' if projetos else pecas["distribuicao"], "nenhum projeto irmão com MEGABRAIN/ encontrado")}

  <!-- ═══ D7 · O QUE VOCÊ CLICA — a única lista numerada do painel ═══ -->
  <h2 class="faixa">O que você clica <small>— 01_acoes\\, numerado de 1 a {len(_reg_acoes)}</small></h2>
  {slot("d7-acoes", "", secao_acoes(c), "registro de ações ausente (bin/mb_registro.py)")}
  {slot("d8-rotina", "Comandos de manutenção", secao_rotina(c), "sem comandos de rotina declarados")}
  {slot("d9-skills", "Suas skills — clique pra ver o que cada uma faz", secao_skills(c), "sem skills declaradas")}
  {slot("d10-agente", "O que a IA roda nos gates (não é pra você clicar)", secao_agente(c), "sem comandos de gate declarados")}

  {slot("d6-telemetria", "Telemetria — o caderninho local desta central", bloco_telemetria, "sem telemetria nesta instância")}

  <!-- ═══ D11-D14 · o que era artefato separado e agora mora aqui ═══ -->
  <h2 class="faixa">O resto <small>— o que antes eram 5 arquivos separados</small></h2>
  {slot("d11-agentes", "Uso por agente", secao_agentes(c), "sem eventos em .mb-log/")}
  {slot("d12-padroes", "O que já se repete e não virou modelo", secao_padroes(c), "compreensor não rodou ainda — ação 2")}
  {slot("d13-copias", "Os megabrains dos seus projetos", secao_copias(c), "nenhuma cópia de projeto encontrada")}
  {slot("d14-para-ia", "Para a IA — este HTML não é a fonte", secao_para_ia(c), "dados/estado.json ausente — rode python bin/mb-estado.py")}

  <!-- ═══ E · ESTADO DA EXECUÇÃO (segue na aba Painel) ═══ -->
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
        <h3 class="slot__tit" style="margin-top:1rem">Fila memoria/pendencias</h3>
        <table><thead><tr><th>nota</th><th>dono</th><th>idade</th></tr></thead>
        <tbody>{linhas_fila}</tbody></table>
        <p class="det">destaque = 7+ dias parada ou sem dono.</p>
      </section>
    </div>
  </div>

  {pf()}

  {pa("esquema")}
  {ask("como as peças se ligam: minha central, o GitHub, as outras pessoas e os projetos?")}
  <h2 class="faixa">O esquema do megabrain <small>— central · GitHub · usuários · projetos · o que desce e o que sobe</small></h2>
  {esquema_html}
  <h2 class="faixa">Workflow <small>— dados em modelos/visuais/exemplos.json; mecânicas em modelos/visuais/mecanicas/</small></h2>
  {slot("w1-gates", "", pecas["gates"])}
  {slot("w2-trilha", "", pecas["trilha"])}
  {slot("w3-camadas", "", pecas["camadas"])}
  {pf()}

  {pa("acoes")}
  {ask("quais botões existem e o que cada um faz quando eu clico?")}
  <h2 class="faixa">Ações <small>— os botões da central, numerados de 1 a {len(_reg_acoes)}</small></h2>
  <p class="det">A lista mora na primeira dobra do Painel, na seção <b>O que você clica</b> —
  <a href="#d7-acoes">ir pra lá</a>. Está num lugar só de propósito: a mesma lista em
  duas seções é como o número de uma delas começa a mentir.</p>
  {pf()}

  {pa("skills")}
  {ask("que poderes o megabrain tem, e como eu chamo cada um?")}
  <h2 class="faixa">Skills <small>— as suas, com gatilho e o que fazem</small></h2>
  <p class="det">Também na primeira dobra do Painel, em <b>Suas skills</b> —
  <a href="#d9-skills">ir pra lá</a>.</p>
  {pf()}

  {pa("cerebro")}
  <h2 class="faixa">Cérebro <small>— memoria/cerebro: raw (fonte crua) · wiki (destilado) · pessoas · o que vence</small></h2>
  {bloco_cerebro}
  {pf()}

  {pa("docs")}
  <!-- ═══ C · CONTEÚDO — os .md da instância, agregados ═══ -->
  <h2 class="faixa">Documentos <small>— o que existe nesta instância, com link pro arquivo</small></h2>
  {bloco_indice}
  <div class="doc">{secoes_md}</div>
  {pf()}

  {pa("historico")}
  {ask("o que mudou de versão pra versão, e onde estão os relatórios antigos?")}
  <h2 class="faixa">Histórico <small>— linha do tempo de versões e relatórios antigos</small></h2>
  {slot("w4-historico", "", pecas["historico"], "VERSAO.txt sem linhas no formato 'AAAA-MM-DD · vX.Y — título'")}
  <p class="det">Relatórios como estavam antes de cada troca de versão: <code>90_arquivo\\relatorios-antigos\\INDICE.md</code></p>
  {pf()}
  </div><!-- /panes -->
  {rail}

  <!-- ═══ R · RODAPÉ ═══ -->
  <p class="meta" style="margin-top:2.5rem">fonte: PROGRESSO.json · ESTADO.md · HANDOFF.md · DECISOES.md · VERSAO.txt · git de {e("_github/repo-local" if git["repo"] else "—")} · .mb-log/ · os .md acima. Arquivo local, não sobe pro GitHub.<br>
  sem servidor local o navegador não detecta mudança de arquivo — por isso o reload em intervalo fixo, preservando o scroll.<br>
  planta fixa D1–D6 · W1–W4 · E1–E4 · C · CB (cérebro): cada bloco tem lugar reservado e aparece vazio quando não há dado, para o relatório de qualquer projeto ter a mesma leitura.</p>
</div>
<script>{seletor_js}</script>
<script>{js_ws}</script>
<script>
requestAnimationFrame(function () {{ requestAnimationFrame(function () {{
  document.documentElement.classList.remove("pre-carga");
}}); }});
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

/* 260825 — o painel recarrega a cada {RELOAD_SEGUNDOS}s. Sem isto, tudo que ele
   abre fecha sozinho antes de terminar de ler: expandir viraria uma armadilha
   em vez de um recurso. Guarda quais <details> estão abertos e reabre. */
(function () {{
  var KEY = "mb-vivo-abertos";
  var abertos;
  try {{ abertos = JSON.parse(sessionStorage.getItem(KEY) || "[]"); }}
  catch (e) {{ abertos = []; }}
  var itens = document.querySelectorAll("details.acao");
  itens.forEach(function (d, i) {{
    var id = d.querySelector(".acao__nome");
    id = id ? id.textContent.trim() : ("i" + i);
    d.dataset.mbId = id;
    if (abertos.indexOf(id) !== -1) {{ d.open = true; }}
    d.addEventListener("toggle", function () {{
      var lista = [];
      document.querySelectorAll("details.acao[open]").forEach(function (x) {{
        lista.push(x.dataset.mbId);
      }});
      try {{ sessionStorage.setItem(KEY, JSON.stringify(lista)); }} catch (e) {{}}
    }});
  }});
}})();

/* Copiar caminho/comando. Navegador não executa .cmd a partir de file:// —
   por isso o botão entrega o texto pronto pra colar, e o número no NOME do
   arquivo é o que faz você achar na pasta. */
(function () {{
  document.querySelectorAll("button.copiar").forEach(function (b) {{
    b.addEventListener("click", function (ev) {{
      ev.preventDefault();
      var txt = b.getAttribute("data-copiar") || "";
      var feito = function () {{
        var antes = b.textContent;
        b.textContent = "copiado";
        b.setAttribute("data-ok", "1");
        setTimeout(function () {{
          b.textContent = antes; b.removeAttribute("data-ok");
        }}, 1600);
      }};
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(txt).then(feito, function () {{ prompt("copie:", txt); }});
      }} else {{
        prompt("copie:", txt);
      }}
    }});
  }});
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

        relatorio_path = u.achar(c, "RELATORIO.html")
        with trava.travado(relatorio_path, agente_arquivo,
                           "regenera relatório e snapshots"):
            if not gerar_html(c, forcar_snapshot=args.snapshot):
                return 1
    except trava.TravaOcupada as e:
        print(f"ERRO: {e}")
        return 1
    print(f"relatório: {u.achar(c, 'RELATORIO.html')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
