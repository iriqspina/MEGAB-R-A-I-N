#!/usr/bin/env python3
"""
mb-arrumar.py — poe a pasta do megabrain em ordem sem quebrar quem depende dela.

Faz cinco coisas, nesta ordem:
  1. mostra o plano (dry-run e o padrao - nada e tocado sem --aplicar);
  2. so remove duplicata se o hash for identico ao do arquivo que fica;
  3. faz backup .zip da raiz antes de qualquer escrita;
  4. move arquivo e conserta as referencias que apontavam pro lugar antigo;
  5. varre o resultado atras de referencia orfa e diz o que sobrou.

Uso:
  python bin/mb-arrumar.py --raiz .              # so mostra o plano
  python bin/mb-arrumar.py --raiz . --aplicar    # executa, com backup antes
  python bin/mb-arrumar.py --raiz . --verificar  # so procura referencia orfa
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

import mb_utils as u

u.utf8_console()

TEXTO = {".md", ".txt", ".py", ".cmd", ".json", ".yaml", ".yml", ".html"}


def sha(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


# --------------------------------------------------------------------- plano
# tipo, origem, destino, motivo
# v2 (260822): raiz enxuta — executaveis em scripts/, congelados em _arquivo/,
# instalaveis em dist/. "remover" nunca apaga: vai para _to_delete/ (o humano
# esvazia). Mover nao renomeia: arquivo datado continua datado.
PLANO: list[tuple[str, str, str, str]] = [
    ("dedup", "SKILL.md", "skills/megabrain/SKILL.md",
     "duplicata byte a byte; os scripts do pacote elegem skills/megabrain como fonte"),
    ("dedup", "260810_MEGABRAIN.md", "MEGABRAIN.md",
     "duplicata byte a byte; prefixo de data nao serve a arquivo canonico"),
    ("dedup", "referencias/anti-slop.md", "referencias/260810_anti-slop.md", "copia sem data, identica"),
    ("dedup", "referencias/metaprompt-patterns.md", "referencias/260810_metaprompt-patterns.md", "copia sem data, identica"),
    ("remover", "LEIAME.md", "", "so aponta pro README.md e se justifica com uma premissa falsa"),
    ("remover", "LEIAME.txt", "", "ja vive em modelos/LEIAME-megabrain-do-projeto.txt (arrumacao v1)"),
    ("remover", "requirements.txt", "", "ja vive em docs/dependencias-sugeridas.txt (arrumacao v1)"),
    ("remover", "bin/260810_mb-sync.py", "", "versao antiga do mb-sync"),
    # executaveis
    ("mover", "260824_abrir-kimi-visual.cmd", "scripts/260824_abrir-kimi-visual.cmd", "executavel sai da raiz"),
    ("mover", "260824_instalar-identidade.cmd", "scripts/260824_instalar-identidade.cmd", "executavel sai da raiz"),
    ("mover", "260824_publicar-e-fotografar.cmd", "scripts/260824_publicar-e-fotografar.cmd", "executavel sai da raiz"),
    ("mover", "260824_sincronizar-identidade.cmd", "scripts/260824_sincronizar-identidade.cmd", "executavel sai da raiz"),
    ("mover", "260824_refresh-plugin-kimi.cmd", "scripts/260824_refresh-plugin-kimi.cmd", "executavel sai da raiz"),
    ("mover", "260824_enviar-pro-github.cmd", "scripts/260824_enviar-pro-github.cmd", "executavel sai da raiz"),
    ("mover", "260824_novo-projeto.cmd", "scripts/260824_novo-projeto.cmd", "executavel sai da raiz"),
    ("mover", "260824_sincronizar-projetos.cmd", "scripts/260824_sincronizar-projetos.cmd", "executavel sai da raiz"),
    # congelados / historico
    ("mover", "PIPELINE.md", "_arquivo/PIPELINE.md", "v2 congelado, substituido por MEGABRAIN.md"),
    ("mover", "260810_VISAO-GERAL.md", "_arquivo/260810_VISAO-GERAL.md", "diario da fusao 260810, nao protocolo"),
    ("mover", "260805_licoes-backup-pre-fix.md", "_arquivo/260805_licoes-backup-pre-fix.md", "backup pontual"),
    ("mover", "260810_backup-raiz-perfil", "_arquivo/260810_backup-raiz-perfil", "backup pontual"),
    ("mover", "260810_variantes", "_arquivo/260810_variantes", "variantes da fusao 260810"),
    ("mover", "260811_prompt-claude-handoff.txt", "_arquivo/260811_prompt-claude-handoff.txt", "prompt pontual"),
    ("mover", "260816_AUDITORIA-megabrain-v5.1.md", "_arquivo/260816_AUDITORIA-megabrain-v5.1.md", "auditoria fechada (v5.1)"),
    ("mover", "260816_RELATORIO-gerenteneuron-v1.html", "_arquivo/260816_RELATORIO-gerenteneuron-v1.html", "relatorio datado"),
    ("mover", "260819_RELATORIO-compreensao-megabrain.html", "_arquivo/260819_RELATORIO-compreensao-megabrain.html", "relatorio datado"),
    ("mover", "260821_RELATORIO-cowork-sensacionalista.html", "_arquivo/260821_RELATORIO-cowork-sensacionalista.html", "relatorio datado"),
    ("mover", "referencias/context-engineering.md", "_arquivo/referencias-v1/context-engineering.md", "fork sem data; a datada e a fonte"),
    ("mover", "referencias/evaluation-gates.md", "_arquivo/referencias-v1/evaluation-gates.md", "fork sem data; a datada e a fonte"),
    ("mover", "referencias/prompt-portatil.md", "_arquivo/referencias-v1/prompt-portatil.md", "fork sem data; a datada e a fonte"),
    ("mover", "referencias/design-duplo-diamante.md", "_arquivo/referencias-v1/design-duplo-diamante.md", "fork sem data; 260810_design-projects.md e a fonte"),
    # v3 (260822, raiz zero): canonicos em nucleo/, estado/, identidade/, relatorios/
    # — tabela em mb_utils.PASTAS_RAIZ; scripts resolvem com u.achar().
    *[("mover", nome, f"{pasta}/{nome}", "raiz sem arquivo solto (v6.3)") for nome, pasta in u.PASTAS_RAIZ.items()],
    # instalaveis
    ("mover", "260816_gerenteneuron.skill", "dist/260816_gerenteneuron.skill", "instalavel sai da raiz"),
    ("mover", "260821_megabrain-v1.1.1.plugin", "dist/260821_megabrain-v1.1.1.plugin", "instalavel sai da raiz"),
]

# arquivo alvo, trecho antigo, trecho novo  (aplicado so se o trecho existir)
PATCHES: list[tuple[str, str, str]] = [
    ("scripts/260824_instalar-identidade.cmd", '%~dp0260810_memoria-pessoal.md', '%~dp0..\\260810_memoria-pessoal.md'),
    ("scripts/260824_instalar-identidade.cmd", '%~dp0bin\\', '%~dp0..\\bin\\'),
    ("scripts/260824_sincronizar-identidade.cmd", 'set "MB=%~dp0"', 'set "MB=%~dp0..\\"'),
    ("scripts/260824_publicar-e-fotografar.cmd", '%~dp0_github/export', '%~dp0..\\_github/export'),
    ("scripts/260824_publicar-e-fotografar.cmd", '%~dp0_github/repo-local', '%~dp0..\\_github/repo-local'),
    ("scripts/260824_publicar-e-fotografar.cmd", '%~dp0bin\\', '%~dp0..\\bin\\'),
    ("scripts/260824_publicar-e-fotografar.cmd", '%~dp0VERSAO.txt', '%~dp0..\\VERSAO.txt'),
    ("scripts/260824_enviar-pro-github.cmd", 'set "RAIZ=%~dp0"', 'set "RAIZ=%~dp0..\\"'),
    ("scripts/260824_novo-projeto.cmd", 'set "FONTE=%~dp0"', 'set "FONTE=%~dp0..\\"'),
    ("scripts/260824_novo-projeto.cmd", 'set "CFG=%~dp0.mb-projetos.cmd"', 'set "CFG=%~dp0..\\.mb-projetos.cmd"'),
    ("README.md", '- `SKILL.md` — o protocolo:', '- `skills/megabrain/SKILL.md` — o protocolo:'),
    ("MEGABRAIN.md", '| `PIPELINE.md` | v2, congelado', '| `_arquivo/PIPELINE.md` | v2, congelado'),
    ("MEGABRAIN.md", '`PIPELINE.md` continua no disco (não apago nem renomeio arquivo já escrito)', '`PIPELINE.md` foi para `_arquivo/` (260822; nome preservado)'),
    ("MEGABRAIN.md", "Ver `260810_VISAO-GERAL.md`", "Ver `_arquivo/260810_VISAO-GERAL.md`"),
    ("MEGABRAIN.md", "5. Espalhar → `260824_sincronizar-projetos.cmd`.", "5. Espalhar → `scripts/260824_sincronizar-projetos.cmd`."),
    ("MEGABRAIN.md", "nível 1 (`260824_novo-projeto.cmd`)", "nível 1 (`scripts/260824_novo-projeto.cmd`)"),
    ("CHECKLIST-ABERTURA.md", "`260824_sincronizar-projetos.cmd`", "`scripts/260824_sincronizar-projetos.cmd`"),
    ("CHECKLIST-ABERTURA.md", "`260824_sincronizar-identidade.cmd`", "`scripts/260824_sincronizar-identidade.cmd`"),
    ("referencias/260818_padrao-resposta.md", "(`260824_sincronizar-identidade.cmd`)", "(`scripts/260824_sincronizar-identidade.cmd`)"),
    ("modelos/LEIAME-megabrain-do-projeto.txt", "rode 260824_sincronizar-projetos.cmd lá", "rode scripts\\260824_sincronizar-projetos.cmd lá"),
    ("HANDOFF.md", "Duplo\n   clique em `260824_enviar-pro-github.cmd`", "Duplo\n   clique em `scripts/260824_enviar-pro-github.cmd`"),
]

# arquivos que FALAM dos nomes antigos por oficio - nao sao referencia quebrada
IGNORAR_NA_VARREDURA = ("bin/mb-arrumar.py", "docs/", "AUDITORIA-", "PAINEL-MEGABRAIN.html",
                        "_arquivo/", "_to_delete/", "90_arquivo/", "99_to_delete/", "memoria/pendencias/", "03_docs/", ".orquestrador/", "DECISOES.md",
                        "licoes-megabrain.md", "PROGRESSO.json", "alteracoes-pendentes/",
                        "_github/export/", "_github/repo-local/", "RELATORIO", "META.md",
                        "bin/mb-generate-template.py", "bin/mb-preflight.py", "VERSAO.txt", "HANDOFF.md", "ESTADO.md", "bin/mb-check-version.py",
                        ".mb-aspirador/", ".venv/", "dna/indice-licoes.json", "site-packages/")

# nomes que nao podem sobrar referenciados depois da arrumacao
ORFAOS = ["260810_MEGABRAIN.md", "260810_mb-sync.py", "LEIAME.md", "requirements.txt",
          "260810_VISAO-GERAL.md", "design-duplo-diamante.md"]


def cabecalho_dependencias() -> str:
    return (
        "DEPENDENCIAS SUGERIDAS (nao obrigatorias)\n"
        "=========================================\n\n"
        "Nenhum script de bin/ importa qualquer uma destas bibliotecas. O nucleo\n"
        "roda em stdlib pura e continua rodando sem instalar nada. A lista abaixo\n"
        "e um roteiro de evolucao, nao um requisito de execucao - por isso deixou\n"
        "de se chamar requirements.txt.\n\n"
    )


def executar(raiz: Path, aplicar: bool) -> int:
    print(f"raiz: {raiz}\nmodo: {'APLICAR' if aplicar else 'dry-run (nada sera tocado)'}\n")
    acoes: list[tuple[str, str, str, str]] = []

    for tipo, origem, destino, motivo in PLANO:
        o = raiz / origem
        if not o.exists():
            print(f"  --    {origem}: nao existe, pulando")
            continue
        if tipo == "dedup":
            d = raiz / destino
            if not d.exists():
                print(f"  !!    {origem}: o par {destino} nao existe — nao removo nada")
                continue
            if sha(o) != sha(d):
                print(f"  !!    {origem}: hash DIFERENTE de {destino} — divergiram, resolva na mao")
                continue
            print(f"  del   {origem}\n        idêntico a {destino} · {motivo}")
            acoes.append(("remover", origem, "", motivo))
        elif tipo == "remover":
            print(f"  del   {origem}\n        {motivo}")
            acoes.append(("remover", origem, "", motivo))
        else:
            print(f"  mv    {origem} → {destino}\n        {motivo}")
            acoes.append(("mover", origem, destino, motivo))

    if not aplicar:
        print(f"\n{len(acoes)} ação(ões) no plano. Rode de novo com --aplicar para executar.")
        return 0
    if not acoes:
        print("\nnada a mover ou remover — só conferindo referências.")
        return patches_e_verificacao(raiz)

    carimbo = dt.datetime.now().strftime("%y%m%d-%H%M")
    backup = raiz / f".mb-backup/arrumar-{carimbo}.zip"
    backup.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(backup, "w", zipfile.ZIP_DEFLATED) as z:
        for f in raiz.rglob("*"):
            if f.is_file() and ".mb-backup" not in f.parts and ".git" not in f.parts and "_to_delete" not in f.parts and "__pycache__" not in f.parts:
                z.write(f, f.relative_to(raiz))
    print(f"\nbackup: {backup.relative_to(raiz)}")

    for tipo, origem, destino, _ in acoes:
        o = raiz / origem
        if tipo == "remover":
            lixo = u.pasta(raiz, "_to_delete") / origem
            lixo.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(o), str(lixo))
        else:
            d = raiz / destino
            d.parent.mkdir(parents=True, exist_ok=True)
            if destino.endswith("dependencias-sugeridas.txt"):
                d.write_text(cabecalho_dependencias() + o.read_text(encoding="utf-8"), encoding="utf-8")
                shutil.move(str(o), str(u.pasta(raiz, "_to_delete") / origem))
            else:
                shutil.move(str(o), str(d))
    print(f"{len(acoes)} ação(ões) executada(s).")
    return patches_e_verificacao(raiz)


def patches_e_verificacao(raiz: Path) -> int:
    print("\nreferências:")
    for alvo, antes, depois in PATCHES:
        f = raiz / alvo
        if not f.exists():
            print(f"  --    {alvo}: nao existe")
            continue
        txt = f.read_text(encoding="utf-8", errors="ignore")
        if depois in txt:
            print(f"  ja    {alvo}: já ajustado")
        elif antes in txt:
            f.write_text(txt.replace(antes, depois), encoding="utf-8")
            print(f"  ok    {alvo}: {antes[:48]}…")
        else:
            print(f"  --    {alvo}: trecho ausente")

    return verificar(raiz)


def verificar(raiz: Path) -> int:
    print("\nvarredura de referência órfã:")
    achou = 0
    for f in sorted(raiz.rglob("*")):
        if not f.is_file() or f.suffix not in TEXTO:
            continue
        rel = f.relative_to(raiz).as_posix()
        if ".git" in f.parts or ".mb-backup" in f.parts:
            continue
        if any(marca in rel for marca in IGNORAR_NA_VARREDURA):
            continue
        txt = f.read_text(encoding="utf-8", errors="ignore")
        for orfao in ORFAOS:
            if orfao in txt and not (raiz / orfao).exists() and not (raiz / "referencias" / orfao).exists():
                for n, linha in enumerate(txt.splitlines(), 1):
                    if orfao in linha and ("_arquivo/" + orfao) not in linha and ("_to_delete/" + orfao) not in linha and ("90_arquivo/" + orfao) not in linha and ("99_to_delete/" + orfao) not in linha:
                        print(f"  {f.relative_to(raiz)}:{n} → {orfao}")
                        achou += 1
    if achou:
        print(f"\n{achou} referência(s) apontando pra arquivo que nao existe mais. Conserte antes de commitar.")
        return 1
    print("  nenhuma. arvore consistente.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--verificar", action="store_true")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    if not u.achar(raiz, "VERSAO.txt").exists():
        print(f"{raiz} nao parece ser a raiz do megabrain (sem VERSAO.txt).")
        return 1
    if args.verificar:
        return verificar(raiz)
    return executar(raiz, args.aplicar)


if __name__ == "__main__":
    sys.exit(main())
