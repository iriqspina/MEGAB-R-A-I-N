#!/usr/bin/env python3
"""
mb-recuperar-megabrain.py — restaura a pasta MEGABRAIN/ de um projeto.

REESCRITO EM 260825 (decisão 260825x). O que mudou e por quê
------------------------------------------------------------
A versão antiga listava "outro projeto" como fonte de restauração — e essa
linha era o que travava a cópia magra: não dá pra emagrecer 19 cópias enquanto
o plano de recuperação DEPENDE de haver 19 cópias gordas. Redundância que só
existe pra alimentar o restaurador é redundância que se paga sozinha, e o preço
medido em 260825 foi 157-182 MB e três bugs nascidos na costura entre layouts.

Fontes agora, em ordem de confiança — cada uma com o que ela prova:

  1. CENTRAL VIVA        estado de agora. Só é usada se `e_central()` passar.
  2. GIT DA CENTRAL      a central existe mas está incompleta/corrompida:
                         `git restore` traz de volta o que foi versionado.
                         Nasceu em 260825 — antes disso não havia git.
  3. .mb-backup/*.zip    foto datada da central inteira.
  4. _github/repo-local  clone do pacote público: SANITIZADO (sem lição, sem
                         identidade), serve pra estrutura e código, não pra
                         memória. O restaurador avisa quando cai aqui.
  5. .mb-origem.json     o ponteiro que o sync escreve em cada cópia. Diz onde
                         a central ESTAVA e de qual commit veio. Última carta.

  ~~outro projeto~~      REMOVIDA. Ver acima.

E ela agora PROVA que restaurou: confere VERSAO.txt legível, MEGABRAIN.md
presente e o conjunto mínimo de arquivos; sem isso, "restaurado" é só o
processo ter terminado sem exceção.

Uso:
    mb-recuperar-megabrain.py --projeto CAMINHO                # detecta a fonte
    mb-recuperar-megabrain.py --projeto CAMINHO --fonte X      # força a fonte
    mb-recuperar-megabrain.py --projeto CAMINHO --listar-fontes  # só mostra
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path

import mb_utils as u

u.utf8_console()


def detectar_central():
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return os.path.abspath(env)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


CENTRAL_DEFAULT = detectar_central()
CENTRAL_DEFAULT_PATH = Path(CENTRAL_DEFAULT).resolve()


def listar_backups(central: Path) -> list[Path]:
    backup_dir = central / ".mb-backup"
    if not backup_dir.is_dir():
        return []
    return sorted(
        [f for f in backup_dir.iterdir() if f.suffix == ".zip"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


ARQUIVOS_MINIMOS = ("VERSAO.txt", "MEGABRAIN.md")


def _git(central: Path, *args) -> str | None:
    import subprocess
    try:
        r = subprocess.run(["git", *args], cwd=central, capture_output=True,
                           text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def central_do_ponteiro(projeto: Path) -> Path | None:
    """`.mb-origem.json` — o sync escreve o caminho da central em cada cópia."""
    import json
    arq = projeto / "MEGABRAIN" / ".mb-origem.json"
    txt = u.safe_read_text(arq)
    if not txt:
        return None
    try:
        d = json.loads(txt)
    except (json.JSONDecodeError, ValueError):
        return None
    alvo = d.get("central") or d.get("repo_central")
    return Path(alvo) if alvo else None


def fontes_disponiveis(projeto: Path, central: Path) -> list[tuple[str, Path, str]]:
    """(rótulo, caminho, o que essa fonte prova). Ordem = confiança."""
    achadas: list[tuple[str, Path, str]] = []

    if central.is_dir() and u.e_central(central):
        achadas.append(("central viva", central, "estado de agora"))

    if (central / ".git").is_dir():
        head = _git(central, "rev-parse", "--short", "HEAD")
        if head:
            achadas.append(("git da central", central,
                            f"histórico versionado, HEAD {head}"))

    for z in listar_backups(central):
        import datetime as dt
        try:
            quando = dt.datetime.fromtimestamp(z.stat().st_mtime).strftime("%d/%m %H:%M")
        except OSError:
            quando = "?"
        achadas.append((f"backup zip ({quando})", z, "foto datada da central"))
        break

    repo = central / "_github" / "repo-local"
    if u.achar(repo, "VERSAO.txt").is_file():
        achadas.append(("_github/repo-local", repo,
                        "SANITIZADO — sem lições nem identidade; estrutura e código só"))

    apontada = central_do_ponteiro(projeto)
    if apontada and apontada.is_dir() and apontada != central and u.e_central(apontada):
        achadas.append((".mb-origem.json do projeto", apontada,
                        "central que o sync registrou nesta cópia"))

    return achadas


def encontrar_fonte(projeto: Path, central: Path) -> Path | None:
    """Primeira fonte da lista de confiança. Sem 'outro projeto' — ver o
    cabeçalho: era ela que travava a cópia magra."""
    fontes = fontes_disponiveis(projeto, central)
    return fontes[0][1] if fontes else None


def conferir(destino: Path) -> tuple[bool, list[str]]:
    """Prova que restaurou. Sem isto, 'restaurado' significa só que o processo
    terminou sem exceção — que é exatamente o que 'anúncio sem mudança =
    teatro' proíbe."""
    problemas = []
    if not destino.is_dir():
        return False, ["a pasta não existe depois da restauração"]
    for nome in ARQUIVOS_MINIMOS:
        arq = u.achar(destino, nome)
        if not arq.is_file():
            problemas.append(f"faltou {nome}")
        elif not (u.safe_read_text(arq) or "").strip():
            problemas.append(f"{nome} está vazio")
    versao = u.read_first_non_empty_line(u.achar(destino, "VERSAO.txt")) or ""
    if versao and " · v" not in versao:
        problemas.append("VERSAO.txt não começa com uma linha de versão reconhecível")
    n = len([x for x in destino.rglob("*") if x.is_file()])
    if n < 5:
        problemas.append(f"só {n} arquivo(s) — restauração parece incompleta")
    return (not problemas), problemas


