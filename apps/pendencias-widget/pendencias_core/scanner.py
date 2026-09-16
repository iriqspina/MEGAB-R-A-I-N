"""Scanner — lê ESTADO.md dos projetos da raiz e alimenta o registro.

Regras medidas na pesquisa (260916):
- Projeto = subpasta direta da raiz (não oculta) com ESTADO.md ou MEGABRAIN/.
- resumo = primeira linha "TL;DR:" (~40 primeiras linhas).
- proximo_passo = primeira linha que casa os padrões medidos nos projetos
  reais ("Próximo passo:", "PRÓXIMO PASSO", "Gate seguinte:", "Pendente:").
- pausado_sugerido = "PAUSADO"/"não retomar"; "TRAVADO_POR: livre" NÃO conta.
- Itens manuais e ativo/pausado do dono são preservados SEMPRE.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from . import registro as reg

LINHAS_RESUMO = 40
LINHAS_PASSO = 80

# toleram markdown: cabeçalhos "##", bullets, negrito "**" no rótulo
_RE_TLDR = re.compile(r"^\s*(?:#{1,6}\s*)?(?:[-*]\s*)?(?:\*\*)?\s*TL;DR\s*(?:\*\*)?\s*[:—-]\s*(.+)$", re.IGNORECASE)
_RE_PASSO = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:[-*]\s*)?(?:\d+[.)]\s*)?(?:\*\*)?"
    r"(?:pr[oó]xim[oa]\s+passo|pr[oó]xima\s+etapa|gate\s+seguinte|pendente|pend[eê]ncia)"
    r"(?:\*\*)?\s*[:—-]\s*(.+)$",
    re.IGNORECASE,
)
_RE_PAUSADO = re.compile(r"(?i)\b(pausad\w*|n[aã]o\s+retomar|logout\s+do\s+projeto)")
_RE_TRAVADO = re.compile(r"(?i)travado[_\s]*por\s*[:=]?\s*(\S.*)$")
_VALORES_LIVRES = {"livre", "nenhum", "-", ""}


def _limpar(texto: str, limite: int = 160) -> str:
    t = texto.strip().strip("*_`").strip()
    return t[: limite - 1] + "…" if len(t) > limite else t


def _ler_estado(caminho: Path) -> str | None:
    try:
        return caminho.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def parse_estado(texto: str | None) -> dict:
    """Extrai resumo, proximo_passo e pausado_sugerido de um ESTADO.md."""
    out = {"resumo": None, "proximo_passo": None, "pausado_sugerido": False}
    if not texto:
        return out
    linhas = texto.splitlines()
    for linha in linhas[:LINHAS_RESUMO]:
        m = _RE_TLDR.match(linha)
        if m:
            out["resumo"] = _limpar(m.group(1))
            break
    for linha in linhas[:LINHAS_PASSO]:
        m = _RE_PASSO.match(linha)
        if m:
            out["proximo_passo"] = _limpar(m.group(1))
            break
    janela = "\n".join(linhas[:60])
    out["pausado_sugerido"] = bool(_RE_PAUSADO.search(janela))
    for m in _RE_TRAVADO.finditer(janela):
        # só conta como LIVRE quando o PRIMEIRO token é livre/nenhum/-;
        # "não livre" e "sessão encerrada em …" continuam travados (gpt2 #10)
        valor = m.group(1).strip()
        primeiro = reg.sem_acento(re.split(r"[\s:;,—–-]", valor, 1)[0]).strip()
        if primeiro not in _VALORES_LIVRES:
            out["pausado_sugerido"] = True
    return out


def _mtz(path: Path) -> str | None:
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat(timespec="seconds")
    except OSError:
        return None


def detectar_projetos(raiz: Path) -> list[dict]:
    """[{nome, caminho, estado_path}] das subpastas diretas que são projeto."""
    achados = []
    if not raiz.is_dir():
        return achados
    for entrada in sorted(raiz.iterdir(), key=lambda p: sem_acento_nome(p.name)):
        if not entrada.is_dir() or entrada.name.startswith((".", "_")):
            continue
        estado = entrada / "ESTADO.md"
        if estado.is_file():
            achados.append({"nome": entrada.name, "caminho": str(entrada), "estado_path": estado})
        elif (entrada / "MEGABRAIN").is_dir():
            achados.append({"nome": entrada.name, "caminho": str(entrada), "estado_path": None})
    return achados


def sem_acento_nome(nome: str) -> str:
    return reg.sem_acento(nome)


def scan(registro: reg.Registro, raiz: Path | None = None) -> dict:
    """Atualiza o registro a partir da raiz; devolve estatísticas do scan."""
    raiz = Path(raiz or registro.dados.get("raiz") or "").expanduser().resolve()
    registro.dados["raiz"] = str(raiz)
    existentes = {reg.sem_acento(p["nome"]): p for p in registro.dados["projetos"]}
    stats = {"projetos": 0, "com_resumo": 0, "com_passo": 0, "pausado_sugerido": 0, "novos": 0}
    for alvo in detectar_projetos(raiz):
        stats["projetos"] += 1
        nome = alvo["nome"]
        p = existentes.get(reg.sem_acento(nome))
        if p is None:
            p = {"nome": nome, "caminho": alvo["caminho"], "ativo": True, "itens": []}
            registro.dados["projetos"].append(p)
            existentes[reg.sem_acento(nome)] = p
            stats["novos"] += 1
        p["caminho"] = alvo["caminho"]
        p["presente"] = True
        if alvo["estado_path"] is not None:
            texto = _ler_estado(alvo["estado_path"])
            info = parse_estado(texto)
            p["resumo"] = info["resumo"]
            p["proximo_passo"] = info["proximo_passo"]
            p["pausado_sugerido"] = info["pausado_sugerido"]
            p["estado_mtime"] = _mtz(alvo["estado_path"])
            p["estado_hash"] = reg.hash_arquivo(alvo["estado_path"]) if texto is not None else None
            stats["com_resumo"] += 1 if info["resumo"] else 0
            stats["com_passo"] += 1 if info["proximo_passo"] else 0
            stats["pausado_sugerido"] += 1 if info["pausado_sugerido"] else 0
        else:
            # sem ESTADO.md: campos derivados ZERADOS (não herdam estado velho)
            p["resumo"] = None
            p["proximo_passo"] = None
            p["pausado_sugerido"] = False
            p.pop("estado_mtime", None)
            p.pop("estado_hash", None)
    for p in registro.dados["projetos"]:
        if p.get("presente"):
            p.pop("presente", None)
        else:
            p["presente"] = False  # não detectado agora: fora do radar, fica no registro
    return stats
