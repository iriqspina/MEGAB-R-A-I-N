#!/usr/bin/env python3
"""
mb_visual.py — renderizador das mecânicas visuais do megabrain (v6.6, 260822).

Por que existe: cada relatório reinventava HTML/CSS do zero, e isso custava
token toda vez. Aqui a peça visual vira DADO. O agente escolhe um id do
catálogo e preenche um dict; o HTML e o CSS já existem no disco.

    import mb_visual as v
    html = v.render("kpi-linha", {"itens": [{"valor": "v6.6", "rotulo": "versão"}]})
    css  = v.css()          # tokens + estilo de todas as mecânicas usadas

Onde ficam as peças: modelos/visuais/tokens.css e modelos/visuais/mecanicas/*.html
Catálogo legível: modelos/visuais/CATALOGO.md · exemplos: modelos/visuais/exemplos.json

Sintaxe do template (mini-mustache, ~40 linhas — não é Jinja de propósito):
    {{campo}}          valor escapado
    {{&campo}}         valor cru (HTML já pronto, ex.: outra mecânica dentro)
    {{#lista}}…{{/lista}}   repete o bloco por item; campos do item têm
                            precedência sobre os de fora; aceita aninhamento.

Campos derivados (o chamador não precisa passar):
    glifo  ← de status/estado: ok ✓ · ativo ● · espera ○ · trava ✕
    pct    ← de n/total em barra-segmentos (total é somado se ausente)
"""

from __future__ import annotations

import html as _html
import json
import re
from pathlib import Path

GLIFO = {"ok": "✓", "ativo": "●", "espera": "○", "trava": "✕"}
_CACHE: dict[str, dict] = {}


def raiz() -> Path:
    """modelos/visuais/: plano (cópia de projeto, central antiga) ou dentro de
    motor/ (v7.1 — etapa 2 da reorg). Sem depender de mb_utils, que esta
    biblioteca não importa de propósito."""
    base = Path(__file__).resolve().parent.parent
    for cand in (base / "modelos" / "visuais", base / "motor" / "modelos" / "visuais"):
        if cand.is_dir():
            return cand
    return base / "modelos" / "visuais"


def _carregar() -> dict[str, dict]:
    if _CACHE:
        return _CACHE
    pasta = raiz() / "mecanicas"
    if not pasta.is_dir():
        return _CACHE
    for arq in sorted(pasta.glob("*.html")):
        txt = arq.read_text(encoding="utf-8")
        meta: dict[str, str] = {}
        mh = re.search(r"<!--@mb-visual(.*?)-->", txt, re.S)
        if mh:
            for linha in mh.group(1).strip().splitlines():
                if ":" in linha:
                    k, _, val = linha.partition(":")
                    meta[k.strip()] = val.strip()
        ms = re.search(r"<style>(.*?)</style>", txt, re.S)
        mt = re.search(r"<template>(.*?)</template>", txt, re.S)
        ident = meta.get("id") or arq.stem
        _CACHE[ident] = {
            "id": ident,
            "arquivo": arq.name,
            "meta": meta,
            "css": (ms.group(1).strip() if ms else ""),
            "tpl": (mt.group(1).strip() if mt else ""),
        }
    return _CACHE


def ids() -> list[str]:
    return sorted(_carregar())


def catalogo() -> list[dict]:
    return [m["meta"] | {"id": m["id"], "arquivo": m["arquivo"]} for m in _carregar().values()]


# --------------------------------------------------------------------------
# motor
# --------------------------------------------------------------------------

def _enriquecer(d: dict) -> dict:
    est = d.get("status") or d.get("estado")
    if est and "glifo" not in d:
        d["glifo"] = GLIFO.get(str(est), "")
    if "n" in d and "pct" not in d:
        try:
            total = float(d.get("total") or 0)
            if total:
                d["pct"] = round(100 * float(d["n"]) / total, 3)
        except (TypeError, ValueError):
            pass
    return d


def _vars(txt: str, ctx: dict) -> str:
    def troca(m: re.Match) -> str:
        val = ctx.get(m.group(2), "")
        val = "" if val is None else str(val)
        return val if m.group(1) == "&" else _html.escape(val, quote=True)
    return re.sub(r"\{\{(&?)(\w+)\}\}", troca, txt)


