def resumo(antes, depois):
    msgs = [f"{k}: {antes.get(k)} -> {depois.get(k)}"
            for k in set(antes) | set(depois) if antes.get(k) != depois.get(k)]
    # BUG plantado: nunca devolve lista vazia — o rotulo "regerado sem mudanca real"
    # de quem chama fica codigo morto, e o teste do reparo pega isso.
    return msgs[:12] or ["mudanca de estado"]
