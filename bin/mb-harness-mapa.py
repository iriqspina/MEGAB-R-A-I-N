#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mapa da cidade MegaBrain (harness animado e editável) — gerador.

Lê a FONTE editável dados/harness-mapa.json, valida (mensagens em português),
tira uma FOTOGRAFIA datada dos dados reais SEM gravar nada (cópia do banco pela
API de backup + leitura de JSON), embute mapa.css/mapa.js e as Ferramentas do
cursor e grava o HTML no caminho fixo:

    00_PARA-VOCE/261011_harnesses/261017_MAPA-DO-HARNESS.html

O nome nunca muda: o rascunho do visor do app depende do caminho do arquivo.

Uso:
    python bin/mb-harness-mapa.py                       # valida, fotografa e gera
    python bin/mb-harness-mapa.py --sem-fotografia      # não lê banco nem arquivos vivos
    python bin/mb-harness-mapa.py --validar             # só valida a fonte
    python bin/mb-harness-mapa.py --aplicar-remendos ARQ.json [--sem-gerar]
        funde os remendos exportados pelo mapa (ou o respostas.json do app)
        na fonte, com backup em .mb-backup/harness-mapa/, e gera de novo.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

CENTRAL = Path(__file__).resolve().parents[1]
BIN = CENTRAL / "bin"
FONTE_PADRAO = CENTRAL / "dados" / "harness-mapa.json"
SAIDA_PADRAO = CENTRAL / "00_PARA-VOCE" / "261011_harnesses" / "261017_MAPA-DO-HARNESS.html"
MODELO_DIR = CENTRAL / "motor" / "modelos" / "harness-mapa"
BACKUP_DIR = CENTRAL / ".mb-backup" / "harness-mapa"
BRT = dt.timezone(dt.timedelta(hours=-3))
LIMITE_HTML = 250_000
FORA_DO_HTML = ("historico", "raizes", "procedencia")  # o mapa não usa; o histórico cresce a cada remendo aplicado

if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))
import mb_pop_tema as pop  # noqa: E402

CAMPOS = {
    "estacao": ("nome", "descricao", "quem", "condicao", "bairro", "tecnico"),
    "linha": ("nome", "cor", "gatilho", "frequencia"),
    "bairro": ("nome", "descricao", "cor"),
}
RE_ID = re.compile(r"^[a-z0-9_]{1,40}$")
RE_COR = re.compile(r"^#[0-9a-fA-F]{6}$")
TIPOS = ("estacao", "placa", "deposito")
RESULTADOS = ("aprovado", "volta_1x", "espera")


class RemendoErro(ValueError):
    """Remendo que não se aplica à planta atual (mensagem em português)."""


def palavras(texto: str) -> int:
    return len([p for p in str(texto or "").split() if p])


