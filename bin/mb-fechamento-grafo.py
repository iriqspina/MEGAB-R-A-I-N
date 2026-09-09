#!/usr/bin/env python3
"""
fechamento-grafo.py — gate de coerencia entre plano e realidade.

Roda no SubagentStop. Compara os arquivos que o plano DECLAROU tocar
com os que o git mostra realmente tocados. Divergencia = falha de
planejamento (nao de execucao) e vai para falhas.jsonl.

Tambem valida o plano contra PLANO.schema.json sem dependencia externa:
checa presenca de chave, minimos e campos vazios — os erros que mais
aparecem na pratica.

Saida: exit 0 sempre (nao bloqueia o fluxo), mas grava a falha e imprime
o aviso no stderr para o agente ler.
"""

import json, os, subprocess, sys, glob
from datetime import datetime, timezone

PLANO = os.environ.get("MB_PLANO", "PLANO.json")
FALHAS = os.environ.get("MB_FALHAS", "falhas.jsonl")

CHAVES_COBERTURA = [
    "migracao_dados", "rollback", "testes", "config_env", "documentacao",
    "erro_rede", "estado_vazio", "estado_carregando", "permissao_auth",
    "responsivo_mobile", "dark_mode", "acessibilidade", "performance",
    "log_observabilidade", "compatibilidade_versao",
]


def git_tocados():
    try:
        r = subprocess.run(["git", "status", "--porcelain"],
                           capture_output=True, text=True, timeout=10)
        out = set()
        for l in r.stdout.splitlines():
            if len(l) > 3:
                p = l[3:].strip()
                if " -> " in p:
                    p = p.split(" -> ")[-1]
                out.add(p.strip('"'))
        return out
    except Exception:
        return set()


def registrar(classe, detalhe, extra=None):
    ev = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "gate": "fechamento-grafo",
        "classe": classe,
        "detalhe": detalhe,
    }
    if extra:
        ev.update(extra)
    try:
        with open(FALHAS, "a") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except Exception:
        pass
    print(f"[megabrain] {classe}: {detalhe}", file=sys.stderr)


def valida_plano(p):
    erros = []

    for k in ["objetivo", "escopo_fora", "itens", "cobertura", "riscos",
              "criterio_de_aceite_global"]:
        if not p.get(k):
            erros.append(f"campo obrigatorio ausente ou vazio: {k}")

    ids = set()
    for it in p.get("itens", []):
        i = it.get("id", "?")
        ids.add(i)
        for k in ["arquivos_alvo", "dono", "criterio_de_pronto", "risco"]:
            if not it.get(k):
                erros.append(f"item {i}: campo '{k}' vazio")
        alvos = it.get("arquivos_alvo") or []
        if any(a.strip() in ("?", "", "TBD", "a definir") for a in alvos):
            erros.append(f"item {i}: arquivo_alvo indefinido — item nao esta planejado")
        cp = (it.get("criterio_de_pronto") or "").lower()
        if cp and len(cp) < 15:
            erros.append(f"item {i}: criterio_de_pronto curto demais para ser verificavel")
        for vago in ["funciona bem", "esta ok", "ficar bom", "corretamente"]:
            if vago in cp:
                erros.append(f"item {i}: criterio_de_pronto vago ('{vago}')")

    for it in p.get("itens", []):
        for d in it.get("depende_de", []):
            if d not in ids:
                erros.append(f"item {it.get('id')}: depende de '{d}' que nao existe no plano")

    cob = p.get("cobertura", {}) or {}
    for k in CHAVES_COBERTURA:
        v = cob.get(k)
        if not isinstance(v, dict) or not v.get("status"):
            erros.append(f"cobertura.{k} nao respondida")
        elif not (v.get("nota") or "").strip():
            erros.append(f"cobertura.{k}: status '{v.get('status')}' sem justificativa")

    lac = p.get("lacunas_adversario")
    if lac is None:
        erros.append("lacunas_adversario ausente — o gate adversarial nao rodou")
    elif len(lac) < 5:
        erros.append(f"lacunas_adversario tem {len(lac)}, minimo 5")
    else:
        for l in lac:
            if l.get("resolucao") != "incorporada" and not (l.get("justificativa") or "").strip():
                erros.append(f"lacuna '{str(l.get('lacuna'))[:40]}' foi {l.get('resolucao')} sem justificativa")

    return erros


def main():
    if not os.path.exists(PLANO):
        return 0

    try:
        p = json.load(open(PLANO))
    except Exception as e:
        registrar("plano-invalido", f"json ilegivel: {e}")
        return 0

    for e in valida_plano(p):
        registrar("plano-incompleto", e)

    declarados = set()
    for it in p.get("itens", []):
        for a in it.get("arquivos_alvo", []):
            declarados.add(a.strip().lstrip("./"))

    reais = {r.lstrip("./") for r in git_tocados()}
    ignorar = {PLANO.lstrip("./"), FALHAS.lstrip("./"),
               "ESTADO.md", "HANDOFF.md", "DECISOES.md"}
    reais -= ignorar

    def casa(r):
        return any(r == d or r.endswith("/" + d) or d.endswith("/" + r) or
                   (d.endswith("/") and r.startswith(d)) for d in declarados)

    nao_previstos = sorted(r for r in reais if not casa(r))
    if nao_previstos:
        registrar("arquivo-nao-previsto",
                  f"{len(nao_previstos)} arquivo(s) alterado(s) fora do plano",
                  {"arquivos": nao_previstos[:20]})

    nao_tocados = sorted(d for d in declarados
                         if not any(r == d or r.endswith("/" + d) for r in reais))
    if nao_tocados and reais:
        registrar("item-nao-executado",
                  f"{len(nao_tocados)} arquivo(s) declarado(s) e nao alterado(s)",
                  {"arquivos": nao_tocados[:20]})

    return 0


if __name__ == "__main__":
    sys.exit(main())
