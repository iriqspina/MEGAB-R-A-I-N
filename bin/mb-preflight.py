#!/usr/bin/env python3
"""
mb-preflight.py — abertura de sessão do megabrain em 1 comando. v6.1 (260821)

É o script que a skill `mb-abertura` documentava desde 260817 e que nunca tinha
sido escrito (confirmado ausente em 260821). Quatro cheques, um veredito, um
código de saída:

  git     o repo local está atrás do origin/main conhecido? árvore suja?
          commits locais sem push? (NÃO consulta a rede — é o que o git sabe;
          passe --fetch pra tentar `git fetch` antes, com timeout)
  skills  a SKILL.md do megabrain instalada em cada agente tem o mesmo hash da
          fonte na central? (a instalada é a que roda — Gate 5)
  fatos   algum JSON com `verificado_em` venceu a `validade_dias` (default 30)?
  legado  sobrou `metaprotocolo` / `metaclaude` fora dos lugares onde o nome
          antigo é reconhecimento deliberado (hook, registrar-licao, histórico)?
  crlf    algum `.cmd`/`.bat` da central está com quebra de linha Unix (LF)?
          O cmd.exe lê batch por deslocamento de byte assumindo CRLF: com LF
          ele desalinha e come as primeiras letras das linhas — o script não
          dá erro, ele executa outra coisa. Em 260824 o sincronizar-projetos
          ficou 20h imprimindo 18 "OK" e copiando zero byte por causa disso.

Saída 0 = pode começar. Saída 2 = pendência (o veredito diz qual).
Cache: <repo>/.megabrain/preflight.json, validade 8 h (--forcar ignora,
--ttl muda). --agentes inclui ~/.claude, ~/.kimi-code, ~/.gemini, ~/.codex.

Uso:
    python bin/mb-preflight.py --repo "<central ou repo-local>"
    python bin/mb-preflight.py --repo "<...>" --agentes --forcar
    python bin/mb-preflight.py --repo "<...>" --fetch
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import mb_utils as u
import mb_trava as trava

u.utf8_console()

TEXTO = {".md", ".txt", ".py", ".cmd", ".js", ".mjs", ".json", ".yaml", ".yml", ".html", ".css"}
# 260825 (decisão 260825m): esta lista casa contra NOME DE PASTA no os.walk,
# então entrada composta nunca casa e vira no-op silencioso. "_github/export"
# estava aqui desde sempre e os cheques varriam o export inteiro à toa — é a
# 3ª vez que a mesma família de bug aparece (relatório, cópia de central,
# preflight). O assert abaixo mata a 4ª na hora do import.
# "90_arquivo" entrou junto: é história congelada, e um manifesto de migração
# arquivada estava fazendo o preflight sair com exit 2 toda abertura de sessão.
PULAR_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mb-backup",
              ".mb-aspirador", ".dna-backup", ".megabrain", ".mb-log", ".mb-lock",
              "_to_delete", "99_to_delete",
              "260810_backup-raiz-perfil", "260810_variantes", "_github", "90_arquivo",
              # 260825: dados/ é DERIVADO — `mb-estado.py` monta o índice a
              # partir dos .md, então qualquer resíduo ali já foi contado na
              # fonte. Acusar o derivado é contar o mesmo texto duas vezes e
              # treinar a ignorar o gate (lição 260822).
              "dados",
              ".orquestrador"}  # diálogos antigos do orquestrador: artefato de execução
assert not any("/" in d or "\\" in d for d in PULAR_DIRS), (
    "PULAR_DIRS casa por nome de pasta: entrada composta nunca casa")
# Onde o nome antigo é reconhecimento deliberado (ler arquivo legado, registrar
# a decisão de renomear, histórico). Fora daqui, é resíduo.
LEGADO_PERMITIDO = (
    "session-start.js", "licoes-kimi", "registrar-licao/SKILL.md", "mb-abertura",
    "DECISOES.md", "licoes-megabrain.md", "VERSAO.txt", "pendencia-nome-metaprotocolo",
    "mb-preflight.py", "mb-contexto.py", "LICOES.md", "CHECKLIST-ABERTURA.md",
    "260816_AUDITORIA", "260821_nota.md", "HANDOFF.md", "ESTADO.md",
    "mb-build-plugin-claude.py", "plugin-megabrain-claude/README.md",
    # derivados que embutem o TEXTO das lições/decisões (regenerados, não fonte)
    "PAINEL-MEGABRAIN.html", "RELATORIO-AGENTES.html", "RELATORIO-VIVO.html",
    # v6.6: o relatório passou a agregar os .md da instância (DECISOES, HANDOFF,
    # lições) — logo ele HERDA as menções históricas que já são permitidas na
    # fonte. Varrer o derivado por resíduo é acusar duas vezes o mesmo texto.
    "00_painel/", "relatorios-antigos/", "RELATORIO.html", "CATALOGO-VISUAL.html",
    "indice-licoes.json", "licoes-recorrencia.json",
    # congelados/backups: história, não fonte viva
    "PIPELINE.md", "260805_licoes-backup", "260811_prompt-claude-handoff", "mb-patch-v5.py",
    "260804_licoes-inicial.md",  # seed do plugin Kimi: texto de lições de 260804 (histórico)
)
PADRAO_LEGADO = re.compile(r"metaprotocolo|metaclaude", re.IGNORECASE)

# --- crlf -------------------------------------------------------------------
# Batch é sensível a quebra de linha e o sintoma NÃO é erro de sintaxe: o
# cmd.exe engole as primeiras letras da linha seguinte ('setlocal' vira
# 'tlocal', 'python' vira 'thon') e segue executando. Variável não definida,
# robocopy com origem vazia, e o `if errorlevel` do fim mede outra coisa —
# 18 "OK" com zero byte copiado. A lição existe desde 260819 e reapareceu em
# 260824 e 260825; markdown pediu três vezes e não garantiu nenhuma.
EXT_BATCH = {".cmd", ".bat"}
# Espelho gerado, arquivo morto e backup não são fonte: quem conserta é o
# gerador. Pedaço ISOLADO de caminho — entrada composta nunca casaria (a
# própria armadilha que fez cada doc entrar 3× no relatório, decisão 260825b).
PULAR_CRLF = {"_github", "90_arquivo", "99_to_delete", ".mb-backup", ".mb-aspirador",
              ".dna-backup", ".git", "__pycache__", ".megabrain", ".mb-lock", "node_modules",
              ".venv", "venv", "MEGABRAIN"}
PADRAO_LF_SOLTO = re.compile(rb"(?<!\r)\n")


def h(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    except OSError:
        return None


def git(repo: Path, *args: str, timeout: int = 8) -> str | None:
    try:
        r = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args],
                           capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def achar_repo(base: Path) -> Path | None:
    for cand in (base, base / "_github/repo-local"):
        if (cand / ".git").exists():
            return cand
    return None


def achar_central(base: Path) -> Path:
    """--repo pode ser a central ou o repo-local dentro dela."""
    if (u.achar(base, "VERSAO.txt")).is_file() and (base / "bin").is_dir() and (base / "_github/repo-local").is_dir():
        return base
    if base.name == "_github/repo-local" and (u.achar(base.parent, "VERSAO.txt")).is_file():
        return base.parent
    return base


def cheque_git(repo: Path | None, fetch: bool) -> tuple[bool, str]:
    if not repo:
        return True, "sem repositório git (nada a comparar)"
    if fetch:
        ok = git(repo, "fetch", "--quiet", "origin", timeout=25)
        fetch_txt = "fetch ok" if ok is not None else "fetch FALHOU (rede/proxy) — comparando com o origin/main conhecido"
    else:
        fetch_txt = "sem fetch (origin/main conhecido localmente)"
    head = (git(repo, "rev-parse", "--short", "HEAD") or "?")
    atras = git(repo, "rev-list", "--count", "HEAD..origin/main")
    frente = git(repo, "rev-list", "--count", "origin/main..HEAD")
    suja = git(repo, "status", "--porcelain")
    problemas = []
    if atras and atras.isdigit() and int(atras) > 0:
        problemas.append(f"{atras} commit(s) ATRÁS do origin/main — git pull antes de editar")
    if frente and frente.isdigit() and int(frente) > 0:
        problemas.append(f"{frente} commit(s) locais SEM PUSH")
    if suja:
        problemas.append(f"árvore suja ({len(suja.splitlines())} arquivo(s))")
    txt = f"HEAD {head} · {fetch_txt}" + (" · " + " · ".join(problemas) if problemas else " · limpo e alinhado")
    # atrás do remoto bloqueia; push pendente e árvore suja só avisam
    bloqueia = any("ATRÁS" in p for p in problemas)
    return not bloqueia, txt


def locais_skill(agentes: bool) -> list[Path]:
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    locais = [
        home / ".claude/skills/megabrain/SKILL.md",
        home / ".claude/plugins/synced/megabrain/skills/megabrain/SKILL.md",
        home / ".kimi-code/plugins/managed/megabrain/skills/megabrain/SKILL.md",
        home / "AppData/Roaming/kimi-desktop/daimon-share/daimon/skills/megabrain/SKILL.md",
    ]
    if agentes:
        locais += [home / ".gemini/skills/megabrain/SKILL.md", home / ".codex/skills/megabrain/SKILL.md"]
    return locais


def cheque_skills(central: Path, agentes: bool) -> tuple[bool, str]:
    fontes = {p: h(p) for p in (u.achar(central, "skills/megabrain/SKILL.md"),
                                u.achar(central, "plugin-megabrain-claude/skills/megabrain/SKILL.md")) if p.is_file()}
    if not fontes:
        return False, "fonte skills/megabrain/SKILL.md não encontrada na central"
    aceitos = set(fontes.values())
    achados, divergentes = [], []
    for p in locais_skill(agentes):
        if not p.is_file():
            continue
        hp = h(p)
        achados.append(p)
        if hp not in aceitos:
            divergentes.append(f"{p} ({hp})")
    if not achados:
        return True, "nenhuma cópia instalada encontrada nos caminhos conhecidos (nada a comparar)"
    if divergentes:
        return False, (f"{len(divergentes)}/{len(achados)} cópia(s) instalada(s) DIVERGEM da fonte "
                       f"(a instalada é a que roda): " + "; ".join(divergentes))
    return True, f"{len(achados)} cópia(s) instalada(s) com hash igual à fonte"


def iter_texto(raiz: Path):
    for dirpath, dirs, files in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in PULAR_DIRS]
        for f in files:
            p = Path(dirpath) / f
            if p.suffix.lower() in TEXTO:
                yield p


def cheque_fatos(raiz: Path) -> tuple[bool, str]:
    hoje = dt.date.today()
    vencidos, total = [], 0
    for p in iter_texto(raiz):
        if p.suffix.lower() != ".json":
            continue
        txt = u.safe_read_text(p)
        if not txt or "verificado_em" not in txt:
            continue
        try:
            d = json.loads(txt)
        except ValueError:
            continue
        itens = d if isinstance(d, list) else [d]
        for item in itens:
            if not isinstance(item, dict) or "verificado_em" not in item:
                continue
            total += 1
            try:
                quando = dt.date.fromisoformat(str(item["verificado_em"])[:10])
            except ValueError:
                vencidos.append(f"{p.name}: verificado_em ilegível")
                continue
            validade = int(item.get("validade_dias", 30) or 30)
            if (hoje - quando).days > validade:
                vencidos.append(f"{p.name}: {item['verificado_em']} (+{validade}d)")
    if vencidos:
        return False, f"{len(vencidos)}/{total} fato(s) VENCIDO(S): " + "; ".join(vencidos[:6])
    return True, f"{total} fato(s) com verificado_em, nenhum vencido" if total else "nenhum JSON com verificado_em"


def cheque_legado(raizes: list[Path]) -> tuple[bool, str]:
    residuo: dict[str, int] = {}
    permitido = 0
    for raiz in raizes:
        if not raiz.is_dir():
            continue
        for p in iter_texto(raiz):
            txt = u.safe_read_text(p)
            if not txt:
                continue
            n = len(PADRAO_LEGADO.findall(txt))
            if not n:
                continue
            rel = p.as_posix()
            if any(tag in rel for tag in LEGADO_PERMITIDO):
                permitido += n
            else:
                residuo[rel] = n
    if residuo:
        itens = sorted(residuo.items())
        lista = "; ".join(f"{Path(k).name} ({v})" for k, v in itens[:20])
        if len(itens) > 20:
            lista += f"; … +{len(itens) - 20}"
        return False, f"RESÍDUO em {len(residuo)} arquivo(s): {lista}"
    return True, f"limpo ({permitido} menção(ões) só em reconhecimento deliberado/histórico)"


def batch_com_lf(raiz: Path) -> list[tuple[str, int]]:
    """Todo .cmd/.bat da árvore com pelo menos um LF sem CR antes.

    Devolve [(caminho relativo, quantas linhas em LF)], ordenado. Lista vazia
    = a árvore está sã. Lê em BYTES de propósito: `read_text` normaliza a
    quebra de linha e o defeito desaparece na leitura — foi assim que ele
    sobreviveu a três lições.
    """
    achados: list[tuple[str, int]] = []
    raiz = Path(raiz)
    for dirpath, dirs, files in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in PULAR_CRLF]
        for f in files:
            p = Path(dirpath) / f
            if p.suffix.lower() not in EXT_BATCH:
                continue
            try:
                dados = p.read_bytes()
            except OSError:
                continue
            n = len(PADRAO_LF_SOLTO.findall(dados))
            if n:
                achados.append((p.relative_to(raiz).as_posix(), n))
    return sorted(achados)


def cheque_crlf(raiz: Path) -> tuple[bool, str]:
    achados = batch_com_lf(raiz)
    if achados:
        lista = "; ".join(f"{c} ({n} linha{'s' if n != 1 else ''})" for c, n in achados[:8])
        if len(achados) > 8:
            lista += f"; … +{len(achados) - 8}"
        return False, (f"{len(achados)} .cmd/.bat em LF — o cmd.exe vai comer as "
                       f"primeiras letras das linhas: {lista}")
    return True, "todo .cmd/.bat da central em CRLF"


def cheque_decisoes(central: Path) -> tuple[bool, str]:
    """IDs são endereços: duplicata bloqueia antes de outro agente editar."""
    caminho = u.achar(central, "DECISOES.md")
    if not caminho.is_file():
        return True, "DECISOES.md ausente (nada a conferir)"
    duplicados = trava.conferir_ids(caminho)
    if duplicados:
        return False, "ID DUPLICADO em DECISOES.md: " + ", ".join(duplicados)
    return True, f"{len(trava.ids_de(u.safe_read_text(caminho) or ''))} ids únicos"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, help="central do megabrain ou _github/repo-local")
    p.add_argument("--agentes", action="store_true", help="varre também ~/.claude, ~/.kimi-code, ~/.gemini, ~/.codex")
    p.add_argument("--fetch", action="store_true", help="tenta git fetch antes de comparar (timeout 25s)")
    p.add_argument("--forcar", action="store_true", help="ignora o cache")
    p.add_argument("--ttl", type=float, default=8.0, help="validade do cache em horas")
    args = p.parse_args()

    base = Path(args.repo).resolve()
    if not base.is_dir():
        print(f"ERRO: --repo não existe: {base}")
        return 1
    central = achar_central(base)
    repo = achar_repo(central)
    cache = (repo or central) / ".megabrain" / "preflight.json"

    if not args.forcar:
        txt = u.safe_read_text(cache)
        if txt:
            try:
                dados = json.loads(txt)
                quando = dt.datetime.fromisoformat(dados["quando"])
                if (dt.datetime.now().astimezone() - quando).total_seconds() < args.ttl * 3600:
                    print(f"(cache de {dados['quando'][:16]} — --forcar pra refazer)")
                    print(dados["relatorio"])
                    return dados["exit"]
            except (ValueError, KeyError, TypeError):
                pass

    home = Path(os.environ.get("USERPROFILE") or Path.home())
    raizes_legado = [central]
    if args.agentes:
        raizes_legado += [home / ".claude" / "skills", home / ".kimi-code" / "skills",
                          home / ".kimi-code" / "plugins", home / ".gemini", home / ".codex"]

    resultados = {
        "git": cheque_git(repo, args.fetch),
        "skills": cheque_skills(central, args.agentes),
        "fatos": cheque_fatos(central),
        "legado": cheque_legado(raizes_legado),
        "crlf": cheque_crlf(central),
        "decisoes": cheque_decisoes(central),
    }
    linhas = [f"preflight megabrain · {central}"]
    for nome, (ok, txt) in resultados.items():
        linhas.append(f"  {'✓' if ok else '✗'} {nome:<7} {txt}")
    exit_code = 0 if all(ok for ok, _ in resultados.values()) else 2
    linhas.append("veredito: " + ("PODE COMEÇAR" if exit_code == 0 else "PENDÊNCIA — resolva o ✗ antes de editar"))
    relatorio = "\n".join(linhas)
    print(relatorio)
    u.atomic_write_text(cache, json.dumps({
        "quando": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "exit": exit_code, "relatorio": relatorio,
        "cheques": {k: {"ok": ok, "txt": t} for k, (ok, t) in resultados.items()},
    }, ensure_ascii=False, indent=2) + "\n")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
