#!/usr/bin/env python3
"""Modo orquestrador do GerenteNeuron — diálogo entre IAs (Claude, Kimi,
OpenAI, Gemini, Ollama) com custo estimado e saída em Markdown + HTML.

Fundido do antigo bin/mb-orquestrador-ia.py (decisão do <USUARIO>, 260819:
"fundir no GerenteNeuron", não aposentar). O que mudou na fusão:
- vive dentro do app: usa config/providers/precos direto, sem sys.path hack;
- NENHUM modelo hardcoded: defaults vêm de pricing.json (que tem carimbo
  `verificado_em` e aviso de validade) — o hardcode era o motivo da fusão;
- corrigido: o provedor openai ignorava argumento e chamava um modelo fixo.

Uso:
    python gerenteneuron/orquestrador.py --prompt contexto.txt --rodadas 3 --saida dialogo.html
(o antigo bin/mb-orquestrador-ia.py continua funcionando como atalho)
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Permite rodar de qualquer cwd: o pacote é o diretório deste arquivo.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import precos
from providers.anthropic import AnthropicProvider
from providers.moonshot import MoonshotProvider
from providers.openai import OpenAIProvider
from providers.gemini import GeminiProvider
from providers.ollama import OllamaProvider

PROVIDER_DO_PAPEL = {
    "claude": "anthropic",
    "kimi": "moonshot",
    "openai": "openai",
    "gemini": "gemini",
    "ollama": "ollama",
}


def _default_modelo(papel: str) -> str | None:
    """Primeiro modelo do provider em pricing.json — nunca hardcoded aqui."""
    try:
        por_provider = precos.por_provider()
        lista = por_provider.get(PROVIDER_DO_PAPEL.get(papel, papel), [])
        if lista:
            return lista[0].get("api_id")
    except Exception:
        pass
    return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Orquestra diálogo entre IAs (modo do GerenteNeuron)")
    parser.add_argument("--prompt", required=True, help="Arquivo .txt com o prompt inicial")
    parser.add_argument("--rodadas", type=int, default=3, help="Número de rodadas (pares de mensagens)")
    parser.add_argument("--saida", default="dialogo-ia.html", help="Arquivo HTML de saída")
    parser.add_argument("--contexto", help="Contexto adicional (arquivo) anexado ao prompt inicial")
    parser.add_argument("--modelo-claude", default=None,
                        help="Modelo Anthropic (default: primeiro do pricing.json)")
    parser.add_argument("--modelo-kimi", default=None,
                        help="Modelo Moonshot/Kimi (default: primeiro do pricing.json)")
    parser.add_argument("--modelo-openai", default=None,
                        help="Modelo OpenAI (default: primeiro do pricing.json)")
    parser.add_argument("--modelo-gemini", default=None,
                        help="Modelo Google Gemini (default: primeiro do pricing.json)")
    parser.add_argument("--modelo-ollama", default=None,
                        help="Modelo Ollama local (default: primeiro do pricing.json)")
    parser.add_argument("--primeiro", choices=["claude", "kimi"], default="claude",
                        help="Quem começa respondendo ao prompt inicial")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Timeout em segundos para chamadas de API")
    parser.add_argument("--max-tokens", type=int, default=8192,
                        help="Máximo de tokens de saída por chamada")
    parser.add_argument("--provedores", default="claude,kimi",
                        help="Provedores a usar: claude,kimi,openai,gemini,ollama (separados por vírgula)")
    parser.add_argument("--max-historico", type=int, default=1200,
                        help="Máximo de caracteres da resposta anterior a repassar no histórico (protege free tiers)")
    return parser.parse_args()


def _ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


def _agora_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _slug_data() -> str:
    return datetime.now(timezone.utc).strftime("%y%m%d-%H%M%S")


def _custo_total(turnos: list[dict]) -> float:
    return sum(t.get("custo_estimado_usd", 0.0) for t in turnos)


def _html_escape(texto: str) -> str:
    return (texto
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _markdown_para_html(texto: str) -> str:
    """Conversão mínima de Markdown para HTML (listas, negrito, itálico, código)."""
    linhas = texto.splitlines()
    html = []
    em_lista = False
    for linha in linhas:
        if linha.startswith("```"):
            if em_lista:
                html.append("</ul>")
                em_lista = False
            html.append("<pre><code>")
            continue
        if em_lista and not linha.strip().startswith(("- ", "* ", "1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. ", "9. ")):
            html.append("</ul>")
            em_lista = False
        if linha.strip().startswith(("- ", "* ")):
            if not em_lista:
                html.append("<ul>")
                em_lista = True
            item = _html_escape(linha.strip()[2:])
            html.append(f"<li>{item}</li>")
        elif linha.strip().startswith(("1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. ", "9. ")):
            if not em_lista:
                html.append("<ol>")
                em_lista = True
            item = _html_escape(linha.strip()[3:])
            html.append(f"<li>{item}</li>")
        else:
            html.append(f"<p>{_html_escape(linha)}</p>")
    if em_lista:
        html.append("</ul>")
    saida = "\n".join(html)
    saida = saida.replace("**", "<b>", 1)
    while "**" in saida:
        saida = saida.replace("**", "</b>", 1)
        if "**" in saida:
            saida = saida.replace("**", "<b>", 1)
    saida = saida.replace("`", "<code>", 1)
    while "`" in saida:
        saida = saida.replace("`", "</code>", 1)
        if "`" in saida:
            saida = saida.replace("`", "<code>", 1)
    return saida


def _salvar_html(caminho: Path, prompt_inicial: str, turnos: list[dict]) -> None:
    css = """
    :root { --bg:#0f1115; --surface:#181b21; --surface-2:#20242c; --text:#e6e6e6; --muted:#9aa0a6; --claude:#d97757; --kimi:#4a9eff; --border:#2f333b; }
    * { box-sizing: border-box; }
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 2rem 1rem; line-height: 1.6; }
    .container { max-width: 900px; margin: 0 auto; }
    header { border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 2rem; }
    h1 { font-size: 1.5rem; margin: 0 0 .25rem; }
    .meta { color: var(--muted); font-size: .875rem; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; margin-bottom: 1.25rem; }
    .card.kimi { border-left: 4px solid var(--kimi); }
    .card.claude { border-left: 4px solid var(--claude); }
    .card.system { background: var(--surface-2); border-left: 4px solid var(--muted); }
    .badge { display: inline-block; padding: .15rem .5rem; border-radius: 999px; font-size: .75rem; font-weight: 600; text-transform: uppercase; margin-bottom: .75rem; }
    .badge.claude { background: rgba(217,119,87,.15); color: var(--claude); }
    .badge.kimi { background: rgba(74,158,255,.15); color: var(--kimi); }
    .badge.system { background: rgba(154,160,166,.15); color: var(--muted); }
    pre { background: #000; padding: 1rem; border-radius: 8px; overflow-x: auto; font-size: .875rem; }
    code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    p code { background: var(--surface-2); padding: .1rem .3rem; border-radius: 4px; }
    footer { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: .875rem; }
    """
    html = [f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Diálogo IA — {_slug_data()}</title><style>{css}</style></head><body><div class="container"><header><h1>Diálogo entre IAs</h1><div class="meta">Iniciado em {_agora_iso()} · {_len_tokens_estimado(prompt_inicial)} tokens no prompt inicial</div></header>"""]

    html.append(f'<div class="card system"><span class="badge system">Prompt inicial</span><div>{_markdown_para_html(prompt_inicial)}</div></div>')

    for turno in turnos:
        quem = turno["quem"]
        cor = "claude" if quem == "claude" else "kimi"
        resposta = turno["resposta"]
        modelo = turno.get("modelo", "?")
        custo = turno.get("custo_estimado_usd", 0.0)
        tokens = turno.get("tokens_entrada", 0) + turno.get("tokens_saida", 0)
        html.append(f'<div class="card {cor}"><span class="badge {cor}">{quem.upper()} · {modelo}</span>')
        html.append(f'<div class="meta">tokens {tokens} · custo estimado ${custo:.6f}</div>')
        html.append(f'<div>{_markdown_para_html(resposta)}</div></div>')

    html.append(f'<footer>Total estimado: ${_custo_total(turnos):.6f} USD · {len(turnos)} turnos · gerado por gerenteneuron/orquestrador.py</footer></div></body></html>')
    caminho.write_text("\n".join(html), encoding="utf-8")