# ═══ validação ═══════════════════════════════════════════════════════════════
def validar(d: dict) -> list[str]:
    """Devolve a lista de problemas (vazia = válido). Mensagens em pt-BR simples."""
    erros: list[str] = []
    if not isinstance(d, dict):
        return ["A fonte precisa ser um objeto JSON."]
    if d.get("formato") != "megabrain-harness-mapa":
        erros.append('Campo "formato" precisa ser "megabrain-harness-mapa".')
    if d.get("versao") != 1:
        erros.append('Campo "versao" precisa ser 1.')
    for campo in ("titulo", "bairros", "estacoes", "linhas", "responsaveis", "cenarios", "legenda", "preferencias"):
        if campo not in d:
            erros.append(f'Falta o campo "{campo}".')
    if erros:
        return erros
    resp = d["responsaveis"]
    if not isinstance(resp, dict) or not resp:
        erros.append('"responsaveis" precisa ter pelo menos um responsável.')
        resp = {}
    for k, r in resp.items():
        if not RE_ID.match(k):
            erros.append(f'Responsável com id inválido: "{k}".')
        if not isinstance(r, dict) or not str(r.get("nome", "")).strip():
            erros.append(f'Responsável "{k}" sem nome.')
            continue
        if not RE_COR.match(str(r.get("cor", ""))):
            erros.append(f'Responsável "{k}": cor inválida (use #RRGGBB).')
        if not (1 <= len(str(r.get("sigla", ""))) <= 3):
            erros.append(f'Responsável "{k}": a sigla precisa ter de 1 a 3 letras.')

    def ids_unicos(lista, rotulo):
        vistos = set()
        if not isinstance(lista, list):
            erros.append(f'"{rotulo}" precisa ser uma lista.')
            return {}
        out = {}
        for item in lista:
            if not isinstance(item, dict):
                erros.append(f'Item de "{rotulo}" precisa ser objeto.')
                continue
            i = item.get("id")
            if not isinstance(i, str) or not RE_ID.match(i):
                erros.append(f'{rotulo}: id inválido "{i}" (use letras minúsculas, números e _).')
                continue
            if i in vistos:
                erros.append(f'{rotulo}: id repetido "{i}".')
            vistos.add(i)
            out[i] = item
        return out

    bairros = ids_unicos(d["bairros"], "bairros")
    estacoes = ids_unicos(d["estacoes"], "estacoes")
    linhas = ids_unicos(d["linhas"], "linhas")
    cenarios = ids_unicos(d["cenarios"], "cenarios")
    for z in bairros.values():
        if not str(z.get("nome", "")).strip():
            erros.append(f'Bairro "{z["id"]}" sem nome.')
        if not RE_COR.match(str(z.get("cor", ""))):
            erros.append(f'Bairro "{z["id"]}": cor inválida (use #RRGGBB).')
        if z.get("faixa") not in (None, "topo", "base"):
            erros.append(f'Bairro "{z["id"]}": faixa precisa ser "topo" ou "base".')
        if z.get("rotulo_lado") not in (None, "esq", "dir"):
            erros.append(f'Bairro "{z["id"]}": rotulo_lado precisa ser "esq" ou "dir".')
    for e in estacoes.values():
        nome = str(e.get("nome", "")).strip()
        rot = f'Estação "{e["id"]}"'
        if not nome:
            erros.append(f"{rot}: falta o nome.")
        elif palavras(nome) > 3 or len(nome) > 28:
            erros.append(f'{rot}: o nome "{nome}" passa de 3 palavras ou 28 letras.')
        desc = str(e.get("descricao", "")).strip()
        if not desc:
            erros.append(f"{rot}: falta a descrição.")
        elif palavras(desc) > 20:
            erros.append(f"{rot}: a descrição tem {palavras(desc)} palavras; o limite é 20.")
        if e.get("bairro") not in bairros:
            erros.append(f'{rot}: bairro desconhecido "{e.get("bairro")}".')
        if e.get("quem") not in resp:
            erros.append(f'{rot}: responsável desconhecido "{e.get("quem")}".')
        if not str(e.get("condicao", "")).strip():
            erros.append(f"{rot}: falta a condição para seguir.")
        if e.get("tipo", "estacao") not in TIPOS:
            erros.append(f'{rot}: tipo precisa ser estacao, placa ou deposito.')
        for c in ("x", "y"):
            v = e.get(c)
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not (0 <= v <= 3000):
                erros.append(f"{rot}: posição {c} inválida (número entre 0 e 3000).")
        if not isinstance(e.get("arquivos", []), list) or not all(isinstance(a, str) for a in e.get("arquivos", [])):
            erros.append(f'{rot}: "arquivos" precisa ser lista de textos.')
        if not isinstance(e.get("verificado"), bool):
            erros.append(f'{rot}: "verificado" precisa ser true ou false.')
        if e.get("rotulo") not in (None, "cima", "baixo", "esq", "dir"):
            erros.append(f'{rot}: rótulo precisa ser cima, baixo, esq ou dir.')
        if e.get("papel") not in (None, "revisao"):
            erros.append(f'{rot}: papel precisa ser "revisao" ou ficar de fora.')
    for l in linhas.values():
        rot = f'Linha "{l["id"]}"'
        nome = str(l.get("nome", "")).strip()
        if not nome or len(nome) > 40 or palavras(nome) > 5:
            erros.append(f"{rot}: nome vazio ou longo demais (até 5 palavras).")
        if not RE_COR.match(str(l.get("cor", ""))):
            erros.append(f"{rot}: cor inválida (use #RRGGBB).")
        ests = l.get("estacoes")
        if not isinstance(ests, list) or len(ests) < 2:
            erros.append(f"{rot}: precisa de pelo menos 2 estações.")
            continue
        if len(set(ests)) != len(ests):
            erros.append(f"{rot}: a mesma estação aparece duas vezes.")
        for s in ests:
            if s not in estacoes:
                erros.append(f'{rot}: estação desconhecida "{s}".')
            elif estacoes[s].get("tipo", "estacao") != "estacao":
                erros.append(f'{rot}: "{s}" é placa ou depósito e não entra em linha.')
        for campo in ("esperas", "curva_cedo"):
            for s in l.get(campo, []) or []:
                if s not in ests:
                    erros.append(f'{rot}: {campo} cita "{s}", que não está na linha.')
        v = l.get("volta")
        if v is not None:
            if not isinstance(v, dict) or v.get("de") not in ests or v.get("para") not in ests:
                erros.append(f"{rot}: a volta precisa ligar duas estações da linha.")
            elif ests.index(v["para"]) >= ests.index(v["de"]):
                erros.append(f"{rot}: a volta precisa voltar para uma estação anterior.")
            elif not isinstance(v.get("max", 1), int) or not (1 <= v.get("max", 1) <= 3):
                erros.append(f"{rot}: máximo de voltas entre 1 e 3.")
            elif v.get("lado") not in (None, "cima", "baixo"):
                erros.append(f'{rot}: lado da volta precisa ser "cima" ou "baixo".')
    for c in cenarios.values():
        rot = f'Cenário "{c["id"]}"'
        if c.get("linha") not in linhas:
            erros.append(f'{rot}: linha desconhecida "{c.get("linha")}".')
            continue
        if c.get("resultado") not in RESULTADOS:
            erros.append(f"{rot}: resultado precisa ser aprovado, volta_1x ou espera.")
        if c.get("resultado") == "volta_1x" and not linhas[c["linha"]].get("volta"):
            erros.append(f"{rot}: volta_1x pede uma linha com volta.")
        if c.get("resultado") == "espera" and not linhas[c["linha"]].get("esperas"):
            erros.append(f"{rot}: espera pede uma linha com estação de espera.")
        if not str(c.get("pedido", "")).strip():
            erros.append(f"{rot}: falta o pedido de exemplo.")
    if not cenarios:
        erros.append("Inclua pelo menos um cenário.")
    leg = d.get("legenda")
    if not isinstance(leg, list) or not (1 <= len(leg) <= 7):
        erros.append("A legenda precisa ter de 1 a 7 símbolos.")
    for campo in ("subtitulo", "subtitulo_curto", "narracao_inicial"):
        if campo in d and (not isinstance(d[campo], str) or len(d[campo]) > 220):
            erros.append(f'"{campo}" precisa ser texto de até 220 letras.')
    for v in d.get("elevadores", []) or []:
        # estação que sumiu por remendo só deixa de ser desenhada; não invalida a planta
        if not isinstance(v, dict) or not isinstance(v.get("estacao"), str) or not str(v.get("texto", "")).strip() or len(str(v.get("texto"))) > 40:
            erros.append('Elevador precisa de "estacao" e de "texto" com até 40 letras.')
    for g in d.get("ligacoes", []) or []:
        if g.get("de") not in estacoes or g.get("para") not in estacoes:
            erros.append(f'Ligação {g.get("de")} → {g.get("para")}: estação desconhecida.')
        if g.get("tipo") not in ("le", "grava"):
            erros.append(f'Ligação {g.get("de")} → {g.get("para")}: tipo precisa ser "le" ou "grava".')
    for n in d.get("notas", []) or []:
        m = re.match(r"^(estacao|linha|bairro):(.+)$", str(n.get("alvo", "")))
        if n.get("alvo") != "mapa" and (not m or m.group(2) not in {"estacao": estacoes, "linha": linhas, "bairro": bairros}[m.group(1)]):
            erros.append(f'Nota "{n.get("id")}": alvo inexistente "{n.get("alvo")}".')
        if not str(n.get("texto", "")).strip():
            erros.append(f'Nota "{n.get("id")}" vazia.')
    pref = d.get("preferencias") or {}
    if pref.get("cenario_inicial") and pref["cenario_inicial"] not in cenarios:
        erros.append('preferencias.cenario_inicial aponta para um cenário que não existe.')
    return erros


# ═══ remendos (mesma semântica de mapa.js · aplicarUm) ════════════════════════
def _por_id(lista, i):
    for x in lista or []:
        if x.get("id") == i:
            return x
    return None


def _num(v, nome=""):
    try:
        n = float(v)
    except (TypeError, ValueError):
        raise RemendoErro(f"Posição inválida{' em ' + nome if nome else ''}.")
    if n != n or n in (float("inf"), float("-inf")):
        raise RemendoErro(f"Posição inválida{' em ' + nome if nome else ''}.")
    return max(0, min(3000, int(math.floor(n + 0.5))))  # igual ao Math.round do mapa.js


