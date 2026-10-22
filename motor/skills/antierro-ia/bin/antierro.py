#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""antierro.py — CLI da skill antierro-ia (stdlib pura, Windows+Linux).

Comandos:
  limites --ia <ia>              lista limites ativos (e avisa vencidos)
  registrar --ia <ia> --categoria <slug> --texto "..." --evidencia <path>
           [--severidade P1|P2|P3] [--achado_por auto|revisor|humano] [--modelo M]
  limite  --ia <ia> --texto "..." --categoria <slug> --reteste "<cmd>" --evidencia <path>
           [--expira_dias 30]   registra/atualiza limitação com expiração
  vencidos                       lista limites com re-teste pendente
  retestar --id <id> --resultado pass|fail   registra re-teste (2 pass seguidos = superado)
  reindex                        regenera INDICE-RETESTE.json
Dados em ias/<ia>/{limites,ocorrencias}.jsonl — append-only, id único.
Edições manuais nesses .jsonl são proibidas; use este CLI."""
import argparse, datetime as dt, json, sys, uuid
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent  # motor/skills/antierro-ia
IAS = AQUI / "ias"


def agora() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _arq(ia: str, nome: str) -> Path:
    p = IAS / ia / f"{nome}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _linhas(ia: str, nome: str) -> list:
    p = _arq(ia, nome)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def cmd_limites(a):
    lim = [l for l in _linhas(a.ia, "limites") if l.get("status") == "ativa"]
    venc = [l for l in lim if l.get("expira_em", "9999") < agora()[:10]]
    for l in lim:
        marca = "  ⚠ VENCIDO — re-teste antes de confiar" if l in venc else ""
        print(f"[{l['id']}] {l['categoria']} · {l['texto'][:90]} · expira {l.get('expira_em','-')}{marca}")
        print(f"        evidencia: {l.get('evidencia','-')} · reteste: {l.get('reteste','-')}")
    if not lim:
        print("(sem limites ativos para esta IA — aplique os gates universais)")
    return 0


def cmd_registrar(a):
    item = dict(id=uuid.uuid4().hex[:10], quando=agora(), ia=a.ia, categoria=a.categoria,
                texto=a.texto, evidencia=a.evidencia, severidade=a.severidade,
                achado_por=a.achado_por, modelo=a.modelo or "NAO_MEDIDO")
    with _arq(a.ia, "ocorrencias").open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print("registrado:", item["id"])
    return 0


def cmd_limite(a):
    existentes = _linhas(a.ia, "limites")
    igual = next((l for l in existentes if l.get("texto") == a.texto and l.get("status") != "superado"), None)
    expira = (dt.date.today() + dt.timedelta(days=a.expira_dias)).isoformat()
    if igual:
        igual.update(status="ativa", expira_em=expira, reteste=a.reteste, evidencia=a.evidencia, ultima=agora())
        linhas = [igual if l.get("id") == igual["id"] else l for l in existentes]
    else:
        linhas = existentes + [dict(id=uuid.uuid4().hex[:8], categoria=a.categoria, texto=a.texto,
                                    status="ativa", detectado_em=agora(), expira_em=expira,
                                    reteste=a.reteste, evidencia=a.evidencia)]
    _arq(a.ia, "limites").write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in linhas), encoding="utf-8")
    reindex(None)
    print("limite ativo. re-teste antes de expira:", expira)
    return 0


def cmd_vencidos(a):
    hoje = agora()[:10]
    achou = 0
    for ia_dir in sorted(IAS.glob("*")):
        if not ia_dir.is_dir() or ia_dir.name.startswith("_"):
            continue
        for l in _linhas(ia_dir.name, "limites"):
            if l.get("status") == "ativa" and l.get("expira_em", "9999") < hoje:
                achou += 1
                print(f"[{ia_dir.name}] {l['id']} · {l['categoria']} · venceu {l['expira_em']} · reteste: {l.get('reteste')}")
    if not achou:
        print("nenhum limite vencido")
    return 0


def cmd_retestar(a):
    for ia_dir in sorted(IAS.glob("*")):
        if not ia_dir.is_dir() or ia_dir.name.startswith("_"):
            continue
        lim = _linhas(ia_dir.name, "limites")
        mudou = False
        for l in lim:
            if l["id"] != a.id:
                continue
            hist = l.get("retestes", [])
            hist.append(dict(quando=agora(), resultado=a.resultado))
            l["retestes"] = hist
            ult2 = [h["resultado"] for h in hist[-2:]]
            if a.resultado == "pass" and len(ult2) == 2 and ult2 == ["pass", "pass"]:
                l["status"] = "superado"
                l["superado_em"] = agora()
                print(f"{l['id']}: SUPERADO (2 passes seguidos) — gate relaxa, histórico preservado")
            else:
                l["expira_em"] = (dt.date.today() + dt.timedelta(days=30)).isoformat()
                print(f"{l['id']}: re-teste {a.resultado} — expiração renovada")
            mudou = True
        if mudou:
            _arq(ia_dir.name, "limites").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lim), encoding="utf-8")
            return reindex(None)
    print("id não encontrado")
    return 1


def reindex(_):
    idx = dict(gerado_em=agora(), limite=[], por_ia={})
    for ia_dir in sorted(IAS.glob("*")):
        if not ia_dir.is_dir():
            continue
        ativos = [l for l in _linhas(ia_dir.name, "limites") if l.get("status") == "ativa"]
        idx["por_ia"][ia_dir.name] = dict(limites_ativos=len(ativos),
                                          ocorrencias=len(_linhas(ia_dir.name, "ocorrencias")))
        for l in ativos:
            idx["limite"].append(dict(id=l["id"], ia=ia_dir.name, categoria=l["categoria"],
                                      expira_em=l.get("expira_em"), reteste=l.get("reteste")))
    (AQUI / "INDICE-RETESTE.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


def main():
    p = argparse.ArgumentParser(description="antierro-ia CLI")
    sub = p.add_subparsers(dest="cmd", required=True)
    for nome in ("limites", "vencidos", "reindex"):
        s = sub.add_parser(nome)
        if nome == "limites":
            s.add_argument("--ia", required=True)
    r = sub.add_parser("registrar")
    r.add_argument("--ia", required=True); r.add_argument("--categoria", required=True)
    r.add_argument("--texto", required=True); r.add_argument("--evidencia", required=True)
    r.add_argument("--severidade", default="P2", choices=["P1", "P2", "P3"])
    r.add_argument("--achado_por", default="auto", choices=["auto", "revisor", "humano"])
    r.add_argument("--modelo", default="")
    l = sub.add_parser("limite")
    l.add_argument("--ia", required=True); l.add_argument("--categoria", required=True)
    l.add_argument("--texto", required=True); l.add_argument("--reteste", required=True)
    l.add_argument("--evidencia", required=True); l.add_argument("--expira_dias", type=int, default=30)
    t = sub.add_parser("retestar")
    t.add_argument("--id", required=True); t.add_argument("--resultado", required=True, choices=["pass", "fail"])
    a = p.parse_args()
    sys.exit(dict(limites=cmd_limites, registrar=cmd_registrar, limite=cmd_limite,
                  vencidos=cmd_vencidos, retestar=cmd_retestar, reindex=reindex)[a.cmd](a))


if __name__ == "__main__":
    main()
