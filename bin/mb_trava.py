#!/usr/bin/env python3
"""
mb_trava.py — trava POR ARQUIVO que os escritores de fato checam.

POR QUE EXISTE (260825, decisão 260825ad)
------------------------------------------
A trava antiga é um campo de texto (`TRAVADO_POR:` no HANDOFF.md) que **um
único script lê** (`mb-sync.py`) e que **nenhum escritor consulta**. Em 260825
ela falhou três vezes no mesmo dia, com agentes diferentes:

  09:50  um agente escreveu em META.md com a trava marcando "livre"
  11:10  duas decisões nasceram com o MESMO id 260825x, ao mesmo tempo
  11:30  a trava de um agente sumiu no meio da operação de outro

Nenhuma delas perdeu dado — as três foram append em regiões diferentes do
mesmo arquivo, e funcionaram por sorte. A quarta não vai.

O QUE ESTE MÓDULO É, E O QUE NÃO É
-----------------------------------
É um **aviso confiável**, não um mutex de sistema operacional. A central virou
git em 260825, então perda passou a ser recuperável — o que faltava não era
impedir a escrita a qualquer custo, era **saber que outra mão está no arquivo**
e **detectar quando duas passaram**. Construir o caro quando o barato resolve
foi um erro que este projeto já cometeu.

Três garantias, nesta ordem de importância:

  1. `checar()` — quem escreve pergunta antes. Barato, e é o que faltava.
  2. `escrever()` — checa, escreve atômico, e registra. Um passo em vez de três.
  3. `conferir_ids()` — recusa dois blocos `## <id>` iguais em DECISOES.md.
     Só isso já teria evitado a colisão das 11:10.

Escopo é POR ARQUIVO. Dois agentes em arquivos diferentes não se bloqueiam —
foi exatamente o que aconteceu hoje e não devia ter sido problema.

CONTRATO
--------
- Trava vive em `.mb-lock/<slug>.json` na central. Uma por arquivo alvo.
- Trava vencida = livre. Agente que morreu não trava o projeto pra sempre.
- O mesmo agente reentra na própria trava (idempotente) — script que chama
  duas vezes não se bloqueia.
- `ceder()` existe para handover explícito: quem toma registra de quem tomou
  e por quê. Roubar em silêncio é o defeito, não a tomada em si.

Uso como biblioteca:

    import mb_trava as t
    with t.travado(arq, agente="claude", motivo="grava decisão"):
        arq.write_text(novo, encoding="utf-8")

    # ou, com a checagem embutida:
    t.escrever(arq, texto, agente="claude")
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path

import mb_utils as u

PASTA = ".mb-lock"
HORAS_PADRAO = 2
FMT = "%Y-%m-%d %H:%M:%S"
# Em 24/08, b/c eram rótulos de lote e se repetem por desenho. Em 25/08 os
# blocos passaram a ser citados como endereços individuais; daí em diante a
# unicidade é contrato e colisão é erro.
ID_UNICO_DESDE = "260825"


class TravaOcupada(Exception):
    """Outro agente tem o arquivo, dentro do prazo."""

    def __init__(self, alvo: Path, dono: str, ate: str, motivo: str = ""):
        self.alvo, self.dono, self.ate, self.motivo = alvo, dono, ate, motivo
        extra = f" ({motivo})" if motivo else ""
        super().__init__(
            f"{alvo.name} está com {dono} até {ate}{extra}. "
            f"Espere, ou tome com mb_trava.ceder() dizendo por quê.")


class IdDuplicado(Exception):
    """Dois blocos com o mesmo identificador no mesmo arquivo."""


def _agora() -> dt.datetime:
    try:
        import mb_telemetria as tel
        return tel.agora()
    except Exception:
        return dt.datetime.now()


def agente_script(nome: str | None = None) -> str:
    """Identidade única para uma execução de script.

    Usar apenas ``script:mb-fila`` faria dois processos diferentes parecerem
    o mesmo dono reentrante. O PID separa as execuções e faz a segunda ser
    recusada de verdade.
    """
    base = nome or Path(sys.argv[0]).stem or "python"
    return f"script:{base}:{os.getpid()}"


def central(inicio: Path | None = None) -> Path:
    base = Path(inicio) if inicio else Path(__file__).resolve().parent.parent
    return base


def _slug(alvo: Path) -> str:
    """Nome de arquivo de trava a partir do caminho do alvo.

    Usa o caminho inteiro, não só o nome: `Portfolio/DECISOES.md` e
    `central/DECISOES.md` são arquivos diferentes e não podem compartilhar
    trava. Slug por nome sozinho foi como o resolvedor de layout errou hoje.
    """
    txt = str(alvo.resolve()).replace("\\", "/")
    limpo = re.sub(r"[^A-Za-z0-9._-]+", "-", txt).strip("-")
    if len(limpo) > 120:
        import hashlib
        limpo = limpo[-90:] + "-" + hashlib.sha256(txt.encode()).hexdigest()[:12]
    return limpo + ".json"


def caminho_trava(alvo: Path, raiz: Path | None = None) -> Path:
    return central(raiz) / PASTA / _slug(Path(alvo))


def ler(alvo: Path, raiz: Path | None = None) -> dict | None:
    """A trava atual do arquivo, ou None se livre/vencida."""
    arq = caminho_trava(alvo, raiz)
    txt = u.safe_read_text(arq)
    if not txt:
        return None
    try:
        d = json.loads(txt)
    except (json.JSONDecodeError, ValueError):
        return None
    try:
        ate = dt.datetime.strptime(d.get("ate", ""), FMT)
    except (ValueError, TypeError):
        return None
    if ate < _agora().replace(tzinfo=None):
        d["vencida"] = True
        return None          # vencida é livre — agente morto não trava pra sempre
    return d


def _criar_exclusivo(arq: Path, dados: dict) -> None:
    """Cria a trava sem janela entre "checar" e "gravar".

    ``O_EXCL`` é a peça que torna duas aquisições simultâneas decidíveis: só
    uma cria o arquivo; a outra relê o dono e falha alto.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(str(arq), flags)
    try:
        conteudo = json.dumps(dados, ensure_ascii=False, indent=2) + "\n"
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            fd = -1
            f.write(conteudo)
            f.flush()
            os.fsync(f.fileno())
    finally:
        if fd != -1:
            os.close(fd)