def _render(tpl: str, ctx: dict) -> str:
    saida, i = [], 0
    while True:
        abre = re.search(r"\{\{#(\w+)\}\}", tpl[i:])
        if not abre:
            saida.append(_vars(tpl[i:], ctx))
            return "".join(saida)
        nome = abre.group(1)
        saida.append(_vars(tpl[i:i + abre.start()], ctx))
        corpo_ini = i + abre.end()
        par = re.compile(r"\{\{(#|/)" + nome + r"\}\}")
        prof, j, corpo_fim = 1, corpo_ini, None
        while prof:
            mm = par.search(tpl, j)
            if not mm:
                raise ValueError(f"mb_visual: seção {{{{#{nome}}}}} sem fechamento")
            prof += 1 if mm.group(1) == "#" else -1
            j = mm.end()
            if prof == 0:
                corpo_fim = mm.start()
        corpo = tpl[corpo_ini:corpo_fim]
        val = ctx.get(nome)
        if isinstance(val, list):
            for item in val:
                sub = dict(ctx)
                sub.update(item if isinstance(item, dict) else {"valor": item})
                saida.append(_render(corpo, _enriquecer(sub)))
        elif isinstance(val, dict):
            sub = dict(ctx); sub.update(val)
            saida.append(_render(corpo, _enriquecer(sub)))
        elif val:
            saida.append(_render(corpo, ctx))
        i = j


def _preparo(ident: str, dados: dict) -> dict:
    d = dict(dados)
    if ident == "barra-segmentos" and d.get("segmentos") and not d.get("total"):
        try:
            d["total"] = sum(float(s.get("n") or 0) for s in d["segmentos"])
        except (TypeError, ValueError):
            pass
    return d


def render(ident: str, dados: dict) -> str:
    """HTML de uma mecânica. Erra alto se o id não existe — silêncio aqui vira
    seção vazia no relatório, que é pior que exceção."""
    m = _carregar().get(ident)
    if not m:
        raise KeyError(f"mb_visual: mecânica '{ident}' não existe. Disponíveis: {', '.join(ids()) or '(nenhuma)'}")
    return _render(m["tpl"], _enriquecer(_preparo(ident, dados)))


def css(usar: list[str] | None = None) -> str:
    """tokens.css + o <style> das mecânicas pedidas (todas, se None)."""
    tok = raiz() / "tokens.css"
    partes = [tok.read_text(encoding="utf-8").strip()] if tok.is_file() else []
    for ident in (usar if usar is not None else ids()):
        m = _carregar().get(ident)
        if m and m["css"]:
            partes.append(f"/* mecânica: {ident} */\n{m['css']}")
    return "\n\n".join(partes)



def temas() -> list[dict]:
    """Os temas disponíveis, lidos de modelos/visuais/temas/NN-nome.css.

    Tema é a IDENTIDADE VISUAL (cor, tipo, raio, densidade); modo é só a
    direção da luminosidade. Os dois eixos são independentes — 3 temas × 2
    modos são 3+2 blocos de CSS, não 6.
    """
    pasta = raiz() / "temas"
    if not pasta.is_dir():
        return []
    achados = []
    for arq in sorted(pasta.glob("[0-9][0-9]-*.css")):
        txt = arq.read_text(encoding="utf-8")
        mn = re.search(r"@nome:\s*(.+)", txt)
        ma = re.search(r"@amostra:\s*(.+)", txt)
        nome = mn.group(1).strip() if mn else arq.stem.split("-", 1)[-1].title()
        amostra = ([c.strip() for c in ma.group(1).split(",")] if ma
                   else ["currentColor"] * 3)
        achados.append({
            "id": arq.stem, "num": arq.stem[:2], "nome": nome, "css": txt,
            "amostra": amostra,
        })
    return achados


def css_temas() -> str:
    return "\n".join(t["css"] for t in temas())


def _peca_tema(nome: str) -> str:
    arq = raiz() / "temas" / nome
    return arq.read_text(encoding="utf-8") if arq.is_file() else ""


def css_seletor() -> str:
    return _peca_tema("seletor.css")


def js_seletor() -> str:
    return _peca_tema("seletor.js")


def script_antiflash() -> str:
    """Inline e bloqueante no <head>: aplica tema/modo ANTES do primeiro paint.
    O try/catch não é opcional — em file:// o Safari LANÇA no localStorage, e
    sem o catch o script morre e nenhum atributo é aplicado."""
    return ("(function(){var R=document.documentElement,K='mb-relatorio:';"
            "try{var t=localStorage.getItem(K+'tema');if(t)R.setAttribute('data-tema',t);"
            "var m=localStorage.getItem(K+'modo');if(m){R.setAttribute('data-modo',m);"
            "R.style.colorScheme=m==='escuro'?'dark':'light';}}catch(e){}"
            "R.classList.add('pre-carga');})();")


