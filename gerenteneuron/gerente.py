"""Gerente geral — roteia pedidos do usuário para projetos/skills ativas."""

import json
from pathlib import Path


raiz_app = Path(__file__).resolve().parent
PROJETOS_PATH = raiz_app / "projetos.json"


def carregar_projetos() -> list[dict]:
    if not PROJETOS_PATH.exists():
        return []
    try:
        data = json.loads(PROJETOS_PATH.read_text(encoding="utf-8"))
        return data.get("projetos", [])
    except Exception:
        return []


def identificar_projeto(mensagem: str, projetos: list[dict]) -> dict | None:
    """Escolhe o projeto mais provável com base em palavras-chave."""
    texto = mensagem.lower()
    melhor = None
    melhor_score = 0

    for p in projetos:
        score = 0
        for kw in p.get("keywords", []):
            if kw.lower() in texto:
                score += 1
        # Bônus se o nome do projeto aparece literalmente.
        if p["nome"].lower() in texto or p["id"].lower() in texto:
            score += 3
        if score > melhor_score:
            melhor_score = score
            melhor = p

    # Só retorna se tiver alguma evidência.
    if melhor_score >= 1:
        return melhor
    return None


def identificar_intencao(mensagem: str) -> str:
    """Classifica o que o usuário quer fazer."""
    texto = mensagem.lower()
    if any(w in texto for w in ["onde estamos", "status", "estado", "resumo", "como ta", "como está"]):
        return "status"
    if any(w in texto for w in ["faz", "fazer", "atualiza", "atualizar", "muda", "mudar", "implementa", "cria", "criar", "ajusta", "ajustar"]):
        return "acao"
    if any(w in texto for w in ["qual", "quais", "como", "por que", "explica", "explique"]):
        return "pergunta"
    return "geral"


def responder_como_gerente(mensagem: str, historico: list | None = None) -> dict:
    projetos = carregar_projetos()
    projeto = identificar_projeto(mensagem, projetos)
    intencao = identificar_intencao(mensagem)

    if projeto:
        if intencao == "status":
            resposta = (
                f"Pedido reconhecido: **status de {projeto['nome']}**.\n\n"
                f"Skill a invocar: `{projeto['skill']}`\n"
                f"Próximo passo: pergunte 'onde estamos' usando `{projeto['skill']}`.\n\n"
                f"Se você quiser, posso formatar o prompt completo: '{mensagem}'"
            )
        elif intencao == "acao":
            resposta = (
                f"Pedido reconhecido: **ação em {projeto['nome']}**.\n\n"
                f"Skill a invocar: `{projeto['skill']}`\n"
                f"Ação sugerida: rode `{projeto['skill']}` e repasse o pedido completo.\n\n"
                f"Prompt pronto: '{mensagem}'"
            )
        else:
            resposta = (
                f"Pedido reconhecido: **{projeto['nome']}**.\n\n"
                f"Skill a invocar: `{projeto['skill']}`\n"
                f"Descrição: {projeto['descricao']}\n\n"
                f"Se quiser que eu execute por dentro do GerenteNeuron, confirme. "
                f"Se preferir, invoque `{projeto['skill']}` diretamente com: '{mensagem}'"
            )
        return {
            "resposta": resposta,
            "provider": "gerente",
            "modelo_usado": "gerente/local",
            "custo_estimado_usd": 0.0,
            "tokens_entrada": 0,
            "tokens_saida": 0,
            "projeto": projeto,
            "intencao": intencao,
        }

    # Sem projeto identificado: resumo geral ou pergunta ao megabrain.
    if intencao == "status":
        lista = "\n".join([f"- {p['nome']} (`{p['skill']}`)" for p in projetos]) or "Nenhum projeto cadastrado em projetos.json."
        resposta = (
            "Não identifiquei um projeto específico. Projetos ativos conhecidos:\n\n"
            + lista
            + "\n\nSe quiser o status de um deles, mencione o nome ou use a skill diretamente."
        )
    else:
        resposta = (
            "Não identifiquei a qual projeto esse pedido se refere. "
            "Mencione o nome do projeto ou cadastre-o em `gerenteneuron/projetos.json`.\n\n"
            "Se for uma questão geral de método, posso invocar `/megabrain`."
        )

    return {
        "resposta": resposta,
        "provider": "gerente",
        "modelo_usado": "gerente/local",
        "custo_estimado_usd": 0.0,
        "tokens_entrada": 0,
        "tokens_saida": 0,
        "projeto": None,
        "intencao": intencao,
    }