def checar(alvo: Path, agente: str, raiz: Path | None = None) -> None:
    """Levanta TravaOcupada se OUTRO agente tem o arquivo. É o passo que
    faltava: barato, e transforma a trava de decoração em garantia."""
    d = ler(alvo, raiz)
    if d and d.get("agente") != agente:
        raise TravaOcupada(Path(alvo), d.get("agente", "?"), d.get("ate", "?"),
                           d.get("motivo", ""))


def travar(alvo: Path, agente: str, motivo: str = "", horas: int = HORAS_PADRAO,
           raiz: Path | None = None) -> dict:
    """Toma a trava por criação exclusiva. Reentrante para o mesmo agente."""
    alvo = Path(alvo)
    arq = caminho_trava(alvo, raiz)
    arq.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(5):
        existente = ler(alvo, raiz)
        if existente:
            if existente.get("agente") != agente:
                raise TravaOcupada(alvo, existente.get("agente", "?"),
                                   existente.get("ate", "?"),
                                   existente.get("motivo", ""))
            # Reentrada explícita do mesmo dono: só a última liberação solta.
            agora = _agora().replace(tzinfo=None)
            existente["contagem"] = max(1, int(existente.get("contagem", 1))) + 1
            existente["ate"] = (agora + dt.timedelta(hours=horas)).strftime(FMT)
            if motivo:
                existente["motivo"] = motivo
            u.atomic_write_text(
                arq, json.dumps(existente, ensure_ascii=False, indent=2) + "\n")
            return existente

        # Arquivo inválido ou vencido não bloqueia. Remova e dispute a criação
        # exclusiva; se outro processo ganhar, o próximo laço verá o dono.
        try:
            arq.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            continue

        agora = _agora().replace(tzinfo=None)
        dados = {
            "arquivo": str(alvo.resolve()),
            "agente": agente,
            "motivo": motivo,
            "pid": os.getpid(),
            "contagem": 1,
            "desde": agora.strftime(FMT),
            "ate": (agora + dt.timedelta(hours=horas)).strftime(FMT),
        }
        try:
            _criar_exclusivo(arq, dados)
            return dados
        except FileExistsError:
            continue
    # A disputa só chega aqui se o arquivo mudou repetidamente durante todas
    # as tentativas. Falhar é mais seguro do que escrever sem dono conhecido.
    raise TravaOcupada(alvo, "outro processo", "desconhecido",
                       "a trava mudou durante a aquisição")


