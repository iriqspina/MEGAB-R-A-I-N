#!/usr/bin/env python3
"""
mb-auditar-copias.py — audita as cópias de megabrain dos projetos irmãos.

Fase 3 da auditoria 260825. Responde três coisas por cópia:
  1. Está na versão da central?
  2. Carrega arquivo que a central já aposentou?
  3. Carrega nome de .cmd que a central já renomeou?

E mede o custo real da decisão PLANO × ANINHADO: quantos arquivos, quanto de
peso morto, e quanto do resolvedor de layout existe só por causa do plano.

Uso:
  mb-auditar-copias.py                 # relatório (não escreve nada)
  mb-auditar-copias.py --limpar        # move os mortos pra <copia>/90_arquivo/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import mb_utils as u

u.utf8_console()

# Arquivos que a central aposentou e que não devem mais existir em cópia nova.
# Cada um com o motivo, porque "arquivo morto" sem motivo vira fé.
MORTOS = {
    "PAINEL-MEGABRAIN.html": "aposentado em 260825 (2,7 MB, sem leitor, zero link)",
    "CATALOGO-VISUAL.html": "aposentado em 260825 (gêmeo do CATALOGO.md)",
    "RELATORIO-VIVO.html": "nome antigo do RELATORIO.html (v6.6)",
    "PIPELINE.md": "substituído por MEGABRAIN.md antes da v5",
    "ALINHAMENTO-AGENTES.md": "registro de incidente de 18/08, arquivado em 260825",
    "CHECKLIST-ABERTURA.md": "5 itens de 18/08 já resolvidos, arquivado em 260825",
    "260810_VISAO-GERAL.md": "excluído do pacote público desde a v6",
    "260805_licoes-backup-pre-fix.md": "backup de migração de 05/08",
    "260811_prompt-claude-handoff.txt": "artefato de sessão de 11/08",
    "mb-sync-all.cmd": "7 caminhos chumbados; substituído pelo sincronizar-projetos",
    "mb-patch-v5.py": "patches v4.9→v5.0; devolve 8/8 FALHA e escreveria VERSAO v5.0",
    "mb-migrar-v7.py": "migração já executada em 260824",
    "mb-migrar-motor.py": "migração já executada em 260824",
    "mb-painel.py": "gerador do PAINEL-MEGABRAIN, aposentado em 260825",
}

# .cmd cujo nome a central trocou. valor = nome novo, ou None se o botão não
# existe mais em cópia de projeto.
RENOMEADOS = {
    "260810_abrir-kimi-visual.cmd": "09_abrir-kimi-visual.cmd",
    "260810_instalar-identidade.cmd": "07_instalar-identidade.cmd",
    "260810_sincronizar-identidade.cmd": "06_sincronizar-identidade.cmd",
    "260810_publicar-github.cmd": None,
    "260821_push-github.cmd": None,
    "260819_refresh-plugin-kimi.cmd": "08_refresh-plugin-kimi.cmd",
    "sincronizar-pipeline.cmd": None,
}


def copias(raiz_projetos: Path) -> list[Path]:
    """Cópias de megabrain dos projetos.

    260825: detecta pelos DOIS formatos. A cópia magra não tem VERSAO.txt — ela
    tem `.mb-origem.json`. Procurar só por VERSAO.txt fez os verificadores
    reportarem "0 cópias" logo depois da conversão: a mudança de formato tinha
    tornado as cópias invisíveis pra quem as vigia.
    """
    achadas = []
    for p in sorted(raiz_projetos.rglob("MEGABRAIN")):
        if p.is_dir() and ((p / "VERSAO.txt").is_file()
                           or (p / ".mb-origem.json").is_file()):
            achadas.append(p)
    return achadas


def formato(p: Path) -> str:
    import json as _j
    txt = u.safe_read_text(p / ".mb-origem.json")
    if txt:
        try:
            if (_j.loads(txt) or {}).get("formato") == "magra":
                return "magra"
        except (ValueError, TypeError):
            pass
    return "aninhada" if (p / "motor").is_dir() or (p / "memoria").is_dir() else "plana"


def versao(p: Path) -> str:
    import json as _j
    if not (p / "VERSAO.txt").is_file():
        txt = u.safe_read_text(p / ".mb-origem.json")
        if txt:
            try:
                curta = (_j.loads(txt) or {}).get("versao_curta") or ""
                for pedaco in curta.split():
                    if pedaco.startswith("v") and pedaco[1:2].isdigit():
                        return pedaco
            except (ValueError, TypeError):
                pass
        return "?"
    linha = u.read_first_non_empty_line(p / "VERSAO.txt") or ""
    for pedaco in linha.split():
        if pedaco.startswith("v") and pedaco[1:2].isdigit():
            return pedaco.rstrip(",;")
    return "?"


def auditar(p: Path) -> dict:
    arquivos = [f for f in p.iterdir() if f.is_file()]
    mortos = [f.name for f in arquivos if f.name in MORTOS]
    velhos = [f.name for f in arquivos if f.name in RENOMEADOS]
    for sub in ("bin",):
        d = p / sub
        if d.is_dir():
            mortos += [f.name for f in d.iterdir() if f.is_file() and f.name in MORTOS]
    peso_morto = 0
    for nome in mortos:
        for cand in (p / nome, p / "bin" / nome):
            if cand.is_file():
                peso_morto += cand.stat().st_size
                break
    return {
        "caminho": p,
        "versao": versao(p),
        "arquivos_topo": len(arquivos),
        "formato": formato(p),
        "mortos": sorted(set(mortos)),
        "velhos": sorted(set(velhos)),
        "peso_morto": peso_morto,
        "licoes": len([1 for _ in (u.safe_read_text(p / "licoes-megabrain.md") or "").splitlines()
                       if _.startswith("## ")]),
    }


def limpar(r: dict) -> int:
    p = r["caminho"]
    destino = p / "90_arquivo" / "aposentados-260825"
    movidos = 0
    for nome in r["mortos"] + r["velhos"]:
        for origem in (p / nome, p / "bin" / nome):
            if origem.is_file():
                destino.mkdir(parents=True, exist_ok=True)
                origem.rename(destino / nome)
                movidos += 1
                break
    if movidos:
        motivo = "\n".join(
            f"- `{n}` — {MORTOS.get(n) or 'renomeado na central para ' + str(RENOMEADOS.get(n))}"
            for n in sorted(set(r["mortos"] + r["velhos"])))
        (destino / "LEIAME.md").write_text(
            "# Aposentados em 260825 (fase 3 da auditoria)\n\n"
            "Movidos, não apagados. A central já tinha aposentado cada um; a cópia\n"
            "deste projeto ficou pra trás porque o sync só ACRESCENTA, nunca remove.\n\n"
            + motivo + "\n", encoding="utf-8")
    return movidos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limpar", action="store_true")
    ap.add_argument("--projetos", default=None)
    a = ap.parse_args()

    central = Path(__file__).resolve().parent.parent
    raiz = Path(a.projetos) if a.projetos else central.parent
    v_central = versao(u.pasta(central, "nucleo"))

    achadas = [p for p in copias(raiz) if p.resolve() != central.resolve()]
    print(f"central: {v_central}  ·  cópias encontradas: {len(achadas)}\n")

    cab = f"{'projeto':<26} {'versão':<7} {'arqs':>5} {'mortos':>7} {'velhos':>7} {'lições':>7}  layout"
    print(cab)
    print("-" * len(cab))
    tot_mortos = tot_peso = 0
    resultados = []
    for p in achadas:
        r = auditar(p)
        resultados.append(r)
        tot_mortos += len(r["mortos"]) + len(r["velhos"])
        tot_peso += r["peso_morto"]
        nome = p.parent.name[:25]
        marca = "!" if r["versao"] != v_central else " "
        print(f"{nome:<26} {r['versao']:<6}{marca} {r['arquivos_topo']:>5} "
              f"{len(r['mortos']):>7} {len(r['velhos']):>7} {r['licoes']:>7}  "
              f"{r['formato']}")

    print(f"\ntotal: {tot_mortos} arquivo(s) morto(s) ou renomeado(s) · "
          f"{tot_peso / 1024:.0f} KB de peso morto")
    desatualizadas = [r for r in resultados if r["versao"] != v_central]
    if desatualizadas:
        print(f"desatualizadas (marcadas !): {len(desatualizadas)} — rode 01_acoes/05_sincronizar-projetos.cmd")

    if a.limpar:
        print("\nlimpando (mover, nunca apagar):")
        total = 0
        for r in resultados:
            n = limpar(r)
            if n:
                total += n
                print(f"  {r['caminho'].parent.name:<26} {n} arquivo(s) → 90_arquivo/aposentados-260825/")
        print(f"\nAPLICADO: {total} arquivo(s) movidos em {len(resultados)} cópia(s)")
    elif tot_mortos:
        print("\ndry-run — rode com --limpar pra mover (nada é apagado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
