"""Coletor de sessões de IA deste PC, para a peça "sessões" do megabrain-mod.

Lê (nunca escreve) o que cada cliente já guarda no disco:
  - Claude no app: AppData/Roaming/Claude/claude-code-sessions/*/*/local_*.json
    (título, pasta, última atividade) + mtime da conversa em ~/.claude/projects;
  - Claude no terminal: ~/.claude/projects/*/*.jsonl com entrypoint "cli"
    que não pertencem a uma sessão do app (rótulo = 1º pedido);
  - Codex 1 (~/.codex) e Codex 2 (~/.codex-gpt2): sessions/**/rollout-*.jsonl
    + nome da conversa em session_index.jsonl (subagentes ficam de fora);
  - ZCode: ~/.zcode/cli/db/db.sqlite aberto só para leitura (tabela session).

Saída: JSON em ASCII no stdout (`--json`) ou uma lista legível.
Uso: python mb_sessoes.py --json [--horas 12]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# Estado pela idade da última atividade. [HEURÍSTICA]: nenhum cliente expõe
# "rodando agora" no disco; atividade recente é o sinal medível.
AGORA_S = 120
RECENTE_S = 3600
LEITURA_MAX_LINHAS = 400
CAUDA_BYTES = 65536  # quanto do fim da conversa se lê para achar o último registro
# Folga do pré-filtro por data do arquivo: no Windows a data de um arquivo que outro
# programa mantém aberto pode atrasar; a hora real vem do registro (ultimo_registro_ms).
FOLGA_MS = 3600 * 1000


def raiz_home() -> Path:
    """Home do usuário; MB_SESSOES_HOME troca a raiz nos testes."""
    return Path(os.environ.get("MB_SESSOES_HOME") or Path.home())


def estado_por_idade(idade_s: float) -> str:
    if idade_s <= AGORA_S:
        return "agora"
    if idade_s <= RECENTE_S:
        return "recente"
    return "parada"


def pasta_do_projeto(cwd: str) -> str:
    """Nome legível do projeto: pasta raiz antes de .claude/worktrees ou evidence."""
    if not cwd:
        return "—"
    partes = [p for p in re.split(r"[\\/]+", cwd) if p]
    for corte in (".claude", "evidence", ".automations"):
        if corte in partes:
            partes = partes[: partes.index(corte)]
    nome = partes[-1] if partes else cwd
    return re.sub(r"\s+", " ", nome).strip()


def pasta_de_transcricao(cwd: str) -> str:
    """Como o Claude Code nomeia a pasta da conversa: todo caractere fora de [A-Za-z0-9] vira '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", cwd)


def mtime_ms(caminho: Path) -> float | None:
    try:
        return caminho.stat().st_mtime * 1000
    except OSError:
        return None


def iso_para_ms(texto: object) -> float | None:
    if not isinstance(texto, str) or not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).timestamp() * 1000
    except ValueError:
        return None


def ultimo_registro_ms(caminho: Path, tipos: frozenset[str] | None = None) -> float | None:
    """Hora do último registro (campo timestamp) lendo só a cauda do arquivo.

    A data de modificação engana nos dois sentidos: o app do Claude grava linhas
    de ponte sem haver conversa, e no Windows a data de arquivo aberto atrasa.
    `tipos` limita aos registros de conversa (ex.: user/assistant).
    """
    try:
        with caminho.open("rb") as f:
            f.seek(0, os.SEEK_END)
            tamanho = f.tell()
            f.seek(max(0, tamanho - CAUDA_BYTES))
            bloco = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    linhas = bloco.splitlines()
    if tamanho > CAUDA_BYTES and linhas:
        linhas = linhas[1:]  # a primeira linha da cauda pode estar cortada
    for linha in reversed(linhas):
        try:
            d = json.loads(linha)
        except ValueError:
            continue
        if not isinstance(d, dict) or (tipos is not None and d.get("type") not in tipos):
            continue
        ms = iso_para_ms(d.get("timestamp"))
        if ms is not None:
            return ms
    return None


CONVERSA_CLAUDE = frozenset({"user", "assistant"})


def primeira_linha_json(caminho: Path) -> dict:
    with caminho.open("r", encoding="utf-8", errors="replace") as f:
        linha = f.readline()
    return json.loads(linha) if linha.strip() else {}


