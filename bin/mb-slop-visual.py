#!/usr/bin/env python3
"""mb-slop-visual.py - vigia de slop VISUAL (v1.0, 260824).

PRA QUE SERVE: o Gate 4 do megabrain audita slop de TEXTO (lexico e estrutura
banidos em referencias/260810_anti-slop.md). Slop VISUAL passava batido: o
gradiente de estoque, a grade de tres colunas iguais, tudo centralizado,
`transition: all`, a sombra que veio do template. Este script aponta os sinais
mecanicos. Ele NAO reescreve e NAO reprova - quem julga e o agente, no Gate 4.

Origem da ideia: `scripts/hooks/design-quality-check.js` do ECC
(github.com/affaan-m/ECC, MIT, (c) Affaan Mustafa). Os padroes de la eram de
Tailwind; estes aqui foram reescritos pro HTML/CSS que o megabrain gera, mais
as regras da casa (cor vem do tema, nunca !important, token de estado).

Referencia de conteudo: referencias/260824_interface-que-sente.md

Uso:
    python bin/mb-slop-visual.py 00_painel/RELATORIO.html
    python bin/mb-slop-visual.py 03_docs/*.html --json
    python bin/mb-slop-visual.py peca.html --tema      # arquivo E um tema: libera hex

Sai sempre com codigo 0 (e conselho, nao portao). --estrito sai 1 se achar algo.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXT_OK = {".html", ".htm", ".css", ".svg", ".jsx", ".tsx", ".vue", ".svelte"}

# (id, regex, rotulo, o-que-fazer)
SINAIS = [
    ("transicao-solta", re.compile(r"transition\s*:\s*all\b", re.I),
     "transition: all",
     "anima o que voce nao pediu e mata desempenho - liste as propriedades"),
    ("will-change-solto", re.compile(r"will-change\s*:\s*all\b", re.I),
     "will-change: all",
     "so em transform/opacity/filter, e so pra tremida de 1o quadro"),
    ("importante", re.compile(r"!important", re.I),
     "!important",
     "regra da casa: cascata :not() padrao Pico resolve; !important e desistir"),
    ("sombra-template", re.compile(
        r"box-shadow\s*:\s*0\s+(?:1px\s+3px|4px\s+6px|2px\s+4px)\s+rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0?\.1", re.I),
     "sombra default de framework",
     "sombra em camadas, transparente o bastante pra servir em fundo claro e escuro"),
    ("gradiente-estoque", re.compile(
        r"#667eea|#764ba2|#f093fb|#4facfe|bg-gradient-to-[trbl]\b", re.I),
     "gradiente de estoque",
     "esse gradiente roxo/azul e o mais copiado da internet - use cor do tema"),
    ("grade-uniforme", re.compile(
        r"grid-template-columns\s*:\s*repeat\(\s*[34]\s*,\s*(?:1fr|minmax)", re.I),
     "grade de 3 ou 4 colunas iguais",
     "cheque se as celulas tem MESMO peso; senao, quebre a simetria"),
    ("cta-generico", re.compile(
        r">\s*(?:saiba mais|clique aqui|comece agora|comece ja|get started|learn more|read more|sign up now)\s*<", re.I),
     "CTA generico",
     "diga o que acontece ao clicar: 'ver os 3 planos', 'baixar o PDF'"),
    ("fonte-default", re.compile(
        r"font-family\s*:\s*(?:inter|system-ui|sans-serif|-apple-system)\s*[;\}]", re.I),
     "fonte default sem pilha",
     "fonte unica sem fallback: escolha a familia e escreva a pilha inteira"),
    ("foco-apagado", re.compile(r"outline\s*:\s*(?:none|0)\s*[;\}]", re.I),
     "outline: none",
     "so vale se houver :focus-visible desenhado logo em seguida - senao quebra teclado"),
]

RE_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RE_ROOT = re.compile(r":root[^{]*\{[^}]*\}", re.S)
RE_CENTER = re.compile(r"text-align\s*:\s*center", re.I)
RE_SELETOR = re.compile(r"\}", re.S)
RE_RADIUS = re.compile(r"border-radius\s*:\s*([^;\}]+)", re.I)
RE_TABNUM = re.compile(r"tabular-nums", re.I)
RE_CONTADOR = re.compile(r"\b(?:contador|counter|valor|total|preco|timer|cronometro|score|placar)\b", re.I)
RE_CLASSE_ATTR = re.compile(r'class\s*=\s*"([^"]*)"')
RE_CLASSE_CSS = re.compile(r"^\s*([.#][\w.#>\s,:-]+)\{", re.M)


def analisar(texto: str, tema: bool = False) -> list[dict]:
    achados: list[dict] = []

    for sid, rx, rotulo, conserto in SINAIS:
        n = len(rx.findall(texto))
        if n:
            achados.append({"id": sid, "sinal": rotulo, "vezes": n, "conserto": conserto})

    # hex solto fora do :root (cor sai do TEMA, nao da mecanica)
    if not tema:
        fora = RE_ROOT.sub("", texto)
        hexes = {h.lower() for h in RE_HEX.findall(fora)}
        hexes -= {"#fff", "#ffffff", "#000", "#000000"}
        if len(hexes) >= 3:
            achados.append({
                "id": "hex-solto", "sinal": f"{len(hexes)} cores em hex fora do :root",
                "vezes": len(hexes),
                "conserto": "cor sai do TEMA (var(--x)); hex solto na mecanica e bug, nao escolha",
                "exemplo": ", ".join(sorted(hexes)[:6])})

    # tudo centralizado
    n_center = len(RE_CENTER.findall(texto))
    n_regras = max(1, len(RE_SELETOR.findall(texto)))
    if n_center >= 4 and n_center / n_regras > 0.12:
        achados.append({
            "id": "tudo-centralizado", "sinal": f"text-align:center em {n_center} regras",
            "vezes": n_center,
            "conserto": "centralizar tudo achata a hierarquia - alinhe a esquerda e destaque o que importa"})

    # raio unico em tudo = suspeita de raio nao-concentrico
    raios = {r.strip().lower() for r in RE_RADIUS.findall(texto)}
    raios -= {"0", "0px", "50%", "999px", "9999px", "100%"}
    if len(raios) == 1 and len(RE_RADIUS.findall(texto)) >= 4:
        achados.append({
            "id": "raio-unico", "sinal": f"um unico border-radius ({raios.pop()}) em tudo",
            "vezes": len(RE_RADIUS.findall(texto)),
            "conserto": "raio externo = raio interno + respiro; pai e filho com o mesmo raio nunca fecha opticamente"})

    # numero que atualiza sem tabular-nums - so olha NOME DE CLASSE/seletor,
    # nunca a prosa (a palavra "valor" num paragrafo nao e um contador)
    nomes = " ".join(RE_CLASSE_ATTR.findall(texto) + RE_CLASSE_CSS.findall(texto))
    if RE_CONTADOR.search(nomes) and not RE_TABNUM.search(texto):
        achados.append({
            "id": "sem-tabular", "sinal": "numero que atualiza sem tabular-nums", "vezes": 1,
            "conserto": "font-variant-numeric: tabular-nums - sem isso o numero dança a cada digito"})

    return achados


def main() -> int:
    ap = argparse.ArgumentParser(description="vigia de slop visual (Gate 4)")
    ap.add_argument("arquivos", nargs="+", help="html/css/svg/jsx a checar")
    ap.add_argument("--json", action="store_true", help="saida em JSON")
    ap.add_argument("--tema", action="store_true", help="o arquivo E um tema: nao reclamar de hex")
    ap.add_argument("--estrito", action="store_true", help="sair 1 se achar sinal")
    a = ap.parse_args()

    relatorio: list[dict] = []
    for bruto in a.arquivos:
        p = Path(bruto)
        if not p.exists():
            print(f"[?] nao existe: {p}", file=sys.stderr)
            continue
        if p.suffix.lower() not in EXT_OK:
            continue
        try:
            texto = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"[?] nao deu pra ler {p}: {e}", file=sys.stderr)
            continue
        relatorio.append({"arquivo": str(p), "achados": analisar(texto, a.tema)})

    if a.json:
        print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    else:
        total = 0
        for r in relatorio:
            ach = r["achados"]
            total += len(ach)
            if not ach:
                print(f"[ok] {r['arquivo']} - nenhum sinal mecanico")
                continue
            print(f"\n[!] {r['arquivo']} - {len(ach)} sinal(is)")
            for x in ach:
                ex = f"  ({x['exemplo']})" if x.get("exemplo") else ""
                print(f"  - {x['sinal']} x{x['vezes']}{ex}")
                print(f"      -> {x['conserto']}")
        if total:
            print("\nO vigia aponta; quem reescreve e voce. Sinal nao e veredito:")
            print("confira no arquivo antes de mudar. Olho humano continua obrigatorio")
            print("pra alinhamento optico, raio concentrico e estado vazio.")
            print("Detalhe: referencias/260824_interface-que-sente.md")

    try:  # telemetria falha em silencio, por contrato
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import mb_telemetria  # type: ignore
        mb_telemetria.registrar("slop_visual",
                                arquivos=len(relatorio),
                                sinais=sum(len(r["achados"]) for r in relatorio))
    except Exception:
        pass

    if a.estrito and any(r["achados"] for r in relatorio):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
