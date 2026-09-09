#!/usr/bin/env python3
"""
orcamento.py — governador de orcamento da sessao megabrain.

Le os transcripts locais do Claude Code (~/.claude/projects/**/*.jsonl),
calcula o consumo da janela movel de 5h e da janela semanal, e devolve
uma POLITICA: qual modelo e qual effort cada papel usa agora.

Invariante do Modo Maratona:
  duas vagas frontier (orquestrador + adversario) sao SEMPRE reservadas.
  A degradacao acontece nos workers e no talker, nunca nos dois gates.

Uso:
  python3 orcamento.py                 # relatorio humano
  python3 orcamento.py --json          # politica em JSON (para hooks)
  python3 orcamento.py --plano p.json  # injeta a politica no bloco "orcamento" do plano
"""

import json, os, sys, glob, argparse
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------- config

CFG_PATH = os.path.expanduser("~/.megabrain/orcamento.json")

PADRAO = {
    # Ajuste conforme seu plano. Estes numeros sao ORCAMENTO SEU, nao leitura
    # oficial do servidor Anthropic. Calibre na primeira semana com /usage.
    "plano": "max20x",
    "limite_5h_tokens": 8_000_000,      # teto que voce se da por janela de 5h
    "limite_semanal_tokens": 120_000_000,
    "teto_frontier_semanal_pct": 0.45,  # Fable/Opus nao passam disso no semanal
    "reserva_frontier_5h_pct": 0.30,    # 30% da janela fica travada p/ os 2 gates
    "janela_horas": 5,
    "peso": {  # custo relativo por token de saida, normalizado em Haiku=1
        "claude-haiku-4-5": 1.0,
        "claude-sonnet-5": 2.0,
        "claude-opus-5": 5.0,
        "claude-fable-5-1": 10.0
    },
    "transcripts": "~/.claude/projects/**/*.jsonl"
}


def cfg():
    c = dict(PADRAO)
    if os.path.exists(CFG_PATH):
        try:
            c.update(json.load(open(CFG_PATH)))
        except Exception:
            pass
    return c


# ---------------------------------------------------------------- leitura

def eventos(padrao):
    """Extrai (timestamp, modelo, tokens_ponderados) de cada assistant turn."""
    C = cfg()
    out = []
    for f in glob.glob(os.path.expanduser(padrao), recursive=True):
        try:
            with open(f, "r", errors="ignore") as fh:
                for linha in fh:
                    linha = linha.strip()
                    if not linha or linha[0] != "{":
                        continue
                    try:
                        d = json.loads(linha)
                    except Exception:
                        continue
                    msg = d.get("message") or {}
                    u = msg.get("usage") or d.get("usage")
                    if not u:
                        continue
                    ts = d.get("timestamp")
                    if not ts:
                        continue
                    try:
                        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except Exception:
                        continue
                    modelo = msg.get("model") or d.get("model") or "desconhecido"
                    ent = (u.get("input_tokens", 0)
                           + u.get("cache_read_input_tokens", 0) * 0.1
                           + u.get("cache_creation_input_tokens", 0) * 1.25)
                    sai = u.get("output_tokens", 0)
                    peso = C["peso"].get(modelo, 2.0)
                    out.append((t, modelo, (ent * 0.2 + sai) * peso))
        except Exception:
            continue
    out.sort(key=lambda e: e[0])
    return out


def frontier(m):
    return "opus" in m or "fable" in m