def _exige_est(m, i):
    e = _por_id(m["estacoes"], i)
    if not e:
        raise RemendoErro(f"Estação não encontrada: {i}.")
    return e


def _exige_est_linha(m, i):
    e = _exige_est(m, i)
    if e.get("tipo", "estacao") != "estacao":
        raise RemendoErro(f"“{e['nome']}” é placa ou depósito e não entra em linha.")
    return e


def _exige_linha(m, i):
    l = _por_id(m["linhas"], i)
    if not l:
        raise RemendoErro(f"Linha não encontrada: {i}.")
    return l


def _sem_dup(lista):
    vistos = set()
    for s in lista:
        if s in vistos:
            raise RemendoErro(f"A estação {s} aparece duas vezes na mesma linha.")
        vistos.add(s)


def _ajustar_linha(m, l):
    if "esperas" in l:
        l["esperas"] = [s for s in l["esperas"] if s in l["estacoes"]]
    if "curva_cedo" in l:
        l["curva_cedo"] = [s for s in l["curva_cedo"] if s in l["estacoes"]]
    v = l.get("volta")
    if v:
        a = l["estacoes"].index(v["de"]) if v.get("de") in l["estacoes"] else -1
        b = l["estacoes"].index(v["para"]) if v.get("para") in l["estacoes"] else -1
        if a < 0 or b < 0 or b >= a:
            del l["volta"]
    if not l.get("volta"):
        for c in m.get("cenarios", []):
            if c.get("linha") == l["id"] and c.get("resultado") == "volta_1x":
                c["resultado"] = "aprovado"
    if not l.get("esperas"):
        for c in m.get("cenarios", []):
            if c.get("linha") == l["id"] and c.get("resultado") == "espera":
                c["resultado"] = "aprovado"


def _checar_texto(campo, v):
    if campo == "nome" and (palavras(v) > 3 or len(v) > 28):
        raise RemendoErro("Use até 3 palavras no nome; os detalhes vão na descrição.")
    if campo == "descricao" and palavras(v) > 20:
        raise RemendoErro("A descrição passa de 20 palavras. Encurte para caber no mapa.")


def aplicar_um(m: dict, p: dict) -> dict:
    if not isinstance(p, dict):
        raise RemendoErro("Remendo inválido.")
    m.setdefault("notas", [])
    m.setdefault("ligacoes", [])
    m.setdefault("cenarios", [])
    op = p.get("op")
    if op == "mover":
        e = _exige_est(m, p.get("estacao"))
        e["x"] = _num(p.get("x"), e["nome"])
        e["y"] = _num(p.get("y"), e["nome"])
    elif op == "editar":
        tipo = p.get("tipo")
        lista = {"estacao": m["estacoes"], "linha": m["linhas"], "bairro": m["bairros"]}.get(tipo)
        if lista is None:
            raise RemendoErro(f"Tipo de edição desconhecido: {tipo}.")
        alvo = _por_id(lista, p.get("id"))
        if not alvo:
            raise RemendoErro(f"Não encontrei {tipo} {p.get('id')}.")
        campo = p.get("campo")
        if campo not in CAMPOS[tipo]:
            raise RemendoErro(f"Campo que não se edita pelo mapa: {campo}.")
        v = str("" if p.get("valor") is None else p.get("valor")).strip()
        if campo == "nome" and not v:
            raise RemendoErro("O nome não pode ficar vazio.")
        if campo == "quem" and v not in (m.get("responsaveis") or {}):
            raise RemendoErro(f"Responsável desconhecido: {v}.")
        if campo == "bairro" and not _por_id(m["bairros"], v):
            raise RemendoErro(f"Bairro desconhecido: {v}.")
        if campo == "cor" and not RE_COR.match(v):
            raise RemendoErro("Cor inválida: use #RRGGBB.")
        if len(v) > 400:
            raise RemendoErro("Texto longo demais (máximo 400 caracteres).")
        if tipo == "estacao":
            _checar_texto(campo, v)
        alvo[campo] = v
    elif op == "nova_estacao":
        i = p.get("id")
        if not isinstance(i, str) or not RE_ID.match(i):
            raise RemendoErro(f"Id de estação inválido: {i}.")
        if _por_id(m["estacoes"], i):
            raise RemendoErro(f"Já existe uma estação com o id {i}.")
        ref = _exige_est(m, p["depois_de"]) if p.get("depois_de") else None
        bz = p.get("bairro") or (ref["bairro"] if ref else ("centro" if _por_id(m["bairros"], "centro") else m["bairros"][0]["id"]))
        if not _por_id(m["bairros"], bz):
            raise RemendoErro(f"Bairro desconhecido: {bz}.")
        quem = p.get("quem") or "escolhida"
        if quem not in (m.get("responsaveis") or {}):
            quem = next(iter(m.get("responsaveis") or {"auto": 1}))
        nome = str(p.get("nome") or "Nova etapa").strip() or "Nova etapa"
        desc = str(p.get("descricao") or "Etapa nova criada no mapa. Descreva o que ela faz.")
        _checar_texto("nome", nome)
        _checar_texto("descricao", desc)
        nova = {
            "id": i, "nome": nome, "bairro": bz,
            "x": _num(p["x"] if p.get("x") is not None else (ref["x"] + 55 if ref else 600)),
            "y": _num(p["y"] if p.get("y") is not None else (ref["y"] if ref else 350)),
            "descricao": desc, "quem": quem, "condicao": str(p.get("condicao") or "a definir"),
            "arquivos": [], "verificado": False, "nota_prova": "Criada no mapa; ainda não existe no harness.",
        }
        m["estacoes"].append(nova)
        if p.get("linha"):
            l = _exige_linha(m, p["linha"])
            k = l["estacoes"].index(ref["id"]) if ref and ref["id"] in l["estacoes"] else -1
            if ref and k < 0:
                raise RemendoErro(f"A estação {ref['id']} não está na linha {l['id']}.")
            l["estacoes"].insert(k + 1, i)
    elif op == "remover_estacao":
        e = _exige_est(m, p.get("id"))
        for l in m["linhas"]:
            if e["id"] in l["estacoes"] and len(l["estacoes"]) <= 2:
                raise RemendoErro(f"A linha “{l['nome']}” ficaria com menos de 2 estações. Remova a linha antes.")
        m["estacoes"].remove(e)
        for l in m["linhas"]:
            l["estacoes"] = [s for s in l["estacoes"] if s != e["id"]]
            _ajustar_linha(m, l)
        m["ligacoes"] = [g for g in m["ligacoes"] if g.get("de") != e["id"] and g.get("para") != e["id"]]
        m["notas"] = [n for n in m["notas"] if n.get("alvo") != "estacao:" + e["id"]]
    elif op == "nova_linha":
        i = p.get("id")
        if not isinstance(i, str) or not RE_ID.match(i):
            raise RemendoErro(f"Id de linha inválido: {i}.")
        if _por_id(m["linhas"], i):
            raise RemendoErro(f"Já existe uma linha com o id {i}.")
        ests = list(p.get("estacoes") or [])
        if len(ests) < 2:
            raise RemendoErro("Uma linha precisa de pelo menos 2 estações.")
        for s in ests:
            _exige_est_linha(m, s)
        _sem_dup(ests)
        cor = p.get("cor") or "#8C9EFF"
        if not RE_COR.match(cor):
            raise RemendoErro("Cor inválida: use #RRGGBB.")
        m["linhas"].append({"id": i, "nome": str(p.get("nome") or "Nova linha").strip() or "Nova linha", "cor": cor,
                            "gatilho": str(p.get("gatilho") or "A definir."), "frequencia": str(p.get("frequencia") or "A definir."),
                            "estacoes": ests, "verificado": False})
        if not _por_id(m["cenarios"], "c_" + i):
            m["cenarios"].append({"id": "c_" + i, "linha": i, "pedido": "Pedido de exemplo", "resultado": "aprovado"})
    elif op == "remover_linha":
        l = _exige_linha(m, p.get("id"))
        if len(m["linhas"]) <= 1:
            raise RemendoErro("O mapa precisa de pelo menos uma linha.")
        m["linhas"].remove(l)
        m["cenarios"] = [c for c in m["cenarios"] if c.get("linha") != l["id"]]
        m["notas"] = [n for n in m["notas"] if n.get("alvo") != "linha:" + l["id"]]
        pref = m.get("preferencias") or {}
        if pref and not _por_id(m["cenarios"], pref.get("cenario_inicial")) and m["cenarios"]:
            pref["cenario_inicial"] = m["cenarios"][0]["id"]
    elif op == "ordem":
        l = _exige_linha(m, p.get("linha"))
        ordem = list(p.get("estacoes") or [])
        if len(ordem) < 2:
            raise RemendoErro("Uma linha precisa de pelo menos 2 estações.")
        for s in ordem:
            _exige_est_linha(m, s)
        _sem_dup(ordem)
        l["estacoes"] = ordem
        _ajustar_linha(m, l)
    elif op == "incluir":
        l = _exige_linha(m, p.get("linha"))
        e = _exige_est_linha(m, p.get("estacao"))
        if e["id"] in l["estacoes"]:
            raise RemendoErro(f"“{e['nome']}” já está na linha “{l['nome']}”.")
        k = -1
        if p.get("depois_de"):
            if p["depois_de"] not in l["estacoes"]:
                raise RemendoErro(f"A estação {p['depois_de']} não está na linha {l['id']}.")
            k = l["estacoes"].index(p["depois_de"])
        l["estacoes"].insert(k + 1, e["id"])
    elif op == "nota":
        texto = str(p.get("texto") or "").strip()
        if not texto:
            raise RemendoErro("A nota está vazia.")
        if len(texto) > 1000:
            raise RemendoErro("Nota longa demais (máximo 1000 caracteres).")
        alvo = p.get("alvo")
        if alvo != "mapa":
            mt = re.match(r"^(estacao|linha|bairro):(.+)$", str(alvo or ""))
            if not mt:
                raise RemendoErro(f"Alvo de nota inválido: {alvo}.")
            col = {"estacao": m["estacoes"], "linha": m["linhas"], "bairro": m["bairros"]}[mt.group(1)]
            if not _por_id(col, mt.group(2)):
                raise RemendoErro(f"A nota aponta para algo que não existe: {alvo}.")
        nid = p.get("id") or f"n{len(m['notas']) + 1}"
        if not RE_ID.match(str(nid)) or _por_id(m["notas"], nid):
            raise RemendoErro(f"Id de nota inválido ou repetido: {nid}.")
        m["notas"].append({"id": nid, "alvo": alvo, "texto": texto, "em": str(p.get("em") or ""), "quem": "voce"})
    elif op == "remover_nota":
        n = _por_id(m["notas"], p.get("id"))
        if not n:
            raise RemendoErro(f"Nota não encontrada: {p.get('id')}.")
        m["notas"].remove(n)
    else:
        raise RemendoErro(f"Remendo desconhecido: {op}.")
    return m