def _salvar_markdown(caminho: Path, prompt_inicial: str, turnos: list[dict]) -> None:
    linhas = [f"# Diálogo entre IAs\n\n**Iniciado:** {_agora_iso()}\n**Prompt inicial:** {_len_tokens_estimado(prompt_inicial)} tokens estimados\n"]
    linhas.append("## Prompt inicial\n\n" + prompt_inicial + "\n")
    for i, turno in enumerate(turnos, 1):
        quem = turno["quem"].upper()
        linhas.append(f"## Turno {i}: {quem}\n")
        linhas.append(f"- Modelo: {turno.get('modelo', '?')}")
        linhas.append(f"- Tokens: {turno.get('tokens_entrada', 0)} in / {turno.get('tokens_saida', 0)} out")
        linhas.append(f"- Custo estimado: ${turno.get('custo_estimado_usd', 0.0):.6f} USD\n")
        linhas.append(turno["resposta"] + "\n")
    linhas.append(f"\n---\n**Total estimado:** ${_custo_total(turnos):.6f} USD · {len(turnos)} turnos")
    caminho.write_text("\n".join(linhas), encoding="utf-8")


def _len_tokens_estimado(texto: str) -> int:
    # Heurística simples: ~1.6 token/palavra em português.
    return max(1, int(len(texto.split()) * 1.6))


