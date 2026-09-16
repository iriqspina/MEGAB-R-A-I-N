"""Settings do widget — arquivo próprio, independente do registro de dados."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULTS = {
    "pos_x": None,
    "pos_y": None,
    "opacity_percent": 76,
    "scale": 1.0,
    "expanded": False,
    "show_paused": False,
    "poll_seconds": 60,
    "raiz": None,  # None = usa a raiz do registro (dados/pendencias.json)
}


def load(path: Path) -> dict:
    dados = dict(DEFAULTS)
    if Path(path).exists():
        try:
            carregado = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(carregado, dict):
                dados.update({k: v for k, v in carregado.items() if k in DEFAULTS})
        except (json.JSONDecodeError, OSError):
            pass  # settings corrompido = defaults; nunca derruba o widget
    return dados


def save(path: Path, dados: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    limpo = {k: dados.get(k, DEFAULTS[k]) for k in DEFAULTS}
    Path(path).write_text(json.dumps(limpo, ensure_ascii=False, indent=2), encoding="utf-8")
