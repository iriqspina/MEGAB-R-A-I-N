#!/usr/bin/env python3
"""Confere pricing.json contra a lista viva de modelos de cada provedor.

O roteador escolhe modelo por preço. Se a tabela envelhece, ele passa a
"economizar" com número inventado — e ninguém percebe, porque o app continua
respondendo. Este script é a garantia de script que o markdown não dá.

    python mb-modelos.py --listar      # tabela ordenada por custo
    python mb-modelos.py --conferir    # bate contra a API de cada provedor

Sai com código 1 quando a tabela está vencida ou diverge do provedor.
"""

import argparse
import sys

import precos
from config import carregar_config
from providers.base import http_get_json


def listar() -> int:
    cfg = precos.carregar()
    print(f"pricing.json verificado em {cfg.get('verificado_em')} "
          f"(há {precos.idade_em_dias()} dias)\n")
    print(f"{'provider':<10} {'modelo':<26} {'classe':<9} {'in':>7} {'out':>7} {'fonte':<10}")
    print("-" * 76)
    for m in sorted(precos.modelos(), key=precos.custo_ponderado):
        print(f"{m['provider']:<10} {m['api_id']:<26} {m['classe']:<9} "
              f"{m['in']:>7.2f} {m['out']:>7.2f} {m.get('fonte', '?'):<10}")

    aviso = precos.aviso_validade()
    if aviso:
        print(f"\nAVISO: {aviso}")
        return 1
    return 0


def _modelos_vivos(provider_id: str, info: dict) -> list[str] | None:
    """IDs que o provedor realmente oferece agora, ou None se não deu para saber."""
    base = (info.get("base_url") or "").rstrip("/")
    key = info.get("key")

    if provider_id in ("openai", "moonshot"):
        if not key:
            return None
        data = http_get_json(f"{base}/models", {"Authorization": f"Bearer {key}"}, timeout=20)
        if "erro" in data:
            return None
        return [m.get("id", "") for m in data.get("data", [])]

    if provider_id == "gemini":
        if not key:
            return None
        data = http_get_json(f"{base}/v1beta/models?key={key}", {}, timeout=20)
        if "erro" in data:
            return None
        return [m.get("name", "").removeprefix("models/") for m in data.get("models", [])]

    if provider_id == "ollama":
        data = http_get_json(f"{base}/api/tags", {}, timeout=10)
        if "erro" in data:
            return None
        return [m.get("name", "") for m in data.get("models", [])]

    # A Anthropic não expõe listagem pública de modelos sem endpoint dedicado;
    # confira em https://platform.claude.com/docs/en/about-claude/pricing
    return None


def conferir() -> int:
    cfg = carregar_config()
    problemas = 0

    aviso = precos.aviso_validade()
    if aviso:
        print(f"AVISO: {aviso}")
        problemas += 1

    for provider_id, info in cfg["providers"].items():
        if provider_id == "mock":
            continue
        declarados = [m["api_id"] for m in precos.modelos() if m["provider"] == provider_id]
        vivos = _modelos_vivos(provider_id, info)

        if vivos is None:
            motivo = "sem key configurada" if not info.get("key") and not info.get("local") else "não consultável"
            print(f"[?] {provider_id:<10} pulado ({motivo}) — {len(declarados)} modelo(s) na tabela")
            continue

        sumidos = [m for m in declarados if m not in vivos]
        if sumidos:
            problemas += 1
            print(f"[X] {provider_id:<10} na tabela mas o provedor não oferece: {', '.join(sumidos)}")
        else:
            print(f"[ok] {provider_id:<10} {len(declarados)} modelo(s) conferem com a API")

    if problemas:
        print(f"\n{problemas} problema(s). Edite pricing.json e atualize 'verificado_em'.")
        return 1
    print("\npricing.json confere com os provedores consultáveis.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Confere a tabela de modelos e preços")
    p.add_argument("--listar", action="store_true", help="imprime a tabela ordenada por custo")
    p.add_argument("--conferir", action="store_true", help="bate a tabela contra a API dos provedores")
    args = p.parse_args()

    if args.conferir:
        return conferir()
    return listar()


if __name__ == "__main__":
    sys.exit(main())