def html_seletor(tema_padrao: str = "02-wildfire") -> str:
    """Dois radiogroups. Cada chip é pintado com os PRÓPRIOS tokens do tema —
    o preview mostra linguagem visual, não só cor."""
    lista = temas()
    if not lista:
        return ""
    botoes = []
    for t in lista:
        sw = "".join(f'<i style="background:{c}"></i>' for c in t["amostra"])
        marcado = "true" if t["id"] == tema_padrao else "false"
        botoes.append(f'<button class="sel__b" role="radio" data-grupo="tema" '
                      f'data-valor="{t["id"]}" aria-checked="{marcado}">'
                      f'<span class="sel__sw">{sw}</span>{t["num"]} {t["nome"]}</button>')
    while len(botoes) < 3:
        n = f"{len(botoes)+1:02d}"
        botoes.append(f'<button class="sel__b" role="radio" disabled aria-checked="false">'
                      f'<span class="sel__sw"><i style="background:var(--line)"></i>'
                      f'<i style="background:var(--line)"></i>'
                      f'<i style="background:var(--line)"></i></span>{n} —</button>')
    modos = "".join(
        f'<button class="sel__b" role="radio" data-grupo="modo" data-valor="{v}" '
        f'aria-checked="{"true" if v == "sistema" else "false"}">{r}</button>'
        for v, r in (("claro", "Claro"), ("escuro", "Escuro"), ("sistema", "Sistema")))
    return (f'<div class="sel">'
            f'<fieldset class="sel__g"><legend class="sel__l">tema</legend>'
            f'<div class="sel__r" role="radiogroup" aria-label="Tema">{"".join(botoes)}</div></fieldset>'
            f'<fieldset class="sel__g"><legend class="sel__l">modo</legend>'
            f'<div class="sel__r" role="radiogroup" aria-label="Modo">{modos}</div></fieldset>'
            f'<span class="sel__hint det" data-dica-modo></span></div>')

def exemplos() -> dict:
    arq = raiz() / "exemplos.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.is_file() else {}



def pagina_catalogo() -> str:
    """Galeria: cada mecânica renderizada com o exemplo + os dados que a
    geraram. É a peça que o <USUARIO> olha pra escolher, e o teste de fumaça
    do renderizador ao mesmo tempo."""
    ex = exemplos()
    blocos = []
    for m in catalogo():
        ident = m["id"]
        dados = ex.get(ident)
        if dados is None:
            corpo = '<p class="cat__falta">sem exemplo em exemplos.json — adicione um antes de usar</p>'
            bruto = ""
        else:
            corpo = render(ident, dados)
            bruto = _html.escape(json.dumps(dados, ensure_ascii=False, indent=2))
        blocos.append(f'''<section class="cat__m" id="{_html.escape(ident)}">
  <header class="cat__cab">
    <code class="cat__id">{_html.escape(ident)}</code>
    <span class="cat__nome">{_html.escape(m.get("nome",""))}</span>
  </header>
  <p class="cat__quando"><strong>quando:</strong> {_html.escape(m.get("quando",""))}</p>
  <p class="cat__dados"><strong>dados:</strong> <code>{_html.escape(m.get("dados",""))}</code>
     &nbsp;·&nbsp; <strong>custo:</strong> {_html.escape(m.get("custo","—"))}</p>
  <div class="cat__palco">{corpo}</div>
  <details class="cat__json"><summary>dados que geraram isto — copie e troque os valores</summary><pre>{bruto}</pre></details>
</section>''')
    indice = " · ".join(f'<a href="#{_html.escape(i)}">{_html.escape(i)}</a>' for i in ids())
    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MEGABRAIN — catálogo visual</title>
<style>
{css()}
*{{box-sizing:border-box}}
body{{margin:0;padding:var(--s4) var(--s3) var(--s4);background:var(--paper);color:var(--ink);
  font-family:var(--sans);font-size:15px;line-height:1.55;max-width:74rem;margin-inline:auto}}
h1{{font-size:1.3rem;margin:0 0 var(--s1)}}
.cat__sub{{color:var(--ink-soft);font-size:.82rem;margin:0 0 var(--s2);max-width:52rem}}
.cat__ind{{font-family:var(--mono);font-size:.72rem;padding:var(--s2) 0 var(--s4);border-bottom:1px solid var(--line)}}
.cat__ind a{{color:var(--info)}}
.cat__m{{padding:var(--s4) 0;border-bottom:1px solid var(--line)}}
.cat__cab{{display:flex;align-items:baseline;gap:var(--s2);flex-wrap:wrap}}
.cat__id{{font-family:var(--mono);font-size:.78rem;font-weight:700;background:var(--paper-sunk);
  border:1px solid var(--line);border-radius:var(--r);padding:1px var(--s1)}}
.cat__nome{{font-weight:700;font-size:.95rem}}
.cat__quando,.cat__dados{{font-size:.74rem;color:var(--ink-soft);margin:var(--s1) 0 0}}
.cat__dados code{{font-family:var(--mono);font-size:.7rem}}
.cat__palco{{margin-top:var(--s2);padding:var(--s3);background:var(--paper);
  border:1px dashed var(--line-strong);border-radius:var(--r)}}
