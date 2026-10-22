#!/usr/bin/env python3
"""
mb-gravar-texto.py — grava texto em arquivo sem passar o conteúdo pelo shell.

POR QUE EXISTE (261016, lição "Barra invertida e fim de linha no Windows [3×]")
------------------------------------------------------------------------------
Heredoc Python pelo Bash do Claude transformou "\\00" e "\\02" de caminhos
S:\\...\\00_PARA-VOCE\\02_... em caractere nulo e "±" ao prefixar ESTADO.md e
HANDOFF.md; antes, write_text tinha virado LF em CRLF. Três vezes vira processo.

CONTRATO
--------
- O conteúdo vem SEMPRE de um arquivo (--entrada), nunca de argumento.
- Modos: anexar (fim), prefixar (topo), trocar-linha (a única linha que começa
  com --prefixo vira o conteúdo da entrada, que deve ter uma linha só).
- Fim de linha do alvo é preservado (LF ou CRLF; misto usa o dominante).
  Bytes antigos não são regravados: o alvo antigo precisa ser prefixo
  (anexar) ou sufixo (prefixar) intacto do novo, ou a gravação é recusada.
- Texto novo com caractere de controle < 32 (exceto \\t \\n \\r) é recusado.
- Bloco já presente no alvo não é gravado de novo (--permitir-duplicado muda).
- Alvo com guard em .mb-lock (arquivo compartilhado) é gravado sob mb_trava;
  --travar força a trava mesmo sem guard.
- Depois de gravar, relê os bytes e compara com o esperado.

Uso:
    python mb-gravar-texto.py anexar   --alvo ARQ --entrada BLOCO.txt
    python mb-gravar-texto.py prefixar --alvo ARQ --entrada BLOCO.txt
    python mb-gravar-texto.py trocar-linha --alvo ARQ --entrada LINHA.txt --prefixo "STATUS:"
Saída 0 = gravado ou já presente; 1 = recusado; 2 = uso errado.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mb_utils as u  # noqa: E402
import mb_trava as trava  # noqa: E402

BOM = b"\xef\xbb\xbf"
PERMITIDOS = {"\t", "\n", "\r"}


class Recusado(Exception):
    """A gravação não é segura; nada foi escrito."""


def controles(texto: str) -> list[tuple[int, int, str]]:
    """(linha, coluna, código) de cada caractere de controle proibido."""
    achados = []
    for n, linha in enumerate(texto.split("\n"), 1):
        for c, ch in enumerate(linha, 1):
            if ord(ch) < 32 and ch not in PERMITIDOS:
                achados.append((n, c, f"0x{ord(ch):02x}"))
    return achados


def ler_entrada(caminho: Path) -> str:
    try:
        bruto = Path(caminho).read_bytes()
    except OSError as e:
        raise Recusado(f"não li a entrada {caminho}: {e}") from e
    if bruto.startswith(BOM):
        bruto = bruto[len(BOM):]      # Out-File do PowerShell grava BOM
    try:
        texto = bruto.decode("utf-8")
    except UnicodeDecodeError as e:
        raise Recusado(f"entrada não é UTF-8 ({e}); salve como UTF-8") from e
    ruins = controles(texto)
    if ruins:
        lista = ", ".join(f"linha {l} col {c} ({cod})" for l, c, cod in ruins[:5])
        raise Recusado(f"texto novo tem caractere de controle: {lista}. "
                       "Caminho Windows com barra invertida passou por "
                       "interpretação de escape; refaça a entrada.")
    return texto


def fim_de_linha(bruto: bytes, alvo: Path) -> bytes:
    crlf = bruto.count(b"\r\n")
    lf = bruto.count(b"\n") - crlf
    if not crlf and not lf:
        return b"\r\n" if alvo.suffix.lower() in {".cmd", ".bat"} else b"\n"
    return b"\r\n" if crlf >= lf else b"\n"


def _norm(texto: str) -> str:
    return texto.replace("\r\n", "\n").replace("\r", "\n")


def ja_presente(antigo: str, bloco: str) -> bool:
    """Bloco (linhas inteiras e contíguas) já existe no alvo."""
    b = _norm(bloco).strip("\n")
    return bool(b) and ("\n" + b + "\n") in ("\n" + _norm(antigo) + "\n")


def montar(modo: str, bruto: bytes, texto: str, alvo: Path,
           prefixo: str | None = None) -> bytes:
    """Bytes novos do alvo. Só acrescenta ou troca uma linha; nunca regrava."""
    nl = fim_de_linha(bruto, alvo)
    bom = BOM if bruto.startswith(BOM) else b""
    corpo = bruto[len(bom):]
    bloco = _norm(texto).strip("\n")

    if modo == "trocar-linha":
        if not prefixo:
            raise Recusado("trocar-linha exige --prefixo")
        if "\n" in bloco or not bloco:
            raise Recusado("trocar-linha exige entrada com exatamente uma linha")
        linhas = corpo.splitlines(keepends=True)
        alvos = [i for i, l in enumerate(linhas)
                 if l.decode("utf-8").startswith(prefixo)]
        if len(alvos) != 1:
            raise Recusado(f"prefixo {prefixo!r} casa {len(alvos)} linhas; "
                           "precisa casar exatamente 1")
        i = alvos[0]
        velha = linhas[i]
        eol = velha[len(velha.rstrip(b"\r\n")):]
        linhas[i] = bloco.encode("utf-8") + eol
        return bom + b"".join(linhas)

    novo = bloco.replace("\n", nl.decode()).encode("utf-8")
    if modo == "anexar":
        sep = b""
        if corpo and not corpo.endswith((b"\n", b"\r")):
            sep += nl
        if corpo.strip() and bloco.startswith("#") and not (
                corpo + sep).endswith(nl + nl):
            sep += nl
        return bruto + sep + novo + nl
    if modo == "prefixar":
        sep = b""
        primeira = corpo.lstrip(b"\r\n")
        if (corpo.strip() and primeira == corpo
                and (bloco.startswith("#") or corpo.startswith(b"#"))):
            sep = nl              # linha em branco entre títulos markdown
        return bom + novo + nl + sep + corpo
    raise Recusado(f"modo desconhecido: {modo}")


def conferir(modo: str, antigo: bytes, novo: bytes) -> None:
    """Invariante: o conteúdo antigo continua intacto dentro do novo."""
    if modo == "anexar" and not novo.startswith(antigo):
        raise Recusado("o alvo antigo não é prefixo intacto do novo")
    if modo == "prefixar":
        bom = BOM if antigo.startswith(BOM) else b""
        if not (novo.startswith(bom) and novo.endswith(antigo[len(bom):])):
            raise Recusado("o alvo antigo não é sufixo intacto do novo")
    if modo == "trocar-linha":
        a, n = antigo.splitlines(keepends=True), novo.splitlines(keepends=True)
        if len(a) != len(n) or sum(x != y for x, y in zip(a, n)) > 1:
            raise Recusado("a troca mexeu em mais de uma linha")


def gravar_bytes(alvo: Path, dados: bytes) -> None:
    """Temp na mesma pasta + os.replace; preserva o atributo oculto (Windows)."""
    alvo.parent.mkdir(parents=True, exist_ok=True)
    oculto = False
    if os.name == "nt" and alvo.exists():
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(alvo))
        oculto = attrs != -1 and bool(attrs & 0x2)
        if oculto:      # os.replace sobre arquivo oculto dá PermissionError
            ctypes.windll.kernel32.SetFileAttributesW(str(alvo), attrs & ~0x2)
    fd, tmp = tempfile.mkstemp(dir=alvo.parent, prefix=f".{alvo.name}.",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dados)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, alvo)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    finally:
        if oculto:
            import ctypes
            a = ctypes.windll.kernel32.GetFileAttributesW(str(alvo))
            ctypes.windll.kernel32.SetFileAttributesW(str(alvo), a | 0x2)


def tem_guard(alvo: Path, raiz: Path | None = None) -> bool:
    arq = trava.caminho_trava(alvo, raiz)
    return arq.exists() or arq.with_suffix(arq.suffix + ".guard").exists()


def executar(modo: str, alvo: Path, entrada: Path, prefixo: str | None = None,
             agente: str | None = None, forcar_trava: bool = False,
             permitir_duplicado: bool = False,
             raiz: Path | None = None) -> str:
    alvo = Path(alvo)
    texto = ler_entrada(entrada)
    if prefixo is not None and controles(prefixo):
        raise Recusado("--prefixo tem caractere de controle")
    usar_trava = forcar_trava or tem_guard(alvo, raiz)
    dono = agente or trava.agente_script("mb-gravar-texto")
    ctx = (trava.travado(alvo, dono, f"mb-gravar-texto {modo}", raiz=raiz)
           if usar_trava else nullcontext())
    with ctx:                       # ler DENTRO da trava (lost update)
        antigo = alvo.read_bytes() if alvo.exists() else b""
        try:
            antigo_txt = antigo.decode("utf-8")
        except UnicodeDecodeError as e:
            raise Recusado(f"alvo não é UTF-8 ({e}); não mexo") from e
        if (modo in {"anexar", "prefixar"} and not permitir_duplicado
                and ja_presente(antigo_txt, texto)):
            return f"{modo}: bloco já presente em {alvo.name}; nada gravado"
        novo = montar(modo, antigo, texto, alvo, prefixo)
        conferir(modo, antigo, novo)
        gravar_bytes(alvo, novo)
        relido = alvo.read_bytes()
        if relido != novo:
            raise Recusado(f"releitura de {alvo.name} difere do esperado")
    nl = "CRLF" if fim_de_linha(novo, alvo) == b"\r\n" else "LF"
    tr = " sob trava" if usar_trava else ""
    return (f"{modo}: ok — {alvo.name} ({len(antigo)} → {len(novo)} bytes, "
            f"{nl}{tr}, conferido por bytes)")


def main(argv: list[str] | None = None) -> int:
    u.utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("modo", choices=["anexar", "prefixar", "trocar-linha"])
    ap.add_argument("--alvo", required=True)
    ap.add_argument("--entrada", required=True,
                    help="arquivo UTF-8 com o texto (nunca o texto em si)")
    ap.add_argument("--prefixo", default=None)
    ap.add_argument("--agente", default=None,
                    help="dono da trava (sessão); default: script:PID")
    ap.add_argument("--travar", action="store_true",
                    help="usar mb_trava mesmo sem guard em .mb-lock")
    ap.add_argument("--permitir-duplicado", action="store_true")
    ap.add_argument("--raiz", default=None, help="raiz do .mb-lock")
    a = ap.parse_args(argv)
    if a.entrada == "-":
        print("--entrada precisa ser um arquivo, não stdin")
        return 2
    try:
        msg = executar(a.modo, Path(a.alvo), Path(a.entrada), a.prefixo,
                       a.agente, a.travar, a.permitir_duplicado,
                       Path(a.raiz).resolve() if a.raiz else None)
    except (Recusado, trava.TravaOcupada, OSError) as e:
        print(f"RECUSADO: {e}")
        return 1
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