def aplicar(base: dict, patches: list) -> dict:
    m = copy.deepcopy(base)
    for i, p in enumerate(patches or [], 1):
        try:
            aplicar_um(m, p)
        except RemendoErro as e:
            raise RemendoErro(f"Remendo {i} ({(p or {}).get('op') if isinstance(p, dict) else '?'}): {e}") from None
    return m


def extrair_remendos(obj) -> tuple[list, str | None]:
    """Aceita a lista pura, o pacote exportado, respostas.json ou o comentário do app."""
    if isinstance(obj, list):
        return obj, None
    if isinstance(obj, dict):
        if isinstance(obj.get("patches"), list):
            return obj["patches"], obj.get("lote")
        for chave in ("mapa_harness", "respostas", "feedback"):
            if chave in obj:
                r = extrair_remendos(obj[chave])
                if r[0]:
                    return r
    return [], None


# ═══ fotografia datada (somente leitura) ══════════════════════════════════════
def _iso(v):
    if not isinstance(v, str) or not v:
        return None
    try:
        d = dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def _quando(d: dt.datetime | None) -> str:
    return d.astimezone(BRT).strftime("%d/%m %H:%M") if d else "?"


def _ler_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def _copiar_banco(origem: Path, destino: Path):
    """Cópia consistente sem gravar na origem: abre só leitura (mode=ro) e usa a API de backup."""
    src = sqlite3.connect(origem.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(destino))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


STATUS_JOB = {
    "completed": ("✓", "concluído", "resultados"),
    "partial": ("◐", "parcial", "rev_glm"),
    "interrupted": ("■", "interrompido", "executor"),
    "running": ("⟳", "rodando", "executor"),
    "queued": ("⟳", "na fila", "executor"),
    "failed": ("✗", "falhou", "executor"),
    "error": ("✗", "falhou", "executor"),
    "observed": ("◎", "acompanhado de fora", None),
}
CONTAS = {"claude": "Claude", "codex": "Codex 1", "codex_gpt2": "Codex 2", "zai": "Z.ai (GLM)", "spark": "Spark"}
STATUS_COMENTARIO = {"CORRIGIDO_VERIFICADO": "corrigido e conferido", "CONCILIADO_COM_PENDENCIAS": "conciliado com pendências",
                     "Recebido, aguardando correção": "aguardando correção"}


