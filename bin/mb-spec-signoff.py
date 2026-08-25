#!/usr/bin/env python3
"""
mb-spec-signoff.py — specs vivas com sign-off obsoleto. v1.0 (260825)

Adaptação da mecânica 1 do djinnai.io: uma spec só é confiável enquanto não
mudou depois de ser assinada. O utilitário rastreia sign-offs em SPEC.md,
detecta quando a spec foi editada depois do commit assinado e marca como
obsoleto.

CONTRATO DO SIGN-OFF
- A última linha da tabela "## Sign-offs" em SPEC.md faz fé.
- Colunas: Quem, Quando, Commit, Estado.
- O commit registrado é comparado com o histórico do arquivo.
- Se houver commits em HEAD..<commit-do-signoff> tocando o arquivo, o
  sign-off fica obsoleto.

Uso:
    python bin/mb-spec-signoff.py --dir <RAIZ> listar
    python bin/mb-spec-signoff.py --dir <RAIZ> assinar <caminho/para/SPEC.md> --quem "<USUARIO>"
    python bin/mb-spec-signoff.py --dir <RAIZ> verificar [caminho/para/SPEC.md]

Sem --dir, assume a central acima de bin/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import mb_utils as u
import mb_trava as trava

u.utf8_console()

RE_TABELA = re.compile(
    r"^##\s+Sign-offs\s*\n.*?\n\|(?:[^\n]*\|)+\n\|?[-:\s|]+\|?\n((?:\|.*\|\n?)+)",
    re.M | re.S,
)
RE_LINHA = re.compile(r"^\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*$")


def _central() -> Path:
    return Path(__file__).resolve().parent.parent


def _git(raiz: Path, *args: str, timeout: int = 15) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            ["git", *args], cwd=raiz, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, check=False,
        )
        return r.returncode, r.stdout or "", r.stderr or ""
    except (OSError, subprocess.SubprocessError) as e:
        return -1, "", str(e)


def _head_short(raiz: Path) -> str | None:
    rc, out, _ = _git(raiz, "rev-parse", "--short", "HEAD")
    return out.strip() if rc == 0 else None


def _hash_atual_do_arquivo(raiz: Path, caminho: Path) -> str | None:
    """Devolve o hash curto do commit em que o arquivo foi modificado pela última vez."""
    rel = caminho.relative_to(raiz).as_posix()
    rc, out, _ = _git(raiz, "log", "-1", "--pretty=%h", "--", rel)
    return out.strip() if rc == 0 and out.strip() else None


def _commit_existe(raiz: Path, commit: str) -> bool:
    rc, _, _ = _git(raiz, "rev-parse", "--verify", commit)
    return rc == 0


def _commits_tocaram_arquivo(raiz: Path, caminho: Path, desde_hash: str) -> list[str]:
    """Lista commits que tocaram o arquivo desde o hash do sign-off (exclusivo)."""
    rel = caminho.relative_to(raiz).as_posix()
    rc, out, _ = _git(
        raiz, "log", f"{desde_hash}..HEAD", "--pretty=%h %s", "--", rel,
    )
    if rc != 0:
        return []
    return [l.strip() for l in out.splitlines() if l.strip()]


def _encontrar_specs(raiz: Path) -> list[Path]:
    """Todas as SPEC.md rastreadas pelo git dentro de raiz."""
    specs: list[Path] = []
    # primeiro: SPEC.md na raiz
    raiz_spec = raiz / "SPEC.md"
    if raiz_spec.is_file():
        specs.append(raiz_spec)
    # depois: todas as SPEC.md rastreadas
    rc, out, _ = _git(raiz, "ls-files", "**/SPEC.md", "SPEC.md")
    if rc == 0:
        for linha in out.splitlines():
            p = raiz / linha.strip()
            if p.is_file() and p not in specs:
                specs.append(p)
    return sorted(specs)


def _extrair_signoffs(texto: str) -> list[dict]:
    """Extrai todas as linhas da tabela de sign-offs."""
    m = RE_TABELA.search(texto)
    if not m:
        return []
    corpo = m.group(1)
    signoffs = []
    for linha in corpo.splitlines():
        linha = linha.strip()
        m2 = RE_LINHA.match(linha)
        if not m2:
            continue
        quem, quando, commit, estado = (m2.group(i).strip() for i in range(1, 5))
        if not quem and not quando and not commit:
            continue
        signoffs.append({
            "quem": quem,
            "quando": quando,
            "commit": commit,
            "estado": estado,
        })
    return signoffs


def _ultimo_signoff(signoffs: list[dict]) -> dict | None:
    return signoffs[-1] if signoffs else None


def _estado_signoff(raiz: Path, caminho: Path, signoff: dict | None) -> dict:
    """Verifica se o sign-off ainda cobre o arquivo atual."""
    if not signoff:
        return {"estado": "sem_signoff", "obsoleto": True, "motivo": "nenhum sign-off encontrado"}

    commit_assinado = signoff.get("commit", "").strip()
    if not commit_assinado:
        return {"estado": "sem_commit", "obsoleto": True, "motivo": "sign-off sem hash de commit"}

    hash_atual = _hash_atual_do_arquivo(raiz, caminho)
    if not hash_atual:
        return {"estado": "desconhecido", "obsoleto": True, "motivo": "arquivo não rastreado no git"}

    if not _commit_existe(raiz, commit_assinado):
        return {
            "estado": "sem_commit",
            "obsoleto": True,
            "motivo": f"commit do sign-off não existe no repo ({commit_assinado})",
        }

    if commit_assinado == hash_atual:
        return {
            "estado": "ok",
            "obsoleto": False,
            "motivo": f"sign-off ainda cobre a versão atual ({hash_atual})",
            "hash_atual": hash_atual,
        }

    commits = _commits_tocaram_arquivo(raiz, caminho, commit_assinado)
    if commits:
        return {
            "estado": "obsoleto",
            "obsoleto": True,
            "motivo": f"{len(commits)} commit(s) tocaram o arquivo desde {commit_assinado}",
            "hash_atual": hash_atual,
            "commits": commits[:5],
        }

    # commit_assinado existe mas o arquivo não mudou desde lá (possível merge)
    return {
        "estado": "ok",
        "obsoleto": False,
        "motivo": f"sign-off cobre o histórico do arquivo ({commit_assinado})",
        "hash_atual": hash_atual,
    }


def _adicionar_signoff_sem_trava(raiz: Path, caminho: Path, quem: str,
                                 notas: str | None = None) -> dict:
    texto = u.safe_read_text(caminho) or ""
    head = _head_short(raiz)
    if not head:
        raise RuntimeError("não foi possível obter o hash do commit atual")

    agora = dt.datetime.now().strftime("%y%m%d %H:%M")
    linha_signoff = f"| {quem} | {agora} | {head} | ok |"
    if notas:
        linha_signoff += f" <!-- {notas} -->"
    linha_signoff += "\n"

    novo_texto: str
    if "## Sign-offs" not in texto:
        # adiciona seção no final
        novo_texto = texto.rstrip() + "\n\n## Sign-offs\n\n"
        novo_texto += "| Quem | Quando | Commit | Estado |\n"
        novo_texto += "|------|--------|--------|--------|\n"
        novo_texto += linha_signoff
    else:
        # insere nova linha após o header da tabela
        m = RE_TABELA.search(texto)
        if not m:
            raise RuntimeError("seção Sign-offs encontrada mas tabela não pôde ser parseada")
        fim_tabela = m.end(1)
        novo_texto = texto[:fim_tabela] + linha_signoff + texto[fim_tabela:]

    u.atomic_write_text(caminho, novo_texto)
    return {"quem": quem, "quando": agora, "commit": head, "caminho": str(caminho)}


def _adicionar_signoff(raiz: Path, caminho: Path, quem: str,
                       notas: str | None = None) -> dict:
    """Read-modify-write protegido desde a leitura da spec."""
    agente_arquivo = trava.agente_script("mb-spec-signoff")
    with trava.travado(caminho, agente_arquivo, "adiciona sign-off na spec"):
        return _adicionar_signoff_sem_trava(raiz, caminho, quem, notas)


def _formatar_status(specs: Iterable[dict]) -> str:
    linhas = ["# Sign-offs de specs", ""]
    simbolo = {"ok": "✓", "obsoleto": "✗", "sem_signoff": "?", "sem_commit": "!", "desconhecido": "?"}
    for s in specs:
        sig = simbolo.get(s["estado"], "?")
        ultimo = s.get("ultimo_signoff")
        detalhe = ""
        if ultimo:
            detalhe = f" — assinado por {ultimo['quem']} em {ultimo['quando']} ({ultimo['commit']})"
        linhas.append(f"- {sig} `{s['caminho']}`  **{s['estado']}**{detalhe}")
        if s.get("motivo"):
            linhas.append(f"    → {s['motivo']}")
    return "\n".join(linhas)


def _status_specs(raiz: Path) -> list[dict]:
    specs = _encontrar_specs(raiz)
    resultado = []
    for p in specs:
        rel = p.relative_to(raiz).as_posix()
        signoffs = _extrair_signoffs(u.safe_read_text(p) or "")
        ultimo = _ultimo_signoff(signoffs)
        estado = _estado_signoff(raiz, p, ultimo)
        resultado.append({
            "caminho": rel,
            "absoluto": str(p),
            "signoffs": len(signoffs),
            "ultimo_signoff": ultimo,
            "estado": estado["estado"],
            "obsoleto": estado["obsoleto"],
            "motivo": estado["motivo"],
            "hash_atual": estado.get("hash_atual"),
            "commits": estado.get("commits"),
        })
    return resultado


def cmd_listar(raiz: Path, *, raw_json: bool = False) -> None:
    resultado = _status_specs(raiz)
    if raw_json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return
    print(_formatar_status(resultado))


def cmd_assinar(raiz: Path, caminho: str, quem: str, notas: str | None = None) -> None:
    p = Path(caminho)
    if not p.is_absolute():
        p = raiz / p
    if not p.is_file():
        raise FileNotFoundError(f"spec não encontrada: {p}")
    info = _adicionar_signoff(raiz, p, quem, notas)
    print(f"sign-off adicionado em {info['caminho']}")
    print(f"  quem: {info['quem']}, quando: {info['quando']}, commit: {info['commit']}")


def cmd_verificar(raiz: Path, caminho: str | None = None) -> None:
    if caminho:
        p = Path(caminho)
        if not p.is_absolute():
            p = raiz / p
        specs = [p]
    else:
        specs = _encontrar_specs(raiz)

    obsoletos = 0
    sem_signoff = 0
    ok = 0
    for p in specs:
        rel = p.relative_to(raiz).as_posix()
        signoffs = _extrair_signoffs(u.safe_read_text(p) or "")
        ultimo = _ultimo_signoff(signoffs)
        estado = _estado_signoff(raiz, p, ultimo)
        print(f"{rel}: {estado['estado']} — {estado['motivo']}")
        if estado["estado"] == "ok":
            ok += 1
        elif estado["estado"] == "sem_signoff":
            sem_signoff += 1
        else:
            obsoletos += 1

    total = len(specs)
    print(f"\ntotal: {total} | ok: {ok} | sem sign-off: {sem_signoff} | obsoleto: {obsoletos}")
    if obsoletos:
        sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None, help="raiz da central/projeto")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("listar", help="lista todas as specs e o estado do sign-off")
    sub.add_parser("json", help="dump do status em JSON")
    p_assinar = sub.add_parser("assinar", help="adiciona um sign-off à spec")
    p_assinar.add_argument("caminho", help="caminho para SPEC.md")
    p_assinar.add_argument("--quem", default="agente", help="quem está assinando")
    p_assinar.add_argument("--notas", default=None, help="nota opcional")
    p_verificar = sub.add_parser("verificar", help="verifica sign-offs obsoletos")
    p_verificar.add_argument("caminho", nargs="?", help="spec específica; se omitido, verifica todas")
    args = ap.parse_args()

    raiz = Path(args.dir).resolve() if args.dir else _central()

    if args.cmd == "listar":
        cmd_listar(raiz)
    elif args.cmd == "json":
        cmd_listar(raiz, raw_json=True)
    elif args.cmd == "assinar":
        cmd_assinar(raiz, args.caminho, args.quem, args.notas)
    elif args.cmd == "verificar":
        cmd_verificar(raiz, args.caminho)
    return 0


if __name__ == "__main__":
    sys.exit(main())