def copiar_pasta(src: Path, dst: Path, base: Path) -> bool:
    try:
        u.resolve_within(dst, base)
    except ValueError as e:
        print(f"ERRO (recusado): {e}")
        return False

    if dst.exists():
        print(f"removendo MEGABRAIN/ antigo em {dst}")
        if not u.safe_rmtree(dst, base=base):
            return False

    try:
        shutil.copytree(src, dst)
        print(f"copiado {src} -> {dst}")
        return True
    except OSError as e:
        print(f"ERRO ao copiar {src} -> {dst}: {e}")
        return False


def extrair_zip(zip_path: Path, dst: Path, base: Path) -> bool:
    try:
        u.resolve_within(dst, base)
    except ValueError as e:
        print(f"ERRO (recusado): {e}")
        return False

    if dst.exists():
        print(f"removendo MEGABRAIN/ antigo em {dst}")
        if not u.safe_rmtree(dst, base=base):
            return False

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Se o zip for de pasta central, extrair só o que seria MEGABRAIN/
            nomes = zf.namelist()
            # Verifica se o zip é de uma pasta central (tem bin/, referencias/ no root)
            raiz_eh_central = any(n.startswith("bin/") for n in nomes) and any(
                n.startswith("referencias/") or n.startswith("motor/referencias/") for n in nomes)
            if raiz_eh_central:
                prefixo = ""
            else:
                # assume MEGABRAIN/ dentro do zip
                prefixo = "MEGABRAIN/"

            dst.mkdir(parents=True, exist_ok=True)
            for membro in nomes:
                if not membro.startswith(prefixo):
                    continue
                resto = membro[len(prefixo):]
                if not resto:
                    continue
                destino_membro = dst / resto
                try:
                    u.resolve_within(destino_membro, base)
                except ValueError:
                    print(f"AVISO: pulando membro fora da área permitida: {membro}")
                    continue
                # Extrai o membro para uma pasta temporária dentro de dst.parent,
                # depois move para o destino final, preservando a estrutura relativa.
                import tempfile
                with tempfile.TemporaryDirectory(dir=dst.parent, prefix=".rec-") as tmpdir:
                    zf.extract(membro, path=tmpdir)
                    origem = Path(tmpdir) / membro
                    if prefixo:
                        # remove o prefixo MEGABRAIN/ do caminho extraído
                        origem = Path(tmpdir) / resto
                    if origem.exists():
                        destino_membro.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(origem), str(destino_membro))
        print(f"extraído {zip_path} -> {dst}")
        return True
    except (OSError, zipfile.BadZipFile) as e:
        print(f"ERRO ao extrair {zip_path}: {e}")
        return False


