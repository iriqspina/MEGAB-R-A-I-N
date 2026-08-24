#!/usr/bin/env python3
"""mb-migrar-motor.py — etapa 2 da reorg: a máquina vai pra motor\\ (v7.1, 260824).

O QUE FAZ: move as pastas de MÁQUINA da raiz da central pra dentro de uma
pasta só (`motor/`), pra raiz mostrar apenas o que é do humano
(00_painel, 01_acoes, 02_entrada, 03_docs, 04_visuais, memoria).

`bin/` NÃO entra: o hook dos agentes (~/.claude/settings.json) aponta pra ele
por caminho absoluto — mover exigiria mexer em config fora da central.

SEGURANÇA
- Dry-run por padrão. Só mexe com --aplicar.
- Recusa se o destino já existir (nada é sobrescrito).
- Conta os arquivos antes e depois: divergiu, grita.
- Grava manifesto em 90_arquivo/migracao-motor-YYMMDD/manifest.json.
- `--desfazer` devolve tudo pra raiz usando o manifesto.

Quem resolve caminho depois disso é mb_utils.pasta()/achar() — nenhum script
deve escrever raiz / "skills" na mão.

Uso:
    python bin/mb-migrar-motor.py            # dry-run
    python bin/mb-migrar-motor.py --aplicar
    python bin/mb-migrar-motor.py --desfazer
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mb_utils as u  # noqa: E402

u.utf8_console()

MOVER = ["skills", "referencias", "modelos", "dna", "tests", "dist",
         "plugin-megabrain", "plugin-megabrain-claude", "gerenteneuron"]

LEIAME = """# motor\\ — a máquina do megabrain

Você não precisa abrir nada aqui. Esta pasta guarda o que faz o megabrain
funcionar; a raiz da central guarda o que é SEU.

| pasta | o que é |
|---|---|
| `skills\\` | os poderes que a IA carrega (/megabrain, /ingerir, ...) |
| `referencias\\` | os textos de método que a IA consulta |
| `modelos\\` | moldes: META, cérebro vazio, peças visuais do relatório |
| `dna\\` | o retrato do protocolo + o backup imaculado das suas infos (`dna\\usuario\\`, nunca sobe) |
| `tests\\` | a rede de segurança: roda com `python bin\\mb-testar.py` |
| `dist\\` | os instaláveis (.plugin/.skill) que você clica pra instalar |
| `plugin-megabrain\\` · `plugin-megabrain-claude\\` | as fontes dos plugins (Kimi e Claude/Cowork) |
| `gerenteneuron\\` | o Neuron: app local e observador de telemetria |

`bin\\` continua na raiz de propósito: o hook dos agentes aponta pra ele por
caminho absoluto, e mover quebraria configuração fora da central.

Criado na etapa 2 da reorg (260824). Manifesto e como desfazer:
`90_arquivo\\migracao-motor-260824\\manifest.json` ·
`python bin\\mb-migrar-motor.py --desfazer`
"""


def conta(d: Path) -> int:
    return sum(1 for x in d.rglob("*") if x.is_file()) if d.is_dir() else 0


def pasta_manifesto(raiz: Path, dia: str) -> Path:
    return u.pasta(raiz, "_arquivo") / f"migracao-motor-{dia}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--desfazer", action="store_true")
    args = ap.parse_args()

    raiz = Path(args.dir).resolve() if args.dir else Path(__file__).resolve().parent.parent
    motor = raiz / u.MOTOR
    dia = dt.date.today().strftime("%y%m%d")
    manif_dir = pasta_manifesto(raiz, dia)
    manif = manif_dir / "manifest.json"

    if args.desfazer:
        if not manif.is_file():
            print(f"ERRO: sem manifesto em {manif} — nada a desfazer")
            return 1
        dados = json.loads(manif.read_text(encoding="utf-8"))
        voltou = []
        for item in dados.get("movidos", []):
            origem = raiz / item["destino"]
            alvo = raiz / item["origem"]
            if not origem.is_dir():
                print(f"  pulando (não está em motor/): {item['destino']}")
                continue
            if alvo.exists():
                print(f"ERRO: {alvo} já existe — desfazer abortado")
                return 1
            shutil.move(str(origem), str(alvo))
            voltou.append(item["origem"])
            print(f"  ← {item['destino']} → {item['origem']}")
        if motor.is_dir() and not any(motor.iterdir()):
            motor.rmdir()
        print(f"desfeito: {len(voltou)} pasta(s) de volta na raiz")
        return 0

    plano, faltando, ocupados = [], [], []
    for nome in MOVER:
        origem = raiz / nome
        destino = motor / nome
        if not origem.is_dir():
            faltando.append(nome)
            continue
        if destino.exists():
            ocupados.append(nome)
            continue
        plano.append({"origem": nome, "destino": f"{u.MOTOR}/{nome}",
                      "arquivos": conta(origem)})

    print(f"etapa 2 · máquina → {u.MOTOR}\\  ·  raiz: {raiz.name}")
    for item in plano:
        print(f"  {item['origem']:<26} → {item['destino']:<34} ({item['arquivos']} arquivos)")
    if faltando:
        print(f"  (não existem na raiz, ignorados: {', '.join(faltando)})")
    if ocupados:
        print(f"  ERRO: já existem no destino: {', '.join(ocupados)}")
        return 1
    if not plano:
        print("nada a mover — a máquina já está no lugar.")
        return 0
    if not args.aplicar:
        print("\ndry-run. Rode com --aplicar pra valer.")
        return 0

    motor.mkdir(exist_ok=True)
    movidos = []
    for item in plano:
        origem, destino = raiz / item["origem"], raiz / item["destino"]
        antes = item["arquivos"]
        shutil.move(str(origem), str(destino))
        depois = conta(destino)
        if antes != depois:
            print(f"  ERRO: {item['origem']} tinha {antes} arquivos e chegou com {depois}")
            return 1
        movidos.append(item)
        print(f"  → {item['origem']} ({depois} arquivos)")

    u.atomic_write_text(motor / "LEIAME.md", LEIAME)
    manif_dir.mkdir(parents=True, exist_ok=True)
    u.atomic_write_text(manif, json.dumps({
        "quando": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "raiz": str(raiz), "motor": u.MOTOR, "movidos": movidos,
        "como_desfazer": "python bin/mb-migrar-motor.py --desfazer",
        "bin_ficou_na_raiz": "hook externo (~/.claude/settings.json) aponta pra bin/",
    }, ensure_ascii=False, indent=1) + "\n")
    print(f"\nmanifesto: {manif}")
    print("agora rode: python bin/mb-testar.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
