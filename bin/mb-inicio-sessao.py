#!/usr/bin/env python3
"""Prepara uma sessão MEGABRAIN sem iniciar modelo nem execução.

Mostra o catálogo de skills da fonte canônica e a instrução curta que abre uma
conversa com qualquer IA. A V6 é o padrão para entrega nova não trivial; este
script não a executa sem um brief e um projeto explícitos.
"""
from __future__ import annotations

import argparse
import importlib.util
import hashlib
import json
import os
import re
import sys
from pathlib import Path


CENTRAL = Path(__file__).resolve().parents[1]
SKILLS = CENTRAL / "motor" / "skills"


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        raise ValueError("frontmatter ausente")
    return dict(re.findall(r"^(name|description):\s*(.+)$", match.group(1), re.MULTILINE))


def catalogo(root: Path = CENTRAL) -> list[dict[str, str]]:
    skills = root / "motor" / "skills"
    rows = []
    for path in sorted(skills.glob("*/SKILL.md"), key=lambda item: item.parent.name.casefold()):
        meta = _frontmatter(path)
        rows.append({
            "nome": meta.get("name", path.parent.name),
            "descricao": meta.get("description", "sem descrição"),
            "arquivo": str(path.relative_to(root)).replace("\\", "/"),
        })
    return rows


