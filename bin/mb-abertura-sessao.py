#!/usr/bin/env python3
"""
mb-abertura-sessao.py — abre a sessão ressincronizando central e git (v7.15, 260914).

Pedido do dono (<USUARIO>, 260914): "quero que em todo início de sessão desse e
todos os projetos haja uma ressincronizada com o git e no meu caso com a pasta
central, afinal eu sou o criador e dono."

O que faz, em ordem:
  1. acha a central: MEGABRAIN_CENTRAL → pasta deste script → projeto e seus
     ancestrais → ponteiro MEGABRAIN/.mb-origem.json → irmãs do projeto e de
     <PROJETOS_ROOT>/;
  2. central → projeto chamando o mb-check-version.py DA CENTRAL. O sync mora
     lá; aqui só se decide SE chama;
  3. git conservador na central e no projeto: com remote, fetch; com upstream
     e nenhum commit local à frente, pull --ff-only. Sem remote, só status.
     Nunca stage, commit ou push — _git() recusa qualquer verbo fora da lista;
  4. retrato de abertura, TL;DR primeiro;
  5. uma linha em <projeto>/.mb-log/sessao.jsonl.

Uso:
  python bin/mb-abertura-sessao.py                    # projeto = pasta atual
  python bin/mb-abertura-sessao.py --projeto CAMINHO
  python bin/mb-abertura-sessao.py --offline          # sem fetch/pull
  python bin/mb-abertura-sessao.py --seco             # não grava nada; diz o que faria

Exit 0 mesmo com aviso (cópia tocada, git sem rede, divergência). Exit 1 só em
erro real: projeto inexistente ou central não achada.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

import mb_utils as u

u.utf8_console()

AQUI = Path(__file__).resolve().parent
# Sanitizado no export público (mb-generate-template troca por <PROJETOS_ROOT>/);
# lá a pasta não existe e a busca por irmãs só pula esta raiz.
RAIZ_PROJETOS = "<PROJETOS_ROOT>/"

# A garantia "nunca commit/push" mora aqui, não na boa vontade de quem edita:
# _git() recusa verbo fora desta lista e pull sem --ff-only.
GIT_VERBOS = ("rev-parse", "remote", "status", "rev-list", "fetch", "pull")

TIMEOUT_SYNC = 90
TIMEOUT_GIT = 15
TIMEOUT_REDE = 30

LIVRE = {"livre", "-", "—", "nenhum", "ninguém", "ninguem"}


# ---------------------------------------------------------------------------
# onde estou: projeto e central
# ---------------------------------------------------------------------------

def _mesmo(a: Path | None, b: Path | None) -> bool:
    if a is None or b is None:
        return False
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.normcase(str(a)) == os.path.normcase(str(b))


def e_central_real(p: Path) -> bool:
    """e_central() + motor/ + o sync.

    A cópia cheia de projeto (MEGABRAIN/ com VERSAO.txt, MEGABRAIN.md e bin/)
    também passa no e_central(). Sem exigir motor/, a abertura rodada de dentro
    da cópia trataria a cópia como central e sincronizaria a cópia com ela mesma.
    """
    try:
        return (p.is_dir() and (p / "motor").is_dir() and u.e_central(p)
                and (p / "bin" / "mb-check-version.py").is_file())
    except OSError:
        return False


def e_projeto(d: Path) -> bool:
    """Marcador por conteúdo, os mesmos do mb-contexto.py (lição 260825:
    worktree é o mesmo projeto em outro endereço — caminho fixo não serve)."""
    try:
        return ((d / "MEGABRAIN").is_dir() or (d / ".mb-origem.json").is_file()
                or u.achar(d, "META.md").is_file())
    except OSError:
        return False


def resolver_projeto(pedido: Path) -> Path:
    """Sobe da pasta pedida até o primeiro marcador; sem marcador, fica a pedida.

    Duplo clique no .cmd abre com a pasta atual = 01_acoes/. Sem subir, o sync
    criaria uma cópia MEGABRAIN/ dentro da pasta de botões da central.
    """
    for d in (pedido, *pedido.parents):
        if e_projeto(d):
            return d
    return pedido


def achar_central(projeto: Path) -> tuple[Path | None, str]:
    """(central, como foi achada)."""
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        p = Path(env).expanduser().resolve()
        if e_central_real(p):
            return p, "MEGABRAIN_CENTRAL"
        # Configuração explícita errada é erro, não convite pra outra central.
        return None, f"MEGABRAIN_CENTRAL aponta pra {p}, que não é uma central"

    for cand, como in ((AQUI.parent, "pasta do script"),
                       *((d, "ancestral do projeto") for d in (projeto, *projeto.parents))):
        if e_central_real(cand):
            return cand, como

    try:
        ponteiro = json.loads(u.safe_read_text(projeto / "MEGABRAIN" / ".mb-origem.json") or "{}")
    except ValueError:
        ponteiro = {}
    c = ponteiro.get("central") if isinstance(ponteiro, dict) else None
    if isinstance(c, str) and c.strip() and e_central_real(Path(c)):
        return Path(c).resolve(), "ponteiro .mb-origem.json"

    vistas = set()
    for r in (os.environ.get("MEGABRAIN_PROJETOS_ROOT"), str(projeto.parent), RAIZ_PROJETOS):
        if not r:
            continue
        raiz = Path(r)
        chave = os.path.normcase(os.path.abspath(raiz))
        if chave in vistas or not raiz.is_dir():
            continue
        vistas.add(chave)
        try:
            filhos = sorted(d for d in raiz.iterdir() if d.is_dir())
        except OSError:
            continue
        for d in filhos:
            if e_central_real(d):
                return d.resolve(), f"irmã em {raiz}"
    return None, ("nenhuma central achada (MEGABRAIN_CENTRAL, pasta do script, "
                  "projeto e ancestrais, .mb-origem.json, irmãs)")


def carregar_check_version(central: Path):
    """O mb-check-version da CENTRAL, como módulo (hífen impede import normal).

    Usado só pra LER versão e comparar — a decisão de ordem é dele, não daqui.
    """
    arq = central / "bin" / "mb-check-version.py"
    spec = importlib.util.spec_from_file_location("mb_check_version", arq)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for nome in ("comparar_versoes", "ler_versao", "ler_versao_projeto", "parse_versao",
                 "e_copia_magra"):
        if not hasattr(mod, nome):
            raise AttributeError(f"{arq} sem {nome}() — central mais velha que este script")
    return mod


def curta(cv, linha: str | None) -> str:
    """'2026-09-14 · v7.15 — changelog…' → 'v7.15 (2026-09-14)'."""
    if not linha:
        return "sem versão"
    data, num = cv.parse_versao(linha)
    if data and num:
        return f"v{num} ({data})"
    return linha.split("—")[0].strip()[:40]


# ---------------------------------------------------------------------------
# 2. sync central → projeto
# ---------------------------------------------------------------------------

def _linha_erro(linhas: list[str]) -> str:
    for marca in ("ERRO", "ATENÇÃO"):
        for linha in linhas:
            if marca in linha:
                return linha
    return linhas[-1] if linhas else "sem saída"


def sincronizar(central: Path, projeto: Path, cv, seco: bool) -> dict:
    if _mesmo(projeto, central):
        return {"estado": "central", "resumo": "é a própria central — nada a puxar"}
    mb = projeto / "MEGABRAIN"
    if not mb.is_dir():
        # O hook roda em qualquer pasta onde uma sessão abre. Criar MEGABRAIN/ e
        # cerebro/ em pasta que não é projeto seria sujeira a cada abertura.
        return {"estado": "pulado",
                "resumo": "sem MEGABRAIN/ — não é projeto megabrain, nada criado "
                          "(projeto novo: 01_acoes/04_novo-projeto.cmd)"}

    v_central = cv.ler_versao(central)
    v_antes = cv.ler_versao_projeto(str(mb))
    relacao = cv.comparar_versoes(v_central, v_antes)
    magra = cv.e_copia_magra(str(mb))
    antes, depois = curta(cv, v_antes), curta(cv, v_central)

    cmd = [sys.executable, "-X", "utf8", str(central / "bin" / "mb-check-version.py"),
           "--projeto", str(projeto), "--central", str(central), "--auto"]
    # "indefinido" + --auto SOBRESCREVE sem perguntar (é o contrato do
    # mb-check-version); a lição 260815 manda perguntar. Abertura não pergunta:
    # ensaia e devolve a decisão.
    ensaio = seco or relacao == "indefinido"
    if ensaio:
        cmd.append("--dry-run")

    if seco:
        previsto = {
            "igual": "conferir se a cópia está intacta (nada a copiar)",
            "central": f"atualizar {antes} → {depois}" + (" (cópia magra: só o ponteiro)" if magra else ""),
            "projeto": "nada — projeto mais novo que a central, não sobrescreve",
            "indefinido": "nada — versões sem ordem clara, decisão sua",
        }.get(relacao, relacao)
        rotulo = "[seco] faria: mb-check-version --auto → " + previsto
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL,
                           timeout=TIMEOUT_SYNC, check=False)
    except subprocess.TimeoutExpired:
        return {"estado": "erro", "resumo": f"mb-check-version passou de {TIMEOUT_SYNC}s", "antes": antes}
    except OSError as e:
        return {"estado": "erro", "resumo": f"não rodou mb-check-version: {e}", "antes": antes}

    linhas = [x.strip() for x in f"{r.stdout}\n{r.stderr}".splitlines() if x.strip()]
    if seco:
        if r.returncode not in (0, 2):
            rotulo += f" · ensaio falhou: {_linha_erro(linhas)}"
        return {"estado": "seco", "resumo": rotulo, "antes": antes}
    if relacao == "indefinido":
        return {"estado": "aviso", "antes": antes,
                "resumo": f"versões sem ordem clara ({antes} × {depois}) — não sobrescrevi; "
                          f"decida com: python bin/mb-check-version.py --projeto \"{projeto}\""}
    if r.returncode == 1 or r.returncode not in (0, 2):
        return {"estado": "erro", "resumo": f"falhou: {_linha_erro(linhas)}", "antes": antes}
    if r.returncode == 2:
        if relacao == "projeto":
            texto = (f"projeto ({antes}) mais novo que a central ({depois}) — não sobrescrevi; "
                     "suba com mb-sync-projeto-para-central.py")
        else:
            texto = ("cópia MEGABRAIN/ editada no projeto (difere da central) — não sobrescrevi; "
                     "suba com mb-sync-projeto-para-central.py ou restaure com --force")
        return {"estado": "aviso", "resumo": texto, "antes": antes}
    if relacao == "central":
        texto = f"atualizou {antes} → {depois}" + (" (cópia magra: só o ponteiro)" if magra else "")
    else:
        texto = "em dia, cópia intacta"
    return {"estado": "ok", "resumo": texto, "antes": antes}


# ---------------------------------------------------------------------------
# 3. git conservador
# ---------------------------------------------------------------------------

def _git(repo: Path, *args: str, timeout: int = TIMEOUT_GIT) -> tuple[int, str]:
    """Único ponto que chama git. Falha fechada: verbo fora da lista levanta."""
    verbo = args[0] if args else ""
    if verbo not in GIT_VERBOS or (verbo == "pull" and "--ff-only" not in args):
        raise ValueError(f"git {' '.join(args)} recusado: a abertura só lê, busca e avança")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never",
               GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                           timeout=timeout, env=env, check=False)
    except FileNotFoundError:
        return 127, "git não instalado"
    except subprocess.TimeoutExpired:
        return 124, f"passou de {timeout}s"
    except OSError as e:
        return 1, str(e)
    saida = r.stdout if r.returncode == 0 else (r.stderr or r.stdout)
    return r.returncode, (saida or "").strip()


def _git_ok(repo: Path, *args: str) -> str | None:
    rc, saida = _git(repo, *args)
    return saida if rc == 0 and saida else None


def _primeira(texto: str) -> str:
    for linha in (texto or "").splitlines():
        linha = linha.strip()
        if linha:
            return linha[:120]
    return "sem mensagem"


def _buscar_e_avancar(topo: Path) -> tuple[str, str]:
    rc, msg = _git(topo, "fetch", "--quiet", timeout=TIMEOUT_REDE)
    if rc != 0:
        return "aviso", f"não consegui buscar o servidor ({_primeira(msg)})"
    upstream = _git_ok(topo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if not upstream:
        return "ok", "buscou o servidor · ramo sem upstream, nada a puxar"
    contagem = _git_ok(topo, "rev-list", "--left-right", "--count", "HEAD...@{u}")
    try:
        frente, atras = (int(x) for x in (contagem or "").split())
    except ValueError:
        return "aviso", f"buscou, mas não consegui comparar com {upstream}"
    if atras == 0:
        extra = f" ({frente} commit(s) seu(s) ainda não enviado(s))" if frente else ""
        return "ok", f"em dia com {upstream}{extra}"
    if frente:
        return "aviso", (f"divergiu de {upstream}: {frente} commit(s) seu(s) × {atras} do servidor "
                         "— não puxei, decisão sua")
    rc, msg = _git(topo, "pull", "--ff-only", "--no-autostash", "--quiet", timeout=TIMEOUT_REDE)
    if rc != 0:
        return "aviso", f"{atras} commit(s) no servidor, pull --ff-only recusado ({_primeira(msg)})"
    return "ok", f"puxou {atras} commit(s) de {upstream} (só avanço, sem mesclar)"


def estado_git(pasta: Path, offline: bool, seco: bool, topo_central: Path | None = None) -> dict:
    rc, topo_txt = _git(pasta, "rev-parse", "--show-toplevel")
    if rc == 127:
        return {"estado": "sem git", "resumo": "git não instalado", "topo": None}
    if rc != 0 or not topo_txt:
        return {"estado": "sem repo", "resumo": "sem repo", "topo": None}
    topo = Path(topo_txt).resolve()
    if topo_central is not None and _mesmo(topo, topo_central):
        return {"estado": "mesmo repo", "resumo": "mesmo repo da central (ver acima)", "topo": topo}

    ramo = _git_ok(topo, "rev-parse", "--abbrev-ref", "HEAD") or "?"
    head = _git_ok(topo, "rev-parse", "--short", "HEAD") or "sem commit"
    tem_remote = bool(_git_ok(topo, "remote"))
    if not tem_remote:
        estado, rede = "sem remote", "só local (sem remote)"
    elif offline:
        estado, rede = "offline", "offline: não busquei o servidor"
    elif seco:
        estado, rede = "seco", ("[seco] faria: git fetch + git pull --ff-only "
                                "(só se não houver commit local à frente)")
    else:
        estado, rede = _buscar_e_avancar(topo)

    rc_s, status = _git(topo, "status", "--porcelain")
    if rc_s != 0:
        local = "status ilegível"
    else:
        sujos = sum(1 for linha in status.splitlines() if linha.strip())
        local = "sem alteração local" if sujos == 0 else f"{sujos} arquivo(s) alterado(s) sem commit"
    return {"estado": estado, "resumo": f"{ramo} @{head} · {rede} · {local}", "topo": topo}


# ---------------------------------------------------------------------------
# 4. trava e 5. telemetria
# ---------------------------------------------------------------------------

def ler_trava(projeto: Path) -> str:
    """Trava do HANDOFF.md. Qualquer TRAVADO_POR não-livre conta — o bloco do
    mb-sync fica no fim e há HANDOFF com a trava no topo; esconder uma trava
    velha custa mais que mostrar uma."""
    texto = u.safe_read_text(u.achar(projeto, "HANDOFF.md"))
    if texto is None:
        return "sem HANDOFF.md"
    blocos = re.findall(r"^TRAVADO_POR:[ \t]*(.*?)[ \t]*$(?:\n^AT[EÉ]:[ \t]*(.*?)[ \t]*$)?",
                        texto, re.MULTILINE)
    if not blocos:
        return "HANDOFF.md sem TRAVADO_POR"
    presos = [(quem, ate) for quem, ate in blocos
              if (quem.split() or ["-"])[0].strip(".,;:").lower() not in LIVRE]
    if not presos:
        return "livre"
    quem, ate = presos[-1]
    return f"TRAVADO_POR: {quem}" + (f" até {ate}" if ate and ate not in LIVRE else "")


def _agora() -> dt.datetime:
    try:
        import mb_telemetria
        return mb_telemetria.agora()
    except Exception:
        return dt.datetime.now().astimezone()


def registrar(projeto: Path, linha: dict) -> Path | None:
    """Anexa 1 linha. Nunca levanta — telemetria não derruba sessão."""
    alvo = projeto / ".mb-log" / "sessao.jsonl"
    try:
        alvo.parent.mkdir(exist_ok=True)
        with alvo.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        return alvo
    except OSError:
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="abertura de sessão: central → projeto + git conservador (nunca commit/push)")
    ap.add_argument("--projeto", default=None, help="pasta do projeto (padrão: pasta atual)")
    ap.add_argument("--offline", action="store_true", help="não busca o servidor git (sem fetch/pull)")
    ap.add_argument("--seco", action="store_true", help="dry-run: não grava nada, só diz o que faria")
    args = ap.parse_args(argv)

    pedido = Path(args.projeto or os.getcwd()).expanduser()
    try:
        pedido = pedido.resolve()
    except OSError:
        pass
    if not pedido.is_dir():
        print(f"TL;DR abertura MEGABRAIN: projeto não existe — {pedido}")
        return 1
    projeto = resolver_projeto(pedido)

    central, como = achar_central(projeto)
    if central is None:
        print("TL;DR abertura MEGABRAIN: central não achada — nada sincronizado.")
        print(f"1. {como}")
        print("2. defina MEGABRAIN_CENTRAL com a pasta da central e abra de novo")
        return 1
    try:
        cv = carregar_check_version(central)
    except Exception as e:  # noqa: BLE001 — qualquer falha ao carregar é erro real
        print(f"TL;DR abertura MEGABRAIN: central em {central} sem sync utilizável — {e}")
        return 1

    e_a_central = _mesmo(projeto, central)
    sync = sincronizar(central, projeto, cv, args.seco)
    gc = estado_git(central, args.offline, args.seco)
    gp = ({"estado": "central", "resumo": "é a própria central (ver acima)", "topo": gc.get("topo")}
          if e_a_central else estado_git(projeto, args.offline, args.seco, gc.get("topo")))

    v_central = curta(cv, cv.ler_versao(central))
    if e_a_central:
        v_projeto = v_central
    elif (projeto / "MEGABRAIN").is_dir():
        v_projeto = curta(cv, cv.ler_versao_projeto(str(projeto / "MEGABRAIN")))
    else:
        v_projeto = "sem MEGABRAIN/"
    trava = ler_trava(projeto)

    avisos = []
    if sync["estado"] in ("aviso", "erro"):
        avisos.append(f"sync {sync['resumo']}")
    for rotulo, g in (("git central", gc), ("git projeto", gp)):
        if g["estado"] == "aviso":
            avisos.append(f"{rotulo}: {g['resumo']}")
    if trava.startswith("TRAVADO_POR"):
        avisos.append(f"trava {trava}")

    nome = projeto.name or str(projeto)
    if not _mesmo(projeto, pedido):
        nome += f" (aberto de {pedido})"
    if args.seco:
        inicio = f"ensaio com {len(avisos)} aviso(s) — {avisos[0]}" if avisos else "ensaio sem aviso"
        veredito = f"{inicio} · nada gravado, servidor git não consultado"
    elif avisos:
        veredito = f"pronto com {len(avisos)} aviso(s) — {avisos[0]}"
    else:
        veredito = "pronto — sync e git conferidos" + (", trava livre" if trava == "livre" else "")
    origem = "" if como == "pasta do script" else f" · central achada por {como}"

    print(f"TL;DR {'[seco] ' if args.seco else ''}abertura MEGABRAIN · {nome}: {veredito}.")
    print(f"1. versão: central {v_central} × projeto {v_projeto}{origem}")
    print(f"2. sync: {sync['resumo']}")
    print(f"3. git central: {gc['resumo']}")
    print(f"4. git projeto: {gp['resumo']}")
    print(f"5. trava (HANDOFF.md): {trava}")

    if args.seco:
        if e_projeto(projeto):
            print(f"   [seco] faria: 1 linha em {projeto / '.mb-log' / 'sessao.jsonl'}")
        return 0
    if not e_projeto(projeto):
        return 0
    linha = {
        "ts": _agora().isoformat(timespec="seconds"),
        "evento": "abertura",
        "projeto": str(projeto),
        "sync": sync["estado"],
        "git_central": gc["estado"],
        "git_projeto": gp["estado"],
        "versao": {"central": v_central, "projeto": v_projeto},
        "avisos": avisos,
        "so": platform.system() or "?",
    }
    if registrar(projeto, linha) is None:
        print("   log: não gravei .mb-log/sessao.jsonl (sem permissão ou disco cheio)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