.cat__json{{margin-top:var(--s2);font-size:.72rem}}
.cat__json summary{{cursor:pointer;color:var(--info)}}
.cat__json pre{{overflow-x:auto;background:var(--paper-sunk);border:1px solid var(--line);
  border-radius:var(--r);padding:var(--s2);font-family:var(--mono);font-size:.68rem;line-height:1.45}}
.cat__falta{{color:var(--signal);font-size:.78rem}}
.cat__rodape{{font-size:.72rem;color:var(--ink-faint);padding-top:var(--s3)}}
</style></head>
<body>
<h1>Catálogo visual do megabrain</h1>
<p class="cat__sub">{len(ids())} mecânicas prontas. Regra: <strong>antes de inventar um visual, procure aqui.</strong>
Escolher um id e preencher os dados custa ~10× menos token do que escrever HTML e CSS do zero —
e o resultado já sai no tema do sistema, com contraste conferido e responsivo.</p>
<nav class="cat__ind">{indice}</nav>
{"".join(blocos)}
<p class="cat__rodape">gerado por <code>bin/mb_visual.py --catalogo</code> ·
fonte: <code>modelos/visuais/mecanicas/</code> + <code>exemplos.json</code> ·
tokens de cor: <code>modelos/visuais/tokens.css</code></p>
</body></html>'''


def catalogo_md() -> str:
    """CATALOGO.md — a versão barata do catálogo, pro agente ler sem gastar
    contexto com HTML. Gerado, nunca escrito à mão: mecânica nova aparece aqui
    sozinha, e catálogo que mente é pior que catálogo que não existe."""
    linhas = [
        "# Catálogo visual do megabrain", "",
        "**Antes de inventar um visual, procure aqui.** Escolher um id e preencher",
        "os dados custa muito menos token do que escrever HTML e CSS do zero — e o",
        "resultado já sai no tema do sistema, com contraste conferido e responsivo.", "",
        "```python",
        "import mb_visual as v",
        "html = v.render(\"kpi-linha\", {\"itens\": [...]})   # peça",
        "css  = v.css()                                    # tokens + estilo",
        "```", "",
        "Formas prontas de dados: `modelos/visuais/exemplos.json` (copie e troque os",
        "valores). Galeria renderizada: `00_painel/CATALOGO-VISUAL.html`",
        "(`python bin/mb_visual.py --catalogo`).", "",
        "Status aceitos em toda mecânica: `ok` ✓ · `ativo` ● · `espera` ○ · `trava` ✕.",
        "O glifo é derivado pelo renderizador — não passe.", "",
        "| id | quando usar | dados | custo |", "|---|---|---|---|",
    ]
    for m in catalogo():
        linhas.append(f"| `{m['id']}` | {m.get('quando','')} | `{m.get('dados','')}` | {m.get('custo','—')} |")
    linhas += ["",
        "## Onde cada uma aparece na planta do relatório", "",
        "| slot | mecânica |", "|---|---|",
        "| D2 | `kpi-linha` |", "| D4 | `semaforo` |", "| D5 | `barra-segmentos` |",
        "| W1 | `fluxo-etapas` |", "| W2 | `trilha-dupla` |", "| W3 | `mapa-camadas` |",
        "| W4 | `timeline` |", "| — | `matriz` (sem slot fixo ainda) |", "",
        "## Como adicionar uma mecânica", "",
        "1. Copie um `.html` de `mecanicas/` — o cabeçalho `<!--@mb-visual -->` é obrigatório",
        "   (`id`, `nome`, `quando`, `dados`, `custo`).",
        "2. Só use variáveis de `tokens.css`. `#hex` solto numa mecânica é bug.",
        "3. Adicione uma entrada em `exemplos.json` — sem exemplo, a galeria acusa.",
        "4. Rode `python bin/mb_visual.py --catalogo` e confira no navegador.", "",
        "Fonte de layout no Figma: arquivo **megabrain** (prancheta MECÂNICAS).",
        "Desenhar lá e ajustar o `.html` conserta todo lugar onde a peça aparece.", "",
    ]
    return "\n".join(linhas)

if __name__ == "__main__":
    import sys
    if "--catalogo" in sys.argv:
        md = raiz() / "CATALOGO.md"
        md.write_text(catalogo_md(), encoding="utf-8")
        print(f"catálogo md: {md}")
        destino = raiz().parent.parent / "00_painel" / "CATALOGO-VISUAL.html"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(pagina_catalogo(), encoding="utf-8")
        print(f"catálogo: {destino}  ({destino.stat().st_size // 1024} KB, {len(ids())} mecânicas)")
    elif "--listar" in sys.argv:
        for m in catalogo():
            print(f"{m['id']:<18} {m.get('nome','')}\n{'':18} quando: {m.get('quando','')}")
    else:
        print(f"{len(ids())} mecânicas: {', '.join(ids())}")
        print(f"raiz: {raiz()}")