CLIENTES = {"": "sem nome (aberta sem --hook)", "desconhecido": "sem nome (aberta sem --hook)", "codex": "Codex",
            "codex desktop": "Codex desktop", "claude code desktop": "Claude Code desktop", "claude code": "Claude Code", "zcode": "ZCode"}


def _nome_cliente(valor) -> str:
    bruto = str(valor or "").strip()
    chave = re.sub(r"[-_\s]+", " ", bruto.lower()).strip()
    return CLIENTES.get(chave, bruto)


def coletar_fotografia(raiz: Path = CENTRAL, agora: dt.datetime | None = None) -> dict:
    agora = agora or dt.datetime.now(dt.timezone.utc)
    app = raiz / "apps" / "megabrain-dashboard"
    limite = agora - dt.timedelta(hours=24)
    foto = {"gerado_em": agora.isoformat(timespec="seconds"), "quando_txt": agora.astimezone(BRT).strftime("%d/%m/%Y %H:%M"),
            "aviso": "Fotografia datada, lida sem gravar nada. Não é ao vivo.", "avisos": [], "estacionados": []}
    # 1. sessões conectadas (24 h)
    pasta = app / "data" / "session-connections"
    sess = {"total": None, "por_cliente": {}, "fonte": "apps/megabrain-dashboard/data/session-connections/*.json"}
    if pasta.is_dir():
        total = 0
        for f in sorted(pasta.glob("*.json")):
            d = _ler_json(f)
            if not isinstance(d, dict):
                continue
            quando = _iso(d.get("updated_at")) or _iso(d.get("started_at"))
            if not quando or quando < limite:
                continue
            total += 1
            chave = _nome_cliente(d.get("application"))
            sess["por_cliente"][chave] = sess["por_cliente"].get(chave, 0) + 1
        sess["total"] = total
        sess["por_cliente"] = dict(sorted(sess["por_cliente"].items(), key=lambda kv: -kv[1]))
        if total:
            foto["estacionados"].append({"estacao": "sessoes", "n": total, "curto": f"{total} sess{'ões' if total != 1 else 'ão'}",
                                         "rotulo": f"{total} sessões se apresentaram ao app nas últimas 24 h"})
    else:
        foto["avisos"].append("Pasta de sessões não encontrada: NAO_MEDIDO.")
    foto["sessoes"] = sess
    # 2-4. banco do app (cópia temporária fora do projeto)
    banco = app / "data" / "central.sqlite3"
    pedidos = {"total": None, "ultimos": [], "fonte": "apps/megabrain-dashboard/data/central.sqlite3 · tabela jobs (cópia por backup)"}
    rel = {"total": None, "ultimos": [], "fonte": "apps/megabrain-dashboard/data/central.sqlite3 · tabela events (report_arrived/report_updated)"}
    com = {"pendentes": None, "total": None, "por_status": {}, "fonte": "apps/megabrain-dashboard/data/central.sqlite3 · tabela comments"}
    if banco.is_file():
        tmp = Path(tempfile.mkdtemp(prefix="mb-harness-foto-"))
        try:
            copia = tmp / "copia.sqlite3"
            _copiar_banco(banco, copia)
            c = sqlite3.connect(str(copia))
            try:
                jobs = []
                for (dado,) in c.execute("select data from jobs"):
                    try:
                        j = json.loads(dado)
                    except ValueError:
                        continue
                    jobs.append(j)
                pedidos["total"] = len(jobs)
                jobs.sort(key=lambda j: str(j.get("updated_at") or ""), reverse=True)
                parados = {}
                for j in jobs[:4]:
                    ic, txt, estacao = STATUS_JOB.get(str(j.get("status")), ("•", str(j.get("status") or "?"), None))
                    titulo = str(j.get("title") or "pedido").strip()
                    pedidos["ultimos"].append({"titulo": titulo[:58] + ("…" if len(titulo) > 58 else ""), "status": j.get("status"),
                                               "status_txt": txt, "icone": ic, "quando": _quando(_iso(j.get("updated_at")))})
                    if estacao:
                        parados.setdefault(estacao, []).append(txt)
                for estacao, lst in parados.items():
                    curto = f"1 pedido {lst[0]}" if len(lst) == 1 else f"{len(lst)} pedidos parados"
                    foto["estacionados"].append({"estacao": estacao, "n": len(lst), "curto": curto,
                                                 "rotulo": f"{len(lst)} pedido(s) do app parado(s) aqui: " + ", ".join(lst)})
                ultimos, total = [], 0
                for (dado,) in c.execute("select data from events order by id desc limit 4000"):
                    try:
                        ev = json.loads(dado)
                    except ValueError:
                        continue
                    if ev.get("kind") not in ("report_arrived", "report_updated"):
                        continue
                    quando = _iso(ev.get("at"))
                    if not quando or quando < limite:
                        continue
                    total += 1
                    if len(ultimos) < 4:
                        ultimos.append({"tipo": "chegou" if ev["kind"] == "report_arrived" else "atualizou", "titulo": str(ev.get("title") or "")[:60], "quando": _quando(quando)})
                rel["total"], rel["ultimos"] = total, ultimos
                if total:
                    foto["estacionados"].append({"estacao": "resultados", "n": total, "curto": f"{total} relatório{'s' if total != 1 else ''} (24 h)",
                                                 "rotulo": f"{total} relatório(s) chegaram ou mudaram nas últimas 24 h"})
                por = {}
                for (dado,) in c.execute("select data from comments"):
                    try:
                        st = json.loads(dado).get("status") or "?"
                    except ValueError:
                        continue
                    rot = STATUS_COMENTARIO.get(st, st)
                    por[rot] = por.get(rot, 0) + 1
                com["por_status"] = por
                com["total"] = sum(por.values())
                com["pendentes"] = sum(v for k, v in por.items() if k != STATUS_COMENTARIO["CORRIGIDO_VERIFICADO"])
                foto["estacionados"].append({"estacao": "balcao", "n": com["pendentes"], "curto": f"{com['pendentes']} sem correção",
                                             "rotulo": f"{com['pendentes']} de {com['total']} comentários ainda sem correção conferida"})
            finally:
                c.close()
        except sqlite3.Error as e:
            foto["avisos"].append(f"Banco do app não pôde ser lido ({e.__class__.__name__}): NAO_MEDIDO.")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        foto["avisos"].append("Banco do app não encontrado: NAO_MEDIDO.")
    foto["pedidos"], foto["relatorios"], foto["comentarios"] = pedidos, rel, com
    # 5. cotas
    cotas = {"contas": [], "maior": None, "fonte": "dados/orcamento_ia.json"}
    orc = _ler_json(raiz / "dados" / "orcamento_ia.json")
    if isinstance(orc, dict):
        for chave, v in orc.items():
            if not isinstance(v, dict):
                continue
            janelas = ((v.get("pacing") or {}).get("windows") or {}) if isinstance(v.get("pacing"), dict) else {}
            melhor = None
            for w in janelas.values():
                if isinstance(w, dict) and isinstance(w.get("used_percent"), (int, float)):
                    if melhor is None or w["used_percent"] > melhor["used_percent"]:
                        melhor = w
            base_conta = chave[:-len("_cancelado")] if chave.endswith("_cancelado") else chave
            conta = CONTAS.get(base_conta, base_conta.replace("_", " ")) + (" (registro cancelado)" if base_conta != chave else "")
            item = {"conta": conta, "pct": round(melhor["used_percent"]) if melhor else None,
                    "janela": (melhor or {}).get("label"), "de": _quando(_iso(v.get("updated_at"))) if v.get("updated_at") else None}
            cotas["contas"].append(item)
        medidas = [x for x in cotas["contas"] if x["pct"] is not None]
        if medidas:
            m = max(medidas, key=lambda x: x["pct"])
            cotas["maior"] = {"conta": m["conta"], "pct": m["pct"]}
            foto["estacionados"].append({"estacao": "retrato", "n": m["pct"], "sufixo": "%", "curto": f"{m['pct']}% da cota",
                                         "rotulo": f"Cota mais usada: {m['conta']} com {m['pct']}% ({m['janela'] or 'janela'})"})
    else:
        foto["avisos"].append("Retrato das cotas não encontrado: NAO_MEDIDO.")
    foto["cotas"] = cotas
    return foto


