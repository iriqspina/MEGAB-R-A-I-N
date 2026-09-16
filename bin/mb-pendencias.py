#!/usr/bin/env python
"""mb-pendencias — CLI do registro de pendências MEGABRAIN (260916).

Fonte da verdade: <CENTRAL>/dados/pendencias.json (escrito SÓ por aqui).
O widget Pendências apenas lê. Uso por qualquer IA em qualquer projeto.

Exemplos:
  python bin/mb-pendencias.py scan
  python bin/mb-pendencias.py listar
  python bin/mb-pendencias.py add Marketeiro "mandar proposta pra Hanada" --detalhe "lote 1"
  python bin/mb-pendencias.py feito Marketeiro "mandar proposta"
  python bin/mb-pendencias.py pausar Pets
  python bin/mb-pendencias.py retomar Pets
  python bin/mb-pendencias.py raiz "S:\\outra pasta de projetos"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "pendencias-widget"))

from pendencias_core import paths, registro as reg  # noqa: E402
from pendencias_core import scanner  # noqa: E402

try:  # Windows: saída UTF-8 mesmo com console em outra codepage
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def _idade(iso: str | None) -> str:
    if not iso:
        return "?"
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return "?"
    dias = max(0, (datetime.now(dt.tzinfo or timezone.utc) - dt).days)
    return "hoje" if dias == 0 else (f"{dias}d" if dias < 30 else f"{dias // 30}m")


_COMANDOS_ESCRITA = {"scan", "add", "feito", "rm", "pausar", "retomar", "ocultar-auto", "mostrar-auto", "raiz"}


def _abrir(args: argparse.Namespace) -> reg.Registro:
    return reg.Registro(Path(args.registro or paths.REGISTRY_PATH)).carregar()


def cmd_scan(args):
    r = _abrir(args)
    raiz = Path(args.raiz) if args.raiz else (Path(r.dados.get("raiz") or "") if r.dados.get("raiz") else None)
    if raiz is None:
        print("ERRO: informe --raiz (ou grave antes com: mb-pendencias.py raiz <caminho>).", file=sys.stderr)
        return 1
    raiz = raiz.expanduser().resolve()
    if not raiz.is_dir():
        print(f"ERRO: raiz nao existe: {raiz}", file=sys.stderr)
        return 1
    stats = scanner.scan(r, raiz)
    r.salvar()
    print(
        f"scan ok: {stats['projetos']} projetos ({stats['novos']} novos), "
        f"{stats['com_resumo']} com resumo, {stats['com_passo']} com proximo passo, "
        f"{stats['pausado_sugerido']} com sugestao de pausa. -> {paths.REGISTRY_PATH if not args.registro else args.registro}"
    )
    return 0


def cmd_listar(args):
    r = _abrir(args)
    if args.json:
        print(json.dumps({"raiz": r.dados.get("raiz"), "grupos": r.resumo(args.todos)}, ensure_ascii=False, indent=2))
        return 0
    itens, projetos = r.contagem_ativa()
    pausados = [p["nome"] for p in r.dados["projetos"] if not p.get("ativo", True)]
    print(f"Pendencias · {itens} em {projetos} projeto(s) · raiz: {r.dados.get('raiz') or '(nao definida)'}")
    grupos = r.resumo(args.todos)
    if not grupos and not pausados:
        print("(registro vazio — rode: python bin/mb-pendencias.py scan --raiz \"S:\\projetos multi i.a\")")
    for g in grupos:
        marca = "" if g["ativo"] else " [PAUSADO]"
        su = " · sugere pausar" if g["pausado_sugerido"] and g["ativo"] else ""
        linha = f"— {g['nome']} ({len(g['itens'])}{'+auto' if g['proximo_passo'] else ''}){marca}{su}"
        print(linha)
        if g["proximo_passo"]:
            print(f"    [auto|{_idade(g['estado_mtime'])}] {g['proximo_passo']}")
        for i in g["itens"]:
            print(f"    [{_idade(i.get('criada_em'))}] {i['titulo']}" + (f" — {i['detalhe']}" if i.get("detalhe") else ""))
        if g["ativo"] and not g["itens"] and not g["proximo_passo"] and g.get("resumo"):
            print(f"    (resumo) {g['resumo']}")
    if pausados and args.todos:
        print(f"Pausados: {', '.join(pausados)}")
    elif pausados:
        print(f"Pausados ({len(pausados)}): {', '.join(pausados)} · use --todos pra ver")
    return 0


def cmd_add(args):
    r = _abrir(args)
    item = r.add(args.projeto, args.titulo, args.detalhe)
    r.salvar()
    print(f"adicionada em {r.projeto(args.projeto)['nome']}: [{item['id']}] {item['titulo']}")
    return 0


def _cmd_fecha(estado_label):
    def cmd(args):
        r = _abrir(args)
        item = r.feito(args.projeto, args.ref) if estado_label == "feita" else r.rm(args.projeto, args.ref)
        r.salvar()
        print(f"{estado_label}: {item['titulo']} ({item['id']})")
        return 0

    return cmd


def cmd_pausar(args):
    r = _abrir(args)
    p = r.pausar(args.projeto)
    r.salvar()
    print(f"pausado: {p['nome']} (itens preservados; some do widget)")
    return 0


def cmd_retomar(args):
    r = _abrir(args)
    p = r.retomar(args.projeto)
    r.salvar()
    print(f"retomado: {p['nome']}")
    return 0


def cmd_auto(ocultar: bool):
    def cmd(args):
        r = _abrir(args)
        p = r.ocultar_auto(args.projeto) if ocultar else r.mostrar_auto(args.projeto)
        r.salvar()
        acao = "ocultada ate o ESTADO.md mudar" if ocultar else "reexibida"
        print(f"linha automatica de {p['nome']}: {acao}")
        return 0

    return cmd


def cmd_raiz(args):
    r = _abrir(args)
    raiz = Path(args.caminho).expanduser().resolve()
    if not raiz.is_dir():
        print(f"ERRO: pasta nao existe: {raiz}", file=sys.stderr)
        return 1
    r.dados["raiz"] = str(raiz)
    r.salvar()
    print(f"raiz gravada: {raiz} (rode 'scan' pra varrer)")
    return 0


def cmd_validar(args):
    r = _abrir(args)
    try:
        reg._validar(r.dados)
    except reg.ErroRegistro as e:
        print(f"INVALIDO: {e}", file=sys.stderr)
        return 1
    print(f"valido: {len(r.dados['projetos'])} projetos · raiz: {r.dados.get('raiz')}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mb-pendencias", description="Registro de pendencias MEGABRAIN")
    ap.add_argument("--registro", help="caminho alternativo do pendencias.json (teste/outro usuario)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="varre a raiz e atualiza o registro (preserva manual)")
    s.add_argument("--raiz", help="pasta com os projetos (default: raiz gravada)")
    s.set_defaults(fn=cmd_scan)

    s = sub.add_parser("listar", help="lista pendencias por projeto")
    s.add_argument("--json", action="store_true", help="saida JSON para outras IAs")
    s.add_argument("--todos", action="store_true", help="inclui projetos pausados")
    s.set_defaults(fn=cmd_listar)

    s = sub.add_parser("add", help="adiciona pendencia manual")
    s.add_argument("projeto")
    s.add_argument("titulo")
    s.add_argument("--detalhe")
    s.set_defaults(fn=cmd_add)

    s = sub.add_parser("feito", help="marca pendencia como feita")
    s.add_argument("projeto")
    s.add_argument("ref", help="id ou titulo (exato ou contido)")
    s.set_defaults(fn=_cmd_fecha("feita"))

    s = sub.add_parser("rm", help="remove pendencia (marca removida, sem apagar)")
    s.add_argument("projeto")
    s.add_argument("ref")
    s.set_defaults(fn=_cmd_fecha("removida"))

    s = sub.add_parser("pausar", help="projeto pausado some do widget (nada e apagado)")
    s.add_argument("projeto")
    s.set_defaults(fn=cmd_pausar)

    s = sub.add_parser("retomar", help="projeto volta ao widget")
    s.add_argument("projeto")
    s.set_defaults(fn=cmd_retomar)

    s = sub.add_parser("ocultar-auto", help="esconde a linha automatica ate o ESTADO.md mudar")
    s.add_argument("projeto")
    s.set_defaults(fn=cmd_auto(True))

    s = sub.add_parser("mostrar-auto", help="reexibe a linha automatica")
    s.add_argument("projeto")
    s.set_defaults(fn=cmd_auto(False))

    s = sub.add_parser("raiz", help="define a pasta de projetos a varrer")
    s.add_argument("caminho")
    s.set_defaults(fn=cmd_raiz)

    s = sub.add_parser("validar", help="checa a estrutura do registro")
    s.set_defaults(fn=cmd_validar)

    args = ap.parse_args(argv)
    try:
        if args.cmd in _COMANDOS_ESCRITA:
            caminho = Path(args.registro or paths.REGISTRY_PATH)
            with reg.trava(caminho):
                return args.fn(args)
        return args.fn(args)
    except reg.ErroRegistro as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