def _truncar_historico(historico: list[dict], max_caracteres: int) -> list[dict]:
    """Trunca mensagens de assistant no histórico para não estourar limites de free tiers."""
    if max_caracteres <= 0:
        return historico
    novo = []
    for h in historico:
        content = h.get("content", "")
        if h.get("role") == "assistant" and len(content) > max_caracteres:
            content = content[:max_caracteres].rsplit(" ", 1)[0] + "… [truncado]"
        novo.append({"role": h.get("role"), "content": content})
    return novo


def main() -> int:
    args = _parse_args()
    prompt_path = Path(args.prompt)
    if not prompt_path.exists():
        print(f"Prompt não encontrado: {prompt_path}", file=sys.stderr)
        return 1

    aviso = precos.aviso_validade()
    if aviso:
        print(f"AVISO pricing.json: {aviso}", file=sys.stderr)

    provedores = [p.strip().lower() for p in args.provedores.split(",") if p.strip()]
    if not provedores:
        print("--provedores não pode ser vazio", file=sys.stderr)
        return 1

    # Resolve modelos: argumento > pricing.json. Sem os dois, erro claro.
    modelos = {}
    argumentos = {
        "claude": args.modelo_claude, "kimi": args.modelo_kimi,
        "openai": args.modelo_openai, "gemini": args.modelo_gemini,
        "ollama": args.modelo_ollama,
    }
    for papel in provedores:
        modelos[papel] = argumentos.get(papel) or _default_modelo(papel)
        if not modelos[papel]:
            print(f"Sem modelo pra '{papel}': passe --modelo-{papel} ou cadastre o provider "
                  "em gerenteneuron/pricing.json", file=sys.stderr)
            return 1

    cfg = config.carregar_config()
    anthropic_cfg = cfg["providers"]["anthropic"]
    moonshot_cfg = cfg["providers"]["moonshot"]
    openai_cfg = cfg["providers"]["openai"]
    gemini_cfg = cfg["providers"]["gemini"]
    ollama_cfg = cfg["providers"]["ollama"]

    if "claude" in provedores and not anthropic_cfg.get("key"):
        print("ANTHROPIC_API_KEY não configurada no .env/cofre", file=sys.stderr)
        return 1
    if "kimi" in provedores and not moonshot_cfg.get("key"):
        print("MOONSHOT_API_KEY não configurada no .env/cofre", file=sys.stderr)
        return 1
    if "openai" in provedores and not openai_cfg.get("key"):
        print("OPENAI_API_KEY não configurada no .env/cofre", file=sys.stderr)
        return 1
    if "gemini" in provedores and not gemini_cfg.get("key"):
        print("GEMINI_API_KEY não configurada no .env/cofre", file=sys.stderr)
        return 1

    prompt_inicial = _ler(prompt_path)
    if args.contexto:
        contexto_path = Path(args.contexto)
        if contexto_path.exists():
            prompt_inicial += "\n\n---\n\n" + _ler(contexto_path)

    saida = Path(args.saida)
    md_saida = saida.with_suffix(".md")

    historico = [{"role": "user", "content": prompt_inicial}]
    turnos = []
    msg_continuacao = "Responda à mensagem anterior continuando o diálogo em português, direto e técnico."

    def _mensagem_atual() -> str:
        # A primeira chamada usa o prompt inicial no histórico; as seguintes precisam
        # de uma mensagem user não-vazia para APIs como Gemini que rejeitam histórico
        # terminando em model/assistant.
        return "" if len(historico) == 1 else msg_continuacao

    ordem_base = ["claude", "kimi"] if args.primeiro == "claude" else ["kimi", "claude"]
    ordem = [p for p in ordem_base if p in provedores]
    ordem += [p for p in provedores if p not in ordem]
    if not ordem:
        ordem = provedores

    envio = {
        "claude": (AnthropicProvider, anthropic_cfg),
        "kimi": (MoonshotProvider, moonshot_cfg),
        "openai": (OpenAIProvider, openai_cfg),
        "gemini": (GeminiProvider, gemini_cfg),
        "ollama": (OllamaProvider, ollama_cfg),
    }

    for rodada in range(args.rodadas):
        for quem in ordem:
            if quem not in envio:
                print(f"Provedor desconhecido: {quem}", file=sys.stderr)
                continue
            provider, provider_cfg = envio[quem]
            modelo = modelos[quem]
            print(f"[rodada {rodada+1}/{args.rodadas}] Chamando {quem} ({modelo})...")
            kwargs = dict(
                mensagem=_mensagem_atual(),
                config=provider_cfg,
                historico=_truncar_historico(historico, args.max_historico),
                modelo=modelo,
            )
            if quem != "gemini":
                kwargs.update(timeout=args.timeout, max_tokens=args.max_tokens)
            resultado = provider.send(**kwargs)

            if resultado.get("erro"):
                print(f"ERRO em {quem}: {resultado['erro']}", file=sys.stderr)
                _salvar_html(saida, prompt_inicial, turnos)
                _salvar_markdown(md_saida, prompt_inicial, turnos)
                return 1

            texto = resultado["resposta"]
            turnos.append({
                "quem": quem,
                "resposta": texto,
                "modelo": resultado.get("modelo_usado", modelo),
                "tokens_entrada": resultado.get("tokens_entrada", 0),
                "tokens_saida": resultado.get("tokens_saida", 0),
                "custo_estimado_usd": resultado.get("custo_estimado_usd", 0.0),
            })
            historico.append({"role": "assistant", "content": f"[{quem.upper()}] {texto}"})
            time.sleep(0.5)

    _salvar_html(saida, prompt_inicial, turnos)
    _salvar_markdown(md_saida, prompt_inicial, turnos)
    print("\nSalvo em:")
    print(f"  HTML: {saida.resolve()}")
    print(f"  MD:   {md_saida.resolve()}")
    print(f"  Custo total estimado: ${_custo_total(turnos):.6f} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