# ═══ HTML ════════════════════════════════════════════════════════════════════
def base_id(d: dict) -> str:
    txt = json.dumps({k: v for k, v in d.items() if k != "historico"}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()[:12]


def _json_seguro(obj) -> str:
    t = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    # "<" vira \u003C: o HTML nunca enxerga </script> ou <!-- nos dados, e o texto continua JSON válido
    return t.replace("<", "\\u003C").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _sem_comentario_final(s: str) -> str:
    """Tira " // ..." do fim da linha só quando as aspas antes dele estão fechadas (URL em string fica)."""
    i = s.find(" //")
    while i >= 0:
        antes = s[:i]
        if antes.count("'") % 2 == 0 and antes.count('"') % 2 == 0 and "`" not in antes:
            return antes.rstrip()
        i = s.find(" //", i + 3)
    return s


def compactar(txt: str, css: bool = False) -> str:
    """Tira recuo, linhas vazias e comentários de linha inteira antes de embutir.

    O HTML tem limite de 250 KB (o cursor sozinho pesa ~73 KB); a fonte em
    motor/modelos/harness-mapa/ continua legível. Não mexe no meio das linhas
    (strings e regex ficam como estão; " // comentário" no fim só sai com as aspas fechadas) e preserva
    as quebras de linha, então a semântica do JS (inclusive ASI) não muda.
    """
    if css:
        txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    saida, em_bloco = [], False
    for ln in txt.split("\n"):
        s = ln.strip()
        if not css:
            if em_bloco:
                if "*/" not in s:
                    continue
                em_bloco = False
                s = s.split("*/", 1)[1].strip()
            elif s.startswith("/*"):
                if "*/" not in s[2:]:
                    em_bloco = True
                    continue
                s = s[2:].split("*/", 1)[1].strip()
            if s.startswith("//"):
                continue
            s = _sem_comentario_final(s)
        if s:
            saida.append(s)
    return "\n".join(saida)


def compactar_cursor(txt: str) -> str:
    # O compactador conserva a semântica da fonte atual, sem strings multilinha.
    # Uma versão futura exige revisão explícita em vez de alterar o conteúdo delas.
    if "`" in txt or re.search(r"\\\r?\n", txt):
        raise ValueError("Cursor contém texto multilinha; revise a compactação antes de gerar o mapa.")
    return compactar(txt)


ICONE_MOV ='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h4l3-7 4 14 3-7h4" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def montar_html(d: dict, foto: dict | None, css: str, js: str, fonte_rel: str, gerado: dt.datetime) -> str:
    dados = {"base": {k: v for k, v in d.items() if k not in FORA_DO_HTML}, "base_id": base_id(d), "foto": foto, "gerado_em": gerado.isoformat(timespec="seconds"),
             "fonte": fonte_rel, "lotes_aplicados": [h["lote"] for h in d.get("historico", []) if isinstance(h, dict) and h.get("lote")]}
    linhas_txt = "".join(f"<li>{_esc(l['nome'])}: " + " → ".join(_esc(_por_id(d['estacoes'], s)['nome']) for s in l['estacoes']) + "</li>" for l in d["linhas"])
    quando = gerado.astimezone(BRT).strftime("%d/%m/%Y %H:%M")
    desc_svg = (f"Mapa em forma de cidade com metrô: {len(d['bairros'])} bairros, {len([e for e in d['estacoes'] if e.get('tipo', 'estacao') == 'estacao'])} estações "
                f"e {len(d['linhas'])} linhas coloridas. Cada linha é um processo do harness, lido da esquerda (você) para a direita (entrega).")
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(d['titulo'])}</title>
<meta name="description" content="Mapa animado e editável do harness MegaBrain. Fonte: {_esc(fonte_rel)}.">
{pop.JS_TEMA_HEAD}
<style>
{css}
</style>
</head>
<body>
<header class="mh-topo">
  <div class="mh-tit">
    <h1 title="Planta de {_esc(d.get('atualizado_em', ''))}"><span class="mh-marca" aria-hidden="true"><i></i></span>{_esc(d['titulo'])}</h1>
    <p class="mh-sub"><span class="mh-sub-l">{_esc(d.get('subtitulo', ''))}</span><span class="mh-sub-c">{_esc(d.get('subtitulo_curto') or d.get('subtitulo', ''))}</span></p>
  </div>
  <div class="mh-prefs" id="mh-prefs">
    <div id="mh-agora" class="mh-agora" role="group" aria-label="O que está parado agora: fotografia datada"></div>
    {pop.HTML_TEMA_CONTROLE}
    <button type="button" id="mh-mov" class="mh-b mh-ic" aria-pressed="false" title="Movimento: normal ou reduzido">{ICONE_MOV}<span class="mh-tx">Movimento: normal</span></button>
  </div>
