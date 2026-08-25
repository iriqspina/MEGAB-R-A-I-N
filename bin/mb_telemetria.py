#!/usr/bin/env python3
"""mb_telemetria.py — dado bruto local do megabrain (v7.1, 260824).

Spec: 03_docs/260824_spec-fase2.md §4.

O QUE É: um caderninho local. Cada coisa que acontece numa sessão vira UMA
linha de texto em `.mb-log/telemetria-YYMMDD.jsonl`. Nada sai daqui: subir
só com opt-in explícito e depois de limpeza (§3).

REGRAS DA CASA
- Formato GENÉRICO: aceita qualquer campo extra sem precisar mudar o código.
- VALOR nunca é generalizado ("RTX 4070" fica "RTX 4070"). Quem generaliza é
  quem envia, não quem registra.
- Falha em silêncio: telemetria quebrada nunca pode derrubar uma sessão.
- Leitura agrega TUDO que já existe em .mb-log/: telemetria-*.jsonl (este
  módulo), neuron.jsonl (router do Neuron) e eventos-*.jsonl (hooks antigos).

CAMPOS SUGERIDOS (nenhum obrigatório além de evento/ts)
  evento     nome curto do que aconteceu: sessao, skill, gate, acao, erro
  skill      skill usada (dá o peso de frequência)
  cliente    cowork · cli · browser · terminal
  agente     claude · kimi · codex...
  modelo     modelo que respondeu (literal)
  modo       modo de inteligência da sessão (META.md)
  gates      lista de gates rodados
  projeto    id do projeto
  resultado  ok · erro · parcial
  duracao_s  float
  so         sistema operacional (preenchido sozinho)

USO
  python bin/mb_telemetria.py --evento sessao --skill megabrain --cliente cowork
  python bin/mb_telemetria.py --resumo --dias 30
  python bin/mb_telemetria.py --resumo --json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import re
from collections import Counter
from pathlib import Path

PREFIXO = "telemetria-"
LEGADOS = ("neuron.jsonl",)
CHAVES_CONTAGEM = ("evento", "skill", "cliente", "agente", "modelo", "modo",
                   "provider", "estrategia", "projeto", "resultado")

# ---------------------------------------------------------------------------
# RELÓGIO DA CENTRAL (260824). A central roda em três lugares: Windows nativo
# (São Paulo), a VM Linux da ponte (UTC) e a sessão de nuvem (UTC). Sem isto,
# entre 21h e meia-noite o log ia pro arquivo do dia SEGUINTE e o ts saía com
# 3 horas de erro — foi o que aconteceu com telemetria-260825.jsonl, criado às
# 22h38 de 260824. Data de evento é SEMPRE o relógio do PC dele.
# ---------------------------------------------------------------------------
FUSO_CENTRAL = "America/Sao_Paulo"


def _fuso() -> dt.tzinfo:
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(FUSO_CENTRAL)
    except Exception:
        # sem base de fusos (Windows sem tzdata): SP não tem horário de verão
        # desde 2019, então -03:00 fixo é fiel.
        return dt.timezone(dt.timedelta(hours=-3), "-03")


def agora() -> dt.datetime:
    """Agora no relógio da central, rode onde rodar."""
    return dt.datetime.now(dt.timezone.utc).astimezone(_fuso())


def hoje() -> dt.date:
    return agora().date()


# ---------------------------------------------------------------------------
# raiz: sobe do arquivo até achar a central. Vale pra qualquer layout — é o
# que faz este módulo sobreviver à mudança da máquina pra motor\ (etapa 2).
# ---------------------------------------------------------------------------
def raiz_central(inicio: Path | None = None) -> Path:
    p = (Path(inicio) if inicio else Path(__file__)).resolve()
    for cand in [p, *p.parents]:
        if not cand.is_dir():
            continue
        if (cand / "bin" / "mb_utils.py").is_file() or (cand / "memoria").is_dir():
            return cand
    return Path(__file__).resolve().parent.parent


def pasta_log(raiz: Path | None = None) -> Path:
    return (raiz or raiz_central()) / ".mb-log"


def arquivo_do_dia(raiz: Path | None = None, dia: dt.date | None = None) -> Path:
    dia = dia or hoje()
    return pasta_log(raiz) / f"{PREFIXO}{dia:%y%m%d}.jsonl"


# ---------------------------------------------------------------------------
# escrita
# ---------------------------------------------------------------------------
def registrar(evento: str, raiz: Path | None = None, **campos) -> bool:
    """Anexa 1 linha. Nunca levanta exceção — telemetria não derruba sessão."""
    try:
        linha = {"ts": agora().isoformat(timespec="seconds"),
                 "evento": str(evento), "so": platform.system() or "?"}
        for k, v in campos.items():
            if v is not None:
                linha[k] = v
        alvo = arquivo_do_dia(raiz)
        alvo.parent.mkdir(exist_ok=True)
        with alvo.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# leitura
# ---------------------------------------------------------------------------
def _linhas(arq: Path) -> list[dict]:
    out = []
    try:
        texto = arq.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            d = json.loads(linha)
        except ValueError:
            continue
        if isinstance(d, dict):
            d["_fonte"] = arq.name
            out.append(d)
    return out


def _data_do_evento(d: dict) -> dt.date | None:
    """Dia do evento NO RELÓGIO DA CENTRAL. Linha gravada em UTC (script que
    rodou pela ponte) é convertida na leitura — o log velho fica intacto e a
    contagem por dia para de mentir. Ts sem fuso já é local: não converte."""
    ts = str(d.get("ts") or "").strip()
    if not ts:
        return None
    try:
        q = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", ts)
        if not m:
            return None
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    if q.tzinfo is not None:
        q = q.astimezone(_fuso())
    return q.date()


def ler(raiz: Path | None = None, dias: int = 30, incluir_legado: bool = True) -> list[dict]:
    """Todos os eventos dos últimos `dias` (0 = tudo), do mais antigo ao mais novo."""
    base = pasta_log(raiz)
    if not base.is_dir():
        return []
    arquivos = sorted(base.glob(f"{PREFIXO}*.jsonl"))
    if incluir_legado:
        arquivos += [base / n for n in LEGADOS if (base / n).is_file()]
        arquivos += sorted(base.glob("eventos-*.jsonl"))
    corte = (hoje() - dt.timedelta(days=dias)) if dias else None
    eventos = []
    for arq in arquivos:
        for d in _linhas(arq):
            data = _data_do_evento(d)
            if corte and data and data < corte:
                continue
            eventos.append(d)
    eventos.sort(key=lambda d: str(d.get("ts") or ""))
    return eventos


def agregar(eventos: list[dict]) -> dict:
    """Contagens por chave + pesos de frequência de skill + custo/duração."""
    por = {k: Counter() for k in CHAVES_CONTAGEM}
    dias = Counter()
    duracoes, custos = [], []
    tokens_in = tokens_out = 0
    for d in eventos:
        for k in CHAVES_CONTAGEM:
            v = d.get(k)
            if isinstance(v, (str, int)) and str(v).strip():
                por[k][str(v)] += 1
        data = _data_do_evento(d)
        if data:
            dias[data.isoformat()] += 1
        if isinstance(d.get("duracao_s"), (int, float)):
            duracoes.append(float(d["duracao_s"]))
        if isinstance(d.get("custo_usd"), (int, float)):
            custos.append(float(d["custo_usd"]))
        if isinstance(d.get("tokens_in"), int):
            tokens_in += d["tokens_in"]
        if isinstance(d.get("tokens_out"), int):
            tokens_out += d["tokens_out"]

    total_skill = sum(por["skill"].values())
    pesos = {k: round(v / total_skill, 4) for k, v in por["skill"].items()} if total_skill else {}
    return {
        "eventos": len(eventos),
        "primeiro": (eventos[0].get("ts") if eventos else None),
        "ultimo": (eventos[-1].get("ts") if eventos else None),
        "dias": dict(sorted(dias.items())),
        "por": {k: dict(v.most_common()) for k, v in por.items()},
        "pesos_skills": dict(sorted(pesos.items(), key=lambda x: -x[1])),
        "duracao_media_s": round(sum(duracoes) / len(duracoes), 2) if duracoes else None,
        "custo_total_usd": round(sum(custos), 4) if custos else 0.0,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }


def resumo(raiz: Path | None = None, dias: int = 30) -> dict:
    return agregar(ler(raiz, dias))


# ---------------------------------------------------------------------------
# conserto retroativo do fuso
# ---------------------------------------------------------------------------
def corrigir_fuso(raiz: Path | None = None, aplicar: bool = False) -> dict:
    """Devolve cada linha de telemetria-*.jsonl pro arquivo do dia CERTO e
    reescreve o ts no relógio da central, guardando o original em `ts_original`.

    Mexe SÓ nos arquivos deste módulo. eventos-*.jsonl e neuron.jsonl são de
    hooks de terceiros e ficam intactos. Sem --aplicar, só relata.
    """
    base = pasta_log(raiz)
    rel = {"arquivos": 0, "linhas": 0, "reescritas": 0, "movidas": 0,
           "destinos": {}, "backup": None, "aplicado": False}
    if not base.is_dir():
        return rel
    arquivos = sorted(base.glob(f"{PREFIXO}*.jsonl"))
    if not arquivos:
        return rel

    fuso = _fuso()
    por_dia: dict[dt.date, list[str]] = {}
    for arq in arquivos:
        rel["arquivos"] += 1
        for d in _linhas(arq):
            d.pop("_fonte", None)
            rel["linhas"] += 1
            ts = str(d.get("ts") or "").strip()
            data = _data_do_evento(d)
            try:
                q = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                q = None
            if q is not None and q.tzinfo is not None:
                local = q.astimezone(fuso)
                novo_ts = local.isoformat(timespec="seconds")
                if novo_ts != ts:
                    d["ts"] = novo_ts
                    d.setdefault("ts_original", ts)
                    rel["reescritas"] += 1
                data = local.date()
            if data is None:
                data = hoje()
            destino = f"{PREFIXO}{data:%y%m%d}.jsonl"
            if destino != arq.name:
                rel["movidas"] += 1
            por_dia.setdefault(data, []).append(json.dumps(d, ensure_ascii=False))

    rel["destinos"] = {f"{d:%y%m%d}": len(v) for d, v in sorted(por_dia.items())}
    if not aplicar:
        return rel

    import shutil
    saco = base / f"_backup-fuso-{agora():%y%m%d-%H%M}"
    saco.mkdir(exist_ok=True)
    for arq in arquivos:
        shutil.copy2(arq, saco / arq.name)
    rel["backup"] = saco.name

    nomes_destino = {f"{PREFIXO}{d:%y%m%d}.jsonl" for d in por_dia}
    for d, linhas in por_dia.items():
        (base / f"{PREFIXO}{d:%y%m%d}.jsonl").write_text(
            "\n".join(linhas) + "\n", encoding="utf-8")
    for arq in arquivos:
        if arq.name not in nomes_destino:
            # o dia inteiro migrou: guarda o vazio no saco em vez de apagar
            arq.replace(saco / (arq.name + ".migrado"))
    rel["aplicado"] = True
    return rel


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _texto_resumo(r: dict, dias: int) -> str:
    if not r["eventos"]:
        return (f"telemetria: nenhum evento nos últimos {dias} dias.\n"
                "Registre um com: python bin/mb_telemetria.py --evento sessao --skill megabrain")
    linhas = [f"telemetria · {r['eventos']} eventos · {len(r['dias'])} dia(s) com registro",
              f"  primeiro: {r['primeiro']}   último: {r['ultimo']}"]
    for chave, rotulo in (("skill", "skills"), ("cliente", "clientes"), ("agente", "agentes"),
                          ("modelo", "modelos"), ("evento", "tipos de evento")):
        itens = list(r["por"].get(chave, {}).items())[:6]
        if itens:
            linhas.append(f"  {rotulo}: " + " · ".join(f"{k} ({v})" for k, v in itens))
    if r["duracao_media_s"] is not None:
        linhas.append(f"  duração média: {r['duracao_media_s']}s")
    if r["custo_total_usd"]:
        linhas.append(f"  custo somado: US$ {r['custo_total_usd']}")
    return "\n".join(linhas)


def main() -> int:
    ap = argparse.ArgumentParser(description="telemetria local do megabrain (nada sobe sem opt-in)")
    ap.add_argument("--evento", help="registra um evento com este nome")
    ap.add_argument("--campo", action="append", default=[], metavar="chave=valor",
                    help="qualquer campo extra (pode repetir)")
    for c in ("skill", "cliente", "agente", "modelo", "modo", "projeto", "resultado"):
        ap.add_argument(f"--{c}")
    ap.add_argument("--duracao-s", type=float)
    ap.add_argument("--corrigir-fuso", action="store_true", dest="corrigir",
                    help="devolve linha gravada em outro fuso pro dia certo (relata; use --aplicar)")
    ap.add_argument("--aplicar", action="store_true", help="com --corrigir-fuso: grava mesmo")
    ap.add_argument("--resumo", action="store_true")
    ap.add_argument("--dias", type=int, default=30)
    ap.add_argument("--json", action="store_true", dest="como_json")
    ap.add_argument("--dir", default=None, help="raiz da central (padrão: deduzida)")
    args = ap.parse_args()

    raiz = Path(args.dir).resolve() if args.dir else raiz_central()

    if args.evento:
        campos = {c: getattr(args, c) for c in
                  ("skill", "cliente", "agente", "modelo", "modo", "projeto", "resultado")}
        if args.duracao_s is not None:
            campos["duracao_s"] = args.duracao_s
        for par in args.campo:
            if "=" in par:
                k, v = par.split("=", 1)
                campos[k.strip()] = v.strip()
        ok = registrar(args.evento, raiz=raiz, **campos)
        print("registrado" if ok else "falhou (silencioso por design)")
        if not args.resumo:
            return 0 if ok else 1

    if args.corrigir:
        r = corrigir_fuso(raiz, aplicar=args.aplicar)
        if args.como_json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        else:
            print(f"fuso · {r['linhas']} linha(s) em {r['arquivos']} arquivo(s) de telemetria")
            print(f"  ts fora do relógio da central: {r['reescritas']}")
            print(f"  linhas no arquivo do dia errado: {r['movidas']}")
            print("  por dia (corrigido): " + (", ".join(f"{k} ({v})" for k, v in r["destinos"].items()) or "—"))
            print(f"  {'APLICADO · backup em .mb-log/' + str(r['backup']) if r['aplicado'] else 'nada gravado (rode com --aplicar)'}")
        return 0

    if args.resumo or not args.evento:
        r = resumo(raiz, args.dias)
        print(json.dumps(r, ensure_ascii=False, indent=1) if args.como_json
              else _texto_resumo(r, args.dias))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