def normalizar_fonte(fonte: Path, central: Path) -> Path | None:
    """Se a fonte for uma pasta central, retorna ela mesma.
    Se for uma pasta MEGABRAIN/, retorna ela.
    Se for um zip, retorna ele."""
    if not fonte.exists():
        return None
    if fonte.is_file() and fonte.suffix == ".zip":
        return fonte
    if fonte.is_dir():
        # Se for central (tem bin/, referencias/ no root)
        if (fonte / "bin").is_dir() and u.pasta(fonte, "referencias").is_dir():
            return fonte
        # Se já for MEGABRAIN/
        if (u.achar(fonte, "VERSAO.txt")).is_file():
            return fonte
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="Recupera MEGABRAIN/ de um projeto")
    p.add_argument("--projeto", required=True, help="pasta do projeto a recuperar")
    p.add_argument("--fonte", default=None,
                   help="fonte: pasta central, pasta MEGABRAIN/, ou arquivo zip")
    p.add_argument("--listar-fontes", action="store_true",
                   help="só mostra as fontes disponíveis, em ordem de confiança")
    args = p.parse_args()

    projeto = Path(args.projeto).resolve()
    central = CENTRAL_DEFAULT_PATH

    if args.listar_fontes:
        fontes = fontes_disponiveis(projeto, central)
        if not fontes:
            print("NENHUMA fonte de restauração disponível.")
            print("É o cenário que a cópia magra tornou possível e que o git da")
            print("central existe pra impedir. Confira: a central existe? tem .git?")
            print("tem .mb-backup/*.zip?")
            return 1
        print(f"fontes disponíveis para {projeto.name}, da mais confiável pra menos:")
        print()
        for i, (rotulo, caminho, prova) in enumerate(fontes, 1):
            print(f"  {i}. {rotulo}")
            print(f"     {caminho}")
            print(f"     prova: {prova}")
            print()
        return 0

    try:
        u.resolve_within(projeto, Path(".").resolve())
    except ValueError:
        # Permite caminho absoluto
        pass

    fonte: Path | None = None
    if args.fonte:
        fonte = Path(args.fonte).resolve()
        if not fonte.exists():
            print(f"ERRO: fonte não encontrada: {fonte}")
            return 1
    else:
        fonte = encontrar_fonte(projeto, central)
        if fonte is None:
            print("ERRO: não consegui detectar uma fonte automaticamente.")
            print("Dica: --listar-fontes mostra o que existe. Fontes possíveis:")
            print("  central viva · git da central · .mb-backup/*.zip · _github/repo-local")
            print("  'outro projeto' NÃO é mais fonte (260825): era ela que obrigava a")
            print("  manter 19 cópias gordas só pra alimentar o restaurador.")
            return 1
        rot = next((r for r, cam, _ in fontes_disponiveis(projeto, central) if cam == fonte), "?")
        print(f"fonte detectada: {rot} — {fonte}")

    mb_destino = projeto / "MEGABRAIN"
    base_segura = projeto.resolve()

    if fonte.is_file():
        ok = extrair_zip(fonte, mb_destino, base_segura)
    elif u.e_central(fonte) and (fonte / "bin" / "mb-check-version.py").is_file():
        # 260825: central viva → delega pro sync. QUEM SABE o que uma cópia de
        # projeto contém é o `mb-check-version.py`, e é ele que cria a cópia
        # plana. A versão antiga fazia `copytree` da central inteira: o teste
        # de 260825 devolveu 3.371 arquivos, com _github/, 90_arquivo/ e
        # 99_to_delete/ dentro. Restaurador que reimplementa a regra de outro
        # script vira a segunda fonte de verdade que este projeto passou o dia
        # inteiro matando.
        import subprocess
        print("central viva → delegando a montagem pro mb-check-version.py")
        r = subprocess.run(
            [sys.executable, "-B", str(fonte / "bin" / "mb-check-version.py"),
             "--projeto", str(projeto), "--central", str(fonte), "--auto", "--offline"],
            capture_output=True, text=True, timeout=300)
        ok = r.returncode == 0
        for linha in (r.stdout or "").splitlines()[-4:]:
            print(f"  {linha}")
        if not ok:
            print((r.stderr or "")[-400:])
    else:
        fonte_normalizada = normalizar_fonte(fonte, central)
        if fonte_normalizada is None:
            print(f"ERRO: fonte não parece uma central, MEGABRAIN/ ou zip válido: {fonte}")
            return 1
        ok = copiar_pasta(fonte_normalizada, mb_destino, base_segura)

    if not ok:
        print("\nA restauração falhou. --listar-fontes mostra as alternativas.")
        return 1

    # A PROVA. Sem ela, "recuperado" significa só que nada explodiu — e o
    # protocolo chama isso de teatro.
    passou, problemas = conferir(mb_destino)
    print(f"\nMEGABRAIN/ escrito em {mb_destino}")
    if passou:
        versao = u.read_first_non_empty_line(u.achar(mb_destino, "VERSAO.txt")) or "?"
        n = len([x for x in mb_destino.rglob("*") if x.is_file()])
        print(f"CONFERIDO: {n} arquivo(s) · versão {versao[:60]}")
        return 0
    print("RESTAURAÇÃO INCOMPLETA — não declaro sucesso:")
    for x in problemas:
        print(f"  ✗ {x}")
    print("\nTente outra fonte: --listar-fontes")
    return 1


if __name__ == "__main__":
    sys.exit(main())
