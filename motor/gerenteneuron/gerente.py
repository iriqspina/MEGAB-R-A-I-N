"""Gerente geral — roteia pedidos do usuário para projetos/skills ativas.

v7.1 (260824): o Neuron também OBSERVA. Pergunta sobre uso ("o que eu mais
uso", "telemetria", "quanto gastei") é respondida a partir do caderninho
local .mb-log/ pelo bin/mb_telemetria.py da central — sem chamar modelo
nenhum e sem nada sair do PC (spec 03_docs/260824_spec-fase2.md §4/§6).
"""

import json
import re
import unicodedata
from pathlib import Path


def _normalizar(texto: str) -> str:
    """Minúsculas, sem acento, com espaço nas bordas para casar palavra inteira."""
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9\-\s]", " ", texto)
    return " " + re.sub(r"\s+", " ", texto).strip() + " "


def _casa(termo: str, texto_norm: str) -> bool:
    """Casa palavra inteira.

    Com `termo in texto` cru, um projeto chamado 'A' casava com 'bom dia' e a
    keyword 'api' casava dentro de 'rapidez'. O gerente apontava a skill errada
    com cara de certeza.
    """
    termo = _normalizar(termo).strip()
    return bool(termo) and f" {termo} " in texto_norm


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
    texto = _normalizar(mensagem)
    melhor = None
    melhor_score = 0

    for p in projetos:
        score = 0
        for kw in p.get("keywords", []):
            if _casa(kw, texto):
                score += 1
        # Bônus se o nome do projeto aparece literalmente.
        if _casa(p.get("nome", ""), texto) or _casa(p.get("id", ""), texto):
            score += 3
        if score > melhor_score:
            melhor_score = score
            melhor = p

    # Só retorna se tiver alguma evidência.
    if melhor_score >= 1:
        return melhor
    return None


PALAVRAS_OBSERVAR = ("telemetria", "uso", "usei", "uso mais", "mais uso", "mais usei",
                     "estatistica", "estatisticas", "quanto gastei", "custo", "custos",
                     "observatorio", "caderninho", "frequencia")


def identificar_intencao(mensagem: str) -> str:
    """Classifica o que o usuário quer fazer."""
    texto = _normalizar(mensagem)
    if any(f" {w} " in texto for w in PALAVRAS_OBSERVAR):
        return "observar"
    if any(w in texto for w in ["onde estamos", "status", "estado", "resumo", "como ta", "como esta"]):
        return "status"
    if any(f" {w} " in texto for w in ["faz", "fazer", "atualiza", "atualizar", "muda", "mudar", "implementa", "cria", "criar", "ajusta", "ajustar"]):
        return "acao"
    if any(f" {w} " in texto for w in ["qual", "quais", "como", "por que", "explica", "explique"]):
        return "pergunta"
    return "geral"


def responder_como_gerente(mensagem: str, historico: list | None = None) -> dict:
    projetos = carregar_projetos()
    projeto = identificar_projeto(mensagem, projetos)
    intencao = identificar_intencao(mensagem)

    if intencao == "observar":
        return {
            "resposta": texto_observatorio(),
            "provider": "gerente",
            "modelo_usado": "gerente/local",
            "custo_estimado_usd": 0.0,
            "tokens_entrada": 0,
            "tokens_saida": 0,
            "projeto": projeto,
            "intencao": intencao,
        }

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


# ---------------------------------------------------------------------------
# v7.1 — o Neuron lê a telemetria da central (spec §4/§6)
# Sobe do arquivo até achar bin/mb_telemetria.py: sobrevive à mudança da
# máquina pra motor\ (etapa 2 da reorg) sem reapontar caminho na mão.
# ---------------------------------------------------------------------------

def _bin_da_central() -> Path | None:
    aqui = Path(__file__).resolve()
    for cand in [aqui.parent, *aqui.parents]:
        alvo = cand / "bin" / "mb_telemetria.py"
        if alvo.is_file():
            return alvo.parent
    return None


def telemetria_resumo(dias: int = 90) -> dict | None:
    """Agregado local de .mb-log/. None se a central não estiver por perto."""
    caminho_bin = _bin_da_central()
    if caminho_bin is None:
        return None
    import sys
    if str(caminho_bin) not in sys.path:
        sys.path.insert(0, str(caminho_bin))
    try:
        import mb_telemetria as tel
        return tel.resumo(caminho_bin.parent, dias=dias)
    except Exception:
        return None


def texto_observatorio(dias: int = 90) -> str:
    """Resposta do Neuron observador, em markdown, sem chamar modelo."""
    r = telemetria_resumo(dias)
    if r is None:
        return ("Não achei a central do megabrain a partir daqui, então não tenho "
                "caderninho pra ler. Rode o Neuron de dentro da pasta da central.")
    if not r.get("eventos"):
        return (f"O caderninho está vazio nos últimos {dias} dias.\n\n"
                "Ele enche sozinho conforme as sessões registram "
                "(`bin/mb_telemetria.py --evento sessao --skill ...`). "
                "Nada disso sai do seu PC.")
    def _lista(chave, rotulo, n=5):
        itens = list(r["por"].get(chave, {}).items())[:n]
        if not itens:
            return ""
        return f"\n**{rotulo}**\n" + "\n".join(f"- {k} — {v}" for k, v in itens) + "\n"
    partes = [f"**Observatório do Neuron** — {r['eventos']} eventos em "
              f"{len(r.get('dias', {}))} dia(s), janela de {dias} dias.\n"]
    partes.append(_lista("skill", "Skills mais usadas"))
    partes.append(_lista("agente", "Quem trabalhou"))
    partes.append(_lista("cliente", "Por onde"))
    partes.append(_lista("modelo", "Modelos vistos"))
    if r.get("duracao_media_s"):
        partes.append(f"\nDuração média das respostas: {r['duracao_media_s']}s.")
    if r.get("custo_total_usd"):
        partes.append(f"\nCusto somado registrado: US$ {r['custo_total_usd']}.")
    partes.append("\n\n_Tudo isso é local: nada sobe sem você ligar o envio._")
    return "".join(x for x in partes if x)
