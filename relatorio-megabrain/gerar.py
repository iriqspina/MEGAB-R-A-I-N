#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera a apresentação institucional autocontida do MEGABRAIN."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


FONTE = Path(__file__).resolve().parent
RAIZ = FONTE.parent
SAIDA = RAIZ / "RELATORIO.html"


def versao_atual() -> str:
    primeira_linha = (RAIZ / "VERSAO.txt").read_text(encoding="utf-8").splitlines()[0]
    achado = re.search(r"v\d+(?:\.\d+)+", primeira_linha)
    return achado.group(0) if achado else "versão não identificada"


def gerar() -> Path:
    template = (FONTE / "template.html").read_text(encoding="utf-8")
    css = (FONTE / "estilo.css").read_text(encoding="utf-8")
    javascript = (FONTE / "app.js").read_text(encoding="utf-8")
    agora = datetime.now().astimezone()
    versao = versao_atual()

    dados = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "name": "MEGABRAIN — visão geral",
        "abstract": (
            "Protocolo operacional para organizar projetos feitos com agentes de IA, "
            "preservar contexto, auditar entregas e registrar aprendizado."
        ),
        "dateModified": agora.isoformat(),
        "version": versao,
    }

    valores = {
        "{{CSS}}": css,
        "{{JS}}": javascript,
        "{{VERSAO}}": versao,
        "{{GENERATED_AT}}": agora.strftime("%d/%m/%Y %H:%M"),
        "{{JSON_LD}}": json.dumps(dados, ensure_ascii=False).replace("</", "<\\/"),
    }
    for marcador, valor in valores.items():
        template = template.replace(marcador, valor)

    restantes = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", template)))
    if restantes:
        raise RuntimeError(f"marcadores não resolvidos: {', '.join(restantes)}")

    paineis = {"comecar", "entender", "usar", "pratica", "limites", "fontes"}
    encontrados = set(re.findall(r'data-panel="([^"]+)"', template))
    if encontrados != paineis:
        raise RuntimeError(f"painéis incorretos: esperado {sorted(paineis)}, encontrado {sorted(encontrados)}")

    SAIDA.write_text(template, encoding="utf-8", newline="\n")
    return SAIDA


if __name__ == "__main__":
    print(f"Relatório gerado: {gerar()}")