def limpar_pedido(texto: str) -> str:
    texto = re.sub(r"<([a-zA-Z][\w-]*)[^>]*>[\s\S]*?</\1>", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def primeiro_pedido_claude(caminho: Path) -> tuple[str, str, str]:
    """(1º pedido, cwd, entrypoint) de uma conversa do Claude Code, lendo só o começo."""
    pedido, cwd, entrada = "", "", ""
    with caminho.open("r", encoding="utf-8", errors="replace") as f:
        for i, linha in enumerate(f):
            if i >= LEITURA_MAX_LINHAS:
                break
            try:
                d = json.loads(linha)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            cwd = cwd or str(d.get("cwd") or "")
            entrada = entrada or str(d.get("entrypoint") or "")
            if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain"):
                continue
            conteudo = (d.get("message") or {}).get("content")
            if isinstance(conteudo, list):
                conteudo = " ".join(b.get("text", "") for b in conteudo if isinstance(b, dict) and b.get("type") == "text")
            texto = limpar_pedido(str(conteudo or ""))
            if texto:
                pedido = texto
                break
    return pedido, cwd, entrada


def coletar_claude(home: Path, desde_ms: float) -> tuple[list[dict], set[str]]:
    """Sessões do app (com título) e os ids das conversas que pertencem a elas."""
    raiz = home / "AppData" / "Roaming" / "Claude" / "claude-code-sessions"
    if not raiz.is_dir():
        raise FileNotFoundError("pasta de sessões do app não encontrada")
    sessoes: list[dict] = []
    do_app: set[str] = set()
    for arq in raiz.glob("*/*/local_*.json"):
        try:
            # o app regrava o arquivo a cada atividade: data antiga = sessão fora da janela
            alterado = mtime_ms(arq)
            if alterado is None or alterado < desde_ms - FOLGA_MS:
                continue
            d = json.loads(arq.read_text(encoding="utf-8"))
            if not isinstance(d, dict):
                continue
            cli = str(d.get("cliSessionId") or "")
            if cli:
                do_app.add(cli)
            if d.get("isArchived"):
                continue
            cwd = str(d.get("cwd") or "")
            try:
                ultima = float(d.get("lastActivityAt") or 0)
            except (TypeError, ValueError):
                ultima = 0.0
            if cli and cwd:
                conversa = ultimo_registro_ms(
                    home / ".claude" / "projects" / pasta_de_transcricao(cwd) / f"{cli}.jsonl", CONVERSA_CLAUDE
                )
                if conversa is not None:
                    ultima = max(ultima, conversa)
        except Exception:  # um arquivo esquisito não derruba a fonte
            continue
        if ultima < desde_ms:
            continue
        sessoes.append(
            {
                "fonte": "Claude",
                "id": str(d.get("sessionId") or arq.stem),
                "ids": [x for x in (str(d.get("sessionId") or ""), cli) if x],
                "titulo": str(d.get("title") or "(sem título)"),
                "cwd": cwd,
                "ultima_ms": ultima,
            }
        )
    return sessoes, do_app


def coletar_claude_terminal(home: Path, desde_ms: float, do_app: set[str]) -> list[dict]:
    raiz = home / ".claude" / "projects"
    if not raiz.is_dir():
        raise FileNotFoundError("pasta ~/.claude/projects não encontrada")
    sessoes = []
    for arq in raiz.glob("*/*.jsonl"):
        if arq.stem in do_app:
            continue
        try:
            alterado = mtime_ms(arq)
            if alterado is None or alterado < desde_ms - FOLGA_MS:
                continue
            pedido, cwd, entrada = primeiro_pedido_claude(arq)
            if entrada != "cli" and not entrada.startswith("sdk"):
                continue
            ultima = ultimo_registro_ms(arq, CONVERSA_CLAUDE) or alterado
        except Exception:
            continue
        if ultima < desde_ms:
            continue
        sessoes.append(
            {
                "fonte": "Claude terminal",
                "id": arq.stem,
                "ids": [arq.stem],
                "titulo": (pedido[:80] + "…") if len(pedido) > 80 else (pedido or "(sem pedido)"),
                "cwd": cwd,
                "ultima_ms": ultima,
                "automacao": entrada.startswith("sdk"),  # claude -p e orquestração
            }
        )
    return sessoes


def coletar_codex(base: Path, nome: str, desde_ms: float) -> list[dict]:
    if not base.is_dir():
        raise FileNotFoundError(f"{base.name} não encontrado")
    nomes: dict[str, str] = {}
    indice = base / "session_index.jsonl"
    if indice.is_file():
        for linha in indice.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                d = json.loads(linha)
            except ValueError:
                continue
            if d.get("id") and d.get("thread_name"):
                nomes[str(d["id"])] = str(d["thread_name"])
    sessoes = []
    pasta = base / "sessions"
    for arq in pasta.rglob("rollout-*.jsonl") if pasta.is_dir() else []:
        try:
            alterado = mtime_ms(arq)
            if alterado is None or alterado < desde_ms - FOLGA_MS:
                continue
            meta = primeira_linha_json(arq).get("payload")
            if not isinstance(meta, dict):
                continue
            ultima = ultimo_registro_ms(arq) or alterado
        except Exception:
            continue
        if ultima < desde_ms:
            continue
        if meta.get("parent_thread_id"):  # subagente: conta na conversa-mãe
            continue
        ident = str(meta.get("id") or arq.stem)
        sessoes.append(
            {
                "fonte": nome,
                "id": ident,
                "ids": [ident],
                "titulo": nomes.get(ident, "(sem nome)"),
                "cwd": str(meta.get("cwd") or ""),
                "ultima_ms": ultima,
                "automacao": meta.get("source") == "exec",  # codex exec = trabalhador da orquestração
            }
        )
    return sessoes


def coletar_zcode(home: Path, desde_ms: float) -> list[dict]:
    banco = home / ".zcode" / "cli" / "db" / "db.sqlite"
    if not banco.is_file():
        raise FileNotFoundError("banco do ZCode não encontrado")
    con = sqlite3.connect(banco.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
    try:
        linhas = con.execute(
            "select id, title, directory, time_updated from session "
            "where parent_id is null and time_archived is null and id not like 'sess_subagent%' "
            "and time_updated >= ?",
            (int(desde_ms) - RECENTE_S * 1000,),
        ).fetchall()
    finally:
        con.close()
    rollout = home / ".zcode" / "cli" / "rollout"
    sessoes = []
    for ident, titulo, pasta, atualizado in linhas:
        ultima = float(atualizado or 0)
        io = mtime_ms(rollout / f"model-io-{ident}.jsonl")
        if io is not None:
            ultima = max(ultima, io)
        if ultima < desde_ms:
            continue
        sessoes.append(
            {
                "fonte": "ZCode",
                "id": str(ident),
                "ids": [str(ident)],
                "titulo": str(titulo or "(sem título)"),
                "cwd": str(pasta or ""),
                "ultima_ms": ultima,
            }
        )
    return sessoes


ORDEM = {"agora": 0, "recente": 1, "parada": 2}


def coletar(horas: float = 12, agora_ms: float | None = None) -> dict:
    home = raiz_home()
    agora_ms = agora_ms if agora_ms is not None else time.time() * 1000
    desde = agora_ms - horas * 3600 * 1000
    fontes: dict[str, dict] = {}
    todas: list[dict] = []

    def rodar(nome, fn):
        try:
            itens = fn()
            fontes[nome] = {"ok": True, "n": len(itens)}
            todas.extend(itens)
        except Exception as erro:  # uma fonte quebrada não derruba as outras
            fontes[nome] = {"ok": False, "n": 0, "erro": str(erro)[:160]}

    do_app: set[str] = set()

    def claude_app():
        itens, ids = coletar_claude(home, desde)
        do_app.update(ids)
        return itens

    rodar("Claude", claude_app)
    rodar("Claude terminal", lambda: coletar_claude_terminal(home, desde, do_app))
    rodar("Codex 1", lambda: coletar_codex(home / ".codex", "Codex 1", desde))
    rodar("Codex 2", lambda: coletar_codex(home / ".codex-gpt2", "Codex 2", desde))
    rodar("ZCode", lambda: coletar_zcode(home, desde))

    for s in todas:
        s.setdefault("automacao", False)
        idade = max(0.0, (agora_ms - s["ultima_ms"]) / 1000)
        s["idade_s"] = round(idade)
        s["estado"] = estado_por_idade(idade)
        s["projeto"] = pasta_do_projeto(s["cwd"])
    todas.sort(key=lambda s: (ORDEM[s["estado"]], -s["ultima_ms"]))
    return {"gerado_ms": round(agora_ms), "horas": horas, "fontes": fontes, "sessoes": todas}


def idade_legivel(s: float) -> str:
    if s < 90:
        return "agora"
    if s < 3600:
        return f"há {round(s / 60)} min"
    return f"há {round(s / 3600, 1):g} h".replace(".", ",")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lista as sessões de IA deste PC (só leitura).")
    ap.add_argument("--json", action="store_true", help="saída JSON (ASCII)")
    ap.add_argument("--horas", type=float, default=12, help="janela de atividade (padrão 12)")
    args = ap.parse_args(argv)
    dados = coletar(args.horas)
    if args.json:
        sys.stdout.write(json.dumps(dados, ensure_ascii=True) + "\n")
        return 0
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for s in dados["sessoes"]:
        if s["automacao"]:
            continue
        print(f"[{s['estado']:<7}] {s['fonte']:<15} {s['projeto'][:24]:<24} {s['titulo'][:60]}  ({idade_legivel(s['idade_s'])})")
    auto = [s for s in dados["sessoes"] if s["automacao"]]
    if auto:
        print(f"(+{len(auto)} automações: claude -p e codex exec)")
    for nome, f in dados["fontes"].items():
        if not f["ok"]:
            print(f"(fonte {nome} não lida: {f['erro']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