def janelas(evs, C):
    agora = datetime.now(timezone.utc)
    jh = C["janela_horas"]

    recentes = [e for e in evs if e[0] > agora - timedelta(hours=jh)]
    if recentes:
        # bloco comeca na hora cheia da primeira msg dentro da janela
        inicio = recentes[0][0].replace(minute=0, second=0, microsecond=0)
    else:
        inicio = agora.replace(minute=0, second=0, microsecond=0)
    fim = inicio + timedelta(hours=jh)
    bloco = [e for e in evs if inicio <= e[0] < fim]

    sem_ini = agora - timedelta(days=7)
    semana = [e for e in evs if e[0] > sem_ini]

    return {
        "bloco_inicio": inicio,
        "bloco_fim": fim,
        "restante_min": max(0, int((fim - agora).total_seconds() // 60)),
        "usado_5h": sum(e[2] for e in bloco),
        "usado_semana": sum(e[2] for e in semana),
        "frontier_semana": sum(e[2] for e in semana if frontier(e[1])),
        "n_5h": len(bloco),
        "agora": agora,
    }


# ---------------------------------------------------------------- politica

def politica(j, C):
    lim5 = C["limite_5h_tokens"]
    limw = C["limite_semanal_tokens"]
    reserva = lim5 * C["reserva_frontier_5h_pct"]

    # orcamento gastavel por workers/talker = teto - reserva dos 2 gates
    gastavel = lim5 - reserva
    queima = j["usado_5h"] / gastavel if gastavel else 1.0

    # ritmo esperado: quanto da janela ja passou
    decorrido = 1 - (j["restante_min"] / (C["janela_horas"] * 60))
    ritmo = queima / max(decorrido, 0.05)   # >1 = gastando acima do ritmo

    sem_pct = j["usado_semana"] / limw if limw else 0
    front_pct = (j["frontier_semana"] / limw) if limw else 0
    front_estourou = front_pct > C["teto_frontier_semanal_pct"]

    if queima >= 0.85 or sem_pct >= 0.92:
        fase = "vermelho"
    elif queima >= 0.55 or ritmo >= 1.4 or sem_pct >= 0.75:
        fase = "amarelo"
    else:
        fase = "verde"

    # ---- papeis. os 2 frontier NUNCA saem, so baixam de effort/modelo.
    if fase == "verde":
        p = {
            "orquestrador": ("claude-opus-5", "high"),
            "adversario":   ("codex:gpt-5.6-sol", "xhigh"),
            "talker":       ("claude-sonnet-5", "medium"),
            "worker":       ("claude-haiku-4-5", "medium"),
            "revisor":      ("codex:gpt-5.6-sol", "high"),
            "fanout_max": 4,
            "rodadas_review_max": 2,
        }
    elif fase == "amarelo":
        p = {
            "orquestrador": ("claude-opus-5", "medium"),
            "adversario":   ("codex:gpt-5.6-sol", "high"),
            "talker":       ("claude-sonnet-5", "low"),
            "worker":       ("claude-haiku-4-5", "low"),
            "revisor":      ("codex:gpt-5.6-terra", "medium"),
            "fanout_max": 2,
            "rodadas_review_max": 1,
        }
    else:
        p = {
            "orquestrador": ("claude-opus-5", "medium"),
            "adversario":   ("codex:gpt-5.6-sol", "high"),
            "talker":       ("claude-haiku-4-5", "low"),
            "worker":       ("codex:gpt-5.6-luna", "low"),
            "revisor":      ("codex:gpt-5.6-terra", "low"),
            "fanout_max": 1,
            "rodadas_review_max": 1,
        }

    if front_estourou:
        # Fable fora; Opus segura o papel. Adversario migra 100% pro Codex,
        # que come outra bolsa de quota — e por isso o par e cross-vendor.
        p["orquestrador"] = ("claude-opus-5", p["orquestrador"][1])
        p["_nota_frontier"] = "teto frontier semanal atingido: Fable bloqueado, adversario so no Codex"

    alertas = []
    if ritmo >= 1.4:
        alertas.append(f"ritmo {ritmo:.1f}x acima do linear — a janela acaba antes das {C['janela_horas']}h")
    if front_estourou:
        alertas.append(f"frontier em {front_pct:.0%} do semanal (teto {C['teto_frontier_semanal_pct']:.0%})")
    if sem_pct >= 0.75:
        alertas.append(f"semanal em {sem_pct:.0%}")
    if j["restante_min"] < 30 and queima < 0.4:
        alertas.append("janela quase virando com orcamento sobrando — bom momento pra tarefa cara")

    return {
        "fase": fase,
        "politica_id": f"{fase}-{j['agora'].strftime('%Y%m%dT%H%M')}",
        "gerado_em": j["agora"].isoformat(),
        "papeis": {k: (list(v) if isinstance(v, tuple) else v) for k, v in p.items()},
        "metricas": {
            "queima_5h": round(queima, 3),
            "ritmo": round(ritmo, 2),
            "restante_min": j["restante_min"],
            "renova_5h_em": j["bloco_fim"].astimezone().strftime("%H:%M"),
            "semanal_pct": round(sem_pct, 3),
            "frontier_semanal_pct": round(front_pct, 3),
            "renova_semanal_em": (j["agora"] + timedelta(days=7)).astimezone().strftime("%d/%m %H:%M"),
            "turnos_na_janela": j["n_5h"],
        },
        "alertas": alertas,
    }


# ---------------------------------------------------------------- saida

def humano(pol):
    m = pol["metricas"]
    icone = {"verde": "OK", "amarelo": "ATENCAO", "vermelho": "CRITICO"}[pol["fase"]]
    L = []
    L.append(f"[{icone}] fase {pol['fase']}  |  janela 5h: {m['queima_5h']:.0%} usada, "
             f"{m['restante_min']}min restantes (renova {m['renova_5h_em']})")
    L.append(f"       semanal: {m['semanal_pct']:.0%}  |  frontier: {m['frontier_semanal_pct']:.0%}  "
             f"|  renova {m['renova_semanal_em']}")
    L.append("")
    for papel in ["orquestrador", "adversario", "talker", "worker", "revisor"]:
        mod, eff = pol["papeis"][papel]
        L.append(f"  {papel:<14} {mod:<24} effort={eff}")
    L.append(f"  {'fan-out max':<14} {pol['papeis']['fanout_max']} workers em paralelo")
    L.append(f"  {'review max':<14} {pol['papeis']['rodadas_review_max']} rodada(s)")
    for a in pol["alertas"]:
        L.append(f"  ! {a}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--plano")
    a = ap.parse_args()

    C = cfg()
    evs = eventos(C["transcripts"])
    if not evs:
        print("nenhum transcript encontrado em " + C["transcripts"], file=sys.stderr)
    pol = politica(janelas(evs, C), C)

    if a.plano:
        d = json.load(open(a.plano))
        d["orcamento"] = {"fase": pol["fase"], "politica_id": pol["politica_id"],
                          "gerado_em": pol["gerado_em"]}
        json.dump(d, open(a.plano, "w"), ensure_ascii=False, indent=2)

    print(json.dumps(pol, ensure_ascii=False, indent=2) if a.json else humano(pol))


if __name__ == "__main__":
    main()