</header>
<nav class="mh-barra" id="mh-barra" aria-label="Controles da animação">
  <div class="mh-ctl">
    <button type="button" id="mh-tocar" class="mh-b mh-b--prim">Tocar</button>
    <button type="button" id="mh-passo" class="mh-b" aria-label="Avançar um passo e narrar" title="Avançar um passo"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5l9 7-9 7zM16 5h3v14h-3z" fill="currentColor"/></svg><span class="mh-tx-c">Passo</span></button>
    <button type="button" id="mh-reiniciar" class="mh-b mh-ic" title="Reiniciar do começo"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12a8 8 0 1 0 3-6.2M4 4v5h5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg><span class="mh-tx">Reiniciar</span></button>
    <div class="mh-seg" id="mh-vel" role="group" aria-label="Velocidade"><button type="button" data-vel="0.5" aria-pressed="false">0,5×</button><button type="button" data-vel="1" aria-pressed="true">1×</button><button type="button" data-vel="2" aria-pressed="false">2×</button></div>
  </div>
  <label class="mh-linha-sel"><i id="mh-linha-cor" aria-hidden="true"></i><select id="mh-linha-sel" aria-label="Linha (processo) para tocar"></select></label>
  <div class="mh-narra-box">
    <div id="mh-regua" class="mh-regua" role="group" aria-label="Paradas desta linha"></div>
    <p id="mh-narra" class="mh-narra" role="status" aria-live="polite"><b id="mh-narra-n"></b><span id="mh-narra-tx">Carregando o mapa…</span></p>
  </div>
  <div class="mh-modos" id="mh-modos">
    <div class="mh-seg" role="group" aria-label="Modo"><button type="button" data-modo="ver" aria-pressed="true">Ver</button><button type="button" data-modo="editar" aria-pressed="false">Editar</button></div>
    <button type="button" id="mh-lista-btn" class="mh-b" aria-pressed="false" title="Ver a mesma informação em tabela">Lista</button>
  </div>
  <button type="button" id="mh-menu-btn" class="mh-b mh-ic" aria-expanded="false" aria-controls="mh-menu" aria-label="Mais opções" title="Mais opções"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h.01M12 12h.01M19 12h.01" stroke="currentColor" stroke-width="3.4" stroke-linecap="round"/></svg></button>
  <div id="mh-menu" class="mh-menu" hidden></div>
</nav>
<div id="mh-chips" class="mh-chips" role="radiogroup" aria-label="Escolha o processo para tocar"></div>
<div id="mh-edit" class="mh-edit" hidden>
  <p><b>Editar a planta = pedir mudança.</b> Arraste, renomeie com duplo clique ou use +. A IA aplica o pedido e gera o mapa de novo.</p>
  <button type="button" id="mh-nova-linha" class="mh-b">+ Linha</button>
  <button type="button" id="mh-desfazer" class="mh-b" disabled>Desfazer</button>
  <button type="button" id="mh-exportar" class="mh-b">Exportar</button>
  <button type="button" id="mh-importar" class="mh-b">Importar</button>
  <button type="button" id="mh-enviar" class="mh-b mh-b--prim">Enviar mudanças para a IA</button>
  <span id="mh-espaco" class="mh-espaco" role="status"></span>
</div>
<main id="mh-palco" class="mh-palco">
  <svg id="mh-mapa" xmlns="http://www.w3.org/2000/svg" role="group" aria-labelledby="mh-svg-t" aria-describedby="mh-svg-d" viewBox="0 0 1380 830">
    <title id="mh-svg-t">{_esc(d['titulo'])}</title>
    <desc id="mh-svg-d">{_esc(desc_svg)}</desc>
    <g id="g-bairros"></g><g id="g-elev"></g><g id="g-lig"></g><g id="g-marcos-conectores"></g><g id="g-bzrot"></g><g id="g-linhas"></g><g id="g-rastro"></g><g id="g-marcos"></g><g id="g-mais"></g><g id="g-est"></g><g id="g-parados"></g><g id="g-notas"></g><g id="g-anim"></g>
    <g id="g-medida" style="visibility:hidden" aria-hidden="true"></g>
  </svg>
  <div id="mh-vert" class="mh-vert"></div>
  <div id="mh-lista" class="mh-lista" hidden></div>
  <noscript><div class="mh-lista"><p>O mapa animado precisa de JavaScript. Resumo das linhas:</p><ul>{linhas_txt}</ul></div></noscript>
</main>
<aside id="mh-det" class="mh-det" hidden aria-label="Detalhe da estação"></aside>
<div id="mh-io" class="mh-io" hidden role="dialog" aria-label="Exportar ou importar mudanças"></div>
<div id="mh-toast" class="mh-toast" hidden role="status" aria-live="polite"></div>
<footer class="mh-rodape">
  <p>Gerado em {quando} por <code>bin/mb-harness-mapa.py</code> a partir de <code>{_esc(fonte_rel)}</code> · planta {dados['base_id']}. {_esc(d.get('procedencia', ''))}</p>
  <details><summary>Como este mapa é feito e como mudar</summary>
    <ol>
      <li>A planta fica em <code>dados/harness-mapa.json</code> (bairros, estações, linhas, quem faz, condição e arquivos que provam).</li>
      <li>O gerador valida a planta, tira uma fotografia dos dados reais sem gravar nada e escreve este arquivo sempre no mesmo caminho.</li>
      <li>No modo Editar você mexe no desenho. Isso fica guardado como pedido de mudança (rascunho); a planta e o harness só mudam quando a IA aplica: <code>python bin/mb-harness-mapa.py --aplicar-remendos &lt;arquivo&gt;</code>.</li>
      <li>“Agora na cidade” é uma fotografia de {_esc(foto['quando_txt']) if foto else 'nenhum momento (gerado sem fotografia)'}; não é ao vivo.</li>
    </ol>
  </details>
