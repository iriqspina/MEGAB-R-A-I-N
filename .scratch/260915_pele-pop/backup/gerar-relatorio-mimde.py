#!/usr/bin/env python3
"""Gera a console operacional única do MIMDE a partir das fontes locais."""

from __future__ import annotations

import html
import json
import re
from datetime import date, datetime
from pathlib import Path

from ticket_model import portfolio_metrics as calcular_portfolio
from ticket_model import service_metrics as calcular_servico


RAIZ = Path(__file__).resolve().parents[1]
FONTE = RAIZ / "relatorio-mimde"
TRACKER = RAIZ / ".scratch" / "automacao-ia" / "TRACKER.md"
FINANCEIRO = Path(r"<PROJETOS_ROOT>\Financeiro da Silva\03_plano\PLANO.md")
SAIDA = RAIZ / "RELATORIO-MIMDE.html"
TICKETS = RAIZ / "materiais" / "tickets-config.json"
PONTAS = RAIZ / ".scratch" / "amarrador" / "PONTAS.md"


def linhas_tabela(texto: str, titulo: str) -> list[dict[str, str]]:
    """Extrai a primeira tabela Markdown depois de um título exato."""
    linhas = texto.splitlines()
    inicio = next((i for i, linha in enumerate(linhas) if linha.strip() == titulo), None)
    if inicio is None:
        return []

    tabela: list[list[str]] = []
    for linha in linhas[inicio + 1 :]:
        limpa = linha.strip()
        if limpa.startswith("## ") and tabela:
            break
        if limpa.startswith("|") and limpa.endswith("|"):
            colunas = [celula.strip() for celula in limpa.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", celula) for celula in colunas):
                continue
            tabela.append(colunas)
        elif tabela and limpa:
            break

    if len(tabela) < 2:
        return []
    cabecalho = tabela[0]
    return [dict(zip(cabecalho, linha)) for linha in tabela[1:] if len(linha) == len(cabecalho)]


def metricas_html(texto: str) -> str:
    linhas = linhas_tabela(texto, "## Placar do sprint")
    if not linhas:
        return '<div class="empty">Tracker sem placar legível.</div>'
    partes = []
    for linha in linhas:
        partes.append(
            '<article class="metric">'
            f'<span class="label">meta · {html.escape(linha.get("Meta em 14 dias", "—"))}</span>'
            f'<strong class="metric__value">{html.escape(linha.get("Atual", "—"))}</strong>'
            f'<span class="metric__name">{html.escape(linha.get("Métrica", "Métrica"))}</span>'
            f'<span class="metric__rule">{html.escape(linha.get("Regra", ""))}</span>'
            '</article>'
        )
    return "".join(partes)


def aprovacoes_html(texto: str) -> str:
    linhas = linhas_tabela(texto, "## Aprovações do diretor")
    if not linhas:
        return '<li class="empty">Nenhum gate registrado.</li>'
    partes = []
    for linha in linhas:
        estado = linha.get("Estado", "Aguardando")
        classe = "tag--ok" if "Aprov" in estado else "tag--signal"
        partes.append(
            '<li class="approval">'
            f'<span class="gate">{html.escape(linha.get("Gate", "H"))}</span>'
            '<div>'
            f'<strong>{html.escape(linha.get("Decisão", ""))}</strong>'
            f'<p class="footnote">Libera: {html.escape(linha.get("Libera", ""))}</p>'
            '</div>'
            f'<span class="tag {classe}">{html.escape(estado)}</span>'
            '</li>'
        )
    return "".join(partes)


def leads_html(texto: str) -> str:
    linhas = linhas_tabela(texto, "## Leads e caixa")
    reais = [linha for linha in linhas if "exemplo" not in linha.get("Lead", "").lower()]
    if not reais:
        return '<div class="empty">Nenhum lead real registrado. O primeiro contato continua bloqueado pelo Gate H1.</div>'

    cabecalhos = ["Lead", "Empresa", "Caminho", "Dor pública observada", "Resposta", "Próxima ação", "Sinal", "Líquido"]
    head = "".join(f"<th>{html.escape(nome)}</th>" for nome in cabecalhos)
    corpo = "".join(
        "<tr>" + "".join(f"<td>{html.escape(linha.get(nome, '—'))}</td>" for nome in cabecalhos) + "</tr>"
        for linha in reais
    )
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{corpo}</tbody></table></div>'


def data_financeiro() -> tuple[str, str]:
    if not FINANCEIRO.is_file():
        return "não encontrada", "fonte indisponível"
    primeira = FINANCEIRO.read_text(encoding="utf-8").splitlines()[0]
    achado = re.search(r"(20\d{2}-\d{2}-\d{2})", primeira)
    if not achado:
        return "sem data", "validar antes de usar"
    data_fonte = date.fromisoformat(achado.group(1))
    atraso = (date.today() - data_fonte).days
    if atraso <= 0:
        frescor = "fonte atual"
    elif atraso == 1:
        frescor = "1 dia sem atualização"
    else:
        frescor = f"{atraso} dias sem atualização"
    return data_fonte.strftime("%d/%m/%Y"), frescor


def moeda(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def dados_tickets() -> dict:
    return json.loads(TICKETS.read_text(encoding="utf-8"))


def metricas_servico(config: dict, servico: dict, canal: str) -> dict[str, float]:
    metricas = calcular_servico(servico, config)
    return {
        "trabalho": metricas["labor"],
        "retrabalho": metricas["rework"],
        "custo_base": metricas["base_cost"],
        "fixo_alocado": metricas["fixed_allocation"],
        "piso": metricas[f"{canal}_floor"],
    }


def tabela_tickets_html(config: dict) -> str:
    linhas = []
    for servico in config["services"]:
        metricas = metricas_servico(config, servico, "direct")
        linhas.append(
            "<tr>"
            f"<td><strong>{html.escape(servico['name'])}</strong></td>"
            f"<td>{str(servico['hours']).replace('.', ',')} h</td>"
            f"<td>{moeda(metricas['piso'])}</td>"
            f"<td>{moeda(servico['direct_price'])}</td>"
            f"<td>{moeda(servico['platform_price'])}</td>"
            "</tr>"
        )
    return "".join(linhas)


def portfolio_metricas(config: dict, portfolio: dict) -> dict[str, float]:
    metricas = calcular_portfolio(config, portfolio)
    return {
        "receita": metricas["revenue"],
        "horas": metricas["billable_hours"],
        "lucro": metricas["operating_profit"],
        "margem": metricas["operating_margin"],
        "anual": metricas["annualized_revenue"],
        "mei_folga": metricas["mei_headroom"],
        "desconto_lucro": metricas["discount_5_profit"],
        "desconto_margem": metricas["discount_5_margin"],
        "estouro_lucro": metricas["hours_overrun_20_profit"],
        "estouro_margem": metricas["hours_overrun_20_margin"],
    }


def portfolios_html(config: dict) -> str:
    notas = {
        "activation": "Paga o motor; ainda não sustenta a meta.",
        "base": "Gera caixa; margem ainda abaixo de 30%.",
        "sustainable_direct": "Primeiro alvo mensal coerente.",
        "sustainable_platform": "Compensa a reserva conservadora do canal.",
    }
    partes = []
    for portfolio in config["portfolios"]:
        m = portfolio_metricas(config, portfolio)
        classe = "offer--primary" if portfolio["id"] == "sustainable_direct" else ""
        horas_texto = f'{m["horas"]:g}'.replace(".", ",")
        margem_texto = f'{m["margem"] * 100:.1f}'.replace(".", ",")
        partes.append(
            f'<article class="offer {classe}">'
            f'<span class="label">{html.escape(portfolio["name"])}</span>'
            f'<strong class="offer__price">{moeda(m["receita"])}/mês</strong>'
            f'<p>{horas_texto} h · lucro {moeda(m["lucro"])} · margem {margem_texto}%</p>'
            f'<p class="offer__scope">{html.escape(notas[portfolio["id"]])}</p>'
            '</article>'
        )
    return "".join(partes)


def sensibilidade_html(config: dict) -> str:
    portfolio = next(item for item in config["portfolios"] if item["id"] == "sustainable_direct")
    m = portfolio_metricas(config, portfolio)
    cenarios = [
        ("Base", m["lucro"], m["margem"], "meta preservada"),
        ("Desconto de 5%", m["desconto_lucro"], m["desconto_margem"], "não conceder sem reduzir escopo"),
        ("Horas +20%", m["estouro_lucro"], m["estouro_margem"], "parar em +10% e reescopar"),
    ]
    linhas = []
    for nome, lucro, margem, decisao in cenarios:
        margem_texto = f"{margem * 100:.1f}".replace(".", ",")
        classe = "tag--ok" if margem >= config["assumptions"]["target_operating_margin"] else "tag--signal"
        linhas.append(
            "<tr>"
            f"<td><strong>{html.escape(nome)}</strong></td>"
            f"<td>{moeda(lucro)}</td>"
            f"<td>{margem_texto}%</td>"
            f'<td><span class="tag {classe}">{html.escape(decisao)}</span></td>'
            "</tr>"
        )
    return "".join(linhas)


def mei_notice_html(config: dict) -> str:
    direto = portfolio_metricas(config, next(item for item in config["portfolios"] if item["id"] == "sustainable_direct"))
    plataforma = portfolio_metricas(config, next(item for item in config["portfolios"] if item["id"] == "sustainable_platform"))
    return (
        f'O direto anualiza {moeda(direto["anual"])} e deixa {moeda(direto["mei_folga"])} de folga antes de outras receitas do CNPJ. '
        f'A plataforma anualiza {moeda(plataforma["anual"])} e excede o teto em {moeda(-plataforma["mei_folga"])}; '
        'se esse ritmo se sustentar, a transição tributária precisa ser planejada antes do estouro.'
    )


def pontas_html() -> str:
    if not PONTAS.is_file():
        return '<li class="empty">Arquivo curado do Amarrador indisponível.</li>'
    linhas = linhas_tabela(PONTAS.read_text(encoding="utf-8"), "# Pontas curadas — MIMDE")
    if not linhas:
        return '<li class="empty">Nenhuma ponta priorizada.</li>'
    partes = []
    for linha in linhas[:5]:
        partes.append(
            '<li class="approval">'
            f'<span class="gate">{html.escape(linha.get("Prioridade", "—"))}</span>'
            '<div>'
            f'<strong>{html.escape(linha.get("Pergunta", ""))}</strong>'
            f'<p class="footnote">Impacto: {html.escape(linha.get("Impacto", ""))}</p>'
            '</div>'
            f'<span class="tag tag--signal">{html.escape(linha.get("Dono", "<USUARIO>"))}</span>'
            '</li>'
        )
    return "".join(partes)


def gerar() -> None:
    tracker = TRACKER.read_text(encoding="utf-8")
    template = (FONTE / "template.html").read_text(encoding="utf-8")
    css = (FONTE / "estilo.css").read_text(encoding="utf-8")
    javascript = (FONTE / "app.js").read_text(encoding="utf-8")
    data_fonte, frescor = data_financeiro()
    tickets = dados_tickets()

    valores = {
        "{{CSS}}": css,
        "{{JS}}": javascript,
        "{{GENERATED_AT}}": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "{{FINANCE_DATE}}": data_fonte,
        "{{FINANCE_FRESHNESS}}": frescor,
        "{{TRACKER_METRICS}}": metricas_html(tracker),
        "{{APPROVAL_ROWS}}": aprovacoes_html(tracker),
        "{{LEAD_TABLE}}": leads_html(tracker),
        "{{TICKET_ROWS}}": tabela_tickets_html(tickets),
        "{{PORTFOLIO_CARDS}}": portfolios_html(tickets),
        "{{SENSITIVITY_ROWS}}": sensibilidade_html(tickets),
        "{{MEI_NOTICE}}": mei_notice_html(tickets),
        "{{LOOSE_ENDS}}": pontas_html(),
    }
    for marcador, valor in valores.items():
        template = template.replace(marcador, valor)

    restantes = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", template)))
    if restantes:
        raise RuntimeError(f"marcadores não resolvidos: {', '.join(restantes)}")

    SAIDA.write_text(template, encoding="utf-8", newline="\n")
    print(f"Relatório gerado: {SAIDA}")


if __name__ == "__main__":
    gerar()