def leitura_uso(root: Path = CENTRAL) -> dict:
    """Somente leitura; conta/capacidade ausente jamais vira saldo disponível."""
    reader = root / "bin" / "mb-leitura-uso.py"
    if not reader.is_file():
        return {"error": "NAO_MEDIDO: leitor de cotas ausente", "dispatch_authorized": False}
    spec = importlib.util.spec_from_file_location("mb_leitura_uso_startup", reader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ler(root / "dados" / "orcamento_ia.json")


def contexto_visual(root: Path = CENTRAL, carregar: bool = False, caso_id: str | None = None) -> dict:
    protocolo = root / "motor/referencias/260921_aprendizado-visual.md"
    base = root / "memoria/cerebro/visual"
    registro = base / "260921_casos-visuais.json"
    result = {"protocolo": str(protocolo), "registro": str(registro), "carregado": False,
              "instrucao": "--visual carrega protocolo/catálogo; --caso-visual ID carrega só o caso pertinente. Existência não aprova render."}
    if not carregar and caso_id is None:
        return result
    try:
        body = protocolo.read_text(encoding="utf-8-sig")
        catalogo = json.loads(registro.read_text(encoding="utf-8-sig"))
        entries = catalogo.get("casos")
        if not isinstance(entries, list) or any(not isinstance(row, dict) or not all(isinstance(row.get(key), str) for key in ("id", "titulo", "arquivo")) for row in entries):
            raise ValueError("catálogo visual inválido")
        if len({row["id"] for row in entries}) != len(entries):
            raise ValueError("IDs visuais duplicados")
        result.update({"texto_protocolo": body, "catalogo_casos": entries,
                       "sha256_protocolo": hashlib.sha256(protocolo.read_bytes()).hexdigest(),
                       "limite": "Leitura de protocolo/catálogo; não certifica inspeção de imagem nova."})
        if caso_id is not None:
            selected = next((row for row in entries if row["id"] == caso_id), None)
            if selected is None:
                raise ValueError("caso não cadastrado")
            caso = (base / selected["arquivo"]).resolve()
            if not caso.is_relative_to(base.resolve()):
                raise ValueError("caso fora do acervo visual")
            sample = json.loads(caso.read_text(encoding="utf-8-sig"))
            if not isinstance(sample, dict) or not isinstance(sample.get("criteria"), list) or not isinstance(sample.get("runs"), list):
                raise ValueError("caso visual sem critérios/resultados")
            result.update({"caso": str(caso), "caso_contextual": sample,
                           "sha256_caso": hashlib.sha256(caso.read_bytes()).hexdigest()})
        result["carregado"] = True
    except (OSError, ValueError, TypeError, AttributeError):
        result["erro"] = "Contexto/caso visual ausente ou inválido; não declarar exemplo carregado ou inspeção aprovada."
    return result


def resumo(root: Path = CENTRAL, visual: bool = False, caso_visual: str | None = None) -> dict[str, object]:
    rows = catalogo(root)
    names = {item["nome"] for item in rows}
    return {
        "central": str(root),
        "leitura_uso": leitura_uso(root),
        "aprendizado_visual": contexto_visual(root, visual, caso_visual),
        "skills": rows,
        "padrao": "/orquestracao1 (V6)",
        "v5": "/orquestracao2 (somente retomada ou pedido explícito)",
        "pronto": {"megabrain", "orquestracao1", "orquestracao2"}.issubset(names),
        "instrucao_para_ia": (
            "Início de sessão MEGABRAIN: leia o catálogo motor/skills e leia por inteiro "
            "as SKILL.md necessárias antes de agir. Para entrega nova não trivial e "
            "decomponível, inicie /orquestracao1 (V6). Não inicie execução para pergunta "
            "simples, conversa, agenda ou correção local óbvia. Use /orquestracao2 apenas "
            "para retomada V5 ou pedido explícito. Antes de planejar uma entrega, leia /amadurecer "
            "e o snapshot leitura_uso; atualize cotas por conta antes de cada despacho. "
            "Compare somente janelas equivalentes e atuais, reserve o limite mais restritivo "
            "e verifique ferramentas, dependências e revisão independente. Codex 1, Codex 2 "
            "e ZCode são clientes/contas reais; não simule participação com nomes de workers. "
            "Distribua trabalho útil para reduzir pressão desigual sem gastar só para igualar "
            "percentuais; custo estimado não é custo medido. Registre rota, prova e reavaliação. "
            "Se o trabalho é visual, rode --visual e aplique o protocolo por formato: "
            "decisão humana, fato observado e inferência separados; compare renders e registre "
            "resultado/evidência por critério antes de declarar aprovação técnica. "
            "Relatórios novos ou regenerados: leia /relatorios-glm; GLM principal MAX compõe e corrige, "
            "Codex/Claude revisam fontes e pixels e podem criar modelos finalizados. Exceção só crédito "
            "extremo comprovado sem reset útil; validar bin/mb-relatorios-glm.py. Evitar Claude MAX e ultracode."
        ),
    }


def curta(descricao: str, limite: int = 130) -> str:
    """Mantém o atalho escaneável; --json preserva a descrição integral."""
    primeira = descricao.split(". ", 1)[0].strip()
    if len(primeira) <= limite:
        return primeira
    return primeira[:limite - 1].rstrip() + "…"


def conectar_app(project: Path, application: str | None = None,
                 session_id: str | None = None, no_open: bool = False, hook: dict | None = None) -> dict:
    try:
        spec = importlib.util.spec_from_file_location("mb_startup_bridge", CENTRAL / "bin/mb-session-bridge.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.connect(project, central=CENTRAL, application=application,
                              session_id=session_id, hook=hook, no_open=no_open, source="mb-inicio-sessao")
    except (OSError, ValueError, AttributeError, ImportError):
        return {"presentation_state": "unavailable", "error": "session_registration_unavailable"}


def auditar_relatorios(project: Path) -> dict:
    """Fiscalização mecânica da sessão; não despacha IA nem retoma tarefas."""
    helper = CENTRAL / "bin/mb-auditar-relatorios-glm.py"
    if not helper.is_file():
        return {"status": "NAO_MEDIDO", "reason": "monitor ausente"}
    try:
        spec = importlib.util.spec_from_file_location("mb_startup_report_audit", helper)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.audit(project=project)
        rows = [row for item in result["projects"] for row in item["reports"]]
        return {"status": "observado", "changed": result["changed"],
                "reports": len(rows), "blocked": sum(bool(row.get("blocked")) for row in rows),
                "model_calls": 0, "queue": str(project / ".automations/relatorios-glm/fila-correcao.json")}
    except (OSError, ValueError, ImportError, AttributeError, KeyError) as exc:
        return {"status": "NAO_MEDIDO", "reason": str(exc), "model_calls": 0}


def projeto_sessao(path: Path) -> Path:
    path = path.expanduser().resolve()
    for candidate in (path, *path.parents):
        if (candidate == CENTRAL or (candidate / "MEGABRAIN").is_dir()
                or (candidate / ".mb-origem.json").is_file()):
            return candidate
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="saída para dashboard ou outro agente")
    parser.add_argument("--visual", action="store_true", help="carrega protocolo e caso visual contextual")
    parser.add_argument("--caso-visual", help="ID do caso pertinente no catálogo visual; implica --visual")
    parser.add_argument("--project", "--projeto", help="raiz do projeto desta sessão")
    parser.add_argument("--application", help="nome do cliente que abriu a sessão")
    parser.add_argument("--session-id", help="identidade estável da sessão fornecida pelo cliente")
    parser.add_argument("--no-app", action="store_true", help="registra sessão sem solicitar janela")
    parser.add_argument("--hook", action="store_true", help="lê session_id/cwd opcionais do JSON de stdin")
    args = parser.parse_args(argv)
    hook = {}
    if args.hook and not sys.stdin.isatty():
        try:
            value = json.load(sys.stdin)
            if isinstance(value, dict):
                hook = {key: value[key] for key in ("session_id", "cwd", "application", "aplicacao")
                        if isinstance(value.get(key), str)}
        except (ValueError, OSError):
            pass
    data = resumo(visual=args.visual, caso_visual=args.caso_visual)
    data["conexao_app"] = conectar_app(projeto_sessao(Path(args.project or hook.get("cwd") or os.getcwd())),
                                      args.application or hook.get("application", hook.get("aplicacao")),
                                      args.session_id, args.no_app, hook)
    data["auditoria_relatorios"] = auditar_relatorios(projeto_sessao(Path(args.project or hook.get("cwd") or os.getcwd())))
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0 if data["pronto"] and "erro" not in data["aprendizado_visual"] else 2

    print("MEGABRAIN — início de sessão")
    print(f"Aplicativo: sessão {data['conexao_app']['presentation_state']}; abertura requer recibo nativo.")
    print("V6 padrão: /orquestracao1 para entrega nova não trivial e decomponível.")
    print("V5: /orquestracao2 só para retomada ou pedido explícito.")
    print("Este comando não chama IA, não inicia loop e não consome cota.\n")
    print("Cotas no startup (snapshot local, renovar antes do despacho):")
    for account in data["leitura_uso"].get("accounts", []):
        print(f"  {account['provider']}: {account['verdict']} · idade {account['age_seconds']} s")
    if "error" in data["leitura_uso"]:
        print(data["leitura_uso"]["error"])
    print("Saldo não comprova capacidade; não há despacho automático.\n")
    if args.visual or args.caso_visual:
        print("Aprendizado visual:")
        print(json.dumps(data["aprendizado_visual"], ensure_ascii=False, indent=2))
    print("Skills disponíveis na fonte canônica:")
    for item in data["skills"]:
        print(f"  - /{item['nome']}: {curta(item['descricao'])}")
    print("\nCopie e cole na IA desta sessão:")
    print(data["instrucao_para_ia"])
    return 0 if data["pronto"] and "erro" not in data["aprendizado_visual"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print("Precisa de atenção: " + str(exc))
        raise SystemExit(2)