def liberar(alvo: Path, agente: str, raiz: Path | None = None) -> bool:
    """Solta a própria trava. Não solta a dos outros — para isso, ceder()."""
    d = ler(alvo, raiz)
    if d and d.get("agente") != agente:
        return False
    arq = caminho_trava(alvo, raiz)
    if d and int(d.get("contagem", 1)) > 1:
        d["contagem"] = int(d["contagem"]) - 1
        return u.atomic_write_text(
            arq, json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    try:
        arq.unlink()
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def ceder(alvo: Path, de: str, para: str, porque: str,
          raiz: Path | None = None) -> dict:
    """Handover EXPLÍCITO: tomar a trava de outro, com registro.

    260825: eu tomei a trava de um agente-irmão pra fazer este módulo, depois
    de mandar ele sair. Tomar não é o defeito — tomar em SILÊNCIO é. Aqui a
    tomada fica escrita no próprio arquivo de trava e no log.
    """
    anterior = ler(alvo, raiz) or {}
    arq = caminho_trava(alvo, raiz)
    arq.parent.mkdir(parents=True, exist_ok=True)
    agora = _agora().replace(tzinfo=None)
    d = {
        "arquivo": str(Path(alvo).resolve()),
        "agente": para,
        "motivo": porque,
        "pid": os.getpid(),
        "desde": agora.strftime(FMT),
        "ate": (agora + dt.timedelta(hours=HORAS_PADRAO)).strftime(FMT),
        "tomada_de": anterior.get("agente") or de,
        "tomada_em": agora.strftime(FMT),
    }
    u.atomic_write_text(arq, json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    try:
        import mb_telemetria as tel
        tel.registrar("trava_cedida", arquivo=Path(alvo).name,
                      de=d["tomada_de"], para=para, porque=porque)
    except Exception:
        pass
    return d


@contextmanager
def travado(alvo: Path, agente: str, motivo: str = "", horas: int = HORAS_PADRAO,
            raiz: Path | None = None):
    """`with travado(arq, "claude"): ...` — trava, executa, libera sempre."""
    travar(alvo, agente, motivo, horas, raiz)
    try:
        yield
    finally:
        liberar(alvo, agente, raiz)


# --------------------------------------------------------------------------
# escrita com checagem embutida
# --------------------------------------------------------------------------

def escrever(alvo: Path, texto: str, agente: str, motivo: str = "",
             raiz: Path | None = None) -> bool:
    """Checa, escreve atômico, libera. É o que os escritores devem chamar.

    Um passo em vez de três é o que faz a regra ser seguida — regra que exige
    disciplina em 3 chamadas vira regra que ninguém segue (foi o Gate 3, com
    4 citações na skill e ZERO execuções em 6 dias).
    """
    alvo = Path(alvo)
    with travado(alvo, agente, motivo or f"escrita por {agente}", raiz=raiz):
        return u.atomic_write_text(alvo, texto)


def anexar(alvo: Path, bloco: str, agente: str, motivo: str = "",
           raiz: Path | None = None) -> bool:
    """Append com trava — o padrão de DECISOES.md e licoes-megabrain.md.

    Lê DENTRO da trava: ler fora e escrever dentro é o lost update clássico,
    e é exatamente a forma do bug das 11:10 de 260825.
    """
    alvo = Path(alvo)
    with travado(alvo, agente, motivo or f"append por {agente}", raiz=raiz):
        atual = u.safe_read_text(alvo) or ""
        novo = atual.rstrip("\n") + "\n" + bloco.rstrip("\n") + "\n"
        return u.atomic_write_text(alvo, novo)


# --------------------------------------------------------------------------
# colisão de identificador
# --------------------------------------------------------------------------

def ids_de(texto: str) -> list[str]:
    """Os endereços `## 260825x — título` de um arquivo de decisões.

    Cabeçalhos antigos usavam só a data e se repetem legitimamente; nunca
    foram endereços citáveis. O sufixo alfabético é o que identifica o sistema
    novo e, portanto, o que precisa ser único.
    """
    achados = []
    for linha in texto.splitlines():
        m = re.match(r"^##\s+~?~?(\d{6}[a-z]{1,2})\b", linha)
        if m:
            achados.append(m.group(1))
    return achados


def conferir_ids(alvo: Path) -> list[str]:
    """Endereços repetidos desde o contrato de unicidade. Vazio = são."""
    import collections
    texto = u.safe_read_text(Path(alvo)) or ""
    cont = collections.Counter(
        i for i in ids_de(texto) if i[:6] >= ID_UNICO_DESDE)
    return sorted([i for i, n in cont.items() if n > 1])


def proximo_id(alvo: Path, data: str | None = None) -> str:
    """Próxima letra livre para a data — `260825ad` se `ac` é o último.

    Não recicla id de bloco removido: número de decisão é ENDEREÇO, não
    posição (lição 260805). Só olha o que existe e vai adiante.
    """
    data = data or _agora().strftime("%y%m%d")
    texto = u.safe_read_text(Path(alvo)) or ""
    usados = {i[6:] for i in ids_de(texto) if i.startswith(data)}
    if not usados:
        return data + "a"

    def numero(sufixo: str) -> int:
        valor = 0
        for ch in sufixo:
            valor = valor * 26 + (ord(ch) - ord("a") + 1)
        return valor

    def sufixo(valor: int) -> str:
        chars = []
        while valor > 0:
            valor, resto = divmod(valor - 1, 26)
            chars.append(chr(ord("a") + resto))
        return "".join(reversed(chars))

    # Vai depois do maior endereço já usado. Preencher um buraco reciclaria um
    # ID que pode continuar citado fora do arquivo.
    return data + sufixo(max(numero(s) for s in usados) + 1)


def anexar_decisao(alvo: Path, bloco: str, agente: str,
                   raiz: Path | None = None) -> str:
    """Append em DECISOES.md com detecção de id duplicado DENTRO da trava.

    Levanta IdDuplicado em vez de gravar. É a garantia que teria evitado a
    colisão das 11:10 de 260825, quando duas decisões nasceram como `260825x`.
    """
    alvo = Path(alvo)
    with travado(alvo, agente, "grava decisão", raiz=raiz):
        atual = u.safe_read_text(alvo) or ""
        novos = ids_de(bloco)
        duplicados_atuais = conferir_ids(alvo)
        if duplicados_atuais:
            raise IdDuplicado(
                f"o arquivo já contém id(s) duplicado(s): "
                f"{', '.join(duplicados_atuais)}. Não gravei.")
        import collections
        repetidos_no_bloco = [i for i, n in collections.Counter(novos).items()
                              if n > 1]
        if repetidos_no_bloco:
            raise IdDuplicado(
                f"o bloco novo repete id(s): {', '.join(repetidos_no_bloco)}. "
                "Não gravei.")
        existentes = set(ids_de(atual))
        colididos = [i for i in novos if i in existentes]
        if colididos:
            livre = proximo_id(alvo)
            raise IdDuplicado(
                f"id(s) {', '.join(colididos)} já existem em {alvo.name}. "
                f"Próximo livre: {livre}. Não gravei — id é endereço, "
                f"e dois blocos com o mesmo endereço quebram toda citação.")
        u.atomic_write_text(alvo, atual.rstrip("\n") + "\n" + bloco)
        return novos[0] if novos else ""


# --------------------------------------------------------------------------
# CLI — pra .cmd, hook e agente que não é python
# --------------------------------------------------------------------------

def main() -> int:
    import argparse
    u.utf8_console()
    ap = argparse.ArgumentParser(description="trava por arquivo do megabrain")
    ap.add_argument("acao", choices=["status", "travar", "liberar", "ceder",
                                     "conferir-ids", "proximo-id", "escrever",
                                     "anexar", "anexar-decisao"])
    ap.add_argument("--arquivo", default=None)
    ap.add_argument("--agente", default="?")
    ap.add_argument("--para", default=None)
    ap.add_argument("--porque", default="")
    ap.add_argument("--horas", type=int, default=HORAS_PADRAO)
    ap.add_argument("--entrada", default=None,
                    help="arquivo com o conteúdo; use - para stdin")
    ap.add_argument("--raiz", default=None,
                    help="onde guardar .mb-lock (default: central deste script)")
    a = ap.parse_args()

    raiz = Path(a.raiz).resolve() if a.raiz else central()
    if a.acao == "status":
        base = raiz / PASTA
        vivas = []
        if base.is_dir():
            for f in sorted(base.glob("*.json")):
                try:
                    d = json.loads(f.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if ler(Path(d.get("arquivo", "")), raiz):
                    vivas.append(d)
        if not vivas:
            print("nenhuma trava ativa")
            return 0
        for d in vivas:
            tomada = f"  (tomada de {d['tomada_de']})" if d.get("tomada_de") else ""
            print(f"{d['agente']:<18} até {d['ate']}  {Path(d['arquivo']).name}{tomada}")
            if d.get("motivo"):
                print(f"{'':<18} {d['motivo']}")
        return 1

    if a.acao == "conferir-ids":
        alvo = Path(a.arquivo) if a.arquivo else u.achar(raiz, "DECISOES.md")
        dup = conferir_ids(alvo)
        if dup:
            print(f"ID DUPLICADO em {alvo.name}: {', '.join(dup)}")
            return 1
        print(f"ids únicos em {alvo.name}")
        return 0

    if a.acao == "proximo-id":
        alvo = Path(a.arquivo) if a.arquivo else u.achar(raiz, "DECISOES.md")
        print(proximo_id(alvo))
        return 0

    if not a.arquivo:
        print("--arquivo é obrigatório para esta ação")
        return 2
    alvo = Path(a.arquivo)

    if a.acao in {"travar", "liberar", "ceder", "escrever", "anexar",
                  "anexar-decisao"} and a.agente == "?":
        print(f"{a.acao} exige --agente com dono identificável")
        return 2

    if a.acao in {"escrever", "anexar", "anexar-decisao"}:
        if not a.entrada:
            print(f"{a.acao} exige --entrada CAMINHO (ou - para stdin)")
            return 2
        try:
            conteudo = (sys.stdin.read() if a.entrada == "-" else
                        Path(a.entrada).read_text(encoding="utf-8"))
            if a.acao == "escrever":
                escrever(alvo, conteudo, a.agente, a.porque, raiz)
            elif a.acao == "anexar":
                anexar(alvo, conteudo, a.agente, a.porque, raiz)
            else:
                anexar_decisao(alvo, conteudo, a.agente, raiz)
        except (OSError, TravaOcupada, IdDuplicado) as e:
            print(f"RECUSADO: {e}")
            return 1
        print(f"{a.acao}: ok — {alvo.name}")
        return 0

    if a.acao == "travar":
        try:
            d = travar(alvo, a.agente, a.porque, a.horas, raiz)
        except TravaOcupada as e:
            print(f"RECUSADO: {e}")
            return 1
        print(f"travado: {d['agente']} até {d['ate']} — {alvo.name}")
        return 0

    if a.acao == "liberar":
        ok = liberar(alvo, a.agente, raiz)
        print("liberado" if ok else "RECUSADO: a trava é de outro agente; use ceder")
        return 0 if ok else 1

    if a.acao == "ceder":
        if not a.para or not a.porque:
            print("ceder exige --para e --porque (tomada sem motivo é o defeito)")
            return 2
        d = ceder(alvo, a.agente, a.para, a.porque, raiz)
        print(f"cedida: {d.get('tomada_de')} → {d['agente']} — {a.porque}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
