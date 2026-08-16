"""
test_mb_sync.py — prova que a trava de handoff realmente trava.

Roda sem pytest:   python tests/test_mb_sync.py
Roda com pytest:   pytest tests/

A trava e a unica garantia do protocolo (regra de ouro 21: garantia real e
script, nao markdown). O corolario: script sem teste e markdown com extensao
.py. Estes casos cobrem o contrato que o SKILL.md promete no Gate 0.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MB_SYNC = RAIZ / "bin" / "mb-sync.py"


def rodar(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(MB_SYNC), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


def novo_projeto() -> Path:
    return Path(tempfile.mkdtemp(prefix="mb-teste-"))


def test_projeto_sem_handoff_esta_livre():
    p = novo_projeto()
    r = rodar("--dir", str(p), "status")
    assert r.returncode == 0, f"projeto novo devia estar livre: {r.stdout}{r.stderr}"


def test_lock_grava_e_status_acusa_travado():
    p = novo_projeto()
    r = rodar("--dir", str(p), "lock", "--agente", "claude", "--escopo", "src/", "--horas", "2")
    assert r.returncode == 0, r.stderr
    assert (p / "HANDOFF.md").exists(), "lock nao criou HANDOFF.md"

    texto = (p / "HANDOFF.md").read_text(encoding="utf-8")
    assert "TRAVADO_POR: claude" in texto
    assert "<USUARIO>" not in texto, "placeholder literal vazou para o HANDOFF"

    r = rodar("--dir", str(p), "status")
    assert r.returncode == 1, "status devia sair 1 quando travado"


def test_release_alheio_e_recusado():
    p = novo_projeto()
    rodar("--dir", str(p), "lock", "--agente", "claude", "--escopo", ".", "--horas", "2")
    r = rodar("--dir", str(p), "release", "--agente", "kimi")
    assert r.returncode != 0, "kimi nao pode liberar trava do claude"
    assert "TRAVADO_POR: claude" in (p / "HANDOFF.md").read_text(encoding="utf-8")


def test_release_proprio_libera():
    p = novo_projeto()
    rodar("--dir", str(p), "lock", "--agente", "claude", "--escopo", ".", "--horas", "2")
    r = rodar("--dir", str(p), "release", "--agente", "claude")
    assert r.returncode == 0, r.stderr
    assert rodar("--dir", str(p), "status").returncode == 0, "devia estar livre apos release"


def test_force_libera_trava_alheia():
    p = novo_projeto()
    rodar("--dir", str(p), "lock", "--agente", "claude", "--escopo", ".", "--horas", "2")
    r = rodar("--dir", str(p), "release", "--agente", "kimi", "--force")
    assert r.returncode == 0, f"--force devia liberar: {r.stderr}"


def test_dir_fora_do_cwd_funciona():
    """Regressao v4.9: --dir fora do diretorio atual era recusado.

    O comando documentado roda o script pelo caminho absoluto da central,
    apontando --dir para um projeto que vive em outro lugar do disco.
    """
    p = novo_projeto()
    r = rodar("--dir", str(p), "lock", "--agente", "claude", "--escopo", ".", cwd=RAIZ)
    assert r.returncode == 0, f"--dir externo devia funcionar: {r.stderr}"


def test_dir_inexistente_falha_claro():
    r = rodar("--dir", "/caminho/que/nao/existe/mb", "status")
    assert r.returncode != 0
    assert "nao encontrada" in (r.stderr + r.stdout).lower()


def main() -> int:
    testes = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    falhas = 0
    for t in testes:
        try:
            t()
            print(f"  ok    {t.__name__}")
        except AssertionError as e:
            falhas += 1
            print(f"  FALHA {t.__name__}: {e}")
    print(f"\n{len(testes) - falhas}/{len(testes)} passaram")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