</footer>
<script>window.HARNESS = {_json_seguro(dados)};</script>
<script>
{js}
</script>
</body>
</html>
"""


def gerar(fonte: Path = FONTE_PADRAO, saida: Path = SAIDA_PADRAO, sem_fotografia: bool = False,
          raiz: Path = CENTRAL, agora: dt.datetime | None = None, modelo_dir: Path = MODELO_DIR) -> dict:
    d = json.loads(Path(fonte).read_text(encoding="utf-8-sig"))
    erros = validar(d)
    if erros:
        raise ValueError("A planta tem problemas:\n- " + "\n- ".join(erros))
    css = (modelo_dir / "mapa.css").read_text(encoding="utf-8")
    js = (modelo_dir / "mapa.js").read_text(encoding="utf-8")
    for nome, txt in (("mapa.css", css), ("mapa.js", js)):
        if "</script" in txt.lower() or "</style" in txt.lower():
            raise ValueError(f"{nome} contém </script> ou </style> e quebraria o HTML.")
    css, js = compactar(css, css=True), compactar(js)
    agora = agora or dt.datetime.now(dt.timezone.utc)
    foto = None if sem_fotografia else coletar_fotografia(raiz, agora)
    try:
        fonte_rel = Path(fonte).resolve().relative_to(CENTRAL).as_posix()
    except ValueError:
        fonte_rel = Path(fonte).name
    texto = montar_html(d, foto, css, js, fonte_rel, agora)
    texto, estado_cursor = pop.aplicar_interacoes(texto)
    if estado_cursor == "sem-componente":
        raise ValueError("Ferramentas do cursor não encontradas (motor/modelos/interacoes/261010_cursor-ferramentas).")
    # Só a cópia embutida do cursor: a fonte canônica permanece integral.
    # Sem encurtar identificadores nem remover quebras (ASI preservado).
    texto = re.sub(r"(<script\b[^>]*>)(/\* cursor-ferramentas.*?)(</script>)",
                   lambda m: m[1] + compactar_cursor(m[2]) + m[3], texto, flags=re.S)
    bruto = texto.encode("utf-8")
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    tmp = saida.with_name("." + saida.name + ".tmp")
    tmp.write_bytes(bruto)
    os.replace(tmp, saida)
    return {"saida": str(saida), "bytes": len(bruto), "sha256": hashlib.sha256(bruto).hexdigest(), "base_id": base_id(d),
            "estacoes": len(d["estacoes"]), "linhas": len(d["linhas"]), "fotografia": bool(foto),
            "avisos_fotografia": (foto or {}).get("avisos", []), "cursor": estado_cursor, "acima_do_alvo": len(bruto) > LIMITE_HTML}


def aplicar_remendos_arquivo(arquivo: Path, fonte: Path = FONTE_PADRAO, backup_dir: Path = BACKUP_DIR,
                             agora: dt.datetime | None = None) -> dict:
    obj = json.loads(Path(arquivo).read_text(encoding="utf-8-sig"))
    patches, lote = extrair_remendos(obj)
    if not patches:
        raise RemendoErro('Não achei remendos no arquivo (campo "patches").')
    bruto = Path(fonte).read_bytes()
    d = json.loads(bruto.decode("utf-8-sig"))
    erros = validar(d)
    if erros:
        raise ValueError("A planta atual já está inválida; corrija antes:\n- " + "\n- ".join(erros))
    novo = aplicar(d, patches)
    erros = validar(novo)
    if erros:
        raise RemendoErro("Depois dos remendos a planta ficou inválida:\n- " + "\n- ".join(erros))
    agora = agora or dt.datetime.now(dt.timezone.utc)
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    copia = backup_dir / f"harness-mapa_{agora.astimezone(BRT).strftime('%y%m%d-%H%M%S')}.json"
    copia.write_bytes(bruto)
    contagem = {}
    for p in patches:
        contagem[p.get("op")] = contagem.get(p.get("op"), 0) + 1
    novo.setdefault("historico", []).append({
        "em": agora.astimezone(BRT).isoformat(timespec="seconds"), "quem": "você, pelo mapa (aplicado pela IA)",
        "mudanca": f"Aplicou {len(patches)} remendo(s): " + ", ".join(f"{k} ×{v}" for k, v in contagem.items()),
        **({"lote": lote} if lote else {}),
    })
    novo["atualizado_em"] = agora.astimezone(BRT).date().isoformat()
    crlf = b"\r\n" in bruto
    texto = json.dumps(novo, ensure_ascii=False, indent=2) + "\n"
    if crlf:
        texto = texto.replace("\n", "\r\n")
    tmp = Path(fonte).with_name("." + Path(fonte).name + ".tmp")
    tmp.write_bytes(texto.encode("utf-8"))
    os.replace(tmp, fonte)
    return {"fonte": str(fonte), "backup": str(copia), "remendos": len(patches), "lote": lote,
            "sha256_antes": hashlib.sha256(bruto).hexdigest(), "sha256_depois": hashlib.sha256(texto.encode("utf-8")).hexdigest()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gera o Mapa da cidade MegaBrain (harness animado e editável).")
    ap.add_argument("--fonte", type=Path, default=FONTE_PADRAO)
    ap.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    ap.add_argument("--raiz", type=Path, default=CENTRAL, help="raiz da central para a fotografia (testes)")
    ap.add_argument("--sem-fotografia", action="store_true")
    ap.add_argument("--validar", action="store_true", help="só valida a fonte")
    ap.add_argument("--aplicar-remendos", type=Path, metavar="ARQ")
    ap.add_argument("--backup-dir", type=Path, default=BACKUP_DIR)
    ap.add_argument("--sem-gerar", action="store_true", help="com --aplicar-remendos: não gera o HTML depois")
    ap.add_argument("--json", action="store_true", help="saída em JSON")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    out: dict = {}
    try:
        if a.validar:
            d = json.loads(a.fonte.read_text(encoding="utf-8-sig"))
            erros = validar(d)
            out = {"valido": not erros, "erros": erros}
            print(json.dumps(out, ensure_ascii=False, indent=1) if a.json else ("Planta válida." if not erros else "Planta com problemas:\n- " + "\n- ".join(erros)))
            return 0 if not erros else 2
        if a.aplicar_remendos:
            out["remendos"] = aplicar_remendos_arquivo(a.aplicar_remendos, a.fonte, a.backup_dir)
            if a.sem_gerar:
                print(json.dumps(out, ensure_ascii=False, indent=1) if a.json else f"Remendos aplicados ({out['remendos']['remendos']}). Backup: {out['remendos']['backup']}")
                return 0
        out["gerado"] = gerar(a.fonte, a.saida, a.sem_fotografia, a.raiz)
    except (ValueError, RemendoErro) as e:
        print(("ERRO: " + str(e)) if not a.json else json.dumps({"erro": str(e)}, ensure_ascii=False))
        return 2
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        g = out["gerado"]
        if "remendos" in out:
            print(f"Remendos aplicados ({out['remendos']['remendos']}). Backup: {out['remendos']['backup']}")
        print(f"Mapa gerado: {g['saida']} ({g['bytes']:,} bytes, sha256 {g['sha256'][:12]}…, planta {g['base_id']}, fotografia {'sim' if g['fotografia'] else 'não'})")
        for av in g["avisos_fotografia"]:
            print("  aviso:", av)
        if g["acima_do_alvo"]:
            print(f"  aviso: acima do alvo de {LIMITE_HTML:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
