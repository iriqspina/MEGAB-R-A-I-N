#!/usr/bin/env python3
"""Validação estrutural do relatório local, sem depender de navegador."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from ticket_model import load_config, portfolio_metrics, validate


RAIZ = Path(__file__).resolve().parents[1]
RELATORIO = RAIZ / "RELATORIO-MIMDE.html"
PAINEIS = {"hoje", "vender", "operar", "diretoria", "aprender", "fontes"}


class Auditor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paineis: list[str] = []
        self.alvos: list[str] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        dados = dict(attrs)
        if dados.get("data-panel"):
            self.paineis.append(str(dados["data-panel"]))
        if dados.get("data-panel-target"):
            self.alvos.append(str(dados["data-panel-target"]))
        if dados.get("id"):
            self.ids.append(str(dados["id"]))


def exigir(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise SystemExit(f"FALHA: {mensagem}")


def main() -> None:
    texto = RELATORIO.read_text(encoding="utf-8")
    config = load_config()
    falhas_modelo = validate(config)
    exigir(not falhas_modelo, f"modelo financeiro inválido: {falhas_modelo}")
    auditor = Auditor()
    auditor.feed(texto)

    exigir(not re.search(r"\{\{[A-Z_]+\}\}", texto), "há marcador não resolvido")
    exigir(set(auditor.paineis) == PAINEIS, f"painéis divergentes: {auditor.paineis}")
    exigir(len(auditor.paineis) == len(set(auditor.paineis)), "painel duplicado")
    exigir(set(auditor.alvos).issubset(PAINEIS), "botão aponta para painel inexistente")
    exigir(len(auditor.ids) == len(set(auditor.ids)), "id HTML duplicado")
    for legado in ("R$ 497", "R$ 897", "R$ 697/mês", "R$ 790–1.490"):
        exigir(legado not in texto, f"preço legado ainda presente: {legado}")
    for obrigatorio in (
        "R$ 5.200",
        "31,2%",
        "R$ 7.500,00/mês",
        "R$ 15,69/h de fixos",
        "Desconto de 5%",
        "R$ 90.000,00",
        "excede o teto em R$ 9.000,00",
        "Amarrador de Pontas",
        "Momentum que termina coisas",
        "data-panel=\"diretoria\"",
    ):
        exigir(obrigatorio in texto, f"conteúdo obrigatório ausente: {obrigatorio}")
    exigir("file://" not in texto, "link file:// foi embutido")
    sustentavel = portfolio_metrics(config, next(item for item in config["portfolios"] if item["id"] == "sustainable_direct"))
    exigir(sustentavel["operating_margin"] >= config["assumptions"]["target_operating_margin"], "cenário sustentável perdeu margem")
    exigir(sustentavel["owner_resources"] >= sustentavel["personal_target"], "cenário sustentável não cobre meta pessoal")
    print("relatório: OK — estrutura, tickets, margem, meta pessoal, MEI, Diretoria, momentum e Amarrador")


if __name__ == "__main__":
    main()
