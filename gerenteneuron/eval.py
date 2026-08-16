"""Avaliação e aprendizado de rotas do GerenteNeuron.

Registra cada interação, coleta feedback (👍/👎) e gera relatório simples
sobre quais estratégias/modelos estão funcionando melhor.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


raiz_app = Path(__file__).resolve().parent
DATA_DIR = raiz_app / "data"
FEEDBACK_FILE = DATA_DIR / "feedback.jsonl"


def _garantir_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def registrar_interacao(
    mensagem: str,
    resposta: dict,
    aba: str = "chat",
    feedback: int | None = None,
) -> dict:
    """Registra uma interação no log. feedback: 1=positivo, -1=negativo, None=sem feedback."""
    _garantir_data_dir()
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "aba": aba,
        "mensagem": mensagem,
        "estrategia": resposta.get("estrategia"),
        "provider": resposta.get("provider"),
        "modelo_usado": resposta.get("modelo_usado"),
        "custo_estimado_usd": resposta.get("custo_estimado_usd", 0),
        "tokens_entrada": resposta.get("tokens_entrada", 0),
        "tokens_saida": resposta.get("tokens_saida", 0),
        "erro": resposta.get("erro"),
        "feedback": feedback,
    }
    linha = json.dumps(registro, ensure_ascii=False)
    with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
        f.write(linha + "\n")
    return registro


def resumo_feedback(limite: int = 100) -> dict:
    """Lê os últimos registros e gera estatísticas por estratégia/modelo."""
    if not FEEDBACK_FILE.exists():
        return {"total": 0, "estrategias": {}, "modelos": {}}

    registros = []
    with FEEDBACK_FILE.open("r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                registros.append(json.loads(linha))
            except Exception:
                continue

    registros = registros[-limite:]
    estrategias = {}
    modelos = {}

    for r in registros:
        est = r.get("estrategia") or "desconhecida"
        mod = r.get("modelo_usado") or "desconhecido"
        fb = r.get("feedback")

        for chave, bucket in [(est, estrategias), (mod, modelos)]:
            if chave not in bucket:
                bucket[chave] = {"total": 0, "positivo": 0, "negativo": 0, "sem": 0, "erros": 0}
            bucket[chave]["total"] += 1
            if fb == 1:
                bucket[chave]["positivo"] += 1
            elif fb == -1:
                bucket[chave]["negativo"] += 1
            else:
                bucket[chave]["sem"] += 1
            if r.get("erro"):
                bucket[chave]["erros"] += 1

    return {"total": len(registros), "estrategias": estrategias, "modelos": modelos}


def sugerir_melhorias() -> list[str]:
    """Gera sugestões de ajuste no roteador baseadas no feedback."""
    resumo = resumo_feedback()
    sugestoes = []

    for est, stats in resumo["estrategias"].items():
        total = stats["total"]
        if total < 5:
            continue
        taxa_neg = stats["negativo"] / total
        taxa_err = stats["erros"] / total
        if taxa_neg > 0.4:
            sugestoes.append(f"Estratégia '{est}' tem {taxa_neg:.0%} de feedback negativo — revisar regras de classificação.")
        if taxa_err > 0.2:
            sugestoes.append(f"Estratégia '{est}' falha em {taxa_err:.0%} das vezes — verificar disponibilidade de modelos.")

    for mod, stats in resumo["modelos"].items():
        total = stats["total"]
        if total < 5:
            continue
        taxa_neg = stats["negativo"] / total
        if taxa_neg > 0.4:
            sugestoes.append(f"Modelo '{mod}' tem {taxa_neg:.0%} de feedback negativo — considerar descer ou subir no roteador.")

    return sugestoes
