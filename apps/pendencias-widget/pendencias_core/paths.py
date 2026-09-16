import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "app" / "data"
SETTINGS_PATH = DATA_DIR / "settings.json"
SINGLETON_KEY = "pendencias-widget-260916-singleton"

# Central MEGABRAIN — apps/pendencias-widget fica duas pastas abaixo dela.
# Mesma convenção do Cotas IA (ver apps/ia-quota-widget/widget_app/paths.py).
CENTRAL_DIR = Path(os.environ.get("MEGABRAIN_CENTRAL") or os.environ.get("MEGABRAIN_HOME") or APP_DIR.parent.parent)

# Fonte da verdade: um JSON só, escrito somente pelo CLI (bin/mb-pendencias.py).
# O widget apenas LÊ — duas fontes escrevendo foi a causa do bug das 2
# instâncias do Cotas IA brigando pelo arquivo (260916).
REGISTRY_PATH = Path(os.environ.get("MEGABRAIN_PENDENCIAS") or (CENTRAL_DIR / "dados" / "pendencias.json"))


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
